"""File-level locking with timeout. Cross-platform where possible.

Uses fcntl on Linux/macOS (POSIX). Provides exclusive (writer) and shared
(reader) lock modes with a configurable timeout. Use as a context manager.
"""
from __future__ import annotations
import os
import time
import fcntl
import errno
from pathlib import Path
from typing import Optional


class LockTimeout(Exception):
    """Raised when a lock acquire exceeds its timeout."""


class FileLock:
    """Exclusive or shared file lock with timeout (fcntl-based).

    Args:
        path: Path to the lock file. Created on first acquire if missing.
        timeout: Seconds to wait for the lock before raising LockTimeout.
            Default 10.0. Use 0.0 for non-blocking.
        exclusive: True for write lock (default), False for shared read lock.

    Example:
        with FileLock("/tmp/state.lock", timeout=5.0):
            # ... critical section ...
            pass
    """

    def __init__(self, path: str, timeout: float = 10.0, exclusive: bool = True):
        self.path = Path(path)
        self.timeout = timeout
        self.exclusive = exclusive
        self._fd: Optional[int] = None
        self._held = False

    @property
    def is_held(self) -> bool:
        return self._held

    def acquire(self) -> None:
        """Acquire the lock. Blocks up to `timeout` seconds, then raises."""
        if self._held:
            raise RuntimeError("Lock already held by this instance")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR, 0o644)

        op = fcntl.LOCK_EX if self.exclusive else fcntl.LOCK_SH
        # Non-blocking when timeout=0, otherwise use blocking call + poll for timeout
        if self.timeout == 0:
            try:
                fcntl.flock(self._fd, op | fcntl.LOCK_NB)
            except OSError as e:
                os.close(self._fd)
                self._fd = None
                if e.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise LockTimeout(f"Lock {self.path} is held by another process") from e
                raise
        else:
            deadline = time.monotonic() + self.timeout
            while True:
                try:
                    fcntl.flock(self._fd, op | fcntl.LOCK_NB)
                    break
                except OSError as e:
                    if e.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                        os.close(self._fd)
                        self._fd = None
                        raise
                    if time.monotonic() >= deadline:
                        os.close(self._fd)
                        self._fd = None
                        raise LockTimeout(
                            f"Timed out after {self.timeout}s waiting for {self.path}"
                        ) from e
                    time.sleep(0.01)  # 10ms poll interval

        self._held = True

    def release(self) -> None:
        """Release the lock. Idempotent — safe to call when not held."""
        if not self._held:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None
            self._held = False

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
