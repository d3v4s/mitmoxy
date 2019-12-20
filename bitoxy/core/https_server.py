import socket
import ssl

from bitoxy.controllers.logger import Logger
from bitoxy.core.server import Server
from bitoxy.core import server


class HttpsServer(Server):
    __max_fails = 50

    def __init__(self, conf_server, conf_log):
        super(HttpsServer, self).__init__(conf_server, conf_log)
        self._address = self._conf_server['https-address']
        self._port = self._conf_server['https-port']

    #####################################
    # PRIVATE METHODS
    #####################################

    # handle to change the request buffer
    def __req_handler(self, buffer):
        return buffer

    # handle to change the response buffer
    def __resp_handler(self, buffer):
        return buffer

    #####################################
    # PROTECTED METHODS
    #####################################

    # method to get server name
    def _get_server_name(self):
        return 'HTTPS proxy'

    # method to manage the negotiation with client
    def _client_negotiation(self, cli_socket: socket.socket):
        cli_address = cli_socket.getpeername()
        logger = Logger(self._conf_log)
        logger.print('############ START CLIENT NEGOTIATION ############')
        while 1:
            # receive data from client
            local_buffer = self._receive_from(cli_socket)
            if len(local_buffer):
                # log request
                logger.log_buffer(cli_address, local_buffer, True)

                # if request type isn't CONNECT send bad request code
                req_type = server.decode_buffer(local_buffer)[:7]
                if req_type != 'CONNECT':
                    cli_socket.sendall(b'HTTP/1.1 400\r\n\r\n')
                    continue

                # change request with handler
                local_buffer = self.__req_handler(local_buffer)

                # get host and port remote and create a socket
                remote_host, remote_port = self._get_remote_address(local_buffer)
                remote_socket = self._get_remote_socket((remote_host, remote_port))

                # send negotiation confirm
                conf_buff = b'HTTP/1.1 200 OK\r\n\r\n'
                logger.print('[*] Send confirm negotiation')
                logger.log_buffer((self._address, self._port), conf_buff, False)
                cli_socket.sendall(conf_buff)

                logger.print('############ END CLIENT NEGOTIATION ############\n')
                return remote_socket, (remote_host, remote_port)

    # function to check if client require to close the connection
    def __close_connection(self, buffer, remote_address):
        logger = Logger(self._conf_log)
        try:
            buffer = server.decode_buffer(buffer)
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
            logger.print('[*] Caught a exception while checking of close require: %s\n' % str(e))
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
                    try:
                        cli_socket.close()
                    except Exception:
                        pass
                    try:
                        remote_socket.close()
                    except Exception:
                        pass

                    out = '[*] Exit require from client. Closing connections %s:%d\n' % (cli_host, cli_port)
                    out += '############ END CONNECTION ############\n'
                    logger.print(out)
                    break

                # log buffer
                logger.log_buffer((cli_host, cli_port), local_buffer, True)

                # change request with handler
                local_buffer = self.__req_handler(local_buffer)

                # send data at remote host
                logger.print('[=>] Sent request to %s:%d' % (remote_host, remote_port))
                remote_socket.sendall(local_buffer)

            # receive data from remote
            remote_buffer = self._receive_from(remote_socket)
            if len(remote_buffer):
                fail = 0
                # log buffer
                logger.log_buffer(remote_address, remote_buffer, False)
                # change response with handler
                remote_buffer = self.__resp_handler(remote_buffer)
                # send response to client
                logger.print('[<=] Send response to %s:%d' % (cli_host, cli_port))
                cli_socket.sendall(remote_buffer)

            # check len of buffers
            if len(local_buffer) == 0 and len(remote_buffer) == 0:
                fail += 1
                # if fails too many times close connections
                if fail >= self.__max_fails:
                    logger.print("[!!] Fails to many times close connection with %s:%d client\n" % (cli_host, cli_port))
                    self._send_400_and_close(cli_socket)
                    try:
                        remote_socket.close()
                    except Exception:
                        pass
                    break

    # method that generate and return the socket
    def _create_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        sock.bind((self._address, self._port))
        return ssl.wrap_socket(
            sock,
            server_side=True,
            certfile=self._conf_server['cert-file'],
            keyfile=self._conf_server['key-file']
        )
