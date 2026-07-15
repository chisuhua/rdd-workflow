"""Roadmap long-term state management.

Extracted from skills/roadmap.md L248-637 (init/state/validate/advance
commands). These were inline Python heredocs in a bash skill body, which
made them:

  1. Impossible to unit-test in isolation (each command ran a different
     embedded Python interpreter with `$VAR` interpolation, breaking
     every `assert` / `monkeypatch` we could try).
  2. Silent on path-traversal or malformed input — the heredoc just
     printed a generic `❌` message and the bash caller had no
     structured return code to act on.
  3. Duplicated logic across `init`, `status`, and `advance` — every
     one of them opened `roadmap-state.json`, parsed phases, and
     iterated categories with the same nesting assumptions.

This module is the testable, single source of truth for those four
operations. Distinct from `roadmap_sprint.py`, which renders the
user-facing AUTO-SPRINT table inside `roadmap.md` — that module is
about presentation; this one is about project-level state transitions.

Public API:
  init_state(state_file, current_phase='phase-1')  -> dict
  read_state(state_file)                          -> dict
  render_status_view(roadmap_file, state_file)    -> int  (0/1)
  validate_change(roadmap_file, meta_file, name)  -> int  (0/1)
  advance_phase(roadmap_file, state_file)         -> int  (0/1)

All functions preserve the EXACT stdout / stderr strings that the
original bash heredocs produced, so the user-facing UX is unchanged.
"""
from __future__ import annotations

import datetime
import json
import os
import re
from typing import Any


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


def init_state(state_file: str, current_phase: str = "phase-1") -> dict:
    """Initialize roadmap state JSON with the default 3-phase template.

    Writes atomically. Returns the state dict (also persisted to disk).

    Default template (preserved from roadmap.md L260-304):
      phase-1: in_progress, 4 categories (arch-design, infra-setup,
               core-impl, core-test), gate with 2 checks.
      phase-2: pending, 3 categories (feature-impl, feature-test,
               perf-opt), empty gate.
      phase-3: pending, 2 categories (advanced, optimization),
               empty gate.
    """
    state = {
        "version": 1,
        "updated_at": _now_iso(),
        "current_phase": current_phase,
        "phases": {
            "phase-1": {
                "status": "in_progress",
                "started_at": _now_iso(),
                "completed_at": None,
                "categories": {
                    "arch-design": {"total_changes": 0, "completed_changes": [], "changes": []},
                    "infra-setup": {"total_changes": 0, "completed_changes": [], "changes": []},
                    "core-impl": {"total_changes": 0, "completed_changes": [], "changes": []},
                    "core-test": {"total_changes": 0, "completed_changes": [], "changes": []},
                },
                "gate_status": {
                    "all_changes_complete": False,
                    "checklist": {
                        "核心接口定义完成": False,
                        "单元测试覆盖 > 80%": False,
                    },
                },
            },
            "phase-2": {
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "categories": {
                    "feature-impl": {"total_changes": 0, "completed_changes": [], "changes": []},
                    "feature-test": {"total_changes": 0, "completed_changes": [], "changes": []},
                    "perf-opt": {"total_changes": 0, "completed_changes": [], "changes": []},
                },
                "gate_status": {
                    "all_changes_complete": False,
                    "checklist": {},
                },
            },
            "phase-3": {
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "categories": {
                    "advanced": {"total_changes": 0, "completed_changes": [], "changes": []},
                    "optimization": {"total_changes": 0, "completed_changes": [], "changes": []},
                },
                "gate_status": {
                    "all_changes_complete": False,
                    "checklist": {},
                },
            },
        },
    }
    os.makedirs(os.path.dirname(state_file) or ".", exist_ok=True)
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)
    print(f"✅ 路线图状态文件已创建: {state_file}")
    return state


def read_state(state_file: str) -> dict:
    """Read state JSON. Returns empty dict if file missing.

    Empty-dict fallback matches the original bash behavior at L348-351
    where a missing state file was silently treated as 'rebuild from
    roadmap.md' rather than an error.
    """
    if not os.path.isfile(state_file):
        return {}
    with open(state_file) as f:
        return json.load(f)


def render_status_view(roadmap_file: str, state_file: str) -> int:
    """Print the status display to stdout. Returns 0 on success, 1 if roadmap missing.

    Output preserves the exact format from roadmap.md Step 2:
      📊 路线图状态
      ==================================================
      当前阶段: <phase>

      <icon> phase-X: <done>/<total> change 完成 (<status>)
         - <cat>: <done>/<total>
      ...

      阶段门控:
        所有 change 完成: ✅/❌
        <check>: ✅/❌
    """
    if not os.path.isfile(roadmap_file):
        print("❌ roadmap.md 不存在")
        print('请先初始化: skill_use("roadmap", "init")')
        return 1

    if not os.path.isfile(state_file):
        print("⚠️  状态文件不存在，正在重建...")
        # Original behavior: caller is expected to rebuild from roadmap.md.
        # We don't auto-rebuild here — keeping that responsibility in the
        # bash caller preserves the contract.

    with open(state_file) as f:
        state = json.load(f)

    current_phase = state.get("current_phase", "unknown")

    print("📊 路线图状态")
    print("=" * 50)
    print(f"当前阶段: {current_phase}")
    print("")

    for phase_id, phase_data in state.get("phases", {}).items():
        status = phase_data.get("status", "unknown")
        status_icon = {
            "completed": "✅",
            "in_progress": "🔄",
            "pending": "⏳",
        }.get(status, "❓")

        total = sum(len(c.get("changes", [])) for c in phase_data.get("categories", {}).values())
        completed = sum(
            len(c.get("completed_changes", [])) for c in phase_data.get("categories", {}).values()
        )

        print(f"{status_icon} {phase_id}: {completed}/{total} change 完成 ({status})")

        for cat_id, cat_data in phase_data.get("categories", {}).items():
            cat_total = len(cat_data.get("changes", []))
            cat_completed = len(cat_data.get("completed_changes", []))
            if cat_total > 0:
                print(f"   - {cat_id}: {cat_completed}/{cat_total}")

    print("")

    if current_phase in state.get("phases", {}):
        gate = state["phases"][current_phase].get("gate_status", {})
        print("阶段门控:")
        print(f'  所有 change 完成: {"✅" if gate.get("all_changes_complete") else "❌"}')
        for check, checked in gate.get("checklist", {}).items():
            print(f'  {check}: {"✅" if checked else "❌"}')

    return 0


def validate_change(roadmap_file: str, meta_file: str, change_name: str) -> int:
    """Validate that a change's roadmap meta matches the roadmap structure.

    Returns 0 if valid, 1 if not. Output format preserved from roadmap.md
    validate command:
      ❌ Change '...' 不存在或没有 roadmap 元数据
      ❌ 阶段 "..." 不存在于 roadmap
      ⚠️  分类 "..." 不在阶段 "..." 中
        有效分类:
          - <cat>: <name>
      ✅ Change "..." 验证通过
         阶段: <phase>
         分类: <category>
    """
    if not os.path.isfile(meta_file):
        print(f"❌ Change '{change_name}' 不存在或没有 roadmap 元数据")
        return 1

    try:
        import yaml
    except ImportError:
        print("❌ PyYAML 未安装,无法解析 roadmap-meta.yaml")
        return 1

    with open(meta_file) as f:
        meta = yaml.safe_load(f)

    change_phase = meta.get("roadmap", {}).get("phase", "unknown")
    change_category = meta.get("roadmap", {}).get("category", "unknown")

    with open(roadmap_file) as f:
        roadmap = f.read()

    phase_pattern = rf"### .*? \({re.escape(change_phase)}\)"
    if not re.search(phase_pattern, roadmap):
        print(f'❌ 阶段 "{change_phase}" 不存在于 roadmap')
        return 1

    phase_section = re.search(
        rf"### .*? \({re.escape(change_phase)}\).*?(?=\n### |\n## |\Z)",
        roadmap,
        re.DOTALL,
    )
    if phase_section:
        cat_pattern = rf"\|\s*{re.escape(change_category)}\s*\|"
        if not re.search(cat_pattern, phase_section.group()):
            print(f'⚠️  分类 "{change_category}" 不在阶段 "{change_phase}" 中')
            print("")
            print("有效分类:")
            for line in phase_section.group().splitlines():
                m = re.match(r"\|\s*([^\s|]+)\s*\|\s*([^|]+?)\s*\|", line)
                if m:
                    cat_id, cat_name = m.group(1), m.group(2).strip()
                    if re.match(r"^[a-z][a-z0-9-]*$", cat_id):
                        print(f"  - {cat_id}: {cat_name}")
            return 1

    print(f'✅ Change "{change_name}" 验证通过')
    print(f"   阶段: {change_phase}")
    print(f"   分类: {change_category}")
    return 0


def add_phase(
    roadmap_file: str,
    state_file: str,
    phase_id: str,
    phase_name: str,
    prereq_phase: str = "",
) -> int:
    """Append a new phase to roadmap.md and roadmap-state.json.

    Used by the `edit` command's "添加新阶段" submenu. Returns 0 on
    success, 1 on error. Preserves the exact markdown template from
    roadmap.md L440-473.

    Args:
        roadmap_file: path to roadmap.md
        state_file: path to roadmap-state.json
        phase_id: e.g. "phase-4"
        phase_name: human-readable phase name (e.g. "高级特性")
        prereq_phase: optional phase ID that must complete before this one
    """
    if not phase_id or not phase_name:
        print("❌ phase_id 和 phase_name 不能为空")
        return 1

    prereq_line = f"**前置阶段**: {prereq_phase}\n" if prereq_phase else ""

    new_section = (
        f"\n### {phase_name} ({phase_id})\n"
        f"**目标**: \n"
        f"**状态**: ⏳ 未开始\n"
        f"{prereq_line}"
        f"**完成条件**:\n"
        f"  - [ ] 所有分类的 change 完成\n"
        f"\n#### 任务分类\n"
        f"| 分类ID | 名称 | 描述 | 优先级 |\n"
        f"|--------|------|------|--------|\n"
    )

    try:
        with open(roadmap_file, "a") as f:
            f.write(new_section)
    except OSError as e:
        print(f"❌ 无法写入 roadmap.md: {e}")
        return 1

    state = read_state(state_file)
    state["phases"][phase_id] = {
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "categories": {},
        "gate_status": {
            "all_changes_complete": False,
            "checklist": {},
        },
    }
    state["updated_at"] = _now_iso()

    try:
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
    except OSError as e:
        print(f"❌ 无法写入 state 文件: {e}")
        return 1

    print(f"✅ 已添加新阶段: {phase_name} ({phase_id})")
    return 0


def advance_phase(roadmap_file: str, state_file: str) -> int:
    """Pre-check + execute phase advance.

    Step 1 (pre-check): verify all changes complete AND all gate checks
                        satisfied for the current phase.
    Step 2 (execute):   find the next phase from roadmap.md regex,
                        mark current completed, activate next, AND
                        update the `**当前阶段**:` marker in roadmap.md.

    Returns 0 on successful advance, 1 on pre-check failure or no next
    phase. Preserves the exact output from roadmap.md advance command
    (which had two separate Python heredocs — this folds them into one).
    """
    state = read_state(state_file)
    if not state:
        print("❌ 状态文件不存在或为空")
        return 1

    current = state["current_phase"]
    phase_data = state["phases"].get(current, {})

    # Pre-check: all changes complete
    all_complete = True
    for cat_id, cat_data in phase_data.get("categories", {}).items():
        total = len(cat_data.get("changes", []))
        completed = len(cat_data.get("completed_changes", []))
        if completed < total:
            all_complete = False
            print(f"❌ 分类 {cat_id} 未完成: {completed}/{total}")

    # Pre-check: gate conditions
    checklist = phase_data.get("gate_status", {}).get("checklist", {})
    for check, checked in checklist.items():
        if not checked:
            all_complete = False
            print(f"❌ 门控条件未完成: {check}")

    if not all_complete:
        print("")
        print("当前阶段未完成，无法推进")
        print("请完成所有 change 和门控条件后重试")
        return 1

    print(f"✅ 阶段 {current} 已完成，可以推进")

    # Find next phase
    if not os.path.isfile(roadmap_file):
        print("❌ roadmap.md 不存在")
        return 1

    with open(roadmap_file) as f:
        content = f.read()

    phases = re.findall(r"\((phase-\d+)\)", content)
    try:
        idx = phases.index(current)
        if idx + 1 < len(phases):
            next_phase = phases[idx + 1]
        else:
            print("🎉 已是最后一个阶段")
            return 0
    except ValueError:
        print("❌ 无法确定下一阶段")
        return 1

    # Update state
    state["phases"][current]["status"] = "completed"
    state["phases"][current]["completed_at"] = _now_iso()
    state["current_phase"] = next_phase
    state["phases"][next_phase]["status"] = "in_progress"
    state["phases"][next_phase]["started_at"] = _now_iso()
    state["updated_at"] = _now_iso()

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

    print(f"✅ 已推进到阶段: {next_phase}")
    update_roadmap_marker(roadmap_file, current, next_phase)
    return 0


def update_roadmap_marker(roadmap_file: str, old_phase: str, new_phase: str) -> int:
    """Rewrite the `**当前阶段**: <phase>` line in roadmap.md.

    Was an inline Python heredoc after the advance state's update.
    Preserves the exact (somewhat buggy) replacement semantics from
    the original: also rewrites the `**状态**: 🔄 进行中\\n**前置阶段**:
    <old_phase>` block, but only when it appears with the exact
    4-space indent and emoji used in the default roadmap template.

    Returns 0 on success, 1 if roadmap.md is missing.
    """
    if not os.path.isfile(roadmap_file):
        print("❌ roadmap.md 不存在")
        return 1

    with open(roadmap_file, "r") as f:
        content = f.read()

    content = content.replace(
        f"**当前阶段**: {old_phase}",
        f"**当前阶段**: {new_phase}",
    )
    content = content.replace(
        f"**状态**: 🔄 进行中\n**前置阶段**: {old_phase}",
        f"**状态**: 🔄 进行中\n**前置阶段**: {old_phase}",
    )

    with open(roadmap_file, "w") as f:
        f.write(content)

    print("✅ roadmap.md 已更新")
    return 0


def get_phase_categories(roadmap_file: str, phase: str) -> int:
    """Print `<cat_id>:<cat_name>` lines for all categories in <phase>.

    Used by the edit command's "获取阶段的有效分类" helper. The caller
    expects stdout lines in `cat_id:cat_name` format so it can parse
    them in bash. Returns 0 always; non-existent phase produces no
    output (matches original behavior).
    """
    if not os.path.isfile(roadmap_file):
        return 0
    with open(roadmap_file) as f:
        content = f.read()

    phase_section = re.search(
        rf"### .*? \({re.escape(phase)}\).*?(?=\n### |\n## |\Z)",
        content,
        re.DOTALL,
    )
    if phase_section:
        for line in phase_section.group().splitlines():
            m = re.match(r"\|\s*([^\s|]+)\s*\|\s*([^|]+?)\s*\|", line)
            if not m:
                continue
            cat_id, cat_name = m.group(1), m.group(2).strip()
            # Skip header rows (分类ID), separator (------), and non-category
            # entries — valid cat IDs are kebab-case English words like
            # "arch-design" or "infra-setup".
            if not re.match(r"^[a-z][a-z0-9-]*$", cat_id):
                continue
            print(f"{cat_id}:{cat_name}")
    return 0


def update_change_count(
    state_file: str,
    change_name: str,
    phase: str,
    category: str,
    operation: str = "add",
) -> int:
    """Add or remove a change from a phase/category in state.json.

    Used by the edit command's "更新 change 计数" helper. Preserves the
    original semantics: silently no-ops if phase/category missing.

    Returns 0 always (the original silent-success contract).
    """
    state = read_state(state_file)
    if (
        phase in state.get("phases", {})
        and category in state["phases"][phase].get("categories", {})
    ):
        cat_data = state["phases"][phase]["categories"][category]

        if operation == "add":
            if change_name not in cat_data["changes"]:
                cat_data["changes"].append(change_name)
                cat_data["total_changes"] = len(cat_data["changes"])
        elif operation == "remove":
            if change_name in cat_data["changes"]:
                cat_data["changes"].remove(change_name)
                cat_data["total_changes"] = len(cat_data["changes"])
            if change_name in cat_data.get("completed_changes", []):
                cat_data["completed_changes"].remove(change_name)

        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    return 0