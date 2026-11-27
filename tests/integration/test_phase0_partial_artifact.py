"""P0 的半成品防护 + 跨轴端到端（AC14 / AC15）。

AC14：delta 形状守卫**拒绝生成**时 ⇒ 不留空 delta 文件、不留半成品 proposal、**重试可再生成**。
AC15：同一 improvement 同时命中两轴（范围节纯表格 + `**delta**: modified`）⇒ 一次 P0 跑出
      **两份都正确**的产物。

⚠ 这两个 AC 只有在**真实脚本**（`phase0_approval.sh` + `generate_full_proposal.py`）上才成立
⇒ 本用例用 `subprocess` 驱动脚本，在临时项目根里跑（不污染真实仓）。
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PHASE0 = _ROOT / "skills" / "rdd-builder" / "scripts" / "phase0_approval.sh"
_MAIN_SPEC = _ROOT / "openspec" / "specs" / "generator-scope-extraction" / "spec.md"


def _make_project(tmp_path: pathlib.Path, improvement: str) -> pathlib.Path:
    (tmp_path / ".rddf" / "improvements").mkdir(parents=True)
    (tmp_path / ".rddf" / "improvements" / "probe.md").write_text(improvement, encoding="utf-8")
    (tmp_path / "openspec" / "changes").mkdir(parents=True)
    if _MAIN_SPEC.is_file():
        dest = tmp_path / "openspec" / "specs" / "generator-scope-extraction"
        dest.mkdir(parents=True)
        shutil.copy2(_MAIN_SPEC, dest / "spec.md")
    return tmp_path


def _run_phase0(root: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(_PHASE0), "probe"],
        cwd=root,
        env={
            "PROJECT_ROOT": str(root),
            "RDDF_LLM_DECISION": "approve",
            "RDDF_OPENSPEC_VERSION": "1.14.3",
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": str(pathlib.Path.home()),
        },
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_delta_refusal_leaves_no_partial_artifacts(tmp_path: pathlib.Path) -> None:
    # **声明了 delta 但无 语义要求** ⇒ 形态守卫必然拒绝（opt-in：不声明则不生成，不算失败）
    root = _make_project(
        tmp_path, "**delta**: added probe-capability\n\n## Acceptance\n\n- [ ] 一条验收\n"
    )
    first = _run_phase0(root)
    assert first.returncode != 0, first.stdout + first.stderr

    change_dir = root / "openspec" / "changes" / "probe"
    leftovers = [p for p in change_dir.rglob("*") if p.is_file()]
    assert leftovers == [], f"拒绝后不应留下任何产物：{leftovers}"

    # 重试：仍拒绝，且仍不落盘（空文件不得永久骗过幂等检查）
    second = _run_phase0(root)
    assert second.returncode != 0, second.stdout + second.stderr
    assert [p for p in change_dir.rglob("*") if p.is_file()] == []


def test_cross_axis_produces_both_artifacts(tmp_path: pathlib.Path) -> None:
    if not _MAIN_SPEC.is_file():
        pytest.skip("openspec/specs/ 不在（openspec/ 整树 gitignore ⇒ 本用例仅本地可跑）")
    improvement = (
        "**delta**: modified generator-scope-extraction\n"
        "**语义要求**: generate-proposal-backward-compatible"
        " | 系统 SHALL 以 golden snapshot 断言语料回归"
        " | 语料快照随语料增长刷新 | 语料新增 improvement 时 | 快照被同 PR 刷新\n\n"
        "## 范围\n\n"
        "**In Scope**\n\n"
        "| # | 改动 | 落点 |\n"
        "|:--:|---|---|\n"
        "| 1 | `a` | `x.hh` |\n\n"
        "**Out of Scope**\n\n"
        "- 不做 `d`\n\n"
        "## Acceptance\n\n- [ ] 一条验收\n"
    )
    root = _make_project(tmp_path, improvement)
    proc = _run_phase0(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    proposal = root / "openspec" / "changes" / "probe" / "proposal.md"
    delta = (
        root
        / "openspec"
        / "changes"
        / "probe"
        / "specs"
        / "generator-scope-extraction"
        / "spec.md"
    )
    assert proposal.is_file() and proposal.stat().st_size > 0
    assert delta.is_file() and delta.stat().st_size > 0

    text = proposal.read_text(encoding="utf-8")
    assert "`a`" in text, text[:400]          # 表格行成条目（轴 1）
    assert "|" not in text.split("## What Changes")[1].split("## Capabilities")[0], text[:600]

    dtext = delta.read_text(encoding="utf-8")
    assert dtext.splitlines()[0] == "## MODIFIED Requirements", dtext[:200]   # 轴 2
    assert "#### Scenario: bullet-only file produces same item count" in dtext


def test_undeclared_delta_is_skipped_not_failed(tmp_path: pathlib.Path) -> None:
    """opt-in：未声明 `**delta**` ⇒ P0 成功、**不生成** delta（存量 improvement 的工作流不变）。"""
    root = _make_project(tmp_path, "## Acceptance\n\n- [ ] 一条验收\n")
    proc = _run_phase0(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "未声明" in (proc.stdout + proc.stderr)
    change_dir = root / "openspec" / "changes" / "probe"
    assert not list(change_dir.rglob("spec.md")), "未声明 delta ⇒ 不应生成任何 delta"
    assert (change_dir / "proposal.md").is_file()
