"""Tests for ConfigParser — multi-source priority-merge configuration."""
import os
import json
import pytest
import yaml
from skills._lib.config import ConfigParser, ConfigError


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all RDDF_* env vars for the test."""
    for k in list(os.environ):
        if k.startswith("RDDF_"):
            monkeypatch.delenv(k, raising=False)
    return monkeypatch


def test_minimal_config_parses(tmp_path, clean_env):
    """A config with only `version` and `interaction.mode` should fill defaults for the rest."""
    cfg_file = tmp_path / ".rddf.json"
    cfg_file.write_text(json.dumps({"version": "2.0", "interaction": {"mode": "hybrid"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["loop"]["max_iterations"] == 100  # from defaults
    assert config["interaction"]["mode"] == "hybrid"


def test_priority_runtime_over_loop_yaml(tmp_path, clean_env):
    """Runtime params override loop.yaml."""
    loop_yaml = tmp_path / "loop.yaml"
    loop_yaml.write_text(yaml.dump({"interaction": {"mode": "menu"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse(runtime_overrides={"interaction.mode": "loop"})
    assert config["interaction"]["mode"] == "loop"


def test_priority_loop_yaml_over_rddf_json(tmp_path, clean_env):
    """loop.yaml overrides .rddf.json."""
    (tmp_path / ".rddf.json").write_text(json.dumps({"interaction": {"mode": "menu"}}))
    (tmp_path / "loop.yaml").write_text(yaml.dump({"interaction": {"mode": "loop"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["interaction"]["mode"] == "loop"


def test_env_var_overrides_file_config(tmp_path, clean_env):
    """RDDF_MODE env var overrides .rddf.json."""
    (tmp_path / ".rddf.json").write_text(json.dumps({"interaction": {"mode": "menu"}}))
    clean_env.setenv("RDDF_MODE", "loop")
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["interaction"]["mode"] == "loop"


def test_invalid_mode_rejected(tmp_path, clean_env):
    """An invalid mode value produces ConfigError with clear message."""
    (tmp_path / ".rddf.json").write_text(json.dumps({"interaction": {"mode": "invalid_mode"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError, match="invalid_mode"):
        parser.parse()


def test_negative_max_iterations_rejected(tmp_path, clean_env):
    """max_iterations must be > 0."""
    (tmp_path / ".rddf.json").write_text(json.dumps({"loop": {"max_iterations": -1}}))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError, match="max_iterations"):
        parser.parse()


def test_type_coercion_for_env_vars(tmp_path, clean_env):
    """Env var RDDF_MAX_ITERATIONS=200 is parsed as int."""
    clean_env.setenv("RDDF_MAX_ITERATIONS", "200")
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["loop"]["max_iterations"] == 200
    assert isinstance(config["loop"]["max_iterations"], int)
