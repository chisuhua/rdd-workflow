"""_lib/write_arch_handoff.py — write .arch-handoff.json (ADR-0016 v2 schema).

Extracted from skills/guide-arch.md lines 618-707 (~88-line inline bash block).
Preserves exact behavior: ADR glob, ID extraction, roadmap phase reading,
discovery metadata, and JSON file output to .rddf/state/.arch-handoff.json.

Known limitations:
- ADR files with non-4-digit IDs (e.g., ADR-42-foo.md) are excluded to align
  with arch_handoff_schema.json v1 which requires ^[0-9]{4}$. If your project
  uses non-4-digit IDs, override by extending the schema.
"""

import glob
import json
import os
import re
from datetime import datetime, timezone
from typing import List, Optional


def _to_bool(s: str) -> bool:
    """Convert discovery 'true'/'false' string to bool."""
    return str(s).lower() == "true"


def _to_int(s: str, default: int = 0) -> int:
    """Convert string to int with fallback."""
    try:
        return int(s)
    except (ValueError, TypeError):
        return default


def _extract_id_prefix(pattern: str) -> str:
    """Extract prefix from ADR pattern (e.g., 'ADR-*.md' → 'ADR')."""
    m = re.match(r"^([A-Za-z]+)-", pattern)
    return m.group(1) if m else "ADR"


def _glob_adr_files(adr_dir_abs: str, pattern: str) -> List[str]:
    """Glob ADR files, excluding ADR-0000-template.md."""
    if not os.path.isdir(adr_dir_abs):
        return []
    files = []
    for path in glob.glob(os.path.join(adr_dir_abs, pattern)):
        if not os.path.isfile(path):
            continue  # Skip directories matching the pattern
        basename = os.path.basename(path)
        # Exclude ADR-0000-template.md (and any -0000-template variant)
        if basename.endswith("-0000-template.md") or basename == "0000-template.md":
            continue
        files.append(path)
    return sorted(files)


def _extract_ids(files: List[str], id_prefix: str) -> List[str]:
    """Extract zero-padded numeric IDs from filenames.

    For id_prefix='ADR' and filename 'ADR-0001-foo.md' → '0001'.
    """
    ids = []
    for path in files:
        basename = os.path.basename(path)
        m = re.match(rf"^{re.escape(id_prefix)}-(\d{{4}})-", basename)
        if m:
            ids.append(m.group(1))
    # Sort numerically (zero-padded strings sort correctly)
    return sorted(set(ids), key=lambda x: int(x))


def _read_roadmap_phase(roadmap_abs: str) -> str:
    """Read current roadmap phase from **当前阶段**: marker."""
    if not os.path.isfile(roadmap_abs):
        return "default"
    try:
        with open(roadmap_abs) as f:
            for line in f:
                if "**当前阶段**" in line:
                    parts = line.split("**当前阶段**", 1)
                    if len(parts) > 1:
                        phase = parts[1].lstrip(":").strip()
                        if phase:
                            return phase
                    break
    except Exception:
        return "default"
    return "default"


def _read_project_yaml_adr_pattern(project_root: str) -> Optional[str]:
    """Read .rddf/project.yaml adr.pattern (Python regex) if present.

    Per complete-project-yaml-config-gaps M4 Task 4.6: arch-handoff carries
    the Python regex from project.yaml so populate_lib can pass it through.
    Returns None if project.yaml absent or corrupt (graceful fallback).
    """
    import yaml
    project_yaml = os.path.join(project_root, ".rddf", "project.yaml")
    if not os.path.isfile(project_yaml):
        return None
    try:
        with open(project_yaml) as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("adr", {}).get("pattern")
    except (yaml.YAMLError, OSError):
        return None


def write_arch_handoff(
    project_root: str,
    discovered_adr_dir: str = "docs/adr",
    discovered_roadmap_path: str = "roadmap.md",
    discovered_architecture_dir: str = "docs/architecture",
    discovered_adr_pattern: str = "ADR-*.md",
    discovered_adr_dir_found: str = "false",
    discovered_roadmap_found: str = "false",
    discovered_arch_found: str = "false",
    discovered_adr_dir_tried: str = "0",
    discovered_roadmap_tried: str = "0",
    discovered_arch_tried: str = "0",
    roadmap_exists_bool: str = "false",
) -> dict:
    """Build and write .arch-handoff.json. Returns the written dict.

    Mirrors the original bash block at guide-arch.md L618-L707:
    - Re-runs artifact discovery (caller responsibility)
    - Globs ADR files using discovered pattern, excludes template
    - Extracts numeric IDs from filenames with configurable prefix
    - Reads current roadmap phase from markdown
    - Builds v1 schema JSON with discovery metadata
    - Writes to .rddf/state/.arch-handoff.json

    Args:
        project_root: Absolute path to project root.
        discovered_adr_dir: Relative path to ADR directory.
        discovered_roadmap_path: Relative path to roadmap file.
        discovered_architecture_dir: Relative path to architecture directory.
        discovered_adr_pattern: Glob pattern for ADR files (e.g., 'ADR-*.md').
        discovered_adr_dir_found: Whether discovery found the ADR dir ('true'/'false').
        discovered_roadmap_found: Whether discovery found the roadmap.
        discovered_arch_found: Whether discovery found the arch dir.
        discovered_adr_dir_tried: Number of candidates tried (string integer).
        discovered_roadmap_tried: Number of candidates tried (string integer).
        discovered_arch_tried: Number of candidates tried (string integer).
        roadmap_exists_bool: Whether roadmap file exists at path ('true'/'false').

    Returns:
        Dict matching arch_handoff_schema.json v1 structure.
    """
    adr_dir_abs = os.path.join(project_root, discovered_adr_dir)

    # Glob ADR files
    id_prefix = _extract_id_prefix(discovered_adr_pattern)
    adr_files = _glob_adr_files(adr_dir_abs, discovered_adr_pattern)
    adr_count = len(adr_files)
    completed_adr_ids = _extract_ids(adr_files, id_prefix)

    # Read roadmap phase
    roadmap_abs = os.path.join(project_root, discovered_roadmap_path)
    current_phase = _read_roadmap_phase(roadmap_abs)

    handoff = {
        "arch_complete_at": datetime.now(timezone.utc).isoformat(),
        "adr_count": adr_count,
        "completed_adr_ids": completed_adr_ids,
        "roadmap_exists": _to_bool(roadmap_exists_bool),
        "current_phase": current_phase,
        "plan_started_at": None,
        "adr_dir": discovered_adr_dir,
        "roadmap_path": discovered_roadmap_path,
        "architecture_dir": discovered_architecture_dir,
        "adr_pattern": discovered_adr_pattern,
        "discovered": {
            "adr_dir": {
                "found": _to_bool(discovered_adr_dir_found),
                "created": False,
                "candidates_tried": _to_int(discovered_adr_dir_tried),
            },
            "roadmap_path": {
                "found": _to_bool(discovered_roadmap_found),
                "created": False,
                "candidates_tried": _to_int(discovered_roadmap_tried),
            },
            "architecture_dir": {
                "found": _to_bool(discovered_arch_found),
                "created": False,
                "candidates_tried": _to_int(discovered_arch_tried),
            },
        },
        "version": 2,
    }
    # v2: add adr_regex from .rddf/project.yaml (Python regex passthrough
    # for populate_lib). Distinct from adr_pattern (glob). Optional.
    adr_regex = _read_project_yaml_adr_pattern(project_root)
    if adr_regex:
        handoff["adr_regex"] = adr_regex

    # Write to disk (Stage 3 Change 0: FileLock + atomic_write_json per Oracle C-1)
    state_dir = os.path.join(project_root, ".rddf", "state")
    os.makedirs(state_dir, exist_ok=True)
    handoff_path = os.path.join(state_dir, ".arch-handoff.json")
    lock_path = os.path.join(state_dir, ".arch-handoff.json.lock")

    from _lib.core.lock import FileLock
    from _lib.core.atomic_write import atomic_write_json

    with FileLock(lock_path, timeout=10.0):
        atomic_write_json(handoff_path, handoff, indent=2, ensure_ascii=False)

    return handoff