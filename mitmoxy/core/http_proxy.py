import socket

from mitmoxy.controllers.logger import Logger
from mitmoxy.core.proxy import Proxy


class HttpProxy(Proxy):

    def __init__(self, conf_server, conf_log):
        super(HttpProxy, self).__init__(conf_server, conf_log)
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
    def _get_server_name(self):
        return 'HTTP proxy'

    # function to manage connection with client
    def _proxy_handler(self, cli_socket: socket.socket):
        # get host and port of client
        cli_host, cli_port = cli_socket.getpeername()
        # init logger and vars
        logger = Logger(self._conf_log)
        remote_socket = None
        remote_host = None
        remote_port = None
        remote_buffer = ''
        # loop to route requests and responses
        # between client and remote host
        while 1:
            # receive data from client
            local_buffer = self._receive_from(cli_socket)
            if len(local_buffer):
                logger.log_buffer((cli_host, cli_port), local_buffer, True)

                # change request with handler
                local_buffer = self.__req_handler(local_buffer)

                # get host and port remote
                remote_host, remote_port = self._get_remote_address(local_buffer)

            # send data at remote host
            if remote_host is not None:
                logger.print('[=>] Sent request to %s:%d' % (remote_host, remote_port))
                remote_socket = self._get_remote_socket((remote_host, remote_port))
                remote_socket.sendall(local_buffer)

                # receive response from remote
                remote_buffer = self._receive_from(remote_socket)
                if len(remote_buffer):
                    logger.log_buffer((remote_host, remote_port), remote_buffer, False)

                    # change response with handler
                    remote_buffer = self.__resp_handler(remote_buffer)

                    # send response to client
                    logger.print('[<=] Send response to %s:%d' % (cli_host, cli_port))
                    cli_socket.sendall(remote_buffer)

            # if there are no other data close the connections
            if not (len(remote_buffer) or len(local_buffer)):
                try:
                    cli_socket.close()
                except Exception:
                    pass
                try:
                    remote_socket.close()
                except Exception:
                    pass
                out = '[*] No more data. Closing connection with client %s:%d\n' % (cli_host, cli_port)
                out += '############ END CONNECTION ############\n'
                logger.print(out)
                break
