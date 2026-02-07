"""Lightweight REST API stub for the application server."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json


class APIHandler(BaseHTTPRequestHandler):
    """Handle API requests."""

    def do_GET(self):
        """Return API status."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {
            'status': 'ok',
            'service': 'api',
            'version': '1.0.0',
        }
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8080), APIHandler)
    server.serve_forever()
