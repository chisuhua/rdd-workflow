#!/usr/bin/env bash
# approve_proposal.sh - Mark a pending RFC entry as approved locally.
#
# Usage: bash approve_proposal.sh <change_name> <gate_type> <approver> <note>
#
# Updates .rddf/state/.cross-repo-pending.json in $RDDF_PROJECT_ROOT:
# - Sets entry status to "approved"
# - Appends log entry to .rddf/state/.cross-repo-audit.jsonl
#
# Side effects: writes timestamped audit log to .rddf/state/.cross-repo-audit.jsonl

set -euo pipefail

if [ $# -lt 4 ]; then
  echo "Usage: $0 <change_name> <gate_type> <approver> <note>" >&2
  exit 2
fi

CHANGE_NAME="$1"
GATE_TYPE="$2"
APPROVER="$3"
NOTE="$4"

PROJECT_ROOT="${RDDF_PROJECT_ROOT:-$(pwd)}"
STATE_DIR="$PROJECT_ROOT/.rddf/state"
PENDING_FILE="$STATE_DIR/.cross-repo-pending.json"
AUDIT_FILE="$STATE_DIR/.cross-repo-audit.jsonl"

mkdir -p "$STATE_DIR"

# Find pending entry matching this gate_type
if [ ! -f "$PENDING_FILE" ]; then
  echo "ERROR: $PENDING_FILE does not exist" >&2
  exit 1
fi

# Update first matching entry's status to approved
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
python3 - "$PENDING_FILE" "$TIMESTAMP" <<'PYEOF'
import json, sys
path, ts = sys.argv[1], sys.argv[2]
with open(path) as f:
    state = json.load(f)
for e in state.get("entries", []):
    if e.get("status") == "pending":
        e["status"] = "approved"
        e["approved_at"] = ts
        break
with open(path, "w") as f:
    json.dump(state, f, indent=2)
PYEOF

# Append audit log entry
python3 - "$AUDIT_FILE" "$CHANGE_NAME" "$GATE_TYPE" "$APPROVER" "$NOTE" "$TIMESTAMP" <<'PYEOF'
import json, sys
audit_file, change, gate, approver, note, ts = sys.argv[1:7]
entry = {
    "version": 1,
    "decision_id": f"manual-{ts}",
    "actor": approver,
    "decision_type": "rfc_approve",
    "result": "approved",
    "timestamp": ts,
    "change_name": change,
    "gate_type": gate,
    "note": note,
}
with open(audit_file, "a") as f:
    f.write(json.dumps(entry) + "\n")
PYEOF

echo "approved: $CHANGE_NAME approved by $APPROVER ($GATE_TYPE)"
