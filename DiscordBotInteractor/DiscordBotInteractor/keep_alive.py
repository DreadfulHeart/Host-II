import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

logger = logging.getLogger('BotAutomation.KeepAlive')

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Bot is running!')

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def log_message(self, format, *args):
        return 

def run_server():
    port = int(os.getenv("PORT", 10000))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    logger.info(f"Starting keep-alive server on port {port}")
    httpd.serve_forever()

def start_server():
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    return server_thread
