"""Tests for FileLock — fcntl-based exclusive/shared file lock with timeout."""
import os
import tempfile
import threading
import time
import pytest
from skills._lib.core.lock import FileLock, LockTimeout


@pytest.fixture
def lock_path(tmp_path):
    return str(tmp_path / "test.lock")


def test_context_manager_acquires_and_releases(lock_path):
    """Lock is held inside `with` block, released on exit."""
    lock = FileLock(lock_path, timeout=2.0)
    with lock:
        assert lock.is_held is True
    # release() unlocks the fcntl advisory lock but does NOT unlink the file —
    # verify the lock is no longer held, and that re-acquire succeeds instantly.
    assert lock.is_held is False
    with FileLock(lock_path, timeout=0.1) as re_acquired:
        assert re_acquired.is_held is True


def test_exclusive_lock_blocks_second_acquire(lock_path):
    """Second acquire on same file within timeout must raise LockTimeout."""
    with FileLock(lock_path, timeout=0.5) as first:
        with pytest.raises(LockTimeout):
            with FileLock(lock_path, timeout=0.5, exclusive=True):
                pass


def test_concurrent_threads_serialize(lock_path):
    """Two threads with the same lock must execute serially, not in parallel."""
    order = []
    barrier = threading.Barrier(2)

    def worker(name, hold_time):
        barrier.wait()  # <-- BEFORE the lock
        with FileLock(lock_path, timeout=2.0):
            order.append(f"{name}-enter")
            time.sleep(hold_time)
            order.append(f"{name}-exit")

    t1 = threading.Thread(target=worker, args=("A", 0.1))
    t2 = threading.Thread(target=worker, args=("B", 0.1))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    # Exactly one of [A-enter, B-enter] must be followed by its own -exit before the other -enter
    assert order in [
        ["A-enter", "A-exit", "B-enter", "B-exit"],
        ["B-enter", "B-exit", "A-enter", "A-exit"],
    ], f"Locks did not serialize: {order}"


def test_lock_released_on_exception(lock_path):
    """Lock must be released even when `with` block raises."""
    try:
        with FileLock(lock_path, timeout=0.5):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    # Should be able to acquire again immediately
    with FileLock(lock_path, timeout=0.5) as lock:
        assert lock.is_held


def test_is_held_property(lock_path):
    """`is_held` returns True inside the block, False before/after."""
    lock = FileLock(lock_path, timeout=0.5)
    assert lock.is_held is False
    with lock:
        assert lock.is_held is True
    assert lock.is_held is False


def test_lock_timeout_raises_locktimeout(lock_path):
    """When timeout expires, must raise LockTimeout (not generic Exception)."""
    with FileLock(lock_path, timeout=5.0):
        start = time.time()
        with pytest.raises(LockTimeout):
            with FileLock(lock_path, timeout=0.3):
                pass
        elapsed = time.time() - start
        assert 0.25 < elapsed < 1.0  # timed out around 0.3s
