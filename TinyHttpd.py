import sys
import BaseHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler

Handler = SimpleHTTPRequestHandler
Server = BaseHTTPServer.HTTPServer
Protocol = "HTTP/1.1"
Handler.protocol_version = Protocol

if __name__ == '__main__':
    http_server = Server(('0.0.0.0', 80), Handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        pass
    http_server.server_close()
