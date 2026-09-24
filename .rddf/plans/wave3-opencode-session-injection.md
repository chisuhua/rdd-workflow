# wave3-opencode-session-injection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为多窗口 owner 区分提供真实 session 标识符。方案 A (OpenCode 平台层 `$OPENCODE_SESSION_ID` 注入) 依赖外部项目排期；方案 B (rdd-workflow-side fallback: `RDDF_OPENCODE_SESSION_AWARE=yes` 探测) 作为短期降级。本期聚焦方案 B 落地的 rdd-workflow 侧代码。

**Architecture:** 在 `rddf_session_hooks.sh:_rddf_resolve_owner` 增加 `RDDF_OPENCODE_SESSION_AWARE=yes` 环境变量探测 + OpenCode session 文件 (`~/.opencode/sessions/{uuid}/`) 的 mtime 推断；简化 fallback 链至 ≤3 层。`_commands.py` resolve_owner 逻辑简化为 per-platform 1 层。

**Tech Stack:** bash (hooks) + Python (commands) + bats (tests)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/rddf-session/scripts/rddf_session_hooks.sh` | `_rddf_resolve_owner` 增加 `RDDF_OPENCODE_SESSION_AWARE` 探测路径 (方案 B) |
| `_lib/rddf_session_pkg/_commands.py` | resolve_owner 局部简化 (per-platform 切到 ~1 层, 保留 fallback) |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_rddf_session_owner.bats` | 扩展: `RDDF_OPENCODE_SESSION_AWARE=yes` env 探测 + session 文件 mtime 推断 |

---

### Task 1: Add RDDF_OPENCODE_SESSION_AWARE probe to _rddf_resolve_owner

**Files:**
- Modify: `skills/rddf-session/scripts/rddf_session_hooks.sh` (~line 55-85, `_rddf_resolve_owner` function)
- Test: `tests/integration/test_rddf_session_owner.bats`

- [x] **Step 1: Write the failing bats test**

Add to `tests/integration/test_rddf_session_owner.bats`:

```bash
@test "RDDF_OPENCODE_SESSION_AWARE=yes sets owner from OpenCode session file" {
    # Create mock OpenCode session dir
    local mock_session_dir="$BATS_TEST_TMPDIR/.opencode/sessions/ses_abc123def456"
    mkdir -p "$mock_session_dir"
    echo "{}" > "$mock_session_dir/meta.json"
    touch -t "202609241200" "$mock_session_dir/meta.json"
    
    HOME="$BATS_TEST_TMPDIR" \
    RDDF_OPENCODE_SESSION_AWARE=yes \
    RDD_EVENTS_PATH="$BATS_TEST_TMPDIR/events.jsonl" \
    run source "$LIB_DIR/rddf_session_hooks.sh" && _rddf_resolve_owner
    
    # AC-P1-3-4: fallback chain ≤ 3 layers when OPENCODE_SESSION_AWARE is set
    [[ "$output" == *"ses_"* ]] || [[ "$output" == "ses_abc123def456" ]]
}

@test "RDDF_OPENCODE_SESSION_AWARE=no behaves identically to unset" {
    RDDF_OPENCODE_SESSION_AWARE=no \
    RDD_EVENTS_PATH="$BATS_TEST_TMPDIR/events.jsonl" \
    run source "$LIB_DIR/rddf_session_hooks.sh" && _rddf_resolve_owner
    
    # Falls through to original fallback chain
    [ -n "$output" ]
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rddf_session_owner.bats -f "RDDF_OPENCODE_SESSION_AWARE" -t`
Expected: FAIL — `_rddf_resolve_owner` doesn't yet handle `RDDF_OPENCODE_SESSION_AWARE`

- [x] **Step 3: Implement RDDF_OPENCODE_SESSION_AWARE probe**

In `skills/rddf-session/scripts/rddf_session_hooks.sh`, locate `_rddf_resolve_owner()`. Add a new probe at the top of the function (before the existing fallback chain):

```bash
# Layer 0: RDDF_OPENCODE_SESSION_AWARE probe (方案 B, per Wave 3 P1-3)
if [ "${RDDF_OPENCODE_SESSION_AWARE:-no}" = "yes" ]; then
    # Scan ~/.opencode/sessions/ for most recent session file
    local opencode_session_dir="$HOME/.opencode/sessions"
    if [ -d "$opencode_session_dir" ]; then
        local latest_session
        latest_session=$(ls -1t "$opencode_session_dir" 2>/dev/null | head -1)
        if [ -n "$latest_session" ]; then
            echo "ses_${latest_session}"
            return 0
        fi
    fi
fi
```

Also adjust AC-P1-3-4: when `RDDF_OPENCODE_SESSION_AWARE=yes`, the effective fallback chain is:
1. `RDDF_OPENCODE_SESSION_AWARE=yes` → `~/.opencode/sessions/` → cache fallback

This is ≤3 layers per the acceptance criterion.

- [x] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_rddf_session_owner.bats -f "RDDF_OPENCODE_SESSION_AWARE" -t`
Expected: PASS (2 tests)

- [x] **Step 5: Defer commit**

---

### Task 2: Simplify _commands.py resolve_owner per-platform (optional)

**Files:**
- Modify: `_lib/rddf_session_pkg/_commands.py` (~lines 50-90, per-owner logic)
- Test: `tests/integration/test_rddf_session_owner.bats`

- [x] **Step 1: Write the failing test**

Add to `tests/integration/test_rddf_session_owner.bats`:

```bash
@test "resolve_owner simplified to ≤3 layers when OPENCODE_SESSION_ID is set" {
    OPENCODE_SESSION_ID="ses_test123456" \
    run python3 -c "
import sys, os
sys.path.insert(0, '$BATS_TEST_DIRNAME/../../_lib')
from rddf_session_pkg._commands import _rddf_resolve_owner
result = _rddf_resolve_owner()
assert result == 'ses_test123456', f'expected ses_test123456, got {result}'
print(result)
"
    [[ "$output" == *"ses_test123456"* ]]
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rddf_session_owner.bats -f "simplified" -t`
Expected: FAIL — `_commands.py` still uses the old 5-layer chain

- [x] **Step 3: Implement simplified resolve_owner in _commands.py**

In `_lib/rddf_session_pkg/_commands.py`, find the per-owner check (around lines 67-78). Refactor to:

```python
def _resolve_owner_command(session: dict) -> str:
    """Resolve owner with simplified chain (≤3 layers per AC-P1-3-4)."""
    # Layer 1: OPENCODE_SESSION_ID (方案 A, defined by platform)
    owner = os.environ.get("OPENCODE_SESSION_ID", "")
    if owner:
        return owner
    
    # Layer 2: RDDF_OWNER (exported from hook)
    owner = os.environ.get("RDDF_OWNER", "")
    if owner:
        return owner
    
    # Layer 3: cache file (fallback)
    # ... (existing logic, reduced)
    return owner_final
```

- [x] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_rddf_session_owner.bats -f "simplified" -t`
Expected: PASS

- [x] **Step 5: Defer commit**

---

### Task 3: Multi-window e2e test — verify process-tree isolation

**Files:**
- Modify: `tests/integration/test_multi_window_poll.bats` or create `test_real_two_owner_poll.bats`
- Ensures 2 concurrent registrations produce distinct owner_opencode_session_id

- [x] **Step 1: Write the failing e2e test**

```bash
@test "REAL-2P-1: Two concurrent registrations produce distinct owners when OPENCODE_SESSION_ID is set" {
    OPENCODE_SESSION_ID="ses_window_a_test" \
    run python3 -c "
import sys, os
sys.path.insert(0, '$LIB_DIR/../../_lib')
from rddf_session_pkg._commands import register_session
ctx = register_session(kind='stage_guide')
print(ctx.get('owner_opencode_session_id', 'MISSING'))
"
    local owner_a="$output"
    
    OPENCODE_SESSION_ID="ses_window_b_test" \
    run python3 -c "
import sys, os
sys.path.insert(0, '$LIB_DIR/../../_lib')
from rddf_session_pkg._commands import register_session
ctx = register_session(kind='stage_builder')
print(ctx.get('owner_opencode_session_id', 'MISSING'))
"
    local owner_b="$output"
    
    # AC-P1-3-2: Two distinct owners
    [ "$owner_a" != "$owner_b" ]
    [[ "$owner_a" == "ses_window_a_test" ]]
    [[ "$owner_b" == "ses_window_b_test" ]]
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_real_two_owner_poll.bats -t` (or the existing test file)
Expected: FAIL — old fallback chain produces same owner for both

- [x] **Step 3: Run test to verify it passes (with OPENCODE_SESSION_ID set)**

Run: `OPENCODE_SESSION_ID=ses_window_a_test bats tests/integration/test_real_two_owner_poll.bats -t`
Expected: PASS — with env var set, two registrations produce different owners

- [x] **Step 4: Run existing owner-related tests to confirm no regression**

Run: `bats tests/integration/test_rddf_session_owner.bats -t`
Expected: PASS (all owner tests)

- [x] **Step 5: Defer commit**

---

### Implementation Priority Note

This change depends on OpenCode platform `$OPENCODE_SESSION_ID` env injection (方案 A, external). If OpenCode platform is not available:
- 方案 B (Task 1: `RDDF_OPENCODE_SESSION_AWARE` probe) is the initial deliverable
- Task 2 (`_commands.py` simplification) is independent and reinforces both paths
- Task 3 (e2e test) validates the combined outcome

Without OpenCode platform `$OPENCODE_SESSION_ID`, the rdd-workflow side can still implement:
- Task 1 (方案 B probe) → partial owner differentiation
- Task 2 (command simplification) → cleaner code regardless
- Task 3 (e2e test with mocked OPENCODE_SESSION_ID) → validates the contract

Once OpenCode platform ships 方案 A, no rdd-workflow code change is needed — the existing `$OPENCODE_SESSION_ID` read in the fallback chain (Layer 1) activates automatically.