#!/usr/bin/env bash
# rddf — rdd-workflow CLI entry point (thin shim → python3 -m skills._lib.cli)
#
# Subcommands (12): archive, cleanup, dashboard, deps, feature, guide,
#                   init, monitor, sessions, status, validate, version
set -euo pipefail
# Derive PACKAGE_DIR from BASH_SOURCE (the rdd-workflow root containing skills/)
_myself="$(realpath "${BASH_SOURCE[0]:-$0}")"
# rddf.sh is at skills/cli/rddf.sh, package root is 3 levels up (skills/cli/ → skills/ → root)
PACKAGE_DIR="$(dirname "$(dirname "$(dirname "$_myself")")")"
export PYTHONPATH="${PACKAGE_DIR}:${PYTHONPATH:-}"
exec python3 -m skills._lib.cli "$@"