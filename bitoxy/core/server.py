import ssl
import socket
import threading
import traceback

from abc import abstractmethod, ABC
from bitoxy.controllers.logger import Logger


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
    _server_socket = None
    _conf_server = None
    _conf_log = None
    _address = None
    _port = None
    _timeout = 0.1

    def __init__(self, conf_server, conf_log):
        self._conf_server = conf_server
        self._conf_log = conf_log

    #####################################
    # PRIVATE METHODS
    #####################################

    # function to get remote socket
    @staticmethod
    def _get_remote_socket(address: tuple):
        host, port = address
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if port == '443':
            return ssl.wrap_socket(remote_socket)
        remote_socket.connect(address)
        return remote_socket

    # function to get remote address and port
    @staticmethod
    def _get_remote_address(request):
        # convert binary to string
        request = decode_buffer(request) if isinstance(request, bytes) else request
        # get url
        url = request.split('\n')[0].split(' ')[1]
        # find pos of ://
        http_pos = url.find("://")
        # get the rest of url
        temp = url if http_pos == -1 else url[(http_pos + 3):]

        # find the port position
        port_pos = temp.find(":")

        # find end of address
        address_pos = temp.find("/")
        if address_pos == -1:
            address_pos = len(temp)

        if port_pos == -1 or address_pos < port_pos:
            # default port
            port = 80
            address = temp[:address_pos]
        else:
            # specific port
            port = int((temp[(port_pos + 1):])[:address_pos - port_pos - 1])
            address = temp[:port_pos]
        return address, port

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

    # function to manage the restart of server
    # exit if restart is disable, else pass and restart the server
    def _exit_or_restart(self, exit_code):
        if not self._conf_server['restart-server']:
            exit(exit_code)

    # function to read buffer from connection
    def _receive_from(self, conn: socket.socket):
        buffer = b''
        # set timeout
        conn.settimeout(self._timeout)
        logger = Logger(self._conf_log)

        # read from socket buffer
        try:
            while 1:
                data = conn.recv(2048)
                if not data:
                    break
                buffer += data
        except KeyboardInterrupt:
            logger.out("[!!] Keyboard interrupt. Exit...")
            try:
                conn.close()
            except Exception:
                pass
            self._server_socket.close()
            exit()
        except Exception as e:
            out = ''
            if not self._bypass_error(e):
                out += traceback.format_exc()
            peer = conn.getpeername()
            out += '[!!] Fail receive data from %s:%d\n' % peer
            out += '[!!] Caught exception: %s' % str(e)
            logger.print(out)
        return buffer

    #####################################
    # ABSTRACT METHODS
    #####################################

    # function to manage connection with client
    @abstractmethod
    def _proxy_handler(self, cli_socket: socket.socket):
        pass

    # method that generate and return the socket
    @abstractmethod
    def _create_socket(self):
        pass

    @abstractmethod
    def _get_server_name(self):
        pass

    #####################################
    # PUBLIC METHODS
    #####################################

    # method to start loop server
    def start_server(self):
        logger = Logger(self._conf_log)
        while 1:
            # create socket and start listen to it
            try:
                self._server_socket = self._create_socket()
            except Exception as e:
                out = traceback.format_exc()
                out += '[!!] Fail to listen on %s:%d\n' % (self._address, self._port)
                out += '[!!] Caught a exception ' + str(e)
                logger.print(out)
                try:
                    self._server_socket.close()
                except Exception:
                    pass
                self._exit_or_restart(self._server_socket)
                logger.print('\n[*] Restart %s' % self._get_server_name())
                continue

            # start listen and loop server
            print('[*] Start %s listen on %s:%d' % (self._get_server_name(), self._address, self._port))
            self._server_socket.listen()
            while 1:
                try:
                    cli_socket, cli_address = self._server_socket.accept()
                    # print connection info
                    out = '\n############ START CONNECTION ############\n'
                    out += '[=>] Incoming connection from %s:%d' % cli_address
                    logger.print(out)

                    # start thread to communicate with client and remote host
                    proxy_thread = threading.Thread(target=self._proxy_handler, args=[cli_socket])
                    proxy_thread.start()
                except KeyboardInterrupt:
                    logger.print("[!!] Keyboard interrupt. Exit...")
                    self._server_socket.close()
                    exit()
                except Exception as e:
                    out = ''
                    if not self._bypass_error(e):
                        out += traceback.format_exc()
                        out += '\n'
                    out += '[!!] Caught a exception on Bitoxy: ' + str(e)
                    logger.print(out)
                    try:
                        self._send_400_and_close(cli_socket)
                    except Exception:
                        pass
                    self._server_socket.close()
                    self._exit_or_restart(-1)
                    logger.print('\n[*] Restart %s' % self._get_server_name())
                    break
