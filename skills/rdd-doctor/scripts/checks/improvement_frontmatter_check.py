"""Check all .rddf/improvements/*.md files for valid YAML frontmatter.

Files MUST start with '---' on line 1 (per `_lib/planner_attach.py` L158-160).
Missing frontmatter means `rddf planner attach` will fail.

The front matter must additionally **parse as YAML**: a block whose scalar
contains ``": "`` (or ends with ``":"``) is rejected by the YAML parser, and
the consumer (`_lib/state_reader.py::_parse_improvement_meta`) then loses
the *whole* metadata set — priority / phase / category / status all degrade
to empty. The delimiter check alone cannot see that, so both are asserted
here.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity


def run(project_root: Path | None = None) -> List[Finding]:
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))

    impr_dir = project_root / ".rddf" / "improvements"
    if not impr_dir.is_dir():
        return []

    try:
        import yaml
    except ImportError:  # pragma: no cover - PyYAML is a declared dep
        yaml = None  # type: ignore[assignment]
    if yaml is None:
        # Without PyYAML the parse check cannot run — stay silent rather than
        # report a problem we cannot verify.
        return []

    findings: List[Finding] = []
    for f in sorted(impr_dir.glob("*.md")):
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            findings.append(Finding(
                severity=Severity.WARNING,
                category="improvement-frontmatter-consistency",
                file=str(f.relative_to(project_root)),
                line=None,
                snippet=f"unreadable file: {f.name}",
                fix_hint="check file permissions and encoding",
            ))
            continue

        first_line = text.split("\n", 1)[0]
        if first_line.strip() != "---":
            findings.append(Finding(
                severity=Severity.WARNING,
                category="improvement-frontmatter-consistency",
                file=str(f.relative_to(project_root)),
                line=1,
                snippet=f"missing frontmatter delimiters — first line is {first_line!r}, expected '---'",
                fix_hint=f"run: python3 -m _lib.cli.migrate_improvement_frontmatter --project-root {project_root}",
            ))
            continue

        # --- front matter must PARSE as YAML ------------------------------
        # A scalar containing ': ' (or ending with ':') breaks the parse and
        # silently costs the whole metadata set downstream.
        end = text.find("\n---", 4)
        if end == -1:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="improvement-frontmatter-consistency",
                file=str(f.relative_to(project_root)),
                line=1,
                snippet="front matter is not terminated by a closing '---'",
                fix_hint="add the closing '---' line after the front matter block",
            ))
            continue

        block = text[4:end]
        try:
            parsed = yaml.safe_load(block)
        except Exception as exc:  # noqa: BLE001 - malformed front matter
            findings.append(Finding(
                severity=Severity.WARNING,
                category="improvement-frontmatter-consistency",
                file=str(f.relative_to(project_root)),
                line=None,
                snippet=f"front matter is not valid YAML: {type(exc).__name__}: {str(exc).splitlines()[0]}",
                fix_hint=(
                    "quote the offending scalar (single quotes) or use a folded "
                    "block scalar ('>-') so the ':' no longer breaks the parse"
                ),
            ))
            continue

        if parsed is not None and not isinstance(parsed, dict):
            findings.append(Finding(
                severity=Severity.WARNING,
                category="improvement-frontmatter-consistency",
                file=str(f.relative_to(project_root)),
                line=1,
                snippet=f"front matter is not a mapping ({type(parsed).__name__})",
                fix_hint="front matter must be a 'key: value' mapping",
            ))

    return findings