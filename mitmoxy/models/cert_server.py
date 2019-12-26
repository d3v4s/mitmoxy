from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread


class CertServer(Thread):
    __cert_path = None

    def __init__(self, address, port, cert_path):
        Thread.__init__(self)
        self.__address = address
        self.__port = port
        CertServer.__cert_path = cert_path

    # method to get bytes of certificate
    @staticmethod
    def get_certificate_bytes() -> bytes:
        file = open(CertServer.__cert_path, 'rb')
        res = file.read()
        file.close()
        return res

    def run(self) -> None:
        http_server = HTTPServer((self.__address, self.__port), self.CertServerHandler)
        http_server.serve_forever()

    class CertServerHandler(BaseHTTPRequestHandler):

        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'application/x-x509-ca-cert')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(CertServer.get_certificate_bytes())
