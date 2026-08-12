"""Tests for ADR-0027 §8 config namespace extension: ``reporting`` section.

ADR-0027 §8 decision: reuse existing ``_lib/config.py`` stack. New ``reporting``
namespace holds the 3-tier opt-in + submit_categories + retention config.
RDDF_REPORT_* env vars override the corresponding dotted paths.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "_lib"))

from config import ConfigParser  # type: ignore[import-not-found]


# ── Default values (TDD 2.1 in tasks.md) ──────────────────────────────────


def test_reporting_default_disabled():
    """When no config file / env is present, ``reporting.enabled`` is False."""
    parser = ConfigParser(project_root="/nonexistent")
    config = parser.parse()
    assert config["reporting"]["enabled"] is False
    assert config["reporting"]["auto_submit"] is False
    assert config["reporting"]["close_on_archive"] is True
    assert config["reporting"]["destination"] == "github"
    assert config["reporting"]["retention_days"] == 30


def test_submit_categories_defaults():
    """Default submit_categories enables the 4 documented categories."""
    parser = ConfigParser(project_root="/nonexistent")
    config = parser.parse()
    cats = config["reporting"]["submit_categories"]
    assert cats["flow-bug"] is True
    assert cats["gate-failure"] is True
    assert cats["phase-crash"] is True
    assert cats["manual"] is True


# ── Env var override (TDD 2.2 in tasks.md) ─────────────────────────────────


def test_rddf_report_enabled_env_overrides_default(monkeypatch):
    """RDDF_REPORT_ENABLED=yes flips ``reporting.enabled`` to True."""
    monkeypatch.setenv("RDDF_REPORT_ENABLED", "yes")
    monkeypatch.delenv("RDDF_REPORT_AUTO_SUBMIT", raising=False)
    monkeypatch.delenv("RDDF_REPORT_CLOSE_ON_ARCHIVE", raising=False)
    parser = ConfigParser(project_root="/nonexistent")
    config = parser.parse()
    assert config["reporting"]["enabled"] is True


def test_rddf_report_destination_env_override(monkeypatch):
    """RDDF_REPORT_DESTINATION=custom-url flips destination."""
    monkeypatch.setenv("RDDF_REPORT_DESTINATION", "custom-url")
    parser = ConfigParser(project_root="/nonexistent")
    config = parser.parse()
    assert config["reporting"]["destination"] == "custom-url"


def test_rddf_report_close_on_archive_env_override(monkeypatch):
    """RDDF_REPORT_CLOSE_ON_ARCHIVE=no disables archive auto-close."""
    monkeypatch.setenv("RDDF_REPORT_CLOSE_ON_ARCHIVE", "no")
    parser = ConfigParser(project_root="/nonexistent")
    config = parser.parse()
    assert config["reporting"]["close_on_archive"] is False


# ── Schema validation (TDD 2.3 in tasks.md) ───────────────────────────────


def test_reporting_section_validates_against_config_schema(tmp_path, monkeypatch):
    """A .rddf.json providing a valid ``reporting`` block passes schema validation."""
    monkeypatch.delenv("RDDF_REPORT_ENABLED", raising=False)
    monkeypatch.delenv("RDDF_REPORT_AUTO_SUBMIT", raising=False)
    monkeypatch.delenv("RDDF_REPORT_DESTINATION", raising=False)
    monkeypatch.delenv("RDDF_REPORT_CLOSE_ON_ARCHIVE", raising=False)

    rddf_json = tmp_path / ".rddf.json"
    rddf_json.write_text(json.dumps({
        "reporting": {
            "enabled": True,
            "auto_submit": True,
            "destination": "github",
            "submit_categories": {
                "flow-bug": True,
                "gate-failure": True,
                "phase-crash": True,
                "manual": True,
            },
            "close_on_archive": True,
            "retention_days": 14,
        }
    }))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["reporting"]["enabled"] is True
    assert config["reporting"]["retention_days"] == 14


def test_reporting_missing_in_rddf_json_uses_defaults(tmp_path, monkeypatch):
    """Loading a .rddf.json without a ``reporting`` section falls back to defaults."""
    monkeypatch.delenv("RDDF_REPORT_ENABLED", raising=False)
    monkeypatch.delenv("RDDF_REPORT_AUTO_SUBMIT", raising=False)
    monkeypatch.delenv("RDDF_REPORT_DESTINATION", raising=False)
    monkeypatch.delenv("RDDF_REPORT_CLOSE_ON_ARCHIVE", raising=False)

    (tmp_path / ".rddf.json").write_text(json.dumps({"loop": {"max_iterations": 50}}))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["reporting"]["enabled"] is False
    assert config["loop"]["max_iterations"] == 50


# ── Regression: existing config still works (TDD 2.9) ─────────────────────


def test_existing_interaction_mode_still_works(monkeypatch):
    """Pre-existing interaction.mode validation must not regress."""
    monkeypatch.delenv("RDDF_REPORT_ENABLED", raising=False)
    monkeypatch.delenv("RDDF_REPORT_AUTO_SUBMIT", raising=False)
    monkeypatch.delenv("RDDF_REPORT_DESTINATION", raising=False)
    monkeypatch.delenv("RDDF_REPORT_CLOSE_ON_ARCHIVE", raising=False)
    parser = ConfigParser(project_root="/nonexistent")
    config = parser.parse()
    assert config["interaction"]["mode"] in ("loop", "menu", "hybrid")
    assert config["loop"]["max_iterations"] >= 1
