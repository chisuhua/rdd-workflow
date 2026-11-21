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


def test_r2_or_idiom_is_flagged(tmp_path):
    """`(Run rdd-arch or guide-plan to start.)` 这类 idiom 也必须报。

    scan-state.sh:669 的真实形态 —— `\brun guide-` 要求 run 紧跟 guide，漏掉了 `or guide-`。
    """
    src = tmp_path / "skills" / "demo" / "scripts"
    src.mkdir(parents=True)
    (src / "demo.py").write_text(
        'MSG = "No orphaned sessions found. Run rdd-arch or guide-plan to start."\n',
        encoding="utf-8")
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


# ---------- R4: openspec/specs normative surface ----------
#
# 口径（冻结）：扫描根 = openspec/specs/*/spec.md（非递归）；normative =
# `### Requirement:` 标题+正文 / `#### Scenario:` 标题+正文 / 正文内 fenced code
# block；不含 `## Purpose` 等散文段。豁免只能靠行内标注，禁止文件级 allowlist。


_REQUIRES_SPECS = pytest.mark.skipif(
    not (REPO_ROOT / "openspec" / "specs").is_dir(),
    reason="openspec/ is gitignored: no specs tree in this checkout",
)


def _enable_scan(project_root: Path) -> None:
    (project_root / ".rddf").mkdir(parents=True, exist_ok=True)
    (project_root / ".rddf" / "project.yaml").write_text(
        "doctor:\n  v4_residue:\n    scan_specs: true\n", encoding="utf-8")


def _spec(project_root: Path, name: str, body: str) -> Path:
    d = project_root / "openspec" / "specs" / name
    d.mkdir(parents=True, exist_ok=True)
    path = d / "spec.md"
    path.write_text(body, encoding="utf-8")
    return path


def _r4(findings):
    return [f for f in findings if "R4" in f.snippet]


def test_r4_switch_defaults_off(tmp_path):
    """AC-13：开关缺省 false ⇒ 一次 spec 扫描都不做（下游项目不受影响）。"""
    _spec(tmp_path, "demo", "### Requirement: r\nSHALL call `guide-ship`.\n")
    assert _r4(v4_residue_check.run(tmp_path)) == []


def test_r4_switch_on_reports_spec_residue(tmp_path):
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo", "### Requirement: r\nSHALL call `guide-ship`.\n")
    r4 = _r4(v4_residue_check.run(tmp_path))
    warns = [f for f in r4 if f.severity.value == "WARNING"]
    assert len(warns) == 1, r4
    assert warns[0].file == "openspec/specs/demo/spec.md"


def test_r4_scan_root_excludes_openspec_changes(tmp_path):
    """AC-1：扫描根恰为 openspec/specs/<cap>/spec.md —— changes/ 下同内容不得报。"""
    _enable_scan(tmp_path)
    archived = tmp_path / "openspec" / "changes" / "archive" / "x"
    archived.mkdir(parents=True)
    (archived / "spec.md").write_text("### Requirement: r\nSHALL call `guide-ship`.\n",
                                      encoding="utf-8")
    assert [f for f in _r4(v4_residue_check.run(tmp_path))
            if f.severity.value == "WARNING"] == []

    _spec(tmp_path, "demo", "### Requirement: r\nSHALL call `guide-ship`.\n")
    assert len([f for f in _r4(v4_residue_check.run(tmp_path))
                if f.severity.value == "WARNING"]) == 1


def test_r4_purpose_prose_is_not_normative(tmp_path):
    """口径：`## Purpose` 里的旧名是历史叙述，不报。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo",
          "# demo\n\n## Purpose\nUsed to be guide-ship. Kept for the record.\n")
    assert [f for f in _r4(v4_residue_check.run(tmp_path))
            if f.severity.value == "WARNING"] == []


def test_r4_fenced_code_block_is_normative(tmp_path):
    """代码块里的 route 枚举会被读者照抄 ⇒ 算 normative。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo",
          "### Requirement: route enum\n\n```json\n{\"route\": \"guide-ship\"}\n```\n")
    assert len([f for f in _r4(v4_residue_check.run(tmp_path))
                if f.severity.value == "WARNING"]) == 1


def test_r4_code_block_switch_off_drops_it(tmp_path):
    """AC-2：口径常量可复算 —— code_block_in=False 时同一 fixture 不报。"""
    from spec_residue_scan import scan_specs
    _spec(tmp_path, "demo",
          "### Requirement: route enum\n\n```json\n{\"route\": \"guide-ship\"}\n```\n")
    assert scan_specs(tmp_path).hits
    assert scan_specs(tmp_path, code_block_in=False).hits == []


def test_r4_requirement_title_is_matched(tmp_path):
    """口径：Requirement 标题行本身也计入（`### Requirement: fill-in-guide-plan`）。"""
    from spec_residue_scan import scan_specs
    _spec(tmp_path, "demo", "### Requirement: fill-phase-in-guide-plan\n\nbody\n")
    assert scan_specs(tmp_path).hits
    assert scan_specs(tmp_path, title_in=False).hits == []


@pytest.mark.parametrize("code", ["enum", "proposal-name", "guard", "history", "rename-history"])
def test_r4_each_allow_code_exempts(tmp_path, code):
    """AC-3 正例：五类合法引用各一条 ⇒ 不报。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo",
          "### Requirement: r\nSHALL accept `guide-ship`.\n"
          f"<!-- v4-residue:allow={code} -->\n")
    assert [f for f in _r4(v4_residue_check.run(tmp_path))
            if f.severity.value == "WARNING"] == []


@pytest.mark.parametrize("code", ["enum", "proposal-name", "guard", "history", "rename-history"])
def test_r4_without_annotation_is_reported(tmp_path, code):
    """AC-3 反例：同一行内容去掉标注 ⇒ 必报。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo", "### Requirement: r\nSHALL accept `guide-ship`.\n")
    assert len([f for f in _r4(v4_residue_check.run(tmp_path))
                if f.severity.value == "WARNING"]) == 1


def test_r4_invalid_allow_code_does_not_exempt(tmp_path):
    """拼错的 code 不得静默豁免（否则一个 typo 永久关掉守卫）。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo",
          "### Requirement: r\nSHALL accept `guide-ship`.\n"
          "<!-- v4-residue:allow=historyy -->\n")
    r4 = _r4(v4_residue_check.run(tmp_path))
    assert any("invalid allow code" in f.snippet for f in r4), r4
    assert any(f.severity.value == "WARNING" and "1 处已退役" in f.snippet for f in r4), r4


def test_r4_stale_allow_is_reported(tmp_path):
    """AC-4：标注的前一行已无命中 ⇒ 报 stale allow（白名单不腐化的唯一保障）。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo",
          "### Requirement: r\nNothing to see here.\n"
          "<!-- v4-residue:allow=guard -->\n")
    r4 = _r4(v4_residue_check.run(tmp_path))
    assert [f for f in r4 if "stale allow" in f.snippet], r4


def test_r4_mixed_same_spec_only_exempts_annotated_line(tmp_path):
    """AC-5：同一 spec 内合法引用与真实残留并存 ⇒ 只豁免前者（禁止文件级 allowlist）。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo",
          "### Requirement: a\nSHALL accept `guide-ship`.\n"
          "<!-- v4-residue:allow=enum -->\n\n"
          "### Requirement: b\nSHALL call `guide-plan` at once.\n")
    warns = [f for f in _r4(v4_residue_check.run(tmp_path))
             if f.severity.value == "WARNING"]
    assert len(warns) == 1, warns
    assert "guide-plan" in warns[0].snippet


def test_r4_annotation_at_file_head_does_not_exempt_whole_file(tmp_path):
    """文件头一条标注不得豁免全文（这是文件级 allowlist 的最短路径）。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo",
          "<!-- v4-residue:allow=history -->\n\n"
          "### Requirement: a\nSHALL call `guide-ship`.\n")
    warns = [f for f in _r4(v4_residue_check.run(tmp_path))
             if f.severity.value == "WARNING" and "1 处已退役" in f.snippet]
    assert len(warns) == 1, warns


def test_r4_inline_annotation_on_hit_line_is_ignored(tmp_path):
    """AC-18(a)：标注与命中同行 ⇒ 不豁免，且提示原因。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo",
          "### Requirement: r\nSHALL call `guide-arch` now. "
          "<!-- v4-residue:allow=guard -->\n")
    warns = [f for f in _r4(v4_residue_check.run(tmp_path))
             if f.severity.value == "WARNING"]
    assert len(warns) == 1, warns
    assert "已忽略" in warns[0].snippet


def test_r4_adjacent_hit_lines_each_annotated(tmp_path):
    """AC-18(b)：命中行紧邻时，逐行插入标注 ⇒ 两行都豁免、无 stale 误报。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo",
          "### Requirement: r\n"
          "SHALL call `guide-ship`.\n"
          "<!-- v4-residue:allow=history -->\n"
          "AND `guide-plan`.\n"
          "<!-- v4-residue:allow=history -->\n")
    r4 = [f for f in _r4(v4_residue_check.run(tmp_path))
          if f.severity.value == "WARNING"]
    assert r4 == [], r4


def test_r4_weak_wording_warns_without_annotation(tmp_path):
    """AC-6：把旧名说成现存物（`the existing`）⇒ WARNING，不豁免。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo",
          "### Requirement: r\n"
          "SHALL include `guide-arch` in addition to the existing `guide-plan`.\n")
    warns = [f for f in _r4(v4_residue_check.run(tmp_path))
             if f.severity.value == "WARNING"]
    assert len(warns) == 1, warns
    assert "措辞" in warns[0].snippet


def test_r4_annotation_wins_over_weak_wording(tmp_path):
    """AC-6 优先级：显式标注优先于措辞启发式。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo",
          "### Requirement: r\n"
          "SHALL include `guide-arch` in addition to the existing `guide-plan`.\n"
          "<!-- v4-residue:allow=guard -->\n")
    assert [f for f in _r4(v4_residue_check.run(tmp_path))
            if f.severity.value == "WARNING"] == []


def test_r4_missing_openspec_does_not_raise(tmp_path):
    """AC-11：没有 openspec/ 的项目 ⇒ 不 raise。"""
    _enable_scan(tmp_path)
    assert v4_residue_check.run(tmp_path) != []   # only the INFO summary
    assert all(f.severity.value == "INFO" for f in v4_residue_check.run(tmp_path))


def test_r4_checked_zero_is_not_clean(tmp_path):
    """AC-12：checked 0 ⇒ INFO 明示「不等于 clean」，不得报「无残留」。"""
    _enable_scan(tmp_path)
    r4 = _r4(v4_residue_check.run(tmp_path))
    assert len(r4) == 1, r4
    assert r4[0].severity.value == "INFO"
    assert "checked 0" in r4[0].snippet
    assert "不等于 clean" in r4[0].snippet


def test_r4_summary_reports_files_scanned(tmp_path):
    """AC-12：有 spec 时报告输出扫描文件数。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "a", "### Requirement: a\nSHALL call `guide-ship`.\n")
    _spec(tmp_path, "b", "### Requirement: b\nclean.\n")
    r4 = _r4(v4_residue_check.run(tmp_path))
    summary = [f for f in r4 if "checked" in f.snippet]
    assert summary and "checked 2 spec file(s)" in summary[0].snippet, r4


def test_r4_mutation_inject_then_remove(tmp_path):
    """AC-10：注入一处新残留 ⇒ 报出；撤掉 ⇒ 不报。"""
    _enable_scan(tmp_path)
    _spec(tmp_path, "demo", "### Requirement: r\nclean.\n")
    assert [f for f in _r4(v4_residue_check.run(tmp_path))
            if f.severity.value == "WARNING"] == []

    _spec(tmp_path, "demo", "### Requirement: r\nSHALL call `guide-spec`.\n")
    assert len([f for f in _r4(v4_residue_check.run(tmp_path))
                if f.severity.value == "WARNING"]) == 1

    _spec(tmp_path, "demo", "### Requirement: r\nclean.\n")
    assert [f for f in _r4(v4_residue_check.run(tmp_path))
            if f.severity.value == "WARNING"] == []


def test_r4_token_word_boundary(tmp_path):
    """`guide-plan-quick-finish` 是**提案名**，不是 stage ⇒ 不得前缀命中。"""
    from spec_residue_scan import scan_specs
    _spec(tmp_path, "demo",
          "### Requirement: r\nSHALL reference the `guide-plan-quick-finish` proposal.\n")
    assert scan_specs(tmp_path).hits == []


@_REQUIRES_SPECS
def test_r4_repo_residue_constant():
    """AC-9：本仓的已知残留基线。

    两个口径分开断言（否则「补标注」与「真清理」无法区分）：
      - **未豁免**（= 台账待办，Phase 1 的判据）：66 处 / 49 块 / 24 份
      - 含已豁免（机器看到的总量）：325 处 / 176 块 / 46 份

    历史：2026-11-20 首次冻结 350 / 192 / 46（0 豁免）；
    `align-spec-residue-prior-18` 把 18 份已签批 spec 的 120 行落成标注/改指（350→191/111/31）；
    `annotate-spec-residue-guard-batch3` 把 4 份 guard spec 的 52 行标成 guard/rename-history（→102/69/27）；
    `annotate-spec-residue-guard-batch4` 把 3 份的 31 行落成标注/改指/注记（→66/49/24）。
    ⚠️ Phase 1 的每个改动都必须在同一提交更新这些常数，否则它会在下次运行时被读成 regression。
    """
    from spec_residue_scan import scan_specs
    result = scan_specs(REPO_ROOT)
    assert result.files_scanned == 165, result.files_scanned

    unexempted = [h for h in result.hits if not h.category]
    assert len(unexempted) == 66, len(unexempted)
    assert len({(h.file, h.block_line) for h in unexempted}) == 49
    assert len({h.file for h in unexempted}) == 24

    assert len(result.hits) == 325, len(result.hits)
    assert len(result.blocks()) == 176, len(result.blocks())
    assert len({h.file for h in result.hits}) == 46
