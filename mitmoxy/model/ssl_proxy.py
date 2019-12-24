import socket
from time import sleep

from .fake_ssl_server import FakeSslServer
from ..controllers.fake_ssl_factory import FakeSslFactory
from ..controllers.logger import Logger
from .proxy import Proxy, decode_buffer


class SslProxy(Proxy):
    __fake_ssl_factory = None

    def __init__(self, logger: Logger, conf_server, fake_ssl_factory: FakeSslFactory):
        super(SslProxy, self).__init__(logger, conf_server)
        self._address = self._conf_server['ssl-address']
        self._port = self._conf_server['ssl-port']
        self.__fake_ssl_factory = fake_ssl_factory
        # self.__fake_server_address = (self._conf_server['fake-server-address'], self._conf_server['fake-server-port'])
        # self.__tls = TLS(conf_server, self._max_fails)

    #####################################
    # PRIVATE STATIC METHODS
    #####################################

    # function to wait the ready of fake ssl server
    @staticmethod
    def __wait_fake_ssl(fake_ssl_server: FakeSslServer):
        fail = 0
        while not fake_ssl_server.ready:
            fail += 1
            if fail > 100:
                raise Exception("[!!] Wait fake SSL server fail too many time")
            sleep(0.15)

    #####################################
    # PRIVATE METHODS
    #####################################

    # handler to change a request on client negotiation
    def __req_handler(self, buffer: bytes) -> bytes:
        return buffer

    # handler to change a response
    def __resp_handler(self, buffer: bytes) -> bytes:
        return buffer

    # method to start the ssl fake server
    def __start_fake_ssl(self):
        pass
        # fake_ssl_server = FakeSslServer(self._conf_server, self._conf_log)
        # fake_ssl_thread = Thread(target=fake_ssl_server.start_server)
        # fake_ssl_thread.start()

    # function to check if client require to close the connection
    def __close_connection(self, buffer, remote_address: tuple):
        # logger = Logger(self._conf_log)
        try:
            buffer = decode_buffer(buffer)
            buff_host, buff_port = self._get_remote_address(buffer)
            if buffer[:7] == 'CONNECT' and buff_host == remote_address[0] and buff_port == remote_address[1]:
                pos_conn = buffer.find('\nConnection: ')
                if pos_conn < 0:
                    return False
                pos_conn += 12
                val_conn = buffer[pos_conn:pos_conn + 5]
                val_conn = val_conn.lower()
                print(val_conn)
                return val_conn == 'close'
        except Exception as e:
            self._logger.print_err('[*] Caught a exception while checking of close require: %s\n' % str(e))
            return False

    #####################################
    # PROTECTED METHODS
    #####################################

    # # override method that generate and return the socket
    # def _get_socket(self):
    #     self.__start_fake_ssl()
    #     return super(SslProxy, self)._get_socket()

    # method to get server name
    def _get_server_name(self) -> str:
        return 'SSL Proxy'

    # method to manage the negotiation with client
    def _client_negotiation(self, cli_socket: socket.socket):
        cli_address = cli_socket.getpeername()
        # logger = Logger(self._conf_log)
        self._logger.print('############ START CLIENT NEGOTIATION ############')
        # fake_server_socket = None  # self._get_remote_socket(self.__fake_server_address)
        fail = 0
        while 1:
            # receive data from client
            local_buffer = self._receive_from(cli_socket, 32)

            # if client is disconnect close connection and return
            if isinstance(local_buffer, bool) and not local_buffer:
                try:
                    cli_socket.close()
                except Exception:
                    pass
                out = "[!!] Client %s:%d is disconnected\n" % cli_address
                out += '############ END CONNECTION ############\n'
                self._logger.print(out)
                raise Exception("Client disconnected")

            if len(local_buffer):
                # log request
                # self._logger.log_buffer(cli_address, local_buffer, True)

                # if request type isn't CONNECT send bad request code
                if decode_buffer(local_buffer)[:7] != 'CONNECT':
                    cli_socket.sendall(b'HTTP/1.1 400 Bad Request\r\n\r\n')
                    raise Exception("Error while negotiation with the client. Bad request from client!!!")

                self._logger.print('[*] CONNECT request from %s:%d' % cli_address)
                # change request with handler
                local_buffer = self.__req_handler(local_buffer)

                # get host and port remote
                remote_address = self._get_remote_address(local_buffer)
                try:
                    remote_socket = self._get_remote_socket(remote_address, True)
                    remote_socket.close()
                except Exception as e:
                    self._send_404_and_close(cli_socket)
                    self._logger.print_err("[!!] Error while get remote socket: %s" % str(e))
                    return False
                # self.__send_address_at_fake(fake_server_socket, remote_address[0], remote_address[1])

                # # close socket if is init
                # if remote_socket is not None:
                #     remote_socket.close()

                fake_ssl_server = self.__fake_ssl_factory.get_fake_ssl(remote_address)

                # create a socket with fake ssl server
                # remote_socket = self._get_remote_socket(remote_address)
                # send negotiation confirm
                # fake_server_socket = self._get_remote_socket(self.__fake_server_address)
                conf_buff = b'HTTP/1.1 200 Connection established\r\n\r\n'
                self._logger.print('[*] Send confirm negotiation at %s:%d' % cli_address)
                # self._logger.log_buffer((self._address, self._port), conf_buff, False)
                cli_socket.sendall(conf_buff)

                self._logger.print('############ END CLIENT NEGOTIATION ############\n')
                return fake_ssl_server   # , remote_address
            # increment fails and check max
            fail += 1
            if fail >= self._max_fails:
                raise Exception("Error while negotiation with the client. Too many fails!!!")

    # function to manage connection with client
    def _proxy_handler(self, cli_socket: socket.socket):
        cli_host, cli_port = cli_socket.getpeername()

        # negotiation with client
        fake_ssl_server = self._client_negotiation(cli_socket)
        # if negotiation failed return
        if isinstance(fake_ssl_server, bool) and not fake_ssl_server:
            return

        # count fail
        fail = 0

        self.__wait_fake_ssl(fake_ssl_server)
        fake_ssl_address = fake_ssl_server.get_address()
        fake_ssl_socket = self._get_remote_socket(fake_ssl_address)

        # loop to route requests and responses
        # between client and remote host
        while 1:
            # receive data from client
            local_buffer = self._receive_from(cli_socket)

            # if client is disconnect close connection and return
            if isinstance(local_buffer, bool) and not local_buffer:
                self._close_socket_pass_exc(cli_socket)
                self._close_socket_pass_exc(fake_ssl_socket)
                out = "[!!] Client %s:%d is disconnected\n" % (cli_host, cli_port)
                out += '############ END CONNECTION ############\n'
                self._logger.print(out)
                return

            if len(local_buffer):
                fail = 0
                # check if client require to exit
                # if self.__close_connection(local_buffer, remote_address):
                #     # close client and remote connections
                #     try:
                #         cli_socket.close()
                #     except Exception:
                #         pass
                #     try:
                #         fake_ssl_server_socket.close()
                #     except Exception:
                #         pass
                #
                #     # print
                #     out = '[*] Exit require from client. Closing connections: Client -> %s:%d  --  Remote -> %s:%d\n'\
                #           % (cli_host, cli_port, remote_host, remote_port)
                #     out += '############ END CONNECTION ############\n'
                #     logger.print(out)
                #     break

                # change reques with handler and log it
                # local_buffer = self.__req_handler(local_buffer)
                # self._logger.log_buffer((cli_host, cli_port), local_buffer, True)
                # send data at remote host
                fake_ssl_socket.sendall(local_buffer)

            # receive response from remote
            remote_buffer = self._receive_from(fake_ssl_socket)

            # if remote is disconnect close connection and return
            if isinstance(remote_buffer, bool) and not remote_buffer:
                self._close_socket_pass_exc(cli_socket)
                self._close_socket_pass_exc(fake_ssl_socket)
                out = "[!!] Fake server is disconnected\n"
                out += '############ END CONNECTION ############\n'
                self._logger.print(out)
                return

            if len(remote_buffer):
                fail = 0

                # # change response with handler and log it
                # remote_buffer = self.__resp_handler(remote_buffer)
                # logger.log_buffer((remote_host, remote_port), remote_buffer, False)
                # logger.print('[<=] Send response to %s:%d' % (cli_host, cli_port))

                # send response to client
                cli_socket.sendall(remote_buffer)

            # check len of buffers
            if not (len(local_buffer) or len(remote_buffer)):
                fail += 1
                # if fails too many times close connections
                if fail >= self._max_fails:
                    out = "[!!] Fails to many times!!! Close connection with %s:%d client\n" % (cli_host, cli_port)
                    out += '############ END CONNECTION ############\n'
                    self._logger.print(out)
                    self._close_socket_pass_exc(cli_socket)
                    self._close_socket_pass_exc(fake_ssl_socket)
                    fake_ssl_server.shutdown()
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
