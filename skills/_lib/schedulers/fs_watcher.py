"""FileSystemWatcher — polls directory for file modifications using mtime comparison."""
from __future__ import annotations
import os
import threading
import time
from typing import Callable, Optional

from skills._lib.loop.event_queue import EventQueue


class FileSystemWatcher:
    """Polls a directory at fixed interval; emits fs events when mtime changes."""

    def __init__(self, event_queue: EventQueue, on_fire: Callable[[str], None],
                 poll_interval: float = 30.0):
        self.queue = event_queue
        self.on_fire = on_fire
        self.poll_interval = poll_interval
        self._snapshots: dict[str, float] = {}  # path -> mtime
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def snapshot(self, path: str) -> None:
        """Take a baseline snapshot of the directory."""
        self._snapshots[path] = self._latest_mtime(path)

    def _latest_mtime(self, path: str) -> float:
        if not os.path.isdir(path):
            return 0.0
        latest = 0.0
        try:
            for root, _dirs, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        m = os.path.getmtime(fp)
                        if m > latest:
                            latest = m
                    except OSError:
                        pass
        except OSError:
            pass
        return latest

    def watch(self, path: str) -> None:
        """Start watching a path. Takes initial snapshot, then polls for changes."""
        if path not in self._snapshots:
            self.snapshot(path)
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop, name="fs-watcher", daemon=True
            )
            self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            for path in list(self._snapshots.keys()):
                current = self._latest_mtime(path)
                if current > self._snapshots[path]:
                    if self.queue.push("fs", {"path": path}):
                        self.on_fire(path)
                    self._snapshots[path] = current
            self._stop.wait(timeout=self.poll_interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
