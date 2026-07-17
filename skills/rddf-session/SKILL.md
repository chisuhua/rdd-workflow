---
name: rddf-session
description: User-perspective workflow session management. Persists rddf-session lifecycle to .rddf/state/sessions.json and provides cross-opencode-session recovery via 5 subcommands (list/show/resume/abandon/archive-history). See ADR-0017.
license: MIT
compatibility: Requires Python 3.11+ and the rddf_session.py module (installed via this skill pack).
metadata:
  version: "2.0"  # rddf-session subfeature is at 1.1 (added current subcommand, spec 2026-07-14)
  author: sisyphus
  evolved-from: "rddf-session.md v1.0"
  depends-on: [rddf_session]
---

# OpenSpec Workflow — rddf-session Management

> **User-perspective session abstraction.** Lets you list, inspect, resume,
> abandon, or archive rddf-sessions that span OpenCode chat sessions.
> Pure CRUD against `.rddf/state/sessions.json` — never mutates other state.

## Subcommands

```
skill_use("rddf-session")                       # default: list
skill_use("rddf-session list")                  # same as above
skill_use("rddf-session show <id>")             # show full JSON for a session
skill_use("rddf-session current")               # show my current binding + recommend next (spec 2026-07-14)
skill_use("rddf-session resume <id>")           # transfer ownership to current opencode session; refresh heartbeat
skill_use("rddf-session abandon <id>")          # mark session as abandoned by current owner
skill_use("rddf-session archive-history")       # move old terminal sessions to .archive.json (default keep=20)
skill_use("rddf-session archive-history --keep=50")  # custom keep count
```

## Implementation (Bash)

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
SESSIONS_FILE="$PROJECT_ROOT/.rddf/state/sessions.json"
mkdir -p "$(dirname "$SESSIONS_FILE")"

SUBCOMMAND="${1:-list}"
shift || true

case "$SUBCOMMAND" in
    list)
        python3 - "$SESSIONS_FILE" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[2] if len(sys.argv) > 2 else ".")
from skills._lib.rddf_session import RddfSessionCoordinator
sessions_file = sys.argv[1]
coord = RddfSessionCoordinator(sessions_file=sessions_file)
# Check timeouts first
coord.check_heartbeat_timeouts()
sessions = coord.list_sessions()
if not sessions:
    print("No rddf-sessions found.")
    sys.exit(0)
hdr = f"{'session_id':<17} {'kind':<14} {'owner':<24} {'state':<11} {'last_heartbeat':<26} {'changes':<8}"
print(hdr)
print("-" * len(hdr))
for s in sessions:
    owner = s.owner_opencode_session_id or "<none>"
    print(f"{s.session_id:<17} {s.kind:<14} {owner:<24} {s.state:<11} {s.last_heartbeat:<26} {len(s.attached_changes):<8}")
PYEOF
        PROJECT_ROOT_ARG="$PROJECT_ROOT" python3 - "$SESSIONS_FILE" "$PROJECT_ROOT"
        ;;

    show)
        SESSION_ID="${1:?Usage: rddf-session show <session_id>}"
        python3 - "$SESSIONS_FILE" "$SESSION_ID" "$PROJECT_ROOT" <<'PYEOF'
import sys, json
sys.path.insert(0, sys.argv[3] if len(sys.argv) > 3 else ".")
from skills._lib.rddf_session import RddfSessionCoordinator
sessions_file = sys.argv[1]
session_id = sys.argv[2]
coord = RddfSessionCoordinator(sessions_file=sessions_file)
session = coord.find_session(session_id)
if not session:
    print(f"Session not found: {session_id}")
    sys.exit(1)
print(json.dumps(session.to_dict(), indent=2))
PYEOF
        ;;

    current)
        OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"
        python3 - "$SESSIONS_FILE" "$OPENCODE_SESSION_ID" "$PROJECT_ROOT" <<'PYEOF'
import sys, json
sys.path.insert(0, sys.argv[3] if len(sys.argv) > 3 else ".")
from skills._lib.rddf_session import RddfSessionCoordinator
sessions_file, owner = sys.argv[1], sys.argv[2]
coord = RddfSessionCoordinator(sessions_file=sessions_file)
coord.check_heartbeat_timeouts()
current = coord.find_current_binding(owner)
if current:
    print(f"📍 Current: {current.session_id} (kind={current.kind}, started={current.started_at})")
else:
    print("📍 No current binding")
    nxt = coord.find_next_recommendation(owner)
    if nxt:
        print(f"💡 Recommended: {nxt.session_id} (kind={nxt.kind}, last_heartbeat={nxt.last_heartbeat})")
        print(f'   → skill_use("rddf-session resume {nxt.session_id}")')
    else:
        print("   No orphaned rddf-sessions found. Run guide-arch or guide-plan to start.")
PYEOF
        ;;

    resume)
        SESSION_ID="${1:?Usage: rddf-session resume <session_id>}"
        OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"
        python3 - "$SESSIONS_FILE" "$SESSION_ID" "$OPENCODE_SESSION_ID" "$PROJECT_ROOT" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[4] if len(sys.argv) > 4 else ".")
from skills._lib.rddf_session import RddfSessionCoordinator
sessions_file = sys.argv[1]
session_id = sys.argv[2]
new_owner = sys.argv[3]
coord = RddfSessionCoordinator(sessions_file=sessions_file)
session = coord.find_session(session_id)
if not session:
    print(f"Session not found: {session_id}")
    sys.exit(1)
if session.state == "orphaned":
    coord.update_session_status(session_id, "active")
    print(f"Session {session_id} transitioned orphaned -> active")
elif session.state == "active":
    print(f"Session {session_id} already active")
else:
    print(f"Cannot resume session in state {session.state}")
    sys.exit(1)
coord.transfer_ownership(session_id, new_owner)
print(f"Ownership transferred to {new_owner}")
PYEOF
        ;;

    abandon)
        SESSION_ID="${1:?Usage: rddf-session abandon <session_id>}"
        python3 - "$SESSIONS_FILE" "$SESSION_ID" "$PROJECT_ROOT" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[3] if len(sys.argv) > 3 else ".")
from skills._lib.rddf_session import RddfSessionCoordinator
sessions_file = sys.argv[1]
session_id = sys.argv[2]
coord = RddfSessionCoordinator(sessions_file=sessions_file)
coord.abandon(session_id)
print(f"Session {session_id} abandoned")
PYEOF
        ;;

    archive-history)
        KEEP=20
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --keep=*) KEEP="${1#*=}" ;;
                *) shift ;;
            esac
            shift || break
        done
        python3 - "$SESSIONS_FILE" "$KEEP" "$PROJECT_ROOT" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[3] if len(sys.argv) > 3 else ".")
from skills._lib.rddf_session import RddfSessionCoordinator
sessions_file = sys.argv[1]
keep = int(sys.argv[2])
coord = RddfSessionCoordinator(sessions_file=sessions_file)
n = coord.archive_history(keep=keep)
print(f"Archived {n} sessions (kept {keep} recent + active/orphaned)")
PYEOF
        ;;

    *)
        echo "Unknown subcommand: $SUBCOMMAND" >&2
        echo "Usage: rddf-session {list|show|current|resume|abandon|archive-history} ..." >&2
        exit 1
        ;;
esac
```

## Architecture

- **Storage**: `.rddf/state/sessions.json` (gitignored, project-scoped)
- **Schema**: `skills/_lib/schemas/sessions_schema.json` v1 (ADR-0017)
- **Concurrency**: file lock via `fcntl.flock`; atomic write via tmp+rename
- **Heartbeat**: refreshed on every `guide-arch`/`guide-plan`/`guide-ship` phase call;
  30-minute timeout → orphaned

## Cross-Reference

- `guide-arch` / `guide-plan` / `guide-ship` automatically create `kind=stage_*` rddf-sessions on entry and close them on phase completion.
- See `docs/v2-multi-session-guide.md` for full user guide and conflict-resolution flow.
- See ADR-0017 for design rationale.