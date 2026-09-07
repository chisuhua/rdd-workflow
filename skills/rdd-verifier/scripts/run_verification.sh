#!/usr/bin/env bash
# run_verification.sh <change_name> — Stage agent verification context (v2.0)
#
# Per ADR-0045 (inline-ac-verifier-into-rdd-verifier): the executing AI agent
# IS the LLM. This script no longer shells out to the deprecated ac-verifier
# skill. Instead it stages a structured context file at
#   .rddf/state/rdd-verify-context-<change>.json
# describing what the agent should verify (proposal path, AC list, cache path,
# audit log path, expected verdict schema, reasoning-keyword contract).
#
# The agent then performs verification per
#   skills/rdd-verifier/SKILL.md § "LLM Verification Protocol"
# writes the verdict cache + audit log, and re-runs `rddf rdd-verify` to pick
# up the cache.
#
# Usage: bash run_verification.sh <change_name>
# Exit:  0 = context staged (agent verification pending)
#        2 = proposal.md missing (skip)
#        3 = staging error
set -euo pipefail

CHANGE_NAME="${1:-}"
[ -z "$CHANGE_NAME" ] && {
    echo "❌ usage: run_verification.sh <change_name>" >&2
    exit 3
}

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# Resolve the CLI backend across install layouts:
#   1. repo checkout: skills/rdd-verifier/scripts → repo-root/_lib/cli/
#   2. global install (symlink): realpath lands in repo; same as (1)
#   3. global install (copied): ~/.agents/skills/rdd-workflow/_lib/cli/
RESOLVED_CLI=""
for CAND in \
    "$SCRIPT_DIR/../../../_lib/cli/rdd_verify_cmd.py" \
    "$HOME/.agents/skills/rdd-workflow/_lib/cli/rdd_verify_cmd.py"; do
  if [ -f "$CAND" ]; then
    RESOLVED_CLI="$CAND"
    break
  fi
done

if [ -z "$RESOLVED_CLI" ]; then
    echo "❌ rdd_verify_cmd.py not found (looked in repo layout and ~/.agents/skills)" >&2
    exit 3
fi

set +e
RDDF_PROJECT_ROOT="$PROJECT_ROOT" \
    python3 "$RESOLVED_CLI" --stage "$CHANGE_NAME"
STAGE_EXIT=$?
set -e

exit "$STAGE_EXIT"
