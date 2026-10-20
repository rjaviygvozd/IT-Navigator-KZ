"""Minimal HTTP listener required for Render web services."""
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/', '/health'):
            data=b'IT Navigator KZ process is running'
            self.send_response(200)
            self.send_header('Content-Type','text/plain; charset=utf-8')
            self.send_header('Content-Length',str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)
    def log_message(self, *_):
        pass

def start_health_server():
    port=int(os.environ.get('PORT','10000'))
    server=ThreadingHTTPServer(('0.0.0.0',port),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return server
