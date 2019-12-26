import ssl

from ..controllers.logger import Logger
from ..utils.socket import close_socket_pass_exc, create_bind_socket
from ..utils.functions import bypass_error
from traceback import format_exc
from threading import Thread


class Proxy(Thread):

    def __init__(self, address, port, proxy_handle_class, server_name, restart=True):
        Thread.__init__(self)
        self._proxy_thread = proxy_handle_class
        self._server_name = server_name
        self._address = address
        self._port = port
        self._restart = restart
        self._logger = Logger()
        self._server_socket = None
        self.name = server_name

    #####################################
    # PROTECTED METHODS
    #####################################

    # function to manage the restart of server
    # exit if restart is disable, else pass and restart the server
    def _exit_or_restart(self, exit_code):
        if not self._restart:
            exit(exit_code)

    # method that generate and return the socket
    def _get_socket(self, ssl_wrap=False, cert_file=None, key_file=None):
        sock = create_bind_socket((self._address, self._port))
        if ssl_wrap:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(certfile=cert_file, keyfile=key_file)
            return context.wrap_socket(sock, server_side=True)
        return sock

    #####################################
    # PUBLIC METHODS
    #####################################

    # method to start loop server
    def run(self) -> None:
        while 1:
            cli_socket = None
            # create socket and start listen to it
            try:
                self._server_socket = self._get_socket()
            except Exception as e:
                out = '' if bypass_error(e) else format_exc()
                out += '[!!] %s fail to listen on %s:%d\n' % (self._server_name, self._address, self._port)
                out += '[!!] Caught an exception on %s %s\n' % (self._server_name, str(e))
                self._logger.print_err(out)
                close_socket_pass_exc(self._server_socket)
                self._exit_or_restart(self._server_socket)
                self._logger.print('[*] Restart %s\n' % self._server_name)
                continue

            # start listen and loop server
            self._logger.print('[*] Start %s listen on %s:%d\n' % (self._server_name, self._address, self._port))
            self._server_socket.listen(5)
            while 1:
                try:
                    cli_socket, cli_address = self._server_socket.accept()
                    cli_address = cli_address[:2]
                    # print connection info
                    self._logger.print_conn('[=>] Incoming connection from %s:%d\n' % cli_address)

                    # start thread to communicate with client and remote host
                    proxy_thread = self._proxy_thread(cli_socket, cli_address, self._server_socket, self._server_name)
                    proxy_thread.start()
                except KeyboardInterrupt:
                    self._logger.print_err("[!!] Keyboard interrupt. Exit...")
                    close_socket_pass_exc(cli_socket)
                    close_socket_pass_exc(self._server_socket)
                    exit()
                except Exception as e:
                    out = '' if bypass_error(e) else format_exc()
                    out += '[!!] Caught an exception on %s: %s\n' \
                           '[!!] Shutdown server!!!\n' % (self._server_name, str(e))
                    self._logger.print_err(out)
                    close_socket_pass_exc(cli_socket)
                    close_socket_pass_exc(self._server_socket)
                    self._exit_or_restart(-1)
                    self._logger.print('[*] Restart %s\n' % self._server_name)
                    break
