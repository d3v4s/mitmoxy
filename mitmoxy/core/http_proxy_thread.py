from .proxy_thread import ProxyThread
from ..utils.functions import bypass_error
from ..utils.socket import close_socket_pass_exc
from traceback import format_exc


class HttpProxyThread(ProxyThread):
    def __init__(self, cli_socket, cli_address, server_socket):
        ProxyThread.__init__(self, cli_socket, cli_address, server_socket)

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
                    out = "[!!] Client %s:%d is disconnected\n" % self._cli_address
                    out += '############ END CONNECTION ############\n'
                    self._logger.print(out)
                    return

                if len(local_buffer):
                    self._logger.log_buffer(self._cli_address, local_buffer, True)

                    # change request with handler
                    local_buffer = self.__req_handler(local_buffer)

                    # get host and port remote and create socket
                    new_addr = self._get_remote_address(local_buffer)
                    # if not (remote_address[0] == new_addr[0] and remote_address[1] == new_addr[1]) \
                    #         or remote_address is None:
                    if remote_address is None:
                        # close old socket for new connection
                        close_socket_pass_exc(remote_socket)
                        remote_address = new_addr
                        remote_socket = self._get_remote_socket(remote_address)

                # send data at remote host
                if remote_socket is not None:
                    # logger.print('[=>] Sent request to %s:%d' % (remote_host, remote_port))
                    remote_socket.sendall(local_buffer)

                    # receive response from remote
                    remote_buffer = self._receive_from(remote_socket, remote_address)

                    # if remote is disconnect close connection and return
                    if isinstance(remote_buffer, bool) and not remote_buffer:
                        close_socket_pass_exc(self._cli_socket)
                        close_socket_pass_exc(remote_socket)
                        out = "[!!] Remote %s:%d is disconnected\n" % remote_address[:2]
                        out += '############ END CONNECTION ############\n'
                        self._logger.print(out)
                        return

                    # if have data from remote log it and send response to client
                    if len(remote_buffer):
                        self._logger.log_buffer(remote_address, remote_buffer, False)

                        # change response with handler
                        remote_buffer = self.__resp_handler(remote_buffer)

                        # send response to client
                        self._logger.print('[<=] Send response to %s:%d' % self._cli_address)
                        self._cli_socket.sendall(remote_buffer)

                # if there are no other data close the connections
                if not (len(remote_buffer) or len(local_buffer)):
                    close_socket_pass_exc(self._cli_socket)
                    close_socket_pass_exc(remote_socket)
                    out = '[*] No more data. Closing connection with client %s:%d\n' % self._cli_address
                    out += '############ END CONNECTION ############\n'
                    self._logger.print(out)
                    break
        except Exception as e:
            close_socket_pass_exc(self._cli_socket)
            out = '' if bypass_error(e) else format_exc()
            out += "[!!] Caught a exception on proxy: %s" % str(e)
            self._logger.print_err(out)
            return
