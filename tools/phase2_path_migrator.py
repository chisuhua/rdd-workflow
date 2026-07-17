#!/usr/bin/env python3
"""Phase 2 path migrator — single-skill helper move.

Migrates 46 single-skill helpers from skills/_lib/ to skills/<skill>/scripts/.
Handles 4 refactor patterns with per-skill type awareness, dry-run support, and
prose-scope control (per ADR-0021 Decision 1+3).

Patterns handled:
  source_sh  — bash `source` lines (incl. readlink, _SCRIPT_DIR, $SCRIPT_DIR, $(dirname...))
  import_py  — Python `from skills._lib.X import Y` (per ADR-0021 Decision 1)
  prose      — narrative mentions in SKILL.md (scope-controlled per ADR-0021 Decision 3)
  check_file — bash `[ -f "$VAR/_lib/X.sh" ]` test expressions
  grep_str   — `grep -E 'X.sh' "$path"` test expressions
  skip_adr   — never touch files under docs/adr/, docs/superpowers/, docs/audit/
  manual     — logged but not changed (readlink, feature.md fallback)

Usage:
    tools/phase2_path_migrator.py --dry-run [--skill guide-ship]
    tools/phase2_path_migrator.py --apply [--skill guide-ship]
    tools/phase2_path_migrator.py --audit [--skill guide-ship]
    tools/phase2_path_migrator.py --list-skills

Exit codes:
    0  success (or dry-run with no broken refs)
    1  broken refs detected (after apply)
    2  usage error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# --- Phase 2 source data: per-skill migration table ---

# Skills and the files they own (single-skill helpers from proposal table)
SINGLE_SKILL_FILES: dict[str, list[str]] = {
    "guide": ["scan-state.sh"],
    "guide-arch": [
        "arch_env_check.sh", "arch_gap_analysis.sh", "arch_done_gate.sh",
        "arch_quality_report.sh", "write_arch_handoff.sh",
        "write_arch_handoff.py", "write_arch_handoff_env.py",
    ],
    "guide-plan": [
        "plan_intake.sh", "plan_queue_overview.sh", "plan_feature_progress.sh",
        "plan_deps_candidates.sh", "plan_deps_candidates.py",
        "plan_deps_candidates_env.py",
        "plan_done_gate.sh", "plan_done_gate.py", "plan_done_gate_env.py",
    ],
    "guide-ship": [
        "ship_case_handler.sh", "ship_plan.sh", "ship_monitor.sh",
        "ship_review.sh", "ship_archive.sh", "post_archive_fill.sh",
    ],
    "propose": [
        "propose_change.sh", "propose_change.py", "validate_baseline.py",
    ],
    "execute": [
        "select_worktree.sh", "update_roadmap_progress.sh",
        "update_roadmap_progress.py", "update_roadmap_progress_env.py",
        "execute_step7.sh", "execute_step7.py", "execute_step7_env.py",
        "tasks_writeback.sh",
    ],
    "feature": [
        "feature_summary.sh", "feature_graph.sh", "feature_status.sh",
        "feature_order.sh", "feature_cli.py", "feature_view.py",
    ],
    "status": ["status_render_mode_a.sh"],
    "deps": ["deps_render_report.sh", "deps_iteration_sync.sh", "deps_output.py"],
    # N3 decision: rddf_session + hooks.sh both move to rddf-session (per ADR-0021 Decision 2)
    "rddf-session": [
        "rddf_session.py", "rddf_session_hooks.sh",
    ],
}

# Files that STAY in _lib/ (cross-skill shared)
SHARED_IN_LIB = {
    "state.sh", "state_vector.py", "state_vector_schema.json",
    "worktree.sh", "archive.sh", "discover-arch-artifacts.sh",
    "status_helpers.sh", "iteration.py",
    "gate.py", "tribunal.py", "sanitizer.py",
    "memory.py", "session_manager.py", "agents.py",
    "detectors.py", "actions.py", "event_log.py", "event_types.py",
    "lock.py", "atomic_write.py", "plugin_loader.py",
    "defaults.py", "roadmap_state.py",
    "validate_delta_targets.py",
}

# Path scopes where we touch (prose) — SKILL.md only, per ADR-0021 Decision 3
PROSE_UPDATE_SCOPES = {
    "skills/*/SKILL.md",
    "skills/INSTALL.md",  # INSTALL.md reflects current install steps
}

# Path scopes where we NEVER touch (per ADR-0021 Decision 3)
NEVER_TOUCH_SCOPES = {
    "docs/adr/",
    "docs/superpowers/",
    "docs/audit/",
    "openspec/changes/",  # proposal/design/tasks are change artifacts, frozen
}


@dataclass
class MigrationRef:
    """One path reference that needs migration."""
    file: Path
    line_no: int
    line: str
    ref_type: str  # source_sh, import_py, prose, check_file, grep_str, manual
    skill: str | None  # which skill this ref belongs to (None if shared/ambiguous)
    old_path: str
    new_path: str
    notes: str = ""


@dataclass
class MigrationReport:
    refs: list[MigrationRef] = field(default_factory=list)
    skipped: list[tuple[Path, int, str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def by_skill(self) -> dict[str, list[MigrationRef]]:
        out: dict[str, list[MigrationRef]] = {}
        for ref in self.refs:
            key = ref.skill or "_shared"
            out.setdefault(key, []).append(ref)
        return out

    @property
    def by_type(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for ref in self.refs:
            out[ref.ref_type] = out.get(ref.ref_type, 0) + 1
        return out


def resolve_skill_for_filename(filename: str) -> str | None:
    """Return skill name if filename (with or without .sh/.py extension) is single-skill, None if shared."""
    # Strip extension for comparison
    stem = filename
    for ext in (".sh", ".py"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break
    if stem in SHARED_IN_LIB or filename in SHARED_IN_LIB:
        return None
    for skill, files in SINGLE_SKILL_FILES.items():
        # Match either with or without extension
        for f in files:
            f_stem = f
            for ext in (".sh", ".py"):
                if f_stem.endswith(ext):
                    f_stem = f_stem[: -len(ext)]
                    break
            if stem == f_stem or filename == f:
                return skill
    return None


def classify_line(line: str) -> str:
    """Classify a line as source_sh, import_py, check_file, grep_str, prose, or skip."""
    stripped = line.strip()
    if not stripped:
        return "empty"
    if stripped.startswith("#"):
        # Comment — could be prose if in scope
        if "skills/_lib/" in line or "_lib/" in stripped:
            return "prose_comment"
        return "comment"
    # Python import (heredoc or direct)
    if re.search(r"from skills\._lib\.\w+", line):
        return "import_py"
    # "from skills._lib import X" (no dot after _lib) — e.g., "from skills._lib import deps_output"
    if re.search(r"from skills\._lib import \b", line):
        return "import_py"
    if "import skills._lib" in line:
        return "import_py"
    # grep structural - check BEFORE source_sh because grep lines often contain "source"
    # as a literal in the search pattern (e.g., `grep -q 'source.*_lib/X.sh'`)
    if "grep" in line and "_lib/" in line:
        return "grep_str"
    # Bash source
    if re.search(r"\bsource\b.*_lib/", line):
        return "source_sh"
    # File existence check
    if re.search(r"-f\s+.*_lib/", line) or re.search(r"\[\[?\s+-f\s+.*_lib/", line):
        return "check_file"
    # Prose narrative mention
    if "skills/_lib/" in line or "_lib/" in stripped:
        return "prose"
    return "other"


# --- Source line transformation ---

# Source line transformation is implemented inline in transform_source_sh below
# (5 modes with shared vs single-skill filename-aware branching per ADR-0021)


def transform_source_sh(line: str, skill: str | None) -> tuple[str, list[str]]:
    """Transform a bash source line. Returns (new_line, warnings).

    Handles 5 modes per ADR-0021 + Phase 1 lessons:
      Mode 1: $(dirname "${BASH_SOURCE[0]:-$0}")/[../]_lib/X.sh
              -> /scripts/X.sh (single-skill) OR /../_lib/X.sh (shared, keep)
      Mode 2: $SCRIPT_DIR/[../]_lib/X.sh -> same logic
      Mode 3: $_SCRIPT_DIR/[../]_lib/X.sh -> same logic
      Mode 4: $REPO_ROOT/skills/_lib/X.sh -> $REPO_ROOT/skills/<skill>/scripts/X.sh (single only)
      Mode 5: $(dirname "$(readlink -f ...)")/[../]_lib/X.sh -> manual (warning only)
    """
    warnings: list[str] = []
    new_line = line

    # Mode 5: readlink pattern (Phase 1 N1 parallel) - detect + warn, don't transform
    if re.search(r'\$\(dirname "\$\(readlink -f "\$\{BASH_SOURCE\[0\]:-\$0\}"\)"\)', new_line):
        warnings.append("readlink pattern detected - handle manually (per Phase 1 N1)")

    # Modes 1-3: handle BASH_SOURCE / $SCRIPT_DIR / $_SCRIPT_DIR with optional ../_lib/ prefix
    # Capture the filename so we can decide shared vs single-skill
    def make_repl(var_pattern: str, var_replacement: str):
        def repl(m: re.Match[str]) -> str:
            filename = m.group(1)
            target = resolve_skill_for_filename(filename)
            if target:
                # Single-skill: replace ../_lib/ or _lib/ with scripts/
                return f"{var_replacement}/scripts/{filename}"
            # Shared: keep ../_lib/ form (normalize to ../_lib/)
            return f"{var_replacement}/../_lib/{filename}"
        return repl

    # Mode 1: $(dirname "${BASH_SOURCE[0]:-$0}")/[../]_lib/X.sh
    new_line = re.sub(
        r'\$\(dirname "\$\{BASH_SOURCE\[0\]:-\$0\}"\)/(?:\.\./)?_lib/([\w.-]+\.sh[\w.-]*)',
        make_repl(
            '$(dirname "${BASH_SOURCE[0]:-$0}")',
            '$(dirname "${BASH_SOURCE[0]:-$0}")',
        ),
        new_line,
    )

    # Mode 2: $SCRIPT_DIR/[../]_lib/X.sh
    new_line = re.sub(
        r'\$SCRIPT_DIR/(?:\.\./)?_lib/([\w.-]+\.sh[\w.-]*)',
        make_repl('$SCRIPT_DIR', '$SCRIPT_DIR'),
        new_line,
    )

    # Mode 3: $_SCRIPT_DIR/[../]_lib/X.sh
    new_line = re.sub(
        r'\$_SCRIPT_DIR/(?:\.\./)?_lib/([\w.-]+\.sh[\w.-]*)',
        make_repl('$_SCRIPT_DIR', '$_SCRIPT_DIR'),
        new_line,
    )

    # Mode 4: $REPO_ROOT/skills/_lib/X.sh - only change single-skill
    m = re.search(r'\$REPO_ROOT/skills/_lib/([\w.-]+)', new_line)
    if m:
        filename = m.group(1)
        target_skill = resolve_skill_for_filename(filename)
        if target_skill:
            new_line = new_line.replace(
                f"$REPO_ROOT/skills/_lib/{filename}",
                f"$REPO_ROOT/skills/{target_skill}/scripts/{filename}",
            )

    # Mode 6: inline `source skills/_lib/X.sh` (no $VAR prefix, common in tests)
    # e.g., bash -c "source skills/_lib/arch_done_gate.sh"
    def repl_inline(m: re.Match[str]) -> str:
        filename = m.group(1)
        ext = m.group(2)
        target = resolve_skill_for_filename(filename)
        if target:
            return f"skills/{target}/scripts/{filename}.{ext}"
        return m.group(0)
    new_line = re.sub(
        r'skills/_lib/([\w.-]+)\.(sh|py)',
        repl_inline,
        new_line,
    )

    return new_line, warnings


# --- Python import transformation ---

def transform_import_py(line: str) -> str:
    """Transform `from skills._lib.X import Y` per ADR-0021 Decision 1.
    Each moved file gets new path `from skills.<skill>.scripts.X import Y`.
    Also handles `from skills._lib import X [as Y]` (pattern 2, no dot after _lib)."""
    def repl(m: re.Match[str]) -> str:
        module = m.group(1)
        # Strip the leading " import" we captured (we'll re-add " import " properly)
        rest = m.group(2).lstrip()
        skill = resolve_skill_for_filename(module)
        if skill:
            return f"from skills.{skill.replace('-', '_')}.scripts.{module} import {rest}"
        return m.group(0)
    # Pattern 1: "from skills._lib.MODULE import ..." (DOT pattern)
    line = re.sub(
        r"from skills\._lib\.([\w]+) import (.+)",
        repl,
        line,
    )
    # Pattern 2: "from skills._lib import X [as Y]" (no dot after _lib)
    def repl_package_import(m: re.Match[str]) -> str:
        module = m.group(1)
        alias = m.group(2).strip()
        skill = resolve_skill_for_filename(module)
        if skill:
            skill_py = skill.replace('-', '_')
            if alias:
                return f"from skills.{skill_py}.scripts import {module} {alias}"
            return f"from skills.{skill_py}.scripts import {module}"
        return m.group(0)
    line = re.sub(r"from skills\._lib import ([\w]+)(.*)", repl_package_import, line)
    return line


# --- Prose transformation (scope-controlled) ---

def transform_prose(line: str, skill: str | None) -> str:
    """Update prose `skills/_lib/X.{sh,py}` to `scripts/X.{sh,py}` in scope.
    Only call this on lines in PROSE_UPDATE_SCOPES files."""
    def repl(m: re.Match[str]) -> str:
        filename = m.group(1)
        ext = m.group(2)
        target_skill = resolve_skill_for_filename(filename)
        if target_skill:
            return f"scripts/{filename}.{ext}"
        # Shared - keep _lib/ reference but qualify
        return m.group(0)
    return re.sub(
        r"skills/_lib/([\w.-]+)\.(sh|py)",
        repl,
        line,
    )


def transform_check_file(line: str) -> str:
    """Transform bash file-existence checks like `[ -f $REPO_ROOT/skills/_lib/X.sh ]`.

    Handles:
      - $REPO_ROOT/skills/_lib/X.sh -> $REPO_ROOT/skills/<skill>/scripts/X.sh (single-skill)
      - $SCRIPT_DIR/[../]_lib/X.sh -> $SCRIPT_DIR/scripts/X.sh (single-skill) or unchanged (shared)
      - $_SCRIPT_DIR/[../]_lib/X.sh -> $_SCRIPT_DIR/scripts/X.sh (single-skill) or unchanged (shared)
      - $PROJECT_ROOT/skills/_lib/X.sh -> $PROJECT_ROOT/skills/<skill>/scripts/X.sh (single-skill)
    """
    def make_repl(var_replacement: str, include_skil: bool = False):
        def repl(m: re.Match[str]) -> str:
            filename = m.group(1)
            ext = m.group(2)
            target = resolve_skill_for_filename(filename)
            if target:
                if include_skil:
                    return f"{var_replacement}/{target}/scripts/{filename}.{ext}"
                return f"{var_replacement}/scripts/{filename}.{ext}"
            return m.group(0)
        return repl

    # $REPO_ROOT/skills/_lib/X.sh -> $REPO_ROOT/skills/<skil>/scripts/X.sh
    line = re.sub(
        r'\$REPO_ROOT/skills/_lib/([\w.-]+)\.(sh|py)',
        make_repl("$REPO_ROOT/skills", include_skil=True),
        line,
    )
    # $PROJECT_ROOT/skills/_lib/X.sh -> $PROJECT_ROOT/skills/<skil>/scripts/X.sh
    line = re.sub(
        r'\$PROJECT_ROOT/skills/_lib/([\w.-]+)\.(sh|py)',
        make_repl("$PROJECT_ROOT/skills", include_skil=True),
        line,
    )
    # $SCRIPT_DIR/[../]_lib/X.sh -> $SCRIPT_DIR/scripts/X.sh (same-skil transform)
    line = re.sub(
        r'\$SCRIPT_DIR/(?:\.\./)?_lib/([\w.-]+)\.(sh|py)',
        make_repl("$SCRIPT_DIR"),
        line,
    )
    # $_SCRIPT_DIR/[../]_lib/X.sh -> $_SCRIPT_DIR/scripts/X.sh (same-skil transform)
    line = re.sub(
        r'\$_SCRIPT_DIR/(?:\.\./)?_lib/([\w.-]+)\.(sh|py)',
        make_repl("$_SCRIPT_DIR"),
        line,
    )
    # Direct path: "skills/_lib/X.sh" -> skills/<skil>/scripts/X.sh
    line = re.sub(
        r'skills/_lib/([\w.-]+)\.(sh|py)',
        make_repl("skills", include_skil=True),
        line,
    )
    return line


def transform_grep_str(line: str) -> str:
    """Transform grep structural test patterns referencing _lib/X.sh.

    Handles:
      - `grep -q '..._lib/X.sh'` patterns (relative _lib/ form)
      - `grep -E '..._lib/X.sh'` patterns
      - Inline string literals containing `skills/_lib/X.sh`
    Single-skill refs become `skills/<skill>/scripts/X.sh`. Shared refs unchanged.
    """
    def repl_with_skill_prefix(m: re.Match[str]) -> str:
        filename = m.group(1)
        ext = m.group(2)
        target_skill = resolve_skill_for_filename(filename)
        if target_skill:
            return f"skills/{target_skill}/scripts/{filename}.{ext}"
        return m.group(0)

    def repl_relative(m: re.Match[str]) -> str:
        filename = m.group(1)
        ext = m.group(2)
        target_skill = resolve_skill_for_filename(filename)
        if target_skill:
            return f"scripts/{filename}.{ext}"
        return m.group(0)

    # skills/_lib/X.sh -> skills/<skill>/scripts/X.sh
    line = re.sub(
        r'skills/_lib/([\w.-]+)\.(sh|py)',
        repl_with_skill_prefix,
        line,
    )
    # _lib/X.sh (relative, in test grep patterns) -> scripts/X.sh
    line = re.sub(
        r'_lib/([\w.-]+)\.(sh|py)',
        repl_relative,
        line,
    )
    return line


# --- Audit logic ---

def audit_file(path: Path, target_skills: list[str] | None) -> MigrationReport:
    """Audit one file for migration candidates."""
    report = MigrationReport()
    rel = path.relative_to(REPO_ROOT)

    # Skip never-touch scopes
    rel_str = str(rel)
    for scope in NEVER_TOUCH_SCOPES:
        if rel_str.startswith(scope):
            report.skipped.append((path, 0, "scope_skip", scope))
            return report

    # Filter by skill if requested (only for skills/ files, not tests/)
    if target_skills and rel_str.startswith("skills/"):
        parts = rel.parts
        if len(parts) >= 2:
            file_skill = parts[1]
            if file_skill not in target_skills and file_skill != "_lib" and file_skill != "INSTALL.md":
                report.skipped.append((path, 0, "skill_filter", str(target_skills)))
                return report
    # Tests/ files are not filtered — they can reference any skill

    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        report.errors.append(f"read {path}: {e}")
        return report

    is_prose_scope = False
    for scope in PROSE_UPDATE_SCOPES:
        if "*" in scope:
            prefix, suffix = scope.split("*", 1)
            if str(rel).startswith(prefix) and str(rel).endswith(suffix.lstrip("/")):
                is_prose_scope = True
                break
        else:
            if rel_str == scope or rel_str.startswith(scope):
                is_prose_scope = True
                break

    for i, line in enumerate(text.splitlines(), 1):
        kind = classify_line(line)
        if kind in ("empty", "comment", "other"):
            continue

        # Per-pattern handling - ALWAYS report refs (even if transform fails)
        # so silent failures surface (Bug B fix per Metis hostile re-review)
        if kind == "import_py":
            new_line = transform_import_py(line)
            m = re.search(r"from skills\._lib\.([\w]+)", line)
            if not m:
                m = re.search(r"from skills\._lib import ([\w]+)", line)
            skill = resolve_skill_for_filename(m.group(1)) if m else None
            note = ""
            if new_line == line and m and skill:
                note = "TRANSFORM_FAILED"
            if m:
                old_path = f"skills._lib.{m.group(1)}"
                new_path = f"skills.{skill}.scripts.{m.group(1)}" if skill else "shared"
                report.refs.append(MigrationRef(
                    file=path, line_no=i, line=line, ref_type="import_py",
                    skill=skill, old_path=old_path, new_path=new_path,
                    notes=note,
                ))
        elif kind == "source_sh":
            m = re.search(r"_lib/([\w.-]+\.sh[\w.-]*)", line)
            if m:
                filename = m.group(1)
                skill = resolve_skill_for_filename(filename)
            else:
                skill = None
            new_line, warnings = transform_source_sh(line, skill)
            old = f"_lib/{m.group(1)}" if m else "_lib/..."
            note_parts = list(warnings)
            if new_line == line and not warnings:
                # No transformation, no warning -> either shared (correct) or silent fail
                if m and skill:
                    note_parts.append("TRANSFORM_FAILED")
            report.refs.append(MigrationRef(
                file=path, line_no=i, line=line, ref_type="source_sh",
                skill=skill, old_path=old,
                new_path=new_line.strip()[:80] if new_line != line else "(unchanged)",
                notes="; ".join(note_parts),
            ))
            for w in warnings:
                report.errors.append(f"{path}:{i} {w}")
        elif kind == "check_file":
            m = re.search(r"_lib/([\w.-]+)", line)
            if m:
                filename = m.group(1)
                skill = resolve_skill_for_filename(filename)
                new_line = transform_check_file(line)
                note = "" if new_line != line else ("TRANSFORM_FAILED" if skill else "shared")
                report.refs.append(MigrationRef(
                    file=path, line_no=i, line=line, ref_type="check_file",
                    skill=skill, old_path=f"_lib/{filename}",
                    new_path=new_line.strip()[:80] if new_line != line else "(unchanged)",
                    notes=note,
                ))
        elif kind == "grep_str":
            m = re.search(r"_lib/([\w.-]+)", line)
            if m:
                filename = m.group(1)
                skill = resolve_skill_for_filename(filename)
                new_line = transform_grep_str(line)
                note = "" if new_line != line else ("TRANSFORM_FAILED" if skill else "shared")
                report.refs.append(MigrationRef(
                    file=path, line_no=i, line=line, ref_type="grep_str",
                    skill=skill, old_path=f"_lib/{filename}",
                    new_path=new_line.strip()[:80] if new_line != line else "(unchanged)",
                    notes=note,
                ))
        elif kind == "prose" or kind == "prose_comment":
            if is_prose_scope:
                m = re.search(r"skills/_lib/([\w.-]+)\.(sh|py)", line)
                if m:
                    filename = m.group(1)
                    skill = resolve_skill_for_filename(filename)
                    if skill:
                        report.refs.append(MigrationRef(
                            file=path, line_no=i, line=line, ref_type="prose",
                            skill=skill, old_path=f"skills/_lib/{filename}",
                            new_path=f"scripts/{filename}",
                        ))

    return report


def audit_repo(target_skills: list[str] | None) -> MigrationReport:
    """Audit entire repo (or filtered subset) for migration candidates."""
    report = MigrationReport()

    # Files to audit: SKILL.md, INSTALL.md, tests/, skills/_lib/, tests/_lib/
    patterns = [
        "skills/*/SKILL.md",
        "skills/INSTALL.md",
        "skills/_lib/*",
        "tests/**/*.bats",
        "tests/**/*.bash",
        "tests/**/*.py",
        "tests/_lib/*.bats",
        "tests/_lib/*.bash",
        "tests/test_helper.bash",
        # Phase 2: scan moved files in per-skill scripts/ after Task 1 physical mv
        "skills/*/scripts/*.py",
        "skills/*/scripts/*.sh",
    ]
    seen: set[Path] = set()
    for pat in patterns:
        for path in REPO_ROOT.glob(pat):
            if path.is_file() and path not in seen:
                seen.add(path)
                sub = audit_file(path, target_skills)
                report.refs.extend(sub.refs)
                report.skipped.extend(sub.skipped)
                report.errors.extend(sub.errors)

    return report


def apply_refs(refs: list[MigrationRef], dry_run: bool) -> int:
    """Apply migration transformations. Returns count of changes applied."""
    # Group by file for efficiency
    by_file: dict[Path, list[MigrationRef]] = {}
    for ref in refs:
        by_file.setdefault(ref.file, []).append(ref)

    total_changes = 0
    for path, file_refs in by_file.items():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            print(f"ERROR reading {path}: {e}", file=sys.stderr)
            continue
        lines = text.splitlines(keepends=True)
        for ref in file_refs:
            idx = ref.line_no - 1
            if idx >= len(lines):
                continue
            original = lines[idx].rstrip("\n")
            if ref.ref_type == "import_py":
                new_line = transform_import_py(original)
            elif ref.ref_type == "source_sh":
                new_line, _ = transform_source_sh(original, ref.skill)
            elif ref.ref_type == "prose":
                new_line = transform_prose(original, ref.skill)
            elif ref.ref_type == "check_file":
                new_line = transform_check_file(original)
            elif ref.ref_type == "grep_str":
                new_line = transform_grep_str(original)
            else:
                continue  # skip manual / unknown
            if new_line != original:
                lines[idx] = new_line + "\n"
                total_changes += 1
        if not dry_run:
            path.write_text("".join(lines), encoding="utf-8")

    return total_changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2 path migrator (per ADR-0021)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_audit = sub.add_parser("audit", help="Find migration candidates (no changes)")
    p_audit.add_argument("--skill", action="append", help="Filter to one skill (repeatable)")

    p_apply = sub.add_parser("apply", help="Apply migrations")
    p_apply.add_argument("--skill", action="append", help="Filter to one skill (repeatable)")
    p_apply.add_argument("--dry-run", action="store_true", help="Print changes without writing")

    p_list = sub.add_parser("list-skills", help="List all single-skill files")

    args = parser.parse_args()

    if args.cmd == "list-skills":
        for skill, files in SINGLE_SKILL_FILES.items():
            print(f"{skill}:")
            for f in files:
                target = f"skills/{skill}/scripts/{f}"
                print(f"  skills/_lib/{f} → {target}")
        print(f"\n{len(SHARED_IN_LIB)} files stay in skills/_lib/ (shared)")
        return 0

    if args.cmd == "audit":
        report = audit_repo(args.skill)
        summary = {
            "total_refs": len(report.refs),
            "by_type": report.by_type,
            "by_skill": {k: len(v) for k, v in report.by_skill.items()},
            "skipped": len(report.skipped),
            "errors": len(report.errors),
        }
        print(json.dumps(summary, indent=2))
        if report.errors:
            print("\nERRORS:", file=sys.stderr)
            for e in report.errors:
                print(f"  {e}", file=sys.stderr)
        return 0

    if args.cmd == "apply":
        report = audit_repo(args.skill)
        n = apply_refs(report.refs, args.dry_run)
        print(f"{'Would change' if args.dry_run else 'Changed'}: {n} lines "
              f"across {len({r.file for r in report.refs})} files")
        if report.errors:
            print(f"\nWarnings ({len(report.errors)}):", file=sys.stderr)
            for e in report.errors:
                print(f"  {e}", file=sys.stderr)
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())