import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('KeepAliveServer')

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Bot is running!')

    def log_message(self, format, *args):
        return  # Suppress HTTP request logs

def run_server():
    port = int(os.getenv('PORT', 8080))  # Use Render’s assigned port
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    logger.info(f"Starting keep-alive server on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    logger.info("Starting standalone keep-alive server")
    run_server()
