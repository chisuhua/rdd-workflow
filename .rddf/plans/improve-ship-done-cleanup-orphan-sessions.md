# improve-ship-done-cleanup-orphan-sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only orphan counter and a conditional option 5 to the `guide-ship` Phase 5 (ship-done) menu so users are nudged to clean up orphaned rddf-sessions before leaving the workflow.

**Architecture:** Extract a single bash helper `count_orphaned_sessions` into `skills/_lib/sessions_count.sh` that counts `state == "orphaned"` entries in `.rddf/state/sessions.json` (jq-first, python3 fallback, silent fail). `check_remaining_work` in `skills/guide-ship/scripts/ship_done.sh` calls the helper and, when the count > 0, inserts a warning line with the first three IDs (plus `+N more` overflow) and appends option 5 before the `i. 其他输入` fallback. When count == 0, the output is byte-for-byte identical to today.

**Tech Stack:** Bash, bats-core, jq (optional), python3 3.11+ (fallback), OpenSpec CLI.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/sessions_count.sh` | New file. Exposes `count_orphaned_sessions <project_root>` (read-only, echoes integer, silent failure). |
| `skills/guide-ship/scripts/ship_done.sh` | Modify. Call `count_orphaned_sessions`, emit warning + option 5 when count > 0, keep baseline output when count == 0. Must stay ≤ 30 lines. |
| `skills/guide-ship/SKILL.md` | Modify. Add one short paragraph in Phase 5 describing the orphan prompt. |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_ship_done_orphan_prompt.bats` | New file. 7 bats cases: 3 helper cases (missing/corrupt/mixed sessions.json) + 4 ship-done matrix cases (orphans+changes / no-orphans+no-changes / 1-orphan+1-change / >3-orphans overflow). |
| `tests/integration/test_ship_done_semantics.bats` | Existing file. No edits; must continue to pass (regression proof for baseline 4-option layout). |

---

### Task 1: Implement read-only orphaned-session counter

**Files:**
- Create: `skills/_lib/sessions_count.sh`
- Create: `tests/integration/test_ship_done_orphan_prompt.bats`

- [ ] **Step 1: Write the failing helper tests**

Create `tests/integration/test_ship_done_orphan_prompt.bats` with the file header, helpers, and three `count_orphaned_sessions` test cases (missing file, corrupt file, mixed sessions). The baseline `setup()`/`teardown()` builds a throwaway git repo at `$repo` and commits one file so that `git rev-parse --show-toplevel` resolves inside the helper.

```bash
#!/usr/bin/env bats
# tests/integration/test_ship_done_orphan_prompt.bats
# Matrix regression tests for ship-done orphan prompt.

load ../test_helper

_make_sessions_json() {
  local repo="$1"
  shift
  mkdir -p "$repo/.rddf/state"
  printf '%s' "$*" > "$repo/.rddf/state/sessions.json"
}

_run_check_remaining_work() {
  local repo="$1"
  bash -c '
    export RDD_WORKFLOW_SRC="$REPO_ROOT"
    source "$REPO_ROOT/skills/guide-ship/scripts/ship_done.sh"
    check_remaining_work "$1"
  ' _ "$repo"
}

setup() {
  repo=$(mktemp -d)
  git init -q "$repo"
  git -C "$repo" config user.email "t@t"
  git -C "$repo" config user.name "t"
  touch "$repo/init"
  git -C "$repo" add init && git -C "$repo" commit -q -m init
}

teardown() {
  rm -rf "$repo"
}

@test "count_orphaned_sessions: returns 0 when sessions.json is missing" {
  run bash -c '
    export RDD_WORKFLOW_SRC="$REPO_ROOT"
    source "$REPO_ROOT/skills/_lib/sessions_count.sh"
    count_orphaned_sessions "$1"
  ' _ "$repo"
  [ "$status" -eq 0 ]
  [ "$output" = "0" ]
}

@test "count_orphaned_sessions: returns 0 when sessions.json is corrupt" {
  _make_sessions_json "$repo" '{not valid}'
  run bash -c '
    export RDD_WORKFLOW_SRC="$REPO_ROOT"
    source "$REPO_ROOT/skills/_lib/sessions_count.sh"
    count_orphaned_sessions "$1"
  ' _ "$repo"
  [ "$status" -eq 0 ]
  [ "$output" = "0" ]
}

@test "count_orphaned_sessions: counts only orphaned sessions" {
  _make_sessions_json "$repo" '{"version":1,"sessions":[{"session_id":"rds_000000000001","state":"orphaned"},{"session_id":"rds_000000000002","state":"active"},{"session_id":"rds_000000000003","state":"completed"}]}'
  run bash -c '
    export RDD_WORKFLOW_SRC="$REPO_ROOT"
    source "$REPO_ROOT/skills/_lib/sessions_count.sh"
    count_orphaned_sessions "$1"
  ' _ "$repo"
  [ "$status" -eq 0 ]
  [ "$output" = "1" ]
}
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cd "$REPO_ROOT" && bats tests/integration/test_ship_done_orphan_prompt.bats --filter count_orphaned_sessions`
Expected: 3 FAIL with `source: skills/_lib/sessions_count.sh: No such file or directory` (helper not yet created).

- [ ] **Step 3: Write the helper implementation**

Create `skills/_lib/sessions_count.sh` with the `count_orphaned_sessions` function. The function uses `jq` when available, falls back to `python3 -c`, and echoes `0` on any failure (missing file, permission denied, corrupt JSON). It must stay ≤ 20 lines.

```bash
#!/usr/bin/env bash
# skills/_lib/sessions_count.sh — read-only orphaned rddf-session counter.

count_orphaned_sessions() {
  local root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local file="$root/.rddf/state/sessions.json"
  [ -f "$file" ] || { echo 0; return 0; }
  if command -v jq >/dev/null 2>&1; then
    jq '[.sessions[]? | select(.state == "orphaned")] | length' "$file" 2>/dev/null || echo 0
  else
    python3 -c 'import json,sys; f=sys.argv[1]; print(len([s for s in json.load(open(f)).get("sessions",[]) if s.get("state")=="orphaned"]))' "$file" 2>/dev/null || echo 0
  fi
}
```

- [ ] **Step 4: Run the helper tests to verify they pass**

Run: `cd "$REPO_ROOT" && bats tests/integration/test_ship_done_orphan_prompt.bats --filter count_orphaned_sessions`
Expected: 3 PASS.

Also verify the line-count constraint: `wc -l skills/_lib/sessions_count.sh` → output must be ≤ 20.

- [ ] **Step 5: Commit the helper**

```bash
cd "$REPO_ROOT"
git add skills/_lib/sessions_count.sh tests/integration/test_ship_done_orphan_prompt.bats
git commit -m "feat(ship-done): read-only orphaned rddf-session counter"
```

---

### Task 2: Integrate orphan prompt into ship-done menu

**Files:**
- Modify: `skills/guide-ship/scripts/ship_done.sh:18-46` (replace `check_remaining_work` body)
- Modify: `tests/integration/test_ship_done_orphan_prompt.bats` (append 4 matrix tests)

- [ ] **Step 1: Write the failing ship-done integration tests**

Append the four matrix tests below to `tests/integration/test_ship_done_orphan_prompt.bats` (after the three helper tests). They cover: 3 orphans + 0 changes, 0 orphans + 0 changes (baseline), 1 orphan + 1 change (📋 还有 header), and >3 orphans with `+N more` overflow.

```bash
@test "ship-done: 3 orphans + 0 changes shows option 5 and lists ids" {
  _make_sessions_json "$repo" '{"version":1,"sessions":[{"session_id":"rds_a1b5","state":"orphaned"},{"session_id":"rds_1221","state":"orphaned"},{"session_id":"rds_0569","state":"orphaned"}]}'
  run _run_check_remaining_work "$repo"
  [ "$status" -eq 0 ]
  [[ "$output" == *"✅ 所有 changes 已处理完毕"* ]]
  [[ "$output" == *"⚠️ 发现 3 个 orphaned rddf-sessions (rds_a1b5, rds_1221, rds_0569)"* ]]
  [[ "$output" == *"5. 🧹 清理 3 个 orphaned sessions"* ]]
  [[ "$output" == *"1. 继续处理"* ]]
  [[ "$output" == *"2. 回到 spec 端"* ]]
  [[ "$output" == *"3. 本次 session 结束"* ]]
  [[ "$output" == *"4. 项目完成"* ]]
  [[ "$output" == *"i. 其他输入"* ]]
}

@test "ship-done: 0 orphans + 0 changes matches baseline output" {
  run _run_check_remaining_work "$repo"
  [ "$status" -eq 0 ]
  [[ "$output" != *"orphaned"* ]]
  [[ "$output" != *"5."* ]]
  [[ "$output" == *"1. 继续处理"* ]]
  [[ "$output" == *"2. 回到 spec 端"* ]]
  [[ "$output" == *"3. 本次 session 结束"* ]]
  [[ "$output" == *"4. 项目完成"* ]]
  [[ "$output" == *"i. 其他输入"* ]]
}

@test "ship-done: 1 orphan + 1 change shows 还有 header and option 5" {
  mkdir -p "$repo/openspec/changes/example-change"
  _make_sessions_json "$repo" '{"version":1,"sessions":[{"session_id":"rds_9999","state":"orphaned"}]}'
  run _run_check_remaining_work "$repo"
  [ "$status" -eq 0 ]
  [[ "$output" == *"📋 还有"* ]]
  [[ "$output" == *"⚠️ 发现 1 个 orphaned rddf-sessions (rds_9999)"* ]]
  [[ "$output" == *"5. 🧹 清理 1 个 orphaned sessions"* ]]
  [[ "$output" == *"1. 继续处理"* ]]
  [[ "$output" == *"2. 回到 spec 端"* ]]
  [[ "$output" == *"3. 本次 session 结束"* ]]
  [[ "$output" == *"4. 项目完成"* ]]
  [[ "$output" == *"i. 其他输入"* ]]
}

@test "ship-done: more than 3 orphans truncates list with +N more" {
  _make_sessions_json "$repo" '{"version":1,"sessions":[{"session_id":"rds_0001","state":"orphaned"},{"session_id":"rds_0002","state":"orphaned"},{"session_id":"rds_0003","state":"orphaned"},{"session_id":"rds_0004","state":"orphaned"},{"session_id":"rds_0005","state":"orphaned"}]}'
  run _run_check_remaining_work "$repo"
  [ "$status" -eq 0 ]
  [[ "$output" == *"rds_0001, rds_0002, rds_0003 ... +2 more"* ]]
  [[ "$output" != *"rds_0004"* ]]
  [[ "$output" != *"rds_0005"* ]]
}
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cd "$REPO_ROOT" && bats tests/integration/test_ship_done_orphan_prompt.bats`
Expected: 4 new FAILs (the 3 helper tests from Task 1 still pass; the 4 matrix tests fail because `check_remaining_work` does not yet emit the orphan warning or option 5). Total status: 3 PASS / 4 FAIL.

- [ ] **Step 3: Modify `check_remaining_work` to emit the orphan prompt**

Replace the body of `check_remaining_work` in `skills/guide-ship/scripts/ship_done.sh` (lines 18-46) with the implementation below. The new body: (1) sources the helper via `skill_root.sh::resolve_rdd_lib_dir`, (2) counts `REMAINING`, `REMAINING_WT`, and `ORPHANS`, (3) prints the same dual-variant header as before, (4) when `ORPHANS > 0` inserts a warning line with the first three IDs (or `+N more` overflow) plus a hint to use `rddf-session` cleanup, and (5) appends option 5 only when `ORPHANS > 0`. The file must stay ≤ 30 lines.

```bash
#!/usr/bin/env bash
# skills/guide-ship/scripts/ship_done.sh
check_remaining_work() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
  source "$(resolve_rdd_lib_dir)/sessions_count.sh"
  local REMAINING REMAINING_WT ORPHANS
  REMAINING=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l | tr -d '[:space:]')
  REMAINING_WT=$(git worktree list 2>/dev/null | awk '$3 ~ /^openspec\// {print $1}' | wc -l | tr -d '[:space:]')
  ORPHANS=$(count_orphaned_sessions "$PROJECT_ROOT")
  if [ "$REMAINING_WT" -gt 0 ] || [ "$REMAINING" -gt 0 ]; then echo "📋 还有 $REMAINING_WT 个 worktree 在跑,$REMAINING 个未处理 change"; else echo "✅ 所有 changes 已处理完毕"; fi
  echo ""
  if [ "$ORPHANS" -gt 0 ]; then
    local IDS; IDS=$(PROJECT_ROOT="$PROJECT_ROOT" python3 -c 'import json, os; d=json.load(open(os.path.join(os.environ["PROJECT_ROOT"], ".rddf/state/sessions.json"))); ids=[s["session_id"] for s in d.get("sessions",[]) if s.get("state")=="orphaned"]; print(", ".join(ids[:3]) + (" ... +{} more".format(len(ids)-3) if len(ids)>3 else ""))' 2>/dev/null || echo "???")
    echo "⚠️ 发现 $ORPHANS 个 orphaned rddf-sessions ($IDS)"
    echo "   建议清理: skill_use(\"rddf-session\", \"abandon\", ...) 或 archive-history"
  fi
  echo "请选择:"
  echo "1. 继续处理 (skill_use(\"guide-ship\")) - 还有 worktree 要处理"
  echo "2. 回到 spec 端 (skill_use(\"guide-arch\") 或 skill_use(\"guide-plan\")) - 创建更多 changes"
  echo "3. 本次 session 结束 - 退出 ship-done,稍后继续"
  echo "4. 项目完成 - 不再做任何 change(此项目归档)"
  [ "$ORPHANS" -gt 0 ] && echo "5. 🧹 清理 $ORPHANS 个 orphaned sessions (skill_use(\"rddf-session\", \"abandon\", ...) 或 archive-history)"
  echo "i. 其他输入"
}
```

Also update the file-level comment header to document the new behavior. Replace the existing lines 3-7 with:

```bash
# Phase 5 "Loop check" logic from guide-ship.md extracted into a reusable helper.
# Was a ~26-line inline bash block at L617-L643 counting remaining unprocessed
# changes and active openspec/* worktrees, then printing a dual-variant menu
# (different intro line depending on REMAINING/REMAINING_WT counts).
# When count_orphaned_sessions > 0, also prints a warning line with the first
# three orphaned rddf-session IDs (plus `+N more` overflow) and appends option 5
# before the `i. 其他输入` fallback. Baseline output is unchanged when orphans
# count is 0.
```

Verify the line-count constraint: `wc -l skills/guide-ship/scripts/ship_done.sh` → output must be ≤ 30.

- [ ] **Step 4: Run the integration tests to verify they pass**

Run: `cd "$REPO_ROOT" && bats tests/integration/test_ship_done_orphan_prompt.bats`
Expected: 7 PASS (3 helper + 4 matrix).

Then run the existing regression suite to confirm the baseline 4-option layout is untouched: `cd "$REPO_ROOT" && bats tests/integration/test_ship_done_semantics.bats`
Expected: 2 PASS (the existing `test_ship_done_semantics.bats` is the regression lock for the old 4-option menu).

- [ ] **Step 5: Commit the ship-done integration**

```bash
cd "$REPO_ROOT"
git add skills/guide-ship/scripts/ship_done.sh tests/integration/test_ship_done_orphan_prompt.bats
git commit -m "feat(ship-done): conditional orphan cleanup prompt in Phase 5 menu"
```

---

### Task 3: Document and validate

**Files:**
- Modify: `skills/guide-ship/SKILL.md` (insert one paragraph after line 614, before the `**输入处理**` line at 616)

- [ ] **Step 1: Add the documentation paragraph**

In `skills/guide-ship/SKILL.md`, insert the following one-paragraph block immediately after the closing ` ``` ` of the `**Loop check:**` code block (line 614) and before the `**输入处理**：` heading (line 616):

```markdown
**Orphaned rddf-sessions prompt**: When `.rddf/state/sessions.json` contains orphaned sessions, `check_remaining_work` prints the first three IDs (with `+N more` if there are more) and adds option 5 to the ship-done menu. Choosing option 5 launches the rddf-session cleanup skill; no automatic cleanup occurs.
```

- [ ] **Step 2: Run the full ship-done bats suite**

Run: `cd "$REPO_ROOT" && bats tests/integration/test_ship_done_*.bats`
Expected: 9 PASS (7 from `test_ship_done_orphan_prompt.bats` + 2 from `test_ship_done_semantics.bats`).

Verify the documentation paragraph is present: `grep -c "orphaned rddf-sessions" skills/guide-ship/SKILL.md` → output must be `1`.
Verify the line-count constraint on the production code: `wc -l skills/guide-ship/scripts/ship_done.sh skills/_lib/sessions_count.sh | tail -1` → the sum line must be ≤ 50 (per spec). Each individual file must be ≤ 30 and ≤ 20 respectively.

- [ ] **Step 3: Run strict OpenSpec validation**

Run: `cd "$REPO_ROOT" && openspec validate --type change improve-ship-done-cleanup-orphan-sessions --strict --json`
Expected: JSON output with `"valid": true` for the change.

If the JSON parsing fails, the literal string `valid=true` must appear in stdout (the validation script may print a non-JSON summary on success in some environments).

- [ ] **Step 4: Commit the documentation update**

```bash
cd "$REPO_ROOT"
git add skills/guide-ship/SKILL.md
git commit -m "docs(ship-done): document orphaned rddf-session prompt in Phase 5"
```
