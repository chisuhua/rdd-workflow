#!/usr/bin/env bash
# guide-arch/scripts/roadmap_incremental_update.sh — sh wrapper for the
# four-mode incremental roadmap updater (move-populate-roadmap-into-guide-arch,
# Task D). Called by guide-arch Phase 6 (Roadmap Sync) and by the deprecated
# populate-roadmap-from-arch thin wrapper.
#
# Oracle C1: env-var only passing. All RDDF_* values are already in the
# environment (exported by the caller); this script never interpolates bash
# $VAR into `python3 -c "..."` strings.
#
# Exit codes: 0 ok / 1 runtime error / 2 invalid env vars.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

# Required env var: project root (must be an existing directory).
if [ -z "${RDDF_PROJECT_ROOT:-}" ]; then
  echo "❌ RDDF_PROJECT_ROOT is required but not set" >&2
  exit 2
fi
if [ ! -d "$RDDF_PROJECT_ROOT" ]; then
  echo "❌ RDDF_PROJECT_ROOT is not a directory: $RDDF_PROJECT_ROOT" >&2
  exit 2
fi
export RDDF_PROJECT_ROOT

# Shared helpers (optional — absent in minimal/global installs).
# shellcheck source=/dev/null
source "${RDDF_LIB_DIR:-/nonexistent}/state.sh" 2>/dev/null || true

# Defaults for optional env vars (validated in detail by the .env.py layer).
export RDDF_ROADMAP_UPDATE="${RDDF_ROADMAP_UPDATE:-on}"
export RDDF_INCREMENTAL="${RDDF_INCREMENTAL:-on}"

exec python3 "$SCRIPT_DIR/roadmap_incremental_update.py"
