import socket


# function to send 404 code and close socket
def send_400_and_close(sock):
    try:
        sock.sendall(b'HTTP/1.1 400 Bad request\r\n\r\n')
    except Exception:
        pass
    close_socket_pass_exc(sock)


# function to send 404 code and close socket
def send_404_and_close(sock):
    try:
        sock.sendall(b'HTTP/1.1 404 Not found\r\n\r\n')
    except Exception:
        pass
    close_socket_pass_exc(sock)


# function to close the socket and pass the exception
def close_socket_pass_exc(sock):
    try:
        sock.close()
    except Exception:
        pass


# function to bind socket at address
def create_bind_socket(address: tuple):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    return sock
