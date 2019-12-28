import socket
import ssl


# function that generate and return the socket
def get_bind_socket(address: tuple, ssl_wrap=False, cert_file=None, key_file=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    if ssl_wrap:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        return context.wrap_socket(sock, server_side=True)
    return sock


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
