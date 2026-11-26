"""spec delta 的 **MODIFIED 语义** + 版本分流（AC8 / AC9 / AC13）。

载体（design D-1，**粗体头行**）::

    **delta**: modified <capability>
    **语义要求**: <requirement> | <body> | <scenario> | <WHEN> | <THEN>

MODIFIED 的硬约束：块内**必须含 main spec 该 requirement 的全部既有 Scenario**
（openspec 归档时逐个比对，缺一个即 abort）。
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_SCRIPT = _ROOT / "skills" / "rdd-builder" / "scripts" / "generate_full_proposal.py"
_spec = importlib.util.spec_from_file_location("gen_fp_modified", _SCRIPT)
gen_fp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_fp)

_SPEC_DIR = _ROOT / "openspec" / "specs" / "generator-scope-extraction" / "spec.md"
_TARGET_REQ = "generate-proposal-backward-compatible"
_EXISTING_SCENARIO = "bullet-only file produces same item count"


def _md(capability: str | None, requirement: str) -> str:
    head = f"**delta**: modified {capability}\n" if capability else ""
    return (
        f"{head}**语义要求**: {requirement} | 系统 SHALL 以 golden snapshot 断言语料回归"
        " | 语料快照随语料增长刷新 | 语料新增 improvement 时 | 快照被同 PR 刷新\n\n"
        "## Acceptance\n\n- [ ] 一条验收\n"
    )


def test_modified_target_is_emitted() -> None:
    out = gen_fp.generate_spec_delta(
        _md("generator-scope-extraction", _TARGET_REQ), "probe"
    )
    assert out.splitlines()[0] == "## MODIFIED Requirements", out[:200]
    assert f"### Requirement: {_TARGET_REQ}" in out, out
    # 既有 Scenario 必须**逐字保留**（openspec 归档前置）
    assert f"#### Scenario: {_EXISTING_SCENARIO}" in out, out
    # 作者的新场景也要在
    assert "#### Scenario: 语料快照随语料增长刷新" in out, out


def test_missing_target_requirement_is_refused() -> None:
    with pytest.raises(ValueError) as exc:
        gen_fp.generate_spec_delta(_md("generator-scope-extraction", "no-such-requirement"), "probe")
    assert "no-such-requirement" in str(exc.value), str(exc.value)


def test_unknown_capability_is_refused() -> None:
    with pytest.raises(ValueError) as exc:
        gen_fp.generate_spec_delta(_md("no-such-capability", _TARGET_REQ), "probe")
    assert "no-such-capability" in str(exc.value), str(exc.value)


def test_added_mode_when_no_delta_field() -> None:
    out = gen_fp.generate_spec_delta(_md(None, "family-domain-has-four-values"), "probe")
    assert out.splitlines()[0] == "## ADDED Requirements", out[:200]


def test_version_comparison_is_semantic_not_lexicographic() -> None:
    """AC13：版本比较必须**语义化**（`1.14.3 > 1.7.0`，字符串比较会判反）。"""
    from _lib import openspec_version as ov

    assert ov.at_least((1, 7, 0), (1, 14, 3)) is True
    assert ov.at_least((1, 7, 0), (1, 4, 1)) is False
    assert ov.at_least((1, 7, 0), (1, 7, 0)) is True
    assert ov.native_scenario_conservation_available((1, 14, 3)) is True
    assert ov.native_scenario_conservation_available((1, 4, 1)) is False


def test_legacy_openspec_still_gets_local_guard(monkeypatch, capsys) -> None:
    """AC13：<1.7.0（无原生检查）时**本地预检仍是唯一守卫** ⇒ 必须显式告警。"""
    monkeypatch.setenv("RDDF_OPENSPEC_VERSION", "1.4.1")
    out = gen_fp.generate_spec_delta(
        _md("generator-scope-extraction", _TARGET_REQ), "probe"
    )
    assert f"#### Scenario: {_EXISTING_SCENARIO}" in out, out
    assert "本地预检" in capsys.readouterr().err


def test_missing_openspec_cli_is_not_fatal(monkeypatch) -> None:
    """边界：本机没有 openspec CLI ⇒ 探测返回 None（**不崩**），并按「无原生检查」保守处理。"""
    from _lib import openspec_version as ov

    monkeypatch.delenv("RDDF_OPENSPEC_VERSION", raising=False)

    def _boom(*a, **k):
        raise FileNotFoundError("openspec")

    monkeypatch.setattr(ov.subprocess, "run", _boom)
    assert ov.current_version() is None
    assert ov.native_scenario_conservation_available() is False
    # 生成侧仍能工作（本地预检兜底），不因探测失败而崩
    out = gen_fp.generate_spec_delta(
        _md("generator-scope-extraction", "generate-proposal-backward-compatible"), "probe"
    )
    assert f"#### Scenario: {_EXISTING_SCENARIO}" in out
