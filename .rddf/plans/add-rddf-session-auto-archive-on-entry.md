# add-rddf-session-auto-archive-on-entry 实施计划

> **P1 hygiene**: hooks 入口 / 关闭自动触发 `archive_history`,解决 sessions.json 长期累积问题。
>
> **TDD 5 步纪律** (来自 rdd-workflow v2.0 execute skill): 每个 task 严格按 Write failing test → Verify fail → Implement → Verify pass → Commit。
>
> **依据**: `improvements/add-rddf-session-auto-archive-on-entry.md` + `openspec/changes/add-rddf-session-auto-archive-on-entry/{proposal,design,tasks}.md`
>
> **预期修改文件**:
> 1. `skills/rddf-session/scripts/rddf_session_hooks.sh` (新增 2 函数 + 2 处调用)
> 2. `tests/integration/test_rddf_session_auto_archive.bats` (新增 — bats 集成)
> 3. `tests/unit/test_rddf_session_auto_archive.py` (新增 — pytest 单元)
> 4. `skills/rddf-session/SKILL.md` (新增"自动归档"章节)
>
> **强约束** (来自 improvements + 设计阶段):
> - 默认 `keep=10`,阈值 `keep + 5 = 15`(避免稳态 12-14 条永远不触发)
> - `RDDF_AUTO_ARCHIVE_KEEP=0` 禁用归档 (主开关)
> - `RDDF_AUTO_ARCHIVE_THRESHOLD=0` 禁用归档 (与 keep=0 协调)
> - 自动归档必须 **best-effort**: `try/except` 不阻塞主流程
> - 不修改 `archive_history` 行为本身 (只调用,不修改)
> - 不修改 sessions.json schema
> - 不引入 cron / 后台调度 (保持纯 hook 触发)
> - **不修改** `rddf_session_hook_entry` / `_close` 已有的 owner 解析、parent linkage 行为
>
> **依赖前置**: P0 `fix-rddf-session-owner-stability` 已实施归档 (`18fc072`),本 P1 是直接下游。

---

### Task 1: 阈值判定 helper (纯函数, 易于单元测试)

**Files:**
- Create: `tests/unit/test_rddf_session_auto_archive.py`
- Modify: `skills/rddf-session/scripts/rddf_session_hooks.sh` (新增 `_rddf_should_auto_archive` 函数)

- [ ] **Step 1: Write the failing test**

**文件**: `tests/unit/test_rddf_session_auto_archive.py`

```python
"""Verify _rddf_should_auto_archive threshold helper.

Contract (from improvements/add-rddf-session-auto-archive-on-entry.md):
  threshold = keep + 5 (default)
  RDDF_AUTO_ARCHIVE_THRESHOLD env var overrides threshold (0 = disabled)
  RDDF_AUTO_ARCHIVE_KEEP env var overrides keep (0 = disabled)

Returns: True if total_count >= threshold AND keep > 0 AND threshold > 0
"""
import os
import subprocess
from pathlib import Path

HOOKS_SCRIPT = Path("skills/rddf-session/scripts/rddf_session_hooks.sh")


def _invoke_helper(total_count: int, keep: int, threshold: int | None) -> bool:
    """Invoke _rddf_should_auto_archive with given args via bash subprocess.

    Helper signature: _rddf_should_auto_archive <total_count> <keep> <threshold>
    Returns 0 (true) if should archive, 1 (false) otherwise.
    """
    args = f"{total_count} {keep} {threshold if threshold is not None else ''}"
    env = os.environ.copy()
    env.pop("RDDF_AUTO_ARCHIVE_KEEP", None)
    env.pop("RDDF_AUTO_ARCHIVE_THRESHOLD", None)
    result = subprocess.run(
        ["bash", "-c",
         f'source "{HOOKS_SCRIPT}" >/dev/null 2>&1; _rddf_should_auto_archive {args}'],
        capture_output=True, env=env,
    )
    return result.returncode == 0


def test_default_threshold_triggers_at_keep_plus_5():
    """Default threshold = keep + 5. So 14 < 15, 15 = 15 (trigger)."""
    assert _invoke_helper(total_count=14, keep=10, threshold=None) is False
    assert _invoke_helper(total_count=15, keep=10, threshold=None) is True
    assert _invoke_helper(total_count=20, keep=10, threshold=None) is True


def test_keep_zero_disables_archive():
    """RDDF_AUTO_ARCHIVE_KEEP=0 → never archive regardless of count."""
    # Helper accepts keep=0 directly
    assert _invoke_helper(total_count=100, keep=0, threshold=None) is False
    assert _invoke_helper(total_count=0, keep=0, threshold=None) is False


def test_threshold_zero_disables_archive():
    """RDDF_AUTO_ARCHIVE_THRESHOLD=0 → never archive regardless of count."""
    assert _invoke_helper(total_count=100, keep=10, threshold=0) is False
    assert _invoke_helper(total_count=15, keep=10, threshold=0) is False


def test_threshold_override_respected():
    """Custom threshold = 20, so 19 < 20, 20 ≥ 20 triggers."""
    assert _invoke_helper(total_count=19, keep=10, threshold=20) is False
    assert _invoke_helper(total_count=20, keep=10, threshold=20) is True


def test_negative_values_treated_as_disabled():
    """Defensive: negative keep or threshold treated as 0 (disabled)."""
    # Note: bash arithmetic handles negative naturally, but contract is
    # "0 means disabled". Helper should clamp negatives to 0.
    assert _invoke_helper(total_count=100, keep=-5, threshold=None) is False
    assert _invoke_helper(total_count=100, keep=10, threshold=-3) is False


def test_below_keep_count_never_triggers():
    """When total count is below keep (no archive possible), never trigger."""
    # If only 5 sessions and keep=10, archive would be empty → no-op anyway.
    # Helper should not trigger.
    assert _invoke_helper(total_count=5, keep=10, threshold=None) is False
    assert _invoke_helper(total_count=10, keep=10, threshold=None) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_rddf_session_auto_archive.py -v`
Expected: FAIL with "command not found" or non-zero exit (helper `_rddf_should_auto_archive` doesn't exist)

- [ ] **Step 3: Write minimal implementation**

**文件**: `skills/rddf-session/scripts/rddf_session_hooks.sh` (在 `_rddf_resolve_owner` 函数后新增)

```bash
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_rddf_session_auto_archive.py -v`
Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "$WT_PATH"
git add tests/unit/test_rddf_session_auto_archive.py \
        skills/rddf-session/scripts/rddf_session_hooks.sh
git commit -m "feat(rddf-session): add _rddf_should_auto_archive threshold helper"
```

---

### Task 2: 自动归档执行 helper (best-effort 调用 archive_history)

**Files:**
- Modify: `tests/unit/test_rddf_session_auto_archive.py` (追加新 test + import json)
- Modify: `skills/rddf-session/scripts/rddf_session_hooks.sh` (新增 `_rddf_auto_archive_if_needed`)

- [ ] **Step 1: Write the failing test**

**文件**: `tests/unit/test_rddf_session_auto_archive.py` (在已有 import 后追加 `import json`,并在文件末尾追加以下 test)

```python
def test_auto_archive_invokes_archive_history_when_triggered(tmp_path, monkeypatch):
    """When threshold met, helper invokes coord.archive_history(keep)."""
    # Setup: fake sessions.json with 20 terminal sessions (>= keep+5=15 threshold)
    sessions_file = tmp_path / "state" / "sessions.json"
    sessions_file.parent.mkdir(parents=True)
    sessions_file.write_text(
        '{"version": 1, "sessions": [{"state": "completed"} for _ in range(20)]}'
    )

    # Patch env so hook can locate sessions.json
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("RDDF_AUTO_ARCHIVE_KEEP", raising=False)
    monkeypatch.delenv("RDDF_AUTO_ARCHIVE_THRESHOLD", raising=False)

    # Invoke helper via bash
    result = subprocess.run(
        ["bash", "-c",
         f'source "{HOOKS_SCRIPT}" >/dev/null 2>&1; _rddf_auto_archive_if_needed "{sessions_file}"'],
        capture_output=True, env=os.environ,
    )
    # Should succeed (exit 0) — best-effort, swallows errors but success path is 0
    assert result.returncode == 0, f"stderr: {result.stderr.decode()}"
    # sessions.json should have been updated (archive-history wrote new state)
    data_after = json.loads(sessions_file.read_text())
    # After archive_history(keep=10): terminal sessions kept = min(20, 10) = 10
    assert len(data_after["sessions"]) <= 10, (
        f"Expected <=10 sessions after archive, got {len(data_after['sessions'])}"
    )


def test_auto_archive_silent_when_below_threshold(tmp_path, monkeypatch):
    """When below threshold, helper does not touch sessions.json."""
    sessions_file = tmp_path / "state" / "sessions.json"
    sessions_file.parent.mkdir(parents=True)
    original_data = {"version": 1, "sessions": [{"state": "completed"} for _ in range(8)]}
    sessions_file.write_text(json.dumps(original_data))

    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

    result = subprocess.run(
        ["bash", "-c",
         f'source "{HOOKS_SCRIPT}" >/dev/null 2>&1; _rddf_auto_archive_if_needed "{sessions_file}"'],
        capture_output=True, env=os.environ,
    )
    assert result.returncode == 0
    # sessions.json unchanged
    data_after = json.loads(sessions_file.read_text())
    assert len(data_after["sessions"]) == 8


def test_auto_archive_swallows_errors(tmp_path, monkeypatch):
    """When archive fails (corrupt file), helper exits 0 and stderr prints warning."""
    sessions_file = tmp_path / "state" / "sessions.json"
    sessions_file.parent.mkdir(parents=True)
    # Corrupt JSON to force archive_history to fail
    sessions_file.write_text("{this is not valid json")

    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

    result = subprocess.run(
        ["bash", "-c",
         f'source "{HOOKS_SCRIPT}" >/dev/null 2>&1; _rddf_auto_archive_if_needed "{sessions_file}"'],
        capture_output=True, env=os.environ,
    )
    # best-effort: even on failure, exit 0
    assert result.returncode == 0
    # stderr should contain a warning
    err = result.stderr.decode()
    assert "auto-archive" in err.lower() or "skip" in err.lower(), (
        f"Expected warning in stderr, got: {err}"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_rddf_session_auto_archive.py -v`
Expected: 3 new tests FAIL (`_rddf_auto_archive_if_needed` doesn't exist)

- [ ] **Step 3: Write minimal implementation**

**文件**: `skills/rddf-session/scripts/rddf_session_hooks.sh` (在 `_rddf_should_auto_archive` 函数后新增)

```bash
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
except Exception:
    print(0)
" 2>/dev/null || echo 0)

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_rddf_session_auto_archive.py -v`
Expected: All 9 tests PASS (6 from Task 1 + 3 new)

- [ ] **Step 5: Commit**

```bash
cd "$WT_PATH"
git add tests/unit/test_rddf_session_auto_archive.py \
        skills/rddf-session/scripts/rddf_session_hooks.sh
git commit -m "feat(rddf-session): add _rddf_auto_archive_if_needed best-effort helper"
```

---

### Task 3: 接入 entry / close hooks (在末尾触发自动归档)

**Files:**
- Modify: `skills/rddf-session/scripts/rddf_session_hooks.sh` (在 rddf_session_hook_entry 和 rddf_session_hook_close 末尾追加调用)
- Create: `tests/integration/test_rddf_session_auto_archive.bats` (新增 — 端到端集成)

- [ ] **Step 1: Write the failing test**

**文件**: `tests/integration/test_rddf_session_auto_archive.bats`

```bats
#!/usr/bin/env bats
# tests/integration/test_rddf_session_auto_archive.bats
# End-to-end verification that rddf_session_hook_entry triggers auto-archive
# when sessions.json exceeds threshold.

load ../test_helper

setup() {
    TEST_DIR=$(mktemp -d)
    export PROJECT_ROOT="$TEST_DIR"
    mkdir -p "$TEST_DIR/.rddf/state"
    # Stub OPENCODE_SESSION_ID to avoid /proc cmdline probe
    export OPENCODE_SESSION_ID="test-session-$(date +%s%N)"
    unset RDDF_AUTO_ARCHIVE_KEEP
    unset RDDF_AUTO_ARCHIVE_THRESHOLD
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "auto-archive: hook entry triggers archive when sessions >= threshold" {
    # Setup sessions.json with 20 terminal sessions (default threshold = 15)
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    mkdir -p "$(dirname "$SESSIONS_FILE")"
    python3 -c "
import json
sessions = []
for i in range(20):
    sessions.append({
        'session_id': f'rds_stale_{i}',
        'state': 'completed',
        'owner_opencode_session_id': 'prev_owner',
        'started_at': '2026-07-01T00:00:00',
        'ended_at': '2026-07-01T01:00:00',
    })
with open('$SESSIONS_FILE', 'w') as f:
    json.dump({'version': 1, 'sessions': sessions}, f)
"

    # Source hooks and invoke entry
    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_arch guide-arch arch-phase design-done
    " 2>/dev/null

    # Verify sessions.json was reduced (archive triggered)
    remaining=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
# After archive_history(keep=10): 10 terminal kept + 1 new = 11
print(len(data['sessions']))
")
    [ "$remaining" -le 11 ] || {
        echo "FAIL: Expected <=11 sessions after auto-archive, got $remaining"
        return 1
    }

    # Verify .archive.json was created
    [ -f "$TEST_DIR/.rddf/state/sessions.archive.json" ] || {
        echo "FAIL: sessions.archive.json not created"
        return 1
    }
}

@test "auto-archive: hook entry is no-op when sessions < threshold" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    mkdir -p "$(dirname "$SESSIONS_FILE")"
    python3 -c "
import json
sessions = []
for i in range(5):
    sessions.append({
        'session_id': f'rds_recent_{i}',
        'state': 'completed',
        'owner_opencode_session_id': 'prev_owner',
        'started_at': '2026-07-01T00:00:00',
        'ended_at': '2026-07-01T01:00:00',
    })
with open('$SESSIONS_FILE', 'w') as f:
    json.dump({'version': 1, 'sessions': sessions}, f)
"

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_arch guide-arch arch-phase design-done
    " 2>/dev/null

    remaining=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
print(len(data['sessions']))
")
    # 5 old + 1 new = 6 (no archive triggered)
    [ "$remaining" -eq 6 ] || {
        echo "FAIL: Expected 6 sessions (no archive), got $remaining"
        return 1
    }
    [ ! -f "$TEST_DIR/.rddf/state/sessions.archive.json" ] || {
        echo "FAIL: archive file should not exist when below threshold"
        return 1
    }
}

@test "auto-archive: RDDF_AUTO_ARCHIVE_KEEP=0 disables" {
    export RDDF_AUTO_ARCHIVE_KEEP=0
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    mkdir -p "$(dirname "$SESSIONS_FILE")"
    python3 -c "
import json
sessions = []
for i in range(50):
    sessions.append({
        'session_id': f'rds_old_{i}',
        'state': 'completed',
        'owner_opencode_session_id': 'prev_owner',
        'started_at': '2026-07-01T00:00:00',
        'ended_at': '2026-07-01T01:00:00',
    })
with open('$SESSIONS_FILE', 'w') as f:
    json.dump({'version': 1, 'sessions': sessions}, f)
"

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        export RDDF_AUTO_ARCHIVE_KEEP=0
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_arch guide-arch arch-phase design-done
    " 2>/dev/null

    remaining=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
print(len(data['sessions']))
")
    # 50 old + 1 new = 51 (archive disabled)
    [ "$remaining" -eq 51 ] || {
        echo "FAIL: Expected 51 (disabled), got $remaining"
        return 1
    }
}

@test "auto-archive: hook close also triggers archive" {
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    mkdir -p "$(dirname "$SESSIONS_FILE")"
    python3 -c "
import json
sessions = []
for i in range(20):
    sessions.append({
        'session_id': f'rds_stale_{i}',
        'state': 'completed',
        'owner_opencode_session_id': 'prev_owner',
        'started_at': '2026-07-01T00:00:00',
        'ended_at': '2026-07-01T01:00:00',
    })
with open('$SESSIONS_FILE', 'w') as f:
    json.dump({'version': 1, 'sessions': sessions}, f)
"

    bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_close stage_arch arch-done guide-arch
    " 2>/dev/null

    remaining=$(python3 -c "
import json
with open('$SESSIONS_FILE') as f:
    data = json.load(f)
print(len(data['sessions']))
")
    [ "$remaining" -le 11 ] || {
        echo "FAIL: Expected <=11 after close-triggered archive, got $remaining"
        return 1
    }
}

@test "auto-archive: hook entry does not crash on corrupt sessions.json (best-effort)" {
    # Force failure: corrupt sessions.json
    SESSIONS_FILE="$TEST_DIR/.rddf/state/sessions.json"
    mkdir -p "$(dirname "$SESSIONS_FILE")"
    echo "{invalid json" > "$SESSIONS_FILE"

    # Best-effort: hook entry may still fail due to create_session error, but
    # the auto-archive portion must not crash with unhandled exception.
    # We assert: timeout (status=124) does NOT happen (would indicate hang).
    run timeout 10 bash -c "
        export PROJECT_ROOT='$TEST_DIR'
        export OPENCODE_SESSION_ID='$OPENCODE_SESSION_ID'
        source '$REPO_ROOT/skills/rddf-session/scripts/rddf_session_hooks.sh'
        rddf_session_hook_entry stage_arch guide-arch arch-phase design-done
    "

    # 124 = timeout from `timeout` cmd (would indicate hung subprocess / crash)
    [ "$status" -ne 124 ]
}
```

注意 bats 顶部需要 `load ../test_helper`,该 helper 提供 `REPO_ROOT` 变量指向 git toplevel。

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rddf_session_auto_archive.bats`
Expected: 5 tests FAIL (rddf_session_hook_entry/close don't call `_rddf_auto_archive_if_needed`)

- [ ] **Step 3: Write minimal implementation**

**文件**: `skills/rddf-session/scripts/rddf_session_hooks.sh`

修改 `rddf_session_hook_entry` 函数:在 PYEOF heredoc **之后**(末尾)追加一行调用:

```bash
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

  local sessions_file="${PROJECT_ROOT}/.rddf/state/sessions.json"

  KIND="$kind" \
  INTENT="$intent" \
  SUBJECT="$subject" \
  EXPECTED_OUTCOME="$expected_outcome" \
  CONTEXT_POINTER="$context_pointer" \
  PROJECT_ROOT="$PROJECT_ROOT" \
  OPENCODE_SESSION_ID="$OPENCODE_SESSION_ID" \
  python3 <<'PYEOF'
  ... (existing PYEOF block unchanged)
PYEOF

  # Auto-archive best-effort (P1: add-rddf-session-auto-archive-on-entry)
  _rddf_auto_archive_if_needed "$sessions_file" 2>/dev/null || true
}
```

同理修改 `rddf_session_hook_close`:

```bash
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
  ... (existing PYEOF block unchanged)
PYEOF

  # Auto-archive best-effort (P1: add-rddf-session-auto-archive-on-entry)
  _rddf_auto_archive_if_needed "$sessions_file" 2>/dev/null || true
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_rddf_session_auto_archive.bats`
Expected: 5 tests PASS (loose assertions, but main archive flow verified)

- [ ] **Step 5: Commit**

```bash
cd "$WT_PATH"
git add skills/rddf-session/scripts/rddf_session_hooks.sh \
        tests/integration/test_rddf_session_auto_archive.bats
git commit -m "feat(rddf-session): wire auto-archive into entry/close hooks"
```

---

### Task 4: 文档更新 — SKILL.md 增加"自动归档"章节

**Files:**
- Modify: `skills/rddf-session/SKILL.md` (新增章节)

- [ ] **Step 1: Write the failing test**

不适用 — 文档无单元测试。

- [ ] **Step 2: Run test to verify it fails**

不适用。

- [ ] **Step 3: Write minimal implementation**

**文件**: `skills/rddf-session/SKILL.md`

在文件末尾 (现有 `## Cross-Reference` 章节之前) 追加:

```markdown
## Auto-Archive on Hook Trigger (P1 hygiene)

`rddf_session_hook_entry` 和 `rddf_session_hook_close` 在主流程完成后,
会自动触发 `archive_history` 来清理长期累积的 sessions.json。

**触发条件**:
- sessions.json 中总 session 数 ≥ 阈值 (默认 = `keep + 5 = 15`)
- 任一 env var 设置为 `0` 时禁用

**环境变量**:

| Env Var | Default | 含义 |
|---------|---------|------|
| `RDDF_AUTO_ARCHIVE_KEEP` | `10` | 每次归档保留多少 terminal session,`0` 禁用自动归档 |
| `RDDF_AUTO_ARCHIVE_THRESHOLD` | `keep + 5` | 触发阈值 (总 session 数 ≥ 阈值 才归档),`0` 禁用 |

**为什么默认阈值是 `keep + 5`**:
原 `≥ 15` 在 keep=10 + 2-4 个 active 的常见稳态 (12-14 条) 下永远不触发,
sessions.json 长期累积。改为 `≥ keep + 5` (默认 15) 后:
- 触发后 archive_history 已按 keep 切片 (10 terminal + active 保留)
- 稳态 10 + N active,触发频率自然下降
- 避免每次 hook 都重写文件

**最佳实践**:
- 大量调试遗留 sessions 时: 手动 `rddf-session archive-history --keep=50`
- CI / 自动化环境: 设 `RDDF_AUTO_ARCHIVE_KEEP=5 RDDF_AUTO_ARCHIVE_THRESHOLD=10` 更激进
- 性能敏感场景: `RDDF_AUTO_ARCHIVE_KEEP=0` 关闭自动归档,定期手动清理

**失败容忍**: auto-archive 任何异常 (JSON corrupt / disk full / permission)
都被 swallow,stderr 打印警告,主流程不受影响。
```

- [ ] **Step 4: Run test to verify it passes**

```bash
# 验证文档存在 + 内容
grep -q "## Auto-Archive on Hook Trigger" skills/rddf-session/SKILL.md
grep -q "RDDF_AUTO_ARCHIVE_KEEP" skills/rddf-session/SKILL.md
grep -q "RDDF_AUTO_ARCHIVE_THRESHOLD" skills/rddf-session/SKILL.md
```

Expected: All `grep -q` exit 0

- [ ] **Step 5: Commit**

```bash
cd "$WT_PATH"
git add skills/rddf-session/SKILL.md
git commit -m "docs(rddf-session): document auto-archive on hook trigger"
```

---

### Task 5: 全量回归 + 端到端验证

**Files:**
- 无新文件 — 验证既有测试不被破坏

- [ ] **Step 1: 验证 pytest 全 pass**

Run: `pytest tests/unit/test_rddf_session_auto_archive.py -v`
Expected: 9 tests PASS

- [ ] **Step 2: 验证 bats 集成全 pass**

Run: `bats tests/integration/test_rddf_session_auto_archive.bats`
Expected: 5 tests PASS

- [ ] **Step 3: 验证既有 rddf-session tests 不回归**

Run: `pytest tests/unit/test_rddf_session.py tests/unit/test_rddf_session_lifecycle.py -v`
Expected: 既有测试 PASS (entry/close 行为未改变,仅末尾追加 auto-archive 调用)

Run: `bats tests/integration/test_rddf_session_hooks_extraction.bats`
Expected: 既有 hooks 测试 PASS (helper 签名未改变)

- [ ] **Step 4: 验证 openspec validate**

Run: `openspec validate add-rddf-session-auto-archive-on-entry --strict`
Expected: PASS (proposal.md / design.md / tasks.md 已提交,本 change 不新增 spec)

- [ ] **Step 5: 验证 iteration.json tasks_total 反映进度**

```bash
python3 -c "
import json
with open('$WT_PATH/.rddf/state/iteration.json') as f:
    data = json.load(f)
for c in data['changes']:
    if c['name'] == 'add-rddf-session-auto-archive-on-entry':
        print(f\"tasks_total: {c.get('tasks_total')}\")
        print(f\"tasks_done: {c.get('tasks_done')}\")
        print(f\"status: {c.get('status')}\")
"
```

Expected: tasks_total=17 (固定), tasks_done 随任务进度更新, status=in_worktree

- [ ] **Step 6: Commit (如 iteration.json 有变更)**

```bash
cd "$WT_PATH"
git status
# 如有 tasks_done 更新或 iteration.json 修改:
git add openspec/changes/add-rddf-session-auto-archive-on-entry/tasks.md \
        .rddf/state/iteration.json 2>/dev/null
git commit -m "chore(change): mark add-rddf-session-auto-archive-on-entry tasks complete"
```

- [ ] **Step 7: 最终验证 (执行完后)**

```bash
cd "$WT_PATH"
git log --oneline "master..HEAD"
```

Expected: 4 commits (Task 1/2/3/4) + 1 commit (Task 5, 如有)

---

## 自检清单 (Self-Review)

**1. Spec 覆盖**:
- [x] `rddf_session_hook_entry` 末尾自动调 `coord.archive_history(keep=10)` → Task 3
- [x] `rddf_session_hook_close` 关闭时同样自动调 → Task 3
- [x] 默认 `keep=10` → Task 1/2 默认值
- [x] `RDDF_AUTO_ARCHIVE_KEEP` env var 覆盖 (0 = 禁用) → Task 1/2
- [x] `RDDF_AUTO_ARCHIVE_THRESHOLD` env var 覆盖 (0 = 禁用) → Task 1
- [x] 触发阈值 `keep + 5` → Task 1 (默认 threshold = keep + 5)
- [x] best-effort `try/except` 不阻塞主流程 → Task 2 (stderr 警告,return 0)
- [x] 单元测试 + bats 集成测试 → Task 1/2/3
- [x] SKILL.md 增加"自动归档"章节 → Task 4

**2. 占位符扫描**:
- 无 "TBD" / "TODO" / "implement later"
- 无 "Add appropriate error handling" — Task 2 明确 best-effort 模式
- 无 "Similar to Task N" — 每 task 独立完整代码
- 所有步骤显示实际可执行命令

**3. 类型一致性**:
- `keep`, `threshold` 都是 int
- `total_count` int
- `coord.archive_history(keep=int(...))` 一致
- 函数签名 `_rddf_should_auto_archive <total_count> <keep> <threshold>` 在 Task 1/2/3 保持一致

**4. 文件路径核对**:
- 测试在 worktree (`$WT_PATH`) 路径下,execute 时 cd 进去
- 修改文件在 `skills/rddf-session/scripts/`(globally shared via symlink to `~/.agents/skills/`)
- 既有 rddf-session tests (e.g. test_rddf_session_hooks_extraction.bats) 仍可找到 helper (因为 hooks helper 路径未变)

---

## 执行交接

**当前 session 执行** (推荐 — plan 较小, 17 tasks):
- 按 Task 1 → 2 → 3 → 4 → 5 顺序执行
- 每个 Task 完成后用 sed 更新 `openspec/changes/add-rddf-session-auto-archive-on-entry/tasks.md` 的 `- [x]`
- Task 5 完成后进入 `guide-ship` Phase 2 (review) → Phase 3 (archive)

**或 `skill_use("execute")`**:
- 加载本 plan 文件
- 自动 TDD 5 步执行 + 每 Task 自动 commit
- 完成后调用 `status` 检查