"""doctor `v4-residue`：契约面的 v3 残留守卫。

R1 路由型 enum 缺 v4 路由值 → CRITICAL
R2 活代码字符串字面量里的 `skill_use("guide-*")` / `--phase guide-*` → WARNING
R3 `skills/*/SKILL.md` frontmatter `name:` 为 `guide-*` → CRITICAL
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = REPO_ROOT / "skills" / "rdd-doctor" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from checks import v4_residue_check  # noqa: E402


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _route_schema(routes):
    return {"properties": {"route": {"enum": routes}}}


# ---------- R1 ----------

def test_r1_route_enum_without_v4_value_is_critical(tmp_path):
    _write_json(tmp_path / "_lib/schemas/verifier_loop_schema.json",
                _route_schema(["archive-ready", "guide-ship", "guide-plan", "halted"]))
    _write_json(tmp_path / "_lib/schemas/iteration_schema.json",
                _route_schema(["archive-ready", "guide-ship", "guide-plan", "halted"]))
    findings = v4_residue_check.run(tmp_path)
    r1 = [f for f in findings if f.category == "v4-residue" and "R1" in f.snippet]
    assert len(r1) == 2, findings
    assert all(f.severity.value == "CRITICAL" for f in r1)


def test_r1_route_enum_containing_v4_value_passes(tmp_path):
    """同时含 v4 值与 legacy 值 → 不报（存量 state 必须仍可加载）。"""
    _write_json(tmp_path / "_lib/schemas/verifier_loop_schema.json",
                _route_schema(["archive-ready", "rdd-builder", "guide-ship", "guide-plan", "halted"]))
    _write_json(tmp_path / "_lib/schemas/iteration_schema.json",
                _route_schema(["archive-ready", "rdd-builder", "guide-ship", "guide-plan", "halted"]))
    assert v4_residue_check.run(tmp_path) == []


# ---------- R2 ----------

def test_r2_string_literal_reference_is_warning(tmp_path):
    src = tmp_path / "skills" / "demo" / "scripts"
    src.mkdir(parents=True)
    (src / "demo.py").write_text(
        'HINT = \'please call skill_use("guide-ship") first\'\n', encoding="utf-8")
    findings = v4_residue_check.run(tmp_path)
    r2 = [f for f in findings if "R2" in f.snippet]
    assert len(r2) == 1, findings
    assert r2[0].severity.value == "WARNING"


def test_r2_run_idiom_is_flagged(tmp_path):
    """`(run guide-plan first)` 这类 idiom 也必须报 —— 曾漏网过一次。"""
    src = tmp_path / "skills" / "demo" / "scripts"
    src.mkdir(parents=True)
    (src / "demo.py").write_text(
        'MSG = "iteration.json not found (run guide-plan first)"\n', encoding="utf-8")
    findings = v4_residue_check.run(tmp_path)
    r2 = [f for f in findings if "R2" in f.snippet]
    assert len(r2) == 1, findings


def test_r2_comment_and_docstring_are_exempt(tmp_path):
    """注释与 docstring 里的历史名是考古信息，不得报。"""
    src = tmp_path / "skills" / "demo" / "scripts"
    src.mkdir(parents=True)
    (src / "demo.py").write_text(
        '"""Historical note: used to call skill_use("guide-ship")."""\n'
        '# old code did skill_use("guide-plan")\n'
        'VALUE = 1\n', encoding="utf-8")
    assert v4_residue_check.run(tmp_path) == []


# ---------- R3 ----------

def test_r3_skill_frontmatter_name_is_critical(tmp_path):
    d = tmp_path / "skills" / "guide-ship"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: guide-ship\n---\n# x\n", encoding="utf-8")
    findings = v4_residue_check.run(tmp_path)
    r3 = [f for f in findings if "R3" in f.snippet]
    assert len(r3) == 1, findings
    assert r3[0].severity.value == "CRITICAL"


def test_r3_v4_skill_name_passes(tmp_path):
    d = tmp_path / "skills" / "rdd-builder"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: rdd-builder\n---\n# x\n", encoding="utf-8")
    assert v4_residue_check.run(tmp_path) == []


# ---------- allowlist ----------

def test_legacy_enum_values_are_allowlisted(tmp_path):
    """feedback source / sessions phase 的历史值属允许项，不得被 R1 误报。"""
    _write_json(tmp_path / "_lib/schemas/feedback_entry_schema.json",
                {"properties": {"source": {"enum": [
                    "rdd-arch", "rdd-builder", "guide-design", "guide-plan",
                    "guide-ship", "human"]}}})
    _write_json(tmp_path / "_lib/schemas/sessions_schema.json",
                {"properties": {"phase": {"enum": ["guide-plan", "arch"]}}})
    assert v4_residue_check.run(tmp_path) == []


def test_missing_schema_files_do_not_raise(tmp_path):
    """空项目 → 不 raise，返回空。"""
    assert v4_residue_check.run(tmp_path) == []


def test_repo_itself_has_no_critical(tmp_path):
    """AC-14：本仓当前态不得被本守卫判 CRITICAL。"""
    critical = [f for f in v4_residue_check.run(REPO_ROOT) if f.severity.value == "CRITICAL"]
    assert critical == [], critical
