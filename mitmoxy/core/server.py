import socket
import traceback

from abc import abstractmethod, ABC

from mitmoxy.controllers.logger import Logger


# function to decode the buffer
def decode_buffer(buffer):
    enc_type = ['utf-8', 'utf-16', 'ascii', 'ISO-8859-1']
    for enc in enc_type:
        try:
            buffer = buffer.decode(encoding=enc, errors='strict')
            return buffer
        except UnicodeDecodeError:
            continue
    raise Exception('[!!] Encode buffer failed!!!')


class Server(ABC):
    _server_socket: socket.socket = None
    _conf_server = None
    _conf_log = None
    _address = None
    _port = None
    _timeout = 0.5

    def __init__(self, conf_server, conf_log):
        self._conf_server = conf_server
        self._conf_log = conf_log

    #####################################
    # STATIC PROTECTED METHODS
    #####################################

    # function to check if bypass the error
    @staticmethod
    def _bypass_error(e: Exception):
        # no bypass error if not have arguments
        if len(e.args) < 1:
            return False

        # bypass timeout exceptions
        if e.args[0] == 'The read operation timed out' or e.args[0] == 'timed out':
            return True

        # bypass ssl exceptions
        if len(e.args) >= 2 and (e.args[1] == '[SSL: HTTPS_PROXY_REQUEST] https proxy request (_ssl.c:1076)' or
                                 e.args[1] == '[SSL: TLSV1_ALERT_UNKNOWN_CA] tlsv1 alert unknown ca (_ssl.c:1076)' or
                                 e.args[1] == '[SSL: HTTP_REQUEST] http request (_ssl.c:1076)'):
            return True

        return False

    # function to send 404 code and close socket
    @staticmethod
    def _send_400_and_close(sock: socket.socket):
        try:
            sock.sendall(b'HTTP/1.1 400\r\n\r\n')
            sock.close()
        except Exception:
            pass

    @staticmethod
    def _create_bind_socket(address: tuple):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(address)
        return sock

    #####################################
    # PROTECTED METHODS
    #####################################

    # function to manage the restart of server
    # exit if restart is disable, else pass and restart the server
    def _exit_or_restart(self, exit_code):
        if not self._conf_server['restart-server']:
            exit(exit_code)

    # method that generate and return the socket
    def _get_socket(self) -> socket.socket:
        sock = self._create_bind_socket((self._address, self._port))
        # if self._conf_server['ssl-socks']:
        #     context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        #     context.load_cert_chain(certfile=self._conf_server['cert-file'], keyfile=self._conf_server['key-file'])
        #     return context.wrap_socket(sock, server_side=True)
        return sock

    # function to read buffer from connection
    def _receive_from(self, conn: socket.socket, chunk_size=2048) -> bytes:
        buffer = b''
        # set timeout
        conn.settimeout(self._timeout)
        logger = Logger(self._conf_log)

        # read from socket buffer
        try:
            while 1:
                data = conn.recv(chunk_size)
                if not data:
                    break
                buffer += data
        except KeyboardInterrupt:
            logger.print("[!!] Keyboard interrupt. Exit...")
            try:
                conn.close()
            except Exception:
                pass
            self._server_socket.close()
            exit()
        except Exception as e:
            # buffer = b''
            out = ''
            if not self._bypass_error(e):
                out += traceback.format_exc()
            peer = conn.getpeername()
            out += '[!!] Fail receive data from %s:%d\n' % peer
            out += '[!!] Caught an exception: %s\n' % str(e)
            logger.print(out)
        return buffer

    #####################################
    # ABSTRACT METHODS
    #####################################

    # # function to manage connection with client
    # @abstractmethod
    # def _server_handler(self, cli_socket: socket.socket):
    #     pass

    @abstractmethod
    def _get_server_name(self):
        pass

    #####################################
    # PUBLIC METHODS
    #####################################

    # method to start loop server
    @abstractmethod
    def start_server(self):
        pass
        # logger = Logger(self._conf_log)
        # cli_socket = None
        # while 1:
        #     # create socket and start listen to it
        #     try:
        #         self._server_socket = self._get_socket()
        #     except Exception as e:
        #         out = traceback.format_exc()
        #         out += '[!!] %s fail to listen on %s:%d\n' % (self._get_server_name(), self._address, self._port)
        #         out += '[!!] Caught an exception %s\n' % str(e)
        #         logger.print_err(out)
        #         try:
        #             self._server_socket.close()
        #         except Exception:
        #             pass
        #         self._exit_or_restart(self._server_socket)
        #         logger.print('[*] Restart %s\n' % self._get_server_name())
        #         continue
        #
        #     # start listen and loop server
        #     logger.print('[*] Start %s listen on %s:%d\n' % (self._get_server_name(), self._address, self._port))
        #     self._server_socket.listen()
        #     while 1:
        #         try:
        #             cli_socket, (cli_address, cli_port) = self._server_socket.accept()
        #             # print connection info
        #             out = '############ START CONNECTION ############\n'
        #             out += '[=>] Incoming connection from %s:%d' % (cli_address, cli_port)
        #             logger.print(out)
        #
        #             # start thread to communicate with client and remote host
        #             proxy_thread = threading.Thread(target=self._server_handler, args=[cli_socket])
        #             proxy_thread.start()
        #         except KeyboardInterrupt:
        #             logger.print_err("[!!] Keyboard interrupt. Exit...")
        #             self._server_socket.close()
        #             exit()
        #         except Exception as e:
        #             out = ''
        #             if not self._bypass_error(e):
        #                 out += traceback.format_exc()
        #                 out += '\n'
        #             out += '[!!] Caught an exception on Mitmoxy: %s\n' % str(e)
        #             logger.print_err(out)
        #             try:
        #                 self._send_400_and_close(cli_socket)
        #             except Exception:
        #                 pass
        #             self._server_socket.close()
        #             self._exit_or_restart(-1)
        #             logger.print('[*] Restart %s' % self._get_server_name())
        #             break
