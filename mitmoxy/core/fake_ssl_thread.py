from .proxy_thread import ProxyThread
from ..utils.functions import bypass_error
from ..utils.socket import close_socket_pass_exc
from traceback import format_exc


class FakeSslThread(ProxyThread):

    def __init__(self, cli_socket, cli_address, server_socket, remote_address):
        ProxyThread.__init__(self, cli_socket, cli_address, server_socket)
        self.__remote_address = remote_address

    #####################################
    # PRIVATE METHODS
    #####################################

    # handler to change a request
    def __req_handler(self, buffer: bytes) -> bytes:
        return buffer

    # handler to change a response
    def __resp_handler(self, buffer: bytes) -> bytes:
        return buffer

    #####################################
    # PUBLIC METHODS
    #####################################

    # function to manage connection with client
    def run(self) -> None:
        remote_socket = None
        try:
            # get host and port of client
            # cli_socket. = cli_socket.getpeername()
            # get remote socket
            remote_socket = self._get_remote_socket(self.__remote_address, True)
        except Exception as e:
            close_socket_pass_exc(self._cli_socket)
            close_socket_pass_exc(remote_socket)
            out = '' if bypass_error(e) else format_exc()
            out += "[!!] Caught a exception on proxy: %s" % str(e)
            self._logger.print_err(out)
            return
        fail = 0
        # loop to route requests and responses
        # between client and remote host
        while 1:
            # receive data from client
            local_buffer = self._receive_from(self._cli_socket, self._cli_address)

            # if client is disconnect close connection and return
            if isinstance(local_buffer, bool) and not local_buffer:
                close_socket_pass_exc(remote_socket)
                close_socket_pass_exc(self._cli_socket)
                out = "[!!] Client %s:%d is disconnected\n" % self._cli_address
                out += "'############ END CONNECTION ############\n'"
                self._logger.print(out)
                return

            # if receive data from client
            if len(local_buffer):
                fail = 0

                # change reques with handler and log it
                local_buffer = self.__req_handler(local_buffer)
                self._logger.log_buffer(self._cli_address, local_buffer, True)

                # send data at remote host
                remote_socket.sendall(local_buffer)

            # receive response from remote
            remote_buffer = self._receive_from(remote_socket, self.__remote_address)

            # if remote is disconnect close connection and return
            if isinstance(remote_buffer, bool) and not remote_buffer:
                close_socket_pass_exc(remote_socket)
                close_socket_pass_exc(self._cli_socket)
                out = "[!!] Remote %s:%d is disconnected\n" % self.__remote_address
                out += "'############ END CONNECTION ############\n'"
                self._logger.print(out)
                return

            # if receive data from remote
            if len(remote_buffer):
                fail = 0

                # change response with handler and log it
                remote_buffer = self.__resp_handler(remote_buffer)
                self._logger.log_buffer(self.__remote_address, remote_buffer, False)

                # send response to client
                self._cli_socket.sendall(remote_buffer)

            # check len of buffers
            if not (len(local_buffer) or len(remote_buffer)):
                fail += 1
                # if fails too many times close connections
                if fail >= self._max_fails:
                    out = "[!!] Fails to many times!!! Close connection with %s:%d client\n" % self._cli_address
                    out += '############ END CONNECTION ############\n'
                    self._logger.print(out)
                    close_socket_pass_exc(remote_socket)
                    close_socket_pass_exc(self._cli_socket)
                    return