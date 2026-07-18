"""GitHookListener — polls git log for new commits and branch/tag changes."""
from __future__ import annotations
import subprocess
import threading
import time
from typing import Callable, Optional

from skills._lib.loop.event_queue import EventQueue


class GitHookListener:
    """Polls git history at fixed interval; emits git events for new commits/branches/tags."""

    def __init__(self, event_queue: EventQueue, on_fire: Callable[[str], None],
                 poll_interval: float = 60.0, repo_path: str = "."):
        self.queue = event_queue
        self.on_fire = on_fire
        self.poll_interval = poll_interval
        self.repo_path = repo_path
        self._last_sha = self._current_head()
        self._last_branches = self._list_branches()
        self._last_tags = self._list_tags()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _run(self, args: list) -> str:
        try:
            r = subprocess.run(
                ["git"] + args, cwd=self.repo_path,
                capture_output=True, text=True, timeout=10,
            )
            return r.stdout.strip() if r.returncode == 0 else ""
        except (subprocess.SubprocessError, OSError):
            return ""

    def _current_head(self) -> str:
        return self._run(["rev-parse", "HEAD"])

    def _list_branches(self) -> set:
        out = self._run(["branch", "--list"])
        return {b.strip().lstrip("* ").strip() for b in out.splitlines() if b.strip()}

    def _list_tags(self) -> set:
        out = self._run(["tag", "--list"])
        return {t.strip() for t in out.splitlines() if t.strip()}

    def start(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop, name="git-hook", daemon=True
            )
            self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            current = self._current_head()
            if current and current != self._last_sha:
                if self.queue.push("git", {"sha": current, "prev": self._last_sha}):
                    self.on_fire(current)
                self._last_sha = current
            current_branches = self._list_branches()
            new_branches = current_branches - self._last_branches
            for branch in new_branches:
                if self.queue.push("git", {"branch": branch, "event": "created"}):
                    self.on_fire(branch)
            self._last_branches = current_branches
            current_tags = self._list_tags()
            new_tags = current_tags - self._last_tags
            for tag in new_tags:
                if self.queue.push("git", {"tag": tag, "event": "tagged"}):
                    self.on_fire(tag)
            self._last_tags = current_tags
            self._stop.wait(timeout=self.poll_interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
