"""spec delta 的**形态守卫** —— 退化形态在**生成时**被拒（AC7）。

背景（2026-11-26，CppTLM 立项会话实测）：P0 生成的 delta 是
`## ADDED Requirements` + `capability-1` + `- **WHEN** the change is applied`
⇒ 正是 `tests/unit/test_spec_requirement_form.py` 判为退化并拒绝的形态，
而 `openspec validate --strict` **照样绿**（结构合法）⇒ 退化形态一路流到归档期才被发现。
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
_spec = importlib.util.spec_from_file_location("gen_fp_shape", _SCRIPT)
gen_fp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_fp)


def _md(requirement: str, when: str, then: str = "该要求成立") -> str:
    return (
        "**delta**: added probe-capability\n"
        "**语义要求**: "
        f"{requirement} | 系统 SHALL 满足该要求 | 场景一 | {when} | {then}\n\n"
        "## Acceptance\n\n- [ ] 一条验收\n"
    )


def test_acceptance_n_name_is_refused() -> None:
    with pytest.raises(ValueError) as exc:
        gen_fp.generate_spec_delta(_md("acceptance-1", "用户声明其来源族"), "probe")
    assert "acceptance" in str(exc.value).lower()


def test_capability_n_name_is_refused() -> None:
    with pytest.raises(ValueError) as exc:
        gen_fp.generate_spec_delta(_md("capability-1", "用户声明其来源族"), "probe")
    assert "capability" in str(exc.value).lower()


def test_tautological_when_is_refused() -> None:
    with pytest.raises(ValueError) as exc:
        gen_fp.generate_spec_delta(_md("family-domain-has-four-values", "the change is applied"), "probe")
    assert "when" in str(exc.value).lower()


def test_wellformed_semantic_requirement_is_accepted() -> None:
    out = gen_fp.generate_spec_delta(
        _md("family-domain-has-four-values", "用户声明其来源族", "family 域恰有 4 值"), "probe"
    )
    assert "### Requirement: family-domain-has-four-values" in out, out
    assert "用户声明其来源族" in out, out
    assert "the change is applied" not in out, out


def test_missing_carrier_is_refused_with_named_diagnostic() -> None:
    # **声明了 delta 但没有语义要求** ⇒ 拒绝并指名缺什么（opt-in 之前提是「声明了才生成」）
    md = "**delta**: added probe-capability\n\n## Acceptance\n\n- [ ] 一条验收\n"
    with pytest.raises(ValueError) as exc:
        gen_fp.generate_spec_delta(md, "probe")
    assert "语义要求" in str(exc.value), str(exc.value)


def test_no_delta_declaration_is_skip_not_failure() -> None:
    """**opt-in**：未声明 `**delta**` ⇒ 抛 `DeltaNotRequested`（调用方跳过，不算失败）。

    存量 300+ improvement 没有载体 ⇒ 旧行为「总是生成」正是退化形态的来源；
    改为「声明了才生成」⇒ 没有 delta 就没有退化 delta，且存量工作流不受影响。
    """
    with pytest.raises(gen_fp.DeltaNotRequested):
        gen_fp.generate_spec_delta(_md("x", "y").replace("**delta**: added probe-capability\n", ""), "probe")
