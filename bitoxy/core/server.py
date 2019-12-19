import socket
import threading


class Server:
    __server_socket = None
    __address = None
    __port = None
    __timeout = 1

    def __init__(self, address, port):
        self.__address = address
        self.__port = port

    #####################################
    # PRIVATE METHODS
    #####################################

    # handle to change a request
    @staticmethod
    def __req_handler(buffer):
        return buffer

    # handle to change a response
    @staticmethod
    def __resp_handler(buffer):
        return buffer

    # function to print hex dump of buffer
    @staticmethod
    def __hex_dump(buffer, length=16):
        result = []
        buffer = str(buffer)
        print(buffer)
        # bytes char 4 if unicode else 2
        # digits = 4 if isinstance(buffer, str) else 2
        for i in range(0, len(buffer), length):
            row = buffer[i:i+length]
            hexa = ' '.join(["%0*X" % (4, ord(char)) for char in row])
            text = ''.join([char if 0x20 <= ord(char) < 0x7F else b'.' for char in row])
            result.append("%04X\t%-*s\t%s" % (i, length*5, hexa, text))

        print('\n'.join(result))

    # function to get remote address and port
    @staticmethod
    def __get_remote(request):
        # convert binary to string
        request = str(request)
        # get url
        url = request.split('\n')[0].split(' ')[1]
        # find pos of ://
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
            port = 80
            address = temp[:address_pos]
        else:
            # specific port
            port = int((temp[(port_pos + 1):])[:address_pos - port_pos - 1])
            address = temp[:port_pos]
        return address, port

    # function to read buffer from connection
    def __receive_from(self, conn):
        buffer = b''
        # set timeout
        conn.settimeout(self.__timeout)

        # read from socket buffer
        try:
            while 1:
                data = conn.recv(1024)
                if not data:
                    break
                buffer += data
        except KeyboardInterrupt:
            print("[!!] Keyboard interrupt. Exit")
            try:
                conn.shutdown(socket.SHUT_RDWR)
                conn.close()
            except IndexError:
                pass
            self.__server_socket.shutdown(socket.SHUT_RDWR)
            self.__server_socket.close()
            exit()
        except Exception as e:
            peer = conn.getpeername()
            print('[!!] Fail receive data from %s:%d' % (peer[0], peer[1]))
            print('[!!] Caught exception: ' + str(e))
        return buffer

    # function to manage connection with client
    def __proxy_handler(self, cli_socket):
        # loop to route requests and responses
        # between client and remote host
        remote_host = None
        cli_host = cli_socket.getpeername()[0]
        cli_port = cli_socket.getpeername()[1]
        while 1:
            # receive data from client
            local_buffer = self.__receive_from(cli_socket)
            if len(local_buffer):
                print('[=>] Received %d bytes from %s:%d' % (
                    len(local_buffer),
                    cli_host,
                    cli_port
                ))
                self.__hex_dump(local_buffer)

                # change request with handler
                local_buffer = self.__req_handler(local_buffer)

                # get host and port remote
                remote_host, remote_port = self.__get_remote(local_buffer)

            # send data at remote host
            remote_buffer = ''
            if remote_host is not None:
                remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote_socket.connect((remote_host, remote_port))
                remote_socket.sendall(local_buffer)
                print('[=>] Sent request to %s:%d' % (remote_host, remote_port))

                # receive response from remote
                remote_buffer = self.__receive_from(remote_socket)
                if len(remote_buffer):
                    print("[<=] Received %d bytes from %s:%d" % (len(remote_buffer), remote_host, remote_port))
                    self.__hex_dump(remote_buffer)
                    # change response with handler
                    remote_buffer = self.__resp_handler(remote_buffer)
                    # send response to client
                    print('[<=] Send response to %s:%d' % (cli_host, cli_port))
                    cli_socket.sendall(remote_buffer)

            # if there are no other data close the connections
            if not (len(remote_buffer) or len(remote_buffer)):
                try:
                    cli_socket.shutdown(socket.SHUT_RDWR)
                    cli_socket.close()
                except IndexError:
                    pass
                try:
                    remote_socket.shutdown(socket.SHUT_RDWR)
                    remote_socket.close()
                except IndexError:
                    pass
                print('[*] No more data. Closing connections')
                print()
                break

    #####################################
    # PUBLIC METHODS
    #####################################

    # method to start loop server
    def start_server(self):
        # create socket and start listen to it
        self.__server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.__server_socket.bind((self.__address, self.__port))
        except Exception as e:
            print('[!!] Fail to listen on %s:%d' % (self.__address, self.__port))
            print('[!!] Caught a exception ' + str(e))
            self.__server_socket.shutdown(socket.SHUT_RDWR)
            self.__server_socket.close()
            exit(-1)

        # start listen and loop server
        print('[*] Start listen on %s:%d' % (self.__address, self.__port))
        self.__server_socket.listen()
        while 1:
            try:
                cli_socket, cli_address = self.__server_socket.accept()
                # print connection info
                print()
                print('[=>] Incoming connection from %s:%d' % (cli_address[0], cli_address[1]))

                # start thread to communicate with client and remote host
                proxy_thread = threading.Thread(target=self.__proxy_handler, args=[cli_socket])
                proxy_thread.start()
            except KeyboardInterrupt:
                print("[!!] Keyboard interrupt. Exit")
                self.__server_socket.shutdown(socket.SHUT_RDWR)
                self.__server_socket.close()
                exit()
            except Exception as e:
                print('[!!] Caught a exception on Bitoxy: ' + str(e))
                self.__server_socket.shutdown(socket.SHUT_RDWR)
                self.__server_socket.close()
                exit(-1)
