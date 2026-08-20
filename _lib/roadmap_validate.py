"""validate_fragment_refs: 8 rules R1-R8 for roadmap fragment integrity.

Shared by `roadmap validate-fragments` (gate) and `rdd-doctor --category roadmap-refs` (diagnostic).
Severity levels: CRITICAL (blocks plan-done in STRICT mode) / WARNING (default) / INFO.

Per Metis review (commit before this version):
  - R8 fixed: previous `if len(Set) < sum(1 for _ in Set)` was always False (Set dedups duplicates),
    so R8 never fired. Now uses Counter on raw list to preserve duplicates.
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
    """Parse main roadmap.md phase table → list of phase ids (preserves duplicates for R8 detection).

    Per Metis review: needed because R8's previous Set-based dedup made the rule never trigger.
    """
    if not main_doc_path.exists():
        return []
    text = main_doc_path.read_text(encoding="utf-8")
    phases: List[str] = []
    for line in text.splitlines():
        m = re.match(r"\|\s*(phase-\S+)\s*\|", line)
        if m:
            phases.append(m.group(1))
    return phases


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

    # R8: duplicate phase ids in main doc (fixed: Counter preserves duplicates)
    phase_id_list = _extract_main_doc_phases_with_duplicates(main_doc)
    phase_counts = Counter(phase_id_list)
    for pid, count in phase_counts.items():
        if count > 1:
            errors.append(
                ValidationError(
                    "R8", pid, f"duplicate phase id '{pid}' in main doc ({count}x)", "CRITICAL"
                )
            )
    # Dedup'd set for R1/R6 reference checks
    main_phases = set(phase_id_list)

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
