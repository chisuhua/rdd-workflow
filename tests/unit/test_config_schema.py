"""Tests for config schema validation - unknown key rejection and schema hardening."""
import json
import os
import pytest
from skills._lib.config import ConfigParser, ConfigError


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all RDDF_* env vars for the test."""
    for k in list(os.environ):
        if k.startswith("RDDF_"):
            monkeypatch.delenv(k, raising=False)
    return monkeypatch


def test_unknown_key_in_loop_rejected(tmp_path, clean_env):
    """A misnamed key like 'maxIterations' (should be 'max_iterations') must raise ConfigError."""
    cfg_file = tmp_path / ".rddf.json"
    cfg_file.write_text(json.dumps({"loop": {"maxIterations": 50}}))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError, match="maxIterations"):
        parser.parse()


def test_valid_config_passes_schema(tmp_path, clean_env):
    """A valid config with known keys in interaction and loop sections must parse successfully."""
    cfg_file = tmp_path / ".rddf.json"
    cfg_file.write_text(json.dumps({
        "interaction": {"mode": "loop", "menu_items": ["propose", "execute"]},
        "loop": {"max_iterations": 50, "max_retries": 3, "retry_backoff_seconds": 5}
    }))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["interaction"]["mode"] == "loop"
    assert config["loop"]["max_iterations"] == 50


def test_wrong_type_rejected_by_schema(tmp_path, clean_env):
    """A wrong type for max_iterations (string instead of integer) must raise ConfigError."""
    cfg_file = tmp_path / ".rddf.json"
    cfg_file.write_text(json.dumps({"loop": {"max_iterations": "abc"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError, match="max_iterations"):
        parser.parse()


def test_out_of_range_rejected(tmp_path, clean_env):
    """An out-of-range value (max_iterations: 0) must raise ConfigError with minimum info."""
    cfg_file = tmp_path / ".rddf.json"
    cfg_file.write_text(json.dumps({"loop": {"max_iterations": 0}}))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError, match="max_iterations"):
        parser.parse()


def test_missing_schema_skips_validation(tmp_path, clean_env, monkeypatch):
    """If the schema file is missing, validation is skipped (backward compatibility)."""
    import skills._lib.config as config_module
    monkeypatch.setattr(config_module, "_CONFIG_SCHEMA_PATH", "/nonexistent/schema.json")
    cfg_file = tmp_path / ".rddf.json"
    cfg_file.write_text(json.dumps({"interaction": {"mode": "loop"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()  # should NOT raise
    assert config["interaction"]["mode"] == "loop"
