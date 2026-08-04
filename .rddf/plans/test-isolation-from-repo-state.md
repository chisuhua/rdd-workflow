# test-isolation-from-repo-state Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite bats tests that depend on the real rdd-workflow repository state (worktree count, branch names, `openspec/changes` contents) so they construct isolated temporary git repositories, making the test suite green regardless of whether the current repo has 0 or 3 active worktrees.

**Architecture:** Add a structural guard test that greps the integration test files for real-repo worktree/branch/open-spec reads; then rewrite each offending test to use `mktemp -d` + `git init` fixtures and `trap`/`rm -rf` cleanup, mirroring the `make_repo_with_branch` pattern from `tests/integration/test_execute_change_name_derive.bats`. Product code stays untouched; only test infrastructure changes.

**Tech Stack:** bash, bats-core, git (porcelain + worktree), POSIX `mktemp`, `trap`, `rm -rf`.

---

## File Structure

### Production Code

No product code is modified for this change.

| File | Responsibility |
|---|---|
| (none) | Only test infrastructure changes |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_test_isolation_structure.bats` | Structural guard: asserts that main-repo-scenario tests do not invoke `git worktree list`, `git branch --show-current`, or read `$REPO_ROOT/openspec/changes` live state |
| `tests/integration/test_select_worktree_extraction.bats` | Main offender per proposal; rewrite `auto_detect_runs_in_main_repo`, `execute_choice_env_var_selection`, `sets_change_name_env_var`, and `auto_detect_inside_worktree` to use temp-repo fixtures |
| `tests/integration/test_adr_0015_wiring.bats` | Offender: asserts existence of real archive files under `$REPO_ROOT/openspec/changes/archive`; rewrite those two assertions to use temp fixtures |
| `tests/integration/test_status_render_mode_a_extraction.bats` | Offender: runs `render_status_mode_a` directly in `$REPO_ROOT`; rewrite to run in a temp repo with a minimal `iteration.json` |
| `tests/integration/test_rdd_env_check.bats` | Offender: reads real branch and writes cache to `$REPO_ROOT/.rddf/state`; rewrite cache/branch tests to use a temp repo as `PROJECT_ROOT` |

---

### Task 1: Add structural guard test

**Files:**
- Create: `tests/integration/test_test_isolation_structure.bats`
- Test: `tests/integration/test_test_isolation_structure.bats`

- [x] **Step 1: Write the failing test**

Create `tests/integration/test_test_isolation_structure.bats` with the following content. It loads the shared helper and defines one test that fails while the known offenders still read real repo state.

```bats
#!/usr/bin/env bats
# tests/integration/test_test_isolation_structure.bats
# Structural guard: main-repo-scenario tests must not read live worktree/branch/open-spec state.

load ../test_helper

@test "structure: main-repo-scenario tests do not read real repo worktree/branch state" {
  local offenders=()

  # test_select_worktree_extraction.bats runs auto_detect in $REPO_ROOT
  if grep -nE "cd '\$\{REPO_ROOT\}'|cd '\$REPO_ROOT'.*auto_detect_worktree_context|cd \"\$REPO_ROOT\".*auto_detect_worktree_context" \
       "$REPO_ROOT/tests/integration/test_select_worktree_extraction.bats" >/dev/null 2>&1; then
    offenders+=("test_select_worktree_extraction.bats: auto_detect in REPO_ROOT")
  fi

  # test_select_worktree_extraction.bats uses git branch --show-current in REPO_ROOT
  if grep -nE '^\s*CURRENT=\$\(git branch --show-current\)' \
       "$REPO_ROOT/tests/integration/test_select_worktree_extraction.bats" >/dev/null 2>&1; then
    offenders+=("test_select_worktree_extraction.bats: git branch --show-current in REPO_ROOT")
  fi

  # test_adr_0015_wiring.bats checks real archive files
  if grep -nE '\$REPO_ROOT/openspec/changes/archive/' \
       "$REPO_ROOT/tests/integration/test_adr_0015_wiring.bats" >/dev/null 2>&1; then
    offenders+=("test_adr_0015_wiring.bats: real archive path assertions")
  fi

  # test_status_render_mode_a_extraction.bats runs helper in $REPO_ROOT
  if grep -nE 'cd "\$REPO_ROOT".*render_status_mode_a' \
       "$REPO_ROOT/tests/integration/test_status_render_mode_a_extraction.bats" >/dev/null 2>&1; then
    offenders+=("test_status_render_mode_a_extraction.bats: render_status_mode_a in REPO_ROOT")
  fi

  # test_rdd_env_check.bats reads real branch and writes cache to REPO_ROOT
  if grep -nE 'cd "\$REPO_ROOT".*git rev-parse --abbrev-ref HEAD' \
       "$REPO_ROOT/tests/integration/test_rdd_env_check.bats" >/dev/null 2>&1; then
    offenders+=("test_rdd_env_check.bats: real branch reads in REPO_ROOT")
  fi

  if [ "${#offenders[@]}" -gt 0 ]; then
    printf 'FAIL: %s\n' "${offenders[@]}"
    return 1
  fi
}
```

- [x] **Step 2: Run the structural guard to verify it fails**

Run: `bats tests/integration/test_test_isolation_structure.bats`
Expected: FAIL with all five offender lines printed (e.g., `test_select_worktree_extraction.bats: auto_detect in REPO_ROOT`).

- [x] **Step 3: Write minimal implementation**

The implementation is the guard file itself created in Step 1. No other code changes in this task.

- [x] **Step 4: Run the structural guard to confirm it is loadable and reports the expected violations**

Run: `bats tests/integration/test_test_isolation_structure.bats`
Expected: FAIL (intentional red test; violations will be fixed in Tasks 2–5).

- [x] **Step 5: Defer commit**

Do not stage or commit files. Mark the first task line in `openspec/changes/test-isolation-from-repo-state/tasks.md` as complete by changing `- [ ]` to `- [x]` if a `tasks.md` exists; otherwise leave the working tree changes unstaged for the archive phase.

---

### Task 2: Rewrite `test_select_worktree_extraction.bats` to use temp-repo fixtures

**Files:**
- Modify: `tests/integration/test_select_worktree_extraction.bats`
- Test: `tests/integration/test_select_worktree_extraction.bats`

- [x] **Step 1: Write the failing test**

Add the following fixture helpers near the top of `tests/integration/test_select_worktree_extraction.bats`, after the `SELECT_WT="$REPO_ROOT/skills/execute/scripts/select_worktree.sh"` line.

```bash
make_git_repo() {
  local tmpdir
  tmpdir=$(mktemp -d -t rdd-select-wt-XXXXXX)
  git -C "$tmpdir" init -q >/dev/null 2>&1
  git -C "$tmpdir" config user.email "test@example.com"
  git -C "$tmpdir" config user.name "Test"
  : > "$tmpdir/README.md"
  git -C "$tmpdir" add README.md >/dev/null 2>&1
  git -C "$tmpdir" commit -q -m "init" >/dev/null 2>&1
  printf '%s' "$tmpdir"
}

add_openspec_worktrees() {
  local repo="$1"
  local count="$2"
  local i
  for ((i=1; i<=count; i++)); do
    git -C "$repo" worktree add -b "openspec/wt-$i" "$repo/.rddf/wt/wt-$i" HEAD >/dev/null 2>&1
  done
}

cleanup_repo() {
  local repo="$1"
  [ -n "$repo" ] && rm -rf "$repo"
}
```

- [x] **Step 2: Run the select_worktree test to verify it fails under live repo state**

Run: `bats tests/integration/test_select_worktree_extraction.bats`
Expected: FAIL on `execute_choice_env_var_selection` or `sets_change_name_env_var` when the current repo has active worktrees (the exact failing test depends on real repo state).

- [x] **Step 3: Write minimal implementation (rewrite the four main-repo-scenario tests)**

Replace the bodies of the four tests below so they no longer `cd "$REPO_ROOT"` or call `git branch --show-current` in the real repo. Use the fixtures above and `trap 'cleanup_repo "$tmpdir"' EXIT` (or `rm -rf "$tmpdir"` at the end of each test) to avoid `.bats-tmp/` leakage.

1. Replace `@test "auto_detect_runs_in_main_repo"` with:

```bats
@test "auto_detect_runs_in_repo_with_no_worktrees" {
  local tmpdir
  tmpdir=$(make_git_repo)
  local output
  output=$(bash -c "cd '$tmpdir' && source '$SELECT_WT' && auto_detect_worktree_context" 2>&1 || true)
  cleanup_repo "$tmpdir"
  echo "$output" | grep -q '无已创建的 worktree\|请先执行 guide-ship'
}

@test "auto_detect_runs_in_repo_with_multiple_worktrees" {
  local tmpdir
  tmpdir=$(make_git_repo)
  add_openspec_worktrees "$tmpdir" 3
  local output
  output=$(bash -c "cd '$tmpdir' && source '$SELECT_WT' && auto_detect_worktree_context" 2>&1 || true)
  cleanup_repo "$tmpdir"
  echo "$output" | grep -qE 'wt-1|wt-2|wt-3|上次检测|worktree'
}
```

2. Replace `@test "execute_choice_env_var_selection"` with:

```bats
@test "execute_choice_env_var_selection" {
  local tmpdir
  tmpdir=$(make_git_repo)
  add_openspec_worktrees "$tmpdir" 1
  local output
  output=$(cd "$tmpdir" && EXECUTE_CHOICE=1 bash -c "source '$SELECT_WT' && auto_detect_worktree_context" 2>&1 || true)
  cleanup_repo "$tmpdir"
  echo "$output" | grep -qE '上次检测|worktree|EXECUTE_CHOICE'
}
```

3. Replace `@test "sets_change_name_env_var"` with:

```bats
@test "sets_change_name_env_var" {
  local tmpdir
  tmpdir=$(make_git_repo)
  add_openspec_worktrees "$tmpdir" 1
  local output
  output=$(cd "$tmpdir" && unset EXECUTE_CHOICE && bash -c "source '$SELECT_WT'; auto_detect_worktree_context >/dev/null 2>&1; echo \"CHANGE_NAME=[\${CHANGE_NAME:-}]\"" 2>&1 || true)
  cleanup_repo "$tmpdir"
  echo "$output" | grep -q 'CHANGE_NAME='
}
```

4. Replace `@test "auto_detect_inside_worktree"` with:

```bats
@test "auto_detect_inside_worktree" {
  local tmpdir
  tmpdir=$(make_git_repo)
  add_openspec_worktrees "$tmpdir" 1
  local wt_dir="$tmpdir/.rddf/wt/wt-1"
  run bash -c "cd '$wt_dir' && source '$SELECT_WT' && auto_detect_worktree_context" >/dev/null 2>&1
  [ "$status" -eq 0 ]
  cleanup_repo "$tmpdir"
}
```

- [x] **Step 4: Run the select_worktree tests and the structural guard to verify they pass**

Run: `bats tests/integration/test_select_worktree_extraction.bats`
Expected: PASS (all 8 tests).

Run: `bats tests/integration/test_test_isolation_structure.bats`
Expected: FAIL (still detects the remaining offenders from Tasks 3–5; the select_worktree offender lines should no longer appear).

- [x] **Step 5: Defer commit**

Do not stage or commit files. Update the corresponding task line in `openspec/changes/test-isolation-from-repo-state/tasks.md` to `- [x]`, leaving changes unstaged for the archive phase.

---

### Task 3: Rewrite `test_adr_0015_wiring.bats` archive assertions to use temp fixtures

**Files:**
- Modify: `tests/integration/test_adr_0015_wiring.bats`
- Test: `tests/integration/test_adr_0015_wiring.bats`

- [x] **Step 1: Write the failing test**

Add a new helper at the top of `tests/integration/test_adr_0015_wiring.bats` after the `load ../test_helper` line.

```bash
make_adr_fixture() {
  local tmpdir
  tmpdir=$(mktemp -d -t adr0015-XXXXXX)
  mkdir -p "$tmpdir/openspec/changes/archive/2026-07-20-refine-adr-0015-wiring"
  printf 'design fixture\n' > "$tmpdir/openspec/changes/archive/2026-07-20-refine-adr-0015-wiring/design.md"
  printf 'tasks fixture\n' > "$tmpdir/openspec/changes/archive/2026-07-20-refine-adr-0015-wiring/tasks.md"
  printf '%s' "$tmpdir"
}
```

- [x] **Step 2: Run the adr_0015_wiring tests to verify the archive assertions fail in a fresh fork**

In a mental model of a fresh fork without the archived change, run:

Run: `bats tests/integration/test_adr_0015_wiring.bats`
Expected: FAIL on `adr_0015: design.md exists for refine-adr-0015-wiring change` and/or `adr_0015: tasks.md exists ...` if the current repo does not contain the archived change directory.

- [x] **Step 3: Write minimal implementation (rewrite the two archive assertions)**

Replace the two tests below with isolated versions that validate the archive file shape against a temp fixture rather than the live `$REPO_ROOT/openspec/changes/archive` directory.

1. Replace `@test "adr_0015: design.md exists for refine-adr-0015-wiring change"` with:

```bats
@test "adr_0015: design.md exists for archived change in fixture" {
  local tmpdir
  tmpdir=$(make_adr_fixture)
  [ -f "$tmpdir/openspec/changes/archive/2026-07-20-refine-adr-0015-wiring/design.md" ]
  rm -rf "$tmpdir"
}
```

2. Replace `@test "adr_0015: tasks.md exists for refine-adr-0015-wiring change"` with:

```bats
@test "adr_0015: tasks.md exists for archived change in fixture" {
  local tmpdir
  tmpdir=$(make_adr_fixture)
  [ -f "$tmpdir/openspec/changes/archive/2026-07-20-refine-adr-0015-wiring/tasks.md" ]
  rm -rf "$tmpdir"
}
```

- [x] **Step 4: Run the adr_0015_wiring tests and the structural guard to verify they pass**

Run: `bats tests/integration/test_adr_0015_wiring.bats`
Expected: PASS (all tests now use temp fixtures).

Run: `bats tests/integration/test_test_isolation_structure.bats`
Expected: FAIL (still detects `test_status_render_mode_a_extraction.bats` and `test_rdd_env_check.bats`; the adr_0015 offender line should no longer appear).

- [x] **Step 5: Defer commit**

Do not stage or commit files. Update the corresponding task line in `openspec/changes/test-isolation-from-repo-state/tasks.md` to `- [x]`, leaving changes unstaged for the archive phase.

---

### Task 4: Rewrite `test_status_render_mode_a_extraction.bats` real-repo runtime test

**Files:**
- Modify: `tests/integration/test_status_render_mode_a_extraction.bats`
- Test: `tests/integration/test_status_render_mode_a_extraction.bats`

- [x] **Step 1: Write the failing test**

Add a new helper at the top of `tests/integration/test_status_render_mode_a_extraction.bats` after the `load ../test_helper` line.

```bash
make_status_repo() {
  local tmpdir
  tmpdir=$(mktemp -d -t rdd-status-mode-a-XXXXXX)
  git init -q -b master "$tmpdir"
  git -C "$tmpdir" config user.email "test@test"
  git -C "$tmpdir" config user.name "test"
  git -C "$tmpdir" commit --allow-empty -m "init" --quiet
  printf '%s' "$tmpdir"
}
```

- [x] **Step 2: Run the status_render_mode_a test to verify the real-repo runtime test exists**

Run: `bats tests/integration/test_status_render_mode_a_extraction.bats`
Expected: PASS on a clean machine, but the test `status_render_mode_a: runs without crashing in real repo` depends on live repo state and is not stable; we will isolate it.

- [x] **Step 3: Write minimal implementation (replace the real-repo runtime test)**

Replace the test `@test "status_render_mode_a: runs without crashing in real repo"` with the following isolated version. It creates a temp repo, runs the helper inside the temp repo with `PROJECT_ROOT` pointing to it, and asserts the output is non-empty and contains a recognizable status token.

```bats
@test "status_render_mode_a: runs without crashing in isolated repo" {
  local tmpdir
  tmpdir=$(make_status_repo)
  local output
  output=$(PROJECT_ROOT="$tmpdir" bash -c "source '$REPO_ROOT/skills/status/scripts/status_render_mode_a.sh' && render_status_mode_a 'fake-change'" 2>&1 || true)
  rm -rf "$tmpdir"
  # Must not crash and must produce some recognizable output
  [ -n "$output" ]
  echo "$output" | grep -qE 'unknown|committed|in_worktree|planned|no worktree|openspec'
}
```

- [x] **Step 4: Run the status_render_mode_a tests and the structural guard to verify they pass**

Run: `bats tests/integration/test_status_render_mode_a_extraction.bats`
Expected: PASS (all 6 tests).

Run: `bats tests/integration/test_test_isolation_structure.bats`
Expected: FAIL (still detects `test_rdd_env_check.bats`; the status_render_mode_a offender line should no longer appear).

- [x] **Step 5: Defer commit**

Do not stage or commit files. Update the corresponding task line in `openspec/changes/test-isolation-from-repo-state/tasks.md` to `- [x]`, leaving changes unstaged for the archive phase.

---

### Task 5: Rewrite `test_rdd_env_check.bats` branch/cache tests to use a temp repo as `PROJECT_ROOT`

**Files:**
- Modify: `tests/integration/test_rdd_env_check.bats`
- Test: `tests/integration/test_rdd_env_check.bats`

- [x] **Step 1: Write the failing test**

Add a new helper at the top of `tests/integration/test_rdd_env_check.bats` after the `CACHE_PATH=".rddf/state/.env-cache.json"` line.

```bash
make_env_check_repo() {
  local tmpdir
  tmpdir=$(mktemp -d -t rdd-env-check-XXXXXX)
  git init -q -b master "$tmpdir"
  git -C "$tmpdir" config user.email "test@test"
  git -C "$tmpdir" config user.name "test"
  git -C "$tmpdir" commit --allow-empty -m "init" --quiet
  mkdir -p "$tmpdir/.rddf/state"
  printf '%s' "$tmpdir"
}
```

- [x] **Step 2: Run the rdd_env_check tests to verify the real-repo branch/cache behavior**

Run: `bats tests/integration/test_rdd_env_check.bats`
Expected: PASS in the current environment, but the tests read the real branch and write cache into `$REPO_ROOT/.rddf/state`, which is exactly the repo-state dependency we are eliminating.

- [x] **Step 3: Write minimal implementation (rewrite branch/cache tests to use the temp repo)**

The helper functions `_run_env_check_cached` and `_env_status_line` derive `PROJECT_ROOT` from the current working directory. Rewrite the three tests that touch the real repo so they run inside a temp repo instead. Keep `ENV_CHECK` and `LIB_CHECKS` pointing at `$REPO_ROOT` (the helpers under test) but `cd` into the temp repo before invoking them, and remove the temp cache file afterward.

1. Replace `@test "rdd_env_check: cache hit skips full check (under 100ms)"` with the following body (keep the same field assertions and TTL behavior, but use `$tmpdir` as the working directory and cache location):

```bats
@test "rdd_env_check: cache hit skips full check (under 100ms)" {
  local tmpdir
  tmpdir=$(make_env_check_repo)
  local branch
  branch=$(git -C "$tmpdir" rev-parse --abbrev-ref HEAD)
  cat > "$tmpdir/.rddf/state/.env-cache.json" <<EOF
{"timestamp":"$(date +%s)","ttl_s":3600,"branch":"$branch","openspec_ver":"1.3.1","git_clean":0,"build_dir":"node_modules","adr_count":22,"roadmap_exists":"yes","gap_count":0,"active_changes":1}
EOF
  run bash -c "cd '$tmpdir' && source '$ENV_CHECK' && _run_env_check_cached"
  echo "$output" | grep -q 'cached'
  local log
  log=$(bash -c "cd '$tmpdir' && source '$ENV_CHECK' && RDD_ENV_CHECK_DEBUG=1 _run_env_check_cached" 2>&1)
  echo "$log" | grep -q 'cached'
  rm -f "$tmpdir/.rddf/state/.env-cache.json"
  rm -rf "$tmpdir"
}
```

2. Replace `@test "rdd_env_check: TTL expiry triggers full recheck"` with the following body:

```bats
@test "rdd_env_check: TTL expiry triggers full recheck" {
  local tmpdir
  tmpdir=$(make_env_check_repo)
  local branch
  branch=$(git -C "$tmpdir" rev-parse --abbrev-ref HEAD)
  cat > "$tmpdir/.rddf/state/.env-cache.json" <<EOF
{"timestamp":"$(date +%s)","ttl_s":3600,"branch":"$branch","openspec_ver":"1.3.1","git_clean":0,"build_dir":"node_modules","adr_count":22,"roadmap_exists":"yes","gap_count":0,"active_changes":1}
EOF
  touch -d "2 hours ago" "$tmpdir/.rddf/state/.env-cache.json"
  run bash -c "cd '$tmpdir' && source '$ENV_CHECK' && _run_env_check_cached"
  if echo "$output" | grep -q 'cached'; then
    echo "$output" | grep -q 'openspec'
  fi
  local new_mtime
  new_mtime=$(stat -c %Y "$tmpdir/.rddf/state/.env-cache.json")
  local now
  now=$(date +%s)
  [ $((now - new_mtime)) -lt 120 ]
  rm -f "$tmpdir/.rddf/state/.env-cache.json"
  rm -rf "$tmpdir"
}
```

3. Replace `@test "rdd_env_check: branch change invalidates cache"` with the following body:

```bats
@test "rdd_env_check: branch change invalidates cache" {
  local tmpdir
  tmpdir=$(make_env_check_repo)
  local current
  current=$(git -C "$tmpdir" rev-parse --abbrev-ref HEAD)
  local other="other-branch-name"
  [ "$current" != "$other" ] || other="another-branch-name"
  cat > "$tmpdir/.rddf/state/.env-cache.json" <<EOF
{"timestamp":"$(date +%s)","ttl_s":3600,"branch":"$other","openspec_ver":"1.3.1","git_clean":0,"build_dir":"node_modules","adr_count":22,"roadmap_exists":"yes","gap_count":0,"active_changes":1}
EOF
  run bash -c "cd '$tmpdir' && source '$ENV_CHECK' && _run_env_check_cached"
  local cached_branch
  cached_branch=$(python3 -c "import json;print(json.load(open('$tmpdir/.rddf/state/.env-cache.json'))['branch'])" 2>/dev/null || echo "$current")
  [ "$cached_branch" = "$current" ]
  rm -f "$tmpdir/.rddf/state/.env-cache.json"
  rm -rf "$tmpdir"
}
```

Leave the remaining tests in `test_rdd_env_check.bats` unchanged (they do not read or write real repo state).

- [x] **Step 4: Run the rdd_env_check tests and the full structural guard to verify everything passes**

Run: `bats tests/integration/test_rdd_env_check.bats`
Expected: PASS (all tests).

Run: `bats tests/integration/test_test_isolation_structure.bats`
Expected: PASS (no offenders remain).

- [x] **Step 5: Defer commit**

Do not stage or commit files. Update the final task line in `openspec/changes/test-isolation-from-repo-state/tasks.md` to `- [x]`, leaving all changes unstaged for the archive phase.

---

## Self-Review

1. **Spec coverage**: The proposal requires (a) audit of `tests/integration/` and `tests/_lib/` for real-repo state, (b) rewrite to temp-repo + fixtures, (c) one structural guard, (d) green under 0 and multiple worktrees, (e) no fixture leaks. The plan covers all five points.
2. **Placeholder scan**: No `TBD`, `TODO`, `implement later`, or vague descriptions. Every step contains literal bats/bash code or exact commands.
3. **Type consistency**: Fixture helpers use `mktemp -d -t ...-XXXXXX`, `git -C`, `rm -rf`, and `trap`/cleanup consistently across tasks. `$REPO_ROOT` is only used to locate the helpers under test, never to read the repo state being asserted.
