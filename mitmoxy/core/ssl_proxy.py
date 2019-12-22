import socket
# import traceback
# import ssl
# from http.server import HTTPServer, BaseHTTPRequestHandler, SimpleHTTPRequestHandler
# from ssl import Purpose
# from threading import Thread

from mitmoxy.controllers.logger import Logger
# from .server import
from .proxy import Proxy, decode_buffer


class SslProxy(Proxy):
    __max_fails = 50
    __fake_ssl_address = None

    def __init__(self, conf_server, conf_log):
        super(SslProxy, self).__init__(conf_server, conf_log)
        self._address = self._conf_server['ssl-address']
        self._port = self._conf_server['ssl-port']
        # self.__fake_ssl_address = (self._conf_server['fake-ssl-address'], self._conf_server['fake-ssl-port'])

    #####################################
    # PRIVATE METHODS
    #####################################

    # handler to change a request
    def __req_handler(self, buffer: bytes) -> bytes:
        return buffer

    # handler to change a response
    def __resp_handler(self, buffer: bytes) -> bytes:
        return buffer

    # method to start fake ssl server
    # def __start_fake_ssl(self):
        # fake_ssl_server = FakeSslServer(self._conf_server, self._conf_log)
        # fake_ssl_thread = Thread(target=fake_ssl_server.start_server)
        # fake_ssl_thread.start()

    #####################################
    # PROTECTED METHODS
    #####################################

    # # override method that generate and return the socket
    # def _get_socket(self):
    #     self.__start_fake_ssl()
    #     return super(SslProxy, self)._get_socket()

    # method to get server name
    def _get_server_name(self):
        return 'SSL proxy'

    # method to manage the negotiation with client
    def _client_negotiation(self, cli_socket: socket.socket) -> tuple:
        cli_address = cli_socket.getpeername()
        logger = Logger(self._conf_log)
        logger.print('############ START CLIENT NEGOTIATION ############')
        fail = 0
        while 1:
            # receive data from client
            local_buffer = self._receive_from(cli_socket, 24)
            if len(local_buffer):
                # log request
                logger.log_buffer(cli_address, local_buffer, True)

                # if request type isn't CONNECT send bad request code
                req_type = decode_buffer(local_buffer)[:7]
                if req_type != 'CONNECT':
                    cli_socket.sendall(b'HTTP/1.1 400 Bad Request\r\n\r\n')
                    raise Exception("Error while negotiation with the client. Bad request from client!!!")

                # change request with handler
                local_buffer = self.__req_handler(local_buffer)

                # get host and port remote and create a socket with fake ssl server
                remote_address = self._get_remote_address(local_buffer)
                remote_socket = self._get_remote_socket(remote_address, True)
                # send negotiation confirm
                conf_buff = b'HTTP/1.1 200 Connection established\r\n\r\n'
                logger.print('[*] Send confirm negotiation at %s:%d' % remote_address)
                logger.log_buffer((self._address, self._port), conf_buff, False)
                cli_socket.sendall(conf_buff)

                logger.print('############ END CLIENT NEGOTIATION ############\n')
                return remote_socket, remote_address
            # increment fails and check max
            fail += 1
            if fail >= self.__max_fails:
                raise Exception("Error while negotiation with the client. Too many fails!!!")

    # function to check if client require to close the connection
    def __close_connection(self, buffer, remote_address: tuple):
        logger = Logger(self._conf_log)
        try:
            buffer = decode_buffer(buffer)
            buff_host, buff_port = self._get_remote_address(buffer)
            if buffer[:7] == 'CONNECT' and buff_host == remote_address[0] and buff_port == remote_address[1]:
                pos_conn = buffer.find('\nConnection: ')
                if pos_conn < 0:
                    return False
                pos_conn += 12
                val_conn = buffer[pos_conn:pos_conn+5]
                val_conn = val_conn.lower()
                print(val_conn)
                return val_conn == 'close'
        except Exception as e:
            logger.print_err('[*] Caught a exception while checking of close require: %s\n' % str(e))
            return False

    # function to manage connection with client
    def _proxy_handler(self, cli_socket: socket.socket):
        cli_host, cli_port = cli_socket.getpeername()
        # negotiation with client
        remote_socket, remote_address = self._client_negotiation(cli_socket)
        remote_host, remote_port = remote_address
        # init the logger
        logger = Logger(self._conf_log)
        # count fail
        fail = 0
        # loop to route requests and responses
        # between client and remote host
        while 1:
            # receive data from client
            local_buffer = self._receive_from(cli_socket)
            if len(local_buffer):
                fail = 0
                # check if client require to exit
                if self.__close_connection(local_buffer, remote_address):
                    # close client and remote connections
                    try:
                        cli_socket.close()
                    except Exception:
                        pass
                    try:
                        remote_socket.close()
                    except Exception:
                        pass

                    # print
                    out = '[*] Exit require from client. Closing connections: Client -> %s:%d  --  Remote -> %s:%d\n'\
                          % (cli_host, cli_port, remote_host, remote_port)
                    out += '############ END CONNECTION ############\n'
                    logger.print(out)
                    break

                # change reques with handler and log it
                local_buffer = self.__req_handler(local_buffer)
                logger.log_buffer((cli_host, cli_port), local_buffer, True)

                # send data at remote host
                remote_socket.sendall(local_buffer)

            # receive response from remote
            remote_buffer = self._receive_from(remote_socket)
            if len(remote_buffer):
                fail = 0

                # change response with handler and log it
                remote_buffer = self.__resp_handler(remote_buffer)
                logger.log_buffer((remote_host, remote_port), remote_buffer, False)
                # logger.print('[<=] Send response to %s:%d' % (cli_host, cli_port))

                # send response to client
                cli_socket.sendall(remote_buffer)

            # check len of buffers
            if not (len(local_buffer) or len(remote_buffer)):
                fail += 1
                # if fails too many times close connections
                if fail >= self.__max_fails:
                    out = "[!!] Fails to many times!!! Close connection with %s:%d client\n" % (cli_host, cli_port)
                    out += '############ END CONNECTION ############\n'
                    logger.print(out)
                    self._send_400_and_close(cli_socket)
                    try:
                        remote_socket.close()
                    except Exception:
                        pass
                    break

                # send data at remote host
                # logger.print('[=>] Sent request to %s:%d' % re)
                # remote_socket.sendall(local_buffer)
                # log buffer
                # logger.log_buffer((cli_host, cli_port), local_buffer, True)

                # change request with handler
                # local_buffer = self.__req_handler(local_buffer)

            # receive data from remote
            # remote_buffer = self._receive_from(remote_socket)
            # if len(remote_buffer):
            #     fail = 0
            #     # log buffer
            #     # logger.log_buffer(remote_address, remote_buffer, False)
            #     # change response with handler
            #     # remote_buffer = self.__resp_handler(remote_buffer)
            #     # send response to client
            #     # logger.print('[<=] Send response to %s:%d' % (cli_host, cli_port))
            #     cli_socket.sendall(remote_buffer)
            #
