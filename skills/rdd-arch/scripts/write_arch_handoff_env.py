#!/usr/bin/env python3
"""Entry-point script for _lib/write_arch_handoff.sh.

Reads env vars and delegates to write_arch_handoff.write_arch_handoff().
No bash string interpolation — all values flow through os.environ (Oracle C1 safe).
"""
import os
import sys
from pathlib import Path

project_root = os.environ.get("PROJECT_ROOT")
if not project_root:
    print("ERROR: PROJECT_ROOT env var not set", file=sys.stderr)
    sys.exit(1)

# Compute repo root from this script's location (grandparent of _lib/).
# This is needed when PROJECT_ROOT points to a temp/scratch directory.
_repo_root = str(Path(__file__).resolve().parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from skills.rdd_arch.scripts import write_arch_handoff as wah

result = wah.write_arch_handoff(
    project_root=os.environ["PROJECT_ROOT"],
    discovered_adr_dir=os.environ.get("DISCOVERED_ADR_DIR", "docs/adr"),
    discovered_roadmap_path=os.environ.get("DISCOVERED_ROADMAP_PATH", "roadmap.md"),
    discovered_architecture_dir=os.environ.get("DISCOVERED_ARCHITECTURE_DIR", "docs/architecture"),
    discovered_adr_pattern=os.environ.get("DISCOVERED_ADR_PATTERN", "ADR-*.md"),
    discovered_adr_dir_found=os.environ.get("DISCOVERED_ADR_DIR_FOUND", "false"),
    discovered_roadmap_found=os.environ.get("DISCOVERED_ROADMAP_FOUND", "false"),
    discovered_arch_found=os.environ.get("DISCOVERED_ARCH_FOUND", "false"),
    discovered_adr_dir_tried=os.environ.get("DISCOVERED_ADR_DIR_TRIED", "0"),
    discovered_roadmap_tried=os.environ.get("DISCOVERED_ROADMAP_TRIED", "0"),
    discovered_arch_tried=os.environ.get("DISCOVERED_ARCH_TRIED", "0"),
    roadmap_exists_bool=os.environ.get("ROADMAP_EXISTS_BOOL", "false"),
)

print(
    "✅ Handoff state written: .rddf/state/.arch-handoff.json "
    f"(adr_count={result['adr_count']}, "
    f"phase={result['current_phase']}, "
    f"adr_dir={result['adr_dir']})"
)