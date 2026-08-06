"""Unit tests for _lib/triggers.py"""
from skills._lib.triggers import Trigger, TriggerManager


def test_trigger_creation_defaults():
    t = Trigger(type="cron", config={"expression": "0 * * * *"})
    assert t.type == "cron"
    assert t.enabled is True
    assert t.rate_limit == 60
    assert t.id.startswith("trigger_")
    assert t.last_fire_at is None


def test_trigger_to_from_dict():
    t = Trigger(type="fs", config={"path": "/tmp"}, rate_limit=10)
    d = t.to_dict()
    t2 = Trigger.from_dict(d)
    assert t2.id == t.id
    assert t2.type == "fs"
    assert t2.rate_limit == 10


def test_manager_register_dedup():
    m = TriggerManager()
    t1 = Trigger(type="cron", config={"expr": "0 * * * *"})
    t2 = Trigger(type="cron", config={"expr": "0 * * * *"})  # same
    id1 = m.register(t1)
    id2 = m.register(t2)
    assert id1 == id2  # dedup returns existing
    assert len(m.triggers) == 1


def test_manager_unregister():
    m = TriggerManager([Trigger(type="cron", config={"a": 1})])
    assert m.unregister(m.triggers[0].id) is True
    assert m.unregister("nonexistent") is False
    assert len(m.triggers) == 0


def test_manager_deduplicate_events():
    m = TriggerManager([
        Trigger(type="git", config={"branch": "main"}, enabled=True),
        Trigger(type="git", config={"branch": "main"}, enabled=True),
        Trigger(type="git", config={"branch": "dev"}, enabled=True),
    ])
    matches = m.deduplicate_events("git", {"branch": "main"})
    assert len(matches) == 1  # two triggers deduped to 1


def test_manager_fire_records():
    t = Trigger(type="cron", config={"expr": "0 *"})
    m = TriggerManager([t])
    assert m.fire(t.id) is True
    assert m.triggers[0].last_fire_at is not None


from skills._lib.trigger_registry import TriggerRegistry
import json
import os


def test_registry_save_load(tmp_path):
    reg = TriggerRegistry(project_root=str(tmp_path), path="triggers.json")
    m = TriggerManager([Trigger(type="cron", config={"expr": "0 * * * *"})])
    reg.save(m)
    expected = tmp_path / "triggers.json"
    assert os.path.isfile(str(expected))
    loaded = reg.load()
    assert len(loaded.triggers) == 1
    assert loaded.triggers[0].type == "cron"


def test_registry_load_missing_file(tmp_path):
    reg = TriggerRegistry(project_root=str(tmp_path), path="nonexistent.json")
    m = reg.load()
    assert len(m.triggers) == 0


def test_registry_load_corrupt(tmp_path):
    bad = tmp_path / "bad_triggers.json"
    bad.write_text("{ not valid json")
    reg = TriggerRegistry(project_root=str(tmp_path), path="bad_triggers.json")
    m = reg.load()
    assert len(m.triggers) == 0  # graceful fallback


def test_registry_atomic_no_leftover(tmp_path):
    reg = TriggerRegistry(project_root=str(tmp_path), path="triggers.json")
    m = TriggerManager([Trigger(type="fs", config={"path": "/tmp"})])
    reg.save(m)
    # Check no .tmp file left behind
    leftovers = list(tmp_path.glob("triggers.*.tmp"))
    assert len(leftovers) == 0
