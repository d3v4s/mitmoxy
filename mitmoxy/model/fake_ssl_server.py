import ssl
import traceback

from ..controllers.logger import Logger
from threading import Thread
from .proxy import Proxy


class FakeSslServer(Proxy):
    __from_port = 4000
    __to_port = 9000
    __remote_address = None
    ready = False

    def __init__(self, remote_address: tuple, logger: Logger, conf_server):
        super(FakeSslServer, self).__init__(logger, conf_server)
        self.__remote_address = remote_address
        self._address = '127.0.0.1'
        self.__start_thread()

    #####################################
    # PRIVATE STATIC METHODS
    #####################################

    #####################################
    # PRIVATE METHODS
    #####################################

    # handler to change a request
    def __req_handler(self, buffer: bytes) -> bytes:
        return buffer

    # handler to change a response
    def __resp_handler(self, buffer: bytes) -> bytes:
        return buffer

    def __start_thread(self):
        thread = Thread(target=self.start_server)
        thread.start()

    # function to get a socket on a free port
    def __get_sock_on_free_port(self) -> ssl.SSLSocket:
        for port in range(self.__from_port, self.__to_port):
            self._port = int(port)
            try:
                sock = self._get_socket(True, self._conf_server['cert-file'], self._conf_server['key-file'])
                return sock
            except Exception as e:
                continue
        raise Exception("Error: free port for fake SSL server not found!!!")

    #####################################
    # PROTECTED METHODS
    #####################################

    # # method that generate and return the socket
    # def _get_socket(self) -> ssl.SSLSocket:
    #     sock = self._create_bind_socket((self._address, self._port))
    #     context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    #     context.load_cert_chain(certfile=self._conf_server['cert-file'], keyfile=self._conf_server['key-file'])
    #     return context.wrap_socket(sock, server_side=True)

    # method to get server name
    def _get_server_name(self) -> str:
        return 'Fake SSL Server'

    # function to manage connection with client
    def _proxy_handler(self, cli_socket: ssl.SSLSocket):
        # get host and port of client
        cli_host, cli_port = cli_socket.getpeername()
        # negotiation with client
        # remote_socket, remote_address = self._client_negotiation(cli_socket)
        # cli_socket.do_handshake()
        # remote_host, remote_port = remote_address
        # init the logger
        # logger = Logger(self._conf_log)
        # count fail
        fail = 0
        # remote_address = self
        try:
            remote_socket = self._get_remote_socket(self.__remote_address, True)
        except Exception as e:
            return
        # loop to route requests and responses
        # between client and remote host
        while 1:
            # receive data from client
            local_buffer = self._receive_from(cli_socket)

            # if client is disconnect close connection and return
            if isinstance(local_buffer, bool) and not local_buffer:
                self._close_socket_pass_exc(remote_socket)
                self._close_socket_pass_exc(cli_socket)

            # if receive data from client
            if len(local_buffer):
                fail = 0

                # change reques with handler and log it
                local_buffer = self.__req_handler(local_buffer)
                self._logger.log_buffer((cli_host, cli_port), local_buffer, True)

                # if remote_address is None:
                #     remote_address = self._get_remote_address(local_buffer, 443)
                #     # remote_host, remote_port = remote_address
                #     remote_socket = self._get_remote_socket(remote_address, True)
                #     try:
                #     except Exception as e:
                #         logger.print("[!!] Error while get remote socket: %s" % str(e))
                #         self._send_404_and_close()
                #         return
                #     if len(e.args) > 1 and e.args[1] == 'Temporary failure in name resolution':

                # send data at remote host
                remote_socket.sendall(local_buffer)

            # receive response from remote
            remote_buffer = self._receive_from(remote_socket)

            # if remote is disconnect close connection and return
            if isinstance(remote_buffer, bool) and not remote_buffer:
                self._close_socket_pass_exc(remote_socket)
                self._close_socket_pass_exc(cli_socket)
                out = "[!!] Remote %s:%d is disconnected\n" % self.__remote_address
                out += "'############ END CONNECTION ############\n'"
                self._logger.print(out)
                return

            # if receive data from remote
            if len(remote_buffer):
                fail = 0

                # change response with handler and log it
                remote_buffer = self.__resp_handler(remote_buffer)
                self._logger.log_buffer(self.__remote_address, remote_buffer, False)
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
                    self._close_socket_pass_exc(remote_socket)
                    self._close_socket_pass_exc(cli_socket)

    #####################################
    # PUBLIC METHODS
    #####################################

    def shutdown(self):
        self.ready = False
        self._close_socket_pass_exc(self._server_socket)

    def get_address(self) -> tuple:
        return self._address, self._port

    # method to start loop server
    def start_server(self):
        cli_socket = None
        try:
            # create socket and start listen to it
            self._server_socket = self.__get_sock_on_free_port()
        except Exception as e:
            self._close_socket_pass_exc(self._server_socket)
            out = traceback.format_exc()
            out += '[!!] %s fail to listen on %s:%d\n' % (self._get_server_name(), self._address, self._port)
            out += '[!!] Caught an exception %s\n' % str(e)
            self._logger.print_err(out)

        # start listen and loop server
        self._logger.print('[*] Start %s listen on %s:%d\n' % (self._get_server_name(), self._address, self._port))
        self._server_socket.listen()
        self.ready = True
        while self.ready:
            try:
                cli_socket, (cli_address, cli_port) = self._server_socket.accept()
                # print connection info
                out = '############ START CONNECTION ############\n'
                out += '[=>] Incoming connection from %s:%d' % (cli_address, cli_port)
                self._logger.print(out)

                # start thread to communicate with client and remote host
                proxy_thread = Thread(target=self._proxy_handler, args=[cli_socket])
                proxy_thread.start()
            except KeyboardInterrupt:
                self._logger.print_err("[!!] Keyboard interrupt. Exit...")
                self._server_socket.close()
                exit()
            except Exception as e:
                out = ''
                if not self._bypass_error(e):
                    out += traceback.format_exc()
                    out += '\n'
                out += '[!!] Caught an exception on Mitmoxy: %s\n' % str(e)
                self._logger.print_err(out)
                # break

        # close all sockets
        self._logger.print('[*] Close %s on %s:%d\n' % (self._get_server_name(), self._address, self._port))
        self._close_socket_pass_exc(cli_socket)
        self._close_socket_pass_exc(self._server_socket)
