"""Standalone mock LLM HTTP server for bats integration tests.

Usage:
    python3 tests/_lib/mock_llm_server.py <port> [mode]

Modes:
    ok    - returns 200 + OpenAI-compatible JSON (default)
    401   - returns 401 Unauthorized
    500   - returns 500 Server Error

Logs to stderr; exit code 0 on SIGTERM, 1 on error.
"""
import http.server
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

MODE = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("MOCK_MODE", "ok")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        _ = self.rfile.read(length)

        if MODE == "401":
            self.send_response(401)
            self.end_headers()
            return
        if MODE == "500":
            self.send_response(500)
            self.end_headers()
            return

        body = {"choices": [{"message": {"content": "[\"ok\"]"}}]}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, *args, **kwargs):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1])
    server = HTTPServer(("127.0.0.1", port), Handler)
    server.serve_forever()
