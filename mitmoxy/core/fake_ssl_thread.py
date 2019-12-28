from .proxy_thread_abc import ProxyThreadABC
from ..utils.functions import bypass_error
from ..utils.socket import close_socket_pass_exc
from ..utils.handlers import *
from traceback import format_exc


class FakeSslThreadABC(ProxyThreadABC):

    def __init__(self, cli_socket, cli_address, server_socket, remote_address, server_name):
        ProxyThreadABC.__init__(self, cli_socket, cli_address, server_socket, server_name)
        self.__remote_address = remote_address
        self.name = "%s handler thread" % server_name

    #####################################
    # PUBLIC METHODS
    #####################################

    # function to manage connection with client
    def run(self) -> None:
        remote_socket = None
        try:
            # get remote socket
            remote_socket = self._get_remote_socket(self.__remote_address, True)
        except Exception as e:
            close_socket_pass_exc(self._cli_socket)
            close_socket_pass_exc(remote_socket)
            out = '' if bypass_error(e) else format_exc()
            out += "[!!] Caught a exception on %s: %s" % (self.name, str(e))
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

                self._logger.print("[*] Local client is disconnected to %s\n" % self.name)
                return

            # if receive data from client
            if len(local_buffer):
                fail = 0

                # change request with handler and log it
                local_buffer = req_handle(local_buffer)
                self._logger.log_buffer(self._cli_address, local_buffer, True)

                # send data at remote host
                remote_socket.sendall(local_buffer)

            # receive response from remote
            remote_buffer = self._receive_from(remote_socket, self.__remote_address)

            # if remote is disconnect close connection and return
            if isinstance(remote_buffer, bool) and not remote_buffer:
                close_socket_pass_exc(remote_socket)
                close_socket_pass_exc(self._cli_socket)
                self._logger.print_conn("[*] Remote %s:%d is disconnected\n" % self.__remote_address)
                return

            # if receive data from remote
            if len(remote_buffer):
                fail = 0

                # change response with handler and log it
                remote_buffer = resp_handle(remote_buffer)
                self._logger.log_buffer(self.__remote_address, remote_buffer, False)

                # send response to client
                self._cli_socket.sendall(remote_buffer)

            # check len of buffers
            if not (len(local_buffer) or len(remote_buffer)):
                fail += 1
                # if fails too many times close connections
                if fail >= self._max_fails:
                    self._logger.print_err("[!!] %s fails to many times!!! Close connections\n" % self.name)
                    close_socket_pass_exc(remote_socket)
                    close_socket_pass_exc(self._cli_socket)
                    return
