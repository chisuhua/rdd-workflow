"""ADR Index Generator — the ONLY generator for the docs/adr index table.

Rebuild the index in place:

    python3 _lib/adr_index_generator.py --write docs/adr/README.md

Print it to stdout instead (to inspect or diff):

    python3 _lib/adr_index_generator.py

This module is the single source of truth for the index block. Do not add a
second generator: a former `_lib/sync_adr_index.py` produced 3-column tables
(no date), forced every status to "待定" (it looked for a `## Status` heading
while this repo writes `> **状态**:`), and deleted the
`<!-- ADR_INDEX_START/END -->` markers. Using it corrupted the README with no
error — 3-column tables render perfectly. It is covered by
`tests/unit/test_adr_index_gate.py::test_no_duplicate_adr_index_generator`.

Only the text between the markers is rewritten; the surrounding prose in
README.md is left untouched.

Public API:
    scan_adrs(adr_dir) -> list[dict]
    extract_metadata(adr_path) -> dict | None
    render_table(adrs) -> str (markdown table)
"""
from pathlib import Path
import re

ADR_PATTERN = re.compile(r"ADR-(\d{4})-(.+)\.md$")

_META_PATTERN = re.compile(
    r"^>\s*\*\*(状态|Status|日期|Date|决策者|Decider|Decided by)\*\*:\s*(.+?)\s*$",
    re.MULTILINE,
)


def scan_adrs(adr_dir: Path) -> list[dict]:
    """Scan adr_dir for ADR-*.md files. Return list of dicts with number/title/slug/filename."""
    adrs = []
    for path in sorted(adr_dir.glob("ADR-*.md")):
        m = ADR_PATTERN.match(path.name)
        if not m:
            continue
        number, slug = m.groups()
        title = _extract_title(path)
        adrs.append({
            "number": number,
            "slug": slug,
            "title": title,
            "filename": path.name,
            "path": path,
        })
    return adrs


def _extract_title(path: Path) -> str:
    """Extract title from ADR file (first # heading)."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return ""


# ---------- status classification (per fix-adr-shape-debt-convergence T4) ----------
#
# ADR Status lines are free text (this repo has a dozen spellings), so nothing
# downstream can consume them. Classification happens **here**, on read - no
# ADR's Status line is rewritten to fit the enum.
#
# Precedence is load-bearing: "已采纳 + AMENDED" is both, and "已采纳。Superseded
# by ADR-0063" is superseded. The widest-scope verdict wins.
_STATUS_CLASS_RULES: list[tuple[str, re.Pattern]] = [
    ("superseded", re.compile(r"已替代|已被取代|supersede", re.IGNORECASE)),
    ("rejected", re.compile(r"已拒绝|拒绝采纳|rejected", re.IGNORECASE)),
    ("amended", re.compile(r"amend", re.IGNORECASE)),
    ("accepted", re.compile(r"已采纳|已接受|accepted|adopted|已实施", re.IGNORECASE)),
    ("proposed", re.compile(r"待采纳|提议|proposed|待批准", re.IGNORECASE)),
    # "draft" is the fallback: 待定 / 草案 / 模板 / unknown all mean "not decided yet"
]


def classify_status(raw: str) -> str:
    """Map a free-text Status value onto one of six classes.

    Classes: draft | proposed | accepted | amended | superseded | rejected.
    Unrecognised text falls back to "draft" - never to a decided state, because
    claiming a decision that the document does not state is the worse error.
    """
    for name, pattern in _STATUS_CLASS_RULES:
        if pattern.search(raw or ""):
            return name
    return "draft"

def extract_metadata(adr_path: Path) -> dict | None:
    """Extract status / date / decider from > 引用块 in ADR file.

    Returns:
        dict with keys: status, status_raw, status_class, date, decider,
        is_template (bool). `status` and `status_raw` are the same verbatim
        text (kept for compatibility); `status_class` is one of the six
        shapes-dashboard classes. None if the file has no metadata block.
    """
    text = adr_path.read_text(encoding="utf-8")
    matches = _META_PATTERN.findall(text)
    if not matches:
        return None
    metadata = {"is_template": "template" in adr_path.name}
    for key, value in matches:
        if key in ("状态", "Status"):
            metadata["status"] = value.strip()
            metadata["status_raw"] = value.strip()
            metadata["status_class"] = classify_status(value)
        elif key in ("日期", "Date"):
            metadata["date"] = value.strip()
        elif key in ("决策者", "Decider", "Decided by"):
            metadata["decider"] = value.strip()
    return metadata


def render_table(adrs: list[dict], include_metadata: bool = True) -> str:
    """Render markdown table from scanned ADRs.

    Skips templates (ADR-0000). Includes metadata columns when available.

    Args:
        adrs: list from scan_adrs()
        include_metadata: whether to join metadata (status/date/decider)

    Returns:
        Markdown table string (header + separator + rows).
    """
    lines = [
        "| ADR | 标题 | 状态 | 日期 |",
        "|-----|------|------|------|",
    ]
    for adr in adrs:
        if "template" in adr["filename"].lower():
            continue
        meta = extract_metadata(adr["path"]) if include_metadata else None
        status = meta.get("status", "—") if meta else "—"
        date = meta.get("date", "—") if meta else "—"
        link = f"[ADR-{adr['number']}]({adr['filename']})"
        lines.append(
            f"| {link} | {adr['title']} | {status} | {date} |"
        )
    return "\n".join(lines) + "\n"


_INDEX_BLOCK = re.compile(
    r"(<!-- ADR_INDEX_START -->\n)(.*?)(\n<!-- ADR_INDEX_END -->)", re.DOTALL
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Without --write, the table goes to stdout.

    Exit codes: 0 = ok, 2 = --write target has no ADR_INDEX_START/END markers.
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Generate the docs/adr index table.")
    parser.add_argument(
        "--write",
        metavar="README",
        help="rewrite the <!-- ADR_INDEX_START -->...<!-- ADR_INDEX_END --> block in this file",
    )
    args = parser.parse_args(argv)

    adr_dir = Path(__file__).resolve().parents[1] / "docs" / "adr"
    table = render_table(scan_adrs(adr_dir))

    if not args.write:
        sys.stdout.write(table)
        return 0

    readme = Path(args.write)
    text = readme.read_text(encoding="utf-8")
    if not _INDEX_BLOCK.search(text):
        sys.stderr.write(
            f"ERR {readme}: ADR_INDEX_START / ADR_INDEX_END markers not found\n"
        )
        return 2
    readme.write_text(
        _INDEX_BLOCK.sub(lambda m: m.group(1) + table.rstrip("\n") + m.group(3), text),
        encoding="utf-8",
    )
    sys.stderr.write(f"rewrote index block in {readme}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())