import os

from ..utils.functions import fake_certificate_exists
from ipaddress import ip_address
from threading import Thread
from queue import Queue


class FakeCertFactory:
    __fake_gen_dir = "conf/key/fake-gen"
    __cert_req_queue = Queue()
    __run = True

    def __init__(self, cert_conf):
        self.__cert_conf = cert_conf
        thread_factory = Thread(target=self.__start_factory)
        thread_factory.start()

    #####################################
    # PRIVATE STATIC METHODS
    #####################################

    # method to check if is ip address or domain
    # and get the alt name for the certificate
    @staticmethod
    def __get_alt_names(host):
        try:
            ip_address(host)
            return "IP.1=%s" % host
        except ValueError:
            return "DNS.1=%s" % host

    #####################################
    # PRIVATE METHODS
    #####################################

    # method to start certificate factory
    def __start_factory(self):
        while FakeCertFactory.__run:
            host = self.__cert_req_queue.get()
            self.__create_certificate(host)

    # method to get the parameter of certificate
    def __get_cert_parameter(self, host):
        return {
            "default_bits": self.__cert_conf['def-bits'],
            "country_name": self.__cert_conf['country-name'],
            "state_province": self.__cert_conf['state-province'],
            "locality": self.__cert_conf['locality'],
            "organization_name": self.__cert_conf['organization-name'],
            "organization_unit_name": self.__cert_conf['organization-unit-name'],
            "common_name": self.__cert_conf['common-name'],
            "email_address": self.__cert_conf['email-address'],
            "alt_names": self.__get_alt_names(host)
        }

    # method to generate certificate
    def __create_certificate(self, host):
        # return if certificate already exist
        if fake_certificate_exists(host):
            return

        # GENERATE CONFIGURATION FILE FOR CSR (CERTIFICATE SIGNING REQUEST)
        # read template
        file = open('template/cert/csr.conf', 'r')
        csr_conf = file.read()
        file.close()
        # set parameter on template
        cert_param = self.__get_cert_parameter(host)
        csr_conf = csr_conf.format_map(cert_param)
        # create csr conf file
        csr_conf_path = "%s/%s.conf" % (FakeCertFactory.__fake_gen_dir, host)
        file = open(csr_conf_path, 'w')
        file.write(csr_conf)
        file.close()

        # GENERATE THE FAKE CERTIFICATE AND KEY
        # call bash script generator
        os.system("cd conf/key && ./fake-cert-generator.sh %s %d" % (host, self.__cert_conf['def-bits']))
        # delete csr configuration file
        os.remove(csr_conf_path)

    #####################################
    # PUBLIC METHODS
    #####################################

    # method to generate a certificate with thread
    def generate_certificate(self, host):
        self.__cert_req_queue.put(host)
