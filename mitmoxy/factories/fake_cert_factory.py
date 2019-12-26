import os
from ipaddress import ip_address
from threading import Thread


class FakeCertFactory:
    __fake_gen_dir = "conf/key/fake-gen"
    __cert_conf = None

    def __init__(self, cert_conf):
        self.__cert_conf = cert_conf

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

    #####################################
    # PUBLIC METHODS
    #####################################

    # method to generate certificate
    def generate_certificate(self, host):
        # get cert and key path and return if already exists
        cert_path = "%s/%s.crt" % (FakeCertFactory.__fake_gen_dir, host)
        key_path = "%s/%s.key" % (FakeCertFactory.__fake_gen_dir, host)
        if os.path.exists(cert_path) and os.path.exists(key_path):
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
        os.system("cd conf/key && ./fake-cert-generator.sh %s %d > /dev/null" % (host, self.__cert_conf['def-bits']))
        # delete csr configuration file
        os.remove(csr_conf_path)

    # method to generate a certificate with thread
    def generate_certificate_thread(self, host):
        thread = Thread(target=self.generate_certificate, args=[host])
        thread.start()
