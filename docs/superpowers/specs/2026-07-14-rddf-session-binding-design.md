# rddf-session Binding & Recommendation — Design Spec

**Date:** 2026-07-14
**Status:** Pending Review
**Scope:** Add discoverable rddf-session binding + next-session recommendation surface
**Target Branch:** `master`
**Supersedes:** None
**Related:** ADR-0017 (rddf-session), ADR-0010 (multi-session management)

---

## 1. Background

`rdd-workflow` v2.0 ships ADR-0017 (rddf-session), which provides
cross-OpenCode-session workflow recovery via 5 subcommands:
`list / show / resume / abandon / archive-history`. The infrastructure
to **bind** an OpenCode session to an rddf-session already exists —
`guide-arch/plan/ship` auto-create rddf-sessions on entry with
`owner_opencode_session_id = $OPENCODE_SESSION_ID`, and
`rddf-session resume <id>` already calls `transfer_ownership()`.

What's missing is the **discovery layer**:

1. The `guide` recommender cannot answer *"which rddf-session am I currently
   bound to?"* — it scans `.arch-handoff.json` / `.plan-handoff.json` /
   `proposal-suggestions.md` but ignores `.rddf/state/sessions.json`.
2. There is no single command that says *"you have no current binding;
   the next orphaned session you should resume is `rds_xxx`."*
3. Users running `rddf-session list` see all sessions but must read
   `owner_opencode_session_id` columns themselves to figure out their binding.
4. The "save current binding" UX is implicit in `resume` — there is no
   explicit `bind <id>` command, and the discoverability of `resume` as
   "the way to bind" is poor.

This spec closes those gaps with a thin, read-only binding surface that:

- Adds 2 methods to `RddfSessionCoordinator` (`find_current_binding`,
  `find_next_recommendation`).
- Adds a `current` subcommand to `rddf-session.md` that prints binding +
  recommendation.
- Adds a `scan_session_binding()` function to `skills/_lib/scan-state.sh`
  and a small extension to `skills/guide.md` so the recommender surfaces
  binding status (1-2 lines appended after RECOMMEND/REASON).
- Locks the behavior with 1 unit test file and 2 integration test files.

**No state file schema changes. No API breaks.**

## 2. Goals

1. Make "which rddf-session am I bound to" answerable via `skill_use("rddf-session current")`.
2. When unbound, recommend the most recently started orphaned rddf-session
   to resume (with the exact subcommand string to run).
3. Surface the same information in the `guide` recommender output (no
   change to `RECOMMEND` priority; just 1-2 appended lines).
4. Reuse the existing `owner_opencode_session_id` field as the binding
   semantic — no new state file.
5. Add `find_current_binding()` and `find_next_recommendation()` to
   `RddfSessionCoordinator` as pure read methods (no locks held beyond
   `_with_file_lock` semantics).
6. Lock behavior with tests in `tests/unit/` (Python) and
   `tests/integration/` (bats).
7. Document the binding policy in `AGENTS.md` and add a cross-reference
   in `ADR-0017`.

## 3. Non-Goals

- No new state file (e.g. `.rddf/state/current_binding.json`). The
  existing `owner_opencode_session_id` field is the binding.
- No new top-level skill. `rddf-session.md` gains a `current` subcommand.
- No breaking changes to `RddfSessionCoordinator` public API (only additive
  methods).
- No schema version bump of `sessions.json` (v1 unchanged).
- No modification to `guide-arch/plan/ship` entry hooks (they already
  auto-create + bind; per ADR-0017 Migration Plan, this is complete).
- No recommendation algorithm that requires cross-session intelligence
  (e.g. matching `RECOMMEND` kind to `stage_*` kind). The first version
  is "any orphaned, most recent started_at". A future iteration may
  add kind matching if user demand emerges.
- No "force takeover" command. `rddf-session resume` already supports
  cross-session transfer via `transfer_ownership()`. New explicit
  takeover UX is out of scope.
- No new ADR. The change is incremental within ADR-0017 scope; we
  update ADR-0017 with a Cross-Reference section instead.

## 4. Files In Scope

| File | Action | Notes |
|------|--------|-------|
| `skills/_lib/rddf_session.py` | **Edit** | Add `find_current_binding()` + `find_next_recommendation()` methods (~25 LOC) |
| `skills/rddf-session.md` | **Edit** | Add `current` subcommand + frontmatter subcommands list (~35 LOC bash heredoc) |
| `skills/_lib/scan-state.sh` | **Edit** | Add `scan_session_binding()` function + `BINDING_LINES` global (~30 LOC) |
| `skills/guide.md` | **Edit** | Append `scan_session_binding` invocation + `BINDING_LINES` print loop (~5 LOC) |
| `tests/unit/test_rddf_binding.py` | **Create** | ~10 unit tests for the 2 new methods |
| `tests/integration/test_rddf_session_current.bats` | **Create** | ~8 integration tests for `current` subcommand |
| `tests/integration/test_guide_binding_alert.bats` | **Create** | ~5 integration tests for guide binding lines |
| `AGENTS.md` | **Edit** | Add `### Session Binding Policy` section (~5 LOC) |
| `docs/adr/ADR-0017-rddf-session.md` | **Edit** | Add `## Cross-Reference` section linking to this spec (~5 LOC) |

Total: 3 created, 6 edited, 0 deleted.

**Not touched:**
`ADR-0010`, `ADR-0018`, `ADR-0019`, `guide-arch.md`, `guide-plan.md`,
`guide-ship.md`, `state_vector.py`, `state_vector_schema.json`,
`sessions_schema.json`, `feature.md`, `iteration.py`, `deps_output.py`.

## 5. Architecture

```
User invokes guide (recommender)             User invokes rddf-session directly
───────────────────────────────             ───────────────────────────────
                                                                          │
   skills/guide.md                              skills/rddf-session.md    │
   ├─ scan_state $ROOT ──┐                                                  │
   │  (existing 11-prio) │                                                  │
   │                     ▼                                                  │
   ├─ echo RECOMMEND + REASON                                               │
   │                     │                                                  │
   ├─ scan_session_binding $ROOT ──┐                                       │
   │  (NEW function in scan-state.sh)│                                       │
   │                                ▼                                       │
   ├─ print BINDING_LINES  ◄──────── NEW: read-only ──┐                     │
   │  (1-2 lines, only when non-empty)                │                     │
   │                                                   │                     │
   ▼                                                   ▼                     ▼
skills/_lib/scan-state.sh                       skills/_lib/rddf_session.py
   └─ inline python3 -c calls                            ├─ find_current_binding(owner)
      (PY_PROJECT_ROOT cwd-safety pattern)               └─ find_next_recommendation(owner)
                                                                          │
                                                                          ▼
                                                       .rddf/state/sessions.json
                                                       (read-only, fcntl.flock
                                                        released after each call)
```

**Reuse boundary:**
- `RddfSessionCoordinator.__init__` + `_read_unlocked` + `_with_file_lock`
  are reused as-is.
- `OPENCODE_SESSION_ID` env var with `hostname -s_$$` fallback is reused
  from `rddf-session.md` line 86.
- `PY_PROJECT_ROOT` cwd-safety env var pattern is reused from `scan-state.sh`
  line 180.

**No-touch boundary:**
- The existing 5 rddf-session subcommands (list / show / resume / abandon /
  archive-history) are not modified.
- The existing 11-priority `scan_state` is not modified.
- `sessions.json` schema v1 is not modified.

## 6. Data Model

### 6.1 No schema changes

`sessions.json` schema v1 (ADR-0017 §Schema) is unchanged. We only
**read** two existing fields:

| Field | Used for |
|-------|----------|
| `sessions[i].owner_opencode_session_id` | binding lookup: matches `OPENCODE_SESSION_ID` env var |
| `sessions[i].state` | filter: only `active` counts as "bound"; `orphaned` is "next recommended" |

### 6.2 New Python methods on `RddfSessionCoordinator`

```python
def find_current_binding(
    self, owner_opencode_session_id: str
) -> Optional[RddfSession]:
    """Return the active rddf-session owned by `owner_opencode_session_id`.

    Returns None if no active session is bound. Does not consider orphaned
    sessions (use find_next_recommendation for those). If multiple active
    sessions exist for the same owner, returns the most recently started
    one (deterministic via list_sessions sort).
    """
```

```python
def find_next_recommendation(
    self, owner_opencode_session_id: Optional[str] = None
) -> Optional[RddfSession]:
    """Return the most recently started orphaned rddf-session.

    Algorithm:
      1. Call self.list_sessions() (already sorted by started_at desc).
      2. Filter: state == "orphaned".
      3. Return the first match.
      4. None if no orphaned sessions exist.

    The owner_opencode_session_id param is currently unused; reserved for
    future "match by owner" filtering (e.g. only recommend sessions
    originally owned by this OpenCode session).
    """
```

### 6.3 New bash function in `scan-state.sh`

```bash
# scan_session_binding [PROJECT_ROOT]
#   Reads .rddf/state/sessions.json via RddfSessionCoordinator and populates
#   BINDING_LINES array with 1-2 formatted lines.
#   Line 1: "📍 Current: rds_xxx (kind=stage_X, 12m ago)" if bound
#           "📍 No current binding" otherwise
#   Line 2: "💡 Recommended: rds_yyy ... → skill_use(...)" only when unbound
#           AND an orphaned session exists.
#   Silent on missing/invalid file (BINDING_LINES stays empty).
BINDING_LINES=()
scan_session_binding() { … }
```

## 7. Algorithm

### Step 1: `find_current_binding`

```python
def find_current_binding(self, owner_opencode_session_id):
    def _do():
        data = self._read_unlocked()
        matches = [
            RddfSession(**s) for s in data["sessions"]
            if s["state"] == "active"
            and s["owner_opencode_session_id"] == owner_opencode_session_id
        ]
        if not matches:
            return None
        # Deterministic: most recently started wins
        matches.sort(key=lambda s: s.started_at, reverse=True)
        return matches[0]
    return self._with_file_lock(_do)
```

Time complexity: O(n) where n = number of sessions in `sessions.json`.
Expected n < 100 in practice.

### Step 2: `find_next_recommendation`

```python
def find_next_recommendation(self, owner_opencode_session_id=None):
    def _do():
        data = self._read_unlocked()
        candidates = [
            RddfSession(**s) for s in data["sessions"]
            if s["state"] == "orphaned"
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda s: s.started_at, reverse=True)
        return candidates[0]
    return self._with_file_lock(_do)
```

Time complexity: O(n log n) due to sort. Sort is necessary because
`list_sessions()` sorts differently (started_at desc) — we re-sort
in case of schema-level sort changes.

### Step 3: `scan_session_binding` (bash + inline python3)

The bash function captures Python stdout into `BINDING_LINES` via
process substitution `< <(...)` to avoid double execution.

```bash
scan_session_binding() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local SESSIONS_FILE="$PROJECT_ROOT/.rddf/state/sessions.json"
  BINDING_LINES=()
  [ -f "$SESSIONS_FILE" ] || return 0
  local owner="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"
  while IFS= read -r line; do
    BINDING_LINES+=("$line")
  done < <(PY_PROJECT_ROOT="$PROJECT_ROOT" \
    python3 - "$SESSIONS_FILE" "$owner" "$PROJECT_ROOT" <<'PYEOF'
import os, sys
sys.path.insert(0, sys.argv[3] if len(sys.argv) > 3 else ".")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file=sys.argv[1])
coord.check_heartbeat_timeouts()
owner = sys.argv[2]
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
    )
}
```

## 8. User Interface

### 8.1 New `current` subcommand

```
skill_use("rddf-session current")
```

**Output when bound**:
```
📍 Current: rds_c9961e41e40e (kind=stage_ship, started=2026-07-11T18:45:05)
```

**Output when unbound + orphaned exists**:
```
📍 No current binding
💡 Recommended: rds_8af12c39b41d (kind=stage_plan, last_heartbeat=2026-07-10T14:51:03)
   → skill_use("rddf-session resume rds_8af12c39b41d")
```

**Output when unbound + no orphaned**:
```
📍 No current binding
   No orphaned rddf-sessions found. Run guide-arch or guide-plan to start.
```

**Output when sessions.json missing** (silent fallback, exit 0):
```
📍 No current binding
   No orphaned rddf-sessions found. Run guide-arch or guide-plan to start.
```

### 8.2 Updated `guide` recommender output

**Before** (existing):
```
🔍 Project state scan:
   - roadmap.md: ✅ exists
   - .rddf/state/.arch-handoff.json: ✅ exists
   - .rddf/state/.plan-handoff.json: ✅ exists
   - committed changes: 2
   - worktrees: 1 (active)

💡 Recommended: skill_use("guide-ship")
   Reason: 变更生成已完成 → 进入变更执行
```

**After** (new — appended lines when binding info exists):
```
🔍 Project state scan:
   - roadmap.md: ✅ exists
   - .rddf/state/.arch-handoff.json: ✅ exists
   - .rddf/state/.plan-handoff.json: ✅ exists
   - committed changes: 2
   - worktrees: 1 (active)

💡 Recommended: skill_use("guide-ship")
   Reason: 变更生成已完成 → 进入变更执行
📍 Current: rds_c9961e41e40e (kind=stage_ship, started=2026-07-11T18:45:05)
```

Or when unbound:
```
💡 Recommended: skill_use("guide-ship")
   Reason: 变更生成已完成 → 进入变更执行
📍 No current binding
💡 Recommended: rds_8af12c39b41d (kind=stage_plan, last_heartbeat=2026-07-10T14:51:03)
   → skill_use("rddf-session resume rds_8af12c39b41d")
```

`RECOMMEND` and `REASON` are unchanged. Only `BINDING_LINES` is appended.

## 9. Error Handling

| Scenario | Behavior | Exit |
|----------|----------|------|
| `sessions.json` missing | `BINDING_LINES=()` empty; `current` prints fallback text | 0 |
| JSON parse error | Same as missing (silent fallback) | 0 |
| Schema version mismatch (future v2) | Silent skip (filter by version=1) | 0 |
| `OPENCODE_SESSION_ID` unset | Fallback `hostname -s_$$` (mirrors rddf-session.md line 86) | 0 |
| File lock contention | `_with_file_lock` raises `RddfSessionError`; caller may print + exit 1 | varies |
| Multiple active sessions for same owner | Return most recently started (deterministic) | 0 |
| All sessions terminal | `find_next_recommendation` returns None; `current` prints "no orphaned" | 0 |
| Stale heartbeat (active but >30min) | `check_heartbeat_timeouts()` promotes to orphaned first | 0 |
| Bash glob / cwd safety | `PY_PROJECT_ROOT` env var pattern (scan-state.sh line 180) | 0 |

## 10. Testing

### 10.1 Unit tests (`tests/unit/test_rddf_binding.py`, ~10 cases)

| Test | Asserts |
|------|---------|
| `test_find_current_binding_returns_active_for_owner` | Owner with one active session → returns that session |
| `test_find_current_binding_returns_none_when_terminal` | Owner with completed/failed only → returns None |
| `test_find_current_binding_returns_none_for_different_owner` | Active session owned by other → returns None |
| `test_find_current_binding_picks_most_recent_of_multiple` | Two actives same owner → returns newer started_at |
| `test_find_next_recommendation_returns_most_recent_orphaned` | Three orphaned → returns newest started_at |
| `test_find_next_recommendation_returns_none_when_no_orphaned` | Only active/completed → returns None |
| `test_find_next_recommendation_ignores_active_and_completed` | Mixed states → only orphaned considered |
| `test_check_heartbeat_timeouts_then_find_current` | Active older than 30min → orphaned promoted → find_current_binding returns None |
| `test_empty_sessions_file` | sessions.json with empty sessions[] → both methods return None |
| `test_corrupted_sessions_file_raises_clear_error` | Invalid JSON → RddfSessionError raised (caller catches) |

### 10.2 Integration tests (`tests/integration/test_rddf_session_current.bats`, ~8 cases)

| Test | Asserts |
|------|---------|
| `current 输出包含 rds_id 当 active 绑定存在` | Bound session → stdout contains "📍 Current: rds_<id>" |
| `current 输出 No current binding 当无绑定` | No active session owned by current → stdout contains "📍 No current binding" |
| `current 输出 Recommended next 当存在 orphaned` | Orphaned exists → stdout contains "💡 Recommended: rds_<id>" and the resume subcommand string |
| `current 在 sessions.json 缺失时输出 fallback 文本` | File deleted → stdout contains "No orphaned rddf-sessions found" |
| `current 在 JSON 损坏时 silent return exit 0` | Truncated file → exit 0, fallback text |
| `current 使用 OPENCODE_SESSION_ID env var` | Env var set → finds session with matching owner_opencode_session_id |
| `current fallback 到 hostname_$$` | Env var unset → uses fallback; if no matching session, returns None |
| `current 不修改 sessions.json` | Run twice, file mtime unchanged, content byte-equal |

### 10.3 Integration tests (`tests/integration/test_guide_binding_alert.bats`, ~5 cases)

| Test | Asserts |
|------|---------|
| `guide 输出 binding 行 当有 current binding` | RECOMMEND line + binding line in correct order |
| `guide 输出 recommended next 行 当无 binding + 有 orphaned` | Both lines emitted, recommendation line ends with subcommand string |
| `guide 不输出 binding 行 当 sessions.json 缺失` | Only RECOMMEND + REASON, no binding lines |
| `guide 不改变 RECOMMEND 当 binding 状态变化` | Two scans (bound / unbound) emit same RECOMMEND |
| `guide binding 行在 RECOMMEND/REASON 之后` | Binding lines never appear before REASON |

### 10.4 CI constant-truth gate

`grep -rn "assert .* or True" tests/` must remain empty (project rule).
All new tests use plain `assert` with informative messages.

## 11. Blast Radius

| File | Change | User-visible? |
|------|--------|---------------|
| `skills/_lib/rddf_session.py` | +2 methods | No (internal API) |
| `skills/rddf-session.md` | +1 subcommand | **Yes** (new `current`) |
| `skills/_lib/scan-state.sh` | +1 function | No (called by guide) |
| `skills/guide.md` | +5 LOC append | **Yes** (binding lines in output) |
| `AGENTS.md` | +5 LOC policy note | No (docs) |
| `ADR-0017-rddf-session.md` | +5 LOC cross-ref | No (docs) |

No behavioral changes to other skills. The new `current` subcommand and
the appended guide binding lines are additive — existing flows are unaffected.

## 12. Migration & Compatibility

- **Backward compatible**: existing `sessions.json` files (any state, any
  age) are handled gracefully by `find_current_binding` (returns None if
  no active match) and `find_next_recommendation` (returns None if no
  orphaned).
- **No schema version bump**: `sessions_schema.json` v1 is unchanged.
- **No data migration script**: the new feature is purely additive.
- **rddf-session subcommands** other than `current` are unchanged. Users
  who upgrade can immediately run `rddf-session current` without any
  prior setup.
- **guide recommender backward compat**: when `sessions.json` is missing
  or invalid, `BINDING_LINES` stays empty and the output looks identical
  to v2.0.x. The 11-priority `RECOMMEND` is unchanged.

## 13. Open Questions

None at spec time. All design decisions were resolved during brainstorming
(5 user-confirmed choices: scan-state.sh extension, function-return-value
variant, only active+orphaned, multi-line table with limit 3, no new
state file).

## 14. Out of Scope (explicit deferrals)

- **Kind-matched recommendations** (e.g. "if RECOMMEND=guide-plan, prefer
  orphaned stage_plan over stage_arch"). v1 uses "any kind, most recent".
  Future iteration may add via `find_next_recommendation(kind=...)`.
- **`bind` subcommand** distinct from `resume`. The user requested "save
  current binding"; we judged `resume` already satisfies this and
  explicitly documented it in `rddf-session.md`. A future `bind` may be
  added if `resume`'s side-effect (orphaned → active transition) is
  unwanted.
- **Force takeover UX** beyond what `resume` provides (cross-session
  ownership transfer with heartbeat refresh).
- **Mandatory-binding runtime check** in scan-state.sh. The check lives
  at guide-arch/plan/ship entry hooks already (per ADR-0017). A future
  spec may add a pre-scan check if users bypass the state machines.
- **Live refresh / file-watcher** for sessions.json. The `current` /
  `scan_session_binding` calls are on-demand; users re-run for fresh data.
- **CLI flag integration with `openspec`**. The skill body uses bash
  case dispatch; no argparse.
- **Cross-platform file lock** beyond POSIX `fcntl.flock`. The existing
  `RddfSessionCoordinator._with_file_lock` is POSIX-only (per ADR-0017
  consequences); Windows remains out of scope.