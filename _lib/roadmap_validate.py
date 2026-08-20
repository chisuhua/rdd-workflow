r"""validate_fragment_refs: 8 rules R1-R8 for roadmap fragment integrity.

Shared by `roadmap validate-fragments` (gate) and `rdd-doctor --category roadmap-refs` (diagnostic).
Severity levels: CRITICAL (blocks plan-done in STRICT mode) / WARNING (default) / INFO.

Per Metis review (commit before this version):
  - R8 fixed: previous `if len(Set) < sum(1 for _ in Set)` was always False (Set dedups duplicates),
    so R8 never fired. Now uses Counter on (phase_id, theme) tuple to detect genuine
    row-level duplicates while tolerating nested-phase main docs that legitimately have
    the same phase id appearing multiple times with different themes.

Per Oracle recommendation:
  - R4 regex strict: `^phase-\d+(\.\d+)?$` (rejects `phase-1-2` nested, allows `phase-2.1` sub-phase).
"""
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

from _lib.roadmap_state import load_fragments


@dataclass
class ValidationError:
    rule: str
    fragment_id: str
    message: str
    severity: str  # CRITICAL | WARNING | INFO

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule} {self.fragment_id}: {self.message}"


def _extract_main_doc_phases(main_doc_path: Path) -> Set[str]:
    """Parse main roadmap.md phase table → set of phase ids (deduplicated)."""
    if not main_doc_path.exists():
        return set()
    text = main_doc_path.read_text(encoding="utf-8")
    phases: Set[str] = set()
    for line in text.splitlines():
        m = re.match(r"\|\s*(phase-\S+)\s*\|", line)
        if m:
            phases.add(m.group(1))
    return phases


def _extract_main_doc_phases_with_duplicates(main_doc_path: Path) -> List[str]:
    """Parse main roadmap.md phase table → list of phase ids (preserves duplicates for R8 detection)."""
    if not main_doc_path.exists():
        return []
    text = main_doc_path.read_text(encoding="utf-8")
    phases: List[str] = []
    for line in text.splitlines():
        m = re.match(r"\|\s*(phase-\S+)\s*\|", line)
        if m:
            phases.append(m.group(1))
    return phases


def _extract_main_doc_phase_rows(main_doc_path: Path) -> List[tuple]:
    """Parse main roadmap.md phase table → list of (phase_id, theme) tuples.

    Used by R8 for nested-phase compatibility: the same phase id may appear
    multiple times with different themes (one row per sub-phase/theme), so
    R8 should only flag genuine duplicates where (phase_id, theme) collide.
    """
    if not main_doc_path.exists():
        return []
    text = main_doc_path.read_text(encoding="utf-8")
    rows: List[tuple] = []
    for line in text.splitlines():
        m = re.match(r"\|\s*(phase-\S+)\s*\|\s*([^|]*?)\s*\|", line)
        if m:
            theme = m.group(2).strip()
            if not theme:
                theme = "(empty)"
            rows.append((m.group(1), theme))
    return rows


def validate_fragment_refs(project_root: str) -> List[ValidationError]:
    """Run all 8 rules. Returns list of ValidationError (may be empty).

    Args:
        project_root: Absolute path to the project root (where .rddf/ lives).

    Returns:
        List of ValidationError; empty list = no issues found.
    """
    base = Path(project_root)
    fragments_dir = base / ".rddf" / "roadmap"
    main_doc = base / ".rddf" / "roadmap.md"
    errors: List[ValidationError] = []

    # R7: fragments_dir missing (backward compat, WARNING only)
    if not fragments_dir.exists():
        errors.append(
            ValidationError(
                "R7", "<project>", "fragments_dir missing (v1 handoff backward compat)", "WARNING"
            )
        )
        return errors  # No further checks possible

    # R8: duplicate (phase_id, theme) rows in main doc
    # Per Oracle review (P0): nested-phase main docs legitimately have the same
    # phase id appearing multiple times with different themes (one row per
    # sub-phase/theme under the parent phase). R8 should only flag genuine
    # duplicates where (phase_id, theme) collide — i.e. the same phase+theme
    # appears in the skeleton table more than once, which is always a typo.
    phase_rows = _extract_main_doc_phase_rows(main_doc)
    row_counts = Counter(phase_rows)
    for (pid, theme), count in row_counts.items():
        if count > 1:
            errors.append(
                ValidationError(
                    "R8",
                    pid,
                    f"duplicate row in main doc phase skeleton: phase='{pid}' theme='{theme}' ({count}x)",
                    "CRITICAL",
                )
            )
    # Dedup'd set for R1/R6 reference checks
    main_phases = {pid for (pid, _) in phase_rows}

    # Load all fragments
    fragments = load_fragments(str(fragments_dir), include_archived=True)
    ids_seen: Set[str] = set()

    # R4 regex: strict per Oracle recommendation (rejects nested, allows single sub-phase)
    R4_RE = re.compile(r"^phase-\d+(\.\d+)?$")

    for frag in fragments:
        # R2: id uniqueness
        if frag.id in ids_seen:
            errors.append(
                ValidationError("R2", frag.id, "duplicate fragment id (already seen)", "CRITICAL")
            )
        ids_seen.add(frag.id)

        # R3: kind enum
        if frag.kind not in ("phase", "feature"):
            errors.append(
                ValidationError(
                    "R3", frag.id, f"kind='{frag.kind}' must be 'phase' or 'feature'", "CRITICAL"
                )
            )

        # R4: phase id naming (strict pattern)
        if frag.kind == "phase" and not R4_RE.match(frag.id):
            errors.append(
                ValidationError(
                    "R4",
                    frag.id,
                    f"phase id '{frag.id}' does not match pattern phase-N(.M)?",
                    "CRITICAL",
                )
            )

        # R5: feature must have non-empty phase_refs (WARNING — not all features need refs)
        if frag.kind == "feature" and not frag.phase_refs:
            errors.append(
                ValidationError(
                    "R5", frag.id, "feature fragment must have non-empty phase_refs", "WARNING"
                )
            )

        # R6: phase fragment id must be in main doc
        if frag.kind == "phase" and frag.id not in main_phases:
            errors.append(
                ValidationError(
                    "R6",
                    frag.id,
                    f"phase id '{frag.id}' not registered in main doc phase table",
                    "CRITICAL",
                )
            )

        # R1: feature.phase_refs must reference main_doc phases
        for ref in frag.phase_refs:
            if ref not in main_phases:
                errors.append(
                    ValidationError(
                        "R1",
                        frag.id,
                        f"phase_refs references '{ref}' not in main doc",
                        "CRITICAL",
                    )
                )

    return errors
