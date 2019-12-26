from .proxy_thread import ProxyThread
from ..utils.functions import bypass_error
from ..utils.socket import close_socket_pass_exc
from traceback import format_exc


class HttpProxyThread(ProxyThread):
    def __init__(self, cli_socket, cli_address, server_socket, server_name):
        ProxyThread.__init__(self, cli_socket, cli_address, server_socket, server_name)

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

    def run(self) -> None:
        try:
            # init vars
            remote_socket = None
            remote_address = None
            remote_buffer = ''
            # loop to route requests and responses
            # between client and remote host
            while 1:
                # receive data from client
                local_buffer = self._receive_from(self._cli_socket, self._cli_address)

                # if client is disconnect close connection and return
                if isinstance(local_buffer, bool) and not local_buffer:
                    close_socket_pass_exc(self._cli_socket)
                    close_socket_pass_exc(remote_socket)
                    self._logger.print_conn("[!!] Client %s:%d is disconnected\n" % self._cli_address)
                    return

                if len(local_buffer):
                    self._logger.log_buffer(self._cli_address, local_buffer, True)

                    # change request with handler
                    local_buffer = self.__req_handler(local_buffer)

                    if remote_address is None:
                        # get host and port remote and create socket
                        remote_address = self._get_remote_address(local_buffer)
                        remote_socket = self._get_remote_socket(remote_address)

                    # send data at remote host
                    remote_socket.sendall(local_buffer)

                if remote_socket is not None:
                    # receive response from remote
                    remote_buffer = self._receive_from(remote_socket, remote_address)
                    # if remote is disconnect close connection and return
                    if isinstance(remote_buffer, bool) and not remote_buffer:
                        close_socket_pass_exc(self._cli_socket)
                        close_socket_pass_exc(remote_socket)
                        self._logger.print_conn("[!!] Remote %s:%d is disconnected\n" % remote_address)
                        return

                    # if have data from remote log it and send response to client
                    if len(remote_buffer):
                        self._logger.log_buffer(remote_address, remote_buffer, False)

                        # change response with handler
                        remote_buffer = self.__resp_handler(remote_buffer)

                        # send response to client
                        self._cli_socket.sendall(remote_buffer)

                # if there are no other data close the connections
                if not (len(remote_buffer) or len(local_buffer)):
                    close_socket_pass_exc(self._cli_socket)
                    close_socket_pass_exc(remote_socket)
                    self._logger.print_conn('[*] No more data. Closing connection with client %s:%d\n' % self._cli_address)
                    break
        except Exception as e:
            close_socket_pass_exc(self._cli_socket)
            out = '' if bypass_error(e) else format_exc()
            out += "[!!] Caught a exception on %s: %s" % (self.name, str(e))
            self._logger.print_err(out)
            return
