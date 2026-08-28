"""CHANGELOG ↔ USAGE.md sync check.

Public API:
    parse_unreleased(changelog_path) -> dict[str, list[str]]
    extract_banner(usage_path) -> str
    check_drift(changelog_path, usage_path) -> list[str] (drift warnings)
"""
import re
import sys
from pathlib import Path

_SECTION_TO_KEY = {
    "### Added": "Added",
    "### Changed": "Changed",
    "### Fixed": "Fixed",
    "### Removed": "Removed",
    "### Deprecated": "Deprecated",
}


def parse_unreleased(changelog_path: Path) -> dict[str, list[str]]:
    """Parse CHANGELOG.md [Unreleased] section, return dict of section_name -> bullet lines."""
    text = changelog_path.read_text(encoding="utf-8")
    match = re.search(r"## \[Unreleased\]\s*\n(.*?)(?=\n## \[|\Z)", text, re.DOTALL)
    if not match:
        return {}
    section_text = match.group(1)
    sections: dict[str, list[str]] = {}
    current_section = None
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped in _SECTION_TO_KEY:
            current_section = _SECTION_TO_KEY[stripped]
            sections.setdefault(current_section, [])
        elif current_section and stripped.startswith("- "):
            sections[current_section].append(stripped)
    return sections


def extract_banner(usage_path: Path) -> str:
    """Extract USAGE.md banner content from VERSION_BANNER_START/END markers."""
    text = usage_path.read_text(encoding="utf-8")
    m = re.search(
        r"<!-- VERSION_BANNER_START -->\s*\n(.*?)<!-- VERSION_BANNER_END -->",
        text, re.DOTALL
    )
    return m.group(1).strip() if m else ""


def check_drift(changelog_path: Path, usage_path: Path) -> list[str]:
    """Return list of drift warnings. Empty list = no drift."""
    sections = parse_unreleased(changelog_path)
    banner = extract_banner(usage_path)
    warnings: list[str] = []
    for section_name, bullets in sections.items():
        if not bullets:
            continue
        if section_name.lower() not in banner.lower():
            warnings.append(
                f"USAGE.md banner missing mention of CHANGELOG [{section_name}] section "
                f"({len(bullets)} entries)"
            )
    return warnings


def main():
    repo_root = Path(__file__).resolve().parents[1]
    changelog = repo_root / "CHANGELOG.md"
    usage = repo_root / "USAGE.md"
    drift = check_drift(changelog, usage)
    if drift:
        print("⚠️  CHANGELOG-USAGE drift detected:")
        for w in drift:
            print(f"  - {w}")
        sys.exit(1 if "--strict" in sys.argv else 0)
    print("✅ CHANGELOG ↔ USAGE in sync")
    sys.exit(0)


if __name__ == "__main__":
    main()