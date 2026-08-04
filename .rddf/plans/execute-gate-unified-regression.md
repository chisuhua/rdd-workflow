# execute-gate-unified-regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the execute-phase full-regression gate so every worktree runs the same recursive bats regression, using the existing `report_regression.sh` baseline comparison when `tests/KNOWN_FAILURES.txt` is present and falling back to plain `bats tests/ --recursive` when it is not.

**Architecture:** Extract a small bash helper (`skills/execute/scripts/run_regression_gate.sh`) that decides between the baseline-aware report and the plain recursive bats run, then wire it into `skills/execute/SKILL.md` Step 5 in place of the current ctest-only gate. Lock both the helper behavior and the skill wiring with bats tests; preserve the `SKIP_REGRESSION=1` escape hatch and do not reimplement or modify `report_regression.sh`.

**Tech Stack:** bash, bats-core, existing `tests/scripts/report_regression.sh`, `tests/KNOWN_FAILURES.txt`.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/execute/scripts/run_regression_gate.sh` | New helper: exports `run_regression_gate`; honors `SKIP_REGRESSION=1`; chooses `report_regression.sh` when baseline exists, otherwise `bats tests/ --recursive`. |
| `skills/execute/SKILL.md` | Replace the ctest-based Step 5 block with `source` + `run_regression_gate` invocation; keep the failure message and `SKIP_REGRESSION` escape hatch. |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_execute_regression_gate.bats` | Regression contract for the new gate: baseline-present path, baseline-absent fallback path, and `SKIP_REGRESSION=1` skip path. |
| `tests/integration/test_execute_skill.bats` | Add one structural test asserting `skills/execute/SKILL.md` references the `run_regression_gate` helper. |

---

### Task 1: Create the unified regression gate helper

**Files:**
- Create: `skills/execute/scripts/run_regression_gate.sh`
- Create: `tests/integration/test_execute_regression_gate.bats`

- [x] **Step 1: Write the failing test**

Create `tests/integration/test_execute_regression_gate.bats` with the following content. The test references `skills/execute/scripts/run_regression_gate.sh`, which does not exist yet, so the run will fail with "No such file or directory".

```bash
#!/usr/bin/env bats
# tests/integration/test_execute_regression_gate.bats
# Regression contract for the execute phase unified regression gate.

load ../test_helper

GATE="$REPO_ROOT/skills/execute/scripts/run_regression_gate.sh"
BASELINE="$REPO_ROOT/tests/KNOWN_FAILURES.txt"

setup() {
  cd "$REPO_ROOT"
  TEST_BIN="$BATS_TEST_TMPDIR/bin"
  mkdir -p "$TEST_BIN"
  ORIGINAL_BASELINE="$BATS_TEST_TMPDIR/original-known-failures"
  if [ -f "$BASELINE" ]; then
    cp "$BASELINE" "$ORIGINAL_BASELINE"
  else
    : > "$ORIGINAL_BASELINE"
  fi
}

teardown() {
  if [ -s "$ORIGINAL_BASELINE" ]; then
    cp "$ORIGINAL_BASELINE" "$BASELINE"
  else
    rm -f "$BASELINE"
  fi
}

write_fake_bats() {
  local output="$1"
  local exit_status="${2:-0}"
  cat > "$TEST_BIN/bats" <<EOF
#!/usr/bin/env bash
printf '%s\\n' "$output"
printf 'ARGS: %s\\n' "\$*"
exit $exit_status
EOF
  chmod +x "$TEST_BIN/bats"
}

@test "run_regression_gate: baseline present runs report_regression.sh" {
  printf '%s\n' 'known failure: baseline fixture # existing reason' > "$BASELINE"
  write_fake_bats 'not ok 1 known failure: baseline fixture'

  run env PATH="$TEST_BIN:$PATH" bash "$GATE"

  [ "$status" -eq 0 ]
  [[ "$output" == *"baseline 对比"* ]]
  [[ "$output" == *"已知失败"* ]]
  [[ "$output" == *"新增失败: 0"* ]]
}

@test "run_regression_gate: baseline absent falls back to recursive bats" {
  rm -f "$BASELINE"
  write_fake_bats '1..0' 0

  run env PATH="$TEST_BIN:$PATH" bash "$GATE"

  [ "$status" -eq 0 ]
  [[ "$output" == *"bats tests/ --recursive"* ]]
  [[ "$output" == *"ARGS: tests/ --recursive"* ]]
}

@test "run_regression_gate: SKIP_REGRESSION=1 skips both paths" {
  rm -f "$BASELINE"
  write_fake_bats 'this should not run' 1

  run env PATH="$TEST_BIN:$PATH" SKIP_REGRESSION=1 bash "$GATE"

  [ "$status" -eq 0 ]
  [[ "$output" == *"跳过全量回归门"* ]]
  [[ "$output" != *"this should not run"* ]]
}
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
bats tests/integration/test_execute_regression_gate.bats
```

Expected: FAIL with the helper script not found (e.g., `bash: /workspace/project/rdd-workflow/skills/execute/scripts/run_regression_gate.sh: No such file or directory`).

- [x] **Step 3: Write minimal implementation**

Create `skills/execute/scripts/run_regression_gate.sh` with the following content. It defines a single function `run_regression_gate` and does not execute anything at source time.

```bash
#!/usr/bin/env bash
# skills/execute/scripts/run_regression_gate.sh
# Unified full-regression gate for the execute phase.
# Exports: run_regression_gate
# Honors SKIP_REGRESSION=1.
# If tests/KNOWN_FAILURES.txt and tests/scripts/report_regression.sh exist,
# run the baseline-aware report; otherwise fall back to plain recursive bats.

set -u

run_regression_gate() {
  if [ "${SKIP_REGRESSION:-}" = "1" ]; then
    printf '%s\n' '⏭  SKIP_REGRESSION=1，跳过全量回归门'
    return 0
  fi

  local SCRIPT_DIR REPO_ROOT
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
  REPO_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

  if [ -f "$REPO_ROOT/tests/KNOWN_FAILURES.txt" ] && [ -f "$REPO_ROOT/tests/scripts/report_regression.sh" ]; then
    printf '%s\n' '🔍 全量回归门 (baseline 对比)...'
    (cd "$REPO_ROOT" && bash "$REPO_ROOT/tests/scripts/report_regression.sh")
  else
    printf '%s\n' '🔍 全量回归门 (bats tests/ --recursive)...'
    (cd "$REPO_ROOT" && bats tests/ --recursive)
  fi
}
```

- [x] **Step 4: Run test to verify it passes**

Run:

```bash
bats tests/integration/test_execute_regression_gate.bats
```

Expected: PASS for all three test cases.

- [x] **Step 5: Defer commit**

本 change 按仓库约定不逐任务 commit；execute 完成后统一在 archive 阶段提交。不要执行 `git add` 或 `git commit`。

---

### Task 2: Wire the unified gate into the execute skill

**Files:**
- Modify: `skills/execute/SKILL.md:192-205`
- Modify: `tests/integration/test_execute_skill.bats:34+`

- [x] **Step 1: Write the failing test**

Append the following test to `tests/integration/test_execute_skill.bats` after the existing tests. It will fail because `skills/execute/SKILL.md` does not yet reference `run_regression_gate`.

```bash
@test "execute_skill uses run_regression_gate helper for full regression" {
  grep -q 'run_regression_gate' "$f"
}
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
bats tests/integration/test_execute_skill.bats
```

Expected: FAIL on the new test with a grep non-zero exit because `run_regression_gate` is not present in `skills/execute/SKILL.md`.

- [x] **Step 3: Write minimal implementation**

In `skills/execute/SKILL.md`, replace the current Step 5 block (lines 196-204) with the following block. The ctest command itself is removed from this step; the new helper now performs the unified regression. The surrounding `SKIP_REGRESSION` check and failure message are preserved.

```bash
if [ "${SKIP_REGRESSION:-}" != "1" ]; then
  echo "🔍 全量回归门 (Step 5)..."
  source "$SCRIPT_DIR/scripts/run_regression_gate.sh"
  run_regression_gate || {
    echo "❌ 全量回归失败: 修复后重试，或 SKIP_REGRESSION=1 跳过"
    exit 1
  }
  echo "✅ 全量回归通过"
fi
```

- [x] **Step 4: Run test to verify it passes**

Run:

```bash
bats tests/integration/test_execute_skill.bats
bats tests/integration/test_execute_regression_gate.bats
```

Expected: PASS for both files. The structural test confirms the skill references the helper; the functional test confirms the helper behaves correctly.

- [x] **Step 5: Defer commit**

本 change 按仓库约定不逐任务 commit；execute 完成后统一在 archive 阶段提交。不要执行 `git add` 或 `git commit`。

---

## Self-Review

1. **Spec coverage**: The proposal requires a unified regression step (baseline-aware when possible, plain recursive bats otherwise), `SKIP_REGRESSION=1` escape hatch, reuse of existing `report_regression.sh`, and one bats test covering both paths. Task 1 implements the helper and its bats test; Task 2 wires it into the execute skill.
2. **No placeholders**: All steps contain concrete file paths, code snippets, and exact commands.
3. **No commit instructions**: Step 5 of each task explicitly defers commit per the repo convention.
4. **Out-of-scope respected**: `report_regression.sh` is reused, not modified or reimplemented. The ctest build-validation command itself is not changed; only the regression gate step that invokes it is replaced by the bats-based unified gate.
