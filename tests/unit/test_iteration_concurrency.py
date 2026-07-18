"""Concurrency tests for iteration.py — locks prevent lost-update bugs.

The M1 Oracle finding: iteration.save() previously had no lock, so two
hooks both running load→mutate→save in parallel could overwrite each
other (the second save clobbers the first's mutations, even for
DIFFERENT change entries). These tests verify the lock prevents this.

Strategy: spawn N threads, each adding a distinct change to iteration.json.
Without the lock, the final state would be missing entries. With the
lock, all N entries must be present.
"""
import os
import threading
import pytest

from skills._lib import iteration as it
from skills._lib.core.lock import LockTimeout


@pytest.fixture
def project_root(tmp_path):
    (tmp_path / ".rddf" / "state").mkdir(parents=True)
    return str(tmp_path)


class TestSerialWrites:
    """Two threads, two distinct changes — both must persist."""

    def test_concurrent_writes_no_lost_updates(self, project_root):
        # Seed with empty state
        it.save(project_root, it.create_empty("v2.1"))

        # Each thread adds a distinct change
        def worker(change_name: str):
            data = it.load(project_root)
            data = it.add_or_update_change(
                data, name=change_name, status="proposed",
                phase="v2.1", category="test",
            )
            it.save(project_root, data)

        threads = [
            threading.Thread(target=worker, args=(f"change-{i}",))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 10 changes must be present (no lost updates)
        loaded = it.load(project_root)
        names = sorted(c["name"] for c in loaded["changes"])
        assert names == [f"change-{i}" for i in range(10)]

    def test_concurrent_different_change_entries(self, project_root):
        """The lost-update bug specifically targets DIFFERENT entries —
        two writers each touch their own change name."""
        it.save(project_root, it.create_empty())

        def worker_a():
            data = it.load(project_root)
            data = it.add_or_update_change(data, name="a", status="proposed")
            it.save(project_root, data)

        def worker_b():
            data = it.load(project_root)
            data = it.add_or_update_change(data, name="b", status="proposed")
            it.save(project_root, data)

        # Run many iterations to amplify race window
        for _ in range(20):
            t1 = threading.Thread(target=worker_a)
            t2 = threading.Thread(target=worker_b)
            t1.start(); t2.start()
            t1.join(); t2.join()

        # Both a and b must always be present
        loaded = it.load(project_root)
        names = {c["name"] for c in loaded["changes"]}
        assert "a" in names
        assert "b" in names

    def test_lock_timeout_raises_lock_timeout(self, project_root):
        """If a writer holds the lock past _LOCK_TIMEOUT, the next save raises."""
        from skills._lib import iteration as it_mod
        # Acquire the lock externally and hold it
        lock_path = os.path.join(project_root, ".rddf", "state", "iteration.json") + ".lock"
        # Patch the lock timeout to be tiny so the test is fast
        original = it_mod._LOCK_TIMEOUT
        it_mod._LOCK_TIMEOUT = 0.1
        try:
            from skills._lib.core.lock import FileLock
            with FileLock(lock_path, timeout=1.0):
                # Now try to save — should time out
                data = it.create_empty()
                with pytest.raises(LockTimeout):
                    it.save(project_root, data)
        finally:
            it_mod._LOCK_TIMEOUT = original


class TestLockFileIsolated:
    """Different projects must use different lock files."""

    def test_lock_files_per_project_root(self, tmp_path):
        # Two projects under different roots
        proj_a = tmp_path / "proj_a" / ".rddf" / "state"
        proj_b = tmp_path / "proj_b" / ".rddf" / "state"
        proj_a.mkdir(parents=True)
        proj_b.mkdir(parents=True)

        # Hold lock on proj_a
        from skills._lib.core.lock import FileLock
        lock_a = proj_a / "iteration.json.lock"
        with FileLock(str(lock_a), timeout=1.0):
            # Save to proj_b must still succeed
            data = it.create_empty("a")
            it.save(str(tmp_path / "proj_b"), data)

        loaded = it.load(str(tmp_path / "proj_b"))
        assert loaded["current_phase"] == "a"