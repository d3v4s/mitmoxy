import datetime

from mitmoxy.model.crypto import generate_rsa_key
from mitmoxy.model.aes import Symmetric
from mitmoxy.model.rsa import Asymmetric


class TLS:
    __max_fails = 10
    __conf_server = None
    __tls_versions = {
        b'\x03\x00': 'SSL 3.0',
        b'\x03\x01': 'TLS 1.0',
        b'\x03\x02': 'TLS 1.1',
        b'\x03\x03': 'TLS 1.2',
        b'\x03\x04': 'TLS 1.3'
    }

    __cipher_suites = {
        b'\x00\x9c': 'RSA-AES128-GCM-SHA256',
        b'\x00\x9d': 'RSA-AES256-GCM-SHA384',
        b'\x00\x2f': 'RSA-AES128-SHA',
        b'\x00\x35': 'RSA-AES256-SHA',
        # b'\xcc\xa8': 'ECDHE-RSA-CHACHA20-POLY1305-SHA256',
        # b'\xcc\xa9': 'ECDHE-ECDSA-CHACHA20-POLY1305-SHA256',
        # b'\xc0\x2f': 'ECDHE-RSA-AES128-GCM-SHA256',
        # b'\xc0\x30': 'ECDHE-RSA-AES256-GCM-SHA384',
        # b'\xc0\x2b': 'ECDHE-ECDSA-AES128-GCM-SHA256',
        # b'\xc0\x2c': 'ECDHE-ECDSA-AES256-GCM-SHA384',
        # b'\xc0\x13': 'ECDHE-RSA-AES128-SHA',
        # b'\xc0\x09': 'ECDHE-ECDSA-AES128-SHA',
        # b'\xc0\x14': 'ECDHE-RSA-AES256-SHA',
        # b'\xc0\x0a': 'ECDHE-ECDSA-AES256-SHA',
        # b'\xc0\x12': 'ECDHE-RSA-3DES-EDE-SHA',
        # b'\x00\x0a': 'RSA-3DES-EDE-SHA',
    }

    __handshake_message_type = {
        b'\x00': 'HELLO_REQUEST',
        b'\x01': 'CLIENT_HELLO',
        b'\x02': 'SERVER_HELLO',
        b'\x0b': 'CERTIFICATE',
        b'\x0c': 'SERVER_KEY_EXCHANGE',
        b'\x0d': 'CERTIFICATE_REQUEST',
        b'\x0e': 'SERVER_DONE',
        b'\x0f': 'CERTIFICATE_VERIFY',
        b'\x10': 'CLIENT_KEY_EXCHANGE',
        b'\x14': 'FINISHED'
    }

    __extensions = {
        b'\x00\x00': 'Server Name Indication',
        b'\x00\x01': 'max_fragment_length',
        b'\x00\x02': 'client_certificate_url',
        b'\x00\x03': 'trusted_ca_keys',
        b'\x00\x04': 'truncated_hmac',
        b'\x00\x05': 'status_request',
        b'\x00\x0d': 'signature_algorithms',
        b'\x00\x17': 'Extended Master Secret',
        b'\x00\x23': 'session_ticket (renamed from "SessionTicket TLS")'
    }

    def __init__(self, conf_server, max_fails=10):
        self.__conf_server = conf_server
        self.__max_fails = max_fails

    #####################################
    # PRIVATE METHODS
    #####################################

    @staticmethod
    def __get_tls_version(data):
        return data[1:3]

    @staticmethod
    def __get_payload_length(data):
        return data[3] * 256 + data[4]

    # @staticmethod
    # def __get_payload_length(data):
    #     return data[3] * 256 + data[4]

    def __get_private_key_ca(self):
        pass

    def __get_ca_signed(self):
        pass

    def __receive_data(self, sock, chunk_size=1024):
        data = b''
        fail = 0
        while 1:
            try:
                data = sock.recv(chunk_size)
            except Exception:
                pass
            if len(data):
                return data
            fail += 1
            if fail >= self.__max_fails:
                return False

    #####################################
    # PUBLIC METHODS
    #####################################

    def tls_handshake(self, sock):
        # read 5 bytes record header from client
        data = self.__receive_data(sock, 5)
        if isinstance(data, bool) and not data:
            raise Exception('TLS handshake problem: Too many fails while receive data from client')

        # byte 0 should be 0x16 - handshake record
        if data[0:1] != b'\x16':
            raise Exception('TLS handshake problem: Byte 0 of handshake is not 0x16: {}'.format(data[0].hex()))

        # throw a exception if tls version is not valid
        if not (self.__get_tls_version(data) in self.__tls_versions):
            raise Exception('TLS handshake problem: TLS version is not valid')

        record_payload_length = self.__get_payload_length(data)
        data = sock.recv(record_payload_length)

        if self.__handshake_message_type[data[0:1]] != 'CLIENT_HELLO':
            raise Exception("Fail TLS handshake")

        print("OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOKKKKKKKKKKKKKKKKKKKKKKKKKKKKK")

        # if data[1] == 'ClientHello':
        #     # represent the starting of handshake
        #     sock.sendall(b'ServerHello')
        #
        #     public_key, private_key = generate_rsa_key()
        #
        #     sign = Asymmetric(self.__get_private_key_ca())
        #     # the server signed packet for client to verify the identity of server,
        #     # the size of the packet is limited by length of 2^14 bytes
        #     server_signed = sign.encrypt(data[0] + '/' + public_key.decode())
        #     # the format is split by b'/'
        #     toSend = self.__get_ca_signed() + b'/' + server_signed
        #
        #     sock.sendall(toSend)
        #     # AES key and a random integer from client
        #     client_packet = sock.recv(1024)
        #     server_unsigned = Asymmetric(private_key)
        #     client_packet = server_unsigned.decrypt(client_packet)
        #     # The format is split by b' '
        #     comm_key, clientInt = client_packet.split(b' ')
        #
        #     aes = Symmetric(comm_key)
        #     # Send to client the encrypted random integer, for client to verify
        #     sock.sendall(aes.encrypt(clientInt.decode()))
        #     return aes

    def handshake(self, sock):
        # read 5 bytes record header from client
        data = b''
        fail = 0
        while 1:
            try:
                data = sock.recv(5)
            except Exception:
                pass
            if len(data):
                break
            fail += 1
            if fail >= self.__max_fails:
                raise Exception('TLS handshake problem: Too many fails while receive data from client')

        print('Read 5 bytes: {}'.format(data.hex()))
        # byte 0 should be 16 - handshake record
        if data[0:1] != b'\x16':
            raise Exception('TLS handshake problem: Byte 0 of handshake is not 0x16: {}'.format(data[0].hex()))

        print('Byte 0 is 0x16: This is a TLS handshake record')
        tls_version = self.__get_tls_version(data)  # (data[1:3])
        tls_translated_version = self.__tls_versions[tls_version]
        print('TLS version {} or {}'.format(tls_version.hex(), tls_translated_version))
        record_payload_length = self.__get_payload_length(data)  # data[3] * 256 + data[4]
        print('Record payload length: {}'.format(record_payload_length))
        data = sock.recv(record_payload_length)
        print('Read {} bytes'.format(record_payload_length))
        # print('record payload: {}'.format(data))
        handshake_header = data[0:4]
        print('Handshake header: {}'.format(handshake_header.hex()))
        print('This is a {}.'.format(self.__handshake_message_type[data[0:1]]))
        handshake_payload_length = data[1] * 65536 + data[2] * 256 + data[3]
        print('Handshake payload length is: {}'.format(handshake_payload_length))
        if handshake_payload_length > record_payload_length - 4:
            print('Handshake payload length exceeds record payload length!')
        handshake_client_version = tls_version = (data[4:6])
        print('Handshake client version: {} or {}'.format(handshake_client_version.hex(), tls_translated_version))
        client_random = data[6:38]
        print('32 Client random bytes {}'.format(client_random.hex()))
        print('Are the first 4 bytes a current timestamp (in spec but not recommended)?')
        seconds = data[6] * 16777216 + data[7] * 65536 + data[8] * 256 + data[9]
        ts = datetime.datetime.fromtimestamp(seconds).strftime('%Y-%m-%d %H:%M:%S')
        print(ts)
        # now things can get shifted, so we use a pointer
        pointer = 38
        session_id_length = data[pointer]
        pointer = pointer + 1
        print('session ID length={}'.format(session_id_length))
        if session_id_length != 0:
            session_id = data[pointer:pointer + session_id_length]
            print('Session ID:{}'.format(session_id))
            pointer = pointer + session_id_length

        cipher_suite_length = data[pointer] * 256 + data[pointer + 1]
        pointer = pointer + 2
        print('Cipher Suite length:{}'.format(cipher_suite_length))
        ciphers = data[pointer:pointer + cipher_suite_length]
        pointer = pointer + cipher_suite_length
        print('Cipher Suite list: {}'.format(ciphers.hex()))
        for i in range(0, len(ciphers), 2):
            cipher = ciphers[i:i + 2]
            if cipher in self.__cipher_suites:
                cipher_name = self.__cipher_suites[cipher]
            else:
                cipher_name = 'unknown'
            print('Cipher ID: {}, Cipher Suite name: {}'.format(cipher.hex(), cipher_name))

        bytes_compression_methods = data[pointer]
        pointer = pointer + 1
        print('{} bytes of compression methods'.format(bytes_compression_methods))
        for i in range(0, bytes_compression_methods):
            print('Compression method: {}'.format(data[pointer]))
            pointer = pointer + 1

        print()
        print('Extensions')
        print()

        extensions_length = data[pointer] * 256 + data[pointer + 1]
        pointer = pointer + 2
        print('Length of extensions is {}'.format(extensions_length))
        # print('Extensions data: {}'.format(data[pointer:pointer+extensions_length]))

        start_of_extensions = pointer
        while (pointer < start_of_extensions + extensions_length):
            extension_type = data[pointer:pointer + 2]
            pointer = pointer + 2
            extension_length = data[pointer] * 256 + data[pointer + 1]
            pointer = pointer + 2
            # print(extension_type, extension_length)
            extension_data = data[pointer:pointer + extension_length]
            pointer = pointer + extension_length
            if extension_type in self.__extensions:
                extension_name = self.__extensions[extension_type]
            else:
                extension_name = 'unknown ({})'.format(extension_type.hex())
            print('{}: {}'.format(extension_name, extension_data.hex()))

    # def continue_handshck(self):

    # method to decript data
    def decrypt(self):
        pass
