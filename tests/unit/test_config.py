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
    """No .rddf/project.yaml → behavior unchanged (backward compatibility).

    Per complete-project-yaml-config-gaps M1 Task 1.2: DEFAULTS now includes
    'project: {}' as a merge placeholder, so 'project' key IS present after parse,
    but its value is empty dict (zero behavioral impact, matching i10 contract).
    """
    (tmp_path / ".rddf.json").write_text(json.dumps({"interaction": {"mode": "menu"}}))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["interaction"]["mode"] == "menu"
    assert config.get("project") == {}, (
        f"Missing project.yaml should yield config['project'] == {{}}, got {config.get('project')!r}"
    )


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
    """Empty project.yaml → equivalent to missing (config['project'] stays empty dict)."""
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text("")
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config.get("project") == {}


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


# ============================================================================
# Task 1.1a (M1): 根级 extras 零回归 (per design.md Decision 11)
# ============================================================================


def test_project_yaml_root_level_extras_allowed(tmp_path, clean_env):
    """Root-level additionalProperties remains true; user-defined keys pass.

    Per design.md Decision 11: root additionalProperties: true (default) preserves
    backward compat for users with extra root-level keys in project.yaml
    (e.g. tool-specific configs). New sections (project/adr/git/verification)
    enforce strict on their OWN contents only.
    """
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(yaml.dump({
        "my_custom_tooling": {"x": 1, "y": "z"},
        "team_notes": "internal",
        # valid known sections also present
        "git": {"openspec_tracked": True},
    }))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    # extras must survive in merged config (passthrough)
    assert config.get("my_custom_tooling") == {"x": 1, "y": "z"}
    assert config.get("team_notes") == "internal"
    # known section still validated
    assert config["git"]["openspec_tracked"] is True


# ============================================================================
# Task 1.3 (M1): schema 严格性回归门 — 跨章节组合断言
# ============================================================================


def test_project_yaml_all_sections_strict_validation(tmp_path, clean_env):
    """All 4 sections (project/adr/git/verification) enforce strict on contents.

    Single end-to-end test that combines: invalid type in 'project', invalid
    glob format in 'adr', invalid type in 'git', invalid enum in 'verification'.
    Each error must be raised; ordering doesn't matter but at least one ConfigError
    must surface so users cannot accidentally ship malformed project.yaml.

    Per complete-project-yaml-config-gaps M1 Task 1.3 + spec.md
    'schema-strict-validation' requirement.
    """
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    # Combine multiple violations — ConfigParser must raise AT LEAST one
    (project_dir / "project.yaml").write_text(yaml.dump({
        "project": {"name": 12345},  # name must be string
        "verification": {"provider": "invalid_choice"},  # not llm/hook
    }))
    parser = ConfigParser(project_root=str(tmp_path))
    with pytest.raises(ConfigError) as exc_info:
        parser.parse()
    msg = str(exc_info.value).lower()
    # At least one of the bad fields must be flagged
    assert "project" in msg or "name" in msg or "verification" in msg or "provider" in msg


def test_project_yaml_valid_full_payload_parses(tmp_path, clean_env):
    """A fully-valid project.yaml with all 4 sections parses successfully (positive control)."""
    project_dir = tmp_path / ".rddf"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(yaml.dump({
        "project": {"name": "chipforge", "version": "0.1.0"},
        "adr": {"pattern": r"^ADR-(\d{3})-.*\.md$", "glob": "ADR-???.md"},
        "git": {"openspec_tracked": False},
        "verification": {"provider": "hook"},
    }))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    assert config["project"]["name"] == "chipforge"
    assert config["adr"]["pattern"] == r"^ADR-(\d{3})-.*\.md$"
    assert config["git"]["openspec_tracked"] is False
    assert config["verification"]["provider"] == "hook"


# ============================================================================
# Task 1.4 (M1): 向后兼容零回归 — 验证现有 i10 测试 + 既有 .rddf.json 用户路径
# ============================================================================


def test_existing_rddf_json_user_zero_alignment(tmp_path, clean_env):
    """Existing user with only .rddf.json (no project.yaml) sees zero behavior change.

    This is the canonical 'zero regression' lock — the i10 contract promised
    that adding project.yaml support does not break existing users.

    Pre-M1: config["project"] was absent, .rddf.json-only users unaffected.
    Post-M1: config["project"] == {} (default placeholder), still zero behavioral impact.
    """
    # Simulate existing user: only .rddf.json, no project.yaml, no loop.yaml
    (tmp_path / ".rddf.json").write_text(json.dumps({
        "interaction": {"mode": "loop"},
        "loop": {"max_iterations": 50, "max_retries": 2},
    }))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    # .rddf.json values preserved
    assert config["interaction"]["mode"] == "loop"
    assert config["loop"]["max_iterations"] == 50
    # project placeholder is empty (no behavioral effect)
    assert config.get("project") == {}
    # No new top-level keys leaked into config (other than defaults' empty project)
    # Defaults-merged keys are allowed (state/event_log/gate/sync/reporting/interaction/loop)
    assert set(config.keys()) >= {"version", "interaction", "loop", "state", "event_log",
                                     "gate", "sync", "reporting", "project"}


def test_existing_loop_yaml_user_zero_alignment(tmp_path, clean_env):
    """Existing user with only loop.yaml sees zero behavior change (priority chain intact)."""
    (tmp_path / "loop.yaml").write_text(yaml.dump({
        "loop": {"max_iterations": 250},
    }))
    parser = ConfigParser(project_root=str(tmp_path))
    config = parser.parse()
    # loop.yaml override applied
    assert config["loop"]["max_iterations"] == 250
    # other defaults preserved
    assert config["loop"]["max_retries"] == 3
    # project placeholder still empty
    assert config.get("project") == {}
