from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('KeepAliveServer')

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
        return  # Suppress logging of HTTP requests

def run_server():
    port = int(os.getenv("PORT", 10000))  # Default to 10000, but use Render's assigned port if available
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    logger.info(f"Starting keep-alive server on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    logger.info("Starting standalone keep-alive server")
    run_server()
