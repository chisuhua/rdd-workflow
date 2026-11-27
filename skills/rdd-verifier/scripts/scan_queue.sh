#!/usr/bin/env bash
# scan_queue.sh — List implemented, task-complete changes (disk-derived).
#
# Thin wrapper: the rules live in `_lib/verifier/discovery.py::discover_eligible`
# (single source, shared with `rddf rdd-verify` batch mode). This file used to
# carry its own inline copy reading `iteration.json` — two implementations of
# one rule is how they drift.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The dir that CONTAINS `_lib/` — not the project root.
PKG_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
MAX_CHANGES="${RDDF_VERIFIER_MAX_CHANGES:-10}"

PKG_ROOT="$PKG_ROOT" PROJECT_ROOT="$PROJECT_ROOT" MAX_CHANGES="$MAX_CHANGES" python3 - <<'PY'
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ["PKG_ROOT"])
from _lib.verifier.discovery import discover_eligible  # noqa: E402

names = discover_eligible(Path(os.environ["PROJECT_ROOT"]))
limit = max(0, int(os.environ.get("MAX_CHANGES") or 10))
print(" ".join(names[:limit]))
PY
