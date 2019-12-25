from .proxy_thread import ProxyThread
from ..controllers.fake_ssl_factory import FakeSslFactory
from ..utils.functions import decode_buffer, bypass_error
from ..utils.socket import close_socket_pass_exc, send_404_and_close
from ..model.fake_ssl_proxy import FakeSslProxy
from traceback import format_exc
from time import sleep


class SslProxyThread(ProxyThread):

    def __init__(self, cli_socket, cli_address, server_socket):
        ProxyThread.__init__(self, cli_socket, cli_address, server_socket)
        self.__fake_ssl_factory = FakeSslFactory()

    #####################################
    # PRIVATE METHODS
    #####################################

    # handler to change a request
    def __req_handler(self, buffer: bytes) -> bytes:
        return buffer

    # handler to change a response
    def __resp_handler(self, buffer: bytes) -> bytes:
        return buffer

    # function to wait the ready of fake ssl server
    @staticmethod
    def __wait_fake_ssl(fake_ssl_server: FakeSslProxy):
        fail = 0
        while not fake_ssl_server.ready:
            fail += 1
            if fail > 100:
                raise Exception("Wait fake SSL server fail too many time")
            sleep(0.1)

    # method to manage the negotiation with client
    def _client_negotiation(self):
        self._logger.print('############ START CLIENT NEGOTIATION ############')
        fail = 0
        while 1:
            # receive data from client
            local_buffer = self._receive_from(self._cli_socket, self._cli_address, 32)

            # if client is disconnect close connection and return
            if isinstance(local_buffer, bool) and not local_buffer:
                try:
                    self._cli_socket.close()
                except Exception:
                    pass
                out = "[!!] Client %s:%d is disconnected\n" % self._cli_address
                out += '############ END CONNECTION ############\n'
                self._logger.print(out)
                raise Exception("Client disconnected")

            if len(local_buffer):
                # log request
                # self._logger.log_buffer(cli_address, local_buffer, True)

                # if request type isn't CONNECT send bad request code
                if decode_buffer(local_buffer)[:7] != 'CONNECT':
                    self._cli_socket.sendall(b'HTTP/1.1 400 Bad Request\r\n\r\n')
                    raise Exception("Error while negotiation with the client. Bad request from client!!!")

                self._logger.print('[*] CONNECT request from %s:%d' % self._cli_address)
                # change request with handler
                local_buffer = self.__req_handler(local_buffer)

                # get host and port remote
                remote_address = self._get_remote_address(local_buffer)
                try:
                    remote_socket = self._get_remote_socket(remote_address, True)
                    remote_socket.close()
                except Exception as e:
                    send_404_and_close(self._cli_socket)
                    self._logger.print_err("[!!] Error while get remote socket: %s" % str(e))
                    return False

                # create a socket with fake ssl server
                fake_ssl_server = self.__fake_ssl_factory.get_fake_ssl(remote_address)
                # send negotiation confirm
                conf_buff = b'HTTP/1.1 200 Connection established\r\n\r\n'
                self._logger.print('[*] Send confirm negotiation at %s:%d' % self._cli_address)
                # self._logger.log_buffer((self._address, self._port), conf_buff, False)
                self._cli_socket.sendall(conf_buff)

                self._logger.print('############ END CLIENT NEGOTIATION ############\n')
                return fake_ssl_server  # , remote_address
            # increment fails and check max
            fail += 1
            if fail >= self._max_fails:
                raise Exception("Error while negotiation with the client. Too many fails!!!")

    #####################################
    # PUBLIC METHODS
    #####################################

    def run(self) -> None:
        try:
            # cli_host, cli_port = cli_socket.getpeername()

            # negotiation with client
            fake_ssl_server = self._client_negotiation()
            # if negotiation failed return
            if isinstance(fake_ssl_server, bool) and not fake_ssl_server:
                return

            # count fail
            fail = 0

            self.__wait_fake_ssl(fake_ssl_server)
            fake_ssl_address = fake_ssl_server.get_address()
            fake_ssl_socket = self._get_remote_socket(fake_ssl_address)
        except Exception as e:
            send_404_and_close(self._cli_socket)
            out = '' if bypass_error(e) else format_exc()
            out += "[!!] Caught a exception on proxy: %s" % str(e)
            self._logger.print_err(out)
            return

        # loop to route requests and responses
        # between client and fake ssl host
        while 1:
            # receive data from client
            local_buffer = self._receive_from(self._cli_socket, self._cli_address)

            # if client is disconnect close connection and return
            if isinstance(local_buffer, bool) and not local_buffer:
                close_socket_pass_exc(self._cli_socket)
                close_socket_pass_exc(fake_ssl_socket)
                fake_ssl_server.shutdown()
                out = "[!!] Client %s:%d is disconnected\n" % self._cli_address
                out += '############ END CONNECTION ############\n'
                self._logger.print(out)
                return

            if len(local_buffer):
                fail = 0
                # send request to fake ssl server
                fake_ssl_socket.sendall(local_buffer)

            # receive response from remote
            remote_buffer = self._receive_from(fake_ssl_socket, fake_ssl_address)

            # if remote is disconnect close connection and return
            if isinstance(remote_buffer, bool) and not remote_buffer:
                close_socket_pass_exc(self._cli_socket)
                close_socket_pass_exc(fake_ssl_socket)
                fake_ssl_server.shutdown()
                out = "[!!] Fake server is disconnected\n"
                out += '############ END CONNECTION ############\n'
                self._logger.print(out)
                return

            if len(remote_buffer):
                fail = 0
                # send response to client
                self._cli_socket.sendall(remote_buffer)

            # check len of buffers
            if not (len(local_buffer) or len(remote_buffer)):
                fail += 1
                # if fails too many times close connections
                if fail >= self._max_fails:
                    out = "[!!] Fails to many times!!! Close connection with %s:%d client\n" % self._cli_address
                    out += '############ END CONNECTION ############\n'
                    self._logger.print_err(out)
                    close_socket_pass_exc(self._cli_socket)
                    close_socket_pass_exc(fake_ssl_socket)
                    fake_ssl_server.shutdown()
                    break
