# _lib/rddf_session_hooks.sh
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
#   - OPENCODE_SESSION_ID fallback: $(hostname -s)_$PPID (parent = opencode
#     server PID; stable across bash tool calls in one window, differs
#     across windows — fixes per-call $$ owner mismatch)
#   - PROJECT_ROOT fallback: git rev-parse --show-toplevel || pwd
#   - Entry: prints "rddf-session: <sid> (<kind>, parent=<id>)" on success
#   - Entry: prints "CONFLICT: ..." + 4-option prompt hint + exit 2 on conflict
#   - Close: prints "rddf-session: <sid> -> completed (<reason>)" on success
#   - Close: prints "rddf-session close skipped: <err>" on unexpected error
#   - Close: prints "rddf-session: sessions.json not found, skipping close"
#     when sessions.json missing (consistent across all 3 callers; was
#     inconsistent in original — only ship was silent)
#

# _rddf_resolve_owner — 3-layer owner ID detection (fix-rddf-session-owner-stability)
#
# Sets 2 env vars (or returns 0 + sets shell vars):
#   RDDF_OWNER     — owner ID (string)
#   RDDF_OWNER_FROM — fallback source: env | proc-cmdline | shell-pid | cached-file
#
# Priority chain:
#   1. $OPENCODE_SESSION_ID env var (OpenCode platform injection)
#   2. ~/.cache/rddf-session-owner cache file (TTL 1h, 0600 perms)
#   3. /proc/<shell-ppid>/cmdline probe (depth ≤5, accept iff cmdline contains "opencode")
#   4. $(hostname -s)_$$  (current shell PID fallback)
#
# 跨 bash 调用持久化机制: 探测成功后将 owner+source 写入 ~/.cache/rddf-session-owner
# (per-host, 0600, TTL 1h). 后续 fallback 在 env var 缺失时优先读此文件.
_rddf_resolve_owner() {
  # 1. env var 优先
  if [ -n "${OPENCODE_SESSION_ID:-}" ]; then
    RDDF_OWNER="$OPENCODE_SESSION_ID"
    RDDF_OWNER_FROM="env"
    export RDDF_OWNER RDDF_OWNER_FROM
    return 0
  fi

  # 2. cache file (per-host, 0600, TTL 1h)
  local cache_file="${HOME}/.cache/rddf-session-owner"
  if [ -f "$cache_file" ]; then
    local cache_age=999999
    if command -v stat >/dev/null 2>&1; then
      local now_ts
      now_ts=$(date +%s 2>/dev/null || echo 0)
      local mtime_ts
      mtime_ts=$(stat -c %Y "$cache_file" 2>/dev/null || stat -f %m "$cache_file" 2>/dev/null || echo 0)
      if [ "$now_ts" -gt 0 ] && [ "$mtime_ts" -gt 0 ]; then
        cache_age=$((now_ts - mtime_ts))
      fi
    fi
    if [ "$cache_age" -lt 3600 ]; then
      RDDF_OWNER=$(awk -F'\t' 'NR==1{print $1; exit}' "$cache_file" 2>/dev/null)
      RDDF_OWNER_FROM="cached-file"
      if [ -n "$RDDF_OWNER" ]; then
        export RDDF_OWNER RDDF_OWNER_FROM
        return 0
      fi
    fi
  fi

  # 3. /proc cmdline 探测 (深度 ≤5, 仅采纳 cmdline 含 "opencode")
  local depth=0
  local cur_ppid="$$"
  while [ "$depth" -lt 5 ] && [ -n "$cur_ppid" ] && [ "$cur_ppid" -gt 1 ]; do
    if [ -r "/proc/$cur_ppid/cmdline" ]; then
      local cmdline
      cmdline=$(tr '\0' ' ' < "/proc/$cur_ppid/cmdline" 2>/dev/null || true)
      if echo "$cmdline" | grep -q "opencode"; then
        RDDF_OWNER="$(hostname -s)_${cur_ppid}"
        RDDF_OWNER_FROM="proc-cmdline"
        # best-effort 写 cache
        if command -v mkdir >/dev/null 2>&1; then
          mkdir -p "$(dirname "$cache_file")" 2>/dev/null || true
          chmod 700 "$(dirname "$cache_file")" 2>/dev/null || true
          printf '%s\t%s\n' "$RDDF_OWNER" "$RDDF_OWNER_FROM" > "$cache_file" 2>/dev/null || true
          chmod 600 "$cache_file" 2>/dev/null || true
        fi
        export RDDF_OWNER RDDF_OWNER_FROM
        return 0
      fi
    fi
    # 沿 PPid 链向上
    if [ -r "/proc/$cur_ppid/status" ]; then
      cur_ppid=$(awk '/^PPid:[[:space:]]+[0-9]+/{print $2; exit}' "/proc/$cur_ppid/status" 2>/dev/null || echo "")
    else
      cur_ppid=""
    fi
    depth=$((depth + 1))
  done

  # 4. shell PID 兜底
  RDDF_OWNER="$(hostname -s)_$$"
  RDDF_OWNER_FROM="shell-pid"
  export RDDF_OWNER RDDF_OWNER_FROM
}

# _rddf_should_auto_archive <total_count> <keep> <threshold>
#
# Pure helper: returns 0 (true) if auto-archive should trigger, 1 (false) otherwise.
# Inputs may come from RDDF_AUTO_ARCHIVE_KEEP (default 10) and
# RDDF_AUTO_ARCHIVE_THRESHOLD (default keep+5).
#
# Disabled when:
#   - keep <= 0 (RDDF_AUTO_ARCHIVE_KEEP=0)
#   - threshold <= 0 (RDDF_AUTO_ARCHIVE_THRESHOLD=0)
# Trigger when: total_count >= threshold
#
# Note: keeps helper as pure function so tests don't need sessions.json fixture.
_rddf_should_auto_archive() {
  local total_count="$1"
  local keep="$2"
  local threshold="$3"

  # Default threshold = keep + 5 when not provided
  if [ -z "$threshold" ]; then
    threshold=$((keep + 5))
  fi

  # Disabled if keep or threshold <= 0
  if [ "$keep" -le 0 ] 2>/dev/null || [ "$threshold" -le 0 ] 2>/dev/null; then
    return 1
  fi

  # Trigger if total_count >= threshold
  if [ "$total_count" -ge "$threshold" ] 2>/dev/null; then
    return 0
  fi
  return 1
}

# _rddf_auto_archive_if_needed <sessions_file>
#
# Best-effort auto-archive trigger. Reads sessions.json, counts total sessions,
# invokes _rddf_should_auto_archive to decide. If triggered, calls
# RddfSessionCoordinator.archive_history(keep) via Python (env-var pattern).
# All exceptions swallowed to never block the main hook flow.
#
# Env vars:
#   RDDF_AUTO_ARCHIVE_KEEP       (default 10, 0 = disabled)
#   RDDF_AUTO_ARCHIVE_THRESHOLD  (default keep+5, 0 = disabled)
_rddf_auto_archive_if_needed() {
  local sessions_file="$1"

  # Read env vars with defaults
  local keep="${RDDF_AUTO_ARCHIVE_KEEP:-10}"
  local threshold="${RDDF_AUTO_ARCHIVE_THRESHOLD:-}"

  # Compute threshold default = keep + 5 if not set
  if [ -z "$threshold" ]; then
    threshold=$((keep + 5))
  fi

  # Skip if sessions.json does not exist (no harm, no foul)
  if [ ! -f "$sessions_file" ]; then
    return 0
  fi

  # Count total sessions
  local total_count
  total_count=$(python3 -c "
import json, sys
try:
    with open('$sessions_file') as f:
        data = json.load(f)
    print(len(data.get('sessions', [])))
except Exception as e:
    print(f'rddf-session auto-archive skipped: cannot read sessions.json: {e}', file=sys.stderr)
    print(0)
")

  # Decide via pure helper
  if ! _rddf_should_auto_archive "$total_count" "$keep" "$threshold"; then
    return 0
  fi

  # Trigger: invoke archive_history via Python (best-effort, swallow errors)
  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}" \
  SESSIONS_FILE="$sessions_file" \
  ARCHIVE_KEEP="$keep" \
  python3 <<'PYEOF' 2>/dev/null
import os, sys
try:
    sys.path.insert(0, os.environ["PROJECT_ROOT"])
    from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
    coord = RddfSessionCoordinator(sessions_file=os.environ["SESSIONS_FILE"])
    archived = coord.archive_history(keep=int(os.environ["ARCHIVE_KEEP"]))
    if archived > 0:
        print(f"rddf-session auto-archive: {archived} sessions moved to .archive.json")
except Exception as e:
    print(f"rddf-session auto-archive skipped: {e}", file=sys.stderr)
PYEOF
  return 0  # always exit 0 (best-effort)
}

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
  _rddf_resolve_owner
  OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-${RDDF_OWNER:-}}"
  OPENCODE_SESSION_ID_FROM="${OPENCODE_SESSION_ID_FROM:-${RDDF_OWNER_FROM:-shell-pid}}"
  export OPENCODE_SESSION_ID_FROM

  if [ -z "${RDDF_WORKFLOW_GROUP:-}" ]; then
    if command -v python3 >/dev/null 2>&1; then
      RDDF_WORKFLOW_GROUP=$(python3 -c "import uuid; print(uuid.uuid4())")
    else
      RDDF_WORKFLOW_GROUP="auto-$(date +%s%N)"
    fi
    export RDDF_WORKFLOW_GROUP
  fi

  local sessions_file="${PROJECT_ROOT}/.rddf/state/sessions.json"

  KIND="$kind" \
  INTENT="$intent" \
  SUBJECT="$subject" \
  EXPECTED_OUTCOME="$expected_outcome" \
  CONTEXT_POINTER="$context_pointer" \
  WORKFLOW_GROUP="$RDDF_WORKFLOW_GROUP" \
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
workflow_group = os.environ.get("WORKFLOW_GROUP", "").strip() or None

sessions_file = os.path.join(project_root, ".rddf", "state", "sessions.json")
os.makedirs(os.path.dirname(sessions_file), exist_ok=True)
coord = RddfSessionCoordinator(sessions_file=sessions_file)
coord.check_heartbeat_timeouts()

parent_id = None
parent_kind_map = {"stage_design": "stage_arch", "stage_plan": "stage_design", "stage_ship": "stage_plan"}
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
    if workflow_group:
        data = coord._store.read_unlocked()
        for s in data.get("sessions", []):
            if s.get("session_id") == sid:
                s["workflow_group"] = workflow_group
                break
        coord._store.atomic_write(data)
    print(f"rddf-session: {sid} ({kind}, parent={parent_id}, workflow_group={workflow_group})")
except ConflictError as e:
    print(f"CONFLICT: {e}")
    print('  → use skill_use(\'rddf-session\',\'list\') to inspect')
    print('  → then skill_use(\'rddf-session\',\'resume\'|\'abandon\') to resolve')
    sys.exit(2)
PYEOF

  local _entry_exit=$?
  if [ "$_entry_exit" -ne 0 ]; then
    return "$_entry_exit"
  fi

  # Auto-archive best-effort (P1: add-rddf-session-auto-archive-on-entry)
  _rddf_auto_archive_if_needed "$sessions_file" 2>/dev/null || true
}

# rddf_session_hook_close <kind> <end_reason> <intent>
rddf_session_hook_close() {
  local kind="$1"
  local end_reason="$2"
  local intent="$3"

  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  _rddf_resolve_owner
  OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-${RDDF_OWNER:-}}"
  OPENCODE_SESSION_ID_FROM="${OPENCODE_SESSION_ID_FROM:-${RDDF_OWNER_FROM:-shell-pid}}"
  export OPENCODE_SESSION_ID_FROM

  local sessions_file="${PROJECT_ROOT}/.rddf/state/sessions.json"

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

  # Auto-archive best-effort (P1: add-rddf-session-auto-archive-on-entry)
  _rddf_auto_archive_if_needed "$sessions_file" 2>/dev/null || true
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
  _rddf_resolve_owner
  OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-${RDDF_OWNER:-}}"
  OPENCODE_SESSION_ID_FROM="${OPENCODE_SESSION_ID_FROM:-${RDDF_OWNER_FROM:-shell-pid}}"
  export OPENCODE_SESSION_ID_FROM

  KIND="$kind" \
  CHANGE_NAME="$change_name" \
  RDDF_SUB_PHASE="${RDDF_SUB_PHASE:-}" \
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
sub_phase = os.environ.get("RDDF_SUB_PHASE", "").strip() or None

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
    if sub_phase:
        data = coord._store.read_unlocked()
        for s in data.get("sessions", []):
            if s.get("session_id") == sid:
                s["sub_phase"] = sub_phase
                from datetime import datetime, timezone
                s["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
                break
        coord._store.atomic_write(data)
    else:
        coord.refresh_heartbeat(sid)
    action = f"(after archive {change_name})" if change_name else ""
    sub_phase_note = f" sub_phase={sub_phase}" if sub_phase else ""
    print(f"rddf-session: {sid} heartbeat refreshed {action}{sub_phase_note}".strip())
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
  _rddf_resolve_owner
  OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-${RDDF_OWNER:-}}"
  OPENCODE_SESSION_ID_FROM="${OPENCODE_SESSION_ID_FROM:-${RDDF_OWNER_FROM:-shell-pid}}"
  export OPENCODE_SESSION_ID_FROM

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
# rddf_session_hook_detach <kind> <change_name>
#   Symmetric counterpart to attach — detaches a change from the session.
#   Used when switching worktrees or abandoning a change.
rddf_session_hook_detach() {
  local kind="$1"
  local change_name="$2"

  PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  _rddf_resolve_owner
  OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-${RDDF_OWNER:-}}"
  OPENCODE_SESSION_ID_FROM="${OPENCODE_SESSION_ID_FROM:-${RDDF_OWNER_FROM:-shell-pid}}"
  export OPENCODE_SESSION_ID_FROM

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
    print("rddf-session: sessions.json not found, skipping detach")
    sys.exit(0)

coord = RddfSessionCoordinator(sessions_file=sessions_file)
try:
    # Find session by owner + kind
    sessions = coord.list_sessions(kind=kind, owner_opencode_session_id=opencode_sid)
    if not sessions:
        print(f"rddf-session: no active {kind} session, detach skipped")
        sys.exit(0)
    
    sid = sessions[0].session_id
    if change_name:
        coord.detach_change(sid, change_name)
    print(f"rddf-session: {sid} change {change_name} detached")
except Exception as e:
    print(f"rddf-session detach skip: {e}")
PYEOF
}
