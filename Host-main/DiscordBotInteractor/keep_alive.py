
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
    
    def log_message(self, format, *args):
        # Suppress logging of HTTP requests
        return

def run_server():
    port = 8080
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    logger.info(f"Starting keep-alive server on port {port}")
    repl_slug = os.getenv('REPL_SLUG', 'unknown')
    repl_owner = os.getenv('REPL_OWNER', 'unknown')
    logger.info(f"Primary URL: https://{repl_slug}.{repl_owner}.repl.co")
    logger.info(f"Alternative URL: https://workspace.{repl_owner}.repl.co")
    httpd.serve_forever()

def start_server():
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True  # So the thread will exit when the main process exits
    server_thread.start()
    return server_thread
