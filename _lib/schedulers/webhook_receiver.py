"""WebhookReceiver — minimal HTTP server that receives webhook POSTs and queues events."""
from __future__ import annotations
import hashlib
import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional

from skills._lib.loop.event_queue import EventQueue


def verify_signature(secret: str, signature: str, payload: bytes,
                     digestmod=hashlib.sha256) -> bool:
    """Verify HMAC-SHA256 signature (format: 'sha256=<hex>').

    An empty/missing signature is always rejected (fail closed).
    """
    if not secret or not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), payload, digestmod).hexdigest()
    provided = signature[len("sha256="):]
    return hmac.compare_digest(expected, provided)


class _WebhookHandler(BaseHTTPRequestHandler):
    queue: EventQueue = None
    on_fire: Callable = None
    secret: Optional[str] = None

    def do_POST(self):  # noqa: N802 — http.server convention
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        raw_body = body

        # HMAC verification when a secret is configured (fail closed).
        if self.secret:
            provided = self.headers.get("X-Hub-Signature", "")
            if not verify_signature(self.secret, provided, raw_body):
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok":false,"error":"invalid-signature"}')
                return
        try:
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except json.JSONDecodeError:
            payload = {"raw": raw_body.decode("utf-8")}
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
                 host: str = "127.0.0.1", port: int = 9090,
                 secret: Optional[str] = None):
        self.queue = event_queue
        self.host = host
        self.port = port
        self.secret = secret
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        _WebhookHandler.queue = event_queue
        _WebhookHandler.on_fire = on_fire
        _WebhookHandler.secret = secret

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
