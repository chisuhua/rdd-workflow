"""Tests for from_roadmap.env validation — anti-injection safety.

Test groups:
1. Rejects shell metacharacters ($, backticks, ;, |, &, newlines, etc.)
2. Accepts valid CJK theme names with punctuation
3. Requires both ADD_IMPROVE_FROM_ROADMAP and ADD_IMPROVE_THEME
"""
import os
import subprocess
import sys
from pathlib import Path

WT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = WT_ROOT / "skills" / "add-improve" / "scripts" / "from_roadmap.env.py"


def _run_validate(env_overrides: dict):
    """Run from_roadmap.env.py validate with given env-var overrides."""
    env = os.environ.copy()
    for k, v in env_overrides.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    return subprocess.run(
        [sys.executable, str(SCRIPT), "validate"],
        env=env,
        capture_output=True,
        text=True,
    )


# === Test Group 1: Rejects shell metacharacters ===

def test_rejects_dollar_command_substitution():
    """Theme with $(whoami) is rejected."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ROADMAP": "phase-1/arch-design",
        "ADD_IMPROVE_THEME": "evil$(whoami)",
    })
    assert result.returncode != 0
    assert "disallowed" in result.stderr.lower()


def test_rejects_backtick_command_substitution():
    """Theme with backtick command substitution is rejected."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ROADMAP": "phase-1/arch-design",
        "ADD_IMPROVE_THEME": "evil`id`",
    })
    assert result.returncode != 0
    assert "disallowed" in result.stderr.lower()


def test_rejects_quote_and_rm():
    """Theme with quote-and-rm injection is rejected."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ROADMAP": "phase-1/arch-design",
        "ADD_IMPROVE_THEME": 'evil"; rm -rf #',
    })
    assert result.returncode != 0
    assert "disallowed" in result.stderr.lower()


def test_rejects_newline_injection():
    """Theme with newline is rejected."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ROADMAP": "phase-1/arch-design",
        "ADD_IMPROVE_THEME": "evil\nnewline",
    })
    assert result.returncode != 0
    assert "disallowed" in result.stderr.lower()


def test_rejects_sql_injection_attempt():
    """Theme with SQL injection chars is rejected."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ROADMAP": "phase-1/arch-design",
        "ADD_IMPROVE_THEME": "evil' OR 1=1 --",
    })
    assert result.returncode != 0
    assert "disallowed" in result.stderr.lower()


# === Test Group 2: Accepts valid themes ===

def test_accepts_cjk_theme():
    """Plain CJK theme name is accepted."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ROADMAP": "phase-1/arch-design",
        "ADD_IMPROVE_THEME": "RBAC权限模型",
    })
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_accepts_theme_with_api_version():
    """Theme with version number and dot is accepted."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ROADMAP": "phase-1/arch-design",
        "ADD_IMPROVE_THEME": "API v2.0 接口",
    })
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_accepts_theme_with_percent():
    """Theme with percent sign (not in disallowed list) is accepted."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ROADMAP": "phase-1/arch-design",
        "ADD_IMPROVE_THEME": "测试覆盖率 80%",
    })
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_accepts_theme_with_event_bus():
    """Theme with spaces is accepted."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ROADMAP": "phase-1/arch-design",
        "ADD_IMPROVE_THEME": "事件总线契约",
    })
    assert result.returncode == 0, f"stderr: {result.stderr}"


# === Test Group 3: Required env-var validation ===

def test_requires_theme_when_from_roadmap_set():
    """ADD_IMPROVE_THEME missing → fails fast."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ROADMAP": "phase-1/arch-design",
        "ADD_IMPROVE_THEME": None,
    })
    assert result.returncode != 0
    assert "ADD_IMPROVE_THEME" in result.stderr


def test_rejects_invalid_from_roadmap_format():
    """ADD_IMPROVE_FROM_ROADMAP must be phase_id/category_id."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ROADMAP": "invalid-format",
        "ADD_IMPROVE_THEME": "validTheme",
    })
    assert result.returncode != 0
    assert "phase_id/category_id" in result.stderr


def test_no_env_vars_is_noop():
    """With no env-vars set, validate succeeds (mode not triggered)."""
    result = _run_validate({
        "ADD_IMPROVE_FROM_ROADMAP": None,
        "ADD_IMPROVE_THEME": None,
        "BRAINSTORM_RATIONALE_DRAFT": None,
    })
    assert result.returncode == 0, f"stderr: {result.stderr}"


# === Test Group 4: Naming env-vars (improve-from-roadmap-naming-flexibility) ===

def _base_env():
    return {
        "ADD_IMPROVE_FROM_ROADMAP": "phase-1/arch-design",
        "ADD_IMPROVE_THEME": "测试主题",
    }


def test_accepts_valid_name_prefix_and_suffix():
    """Kebab-case prefix/suffix are accepted."""
    result = _run_validate({
        **_base_env(),
        "ADD_IMPROVE_NAME_PREFIX": "fix-audit-",
        "ADD_IMPROVE_NAME_SUFFIX": "-rfc",
    })
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_rejects_name_prefix_with_uppercase():
    """Prefix with uppercase violates kebab-case."""
    result = _run_validate({
        **_base_env(),
        "ADD_IMPROVE_NAME_PREFIX": "Fix-Audit-",
    })
    assert result.returncode != 0
    assert "kebab-case" in result.stderr


def test_rejects_name_suffix_with_special_chars():
    """Suffix with special characters is rejected."""
    result = _run_validate({
        **_base_env(),
        "ADD_IMPROVE_NAME_SUFFIX": "-rfc!",
    })
    assert result.returncode != 0
    assert "kebab-case" in result.stderr


def test_accepts_auto_name_true():
    """ADD_IMPROVE_AUTO_NAME=yes is accepted."""
    result = _run_validate({
        **_base_env(),
        "ADD_IMPROVE_AUTO_NAME": "yes",
    })
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_rejects_invalid_auto_name():
    """ADD_IMPROVE_AUTO_NAME=garbage is rejected."""
    result = _run_validate({
        **_base_env(),
        "ADD_IMPROVE_AUTO_NAME": "garbage",
    })
    assert result.returncode != 0
    assert "ADD_IMPROVE_AUTO_NAME" in result.stderr


def test_accepts_multi_positive_int():
    """ADD_IMPROVE_MULTI=3 is accepted."""
    result = _run_validate({
        **_base_env(),
        "ADD_IMPROVE_MULTI": "3",
    })
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_rejects_multi_zero_or_negative():
    """ADD_IMPROVE_MULTI=0 / -1 are rejected."""
    for bad in ("0", "-1", "abc"):
        result = _run_validate({
            **_base_env(),
            "ADD_IMPROVE_MULTI": bad,
        })
        assert result.returncode != 0
        assert "ADD_IMPROVE_MULTI" in result.stderr


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))