import base64

from Crypto.Cipher import AES
from Crypto import Random


# AES class, using for encryption and decryption
class Symmetric:
    # the length of plaintext to encrypted should be the multiple of block_size
    __block_size = AES.block_size

    def __init__(self, key, mode=AES.MODE_CBC):
        # initialize key, mode of AES
        self.key = key
        self.mode = mode

    @staticmethod
    def __unpad(s):
        return s[:-ord(s[len(s) - 1:])]

    def __pad(self, s):
        # append the length of inputed string into the multiple of block_size
        return s + (self.__block_size - len(s) % self.__block_size) *\
               chr(self.__block_size - len(s) % self.__block_size)

    def encrypt(self, plaintext):
        # encrypt the plaintext into ciphertext. Argument "plaintext" should be string. The output is a bytes array
        en = self.__pad(plaintext).encode()
        iv = Random.new().read(AES.block_size)
        cryptor = AES.new(self.key, self.mode, iv)
        cipher_text = cryptor.encrypt(en)

        return base64.b64encode(iv + cipher_text)

    def decrypt(self, cipher_text):
        # decrypt the ciphertext into plaintext. Argument "ciphertext" should be a bytes array. The output is a string
        cipher_text = base64.b64decode(cipher_text)
        iv = cipher_text[:AES.block_size]
        cryptor = AES.new(self.key, self.mode, iv)
        plain_text = cryptor.decrypt(cipher_text[AES.block_size:])

        return self.__unpad(plain_text).decode()

    def get_key(self):
        # return the AES key
        return self.key.decode()
