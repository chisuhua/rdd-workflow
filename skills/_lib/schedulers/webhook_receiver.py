"""WebhookReceiver — minimal HTTP server that receives webhook POSTs and queues events."""
from __future__ import annotations
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional

from skills._lib.loop.event_queue import EventQueue


class _WebhookHandler(BaseHTTPRequestHandler):
    queue: EventQueue = None
    on_fire: Callable = None

    def do_POST(self):  # noqa: N802 — http.server convention
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {"raw": body}
        # Path like /webhook/<name> — extract trigger name
        parts = self.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "webhook":
            payload["trigger_name"] = parts[1]
        else:
            payload["trigger_name"] = "anonymous"
        if self.queue.push("webhook", payload):
            if self.on_fire:
                self.on_fire(payload.get("trigger_name", "anonymous"))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, format, *args):  # noqa: A002
        # Suppress default access logs to keep stdout clean
        pass


class WebhookReceiver:
    """Runs a tiny HTTP server in a background thread to receive webhooks."""

    def __init__(self, event_queue: EventQueue, on_fire: Callable[[str], None],
                 host: str = "127.0.0.1", port: int = 9090):
        self.queue = event_queue
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        _WebhookHandler.queue = event_queue
        _WebhookHandler.on_fire = on_fire

    def start(self) -> bool:
        """Start the server. Returns False if port already in use."""
        try:
            self._server = HTTPServer((self.host, self.port), _WebhookHandler)
        except OSError:
            return False
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="webhook", daemon=True
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
