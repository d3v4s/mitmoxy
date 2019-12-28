from ..controllers.logger import Logger
from ..core.proxy_thread import ProxyThread
from ..utils.socket import close_socket_pass_exc, get_bind_socket
from ..utils.functions import bypass_error
from traceback import format_exc
from threading import Thread


class Proxy(Thread):

    def __init__(self, address, port, server_name, restart: bool):
        Thread.__init__(self)
        self.name = self.__server_name = server_name
        self.__address = address
        self.__port = port
        self.__restart = restart
        self.__logger = Logger()
        self.__server_socket = None

    #####################################
    # PROTECTED METHODS
    #####################################

    # function to manage the restart of server
    # exit if restart is disable, else pass and restart the server
    def _exit_or_restart(self, exit_code):
        if not self.__restart:
            exit(exit_code)

    #####################################
    # PUBLIC METHODS
    #####################################

    # method to start loop server
    def run(self) -> None:
        while 1:
            cli_socket = None
            # create socket and start listen to it
            try:
                self.__server_socket = get_bind_socket((self.__address, self.__port))
            except Exception as e:
                out = '' if bypass_error(e) else format_exc()
                out += '[!!] %s fail to listen on %s:%d\n' % (self.__server_name, self.__address, self.__port)
                out += '[!!] Caught an exception on %s %s\n' % (self.__server_name, str(e))
                self.__logger.print_err(out)
                close_socket_pass_exc(self.__server_socket)
                self._exit_or_restart(self.__server_socket)
                self.__logger.print('[*] Restart %s\n' % self.__server_name)
                continue

            # start listen and loop server
            self.__logger.print('[*] Start %s listen on %s:%d\n' % (self.__server_name, self.__address, self.__port))
            self.__server_socket.listen(5)
            while 1:
                try:
                    cli_socket, cli_address = self.__server_socket.accept()
                    cli_address = cli_address[:2]
                    # print connection info
                    self.__logger.print_conn('[=>] Incoming connection from %s:%d\n' % cli_address)

                    # start thread to communicate with client and remote host
                    proxy_thread = ProxyThread(cli_socket, cli_address,
                                               self.__server_socket,
                                               self.__server_name)
                    proxy_thread.start()
                except KeyboardInterrupt:
                    self.__logger.print_err("[!!] Keyboard interrupt. Exit...")
                    close_socket_pass_exc(cli_socket)
                    close_socket_pass_exc(self.__server_socket)
                    exit()
                except Exception as e:
                    out = '' if bypass_error(e) else format_exc()
                    out += '[!!] Caught an exception on %s: %s\n' \
                           '[!!] Shutdown server!!!\n' % (self.__server_name, str(e))
                    self.__logger.print_err(out)
                    close_socket_pass_exc(cli_socket)
                    close_socket_pass_exc(self.__server_socket)
                    self._exit_or_restart(-1)
                    self.__logger.print('[*] Restart %s\n' % self.__server_name)
                    break
