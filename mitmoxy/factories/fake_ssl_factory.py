from .fake_cert_factory import FakeCertFactory
from ..controllers.logger import Logger
from ..models.fake_ssl_proxy import FakeSslProxy
from ..utils.functions import fake_certificate_exists
from json import load as json_load


class FakeSslFactory:
    __fake_cert_factory = None
    __logger = None

    def __init__(self):
        self.__fake_cert_factory = FakeCertFactory(self.__get_cert_conf())
        self.__logger = Logger()

    # function to get the certificates configuration
    @staticmethod
    def __get_cert_conf():
        conf_file = open("conf/cert.json", 'r')
        return json_load(conf_file)

    def get_fake_ssl(self, remote_address: tuple, cli_address) -> FakeSslProxy:
        if not fake_certificate_exists(remote_address[0]):
            self.__fake_cert_factory.generate_certificate(remote_address[0])

        fake_ssl = FakeSslProxy(remote_address, cli_address)
        return fake_ssl
