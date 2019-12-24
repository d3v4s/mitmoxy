import sys
import threading

from .fake_ssl_factory import FakeSslFactory
from .logger import Logger
from ..model.ssl_proxy import SslProxy
from ..model.http_proxy import HttpProxy


class Controller:
    __instance = None
    __command = None
    __conf_server = None
    __conf_log = None

    # singleton
    def __new__(cls, command=None, conf_server=None, conf_log=None):
        return object.__new__(cls) if Controller.__instance is None else Controller.__instance

    def __init__(self, command=None, conf_server=None, conf_log=None):
        if Controller.__instance is not None:
            return
        Controller.__instance = self
        # set attributes
        self.__conf_server = conf_server
        self.__conf_log = conf_log
        self.__command = command
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
        # init logger and fake ssl server factory
        # logger = Logger(self.__conf_log)
        fake_ssl_factory = FakeSslFactory(self.__conf_log, self.__conf_server)

        ssl_server = SslProxy(self.__conf_log, self.__conf_server, fake_ssl_factory)
        http_server = HttpProxy(self.__conf_log, self.__conf_server)
        ssl_server_thread = threading.Thread(target=ssl_server.start_server)
        http_server_thread = threading.Thread(target=http_server.start_server)
        ssl_server_thread.start()
        http_server_thread.start()

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
