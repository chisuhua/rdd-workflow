# check-project-setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable `check_project_setup` helper that hard-blocks `guide-arch` Phase 1 when downstream projects lack required `.gitignore` rules, soft-presents setup issues in `guide` and `INSTALL.md`, and is locked by bats integration tests.

**Architecture:** A single bash helper `skills/_lib/check_project_setup.sh` emits a JSON array of issues (`name`, `status`, `severity`, `fix_command`, `detail`). Two consumers wire it in: `skills/guide-arch/scripts/arch_env_check.sh` (hard gate: return 1 on `severity==error && status==fail`) and `skills/guide/scripts/scan-state.sh` (soft pre-menu analysis: always continues, treats every issue as `safe_auto_fix`). One existing bats test is refactored to assert through the helper instead of duplicating `.gitignore` inspection logic.

**Tech Stack:** bash (helper + consumers), bats-core 1.10+ (integration tests), `jq` (JSON parsing in consumers), `python3 -m json.tool` (validation), `git ls-files`, `du -sm`, `openspec --version`.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/check_project_setup.sh` | Public function `check_project_setup <project_root>` emitting JSON issue array (6 checks) |
| `skills/guide-arch/scripts/arch_env_check.sh` | Hard gate: source helper, return 1 if any `severity==error && status==fail` |
| `skills/guide/scripts/scan-state.sh` | Soft pre-menu analysis: display all issues as `safe_auto_fix`, never block |
| `skills/INSTALL.md` | New Section 5 "项目设置检查" with ✅/❌ checklist |
| `USAGE.md` | Add "常见陷阱" line about `guide-arch` `.gitignore` failure fix |
| `docs/v2-workflow-overview.md` | Add paragraph about project-setup check triggers |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_check_project_setup.bats` | 7 scenarios covering passing fixture, missing `.rddf/state/`, missing `.rddf/wt/`, plans regression, no `.gitignore`, large untracked dirs, JSON schema |
| `tests/integration/test_plan_review_phase.bats` | Refactor lines 62-66 to assert via helper |

---

### Task 1: Implement project-setup helper

**Files:**
- Create: `skills/_lib/check_project_setup.sh`
- Test: `tests/integration/test_check_project_setup.bats` (created in Task 2)

#### 1.1: Create helper skeleton with JSON output

**Files:**
- Create: `skills/_lib/check_project_setup.sh`

- [ ] **Step 1: Write the failing test stub**

Create `tests/integration/test_check_project_setup.bats` (minimal first case):
```bash
#!/usr/bin/env bats
load ../test_helper

@test "check_project_setup: passing project emits valid JSON array" {
  run bash -c "source '$REPO_ROOT/skills/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT'"
  [ "$status" -eq 0 ]
  echo "$output" | python3 -m json.tool >/dev/null
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_check_project_setup.bats --filter "passing project"`
Expected: FAIL with "No such file or directory" or non-zero status (helper not yet created)

- [ ] **Step 3: Write minimal implementation**

Create `skills/_lib/check_project_setup.sh`:
```bash
#!/usr/bin/env bash
# check_project_setup.sh - validate project setup for rdd-workflow runtime.
# Emits a JSON array of issues to stdout. Returns 0 regardless of issue status.
set -u

check_project_setup() {
  local project_root="${1:-$(pwd)}"
  printf '[]\n'
}

# Allow sourcing without running
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  check_project_setup "$@"
fi
```

Make executable: `chmod +x skills/_lib/check_project_setup.sh`

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "passing project"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/check_project_setup.sh tests/integration/test_check_project_setup.bats
git commit -m "feat(check-project-setup): scaffold check_project_setup helper"
```

#### 1.2: Implement gitignore checks for `.rddf/state/`, `.rddf/wt/`, `.rddf/plans/`

**Files:**
- Modify: `skills/_lib/check_project_setup.sh`

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/test_check_project_setup.bats`:
```bash
@test "check_project_setup: rddf_state_ignored passes on repo" {
  run bash -c "source '$REPO_ROOT/skills/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT' | jq '.[] | select(.name==\"rddf_state_ignored\") | .status'"
  [ "$status" -eq 0 ]
  [ "$output" = "pass" ]
}

@test "check_project_setup: rddf_plans_not_ignored passes on repo" {
  run bash -c "source '$REPO_ROOT/skills/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT' | jq '.[] | select(.name==\"rddf_plans_not_ignored\") | .status'"
  [ "$status" -eq 0 ]
  [ "$output" = "pass" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_check_project_setup.bats --filter "rddf_state_ignored|rddf_plans_not_ignored"`
Expected: FAIL (no `rddf_state_ignored` field in output yet)

- [ ] **Step 3: Write implementation**

Replace `check_project_setup` body in `skills/_lib/check_project_setup.sh`:
```bash
check_project_setup() {
  local project_root="${1:-$(pwd)}"
  local gitignore="$project_root/.gitignore"
  local issues=()

  # Helper: emit one issue object
  _emit_issue() {
    local name="$1" status="$2" severity="$3" fix_command="$4" detail="$5"
    printf '{"name":"%s","status":"%s","severity":"%s","fix_command":"%s","detail":"%s"}' \
      "$name" "$status" "$severity" "$fix_command" "$detail"
  }

  # Check 1: .rddf/state/ must be ignored
  if [ ! -f "$gitignore" ]; then
    issues+=("$(_emit_issue "rddf_state_ignored" "fail" "error" "echo '.rddf/state/' >> .gitignore" "现状: .gitignore 不存在; 期望: 包含 .rddf/state/")")
  elif grep -qE '^\.rddf/state/' "$gitignore" || grep -qE '^\.rddf/' "$gitignore"; then
    issues+=("$(_emit_issue "rddf_state_ignored" "pass" "info" "" "现状: .rddf/state/ 已忽略; 期望: 同上")")
  else
    issues+=("$(_emit_issue "rddf_state_ignored" "fail" "error" "echo '.rddf/state/' >> .gitignore" "现状: .gitignore 无 .rddf/state/; 期望: 包含 .rddf/state/")")
  fi

  # Check 2: .rddf/wt/ must be ignored
  if grep -qE '^\.rddf/wt/' "$gitignore" || grep -qE '^\.rddf/' "$gitignore"; then
    issues+=("$(_emit_issue "rddf_wt_ignored" "pass" "info" "" "现状: .rddf/wt/ 已忽略; 期望: 同上")")
  else
    issues+=("$(_emit_issue "rddf_wt_ignored" "fail" "error" "echo '.rddf/wt/' >> .gitignore" "现状: .gitignore 无 .rddf/wt/; 期望: 包含 .rddf/wt/")")
  fi

  # Check 3: .rddf/plans/ must NOT be ignored (regression detection)
  if grep -qE '^\.rddf/plans/' "$gitignore"; then
    issues+=("$(_emit_issue "rddf_plans_not_ignored" "fail" "error" "sed -i '/^\\.rddf\\/plans\\//d' .gitignore" "现状: .rddf/plans/ 被忽略; 期望: 不应被忽略(执行契约路径)")")
  else
    issues+=("$(_emit_issue "rddf_plans_not_ignored" "pass" "info" "" "现状: .rddf/plans/ 未被忽略; 期望: 同上")")
  fi

  # ... (additional checks added in next subtasks)
  printf '[%s]\n' "$(IFS=,; echo "${issues[*]}")"
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "rddf_state_ignored|rddf_plans_not_ignored"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/check_project_setup.sh tests/integration/test_check_project_setup.bats
git commit -m "feat(check-project-setup): implement .rddf/{state,wt,plans} gitignore checks"
```

#### 1.3: Implement openspec CLI availability check

**Files:**
- Modify: `skills/_lib/check_project_setup.sh`

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_check_project_setup.bats`:
```bash
@test "check_project_setup: openspec_cli_available passes when CLI present" {
  if ! command -v openspec >/dev/null 2>&1; then
    skip "openspec CLI not installed"
  fi
  run bash -c "source '$REPO_ROOT/skills/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT' | jq '.[] | select(.name==\"openspec_cli_available\") | .status'"
  [ "$status" -eq 0 ]
  [ "$output" = "pass" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_check_project_setup.bats --filter "openspec_cli_available"`
Expected: FAIL (no `openspec_cli_available` field in output yet)

- [ ] **Step 3: Write implementation**

Add inside `check_project_setup` after the `rddf_plans_not_ignored` check, before `printf`:
```bash
  # Check 4: openspec CLI must be available
  if command -v openspec >/dev/null 2>&1 && openspec --version >/dev/null 2>&1; then
    issues+=("$(_emit_issue "openspec_cli_available" "pass" "info" "" "现状: openspec --version 成功; 期望: 同上")")
  else
    issues+=("$(_emit_issue "openspec_cli_available" "fail" "error" "参见 rdd-workflow INSTALL.md 安装 openspec CLI" "现状: openspec --version 失败; 期望: 命令可用")")
  fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "openspec_cli_available"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/check_project_setup.sh tests/integration/test_check_project_setup.bats
git commit -m "feat(check-project-setup): add openspec CLI availability check"
```

#### 1.4: Implement git HEAD existence check

**Files:**
- Modify: `skills/_lib/check_project_setup.sh`

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_check_project_setup.bats`:
```bash
@test "check_project_setup: git_head_exists passes in repo" {
  run bash -c "source '$REPO_ROOT/skills/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT' | jq '.[] | select(.name==\"git_head_exists\") | .status'"
  [ "$status" -eq 0 ]
  [ "$output" = "pass" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_check_project_setup.bats --filter "git_head_exists"`
Expected: FAIL (no `git_head_exists` field in output yet)

- [ ] **Step 3: Write implementation**

Add inside `check_project_setup` after the `openspec_cli_available` check:
```bash
  # Check 5: git HEAD must exist
  if (cd "$project_root" && git rev-parse HEAD >/dev/null 2>&1); then
    issues+=("$(_emit_issue "git_head_exists" "pass" "info" "" "现状: git rev-parse HEAD 成功; 期望: 同上")")
  else
    issues+=("$(_emit_issue "git_head_exists" "fail" "error" "git commit --allow-empty -m 'initial commit'" "现状: git rev-parse HEAD 失败; 期望: 至少存在一次提交")")
  fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "git_head_exists"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/check_project_setup.sh tests/integration/test_check_project_setup.bats
git commit -m "feat(check-project-setup): add git HEAD existence check"
```

#### 1.5: Implement large-untracked-directory check

**Files:**
- Modify: `skills/_lib/check_project_setup.sh`

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_check_project_setup.bats`:
```bash
@test "check_project_setup: large_untracked_dirs severity is safe_auto_fix or info" {
  run bash -c "source '$REPO_ROOT/skills/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT' | jq '.[] | select(.name==\"large_untracked_dirs\") | .severity'"
  [ "$status" -eq 0 ]
  [[ "$output" == "safe_auto_fix" || "$output" == "info" ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_check_project_setup.bats --filter "large_untracked_dirs"`
Expected: FAIL (no `large_untracked_dirs` field in output yet)

- [ ] **Step 3: Write implementation**

Add inside `check_project_setup` after the `git_head_exists` check:
```bash
  # Check 6: large untracked directories (>10MB) → safe_auto_fix
  local large_dirs=""
  while IFS= read -r dir; do
    local size_mb
    size_mb=$(du -sm "$project_root/$dir" 2>/dev/null | awk '{print $1}')
    if [ -n "$size_mb" ] && [ "$size_mb" -gt 10 ] 2>/dev/null; then
      large_dirs="$large_dirs $dir(${size_mb}MB)"
    fi
  done < <(cd "$project_root" && git ls-files --others --exclude-standard --directory 2>/dev/null | awk -F/ '{print $1}' | sort -u)

  if [ -n "$large_dirs" ]; then
    issues+=("$(_emit_issue "large_untracked_dirs" "warn" "safe_auto_fix" "echo '$large_dirs' | xargs -I{} sh -c 'echo {}/ >> .gitignore'" "现状: 大目录未跟踪:$large_dirs; 期望: 加入 .gitignore")")
  else
    issues+=("$(_emit_issue "large_untracked_dirs" "pass" "info" "" "现状: 无 >10MB 未跟踪目录; 期望: 同上")")
  fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "large_untracked_dirs"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/check_project_setup.sh tests/integration/test_check_project_setup.bats
git commit -m "feat(check-project-setup): add large untracked dirs check (safe_auto_fix)"
```

---

### Task 2: Add bats integration tests

**Files:**
- Modify: `tests/integration/test_check_project_setup.bats`

#### 2.1: Set up passing-project fixture

**Files:**
- Modify: `tests/integration/test_check_project_setup.bats`

- [ ] **Step 1: Write the failing test for passing-project fixture**

Ensure the file begins with `load ../test_helper` and has a per-test fixture setup. Append:
```bash
setup() {
  BATS_TEST_TMPDIR="${BATS_TEST_TMPDIR:-$BATS_TMPDIR/test-passing-$$}"
  mkdir -p "$BATS_TEST_TMPDIR"
  (cd "$BATS_TEST_TMPDIR" && git init -q && \
    echo ".rddf/state/" > .gitignore && \
    echo ".rddf/wt/" >> .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  export PASSING_FIXTURE="$BATS_TEST_TMPDIR"
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "passing project"`
Expected: PASS (existing Task 1.1 test now uses the passing fixture)

- [ ] **Step 3: Implement the fixture setup**

(Already written in Step 1 — ensure it is in the file)

- [ ] **Step 4: Run test to verify it still passes**

Run: `bats tests/integration/test_check_project_setup.bats`
Expected: all currently passing tests still pass

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_check_project_setup.bats
git commit -m "test(check-project-setup): add passing-project fixture setup()"
```

#### 2.2: Test missing `.rddf/state/` ignore rule

**Files:**
- Modify: `tests/integration/test_check_project_setup.bats`

- [ ] **Step 1: Write the failing test**

Append:
```bash
@test "check_project_setup: missing rddf_state_ignored → status=fail severity=error" {
  local fixture="$BATS_TEST_TMPDIR/missing-state"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    echo ".rddf/wt/" > .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  run bash -c "source '$REPO_ROOT/skills/_lib/check_project_setup.sh' && check_project_setup '$fixture' | jq '.[] | select(.name==\"rddf_state_ignored\") | {status, severity}'"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r .status)" = "fail" ]
  [ "$(echo "$output" | jq -r .severity)" = "error" ]
}
```

- [ ] **Step 2: Run test to verify it fails (before impl, but impl already exists)**

Run: `bats tests/integration/test_check_project_setup.bats --filter "missing rddf_state_ignored"`
Expected: PASS (helper from Task 1.2 already implements this)

- [ ] **Step 3: Implement (already done in Task 1.2)**

No new implementation needed — Task 1.2 already implements the `rddf_state_ignored` check. Confirm by reading the helper.

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "missing rddf_state_ignored"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_check_project_setup.bats
git commit -m "test(check-project-setup): add missing rddf_state_ignored case"
```

#### 2.3: Test missing `.rddf/wt/` ignore rule

**Files:**
- Modify: `tests/integration/test_check_project_setup.bats`

- [ ] **Step 1: Write the failing test**

Append:
```bash
@test "check_project_setup: missing rddf_wt_ignored fix_command suggests echo to .gitignore" {
  local fixture="$BATS_TEST_TMPDIR/missing-wt"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    echo ".rddf/state/" > .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  run bash -c "source '$REPO_ROOT/skills/_lib/check_project_setup.sh' && check_project_setup '$fixture' | jq -r '.[] | select(.name==\"rddf_wt_ignored\") | .fix_command'"
  [ "$status" -eq 0 ]
  [[ "$output" == *".rddf/wt/"* ]]
  [[ "$output" == *".gitignore"* ]]
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "missing rddf_wt_ignored"`
Expected: PASS (helper already emits correct fix_command)

- [ ] **Step 3: Implement (already done in Task 1.2)**

No new implementation — Task 1.2 already implements the `rddf_wt_ignored` check.

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "missing rddf_wt_ignored"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_check_project_setup.bats
git commit -m "test(check-project-setup): add missing rddf_wt_ignored case"
```

#### 2.4: Test `.rddf/plans/` accidentally ignored (regression)

**Files:**
- Modify: `tests/integration/test_check_project_setup.bats`

- [ ] **Step 1: Write the failing test**

Append:
```bash
@test "check_project_setup: plans regression — rddf_plans_not_ignored status=fail" {
  local fixture="$BATS_TEST_TMPDIR/plans-ignored"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    printf '.rddf/state/\n.rddf/wt/\n.rddf/plans/\n' > .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  run bash -c "source '$REPO_ROOT/skills/_lib/check_project_setup.sh' && check_project_setup '$fixture' | jq -r '.[] | select(.name==\"rddf_plans_not_ignored\") | .status'"
  [ "$status" -eq 0 ]
  [ "$output" = "fail" ]
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "plans regression"`
Expected: PASS (helper from Task 1.2 already detects regression)

- [ ] **Step 3: Implement (already done in Task 1.2)**

No new implementation — Task 1.2 already implements the regression check.

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "plans regression"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_check_project_setup.bats
git commit -m "test(check-project-setup): add plans regression case"
```

#### 2.5: Test missing `.gitignore` file

**Files:**
- Modify: `tests/integration/test_check_project_setup.bats`

- [ ] **Step 1: Write the failing test**

Append:
```bash
@test "check_project_setup: no gitignore → rddf_state_ignored fail + suggested creation command" {
  local fixture="$BATS_TEST_TMPDIR/no-gitignore"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init)
  # Remove .gitignore if it was created
  rm -f "$fixture/.gitignore"
  run bash -c "source '$REPO_ROOT/skills/_lib/check_project_setup.sh' && check_project_setup '$fixture' | jq -r '.[] | select(.name==\"rddf_state_ignored\") | {status, fix_command}'"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r .status)" = "fail" ]
  [[ "$(echo "$output" | jq -r .fix_command)" == *"echo"* ]]
  [[ "$(echo "$output" | jq -r .fix_command)" == *".gitignore"* ]]
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "no gitignore"`
Expected: PASS (helper's `if [ ! -f "$gitignore" ]` branch handles this)

- [ ] **Step 3: Implement (already done in Task 1.2)**

No new implementation — Task 1.2 already handles missing `.gitignore`.

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "no gitignore"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_check_project_setup.bats
git commit -m "test(check-project-setup): add missing .gitignore case"
```

#### 2.6: Test large untracked directory >10MB

**Files:**
- Modify: `tests/integration/test_check_project_setup.bats`

- [ ] **Step 1: Write the failing test**

Append:
```bash
@test "check_project_setup: large untracked dir → severity=safe_auto_fix" {
  local fixture="$BATS_TEST_TMPDIR/large-untracked"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    printf '.rddf/state/\n.rddf/wt/\n' > .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  # Create an untracked dir >10MB
  mkdir -p "$fixture/bigbuild"
  dd if=/dev/zero of="$fixture/bigbuild/blob" bs=1M count=11 status=none
  run bash -c "source '$REPO_ROOT/skills/_lib/check_project_setup.sh' && check_project_setup '$fixture' | jq -r '.[] | select(.name==\"large_untracked_dirs\") | .severity'"
  [ "$status" -eq 0 ]
  [ "$output" = "safe_auto_fix" ]
  rm -f "$fixture/bigbuild/blob"
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "large untracked"`
Expected: PASS (helper from Task 1.5 already emits `safe_auto_fix`)

- [ ] **Step 3: Implement (already done in Task 1.5)**

No new implementation — Task 1.5 already implements the large-untracked check.

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "large untracked"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_check_project_setup.bats
git commit -m "test(check-project-setup): add large untracked dir case"
```

#### 2.7: Add JSON schema compliance test

**Files:**
- Modify: `tests/integration/test_check_project_setup.bats`

- [ ] **Step 1: Write the failing test**

Append:
```bash
@test "check_project_setup: JSON schema — every issue has name/status/severity/fix_command/detail" {
  run bash -c "source '$REPO_ROOT/skills/_lib/check_project_setup.sh' && check_project_setup '$REPO_ROOT' | jq '.[] | has(\"name\") and has(\"status\") and has(\"severity\") and has(\"fix_command\") and has(\"detail\")' | sort -u"
  [ "$status" -eq 0 ]
  [ "$output" = "true" ]
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "JSON schema"`
Expected: PASS (helper emits all 5 fields per issue)

- [ ] **Step 3: Implement (already done across Tasks 1.2-1.5)**

No new implementation — every issue already carries all 5 fields.

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_check_project_setup.bats --filter "JSON schema"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_check_project_setup.bats
git commit -m "test(check-project-setup): add JSON schema compliance case"
```

---

### Task 3: Integrate helper into workflow entry points

**Files:**
- Modify: `skills/guide-arch/scripts/arch_env_check.sh`
- Modify: `skills/guide/scripts/scan-state.sh`
- Modify: `skills/INSTALL.md`

#### 3.1: Wire helper into `arch_env_check.sh` as hard gate

**Files:**
- Modify: `skills/guide-arch/scripts/arch_env_check.sh`

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_arch_env_check_extraction.bats`:
```bash
@test "arch_env_check: setup gate — failing project returns 1" {
  local fixture="$BATS_TEST_TMPDIR/failing-setup"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    printf 'build/\n' > .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  # Ensure rdd_workflow is loadable; source helper and gate function from arch_env_check.sh
  run bash -c "source '$REPO_ROOT/skills/guide-arch/scripts/arch_env_check.sh' && run_arch_env_setup_gate '$fixture'"
  [ "$status" -ne 0 ]
  [[ "$output" == *".rddf/state/"* ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_arch_env_check.bats --filter "setup gate" 2>/dev/null || echo "run bats tests/integration/test_arch_env_check.bats"`
Expected: FAIL (`run_arch_env_setup_gate` function not defined yet)

- [ ] **Step 3: Implement**

Append to `skills/guide-arch/scripts/arch_env_check.sh`:
```bash
# Hard gate: check project setup. Returns 1 if any error-severity issue.
run_arch_env_setup_gate() {
  local project_root="${PROJECT_ROOT:-$(pwd)}"
  if [ -f "${project_root}/skills/_lib/check_project_setup.sh" ]; then
    source "${project_root}/skills/_lib/check_project_setup.sh"
  else
    source "$REPO_ROOT/skills/_lib/check_project_setup.sh" 2>/dev/null || return 0
  fi
  local issues
  issues=$(check_project_setup "$project_root")
  local fatal
  fatal=$(echo "$issues" | jq -r '.[] | select(.severity=="error" and .status=="fail") | "\(.name)|\(.detail)|\(.fix_command)"')
  if [ -n "$fatal" ]; then
    echo "❌ 项目设置检查未通过 (project-setup-check):"
    while IFS='|' read -r name detail fix; do
      echo "  - $name"
      echo "    $detail"
      echo "    fix: $fix"
    done <<< "$fatal"
    return 1
  fi
  return 0
}
```

Then in the main `run_arch_env_check` function, append near the end before `echo "📋 现有 ADR..."`:
```bash
  if ! run_arch_env_setup_gate "${PROJECT_ROOT:-$REPO_ROOT}"; then
    return 1
  fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_arch_env_check_extraction.bats --filter "setup gate"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/guide-arch/scripts/arch_env_check.sh tests/integration/test_arch_env_check_extraction.bats
git commit -m "feat(guide-arch): wire check_project_setup as Phase 1 hard gate"
```

#### 3.2: Replace legacy inline large-untracked block in `scan-state.sh`

**Files:**
- Modify: `skills/guide/scripts/scan-state.sh`

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_scan_state.bats` (or create if missing):
```bash
@test "scan_state: sources check_project_setup and removes legacy LARGE_DIRS block" {
  grep -q 'check_project_setup' "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
  ! grep -q 'LARGE_DIRS' "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
}

@test "scan_state: setup issues printed but never block (exit 0)" {
  local fixture="$BATS_TEST_TMPDIR/scan-fixture"
  mkdir -p "$fixture" && (cd "$fixture" && git init -q && \
    printf 'build/\n' > .gitignore && \
    git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
  run bash -c "cd '$fixture' && source '$REPO_ROOT/skills/guide/scripts/scan-state.sh' && scan_state"
  [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `grep -n "check_project_setup" skills/guide/scripts/scan-state.sh && ! grep -q "LARGE_DIRS" skills/guide/scripts/scan-state.sh`
Expected: grep returns no match (helper not yet wired in)

- [ ] **Step 3: Implement**

Remove the legacy inline `du -sm`/`LARGE_DIRS` block in `skills/guide/scripts/scan-state.sh`. Then add at the top of the `scan_state` function:
```bash
  # Pre-menu setup analysis (non-blocking)
  local _lib_dir
  _lib_dir=$(cd "$REPO_ROOT/skills/_lib" 2>/dev/null && pwd || echo "$REPO_ROOT/skills/_lib")
  if [ -f "$_lib_dir/check_project_setup.sh" ]; then
    source "$_lib_dir/check_project_setup.sh"
    local _setup_issues
    _setup_issues=$(check_project_setup "${PROJECT_ROOT:-$REPO_ROOT}" 2>/dev/null || echo '[]')
    echo ""
    echo "🔧 项目设置检查 (safe_auto_fix, 不阻塞):"
    echo "$_setup_issues" | jq -r '.[] | "  - \(.name): \(.status) — \(.detail)\n    fix: \(.fix_command)"' 2>/dev/null || true
  fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `grep -n "check_project_setup" skills/guide/scripts/scan-state.sh && ! grep -q "LARGE_DIRS" skills/guide/scripts/scan-state.sh`
Expected: exit 0 (helper wired, LARGE_DIRS removed)

- [ ] **Step 5: Commit**

```bash
git add skills/guide/scripts/scan-state.sh tests/integration/test_scan_state.bats
git commit -m "refactor(guide): replace inline LARGE_DIRS block with check_project_setup analysis"
```

#### 3.3: Add Section 5 "项目设置检查" to `INSTALL.md`

**Files:**
- Modify: `skills/INSTALL.md`

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_install_md.bats` (or create):
```bash
@test "INSTALL.md: contains 项目设置检查 section" {
  grep -q '项目设置检查' "$REPO_ROOT/skills/INSTALL.md"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `grep -n "项目设置检查" skills/INSTALL.md`
Expected: no match (section not yet added)

- [ ] **Step 3: Implement**

Append to `skills/INSTALL.md`:
```markdown
## 5. 项目设置检查

安装完成后,执行项目设置检查以确认 `.gitignore` 已正确配置:

\`\`\`bash
source skills/_lib/check_project_setup.sh
issues=$(check_project_setup "$(pwd)")
echo "$issues" | jq -r '.[] | "  \(if .status == "pass" then "✅" else "❌" end) \(.name): \(.detail)"'
\`\`\`

检查项:`rddf_state_ignored` / `rddf_wt_ignored` / `rddf_plans_not_ignored` /
`openspec_cli_available` / `git_head_exists` / `large_untracked_dirs`。

无论结果如何,安装流程均不中断。如有 ❌,运行对应 `fix_command` 后重新执行。
```

- [ ] **Step 4: Run test to verify it passes**

Run: `grep -n "项目设置检查" skills/INSTALL.md`
Expected: match found

- [ ] **Step 5: Commit**

```bash
git add skills/INSTALL.md tests/integration/test_install_md.bats
git commit -m "docs(INSTALL): add Section 5 项目设置检查 checklist"
```

---

### Task 4: Update documentation and refactor duplicated assertions

**Files:**
- Modify: `USAGE.md`
- Modify: `docs/v2-workflow-overview.md`
- Modify: `tests/integration/test_plan_review_phase.bats`

#### 4.1: Update `USAGE.md` 常见陷阱

**Files:**
- Modify: `USAGE.md`

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_usage_md.bats`:
```bash
@test "USAGE.md: mentions fix_command in 常见陷阱" {
  grep -q 'fix_command' "$REPO_ROOT/USAGE.md"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `grep -n "fix_command" USAGE.md`
Expected: no match

- [ ] **Step 3: Implement**

In `USAGE.md` "## 常见陷阱" section, append:
```markdown
- **`guide-arch` 首次因 `.gitignore` 失败**:运行检查器打印的 `fix_command` 后重新执行。
```

- [ ] **Step 4: Run test to verify it passes**

Run: `grep -n "fix_command" USAGE.md`
Expected: match found

- [ ] **Step 5: Commit**

```bash
git add USAGE.md tests/integration/test_usage_md.bats
git commit -m "docs(USAGE): add fix_command pitfall note for first guide-arch failure"
```

#### 4.2: Update `docs/v2-workflow-overview.md`

**Files:**
- Modify: `docs/v2-workflow-overview.md`

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_workflow_overview_md.bats`:
```bash
@test "docs/v2-workflow-overview.md: mentions project-setup check" {
  grep -q 'project-setup' "$REPO_ROOT/docs/v2-workflow-overview.md"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `grep -n "project-setup" docs/v2-workflow-overview.md`
Expected: no match

- [ ] **Step 3: Implement**

In `docs/v2-workflow-overview.md`, append a paragraph:
```markdown
## 项目设置检查

`check_project_setup` 在 `guide-arch` Phase 1 入口硬阻断任何 `severity=error` 的设置问题
(典型为缺失 `.rddf/state/` / `.rddf/wt/` 忽略规则),并在 `guide` 推荐器和 `INSTALL.md`
Section 5 中软展示 `safe_auto_fix` 候选。修复方式:运行失败信息中打印的 `fix_command`,
然后重新执行当前阶段。
```

- [ ] **Step 4: Run test to verify it passes**

Run: `grep -n "project-setup" docs/v2-workflow-overview.md`
Expected: match found

- [ ] **Step 5: Commit**

```bash
git add docs/v2-workflow-overview.md tests/integration/test_workflow_overview_md.bats
git commit -m "docs(workflow-overview): describe project-setup check triggers"
```

#### 4.3: Refactor `test_plan_review_phase.bats:62-66`

**Files:**
- Modify: `tests/integration/test_plan_review_phase.bats`

- [ ] **Step 1: Write the failing test (no-op since refactor only)**

The existing test at lines 62-66:
```bash
@test "plan_review: validate_report is gitignored (state file lives under .rddf/)" {
  # validate_report writes to .rddf/state/openspec-validate.json
  [ -f ".gitignore" ]
  grep -qE '^\.rddf/state/' ".gitignore" || grep -qE '^\.rddf/' ".gitignore"
}
```

Replace with assertion through the helper:
```bash
@test "plan_review: validate_report is gitignored (via check_project_setup helper)" {
  source "$REPO_ROOT/skills/_lib/check_project_setup.sh"
  run check_project_setup "$REPO_ROOT"
  [ "$status" -eq 0 ]
  echo "$output" | jq -e '.[] | select(.name=="rddf_state_ignored") | .status == "pass"' >/dev/null
}
```

- [ ] **Step 2: Run test to verify it fails (before refactor)**

Run: `bats tests/integration/test_plan_review_phase.bats --filter "validate_report is gitignored"`
Expected: PASS with old implementation (verifies old behavior is still in place)

- [ ] **Step 3: Implement refactor**

Edit `tests/integration/test_plan_review_phase.bats` lines 62-66 with the replacement above.

- [ ] **Step 4: Run test to verify it passes**

Run: `sed -n '60,70p' tests/integration/test_plan_review_phase.bats`
Expected: line range shows the new test body referencing `check_project_setup`

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_plan_review_phase.bats
git commit -m "refactor(test): assert plan_review gitignore via check_project_setup helper"
```

---

### Task 5: Acceptance validation

**Files:**
- (verification only — no production changes)

#### 5.1: Run new bats suite

**Files:**
- (read-only verification)

- [ ] **Step 1: Prepare validation**

No file changes needed for this verification step.

- [ ] **Step 2: Run the suite**

Run: `bats tests/integration/test_check_project_setup.bats`
Expected: all cases PASS

- [ ] **Step 3: Confirm pass**

If any case fails, identify the failing case and fix the underlying implementation, then re-run. Do not mark this task complete until exit code is 0.

- [ ] **Step 4: Re-run to confirm stability**

Run: `bats tests/integration/test_check_project_setup.bats`
Expected: PASS (idempotent)

- [ ] **Step 5: No commit needed (verification only)**

#### 5.2: Run Python tests for no regressions

**Files:**
- (read-only verification)

- [ ] **Step 1: Prepare validation**

No file changes needed.

- [ ] **Step 2: Run Python tests**

Run: `python3 -m pytest tests/ -q --tb=short`
Expected: exit code 0; no NEW failures (pre-existing failures unrelated to this change are acceptable but should be noted).

- [ ] **Step 3: Confirm no regressions**

If `test_check_project_setup` or related tests fail, fix and re-run. Pre-existing failures in unrelated tests should be flagged but not block this task.

- [ ] **Step 4: Re-run to confirm stability**

Run: `python3 -m pytest tests/ -q --tb=short`
Expected: same result as Step 2

- [ ] **Step 5: No commit needed (verification only)**

#### 5.3: Run `npm test` for bats smoke/static/worktree subsets

**Files:**
- (read-only verification)

- [ ] **Step 1: Prepare validation**

No file changes needed.

- [ ] **Step 2: Run npm test**

Run: `npm test`
Expected: exit code 0 (smoke + static + git-worktree subsets all pass)

- [ ] **Step 3: Confirm pass**

If any subset fails, fix the underlying issue and re-run.

- [ ] **Step 4: Re-run to confirm stability**

Run: `npm test`
Expected: PASS

- [ ] **Step 5: No commit needed (verification only)**

#### 5.4: Run `openspec validate check-project-setup --strict`

**Files:**
- (read-only verification)

- [ ] **Step 1: Prepare validation**

No file changes needed.

- [ ] **Step 2: Run openspec validate**

Run: `openspec validate check-project-setup --strict`
Expected: exit code 0; "Validation passed" output

- [ ] **Step 3: Confirm pass**

If validation fails, fix the change artifacts and re-run.

- [ ] **Step 4: Re-run to confirm stability**

Run: `openspec validate check-project-setup --strict`
Expected: PASS

- [ ] **Step 5: No commit needed (verification only)**

#### 5.5: Run `openspec status` and confirm all artifacts complete

**Files:**
- (read-only verification)

- [ ] **Step 1: Prepare validation**

No file changes needed.

- [ ] **Step 2: Run openspec status**

Run: `openspec status --change check-project-setup --json | jq '.isComplete'`
Expected: `true`

- [ ] **Step 3: Confirm completeness**

If `false`, identify the missing artifact and create it (likely tasks.md checkboxes not all checked).

- [ ] **Step 4: Re-run to confirm stability**

Run: `openspec status --change check-project-setup --json | jq '.isComplete'`
Expected: `true`

- [ ] **Step 5: No commit needed (verification only)**

#### 5.6: Verify helper runtime under 50ms

**Files:**
- (read-only verification)

- [ ] **Step 1: Prepare validation**

No file changes needed.

- [ ] **Step 2: Measure runtime**

Run: `source skills/_lib/check_project_setup.sh && time check_project_setup /workspace/project/rdd-workflow >/dev/null`
Expected: real < 0m0.050s (50ms)

- [ ] **Step 3: Confirm under threshold**

If runtime exceeds 50ms, identify the slow check (likely `du -sm` over many files) and optimize.

- [ ] **Step 4: Re-run to confirm stability**

Run: `source skills/_lib/check_project_setup.sh && time check_project_setup /workspace/project/rdd-workflow >/dev/null`
Expected: same result, under 50ms

- [ ] **Step 5: No commit needed (verification only)**

#### 5.7: Manual `guide-arch` Phase 1 e2e against three fixtures

**Files:**
- (read-only verification; record results in change execution log)

- [ ] **Step 1: Prepare three fixtures**

```bash
TMP_BASE=$(mktemp -d)
# Fixture A: correctly configured
mkdir -p "$TMP_BASE/passing" && (cd "$TMP_BASE/passing" && git init -q && \
  printf '.rddf/state/\n.rddf/wt/\n' > .gitignore && \
  git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
# Fixture B: missing .rddf/state/
mkdir -p "$TMP_BASE/missing" && (cd "$TMP_BASE/missing" && git init -q && \
  printf '.rddf/wt/\n' > .gitignore && \
  git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
# Fixture C: incorrectly ignored .rddf/plans/
mkdir -p "$TMP_BASE/plans-blocked" && (cd "$TMP_BASE/plans-blocked" && git init -q && \
  printf '.rddf/state/\n.rddf/wt/\n.rddf/plans/\n' > .gitignore && \
  git add .gitignore && git -c user.email=t@t -c user.name=t commit -q -m init)
```

- [ ] **Step 2: Run e2e against fixture A (expect exit 0)**

Run: `cd "$TMP_BASE/passing" && bash -c "source '$REPO_ROOT/skills/guide-arch/scripts/arch_env_check.sh' && run_arch_env_check; echo EXIT=\$?"`
Expected: `EXIT=0`

- [ ] **Step 3: Run e2e against fixture B (expect non-zero)**

Run: `cd "$TMP_BASE/missing" && bash -c "source '$REPO_ROOT/skills/guide-arch/scripts/arch_env_check.sh' && run_arch_env_check; echo EXIT=\$?"`
Expected: `EXIT` non-zero; stdout contains the `.rddf/state/` `fix_command`

- [ ] **Step 4: Run e2e against fixture C (expect non-zero)**

Run: `cd "$TMP_BASE/plans-blocked" && bash -c "source '$REPO_ROOT/skills/guide-arch/scripts/arch_env_check.sh' && run_arch_env_check; echo EXIT=\$?"`
Expected: `EXIT` non-zero; stdout contains the `.rddf/plans/` `fix_command` (the `sed -i` removal command)

- [ ] **Step 5: Record results**

Append to the change execution log:
```
5.7 e2e (manual):
- fixture A (passing):        exit=0
- fixture B (missing state):  exit=<non-zero>, printed fix_command for .rddf/state/
- fixture C (plans blocked):  exit=<non-zero>, printed fix_command for .rddf/plans/
```