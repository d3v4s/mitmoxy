from .crypto import str64decode


# RSA class, using for encryption and decryption
class Asymmetric:
    __max_key_length = None
    __byte_length = 3
    __key = None

    def __init__(self, key):
        # Initialize the key into special format
        key = key.split(b' ')
        self.__key = str64decode(key[0]), str64decode(key[1])
        self.__max_key_length = len(str(self.__key[0])) // 3 - 1

    # function to separate a string or a list into dispersed elements, limited by length
    @staticmethod
    def __spc(x, length):
        return [x[i:i + length:] for i in range(0, len(x) - length, length)] + \
               [x[-(len(x) % length):-1] + x[-1]]

    # function to encode a string into a list of postive integers, the argument "text" should be a string
    def __buff_encode(self, buffer):
        enText = ['1'] + [(self.__byte_length - len(str(ord(i)))) * '0' + str(ord(i)) for i in buffer]
        return int(''.join(enText))

    # function to decode a list of positve integers into a string, the argument "text" should be a list of integers
    def __buff_decode(self, buffer):
        deText = [chr(int(str(buffer)[i + 1:i + 1 + self.__byte_length])) for i in
                  range(0, len(str(buffer)) - self.__byte_length, self.__byte_length)]
        return ''.join(deText)

    # function to encrypt the plaintext into cipher text.
    # Argument "text" should be string. The output is a bytes array
    def encrypt(self, text: str):
        text = self.__spc(text, self.__max_key_length)
        en = []
        for elem in text:
            elem = self.__buff_encode(elem)
            en.append(str(pow(elem, self.__key[1], self.__key[0])))

        return ' '.join(en).encode()

    # function to decrypt the cipher text into plaintext.
    # Argument "text" should be a list of string. The output is a string
    def decrypt(self, text):
        text = [int(i) for i in text.decode().split()]
        de = ''
        for elem in text:
            de += self.__buff_decode(pow(elem, self.__key[1], self.__key[0]))

        return de.encode()
