"""Thread-safe event queue for passing trigger events from background producers to consumers."""
from __future__ import annotations
import queue
import threading
import time
from typing import Optional


class EventQueue:
    """Thread-safe FIFO queue with deduplication by event signature."""

    def __init__(self, max_size: int = 10000):
        self._queue: queue.Queue = queue.Queue(maxsize=max_size)
        self._lock = threading.Lock()
        self._seen_signatures: set = set()
        self._seen_max = 10000

    def push(self, event_type: str, payload: dict) -> bool:
        """Push event. Returns False if duplicate (within dedup window) or queue full."""
        sig = (event_type, tuple(sorted(payload.items())))
        with self._lock:
            if sig in self._seen_signatures:
                return False
            # Bound the dedup window
            if len(self._seen_signatures) >= self._seen_max:
                self._seen_signatures.clear()
            self._seen_signatures.add(sig)
        try:
            self._queue.put_nowait({"type": event_type, "payload": payload, "ts": time.time()})
            return True
        except queue.Full:
            return False

    def pop(self, timeout: float = 0.1) -> Optional[dict]:
        """Pop next event or None on timeout."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain(self) -> list:
        """Drain all pending events (non-blocking)."""
        events = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return events

    def qsize(self) -> int:
        return self._queue.qsize()
