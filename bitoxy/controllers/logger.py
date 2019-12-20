from time import sleep


class Logger:
    __instance = None
    __conf_log = None
    __lock = False

    # singleton
    def __new__(cls, conf_log=None):
        return object.__new__(cls) if Logger.__instance is None else Logger.__instance

    def __init__(self, conf_log=None):
        if Logger.__instance is not None:
            return
        Logger.__instance = self
        self.__conf_log = conf_log

    #####################################
    # PRIVATE METHODS
    #####################################

    # function to print hex dump of buffer
    def __hex_dump(self, buffer, length=16):
        # return if not print hex dump
        if not self.__conf_log['hex-dump']:
            return

        # init result and decode buffer
        from bitoxy.core import server
        result = []
        buffer = server.decode_buffer(buffer)
        print()
        print('############ START CONTENT ############')
        print(buffer)
        print('############ END CONTENT ############')
        print()
        print('############ HEX-DUMP ############')
        # create hex dump
        for i in range(0, len(buffer), length):
            # get row of length specified
            row = buffer[i:i + length]
            # create hex
            hexa = ' '.join(["%0*X" % (4, ord(char)) for char in row])
            # create text
            text = ''.join([char if 0x20 <= ord(char) < 0x7F else '.' for char in row])
            # append hex and text on result
            result.append("%04X\t%-*s\t%s" % (i, length * 5, hexa, text))
        # print result
        result = '\n'.join(result)
        print(result)
        return result

    # method to save the logs
    def __save_log_address(self, from_address, log):
        pass

    def __save_log(self, log):
        pass

    # function to try lock
    def __try_lock(self, timeout=None):
        while 1:
            # try to lock
            if not self.__lock:
                # lock and return
                self.__lock = True
                return True
            sleep(0.1)

    # function to unlock
    def _unlock(self):
        self.__lock = False

    #####################################
    # PUBLIC METHODS
    #####################################

    # function to log the buffer
    # implement a lock
    def log(self, from_address, buffer, is_cli):
        if self.__try_lock():
            print('[%s] Received %d bytes from %s:%d' % (
                "=>" if is_cli else "<=",
                len(buffer),
                from_address[0],
                from_address[1]
            ))
            # print hex dump
            hex_dump = self.__hex_dump(buffer)
            self.__save_log_address(from_address, hex_dump)
            self._unlock()

    # function to check if print in stdo (standard output)
    # is enable, and write the log
    def print(self, content):
        if self.__try_lock():
            print(content)
            self.__save_log(content)
            self._unlock()
