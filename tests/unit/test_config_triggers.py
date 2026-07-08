"""Unit tests for v3 triggers config."""
import os
from skills._lib.config import ConfigParser, apply_safety_rails, is_triggers_disabled


def test_config_parser_has_triggers():
    cp = ConfigParser(project_root="/tmp")
    cp.parse()
    assert hasattr(cp, "triggers")
    assert cp.triggers["enabled"] is True


def test_apply_safety_rails_default():
    cfg = {"enabled": True, "safety": {"trigger_off_override": False}}
    apply_safety_rails(cfg)
    assert cfg["enabled"] is True


def test_apply_safety_rails_override():
    cfg = {"enabled": True, "safety": {"trigger_off_override": True}}
    apply_safety_rails(cfg)
    assert cfg["enabled"] is False


def test_apply_safety_rails_env(monkeypatch):
    monkeypatch.setenv("TRIGGER_OFF", "1")
    cfg = {"enabled": True, "safety": {"trigger_off_override": False}}
    apply_safety_rails(cfg)
    assert cfg["enabled"] is False


def test_is_triggers_disabled_env(monkeypatch):
    monkeypatch.setenv("TRIGGER_OFF", "true")
    assert is_triggers_disabled() is True
    monkeypatch.delenv("TRIGGER_OFF")
    assert is_triggers_disabled() is False
