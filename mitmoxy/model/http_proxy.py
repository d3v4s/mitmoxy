import socket

from mitmoxy.controllers.logger import Logger
from mitmoxy.model.proxy import Proxy


class HttpProxy(Proxy):

    def __init__(self, logger: Logger, conf_server):
        super(HttpProxy, self).__init__(logger, conf_server)
        self._address = self._conf_server['http-address']
        self._port = self._conf_server['http-port']

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
    # PROTECTED METHODS
    #####################################

    # method to get server name
    def _get_server_name(self) -> str:
        return 'HTTP Proxy'

    # function to manage connection with client
    def _proxy_handler(self, cli_socket: socket.socket):
        # get host and port of client
        cli_host, cli_port = cli_socket.getpeername()
        # init logger and vars
        # logger = Logger(self._conf_log)
        remote_socket = None
        remote_address = None
        remote_buffer = ''
        # loop to route requests and responses
        # between client and remote host
        while 1:
            # receive data from client
            local_buffer = self._receive_from(cli_socket)

            # if client is disconnect close connection and return
            if isinstance(local_buffer, bool) and not local_buffer:
                self._close_socket_pass_exc(cli_socket)
                self._close_socket_pass_exc(remote_socket)
                out = "[!!] Client %s:%d is disconnected\n" % (cli_host, cli_port)
                out += '############ END CONNECTION ############\n'
                self._logger.print(out)
                return

            if len(local_buffer):
                self._logger.log_buffer((cli_host, cli_port), local_buffer, True)

                # change request with handler
                local_buffer = self.__req_handler(local_buffer)

                # get host and port remote and create socket
                new_addr = self._get_remote_address(local_buffer)
                if not (remote_address[0] == new_addr[0] and remote_address[1] == new_addr[1])\
                        or remote_address is None:
                    # close old socket for new connection
                    self._close_socket_pass_exc(remote_socket)
                    remote_address = new_addr
                    remote_socket = self._get_remote_socket(remote_address)

            # send data at remote host
            if remote_socket is not None:
                # logger.print('[=>] Sent request to %s:%d' % (remote_host, remote_port))
                remote_socket.sendall(local_buffer)

                # receive response from remote
                remote_buffer = self._receive_from(remote_socket)

                # if remote is disconnect close connection and return
                if isinstance(remote_buffer, bool) and not remote_buffer:
                    self._close_socket_pass_exc(cli_socket)
                    self._close_socket_pass_exc(remote_socket)
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
                    self._logger.print('[<=] Send response to %s:%d' % (cli_host, cli_port))
                    cli_socket.sendall(remote_buffer)

            # if there are no other data close the connections
            if not (len(remote_buffer) or len(local_buffer)):
                self._close_socket_pass_exc(cli_socket)
                self._close_socket_pass_exc(remote_socket)
                out = '[*] No more data. Closing connection with client %s:%d\n' % (cli_host, cli_port)
                out += '############ END CONNECTION ############\n'
                self._logger.print(out)
                break
