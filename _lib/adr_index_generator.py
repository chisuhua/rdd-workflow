"""ADR Index Generator — scans docs/adr/ADR-*.md, generates markdown table.

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


def extract_metadata(adr_path: Path) -> dict | None:
    """Extract status / date / decider from > 引用块 in ADR file.

    Returns:
        dict with keys: status, date, decider, is_template (bool)
        None if file has no metadata block (e.g. broken ADR).
    """
    text = adr_path.read_text(encoding="utf-8")
    matches = _META_PATTERN.findall(text)
    if not matches:
        return None
    metadata = {"is_template": "template" in adr_path.name}
    for key, value in matches:
        if key in ("状态", "Status"):
            metadata["status"] = value.strip()
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


def main():
    """CLI entry: regenerate docs/adr/README.md table."""
    import sys
    repo_root = Path(__file__).resolve().parents[1]
    adrs = scan_adrs(repo_root / "docs" / "adr")
    table = render_table(adrs)
    sys.stdout.write(table)
    sys.exit(0)


if __name__ == "__main__":
    main()