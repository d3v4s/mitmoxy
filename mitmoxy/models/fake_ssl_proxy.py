import datetime

from ..controllers.logger import Logger
from ..core.fake_ssl_thread import FakeSslThreadABC
from ..utils.functions import bypass_error, fake_certificate_exists
from ..utils.socket import close_socket_pass_exc, get_bind_socket
from traceback import format_exc
from threading import Thread
from ssl import SSLSocket


class FakeSslProxy(Thread):

    def __init__(self, remote_address, cli_address):
        Thread.__init__(self)
        self.name = self.__server_name = "Fake SSL Server Proxy (%s:%d)" % remote_address
        self.__address = "127.0.0.1"
        self.__port = None
        self.__logger = Logger()
        self.__server_socket = None
        self.__remote_address = remote_address
        self.__cli_address = cli_address
        self.__from_port = 4000
        self.__to_port = 9000
        self.ready = False
        self.start()

    #####################################
    # PRIVATE METHODS
    #####################################

    # function to wait a generation of fake certificate
    def __wait_certificate(self, timeout=2):
        start_time = datetime.datetime.now()
        max_time = datetime.timedelta(seconds=timeout)
        while 1:
            if fake_certificate_exists(self.__remote_address[0]):
                return
            exec_time = datetime.datetime.now() - start_time
            # exec_time.time
            if exec_time > max_time:
                raise Exception("Wait certificate for %s timeout" % self.__remote_address)

    # function to get a socket on a free port
    def __get_sock_on_free_port(self) -> SSLSocket:
        for port in range(self.__from_port, self.__to_port):
            self.__port = int(port)
            try:
                sock = get_bind_socket(
                    (self.__address, port),
                    True,
                    "conf/key/fake-gen/%s.crt" % self.__remote_address[0],
                    "conf/key/fake-gen/%s.key" % self.__remote_address[0]
                )
                return sock
            except Exception as e:
                continue
        raise Exception("Free port for %s server not found" % self.__server_name)

    #####################################
    # PUBLIC METHODS
    #####################################

    def shutdown(self):
        self.ready = False
        close_socket_pass_exc(self.__server_socket)

    # method to get the tuple that represent
    # the server address (host and port)
    def get_address(self) -> tuple:
        return self.__address, self.__port

    # method to start loop server
    def run(self) -> None:
        cli_socket = None
        try:
            self.__wait_certificate()
            # create socket and start listen to it
            self.__server_socket = self.__get_sock_on_free_port()
        except Exception as e:
            close_socket_pass_exc(self.__server_socket)
            out = '' if bypass_error(e) else format_exc()
            out += '[!!] %s starting failed\n' % self.__server_name
            out += '[!!] Caught an exception %s\n' % str(e)
            self.__logger.print_err(out)
            return

        # start listen and loop server
        self.__logger.print_conn('[*] Start %s listen on %s:%d\n' % (self.__server_name, self.__address, self.__port))
        self.__server_socket.listen()
        self.ready = True
        while self.ready:
            try:
                cli_socket, cli_address = self.__server_socket.accept()
                cli_address = cli_address[:2]
                # print connection info
                self.__logger.print_conn('[=>] Local client connect to %s' % self.__server_name)

                # start thread to communicate with client and remote host
                proxy_thread = FakeSslThreadABC(
                    cli_socket,
                    cli_address,
                    self.__server_socket,
                    self.__remote_address,
                    self.__server_name
                )
                proxy_thread.start()
            except KeyboardInterrupt:
                self.__logger.print_err("[!!] Keyboard interrupt. Exit...")
                self.__server_socket.close()
                exit()
            except Exception as e:
                out = '' if bypass_error(e) else format_exc()
                out += '[!!] Caught an exception on %s: %s\n' % (self.__server_name, str(e))
                self.__logger.print_err(out)
                # break

        # close all sockets
        self.__logger.print_conn('[*] Close %s\n' % self.__server_name)
        close_socket_pass_exc(cli_socket)
        close_socket_pass_exc(self.__server_socket)
