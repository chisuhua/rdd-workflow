# skills/_lib/rddf_session_hooks.sh
# Bash wrapper for rddf-session entry/close hooks in guide-arch/plan/ship.
# Extracted from inline PYEOF heredocs (P3-4) per ADR-0017.
#
# Functions exported:
#   - rddf_session_hook_entry <kind> <intent> <subject> <expected_outcome> [context_pointer]
#       Creates or finds active rddf-session of <kind> for current
#       OPENCODE_SESSION_ID. Parent linkage: stage_plan -> stage_arch,
#       stage_ship -> stage_plan. ConflictError (different owner, same
#       kind active) -> exit 2 with 4-option soft prompt hint.
#
#   - rddf_session_hook_close <kind> <end_reason> <intent>
#       Closes the rddf-session of <kind> for current OPENCODE_SESSION_ID.
#       Uses find-or-create semantics: if an active session exists for
#       the same owner, marks IT completed; otherwise creates a new
#       session and immediately marks it completed (audit trail).
#       Gracefully skips when sessions.json does not exist.
#
# Behavior preserved from inline versions:
#   - OPENCODE_SESSION_ID fallback: $(hostname -s)_$$ (matches inline)
#   - PROJECT_ROOT fallback: git rev-parse --show-toplevel || pwd
#   - Entry: prints "rddf-session: <sid> (<kind>, parent=<id>)" on success
#   - Entry: prints "CONFLICT: ..." + 4-option prompt hint + exit 2 on conflict
#   - Close: prints "rddf-session: <sid> -> completed (<reason>)" on success
#   - Close: prints "rddf-session close skipped: <err>" on unexpected error
#   - Close: prints "rddf-session: sessions.json not found, skipping close"
#     when sessions.json missing (consistent across all 3 callers; was
#     inconsistent in original — only ship was silent)
#
# Concurrency: fcntl.flock inside RddfSessionCoordinator._with_file_lock
# serializes parallel hook invocations. Multiple parallel entries
# complete safely without corrupting sessions.json.
#
# No API surface change: RddfSessionCoordinator unchanged. Helper
# thin-wraps create_session + check_heartbeat_timeouts +
# update_session_status + list_sessions.

# rddf_session_hook_entry <kind> <intent> <subject> <expected_outcome> [context_pointer]
rddf_session_hook_entry() {
  local kind="$1"
  local intent="$2"
  local subject="$3"
  local expected_outcome="$4"
  local context_pointer="${5:-}"

  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"

  KIND="$kind" \
  INTENT="$intent" \
  SUBJECT="$subject" \
  EXPECTED_OUTCOME="$expected_outcome" \
  CONTEXT_POINTER="$context_pointer" \
  PROJECT_ROOT="$PROJECT_ROOT" \
  OPENCODE_SESSION_ID="$OPENCODE_SESSION_ID" \
  python3 <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator, ConflictError

project_root = os.environ["PROJECT_ROOT"]
kind = os.environ["KIND"]
opencode_sid = os.environ["OPENCODE_SESSION_ID"]
intent = os.environ["INTENT"]
subject = os.environ["SUBJECT"]
expected_outcome = os.environ["EXPECTED_OUTCOME"]
context_pointer = os.environ.get("CONTEXT_POINTER") or None

sessions_file = os.path.join(project_root, ".rddf", "state", "sessions.json")
os.makedirs(os.path.dirname(sessions_file), exist_ok=True)
coord = RddfSessionCoordinator(sessions_file=sessions_file)
coord.check_heartbeat_timeouts()

parent_id = None
parent_kind_map = {"stage_plan": "stage_arch", "stage_ship": "stage_plan"}
parent_kind = parent_kind_map.get(kind)
if parent_kind:
    parents = coord.list_sessions(kind=parent_kind)
    parent_id = parents[0].session_id if parents else None

try:
    sid = coord.create_session(
        kind=kind,
        owner_opencode_session_id=opencode_sid,
        goal={"intent": intent, "subject": subject, "expected_outcome": expected_outcome},
        parent_session_id=parent_id,
        context_pointer=context_pointer,
    )
    print(f"rddf-session: {sid} ({kind}, parent={parent_id})")
except ConflictError as e:
    print(f"CONFLICT: {e}")
    print('  → use skill_use(\'rddf-session\',\'list\') to inspect')
    print('  → then skill_use(\'rddf-session\',\'resume\'|\'abandon\') to resolve')
    sys.exit(2)
PYEOF
}

# rddf_session_hook_close <kind> <end_reason> <intent>
rddf_session_hook_close() {
  local kind="$1"
  local end_reason="$2"
  local intent="$3"

  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"

  KIND="$kind" \
  END_REASON="$end_reason" \
  INTENT="$intent" \
  PROJECT_ROOT="$PROJECT_ROOT" \
  OPENCODE_SESSION_ID="$OPENCODE_SESSION_ID" \
  python3 <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator

project_root = os.environ["PROJECT_ROOT"]
kind = os.environ["KIND"]
end_reason = os.environ["END_REASON"]
intent = os.environ["INTENT"]
opencode_sid = os.environ["OPENCODE_SESSION_ID"]

sessions_file = os.path.join(project_root, ".rddf", "state", "sessions.json")
if not os.path.exists(sessions_file):
    print("rddf-session: sessions.json not found, skipping close")
    sys.exit(0)

coord = RddfSessionCoordinator(sessions_file=sessions_file)
try:
    sid = coord.create_session(
        kind=kind,
        owner_opencode_session_id=opencode_sid,
        goal={"intent": intent},
    )
    coord.update_session_status(sid, "completed", end_reason=end_reason)
    print(f"rddf-session: {sid} -> completed ({end_reason})")
except Exception as e:
    print(f"rddf-session close skipped: {e}")
PYEOF
}

# rddf_session_hook_heartbeat <kind> [change_name]
#
# Called by guide-ship Phase 3 after each archive to refresh the
# rddf-session heartbeat (marking the session as still active until
# ship-done). Optionally detaches the archived change from the session.
#
# Gracefully skips when sessions.json does not exist (consistent with
# entry/close hooks after P3-4c alignment).
rddf_session_hook_heartbeat() {
  local kind="$1"
  local change_name="${2:-}"

  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"

  KIND="$kind" \
  CHANGE_NAME="$change_name" \
  PROJECT_ROOT="$PROJECT_ROOT" \
  OPENCODE_SESSION_ID="$OPENCODE_SESSION_ID" \
  python3 <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator

project_root = os.environ["PROJECT_ROOT"]
kind = os.environ["KIND"]
change_name = os.environ.get("CHANGE_NAME") or None
opencode_sid = os.environ["OPENCODE_SESSION_ID"]

sessions_file = os.path.join(project_root, ".rddf", "state", "sessions.json")
if not os.path.exists(sessions_file):
    print("rddf-session: sessions.json not found, skipping heartbeat")
    sys.exit(0)

coord = RddfSessionCoordinator(sessions_file=sessions_file)
try:
    sid = coord.create_session(
        kind=kind,
        owner_opencode_session_id=opencode_sid,
        goal={"intent": "guide-ship"},
    )
    if change_name:
        coord.detach_change(sid, change_name)
    coord.refresh_heartbeat(sid)
    action = f"(after archive {change_name})" if change_name else ""
    print(f"rddf-session: {sid} heartbeat refreshed {action}".strip())
except Exception as e:
    print(f"rddf-session heartbeat skip: {e}")
PYEOF
}

# rddf_session_hook_attach <kind> <change_name>
#
# Called by guide-plan Phase 2 (after propose) and guide-ship Phase 1
# (after plan generation) to attach a change to the active rddf-session.
# Idempotent: duplicate calls do not raise an error.
rddf_session_hook_attach() {
  local kind="$1"
  local change_name="$2"

  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"

  KIND="$kind" \
  CHANGE_NAME="$change_name" \
  PROJECT_ROOT="$PROJECT_ROOT" \
  OPENCODE_SESSION_ID="$OPENCODE_SESSION_ID" \
  python3 <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["PROJECT_ROOT"])
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator

project_root = os.environ["PROJECT_ROOT"]
kind = os.environ["KIND"]
change_name = os.environ.get("CHANGE_NAME") or ""
opencode_sid = os.environ["OPENCODE_SESSION_ID"]

sessions_file = os.path.join(project_root, ".rddf", "state", "sessions.json")
if not os.path.exists(sessions_file):
    print("rddf-session: sessions.json not found, skipping attach")
    sys.exit(0)

coord = RddfSessionCoordinator(sessions_file=sessions_file)
try:
    sid = coord.create_session(
        kind=kind,
        owner_opencode_session_id=opencode_sid,
        goal={"intent": "guide-ship"},
    )
    if change_name:
        coord.attach_change(sid, change_name)
    print(f"rddf-session: {sid} change {change_name} attached")
except Exception as e:
    print(f"rddf-session attach skip: {e}")
PYEOF
}