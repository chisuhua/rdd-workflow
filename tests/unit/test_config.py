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


def test_project_yaml_missing_no_effect(tmp_path, clean_env):
    """No .rddf/project.yaml → behavior unchanged (backward compatibility)."""
    (tmp_path / ".rddf.json").write_text(json.dumps({"interaction": {"mode": "menu"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["interaction"]["mode"] == "menu"
    assert "project" not in config


def test_priority_project_yaml_over_loop_yaml(tmp_path, clean_env):
    """project.yaml overrides loop.yaml (highest project-level config)."""
    (tmp_path / "loop.yaml").write_text(yaml.dump({"interaction": {"mode": "menu"}}))
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(
        yaml.dump({"interaction": {"mode": "loop"}})
    )
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["interaction"]["mode"] == "loop"


def test_project_yaml_over_env_vars(tmp_path, clean_env):
    """project.yaml overrides env vars (project-level > CI injection)."""
    clean_env.setenv("RDDF_MODE", "menu")
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(
        yaml.dump({"interaction": {"mode": "loop"}})
    )
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["interaction"]["mode"] == "loop"


def test_project_yaml_runtime_overrides(tmp_path, clean_env):
    """Runtime overrides still beat project.yaml."""
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(
        yaml.dump({"interaction": {"mode": "menu"}})
    )
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse(runtime_overrides={"interaction.mode": "loop"})
    assert config["interaction"]["mode"] == "loop"


def test_project_yaml_empty_file_handled(tmp_path, clean_env):
    """Empty project.yaml → equivalent to missing."""
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text("")
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert "project" not in config


def test_project_yaml_invalid_yaml_raises(tmp_path, clean_env):
    """Invalid YAML in project.yaml raises ConfigError."""
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text("invalid: : : yaml")
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(Exception):  # yaml.YAMLError or ConfigError
        parser.parse()


def test_project_yaml_nested_keys(tmp_path, clean_env):
    """Nested project.yaml keys merge with defaults via deep_merge."""
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(yaml.dump({
        "project": {"name": "chipforge", "version": "0.1.0"},
        "adr": {"pattern": r"^ADR-(\d{3})-.*\.md$"},
    }))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["project"]["name"] == "chipforge"
    assert config["adr"]["pattern"] == r"^ADR-(\d{3})-.*\.md$"


def test_project_config_sh_helper(tmp_path, clean_env, monkeypatch):
    """_lib/project_config.sh::project_yaml_get reads .rddf/project.yaml."""
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(yaml.dump({
        "adr": {"pattern": r"^ADR-\d{3}-"},
        "git": {"openspec_tracked": False},
        "verification": {"provider": "hook"},
    }))
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("PROJECT_CONFIG_NO_CACHE", "1")

    import subprocess
    result = subprocess.run(
        ["bash", "-c", f"source {tmp_path}/../_lib/project_config.sh 2>/dev/null; "
         f"source /workspace/project/rdd-workflow/_lib/project_config.sh; "
         f"project_yaml_get adr.pattern"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert "^ADR-\\d{3}-" in result.stdout


# ============================================================================
# Task 1.1 (complete-project-yaml-config-gaps M1): config_schema.json 新增 4 节
# ============================================================================


def test_project_yaml_schema_strict_raises(tmp_path, clean_env):
    """project.yaml with invalid git.openspec_tracked type raises ConfigError.

    Per design.md Decision 11: schema strict on new sections' internal contents.
    Per spec.md `schema-strict-validation`: invalid types SHALL raise ConfigError.
    """
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(yaml.dump({
        "git": {"openspec_tracked": "yes"},  # string instead of bool
    }))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError) as exc_info:
        parser.parse()
    # Error message must mention the offending field for debuggability
    msg = str(exc_info.value).lower()
    assert "openspec_tracked" in msg or "git" in msg


def test_project_yaml_verification_provider_enum_rejects(tmp_path, clean_env):
    """project.yaml verification.provider must be 'llm' or 'hook', not arbitrary string."""
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(yaml.dump({
        "verification": {"provider": "gpt-5"},  # not in enum
    }))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError) as exc_info:
        parser.parse()
    msg = str(exc_info.value).lower()
    assert "verification" in msg or "provider" in msg


def test_project_yaml_adr_unknown_field_rejected(tmp_path, clean_env):
    """project.yaml adr section rejects unknown subfields (additionalProperties: false)."""
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(yaml.dump({
        "adr": {"pattern": r"^ADR-\d{4}$", "made_up_field": "foo"},
    }))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError) as exc_info:
        parser.parse()
    msg = str(exc_info.value).lower()
    assert "adr" in msg or "made_up_field" in msg
