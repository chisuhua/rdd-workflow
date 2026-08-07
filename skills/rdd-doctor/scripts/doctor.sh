#!/usr/bin/env bash
# skills/rdd-doctor/scripts/doctor.sh
# Bash entry for rdd-doctor skill.
#
# Forwards all flags to a single Python process (doctor_main) that imports all
# 5 checkers. Sets RDDF_PROJECT_ROOT from git toplevel so checkers can resolve
# real _lib/ paths.

set -euo pipefail

if [ -z "${RDDF_PROJECT_ROOT:-}" ]; then
    PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
    export RDDF_PROJECT_ROOT="$PROJECT_ROOT"
fi

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
export RDDF_PROJECT_ROOT
exec python3 "$SCRIPT_DIR/doctor_main.py" "$@"