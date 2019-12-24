from _ctypes import pointer

from .logger import Logger
from .fake_cert_factory import FakeCertFactory
from ..model.fake_ssl_server import FakeSslServer


class FakeSslFactory:
    __fake_cert_factory = None
    __conf_server = None
    __logger = None

    def __init__(self, conf_log, conf_server):
        self.__fake_cert_factory = FakeCertFactory()
        self.__conf_server = conf_server
        self.__logger = Logger(conf_log)

    def get_fake_ssl(self, remote_address: tuple) -> FakeSslServer:
        fake_ssl = FakeSslServer(remote_address, self.__logger, self.__conf_server)
        return fake_ssl
