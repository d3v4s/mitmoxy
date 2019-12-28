from .proxy_thread_abc import ProxyThreadABC
from ..factories.fake_ssl_factory import FakeSslFactory
from ..utils.functions import bypass_error
from ..utils.handlers import *
from ..utils.socket import close_socket_pass_exc, send_404_and_close
from time import sleep
from traceback import format_exc


class ProxyThread(ProxyThreadABC):
    cert_download = False
    cert_address = None
    cert_file_path = None

    def __init__(self, cli_socket, cli_address, server_socket, server_name):
        ProxyThreadABC.__init__(self, cli_socket, cli_address, server_socket, server_name)
        self.__fake_ssl_factory = FakeSslFactory()

    #####################################
    # PRIVATE STATIC METHODS
    #####################################

    # function to wait the ready of fake ssl server
    @staticmethod
    def __wait_fake_ssl(fake_ssl_server):
        fail = 0
        while not fake_ssl_server.ready:
            fail += 1
            if fail > 30:
                raise Exception("Wait fake SSL server fail too many time")
            sleep(0.1)

    #####################################
    # PRIVATE METHODS
    #####################################

    # function to check if is ssl request
    # check if contain CONNECT
    def __is_ssl_req(self, buffer):
        # if client is disconnect close connection and throw a exception
        if isinstance(buffer, bool) and not buffer:
            close_socket_pass_exc(self._cli_socket)
            raise Exception("Client %s:%d disconnected from %s" %
                            (self._cli_address[0], self._cli_address[1], self.name))

        if len(buffer):
            # if request type isn't CONNECT return true
            if buffer[:7] == b'CONNECT':
                return True
        # else return false
        return False

    # method to manage the negotiation with client
    def __client_negotiation(self, buffer):
        try:
            # get host and port remote
            remote_address = self._get_remote_address(buffer)
            remote_socket = self._get_remote_socket(remote_address, True)
            remote_socket.close()
            # send negotiation confirm
            conf_buff = b'HTTP/1.1 200 Connection established\r\n\r\n'
            self._cli_socket.sendall(conf_buff)
            # create a socket with fake ssl server and return it
            return self.__fake_ssl_factory.get_fake_ssl(remote_address, self._cli_address)
        except Exception as e:
            send_404_and_close(self._cli_socket)
            self._logger.print_err("[!!] Error while get remote socket: %s" % str(e))
            return False

    # method to send certificate authority
    def __send_ca(self):
        file = open(self.cert_file_path, 'rb')
        cert_bytes = file.read()
        file.close()
        out = b'HTTP/1.1 200 OK\r\n'
        out += b'Content-Type: application/x-x509-ca-cert\r\n'
        out += b'X-Content-Type-Options: nosniff\r\n\r\n'
        out += cert_bytes
        self._cli_socket.sendall(out)

    # method to mange the http request
    def __http_handle(self, local_buffer):
        # get remote host and port,
        # and create a socket
        self._logger.log_buffer(self._cli_address, local_buffer, True)
        remote_address = self._get_remote_address(local_buffer)

        # if certificate download is active and client require it
        # send certificate, close socket and return
        if self.cert_download and remote_address[0] == 'mitmoxy.crt':
            self.__send_ca()
            close_socket_pass_exc(self._cli_socket)
            close_socket_pass_exc(self._server_socket)
            return

        print("REMOTE: " + str(remote_address))
        remote_socket = self._get_remote_socket(remote_address)
        # init buffer
        remote_buffer = ''
        # loop to route requests and responses
        # between client and remote host
        while 1:
            if len(local_buffer):
                self._logger.log_buffer(self._cli_address, local_buffer, True)

                # change request with handler
                local_buffer = req_handle(local_buffer)

                # send data at remote host
                remote_socket.sendall(local_buffer)

            if remote_socket is not None:
                # receive response from remote
                remote_buffer = self._receive_from(remote_socket, remote_address)
                # if remote is disconnect close connection and return
                if isinstance(remote_buffer, bool) and not remote_buffer:
                    close_socket_pass_exc(self._cli_socket)
                    close_socket_pass_exc(remote_socket)
                    self._logger.print_conn("[!!] Remote %s:%d is disconnected\n" % remote_address)
                    return

                # if have data from remote log it and send response to client
                if len(remote_buffer):
                    self._logger.log_buffer(remote_address, remote_buffer, False)

                    # change response with handler
                    remote_buffer = resp_handle(remote_buffer)

                    # send response to client
                    self._cli_socket.sendall(remote_buffer)

                # receive data from client
                local_buffer = self._receive_from(self._cli_socket, self._cli_address)

                # if client is disconnect close connection and return
                if isinstance(local_buffer, bool) and not local_buffer:
                    close_socket_pass_exc(self._cli_socket)
                    close_socket_pass_exc(remote_socket)
                    self._logger.print_conn("[!!] Client %s:%d is disconnected\n" % self._cli_address)
                    return

            # if there are no other data close the connections
            if not (len(remote_buffer) or len(local_buffer)):
                close_socket_pass_exc(self._cli_socket)
                close_socket_pass_exc(remote_socket)
                self._logger.print_conn(
                    '[*] No more data. Closing connection with client %s:%d\n' % self._cli_address)
                break
        # try:
        # except Exception as e:
        #     close_socket_pass_exc(self._cli_socket)
        #     out = '' if bypass_error(e) else format_exc()
        #     out += "[!!] Caught a exception on %s: %s" % (self.name, str(e))
        #     self._logger.print_err(out)
        #     return

    # method to mange the ssl request
    def __ssl_handle(self, local_buffer):
        try:
            # negotiation with client
            fake_ssl_server = self.__client_negotiation(local_buffer)
            # if negotiation failed return
            if isinstance(fake_ssl_server, bool) and not fake_ssl_server:
                return

            self.__wait_fake_ssl(fake_ssl_server)
            fake_ssl_address = fake_ssl_server.get_address()
            fake_ssl_socket = self._get_remote_socket(fake_ssl_address)

        except Exception as e:
            send_404_and_close(self._cli_socket)
            out = '' if bypass_error(e) else format_exc()
            out += "[!!] Caught a exception on %s: %s" % (self.name, str(e))
            self._logger.print_err(out)
            return

        # count fail
        fail = 0
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
                self._logger.print_conn("[!!] Client %s:%d is disconnected\n" % self._cli_address)
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
                self._logger.print_conn("[!!] Fake server is disconnected\n")
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
                    self._logger.print_err('[!!] %s fails to many times!!!\n'
                                           '[!!] Close connections\n' % self.name)
                    close_socket_pass_exc(self._cli_socket)
                    close_socket_pass_exc(fake_ssl_socket)
                    fake_ssl_server.shutdown()
                    break

    #####################################
    # PUBLIC METHODS
    #####################################

    def run(self) -> None:
        try:
            # receive first data from client
            buffer = self._receive_from(self._cli_socket, self._cli_address, 8)
        except Exception as e:
            send_404_and_close(self._cli_socket)
            out = '' if bypass_error(e) else format_exc()
            out += "[!!] Caught a exception %s: %s" % (self.name, str(e))
            self._logger.print_err(out)
            return

        handle = self.__ssl_handle if self.__is_ssl_req(buffer) else self.__http_handle

        try:
            handle(buffer)
        except Exception as e:
            out = format_exc()
            out += "[!!] Caught a exception on %s: %s\n"\
                   "[!!] Close it...\n" % (self.name, str(e))
            close_socket_pass_exc(self._cli_socket)
            self._logger.print_err(out)
