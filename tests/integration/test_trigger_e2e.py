"""End-to-end integration tests for v3-scheduled-triggers.

Tests the full trigger lifecycle: registration -> persistence -> dedup -> rate-limit -> fire.
"""
import json
import os
import time
import tempfile
from datetime import datetime
from pathlib import Path

from skills._lib.triggers import Trigger, TriggerManager
from skills._lib.trigger_registry import TriggerRegistry
from skills._lib.rate_limiter import TokenBucket
from skills._lib.event_queue import EventQueue
from skills._lib.schedulers.cron_scheduler import validate_cron, next_fire_time


def test_full_trigger_lifecycle_cron():
    """Cron trigger: register -> save -> load -> fire -> rate-limit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Register
        reg = TriggerRegistry(project_root=tmpdir, path="triggers.json")
        mgr = TriggerManager()
        t = Trigger(type="cron", config={"expression": "0 * * * *"}, rate_limit=2)
        assert mgr.register(t) == t.id
        assert len(mgr.triggers) == 1

        # 2. Save & reload
        reg.save(mgr)
        assert os.path.isfile(os.path.join(tmpdir, "triggers.json"))
        mgr2 = reg.load()
        assert len(mgr2.triggers) == 1
        loaded = mgr2.triggers[0]
        assert loaded.type == "cron"
        assert loaded.config["expression"] == "0 * * * *"

        # 3. Fire (subject to rate limit)
        assert mgr2.fire(loaded.id) is True  # 1st
        assert mgr2.fire(loaded.id) is True  # 2nd
        assert mgr2.fire(loaded.id) is False  # 3rd rate-limited

        # 4. Persist updated state
        reg.save(mgr2)
        mgr3 = reg.load()
        # Rate limit state should be persisted
        loaded2 = mgr3.triggers[0]
        assert loaded2.last_fire_at is not None


def test_full_trigger_lifecycle_dedup():
    """Two identical triggers should dedup to one."""
    mgr = TriggerManager()
    t1 = Trigger(type="git", config={"branch": "main"})
    t2 = Trigger(type="git", config={"branch": "main"})
    id1 = mgr.register(t1)
    id2 = mgr.register(t2)
    assert id1 == id2  # deduped
    assert len(mgr.triggers) == 1


def test_trigger_event_queue_integration():
    """EventQueue receives events, drains them, dedup works."""
    q = EventQueue()
    assert q.push("git", {"sha": "abc123"}) is True
    assert q.push("git", {"sha": "abc123"}) is False  # dup
    assert q.push("git", {"sha": "def456"}) is True  # new
    events = q.drain()
    assert len(events) == 2
    assert events[0]["payload"]["sha"] == "abc123"
    assert events[1]["payload"]["sha"] == "def456"


def test_cron_expression_validation():
    """Standard cron expressions validate, invalid ones don't."""
    valid = ["0 * * * *", "*/5 * * * *", "0 0 * * 0", "0 2 * * 1-5"]
    for expr in valid:
        assert validate_cron(expr) is True, f"{expr!r} should be valid"
    invalid = ["not a cron", "", "99 * * * *", "* * *", "0 25 * * *"]
    for expr in invalid:
        assert validate_cron(expr) is False, f"{expr!r} should be invalid"


def test_cron_next_fire_calculation():
    """next_fire_time returns correct next datetime."""
    base = datetime(2026, 6, 1, 10, 30, 0)
    # "0 * * * *" = top of every hour
    nxt = next_fire_time("0 * * * *", after=base)
    assert nxt == datetime(2026, 6, 1, 11, 0, 0)


def test_token_bucket_persistence_roundtrip():
    """Bucket state survives JSON serialization."""
    b = TokenBucket.from_rate_limit(120)  # 120/hour
    b.consume(50)
    d = b.to_dict()
    b2 = TokenBucket.from_dict(d)
    assert abs(b2.tokens - b.tokens) < 0.01
    assert b2.capacity == 120.0


def test_crash_recovery_via_registry():
    """Trigger state survives registry reload (crash recovery scenario)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Pre-crash state: 1 trigger, 5 fires already done
        reg = TriggerRegistry(project_root=tmpdir, path="triggers.json")
        mgr = TriggerManager([Trigger(type="cron", config={"expression": "0 * * * *"}, rate_limit=5)])
        for _ in range(5):
            mgr.fire(mgr.triggers[0].id)
        last_fire_before = mgr.triggers[0].last_fire_at
        bucket_before = mgr.triggers[0].token_bucket
        reg.save(mgr)

        # Simulate crash + restart
        mgr2 = reg.load()
        loaded = mgr2.triggers[0]
        # last_fire_at is preserved
        assert loaded.last_fire_at == last_fire_before
        # bucket state is preserved
        assert abs(loaded.token_bucket - bucket_before) < 0.01


def test_multiple_trigger_types_coexist():
    """cron + fs + git + webhook can all be in same registry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = TriggerRegistry(project_root=tmpdir, path="triggers.json")
        mgr = TriggerManager([
            Trigger(type="cron", config={"expression": "0 * * * *"}),
            Trigger(type="fs", config={"path": "/tmp"}),
            Trigger(type="git", config={"branch": "main"}),
            Trigger(type="webhook", config={"trigger_name": "deploy"}),
        ])
        reg.save(mgr)
        mgr2 = reg.load()
        types = sorted(t.type for t in mgr2.triggers)
        assert types == ["cron", "fs", "git", "webhook"]


def test_disabled_trigger_doesnt_fire():
    """enabled=False triggers are skipped by register() and fire()."""
    mgr = TriggerManager()
    t = Trigger(type="cron", config={"expression": "0 * * * *"}, enabled=False)
    mgr.register(t)
    # Disabled triggers are not added to the manager's trigger list
    assert len(mgr.triggers) == 0
    # Even with rate-limit budget, disabled triggers don't fire (not in list)
    assert mgr.fire(t.id) is False


def test_deduplicate_events_filters_by_payload():
    """deduplicate_events only returns triggers whose config matches the payload."""
    mgr = TriggerManager([
        Trigger(type="git", config={"branch": "main"}, enabled=True),
        Trigger(type="git", config={"branch": "dev"}, enabled=True),
    ])
    matches = mgr.deduplicate_events("git", {"branch": "main"})
    assert len(matches) == 1
    assert mgr.triggers[0].id in matches


def test_legacy_unregistered_triggers_compatible():
    """Triggers without going through register() still load from JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Manually write a triggers.json without using TriggerManager.register
        data = {
            "version": 1,
            "triggers": [
                {
                    "id": "manual_1",
                    "type": "cron",
                    "config": {"expression": "*/10 * * * *"},
                    "rate_limit": 60,
                    "enabled": True,
                    "created_at": "2026-01-01T00:00:00",
                    "last_fire_at": None,
                    "token_bucket": 0.0,
                }
            ]
        }
        path = os.path.join(tmpdir, "triggers.json")
        with open(path, "w") as f:
            json.dump(data, f)

        reg = TriggerRegistry(project_root=tmpdir, path="triggers.json")
        mgr = reg.load()
        assert len(mgr.triggers) == 1
        assert mgr.triggers[0].id == "manual_1"


def test_atomic_write_no_temp_leftover():
    """After save(), no .tmp files remain."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = TriggerRegistry(project_root=tmpdir, path="triggers.json")
        for i in range(5):
            mgr = TriggerManager([Trigger(type="cron", config={"i": i})])
            reg.save(mgr)
            # After each save, no temp file should exist
            tmps = list(Path(tmpdir).glob("triggers.*.tmp"))
            assert len(tmps) == 0, f"Found leftover temp: {tmps}"
