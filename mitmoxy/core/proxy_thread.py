import socket
import ssl

from ..controllers.logger import Logger
from ..utils.functions import decode_buffer, bypass_error
from ..utils.socket import close_socket_pass_exc, send_404_and_close
from ..models.fake_ssl_proxy import FakeSslProxy
from ..factories.fake_ssl_factory import FakeSslFactory
from abc import ABC, abstractmethod
from traceback import format_exc
from threading import Thread
from time import sleep


class ProxyThread(Thread, ABC):

    def __init__(self, cli_socket, cli_address, server_socket, server_name):
        Thread.__init__(self)
        self._cli_socket = cli_socket
        self._cli_address = cli_address
        self._server_socket = server_socket
        self._server_name = server_name
        self._logger = Logger()
        self._max_fails = 2
        self._timeout = 0.1
        self.__fake_ssl_factory = FakeSslFactory()
        self.name = "%s handler thread - Client: %s:%d" % (server_name, cli_address[0], cli_address[1])

    #####################################
    # PRIVATE METHODS
    #####################################

    # function to wait the ready of fake ssl server
    @staticmethod
    def __wait_fake_ssl(fake_ssl_server: FakeSslProxy):
        fail = 0
        while not fake_ssl_server.ready:
            fail += 1
            if fail > 100:
                raise Exception("Wait fake SSL server fail too many time")
            sleep(0.1)

    # method to manage the negotiation with client
    def _client_negotiation(self):
        fail = 0
        while 1:
            # receive data from client
            local_buffer = self._receive_from(self._cli_socket, self._cli_address, 32)

            # if client is disconnect close connection and return
            if isinstance(local_buffer, bool) and not local_buffer:
                try:
                    self._cli_socket.close()
                except Exception:
                    pass
                # out = "[!!] Client %s:%d is disconnected\n" % self._cli_address
                # out += '############ END CONNECTION ############\n'
                # self._logger.print(out)
                raise Exception("Client %s:%d disconnected from %s" %
                                (self._cli_address[0], self._cli_address[1], self.name))

            if len(local_buffer):
                # if request type isn't CONNECT send bad request code
                if decode_buffer(local_buffer)[:7] != 'CONNECT':
                    self._cli_socket.sendall(b'HTTP/1.1 400 Bad Request\r\n\r\n')
                    raise Exception("Error while negotiation with the client. Bad request from client!!!")

                # get host and port remote
                remote_address = self._get_remote_address(local_buffer)
                try:
                    remote_socket = self._get_remote_socket(remote_address, True)
                    remote_socket.close()
                except Exception as e:
                    send_404_and_close(self._cli_socket)
                    self._logger.print_err("[!!] Error while get remote socket: %s" % str(e))
                    return False

                # send negotiation confirm
                conf_buff = b'HTTP/1.1 200 Connection established\r\n\r\n'
                self._cli_socket.sendall(conf_buff)
                # create a socket with fake ssl server and return it
                return self.__fake_ssl_factory.get_fake_ssl(remote_address, self._cli_address)
            # increment fails and check max
            fail += 1
            if fail >= self._max_fails:
                raise Exception("Error while negotiation with the client. Too many fails!!!")

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
            # self._logger.print("[*] Start receive from %s:%d" % address)
            while 1:
                data = conn.recv(chunk_size)
                if not data:
                    break
                buffer += data
        except KeyboardInterrupt:
            self._logger.print_err("[!!] Keyboard interrupt. Exit...")
            close_socket_pass_exc(conn)
            close_socket_pass_exc(self._server_socket)
            exit()
        except Exception as e:
            if bypass_error(e):
                return buffer
            out = format_exc()
            out += '[!!] Fail receive data from %s:%d\n' % address
            out += '[!!] Caught an exception on %s: %s\n' % (self.name, str(e))
            self._logger.print_err(out)
            # if endpoint is disconnected return false
            if len(e.args) >= 2 and e.args[1] == 'Transport endpoint is not connected':
                return False
        return buffer

    def run(self) -> None:
        try:

            # cli_host, cli_port = cli_socket.getpeername()

            # negotiation with client
            fake_ssl_server = self._client_negotiation()
            # if negotiation failed return
            if isinstance(fake_ssl_server, bool) and not fake_ssl_server:
                return

            # count fail
            fail = 0

            self.__wait_fake_ssl(fake_ssl_server)
            fake_ssl_address = fake_ssl_server.get_address()
            fake_ssl_socket = self._get_remote_socket(fake_ssl_address)
        except Exception as e:
            send_404_and_close(self._cli_socket)
            out = '' if bypass_error(e) else format_exc()
            out += "[!!] Caught a exception %s: %s" % (self.name, str(e))
            self._logger.print_err(out)
            return

        # loop to route requests and responses
        # between client and fake ssl host
        while 1:
            # receive data from client
            local_buffer = self._receive_from(self._cli_socket, self._cli_address)

            # if client is disconnect close connection and return
            if isinstance(local_buffer, bool) and not local_buffer:
                close_socket_pass_exc(self._cli_socket)
                close_socket_pass_exc(fake_ssl_socket)
                fake_ssl_server.shutdown()
                self._logger.print_conn("[!!] Client %s:%d is disconnected\n" % self._cli_address)
                return

            if len(local_buffer):
                fail = 0
                # send request to fake ssl server
                fake_ssl_socket.sendall(local_buffer)

            # receive response from remote
            remote_buffer = self._receive_from(fake_ssl_socket, fake_ssl_address)

            # if remote is disconnect close connection and return
            if isinstance(remote_buffer, bool) and not remote_buffer:
                close_socket_pass_exc(self._cli_socket)
                close_socket_pass_exc(fake_ssl_socket)
                fake_ssl_server.shutdown()
                self._logger.print_conn("[!!] Fake server is disconnected\n")
                return

            if len(remote_buffer):
                fail = 0
                # send response to client
                self._cli_socket.sendall(remote_buffer)

            # check len of buffers
            if not (len(local_buffer) or len(remote_buffer)):
                fail += 1
                # if fails too many times close connections
                if fail >= self._max_fails:
                    out = '[!!] %s fails to many times!!!\n' % self.name
                    out += '[!!] Close connections of %s\n' % self._server_name
                    self._logger.print_err(out)
                    close_socket_pass_exc(self._cli_socket)
                    close_socket_pass_exc(fake_ssl_socket)
                    fake_ssl_server.shutdown()
                    break
