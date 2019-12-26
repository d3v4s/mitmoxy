import sys

from mitmoxy.factories.fake_ssl_factory import FakeSslFactory
from ..core.http_proxy_thread import HttpProxyThread
from ..core.ssl_proxy_thread import SslProxyThread
from ..models.cert_server import CertServer
from ..models.proxy import Proxy


class Controller:
    __instance = None

    # singleton
    def __new__(cls, command=None, conf_server=None, cert_server_conf=None):
        return object.__new__(cls) if Controller.__instance is None else Controller.__instance

    def __init__(self, command=None, conf_server=None, cert_server_conf=None):
        if Controller.__instance is not None:
            return
        Controller.__instance = self
        # set attributes
        self.__conf_server = conf_server
        self.__command = command
        self.__cert_server_conf = cert_server_conf
        # self.__log = Logger(conf_log)

    #####################################
    # PRIVATE METHODS
    #####################################

    # method for invalid command
    def __invalid_command(self):
        print('[!!] Invalid command ' + str(self.__command))
        print('[!!] Show the help with "{name} help"'.format(name=sys.argv[0]))
        sys.exit(1)

    # method to start the servers
    def __start_server(self):
        # init fake ssl server factory
        fake_ssl_factory = FakeSslFactory()

        # init proxies threads
        ssl_server = Proxy(
            self.__conf_server['ssl-address'],
            self.__conf_server['ssl-port'],
            SslProxyThread,
            "SSL proxy",
            self.__conf_server['restart-server']
        )
        http_server = Proxy(
            self.__conf_server['http-address'],
            self.__conf_server['http-port'],
            HttpProxyThread,
            "HTTP proxy",
            self.__conf_server['restart-server']
        )
        ssl_server.start()
        http_server.start()

        if self.__cert_server_conf['active']:
            cert_server = CertServer(
                self.__cert_server_conf['address'],
                self.__cert_server_conf['port'],
                self.__cert_server_conf['cert-path']
            )
            cert_server.start()

    #####################################
    # PUBLIC METHODS
    #####################################

    # method to execute the request command
    def execute(self):
        # switch command and call function
        switcher = {
            "start": self.__start_server
        }
        func = switcher.get(self.__command, self.__invalid_command)
        func()
