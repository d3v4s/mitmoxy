import socket
import ssl

from mitmoxy.controllers.logger import Logger
from .proxy import Proxy, decode_buffer


class FakeSslServer(Proxy):
    __max_fails = 50

    def __init__(self, conf_server, conf_log):
        super(FakeSslServer, self).__init__(conf_server, conf_log)
        self._address = self._conf_server['fake-server-address']
        self._port = self._conf_server['fake-server-port']

    #####################################
    # PRIVATE STATIC METHODS
    #####################################

    # function to get remote address and port
    @staticmethod
    def _get_remote_address(request, def_port=80) -> tuple:
        # convert binary to string
        request = decode_buffer(request) if isinstance(request, bytes) else request
        url = None
        # get url
        request = request.split('\n')
        for row in request:
            if row.find("Host: ") >= 0:
                url = row.split(' ')[1]
                url = url.strip(" ")
                url = url.strip('\r\n')


        if url is None:
            raise Exception("Error while get remote address from request")

        # find position of ://
        http_pos = url.find("://")
        # get the rest of url
        temp = url if http_pos == -1 else url[(http_pos + 3):]

        # find the port position
        port_pos = temp.find(":")

        # find end of address
        address_pos = temp.find("/")
        if address_pos == -1:
            address_pos = len(temp)

        if port_pos == -1 or address_pos < port_pos:
            # default port
            port = def_port
            address = temp[:address_pos]
        else:
            # specific port
            port = int((temp[(port_pos + 1):])[:address_pos - port_pos - 1])
            address = temp[:port_pos]
        return address, port

    #####################################
    # PRIVATE METHODS
    #####################################

    # handler to change a request
    def __req_handler(self, buffer: bytes) -> bytes:
        return buffer

    # handler to change a response
    def __resp_handler(self, buffer: bytes) -> bytes:
        return buffer

    #####################################
    # PROTECTED METHODS
    #####################################

    # method that generate and return the socket
    def _get_socket(self) -> ssl.SSLSocket:
        sock = self._create_bind_socket((self._address, self._port))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=self._conf_server['cert-file'], keyfile=self._conf_server['key-file'])
        return context.wrap_socket(sock, server_side=True)

    # method to get server name
    def _get_server_name(self):
        return 'Fake SSL Server'

    # function to manage connection with client
    def _proxy_handler(self, cli_socket: ssl.SSLSocket):
        # get host and port of client
        cli_host, cli_port = cli_socket.getpeername()
        # negotiation with client
        # remote_socket, remote_address = self._client_negotiation(cli_socket)
        # cli_socket.do_handshake()
        # remote_host, remote_port = remote_address
        # init the logger
        logger = Logger(self._conf_log)
        # count fail
        fail = 0
        remote_address = None
        remote_socket = None
        # loop to route requests and responses
        # between client and remote host
        while 1:
            # receive data from client
            local_buffer = self._receive_from(cli_socket)
            # if receive data from client
            if len(local_buffer):
                fail = 0

                # change reques with handler and log it
                local_buffer = self.__req_handler(local_buffer)
                logger.log_buffer((cli_host, cli_port), local_buffer, True)

                if remote_address is None:
                    remote_address = self._get_remote_address(local_buffer, 443)
                    # remote_host, remote_port = remote_address
                    remote_socket = self._get_remote_socket(remote_address, True)

                # send data at remote host
                remote_socket.sendall(local_buffer)

            # receive response from remote
            remote_buffer = self._receive_from(remote_socket)
            # if receive data from remote
            if len(remote_buffer):
                fail = 0

                # change response with handler and log it
                remote_buffer = self.__resp_handler(remote_buffer)
                logger.log_buffer(remote_address, remote_buffer, False)
                # logger.print('[<=] Send response to %s:%d' % (cli_host, cli_port))

                # send response to client
                cli_socket.sendall(remote_buffer)

            # check len of buffers
            if not (len(local_buffer) or len(remote_buffer)):
                fail += 1
                # if fails too many times close connections
                if fail >= self.__max_fails:
                    out = "[!!] Fails to many times!!! Close connection with %s:%d client\n" % (cli_host, cli_port)
                    out += '############ END CONNECTION ############\n'
                    logger.print(out)
                    self._send_400_and_close(cli_socket)
                    try:
                        remote_socket.close()
                    except Exception:
                        pass
                    break
