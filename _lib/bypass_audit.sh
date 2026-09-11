#!/usr/bin/env bash
# bypass_audit.sh — unified audit log writer for SKIP_* bypass entries
#
# Per improvement #bypass-audit-mechanism (P2 governance):
# - Single append-only log: .rddf/state/.bypass-audit.jsonl
# - Aggregated by rdd-doctor --category bypass-audit
# - Threshold warnings (CRITICAL if count > 2x threshold)
#
# Public API:
#   audit_bypass_log <env_var> <reason> [change] [scope]
#
# Usage in any SKIP_* gate:
#   if [ "${SKIP_RDD_VERIFIER:-no}" = "yes" ]; then
#     source "$_LIB_DIR/bypass_audit.sh"
#     audit_bypass_log "SKIP_RDD_VERIFIER" "${RDDF_VERIFIER_BYPASS_REASON:-no reason given}" "$CHANGE_NAME" "verifier"
#   fi
#
# Schema (each line is a JSON object):
#   {
#     "ts": "2026-09-11T...",
#     "env_var": "SKIP_RDD_VERIFIER",
#     "reason": "hotfix for prod incident #123",
#     "change": "my-change-name",     // optional
#     "actor": "sisyphus",             // git config user.name
#     "codebase_commit": "abc1234",    // git rev-parse HEAD
#     "scope": "verifier|design-gate|archive-on-main|cross-repo|..."
#   }

set -u

# Resolve paths
_BYPASS_AUDIT_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
_BYPASS_AUDIT_REPO_ROOT="$(cd "$_BYPASS_AUDIT_SCRIPT_DIR/.." && pwd)"

# Helper: compute audit file path (lazy — re-evaluated each call so that
# RDDF_PROJECT_ROOT env var overrides at runtime work correctly).
_bypass_audit_path() {
    local root="${RDDF_PROJECT_ROOT:-$PWD}"
    echo "${root}/.rddf/state/.bypass-audit.jsonl"
}

# Helper: append one audit event.
# Args:
#   $1 - env_var (e.g. "SKIP_RDD_VERIFIER")
#   $2 - reason (required, free-form text)
#   $3 - change (optional, defaults to "")
#   $4 - scope (optional, defaults to "unknown")
audit_bypass_log() {
    local env_var="$1"
    local reason="$2"
    local change="${3:-}"
    local scope="${4:-unknown}"

    # Validate required args
    if [ -z "$env_var" ] || [ -z "$reason" ]; then
        echo "❌ audit_bypass_log: env_var and reason are required" >&2
        return 2
    fi

    local audit_file
    audit_file="$(_bypass_audit_path)"

    # Ensure parent dir exists
    mkdir -p "$(dirname "$audit_file")" 2>/dev/null || true

    # Capture metadata
    local ts
    ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    local actor
    actor="$(git config user.name 2>/dev/null || echo 'unknown')"
    local commit
    commit="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')"

    # Write JSONL entry. Use python3 for safe JSON encoding (no jq dep).
    BYPASS_AUDIT_ENV_VAR="$env_var" \
    BYPASS_AUDIT_REASON="$reason" \
    BYPASS_AUDIT_CHANGE="$change" \
    BYPASS_AUDIT_SCOPE="$scope" \
    BYPASS_AUDIT_TS="$ts" \
    BYPASS_AUDIT_ACTOR="$actor" \
    BYPASS_AUDIT_COMMIT="$commit" \
    BYPASS_AUDIT_FILE="$audit_file" \
    python3 <<'PYEOF'
import json
import os
from pathlib import Path

record = {
    "ts": os.environ["BYPASS_AUDIT_TS"],
    "env_var": os.environ["BYPASS_AUDIT_ENV_VAR"],
    "reason": os.environ["BYPASS_AUDIT_REASON"],
    "change": os.environ["BYPASS_AUDIT_CHANGE"],
    "actor": os.environ["BYPASS_AUDIT_ACTOR"],
    "codebase_commit": os.environ["BYPASS_AUDIT_COMMIT"],
    "scope": os.environ["BYPASS_AUDIT_SCOPE"],
}

audit_file = Path(os.environ["BYPASS_AUDIT_FILE"])
audit_file.parent.mkdir(parents=True, exist_ok=True)
with audit_file.open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False) + "\n")
PYEOF
}

# Helper: read all audit events. Returns JSON array.
audit_bypass_read() {
    local file="${1:-$(_bypass_audit_path)}"
    if [ ! -f "$file" ]; then
        echo "[]"
        return 0
    fi
    python3 -c "
import json
import sys
from pathlib import Path
events = []
for line in Path('$file').read_text().splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        events.append(json.loads(line))
    except json.JSONDecodeError as e:
        print(f'WARN: malformed audit line: {line[:80]!r}: {e}', file=sys.stderr)
print(json.dumps(events))
"
}

# Helper: monthly count by env_var. Returns JSON dict.
audit_bypass_monthly_count() {
    local file="${1:-$(_bypass_audit_path)}"
    if [ ! -f "$file" ]; then
        echo "{}"
        return 0
    fi
    BYPASS_AUDIT_FILE="$file" python3 -c "
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone

events = []
for line in Path('$file').read_text().splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        events.append(json.loads(line))
    except json.JSONDecodeError:
        continue

month = datetime.now(timezone.utc).strftime('%Y-%m')
counts = defaultdict(int)
for e in events:
    if e.get('ts', '').startswith(month):
        counts[e.get('env_var', 'unknown')] += 1
print(json.dumps(dict(counts)))
"
}