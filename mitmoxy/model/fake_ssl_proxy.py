from .proxy import Proxy
from ..core.fake_ssl_thread import FakeSslThread
from ..utils.functions import bypass_error
from ..utils.socket import close_socket_pass_exc
from traceback import format_exc
from threading import Thread
from ssl import SSLSocket


class FakeSslProxy(Proxy):

    def __init__(self, server_name, remote_address):
        Proxy.__init__(self, "127.0.0.1", None, False, None, server_name)
        self.__remote_address = remote_address
        self.__from_port = 4000
        self.__to_port = 9000
        self.ready = False
        self.__start_thread()

    #####################################
    # PRIVATE METHODS
    #####################################

    def __start_thread(self):
        thread = Thread(target=self.start_server)
        thread.start()

    # function to get a socket on a free port
    def __get_sock_on_free_port(self) -> SSLSocket:
        for port in range(self.__from_port, self.__to_port):
            self._port = int(port)
            try:
                sock = self._get_socket(
                    True,
                    "conf/key/fake-gen/%s.crt" % self.__remote_address[0],
                    "conf/key/fake-gen/%s.key" % self.__remote_address[0]
                )
                return sock
            except Exception:
                continue
        raise Exception("Free port for fake SSL server not found")

    #####################################
    # PUBLIC METHODS
    #####################################

    def shutdown(self):
        self.ready = False
        close_socket_pass_exc(self._server_socket)

    def get_address(self) -> tuple:
        return self._address, self._port

    # method to start loop server
    def start_server(self):
        cli_socket = None
        try:
            # create socket and start listen to it
            self._server_socket = self.__get_sock_on_free_port()
        except Exception as e:
            close_socket_pass_exc(self._server_socket)
            out = '' if bypass_error(e) else format_exc()
            out += '[!!] %s starting failed\n' % self._server_name
            out += '[!!] Caught an exception %s\n' % str(e)
            self._logger.print_err(out)
            return

        # start listen and loop server
        self._logger.print('[*] Start %s listen on %s:%d\n' % (self._server_name, self._address, self._port))
        self._server_socket.listen()
        self.ready = True
        while self.ready:
            try:
                cli_socket, cli_address = self._server_socket.accept()
                cli_address = cli_address[:2]
                # print connection info
                out = '############ START CONNECTION ############\n'
                out += '[=>] Incoming connection from %s:%d' % cli_address
                self._logger.print(out)

                # start thread to communicate with client and remote host
                proxy_thread = FakeSslThread(cli_socket, cli_address, self._server_socket, self.__remote_address)
                proxy_thread.start()
            except KeyboardInterrupt:
                self._logger.print_err("[!!] Keyboard interrupt. Exit...")
                self._server_socket.close()
                exit()
            except Exception as e:
                out = '' if bypass_error(e) else format_exc()
                out += '[!!] Caught an exception on Mitmoxy: %s\n' % str(e)
                self._logger.print_err(out)
                # break

        # close all sockets
        self._logger.print('[*] Close %s on %s:%d\n' % (self._server_name, self._address, self._port))
        close_socket_pass_exc(cli_socket)
        close_socket_pass_exc(self._server_socket)
