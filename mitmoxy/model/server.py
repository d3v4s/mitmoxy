import socket
import ssl
import traceback
from _ctypes import pointer

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
    _logger: Logger = None
    _conf_server = None
    _address = None
    _port = None
    _timeout = 0.1
    _max_fails = 10

    def __init__(self, conf_log, conf_server=None):
        self._conf_server = conf_server
        self._logger = Logger(conf_log)

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

        # bypass ssl exceptions and endpoint not connected
        if len(e.args) >= 2 and (e.args[1] == '[SSL: SSLV3_ALERT_BAD_CERTIFICATE] sslv3 alert bad certificate '
                                              '(_ssl.c:1076)' or
                                 e.args[1] == '[SSL: TLSV1_ALERT_UNKNOWN_CA] tlsv1 alert unknown ca (_ssl.c:1076)' or
                                 e.args[1] == '[SSL: HTTPS_PROXY_REQUEST] https proxy request (_ssl.c:1076)' or
                                 e.args[1] == '[SSL: HTTP_REQUEST] http request (_ssl.c:1076)' or
                                 e.args[1] == 'Transport endpoint is not connected'):
            return True

        return False

    # function to send 404 code and close socket
    @staticmethod
    def _send_400_and_close(sock: socket.socket):
        try:
            sock.sendall(b'HTTP/1.1 400 Bad request\r\n\r\n')
            sock.close()
        except Exception:
            pass

    # function to send 404 code and close socket
    @staticmethod
    def _send_404_and_close(sock: socket.socket):
        try:
            sock.sendall(b'HTTP/1.1 404 Not found\r\n\r\n')
            sock.close()
        except Exception:
            pass

    # function to close the socket and pass the exception
    @staticmethod
    def _close_socket_pass_exc(sock):
        try:
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
    def _get_socket(self, ssl_wrap=False, cert_file=None, key_file=None):
        sock = self._create_bind_socket((self._address, self._port))
        if ssl_wrap:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(certfile=cert_file, keyfile=key_file)
            return context.wrap_socket(sock, server_side=True)
        return sock

    # function to read buffer from connection
    def _receive_from(self, conn: socket.socket, chunk_size=2048):
        buffer = b''
        # set timeout
        conn.settimeout(self._timeout)
        # logger = Logger(self._conf_log)
        # read from socket buffer
        try:
            peer = conn.getpeername()[:2]
            self._logger.print("[*] Start receive from %s:%d" % peer)
            while 1:
                data = conn.recv(chunk_size)
                if not data:
                    break
                buffer += data
        except KeyboardInterrupt:
            self._logger.print("[!!] Keyboard interrupt. Exit...")
            self._close_socket_pass_exc(conn)
            self._close_socket_pass_exc(self._server_socket)
            exit()
        except Exception as e:
            # buffer = b''
            out = ''
            if not self._bypass_error(e):
                out += traceback.format_exc()
            out += '[!!] Fail receive data'
            try:
                peer = conn.getpeername()[:2]
                out += 'from %s:%d\n' % peer
            except Exception:
                out += '\n'

            out += '[!!] Caught an exception: %s\n' % str(e)
            self._logger.print(out)
            # if endpoint is disconnected return false
            if len(e.args) >= 2 and e.args[1] == 'Transport endpoint is not connected':
                return False
        return buffer

    #####################################
    # ABSTRACT METHODS
    #####################################

    # # function to manage connection with client
    # @abstractmethod
    # def _server_handler(self, cli_socket: socket.socket):
    #     pass

    @abstractmethod
    def _get_server_name(self) -> str:
        pass

    #####################################
    # PUBLIC METHODS
    #####################################

    # method to start loop server
    @abstractmethod
    def start_server(self):
        pass
