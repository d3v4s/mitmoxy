import ssl
import socket
import threading
import traceback

from abc import abstractmethod, ABC
from .server import Server, decode_buffer

from mitmoxy.controllers.logger import Logger


class Proxy(Server, ABC):

    #####################################
    # STATIC PROTECTED METHODS
    #####################################

    # function to get remote socket
    @staticmethod
    def _get_remote_socket(address: tuple, ssl_wrap=False):
        # host, port = address
        # create socket
        print("ADDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD: %s:%d" % address)
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # if ssl_wrap is true, then create ssl socket
        if ssl_wrap:
            # create ssl context
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_default_certs(purpose=ssl.Purpose.SERVER_AUTH)
            # connect to remote
            # remote_socket = socket.create_connection(address)
            remote_socket.connect(address)
            # wrap socket on ssl context and return it
            return context.wrap_socket(remote_socket, server_hostname=address[0])

        # else connect to remote and return the socket
        remote_socket.connect(address)
        return remote_socket

    # function to get remote address and port
    @staticmethod
    def _get_remote_address(request, def_port=80) -> tuple:
        # convert binary to string
        request = decode_buffer(request) if isinstance(request, bytes) else request
        # get url
        url = request.split('\n')[0].split(' ')[1]
        # find position of ://
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
            port = def_port
            address = temp[:address_pos]
        else:
            # specific port
            port = int((temp[(port_pos + 1):])[:address_pos - port_pos - 1])
            address = temp[:port_pos]
        return address, port

    #####################################
    # ABSTRACT METHODS
    #####################################

    # function to manage connection with client
    @abstractmethod
    def _proxy_handler(self, cli_socket: socket.socket):
        pass

    #####################################
    # PUBLIC METHODS
    #####################################

    # method to start loop server
    def start_server(self):
        logger = Logger(self._conf_log)
        cli_socket = None
        while 1:
            # create socket and start listen to it
            try:
                self._server_socket = self._get_socket()
            except Exception as e:
                out = traceback.format_exc()
                out += '[!!] %s fail to listen on %s:%d\n' % (self._get_server_name(), self._address, self._port)
                out += '[!!] Caught an exception %s\n' % str(e)
                logger.print_err(out)
                try:
                    self._server_socket.close()
                except Exception:
                    pass
                self._exit_or_restart(self._server_socket)
                logger.print('[*] Restart %s\n' % self._get_server_name())
                continue

            # start listen and loop server
            logger.print('[*] Start %s listen on %s:%d\n' % (self._get_server_name(), self._address, self._port))
            self._server_socket.listen(5)
            while 1:
                try:
                    cli_socket, (cli_address, cli_port) = self._server_socket.accept()
                    # print connection info
                    out = '############ START CONNECTION ############\n'
                    out += '[=>] Incoming connection from %s:%d' % (cli_address, cli_port)
                    logger.print(out)

                    # start thread to communicate with client and remote host
                    proxy_thread = threading.Thread(target=self._proxy_handler, args=[cli_socket])
                    proxy_thread.start()
                except KeyboardInterrupt:
                    logger.print_err("[!!] Keyboard interrupt. Exit...")
                    self._server_socket.close()
                    exit()
                except Exception as e:
                    out = ''
                    if not self._bypass_error(e):
                        out += traceback.format_exc()
                        out += '\n'
                    out += '[!!] Caught an exception on Mitmoxy: %s\n' % str(e)
                    logger.print_err(out)
                    try:
                        self._send_400_and_close(cli_socket)
                    except Exception:
                        pass
                    self._server_socket.close()
                    self._exit_or_restart(-1)
                    logger.print('[*] Restart %s' % self._get_server_name())
                    break
