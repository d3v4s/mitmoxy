import sys

from ..core.proxy_thread import ProxyThread
from ..models.proxy import Proxy


class Controller:
    __instance = None

    # singleton
    def __new__(cls, command=None, conf_server=None):
        return object.__new__(cls) if Controller.__instance is None else Controller.__instance

    def __init__(self, command=None, conf_server=None):
        if Controller.__instance is not None:
            return
        Controller.__instance = self
        # set attributes
        self.__conf_server = conf_server
        self.__command = command
        # self.__log = Logger(conf_log)

    #####################################
    # PRIVATE METHODS
    #####################################

    # method for invalid command
    def __invalid_command(self):
        print('[!!] Invalid command %s' % str(self.__command))
        print('[!!] Show the help with "{name} help"'.format(name=sys.argv[0]))
        sys.exit(1)

    # method to start the servers
    def __start_server(self):
        # init fake ssl factory
        # ssl_factory = FakeSslFactory()
        # init proxy thread
        proxy = Proxy(
            self.__conf_server['address'],
            self.__conf_server['port'],
            # SslProxyThread,
            "Mitmoxy proxy",
            self.__conf_server['restart-server']
        )

        if self.__conf_server['mitmoxy-cert-download']:
            ProxyThread.cert_download = self.__conf_server['mitmoxy-cert-download']
            ProxyThread.cert_address = self.__conf_server['cert-address']
            ProxyThread.cert_file_path = self.__conf_server['cert-path']

        proxy.start()

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
