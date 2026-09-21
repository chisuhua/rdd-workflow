"""Phase 1: Project Environment Detection (read-only).

Pure functions for file-based detection. <200ms total target.
All return dict / list / bool for JSON-friendliness.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def detect_git_repo(project_root: Path) -> bool:
    """Return True if project_root contains a .git/ directory."""
    return (Path(project_root) / ".git").exists()


def detect_rddf_dir(project_root: Path) -> bool:
    """Return True if project_root contains a .rddf/ directory."""
    return (Path(project_root) / ".rddf").exists()


def detect_language(project_root: Path) -> list[str]:
    """Detect project language(s) by marker files. Returns list of languages found."""
    project_root = Path(project_root)
    found = []
    # Python
    if (project_root / "pyproject.toml").is_file() or (project_root / "setup.py").is_file():
        found.append("python")
    # Node
    if (project_root / "package.json").is_file():
        found.append("node")
    # Go
    if (project_root / "go.mod").is_file():
        found.append("go")
    # Rust
    if (project_root / "Cargo.toml").is_file():
        found.append("rust")
    return found or ["unknown"]


def detect_rddf_install() -> dict[str, Any]:
    """Detect rddf CLI install + version. Returns {installed: bool, version: str | None}.

    Uses shutil.which (fast) + rddf --version subprocess (slow but bounded by 2s timeout).
    """
    rddf_path = shutil.which("rddf")
    if rddf_path is None:
        return {"installed": False, "version": None}
    try:
        r = subprocess.run(
            ["rddf", "--version"], capture_output=True, text=True, timeout=2
        )
        version = (r.stdout or r.stderr).strip().split("\n")[0] if r.returncode == 0 else None
        return {"installed": True, "version": version}
    except (subprocess.TimeoutExpired, OSError):
        return {"installed": True, "version": None}


def detect_ai_config_files(project_root: Path) -> list[str]:
    """Return list of AI config files present in project_root (relative paths).

    Detection priority (per ADR-0052 + AC-4):
    - AGENTS.md
    - .cursorrules
    - CLAUDE.md
    - .clinerules
    - .continue/rules/*.md
    - .github/copilot-instructions.md
    """
    project_root = Path(project_root)
    candidates = [
        "AGENTS.md",
        ".cursorrules",
        "CLAUDE.md",
        ".clinerules",
        ".github/copilot-instructions.md",
    ]
    found = []
    for c in candidates:
        if (project_root / c).is_file():
            found.append(c)
    # Glob for .continue/rules/*.md
    continue_dir = project_root / ".continue" / "rules"
    if continue_dir.is_dir():
        for md in sorted(continue_dir.glob("*.md")):
            if md.is_file():
                found.append(str(md.relative_to(project_root)))
    return found


def detect_all(project_root: Path) -> dict[str, Any]:
    """Run all detectors and return combined dict. Convenience entry for CLI."""
    return {
        "is_git_repo": detect_git_repo(project_root),
        "has_rddf_dir": detect_rddf_dir(project_root),
        "language_hints": detect_language(project_root),
        "rddf_installed": detect_rddf_install(),
        "ai_config_files_detected": detect_ai_config_files(project_root),
    }


if __name__ == "__main__":
    import json
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    print(json.dumps(detect_all(target), ensure_ascii=False, indent=2))


__all__ = [
    "detect_git_repo",
    "detect_rddf_dir",
    "detect_language",
    "detect_rddf_install",
    "detect_ai_config_files",
    "detect_all",
]
