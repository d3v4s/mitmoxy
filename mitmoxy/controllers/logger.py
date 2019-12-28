from queue import Queue
from threading import Thread

from ..utils.functions import get_conf, decode_buffer
from traceback import format_exc
from datetime import datetime, timedelta
from time import sleep


class Logger:
    __instance = None

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

        self.__dec_buffer = None
        self.__log_queue = Queue()
        self.active = True
        logger_thread = Thread(target=self.__start_logger)
        logger_thread.start()

    #####################################
    # PRIVATE METHODS
    #####################################

    def __start_logger(self):
        while self.active:
            function, param = self.__log_queue.get()
            function(param)

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

    # function to log the buffer
    def __log_buffer(self, args: list):  # from_address, buffer: bytes, is_cli):
        from_address = args[0]
        buffer = args[1]
        is_cli = args[2]
        if (is_cli and self.__conf_log['req']) or (not is_cli and self.__conf_log['resp']):  # and self.__try_lock():
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

    # function to check if print in
    # stdo (standard output) is enable,
    # and write on log
    def __print(self, args: list):
        try:
            content = args[0]
            self.__stdo_print(content)
            self.__save_log(content)
        except Exception as e:
            print(format_exc())
            print("[!!] Caught an exception while logging: %s" % str(e))

    # function to print error and write on log
    def __print_err(self, args: list):
        try:
            err = args[0]
            print("[%s]" % datetime.now())
            print(err)
            self.__save_log_err(err)
        except Exception as e:
            print(format_exc())
            print("[!!] Caught an exception while logging the error: %s" % str(e))

    # function to print connection info and write it on log
    def __print_conn(self, args: list):
        if self.__conf_log['conn']:
            try:
                log = args[0]
                print("[%s]" % datetime.now())
                print(log)
                self.__save_log(log)
            except Exception as e:
                print(format_exc())
                print("[!!] Caught an exception while logging the connection: %s" % str(e))

    #####################################
    # PUBLIC METHODS
    #####################################

    # function to add print log buffer on log queue
    def log_buffer(self, from_address, buffer: bytes, is_cli):
        self.__log_queue.put((self.__log_buffer, [from_address, buffer, is_cli]))

    # function to add simple print on log queue
    def print(self, content: str):
        self.__log_queue.put((self.__print, [content]))

    # function to add print error on log queue
    def print_err(self, err: str):
        self.__log_queue.put((self.__print_err, [err]))

    # function to add print connection on log queue
    def print_conn(self, log: str):
        self.__log_queue.put((self.__print_conn, [log]))
