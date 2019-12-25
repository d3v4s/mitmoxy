from ..utils.functions import get_conf, decode_buffer
from traceback import format_exc
from datetime import datetime
from time import sleep


class Logger:
    __instance = None
    __conf_log = None
    __lock_timeout = 3
    __lock = False
    __dec_buffer = None

    # singleton
    def __new__(cls, conf_log=None):
        return object.__new__(cls) if Logger.__instance is None else Logger.__instance

    def __init__(self, conf_log=None):
        if Logger.__instance is not None:
            return
        Logger.__instance = self
        if conf_log is None:
            self.__conf_log = get_conf("conf/log.json")
        else:
            self.__conf_log = conf_log

    #####################################
    # PRIVATE METHODS
    #####################################

    # function to print out in stdo
    def __stdo_print(self, out):
        if self.__conf_log['print-stdo']:
            print("[%s]" % datetime.now())
            print(out)

    # function to get hex dump of buffer
    def __hex_dump(self, length=16) -> str:
        # return if not hex dump require
        if not self.__conf_log['hex-dump']:
            return ''

        # init result and decode buffer
        buffer = self.__dec_buffer
        result = ['', '############ START HEX-DUMP ############']
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
        result.append('############ END HEX-DUMP ############')
        result.append('')
        return '\n'.join(result)

    # function to get bytes of buffer
    def __bytes(self, buffer: bytes) -> str:
        if not self.__conf_log['bytes']:
            return ''
        res = [
            '',
            '############ START BYTES ############',
            ':'.join("{:02x}".format(x) for x in buffer),
            '############ END BYTES ############',
            ''
        ]
        return '\n'.join(res)

    # function to get contents of buffer
    def __contents(self) -> str:
        if not self.__conf_log['content']:
            return ''

        # buffer = server.decode_buffer(buffer)
        # buffer =
        res = [
            '',
            '############ START CONTENT ############',
            ''.join([char if 0x20 <= ord(char) < 0x7F or ord(char) == 0x0A or ord(char) == 0x0D else '.'
                     for char in self.__dec_buffer]),
            '############ END CONTENT ############',
            ''
        ]
        return '\n'.join(res)

    # method to save the logs
    def __save_log_address(self, from_address, log):
        pass

    def __save_log_err(self, error):
        pass

    def __save_log(self, log):
        pass

    # function to try lock
    def __try_lock(self) -> bool:
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
    def log_buffer(self, from_address, buffer: bytes, is_cli):
        if self.__try_lock():
            try:
                self.__stdo_print('[%s] Received %d bytes from %s:%d' % (
                    "=>" if is_cli else "<=",
                    len(buffer),
                    from_address[0],
                    from_address[1]
                ))
                self.__dec_buffer = decode_buffer(buffer)
                # get bytes
                out = self.__bytes(buffer)
                # get content
                out += self.__contents()
                # get hex dump
                out += self.__hex_dump()
                # print in stdo and log it
                self.__stdo_print(out)
                self.__save_log_address(from_address, out)
            except Exception as e:
                print(format_exc())
                print("[!!] An exception was caught while running buffer logging: %s" % str(e))
            finally:
                self._unlock()

    # function to check if print in
    # stdo (standard output) is enable,
    # and write on log
    def print(self, content: str):
        if self.__try_lock():
            try:
                self.__stdo_print(content)
                self.__save_log(content)
            except Exception as e:
                print(format_exc())
                print("[!!] Caught an exception while logging: %s" % str(e))
            finally:
                self._unlock()

    # function to print error on stdo and write on log
    def print_err(self, err: str):
        if self.__try_lock():
            try:
                print(err)
                self.__save_log_err(err)
            except Exception as e:
                print(format_exc())
                print("[!!] Caught an exception while logging the error: %s" % str(e))
            finally:
                self._unlock()
