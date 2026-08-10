"""skills/guide-design/scripts/design_content_review.py — improvements-layer review (D4).

D4: improvements-layer checks (5 sections, ADR refs, acceptance checkboxes,
head fields, HOW-leakage heuristic warning). Returns list of error/warning
strings (empty == pass). HOW-leakage findings are emitted with the
"[HOW-LEAKAGE-WARN]" prefix so callers can distinguish advisory warnings
from structural errors. Severity (warning vs blocking) is decided upstream
by STRICT_DESIGN_GATE; HOW-leakage warnings never block by default.

Openspec proposal-layer checks (length / ADR / scope) live in
skills/propose/scripts/propose_quality_check.py::run_design_checks, which
also calls the same HOW-leakage detector so both layers share the format.
"""
import re
import sys
from pathlib import Path

# HOW-leakage detector import. Lives at top-level _lib/ (see shim in
# skills/_lib/__init__.py). When this module is invoked as a script,
# the project root is already on sys.path via the bash wrapper.
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from _lib import proposal_review  # type: ignore
except ImportError:  # pragma: no cover - shim fallback
    proposal_review = None


REQUIRED_SECTIONS = ["架构依据", "范围", "关键场景", "技术约束", "验收标准"]
REQUIRED_HEAD = ["阶段", "分类", "类型"]
ADR_RE = re.compile(r"ADR-\d{4}")
CHECKBOX_RE = re.compile(r"^- \[[ x]\] ", re.MULTILINE)


def review_improvements(md: str) -> list[str]:
    """Run all improvements-layer checks. Returns list of error/warning messages.

    Empty list means pass. Each item is a human-readable string:
      - Structural errors (missing fields, missing sections, no ADR ref,
        no checkboxes) — decided by STRICT_DESIGN_GATE upstream.
      - HOW-leakage warnings (prefix "[HOW-LEAKAGE-WARN]") — advisory only,
        never block by default.

    Per design (openspec/changes/add-proposal-how-leakage-warning):
      HOW-leakage warnings use the same WarningRecord format as the
      proposal-layer review (skills/propose/scripts/propose_quality_check.py)
      so reviewers see consistent output across both layers.
    """
    errors: list[str] = []

    for field in REQUIRED_HEAD:
        if not re.search(rf"\*\*{field}\*\*:\s*\S", md):
            errors.append(f"missing head field: {field}")

    for section in REQUIRED_SECTIONS:
        if not re.search(rf"^## {section}\s*$", md, re.MULTILINE):
            errors.append(f"missing section: {section}")

    if not ADR_RE.search(md):
        errors.append("架构依据 missing ADR-NNNN reference")

    if not CHECKBOX_RE.search(md):
        errors.append("验收标准 has no markdown checkboxes (not quantifiable)")

    if proposal_review is not None:
        try:
            hits = proposal_review.detect_how_leakage(md)
        except Exception:
            hits = []
        for h in hits:
            errors.append(
                f"[HOW-LEAKAGE-WARN] signal={h['signal']} section={h['section']} "
                f"weighted_score={h['weighted_score']:.2f} action={h['action']} "
                f"(non-blocking; review manually)"
            )

    return errors


if __name__ == "__main__":
    import os
    import sys

    improvements_path = os.environ.get("IMPROVEMENTS_PATH", "")
    strict = os.environ.get("STRICT_DESIGN_GATE", "no") == "yes"
    skip = os.environ.get("SKIP_CONTENT_REVIEW", "no") == "yes"

    if skip:
        print("SKIP_CONTENT_REVIEW=yes: skipping review")
        sys.exit(0)

    if not improvements_path or not os.path.exists(improvements_path):
        print("ERROR: IMPROVEMENTS_PATH missing or file not found", file=sys.stderr)
        sys.exit(2)

    text = open(improvements_path, encoding="utf-8").read()
    errs = review_improvements(text)
    if errs:
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        if strict:
            print("STRICT_DESIGN_GATE=yes: blocking", file=sys.stderr)
            sys.exit(1)
        else:
            print("WARNING (set STRICT_DESIGN_GATE=yes to block)", file=sys.stderr)
            sys.exit(0)
    else:
        print("improvements content review: OK")
        sys.exit(0)
