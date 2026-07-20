#!/usr/bin/env bash
set -euo pipefail
# Derive PACKAGE_DIR from BASH_SOURCE (the spec-workflow root containing skills/)
_myself="$(realpath "${BASH_SOURCE[0]:-$0}")"
# rddf.sh is at skills/cli/rddf.sh, package root is 3 levels up (skills/cli/ → skills/ → root)
PACKAGE_DIR="$(dirname "$(dirname "$(dirname "$_myself")")")"
export PYTHONPATH="${PACKAGE_DIR}:${PYTHONPATH:-}"
exec python3 -m skills._lib.cli "$@"