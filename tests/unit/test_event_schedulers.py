"""Unit tests for event_queue + fs_watcher + git_hook + webhook_receiver."""
import os
import time
from skills._lib.event_queue import EventQueue
from skills._lib.schedulers.fs_watcher import FileSystemWatcher
from skills._lib.schedulers.git_hook import GitHookListener
from skills._lib.schedulers.webhook_receiver import WebhookReceiver


def test_event_queue_push_pop():
    q = EventQueue()
    assert q.push("fs", {"path": "/tmp"}) is True
    assert q.qsize() == 1
    e = q.pop(timeout=0.1)
    assert e["type"] == "fs"
    assert e["payload"]["path"] == "/tmp"


def test_event_queue_dedup():
    q = EventQueue()
    assert q.push("git", {"sha": "abc"}) is True
    assert q.push("git", {"sha": "abc"}) is False  # dup
    assert q.qsize() == 1


def test_event_queue_drain():
    q = EventQueue()
    q.push("fs", {"a": 1})
    q.push("fs", {"a": 2})
    events = q.drain()
    assert len(events) == 2


def test_fs_watcher_snapshot(tmp_path):
    q = EventQueue()
    fired = []
    w = FileSystemWatcher(q, on_fire=lambda p: fired.append(p), poll_interval=0.5)
    w.snapshot(str(tmp_path))
    assert str(tmp_path) in w._snapshots
    w.stop()


def test_fs_watcher_detects_new_file(tmp_path):
    q = EventQueue()
    fired = []
    w = FileSystemWatcher(q, on_fire=lambda p: fired.append(p), poll_interval=0.2)
    w.snapshot(str(tmp_path))
    w.watch(str(tmp_path))
    time.sleep(0.1)
    # Create a new file
    (tmp_path / "new.txt").write_text("hello")
    # Wait for poll
    time.sleep(0.5)
    w.stop()
    assert len(fired) >= 1


def test_git_hook_snapshot():
    q = EventQueue()
    fired = []
    h = GitHookListener(q, on_fire=lambda s: fired.append(s), poll_interval=10.0)
    assert h._last_sha != ""  # we're in a git repo
    h.stop()


def test_webhook_receiver_start_stop():
    q = EventQueue()
    fired = []
    r = WebhookReceiver(q, on_fire=lambda n: fired.append(n), port=19090)
    assert r.start() is True
    time.sleep(0.2)
    r.stop()
