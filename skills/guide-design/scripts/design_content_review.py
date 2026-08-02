"""skills/guide-design/scripts/design_content_review.py — improvements-layer review (D4).

D4: improvements-layer checks (5 sections, ADR refs, acceptance checkboxes,
head fields). Returns list of error strings (empty == pass). The bash
wrapper (design_content_review.sh) handles SKIP_CONTENT_REVIEW bypass and
STRICT_DESIGN_GATE blocking.

Openspec proposal-layer checks (length / ADR / scope) live in
skills/propose/scripts/propose_quality_check.py::run_design_checks.
"""
import re


REQUIRED_SECTIONS = ["架构依据", "范围", "关键场景", "技术约束", "验收标准"]
REQUIRED_HEAD = ["阶段", "分类", "类型"]
ADR_RE = re.compile(r"ADR-\d{4}")
CHECKBOX_RE = re.compile(r"^- \[[ x]\] ", re.MULTILINE)


def review_improvements(md: str) -> list[str]:
    """Run all improvements-layer checks. Returns list of error messages.

    Empty list means pass. Each error is a human-readable string.
    Severity (warning vs blocking) is decided upstream by STRICT_DESIGN_GATE.
    """
    errors: list[str] = []

    for field in REQUIRED_HEAD:
        if not re.search(rf"\*\*{field}\*\*:\s*\S", md):
            errors.append(f"missing head field: {field}")

    for section in REQUIRED_SECTIONS:
        if not re.search(rf"^## {section}\s*$", md, re.MULTILINE):
            errors.append(f"missing section: {section}")

    # Architecture依据 must reference at least one ADR
    if not ADR_RE.search(md):
        errors.append("架构依据 missing ADR-NNNN reference")

    # Acceptance criteria must be quantifiable (markdown checkboxes)
    if not CHECKBOX_RE.search(md):
        errors.append("验收标准 has no markdown checkboxes (not quantifiable)")

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
