"""Structured deps analysis output.

`deps-analysis.json` is the machine-readable counterpart to
`.rddf/state/.deps-output.md` (the human-readable markdown report).
It lives at `.rddf/state/deps-analysis.json` and is the **preferred
source** for downstream consumers (notably the iteration.json sync
hook in `deps.md` Step 6 and any future "sprint planner" tooling).

Why a separate JSON file rather than parsing the markdown?
- The markdown format is for human eyes and may evolve (column
  reordering, additional columns, footnotes). Regex-parse-then-update
  is fragile.
- The JSON contract here is locked by a JSON Schema and by
  `tests/integration/test_deps_analysis.py`. Breaking changes require
  bumping `version`.
- Downstream consumers (iteration sync, future planner) want
  O(structure), not O(text).

Schema (v1):
- `version`: int = 1
- `updated_at`: ISO 8601 timestamp
- `fallback`: bool. True when deps ran in static-only mode (AI subagent
  unavailable). Consumers should treat `semantic_deps` and
  `suggestions` as empty/absent in this case.
- `changes`: dict[name, ChangeAnalysis]
- `execution_order`: list[name] in recommended order (already merged
  with parallel groups: items at the same index may run together)

ChangeAnalysis:
- `name`: str
- `phase` / `category`: from roadmap-meta.yaml (may be null)
- `status`: enum "ready" | "blocked_by" | "prerequisite" | "conflict"
- `blocker`: change name that hard-blocks this one (null if ready)
- `blocks`: list[change name] this change blocks
- `parallel_group`: int. 0 = first wave (no deps), 1 = depends on wave 0, ...
- `conflicts`: list[change name] with file-level conflicts
- `confidence`: "high" | "low" (low = AI-inferred only, no static evidence)
- `recommendation`: human-readable execution hint
"""
from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from skills._lib.core.lock import FileLock, LockTimeout

logger = logging.getLogger(__name__)

ANALYSIS_PATH_TEMPLATE = ".rddf/state/deps-analysis.json"
SCHEMA_VERSION = 1
_LOCK_TIMEOUT = 5.0


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _atomic_write(path: str, data: dict) -> None:
    # v2.0.3: delegate to shared atomic_write helper (Wave 3.1).
    from skills._lib.core.atomic_write import atomic_write_json
    atomic_write_json(path, data)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_analysis(
    changes: list[dict],
    execution_order: Optional[list[str]] = None,
    fallback: bool = True,
) -> dict:
    """Build a deps-analysis.json structure from per-change records.

    `changes` is a list of dicts, one per analyzed change, each with
    fields:
      - name (str, required)
      - phase, category (str | None)
      - status: "ready" | "blocked_by" | "prerequisite" | "conflict"
      - blocker (str | None)
      - blocks (list[str])
      - parallel_group (int)
      - conflicts (list[str])
      - confidence (str)
      - recommendation (str)

    `execution_order` defaults to the input order, filtered to only
    include names that appear in `changes`.
    """
    change_map = {}
    for c in changes:
        if "name" not in c:
            raise ValueError("each change record requires 'name'")
        # Normalize defaults
        record = {
            "name": c["name"],
            "phase": c.get("phase"),
            "category": c.get("category"),
            "status": c.get("status", "ready"),
            "blocker": c.get("blocker"),
            "blocks": list(c.get("blocks", [])),
            "parallel_group": int(c.get("parallel_group", 0)),
            "conflicts": list(c.get("conflicts", [])),
            "confidence": c.get("confidence", "high"),
            "recommendation": c.get("recommendation", ""),
        }
        change_map[c["name"]] = record

    if execution_order is None:
        execution_order = [c["name"] for c in changes]
    else:
        # Filter to only include known changes, preserving order
        known = set(change_map.keys())
        execution_order = [n for n in execution_order if n in known]

    return {
        "version": SCHEMA_VERSION,
        "updated_at": _now_iso(),
        "fallback": fallback,
        "changes": change_map,
        "execution_order": execution_order,
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def write_analysis(project_root: str, data: dict) -> str:
    """Write deps-analysis.json atomically with merge-on-save by change name.

    See iteration.save for the rationale on merge-on-save. Briefly:
    two hooks both reading state, both mutating different entries,
    second save overwriting first is the lost-update bug. Merging
    inside the lock prevents it.

    Raises LockTimeout on contention beyond timeout.
    """
    path = os.path.join(project_root, ANALYSIS_PATH_TEMPLATE)
    lock_path = path + ".lock"
    with FileLock(lock_path, timeout=_LOCK_TIMEOUT):
        # Re-read inside the lock and merge by change name. Incoming wins.
        existing = _load_unlocked(path)
        if existing is not None:
            data = dict(data)
            existing_by_name = dict(existing.get("changes", {}))
            existing_by_name.update(data.get("changes", {}))
            data["changes"] = existing_by_name
            data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        _atomic_write(path, data)
    logger.debug("deps-analysis.json written to %s (%d changes)", path, len(data.get("changes", {})))
    return path


def _load_unlocked(path: str) -> Optional[dict]:
    """Read deps-analysis.json without acquiring the lock."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict) or data.get("version") != SCHEMA_VERSION:
        return None
    if "changes" not in data or not isinstance(data["changes"], dict):
        return None
    return data


def load_analysis(project_root: str) -> Optional[dict]:
    """Load deps-analysis.json. Returns None if missing or invalid.

    Consumers should treat None as "deps has not run yet" and skip
    iteration sync. The deps.md Step 6 hook falls back to markdown
    parsing when JSON is unavailable.
    """
    path = os.path.join(project_root, ANALYSIS_PATH_TEMPLATE)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("deps-analysis.json at %s unreadable: %s", path, e)
        return None
    if not isinstance(data, dict) or data.get("version") != SCHEMA_VERSION:
        logger.warning(
            "deps-analysis.json at %s has wrong version: %s (expected %s)",
            path, data.get("version"), SCHEMA_VERSION,
        )
        return None
    if "changes" not in data or not isinstance(data["changes"], dict):
        logger.warning("deps-analysis.json at %s has malformed 'changes' field", path)
        return None
    return data


# ---------------------------------------------------------------------------
# Iteration sync helper (used by deps.md Step 6)
# ---------------------------------------------------------------------------

def sync_iteration_from_analysis(project_root: str, iteration_module: Any) -> int:
    """Sync iteration.json from deps-analysis.json.

    Returns the number of changes updated. 0 means nothing to do
    (deps-analysis.json missing, or all changes already up to date).
    Raises nothing on failure: logs and returns 0.
    """
    analysis = load_analysis(project_root)
    if analysis is None:
        return 0

    data = iteration_module.load(project_root)
    count = 0
    for name, info in analysis.get("changes", {}).items():
        kwargs = {
            "name": name,
            "blocker": info.get("blocker"),
            "parallel_group": info.get("parallel_group", 0),
            "conflicts": info.get("conflicts", []),
        }
        data = iteration_module.set_deps_info(data, **kwargs)
        count += 1
    if count > 0:
        iteration_module.save(project_root, data)
    return count


# ---------------------------------------------------------------------------
# Markdown fallback parser (P3-4d: extracted from deps.md Step 6 inline heredoc)
# ---------------------------------------------------------------------------

DEPS_OUTPUT_MD_PATH = ".rddf/state/.deps-output.md"


def parse_markdown_fallback(project_root: str) -> Optional[List[dict]]:
    """Parse .deps-output.md as fallback when deps-analysis.json is missing/stale.

    Returns list of change records compatible with build_analysis(), or None
    when file is missing/malformed/has no Change 状态表. Records carry
    confidence='low' to signal markdown-fallback origin.
    """
    path = os.path.join(project_root, DEPS_OUTPUT_MD_PATH)
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None

    changes_info: Dict[str, dict] = {}

    status_table = re.search(
        r"## Change 状态表\n\n\|.*?\n\|.*?\n((?:\|.*?\n)+)",
        text,
    )
    if status_table:
        rows = status_table.group(1).strip().split("\n")
        for idx, row in enumerate(rows):
            cells = [c.strip() for c in row.strip("|").split("|")]
            if len(cells) < 2:
                continue
            name = cells[0]
            if not name or name == "—":
                continue
            blocker = (
                cells[2]
                if len(cells) > 2 and cells[2] not in ("—", "")
                else None
            )
            changes_info[name] = {
                "blocker": blocker,
                "parallel_group": idx if blocker else 0,
                "conflicts": [],
            }

    conflicts_section = re.search(
        r"## 冲突警告.*?\n(.*?)(?=\n## |\Z)",
        text,
        re.DOTALL,
    )
    if conflicts_section:
        for line in conflicts_section.group(1).split("\n"):
            m = re.search(r"(\S+)\s+←→\s+(\S+):", line)
            if not m:
                continue
            a, b = m.group(1), m.group(2)
            for n in (a, b):
                changes_info.setdefault(
                    n, {"blocker": None, "parallel_group": 0, "conflicts": []}
                )
                existing = changes_info[n].get("conflicts", [])
                other = b if n == a else a
                if other not in existing:
                    existing.append(other)
                changes_info[n]["conflicts"] = existing

    if not changes_info:
        return None

    return [
        {
            "name": name,
            "status": "blocked_by" if info.get("blocker") else "ready",
            "blocker": info.get("blocker"),
            "blocks": [],
            "parallel_group": info.get("parallel_group", 0),
            "conflicts": info.get("conflicts", []),
            "confidence": "low",
            "recommendation": "",
        }
        for name, info in changes_info.items()
    ]


# ---------------------------------------------------------------------------
# render_markdown_report (P3-4e: extracted from deps.md Step 5 lines 483-642)
# ---------------------------------------------------------------------------


def render_markdown_report(
    candidates,
    project_root,
    ai_result_file=None,
    roadmap_current_phase=None,
):
    """Render the deps.md .rddf/state/.deps-output.md human-readable report.

    Args:
        candidates: list of change names to include
        project_root: for reading openspec/changes/<name>/{design.md,roadmap-meta.yaml}
        ai_result_file: optional path to .rddf/state/.deps-ai-result.json (AI subagent output)
        roadmap_current_phase: optional current phase for out-of-phase detection

    Returns:
        Complete markdown report as a string. Caller writes to file.

    Behavior preserved from inline version (deps.md lines 483-642):
    - Mermaid graph with double-bracket [[name]] markers for skeleton changes
    - Phase precheck table (in-phase vs out-of-phase vs missing roadmap-meta)
    - Change status table (ready vs blocked_by from AI hard deps)
    - Recommended execution order (first candidate)
    - Conflict warnings placeholder
    - AI analysis section (rich if ai_result_file exists, fallback otherwise)
    """
    from datetime import datetime, timezone
    lines = []
    timestamp = datetime.now(timezone.utc).isoformat()

    lines.append("# 依赖分析报告")
    lines.append("")
    lines.append(f"生成时间: {timestamp}")
    lines.append(f"候选 changes: {len(candidates)}")
    lines.append("")

    # Mermaid graph
    lines.append("## 依赖图 (Mermaid)")
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart LR")
    for name in candidates:
        design_path = os.path.join(project_root, "openspec", "changes", name, "design.md")
        if not os.path.isfile(design_path):
            lines.append(f"    {name}[[{name}]]  %% skeleton change %% ")
        else:
            lines.append(f"    {name}[{name}]")
    lines.append("```")
    lines.append("")

    # Phase precheck
    lines.append("## 阶段预检")
    lines.append("")
    lines.append("基于每 change 的 `roadmap-meta.yaml`：")
    lines.append("")
    lines.append("| Change | Phase | Category | 状态 |")
    lines.append("|--------|-------|----------|------|")
    for name in candidates:
        meta_file = os.path.join(
            project_root, "openspec", "changes", name, "roadmap-meta.yaml"
        )
        if os.path.isfile(meta_file):
            meta_content = open(meta_file).read()
            phase_match = re.search(r'^\s*phase:\s*"?([^"\s]+)"?', meta_content, re.MULTILINE)
            category_match = re.search(r'^\s*category:\s*"?([^"\s]+)"?', meta_content, re.MULTILINE)
            phase = phase_match.group(1) if phase_match else ""
            category = category_match.group(1) if category_match else ""
            if roadmap_current_phase and phase and phase != roadmap_current_phase:
                lines.append(f"| {name} | {phase} | {category} | ⚠️ 不在当前阶段 ({roadmap_current_phase}) |")
            else:
                lines.append(f"| {name} | {phase} | {category} | ✅ 在阶段内 |")
        else:
            lines.append(f"| {name} | (compat) | (compat) | ⚠️ 无 roadmap-meta |")
    lines.append("")

    # Change status table
    lines.append("## Change 状态表")
    lines.append("")
    lines.append("| Change | 状态 | 推荐 | 备注 |")
    lines.append("|--------|------|------|------|")

    ai_blockers = {}
    if ai_result_file and os.path.isfile(ai_result_file):
        try:
            with open(ai_result_file) as f:
                ai_data = json.load(f)
            for d in ai_data.get("ai_deps", []):
                if d.get("kind") == "hard":
                    ai_blockers[d.get("to")] = d.get("from", "")
        except (json.JSONDecodeError, OSError):
            pass

    for name in candidates:
        design_path = os.path.join(project_root, "openspec", "changes", name, "design.md")
        is_skeleton = "" if os.path.isfile(design_path) else "📋 skeleton"
        if name in ai_blockers:
            lines.append(f"| {name} | ⚠️ blocked_by | {ai_blockers[name]} | {is_skeleton} |")
        else:
            lines.append(f"| {name} | ✅ ready | 第 1 | {is_skeleton} |")
    lines.append("")

    # Recommended execution order
    lines.append("## 推荐执行顺序")
    lines.append("")
    first = candidates[0] if candidates else "none"
    lines.append(f"1. `{first}` ← 第一个候选")
    lines.append("")

    # Conflict warnings placeholder
    lines.append("## 冲突警告")
    lines.append("")
    lines.append("（如有文件冲突将列于此处）")
    lines.append("")

    # AI analysis
    lines.append("## 🧠 AI 分析建议")
    lines.append("")

    if ai_result_file and os.path.isfile(ai_result_file):
        lines.append("")
        lines.append(f"**子代理语义分析结果** (来源: `{ai_result_file}`):")
        lines.append("")
        try:
            with open(ai_result_file) as f:
                ai_data = json.load(f)
            ai_deps = ai_data.get("ai_deps", [])
            suggestions = ai_data.get("suggestions", [])
            if ai_deps:
                lines.append("**AI 识别的额外依赖** (低置信度, 仅作参考):")
                lines.append("")
                for d in ai_deps:
                    kind = d.get("kind", "soft")
                    reason = d.get("reason", "")
                    from_name = d.get("from", "")
                    to_name = d.get("to", "")
                    lines.append(f"- `{from_name}` → `{to_name}` ({kind}): {reason}")
            if suggestions:
                lines.append("")
                lines.append("**重组建议** (仅建议不执行):")
                lines.append("")
                for s in suggestions:
                    change = s.get("change", "")
                    action = s.get("action", "")
                    reason = s.get("reason", "")
                    pf = s.get("parent_feature")
                    if pf:
                        lines.append(f"- `{change}`: {action} — {reason} (parent_feature: {pf})")
                    else:
                        lines.append(f"- `{change}`: {action} — {reason}")
        except (json.JSONDecodeError, OSError):
            pass
        else:
            return "\n".join(lines)

    # Fallback
    lines.append("")
    lines.append("⚠️ **AI 语义分析未启用 (fallback)** - 子代理不可用或调用失败, 详见 deps.md Step 3f")
    lines.append("以下内容为基于静态三轴分析（文件冲突、ADR 引用、接口依赖）的结论。")
    lines.append("AI 子代理语义分析功能（语义依赖、粒度评估、重组建议）待子代理可用时启用。")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# merge_manual_deps: merge human-authored overrides from roadmap-meta.yaml
# ---------------------------------------------------------------------------


def _load_manual_overrides(project_root: str, name: str) -> Optional[dict]:
    """Read manual_deps / manual_blocks from a change's roadmap-meta.yaml.

    Returns a dict with optional keys ``manual_deps`` and ``manual_blocks``
    (each a list[str]) if the file exists and parses. Returns None if the
    file is missing or malformed (a warning is logged on malformed YAML).

    The returned dict only contains keys that are actually present in the
    yaml's ``roadmap:`` section - callers should use ``.get()`` to check.
    """
    meta_path = os.path.join(
        project_root, "openspec", "changes", name, "roadmap-meta.yaml"
    )
    if not os.path.isfile(meta_path):
        return None
    try:
        import yaml
    except ImportError:
        logger.warning(
            "PyYAML not installed; cannot parse roadmap-meta.yaml for %s", name
        )
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as e:
        logger.warning(
            "malformed roadmap-meta.yaml at %s: %s; skipping manual deps",
            meta_path, e,
        )
        return None
    if not isinstance(meta, dict):
        return None
    roadmap = meta.get("roadmap")
    if not isinstance(roadmap, dict):
        return None
    out: dict = {}
    md = roadmap.get("manual_deps")
    if isinstance(md, list):
        out["manual_deps"] = [str(x) for x in md if isinstance(x, str)]
    mb = roadmap.get("manual_blocks")
    if isinstance(mb, list):
        out["manual_blocks"] = [str(x) for x in mb if isinstance(x, str)]
    return out if out else None


def merge_manual_deps(changes: list[dict], project_root: str) -> list[dict]:
    """Merge human-authored dependency overrides from roadmap-meta.yaml.

    For each change in ``changes``, reads
    ``openspec/changes/<name>/roadmap-meta.yaml``. If the file contains
    ``manual_deps`` or ``manual_blocks`` under the ``roadmap:`` section,
    merges them into the change record:

    - ``manual_deps`` (this change depends on others):
      * If the change's ``blocker`` is not already set by static analysis,
        set it to the first entry in ``manual_deps``.
      * Append any ``manual_deps`` entries that are not already in the
        change's ``blocks`` list.
    - ``manual_blocks`` (this change is a prerequisite for others):
      * For each blocked_change in ``manual_blocks``, find that change in
        the list and, if its ``blocker`` is not already set, set its
        ``blocker`` to this change's name.

    When a manual override differs from the static-analysis blocker or
    adds to ``blocks``, the change's ``recommendation`` is annotated with
    ``"manual override"`` so downstream renderers can surface it.

    The ``conflicts`` field is never modified by this function.

    Gracefully skips changes whose roadmap-meta.yaml is missing or
    malformed (a warning is logged for malformed YAML).

    Args:
        changes: list of change records (mutated in place and returned).
        project_root: path to project root for reading roadmap-meta.yaml.

    Returns:
        The same ``changes`` list (mutated in place).
    """
    by_name: Dict[str, dict] = {
        c["name"]: c for c in changes if c.get("name")
    }

    for change in changes:
        name = change.get("name")
        if not name:
            continue
        overrides = _load_manual_overrides(project_root, name)
        if overrides is None:
            continue

        manual_deps = overrides.get("manual_deps")
        manual_blocks = overrides.get("manual_blocks")

        annotated = False

        if manual_deps:
            if not change.get("blocker") and manual_deps:
                change["blocker"] = manual_deps[0]
                annotated = True
            existing_blocks = change.setdefault("blocks", [])
            for dep in manual_deps:
                if dep not in existing_blocks:
                    existing_blocks.append(dep)
                    annotated = True

        if manual_blocks:
            for blocked_name in manual_blocks:
                blocked_change = by_name.get(blocked_name)
                if blocked_change is None:
                    continue
                if not blocked_change.get("blocker"):
                    blocked_change["blocker"] = name
                    blocked_change.setdefault("blocks", [])
                    if name not in blocked_change["blocks"]:
                        blocked_change["blocks"].append(name)
                    rec = blocked_change.get("recommendation", "") or ""
                    if "manual override" not in rec:
                        blocked_change["recommendation"] = (
                            (rec + " " if rec else "") + "manual override"
                        ).strip()

        if annotated:
            rec = change.get("recommendation", "") or ""
            if "manual override" not in rec:
                change["recommendation"] = (
                    (rec + " " if rec else "") + "manual override"
                ).strip()

    return changes
