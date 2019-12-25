import socket
import ssl

from ..controllers.logger import Logger
from ..utils.functions import decode_buffer, bypass_error
from ..utils.socket import close_socket_pass_exc
from abc import ABC, abstractmethod
from traceback import format_exc
from threading import Thread


class ProxyThread(Thread, ABC):

    def __init__(self, cli_socket, cli_address, server_socket):
        Thread.__init__(self)
        self._cli_socket = cli_socket
        self._cli_address = cli_address
        self._server_socket = server_socket
        self._logger = Logger()
        self._max_fails = 10
        self._timeout = 0.1
        # self._server_name

    #####################################
    # STATIC PROTECTED METHODS
    #####################################

    # function to get remote socket
    @staticmethod
    def _get_remote_socket(address: tuple, ssl_wrap=False):
        # create socket
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
    # PROTECTED METHODS
    #####################################

    # function to read buffer from connection
    def _receive_from(self, conn: socket.socket, address, chunk_size=2048):
        buffer = b''
        # read from socket buffer
        try:
            # set timeout
            conn.settimeout(self._timeout)
            self._logger.print("[*] Start receive from %s:%d" % address)
            while 1:
                data = conn.recv(chunk_size)
                if not data:
                    break
                buffer += data
        except KeyboardInterrupt:
            self._logger.print("[!!] Keyboard interrupt. Exit...")
            close_socket_pass_exc(conn)
            close_socket_pass_exc(self._server_socket)
            exit()
        except Exception as e:
            out = '' if bypass_error(e) else format_exc()
            out += '[!!] Fail receive data'
            try:
                out += 'from %s:%d\n' % address
            except Exception:
                out += '\n'

            out += '[!!] Caught an exception: %s\n' % str(e)
            self._logger.print_err(out)
            # if endpoint is disconnected return false
            if len(e.args) >= 2 and e.args[1] == 'Transport endpoint is not connected':
                return False
        return buffer

    #####################################
    # ABSTRACT METHODS
    #####################################

    @abstractmethod
    def run(self) -> None:
        pass
