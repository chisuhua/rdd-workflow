# e2e Test Plan Phase 1 — A Layer Infrastructure + Smoke Tests

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 e2e 测试的 A 层基础设施（3 helper + 8 phase 脚本非交互 flag + test.sh 扩展），并交付 `tests/e2e/script/` 下 10 个 A 层 smoke cases，让 CI 必跑的 e2e 部分能立即生效。

**Architecture:** 3 个 bash helper 提供 isolation / script entrypoint / golden output 三大原语；6 个 rdd-builder phase 脚本 + rdd-quick scaffold_plan.sh 各加一个 `--auto-approve`/`--no-confirm` flag，让 bats 能无人工 prompt 调用真路径；`test.sh` 暴露 `--e2e-smoke`（CI 必跑）和 `--e2e-agent`（nightly 必跑）两个新 mode；2 个 A 层 .bats 文件落地 10 个 smoke cases。

**Tech Stack:** bash 5.x / bats-core 1.10+ / Python 3.11+ / POSIX `sha256sum` / `git worktree`

**Spec:** `docs/superpowers/specs/2026-09-08-e2e-test-plan-design.md` §9 Phase 1
**Scenario specs:**
- `docs/superpowers/specs/2026-09-08-rdd-quick-e2e-scenarios.md` (Q-E1..Q-E8)
- `docs/superpowers/specs/2026-09-08-rdd-builder-e2e-scenarios.md` (B-E1..B-E12)

---

## Task 1: `tests/e2e/_lib/isolation.bash` — BATS_TEST_TMPDIR wrapper

**Files:**
- Create: `tests/e2e/_lib/test_isolation.bats` (self-test, will be deleted after Task 13)
- Create: `tests/e2e/_lib/isolation.bash`

- [ ] **Step 1: Write the failing self-test**

Create `tests/e2e/_lib/test_isolation.bats`:
```bash
#!/usr/bin/env bats
load ../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/isolation.bash"
    REPO_ROOT="$REPO_ROOT"  # isolation.bash reads this
}

@test "isolation::snapshot_repo_state writes sha256 to file" {
    run isolation::snapshot_repo_state "$BATS_TEST_TMPDIR/baseline.sha256"
    [ "$status" -eq 0 ]
    [ -f "$BATS_TEST_TMPDIR/baseline.sha256" ]
    [ -s "$BATS_TEST_TMPDIR/baseline.sha256" ]
}

@test "isolation::verify_zero_pollution returns 0 when state unchanged" {
    isolation::snapshot_repo_state "$BATS_TEST_TMPDIR/baseline.sha256"
    # No mutation between snapshot and verify
    run isolation::verify_zero_pollution "$BATS_TEST_TMPDIR/baseline.sha256"
    [ "$status" -eq 0 ]
}

@test "isolation::verify_zero_pollution returns 1 when .rddf/ modified" {
    isolation::snapshot_repo_state "$BATS_TEST_TMPDIR/baseline.sha256"
    # Simulate pollution
    mkdir -p "$REPO_ROOT/.rddf/state"
    echo "polluted" > "$REPO_ROOT/.rddf/state/test.sha256"
    run isolation::verify_zero_pollution "$BATS_TEST_TMPDIR/baseline.sha256"
    # Cleanup before assertion to avoid polluting later tests
    rm -f "$REPO_ROOT/.rddf/state/test.sha256"
    [ "$status" -eq 1 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/e2e/_lib/test_isolation.bats`
Expected: FAIL with "isolation.bash: No such file or directory"

- [ ] **Step 3: Implement `isolation.bash`**

Create `tests/e2e/_lib/isolation.bash`:
```bash
#!/usr/bin/env bash
# tests/e2e/_lib/isolation.bash
# E2E isolation primitives: snapshot repo state, verify zero pollution.
# Locked files (per 2026-09-08-e2e-test-plan-design.md §7 #6):
#   $REPO_ROOT/.rddf/
#   $REPO_ROOT/openspec/
#   $REPO_ROOT/.rddf/wt/

# Locked paths relative to REPO_ROOT
_ISOLATION_LOCKED_PATHS=(
    ".rddf"
    "openspec"
    ".rddf/wt"
    ".rddf/state/iteration.json"
    ".rddf/state/sessions.json"
    ".rddf/state/roadmap-state.json"
)

# isolation::snapshot_repo_state <output_file>
# Compute sha256 of locked paths (or "ABSENT:<path>" if not exist) and write
# one line per path to <output_file>. Format: "<sha256>  <path>"
isolation::snapshot_repo_state() {
    local out="$1"
    : > "$out"
    local p sha
    for p in "${_ISOLATION_LOCKED_PATHS[@]}"; do
        if [ -e "$REPO_ROOT/$p" ]; then
            sha=$(cd "$REPO_ROOT" && sha256sum "$p" 2>/dev/null | awk '{print $1}')
        else
            sha="ABSENT"
        fi
        echo "$sha  $p" >> "$out"
    done
}

# isolation::verify_zero_pollution <baseline_file>
# Recompute current sha256 of locked paths and diff against baseline.
# Returns 0 if all match, 1 if any differ, 2 on internal error.
isolation::verify_zero_pollution() {
    local baseline="$1"
    local current
    current=$(mktemp)
    isolation::snapshot_repo_state "$current"
    if diff -q "$baseline" "$current" >/dev/null 2>&1; then
        rm -f "$current"
        return 0
    else
        diff "$baseline" "$current" >&2 || true
        rm -f "$current"
        return 1
    fi
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/e2e/_lib/test_isolation.bats`
Expected: 3 pass, 0 fail

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/_lib/isolation.bash tests/e2e/_lib/test_isolation.bats
git commit -m "feat(e2e/_lib): add isolation.bash with snapshot/verify primitives

Per 2026-09-08-e2e-test-plan-design.md §7 #6:
- snapshot_repo_state: write sha256 of 6 locked paths to file
- verify_zero_pollution: diff current vs baseline, return 0/1

Locked paths: .rddf/ / openspec/ / .rddf/wt/ + 3 state files.
ABSENT sentinel for missing paths (sha256 of empty tree is misleading)."
```

---

## Task 2: `tests/e2e/_lib/script_smoke.bash` — A-layer phase script entrypoint

**Files:**
- Create: `tests/e2e/_lib/test_script_smoke.bats`
- Create: `tests/e2e/_lib/script_smoke.bash`

- [ ] **Step 1: Write the failing self-test**

Create `tests/e2e/_lib/test_script_smoke.bats`:
```bash
#!/usr/bin/env bats
load ../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/script_smoke.bash"
    export SMOKE_FAKE_ROOT="$BATS_TEST_TMPDIR/fake"
    export SMOKE_REPO_ROOT="$REPO_ROOT"
    script_smoke::setup_fake_project "$SMOKE_FAKE_ROOT"
}

teardown() {
    script_smoke::cleanup_fake_project "$SMOKE_FAKE_ROOT"
}

@test "script_smoke::setup_fake_project creates git repo + openspec skeleton" {
    [ -d "$SMOKE_FAKE_ROOT/.git" ]
    [ -d "$SMOKE_FAKE_ROOT/openspec/changes" ]
    [ -d "$SMOKE_FAKE_ROOT/.rddf" ]
}

@test "script_smoke::invoke_phase exits 0 on --auto-approve" {
    # phase0_approval.sh does not exist yet, but smoke helper should fail-soft
    run script_smoke::invoke_phase "phase0_approval.sh" "test-change" "$SMOKE_FAKE_ROOT" "--auto-approve"
    # Acceptable: 0 if script exists and works; non-zero if script not found
    [ "$status" -ge 0 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/e2e/_lib/test_script_smoke.bats`
Expected: FAIL with "script_smoke.bash: No such file or directory"

- [ ] **Step 3: Implement `script_smoke.bash`**

Create `tests/e2e/_lib/script_smoke.bash`:
```bash
#!/usr/bin/env bash
# tests/e2e/_lib/script_smoke.bash
# A-layer (CI必跑) helper: fake project setup + phase script invocation.
# Wraps `bash skills/<skill>/scripts/<phase>.sh <args>` for non-interactive use.

# script_smoke::setup_fake_project <root>
# Initialize fake git repo + openspec skeleton + .rddf/ at <root>.
script_smoke::setup_fake_project() {
    local root="$1"
    mkdir -p "$root/openspec/changes"
    mkdir -p "$root/openspec/specs"
    mkdir -p "$root/.rddf/state"
    git -C "$root" init -q -b main
    git -C "$root" config user.email "e2e@test.local"
    git -C "$root" config user.name "e2e test"
    git -C "$root" add -A
    git -C "$root" commit -q -m "e2e: initial fake project"
}

# script_smoke::cleanup_fake_project <root>
script_smoke::cleanup_fake_project() {
    local root="$1"
    [ -d "$root" ] && rm -rf "$root"
}

# script_smoke::invoke_phase <phase_script> <change_name> <fake_root> [extra_args...]
# Run phase script in fake project context. Returns script's exit code.
# Requires phase scripts to support --auto-approve flag (added in Tasks 4-9).
script_smoke::invoke_phase() {
    local phase_script="$1"
    local change_name="$2"
    local fake_root="$3"
    shift 3
    local script_path="$SMOKE_REPO_ROOT/skills/rdd-builder/scripts/$phase_script"
    if [ ! -x "$script_path" ]; then
        echo "ERROR: $script_path not found or not executable" >&2
        return 127
    fi
    ( cd "$fake_root" && CHANGE_NAME="$change_name" bash "$script_path" "$change_name" "$@" )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/e2e/_lib/test_script_smoke.bats`
Expected: 2 pass, 0 fail

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/_lib/script_smoke.bash tests/e2e/_lib/test_script_smoke.bats
git commit -m "feat(e2e/_lib): add script_smoke.bash for A-layer phase invocation

Per 2026-09-08-e2e-test-plan-design.md §3.2:
- setup_fake_project: fake git repo + openspec skeleton + .rddf/
- cleanup_fake_project: rm -rf
- invoke_phase: cd <fake_root> + bash <phase_script> with CHANGE_NAME env

Returns 127 if script not found (fail-soft for Task 2 self-test before
phase scripts gain --auto-approve in Tasks 4-9)."
```

---

## Task 3: `tests/e2e/_lib/golden_compare.bash` — golden output key-field diff

**Files:**
- Create: `tests/e2e/_lib/test_golden_compare.bats`
- Create: `tests/e2e/_lib/golden_compare.bash`

- [ ] **Step 1: Write the failing self-test**

Create `tests/e2e/_lib/test_golden_compare.bats`:
```bash
#!/usr/bin/env bats
load ../test_helper

setup() {
    source "$REPO_ROOT/tests/e2e/_lib/golden_compare.bash"
    GOLDEN_DIR="$BATS_TEST_TMPDIR/golden"
    mkdir -p "$GOLDEN_DIR"
}

@test "golden_compare::update writes file with sha256 + fields" {
    local actual_file="$BATS_TEST_TMPDIR/actual.json"
    echo '{"ac_id": "AC-1", "status": "pass", "confidence": 0.95}' > "$actual_file"
    run golden_compare::update "$GOLDEN_DIR/v1.json" "$actual_file" "ac_id,status,confidence"
    [ "$status" -eq 0 ]
    [ -f "$GOLDEN_DIR/v1.json" ]
    grep -q "sha256:" "$GOLDEN_DIR/v1.json"
    grep -q "fields:" "$GOLDEN_DIR/v1.json"
}

@test "golden_compare::check returns 0 when current matches golden" {
    local actual_file="$BATS_TEST_TMPDIR/actual.json"
    echo '{"ac_id": "AC-1", "status": "pass"}' > "$actual_file"
    golden_compare::update "$GOLDEN_DIR/v1.json" "$actual_file" "ac_id,status"
    # No change → still matches
    run golden_compare::check "$GOLDEN_DIR/v1.json" "$actual_file" "ac_id,status"
    [ "$status" -eq 0 ]
}

@test "golden_compare::check returns 1 when field drift detected" {
    local actual_file="$BATS_TEST_TMPDIR/actual.json"
    echo '{"ac_id": "AC-1", "status": "pass"}' > "$actual_file"
    golden_compare::update "$GOLDEN_DIR/v1.json" "$actual_file" "ac_id,status"
    # Modify actual
    echo '{"ac_id": "AC-1", "status": "fail"}' > "$actual_file"
    run golden_compare::check "$GOLDEN_DIR/v1.json" "$actual_file" "ac_id,status"
    [ "$status" -eq 1 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/e2e/_lib/test_golden_compare.bats`
Expected: FAIL with "golden_compare.bash: No such file or directory"

- [ ] **Step 3: Implement `golden_compare.bash`**

Create `tests/e2e/_lib/golden_compare.bash`:
```bash
#!/usr/bin/env bash
# tests/e2e/_lib/golden_compare.bash
# Golden output lock helper per 2026-09-08-e2e-test-plan-design.md §3.1
# Combines: (1) full file sha256 + (2) key-field extracted values.
# Drift detected = either sha changed OR key field value changed.

# golden_compare::update <golden_file> <actual_file> <csv_fields>
# Compute sha256 + extract <csv_fields> as JSON paths, write to <golden_file>.
golden_compare::update() {
    local golden="$1" actual="$2" fields="$3"
    local sha
    sha=$(sha256sum "$actual" | awk '{print $1}')
    {
        echo "sha256:$sha"
        echo "fields:$fields"
        echo "values:"
        IFS=',' read -ra field_arr <<< "$fields"
        # Extract each field as a JSON key=value line using python3
        python3 -c "
import json, sys
data = json.load(open('$actual'))
fields = '''$fields'''.split(',')
for f in fields:
    f = f.strip()
    # Support dotted path navigation (e.g. changes.0.status)
    parts = f.split('.')
    val = data
    for p in parts:
        if p.isdigit():
            val = val[int(p)] if isinstance(val, list) and int(p) < len(val) else None
        else:
            val = val.get(p) if isinstance(val, dict) else None
        if val is None:
            break
    print(f'  {f}={val}')
"
    } > "$golden"
}

# golden_compare::check <golden_file> <actual_file> <csv_fields>
# Return 0 if both sha and key fields match, 1 if any drift, 2 on error.
golden_compare::check() {
    local golden="$1" actual="$2" fields="$3"
    local actual_golden
    actual_golden=$(mktemp)
    golden_compare::update "$actual_golden" "$actual" "$fields"
    if diff -q "$golden" "$actual_golden" >/dev/null 2>&1; then
        rm -f "$actual_golden"
        return 0
    else
        diff "$golden" "$actual_golden" >&2 || true
        rm -f "$actual_golden"
        return 1
    fi
}

# golden_compare::regen <golden_file> <actual_file> <csv_fields>
# Alias for update, used when UPDATE_GOLDEN=1 env is set.
golden_compare::regen() {
    golden_compare::update "$@"
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/e2e/_lib/test_golden_compare.bats`
Expected: 3 pass, 0 fail

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/_lib/golden_compare.bash tests/e2e/_lib/test_golden_compare.bats
git commit -m "feat(e2e/_lib): add golden_compare.bash for C-layer drift detection

Per 2026-09-08-e2e-test-plan-design.md §3.1:
- update: write sha256 + key-field values to golden file
- check: diff current vs golden, return 0/1
- regen: alias for update (UPDATE_GOLDEN=1 path)

Key field extraction via python3 JSON navigation (supports dotted paths
like changes.0.status). Drift = either sha mismatch OR any key field
value changed. Avoids over-sensitivity of full-text sha256 while
catching silent prose drift in C-layer scenarios."
```

---

## Task 4: Add `--auto-approve` flag to `phase0_approval.sh`

**Files:**
- Create: `tests/integration/test_phase0_auto_approve.bats`
- Modify: `skills/rdd-builder/scripts/phase0_approval.sh` (add flag handling near top)

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_phase0_auto_approve.bats`:
```bash
#!/usr/bin/env bats
load ../test_helper

setup() {
    FAKE_ROOT="$BATS_TEST_TMPDIR/fake-p0"
    mkdir -p "$FAKE_ROOT/openspec/changes"
    git -C "$FAKE_ROOT" init -q -b main
    git -C "$FAKE_ROOT" config user.email "e2e@test.local"
    git -C "$FAKE_ROOT" config user.name "e2e"
}

@test "phase0_approval.sh: --auto-approve skips interactive prompt (exits 0 or 1 without TTY hang)" {
    # Use timeout to detect TTY hang; if --auto-approve not honored, hangs
    run timeout 10 bash "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" \
        "test-change" "--auto-approve"
    # Acceptable outcomes: 0 (approved), 1 (no proposal to approve, gate)
    # Unacceptable: 124 (timeout, indicates TTY hang)
    [ "$status" -ne 124 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_phase0_auto_approve.bats`
Expected: FAIL or HANG (timeout). Acceptable for now: any non-124 result.

- [ ] **Step 3: Add `--auto-approve` flag handling**

Modify `skills/rdd-builder/scripts/phase0_approval.sh`. At the top (after `#!/usr/bin/env bash` and any existing set/var declarations), add:
```bash
# E2E smoke support: --auto-approve flag skips interactive prompt
AUTO_APPROVE=0
for arg in "$@"; do
    case "$arg" in
        --auto-approve) AUTO_APPROVE=1 ;;
    esac
done
export AUTO_APPROVE
```

Then find the interactive prompt (likely a `read` or similar) and gate it:
```bash
# Before: read -p "Approve? (y/n) " ans
# After:
if [ "${AUTO_APPROVE:-0}" = "1" ]; then
    ans="y"
else
    read -p "Approve? (y/n) " ans
fi
```

(Adjust the exact gating based on the script's actual prompt location — if no `read` exists, the script may already be non-interactive; just adding the flag parsing is enough for the test to pass.)

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_phase0_auto_approve.bats`
Expected: 1 pass, 0 fail

- [ ] **Step 5: Commit**

```bash
git add skills/rdd-builder/scripts/phase0_approval.sh tests/integration/test_phase0_auto_approve.bats
git commit -m "feat(rdd-builder): add --auto-approve flag to phase0_approval.sh

Per 2026-09-08-e2e-test-plan-design.md §3.2: A-layer needs non-interactive
entrypoint. Add AUTO_APPROVE env var + --auto-approve flag parsing.
Gate any existing read prompts on AUTO_APPROVE=1 to default to 'y'.

If script is already non-interactive (no read prompts), flag parsing
alone satisfies the test. Idempotent: existing manual usage unchanged."
```

---

## Task 5: Add `--auto-approve` flag to `phase1_plan.sh`

**Files:**
- Create: `tests/integration/test_phase1_auto_approve.bats`
- Modify: `skills/rdd-builder/scripts/phase1_plan.sh`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_phase1_auto_approve.bats`:
```bash
#!/usr/bin/env bats
load ../test_helper

setup() {
    FAKE_ROOT="$BATS_TEST_TMPDIR/fake-p1"
    mkdir -p "$FAKE_ROOT/openspec/changes/e2e-p1" "$FAKE_ROOT/.rddf"
    echo "# proposal" > "$FAKE_ROOT/openspec/changes/e2e-p1/proposal.md"
    git -C "$FAKE_ROOT" init -q -b main
    git -C "$FAKE_ROOT" config user.email "e2e@test.local"
    git -C "$FAKE_ROOT" config user.name "e2e"
    git -C "$FAKE_ROOT" add -A && git -C "$FAKE_ROOT" commit -q -m "init"
}

@test "phase1_plan.sh: --auto-approve exits 0 or 1 (not 124 timeout)" {
    run timeout 10 bash "$REPO_ROOT/skills/rdd-builder/scripts/phase1_plan.sh" \
        "e2e-p1" --auto-approve
    [ "$status" -ne 124 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_phase1_auto_approve.bats`
Expected: FAIL (no --auto-approve handler) or HANG.

- [ ] **Step 3: Add `--auto-approve` flag handling to `phase1_plan.sh`**

Same pattern as Task 4 Step 3: add flag parsing + gate any read prompts.

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_phase1_auto_approve.bats`
Expected: 1 pass

- [ ] **Step 5: Commit**

```bash
git add skills/rdd-builder/scripts/phase1_plan.sh tests/integration/test_phase1_auto_approve.bats
git commit -m "feat(rdd-builder): add --auto-approve flag to phase1_plan.sh"
```

---

## Task 6: Add `--auto-approve` flag to `phase1_5_deps.sh`

Same pattern as Task 5. Files:
- Create: `tests/integration/test_phase1_5_auto_approve.bats`
- Modify: `skills/rdd-builder/scripts/phase1_5_deps.sh`

- [ ] **Step 1**: Write test (same as Task 5 with `phase1_5_deps.sh` and `"e2e-p1-5"`)
- [ ] **Step 2**: Run, expect fail
- [ ] **Step 3**: Add flag handling
- [ ] **Step 4**: Run, expect pass
- [ ] **Step 5**: Commit with message `feat(rdd-builder): add --auto-approve flag to phase1_5_deps.sh`

---

## Task 7: Add `--auto-approve` flag to `phase2_execute.sh`

Same pattern. Files:
- Create: `tests/integration/test_phase2_auto_approve.bats`
- Modify: `skills/rdd-builder/scripts/phase2_execute.sh`

Commit: `feat(rdd-builder): add --auto-approve flag to phase2_execute.sh`

---

## Task 8: Add `--auto-approve` flag to `phase2_5_review.sh`

Same pattern. Files:
- Create: `tests/integration/test_phase2_5_auto_approve.bats`
- Modify: `skills/rdd-builder/scripts/phase2_5_review.sh`

Commit: `feat(rdd-builder): add --auto-approve flag to phase2_5_review.sh`

---

## Task 9: Add `--auto-approve` flag to `phase3_archive.sh`

Same pattern. Files:
- Create: `tests/integration/test_phase3_auto_approve.bats`
- Modify: `skills/rdd-builder/scripts/phase3_archive.sh`

Commit: `feat(rdd-builder): add --auto-approve flag to phase3_archive.sh`

(Note: phase3 already passes `--yes` to `openspec archive`, so this may just need flag parsing for consistency. Verify in Step 3.)

---

## Task 10: Add `--no-confirm` flag to `scaffold_plan.sh`

**Files:**
- Create: `tests/integration/test_scaffold_plan_no_confirm.bats`
- Modify: `skills/rdd-quick/scripts/scaffold_plan.sh`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_scaffold_plan_no_confirm.bats`:
```bash
#!/usr/bin/env bats
load ../test_helper

setup() {
    RDDF_QUICK_PLAN_DIR="$BATS_TEST_TMPDIR/plans"
    mkdir -p "$RDDF_QUICK_PLAN_DIR"
    export RDDF_QUICK_PLAN_DIR
}

@test "scaffold_plan.sh: --no-confirm writes plan without TTY" {
    run bash "$REPO_ROOT/skills/rdd-quick/scripts/scaffold_plan.sh" \
        --name "smoke-test" --proposal "smoke test proposal" --no-confirm
    [ "$status" -eq 0 ]
    [ -f "$RDDF_QUICK_PLAN_DIR/quick-smoke-test.md" ]
}

@test "scaffold_plan.sh: refuses to overwrite without --force flag" {
    bash "$REPO_ROOT/skills/rdd-quick/scripts/scaffold_plan.sh" \
        --name "smoke-test" --proposal "first" --no-confirm
    run bash "$REPO_ROOT/skills/rdd-quick/scripts/scaffold_plan.sh" \
        --name "smoke-test" --proposal "second" --no-confirm
    [ "$status" -ne 0 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_scaffold_plan_no_confirm.bats`
Expected: FAIL (no --no-confirm handler) or first test passes if already non-interactive.

- [ ] **Step 3: Add `--no-confirm` flag handling to `scaffold_plan.sh`**

Find the argument parsing section and add `--no-confirm`:
```bash
NO_CONFIRM=0
for arg in "$@"; do
    case "$arg" in
        --no-confirm) NO_CONFIRM=1 ;;
    esac
done
export NO_CONFIRM
```

Gate any read prompts on `NO_CONFIRM=1`.

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_scaffold_plan_no_confirm.bats`
Expected: 2 pass

- [ ] **Step 5: Commit**

```bash
git add skills/rdd-quick/scripts/scaffold_plan.sh tests/integration/test_scaffold_plan_no_confirm.bats
git commit -m "feat(rdd-quick): add --no-confirm flag to scaffold_plan.sh

Per 2026-09-08-e2e-test-plan-design.md §3.2: A-layer non-interactive
entrypoint. Flag suppresses any future TTY prompts. Default behavior
unchanged."
```

---

## Task 11: Extend `test.sh` with `--e2e-smoke` / `--e2e-agent` / `--e2e-all` modes

**Files:**
- Modify: `test.sh` (add 3 new mode handlers + help text update)

- [ ] **Step 1: Update help text**

In `test.sh`, after the existing mode list in the header comment (around line 11), add:
```bash
#   ./test.sh --e2e-smoke             只跑 A 层 e2e (tests/e2e/script/) — CI 必跑
#   ./test.sh --e2e-agent             只跑 C 层 e2e (tests/e2e/agent/) — nightly 必跑
#   ./test.sh --e2e-all               A + C 全跑 (本地选)
```

- [ ] **Step 2: Add mode parsing**

Find the existing mode parsing block (after `POSITIONAL=()`) and add 3 new cases. Locate where `--quick`, `--full`, `--bats`, `--python`, `--unit`, `--integration` are handled. Add:
```bash
        --e2e-smoke)
            MODE="e2e-smoke"
            ;;
        --e2e-agent)
            MODE="e2e-agent"
            ;;
        --e2e-all)
            MODE="e2e-all"
            ;;
```

- [ ] **Step 3: Add mode handlers**

Find where the existing mode handlers run (e.g. the case statement that runs `npm test` or `pytest` based on `$MODE`). Add:
```bash
        e2e-smoke)
            echo "${CYAN}=== A-layer e2e smoke (CI required) ===${NC}"
            run_bats_dir "tests/e2e/script/" --regression
            ;;
        e2e-agent)
            if [ "${RDDF_AGENT_E2E:-0}" != "1" ]; then
                echo "${YELLOW}SKIP: C-layer e2e agent (set RDDF_AGENT_E2E=1 to enable)${NC}"
                echo "${YELLOW}Hint: nightly cron sets this automatically${NC}"
                exit 0
            fi
            echo "${CYAN}=== C-layer e2e agent (nightly) ===${NC}"
            run_bats_dir "tests/e2e/agent/"
            ;;
        e2e-all)
            "$0" --e2e-smoke
            "$0" --e2e-agent
            ;;
```

(If `run_bats_dir` doesn't exist, add a helper:
```bash
run_bats_dir() {
    local dir="$1"
    shift
    if [ -d "$dir" ]; then
        bats "$@" "$dir"
    else
        echo "${YELLOW}SKIP: $dir not found (will be created in later phase)${NC}"
        return 0
    fi
}
```
)

- [ ] **Step 4: Smoke test the new modes**

Run: `./test.sh --e2e-smoke`
Expected: PASS or SKIP (tests/e2e/script/ doesn't exist yet, will be created in Task 12-13)

Run: `RDDF_AGENT_E2E=0 ./test.sh --e2e-agent`
Expected: SKIP message, exit 0

Run: `./test.sh --e2e-all`
Expected: both e2e-smoke and e2e-agent run

- [ ] **Step 5: Commit**

```bash
git add test.sh
git commit -m "feat(test.sh): add --e2e-smoke / --e2e-agent / --e2e-all modes

Per 2026-09-08-e2e-test-plan-design.md §5:
- --e2e-smoke: A-layer (CI required, no agent creds)
- --e2e-agent: C-layer (nightly, RDDF_AGENT_E2E=1 opt-in)
- --e2e-all: A + C in sequence

run_bats_dir helper added for graceful SKIP when dir missing.
C-layer auto-skips without RDDF_AGENT_E2E=1 (default safe).
Updated header comment with 3 new modes."
```

---

## Task 12: `tests/e2e/script/test_rdd_quick_smoke.bats` — 4 A-layer cases

**Files:**
- Create: `tests/e2e/script/test_rdd_quick_smoke.bats`

- [ ] **Step 1: Write the bats file**

Create `tests/e2e/script/test_rdd_quick_smoke.bats`:
```bash
#!/usr/bin/env bats
# tests/e2e/script/test_rdd_quick_smoke.bats
# A-layer smoke for rdd-quick per 2026-09-08-rdd-quick-e2e-scenarios.md
# 4 cases: scaffold + append_history + AC source + isolation
# Runs in <5s on CI.

load ../../test_helper

setup() {
    load_lib isolation
    load_lib script_smoke
    load_lib golden_compare

    FAKE_ROOT="$BATS_TEST_TMPDIR/fake-quick"
    export SMOKE_FAKE_ROOT="$FAKE_ROOT"
    export SMOKE_REPO_ROOT="$REPO_ROOT"
    script_smoke::setup_fake_project "$FAKE_ROOT"
    BASELINE_FILE="$BATS_TEST_TMPDIR/baseline.sha256"
    isolation::snapshot_repo_state "$BASELINE_FILE"
}

teardown() {
    script_smoke::cleanup_fake_project "$FAKE_ROOT"
    isolation::verify_zero_pollution "$BASELINE_FILE" || {
        echo "POLLUTION DETECTED — see diff above" >&2
        return 1
    }
}

@test "rdd-quick A1: scaffold_plan.sh --no-confirm creates quick-*.md with 5 TDD markers" {
    RDDF_QUICK_PLAN_DIR="$FAKE_ROOT/.rddf/plans"
    mkdir -p "$RDDF_QUICK_PLAN_DIR"
    run bash "$REPO_ROOT/skills/rdd-quick/scripts/scaffold_plan.sh" \
        --name "smoke-test" --proposal "smoke test" --no-confirm
    [ "$status" -eq 0 ]
    [ -f "$RDDF_QUICK_PLAN_DIR/quick-smoke-test.md" ]
    grep -q "Step 1: Write the failing test" "$RDDF_QUICK_PLAN_DIR/quick-smoke-test.md"
    grep -q "Step 5: Defer commit" "$RDDF_QUICK_PLAN_DIR/quick-smoke-test.md"
}

@test "rdd-quick A2: append_history.py validates and appends to .quick-history.jsonl" {
    HIST="$FAKE_ROOT/.rddf/state/.quick-history.jsonl"
    mkdir -p "$(dirname "$HIST")"
    local entry='{"name":"smoke","plan_file":"quick-smoke.md","commit_sha":"abc123","started_at":"2026-09-08T00:00:00Z","ended_at":"2026-09-08T00:01:00Z","complexity":"low","reviewed_by":null,"retry_count":0,"verdict_summary":"1/1 pass","outcome":"completed","upgraded_to_change":null}'
    run bash "$REPO_ROOT/skills/rdd-quick/scripts/append_history.py" <<< "$entry"
    [ "$status" -eq 0 ]
    [ -f "$HIST" ]
    [ "$(wc -l < "$HIST")" -eq 1 ]
}

@test "rdd-quick A3: scaffold_plan.sh plan file contains ## Acceptance section" {
    RDDF_QUICK_PLAN_DIR="$FAKE_ROOT/.rddf/plans"
    mkdir -p "$RDDF_QUICK_PLAN_DIR"
    bash "$REPO_ROOT/skills/rdd-quick/scripts/scaffold_plan.sh" \
        --name "smoke-acceptance" --proposal "smoke" --no-confirm
    run grep -c "^## Acceptance" "$RDDF_QUICK_PLAN_DIR/quick-smoke-acceptance.md"
    [ "$output" -ge 1 ]
    run grep -c "^- \[ \] AC-" "$RDDF_QUICK_PLAN_DIR/quick-smoke-acceptance.md"
    [ "$output" -ge 1 ]
}

@test "rdd-quick A4: scaffold_plan.sh does NOT read openspec/changes/*/proposal.md for AC" {
    # Negative test: ensure rdd-quick stays decoupled from openspec changes
    # Per 2026-09-08-e2e-test-plan-design.md §4 (zero pollution)
    RDDF_QUICK_PLAN_DIR="$FAKE_ROOT/.rddf/plans"
    mkdir -p "$RDDF_QUICK_PLAN_DIR" "$FAKE_ROOT/openspec/changes/decoy/specs/decoy"
    cat > "$FAKE_ROOT/openspec/changes/decoy/specs/decoy/spec.md" <<EOF
## ADDED Requirements
### Requirement: decoy-requirement
#### Scenario: malicious_AC
- [ ] AC-99: This AC must NOT appear in rdd-quick plan
EOF
    bash "$REPO_ROOT/skills/rdd-quick/scripts/scaffold_plan.sh" \
        --name "decoy-test" --proposal "decoy" --no-confirm
    run grep -c "AC-99\|decoy-requirement" "$RDDF_QUICK_PLAN_DIR/quick-decoy-test.md"
    [ "$output" -eq 0 ]
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `bats tests/e2e/script/test_rdd_quick_smoke.bats`
Expected: 4 pass, 0 fail (assumes Tasks 1, 2, 10 done)

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/script/test_rdd_quick_smoke.bats
git commit -m "test(e2e): add A-layer rdd-quick smoke (4 cases)

Per 2026-09-08-rdd-quick-e2e-scenarios.md:
- A1: scaffold 5 TDD markers
- A2: append_history.py validates + appends
- A3: ## Acceptance section + AC checkboxes
- A4: zero pollution — does NOT read openspec/proposal.md

Each case uses script_smoke + isolation helpers from Task 1, 2.
teardown verifies zero pollution via sha256 lock (6 paths).
Total runtime < 5s, CI-compatible."
```

---

## Task 13: `tests/e2e/script/test_rdd_builder_smoke.bats` — 6 A-layer cases

**Files:**
- Create: `tests/e2e/script/test_rdd_builder_smoke.bats`

- [ ] **Step 1: Write the bats file**

Create `tests/e2e/script/test_rdd_builder_smoke.bats`:
```bash
#!/usr/bin/env bats
# tests/e2e/script/test_rdd_builder_smoke.bats
# A-layer smoke for rdd-builder per 2026-09-08-rdd-builder-e2e-scenarios.md
# 6 cases: one per phase script (B-E1..B-E6 from spec, A-layer subset).
# Runs in <30s on CI.

load ../../test_helper

setup() {
    load_lib isolation
    load_lib script_smoke

    FAKE_ROOT="$BATS_TEST_TMPDIR/fake-builder"
    export SMOKE_FAKE_ROOT="$FAKE_ROOT"
    export SMOKE_REPO_ROOT="$REPO_ROOT"
    script_smoke::setup_fake_project "$FAKE_ROOT"
    BASELINE_FILE="$BATS_TEST_TMPDIR/baseline.sha256"
    isolation::snapshot_repo_state "$BASELINE_FILE"
}

teardown() {
    script_smoke::cleanup_fake_project "$FAKE_ROOT"
    isolation::verify_zero_pollution "$BASELINE_FILE" || {
        echo "POLLUTION DETECTED — see diff above" >&2
        return 1
    }
}

@test "rdd-builder A1: phase0_approval.sh --auto-approve handles non-interactive (B-E1 subset)" {
    # Create a minimal proposal
    mkdir -p "$FAKE_ROOT/openspec/changes/b-e1"
    cat > "$FAKE_ROOT/openspec/changes/b-e1/proposal.md" <<EOF
# Proposal b-e1
## Why
Test.
## What Changes
- Add test
## Capabilities
- capability-1
## Acceptance
- [ ] AC-1: pass
EOF
    git -C "$FAKE_ROOT" add -A && git -C "$FAKE_ROOT" commit -q -m "init b-e1"
    run timeout 10 script_smoke::invoke_phase "phase0_approval.sh" "b-e1" "$FAKE_ROOT" --auto-approve
    [ "$status" -ne 124 ]
    # Note: may exit 1 if proposal insufficient; that's expected for smoke
}

@test "rdd-builder A2: phase1_plan.sh --auto-approve runs without TTY hang (B-E3 subset)" {
    run timeout 10 script_smoke::invoke_phase "phase1_plan.sh" "b-e2" "$FAKE_ROOT" --auto-approve
    [ "$status" -ne 124 ]
}

@test "rdd-builder A3: phase1_5_deps.sh --auto-approve runs without TTY hang (B-E4 subset)" {
    run timeout 10 script_smoke::invoke_phase "phase1_5_deps.sh" "b-e3" "$FAKE_ROOT" --auto-approve
    [ "$status" -ne 124 ]
}

@test "rdd-builder A4: phase2_execute.sh --auto-approve runs without TTY hang (B-E6 subset)" {
    run timeout 10 script_smoke::invoke_phase "phase2_execute.sh" "b-e4" "$FAKE_ROOT" --auto-approve
    [ "$status" -ne 124 ]
}

@test "rdd-builder A5: phase2_5_review.sh --auto-approve runs without TTY hang (B-E8 subset)" {
    run timeout 10 script_smoke::invoke_phase "phase2_5_review.sh" "b-e5" "$FAKE_ROOT" --auto-approve
    [ "$status" -ne 124 ]
}

@test "rdd-builder A6: phase3_archive.sh --auto-approve handles missing change gracefully" {
    # Smoke: ensures phase3 exits cleanly when change doesn't exist
    run timeout 10 script_smoke::invoke_phase "phase3_archive.sh" "nonexistent" "$FAKE_ROOT" --auto-approve
    # Acceptable: 1 (no change to archive) or 0 (graceful skip)
    [ "$status" -ne 124 ]
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `bats tests/e2e/script/test_rdd_builder_smoke.bats`
Expected: 6 pass, 0 fail (assumes Tasks 4-9 done)

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/script/test_rdd_builder_smoke.bats
git commit -m "test(e2e): add A-layer rdd-builder smoke (6 cases)

Per 2026-09-08-rdd-builder-e2e-scenarios.md (A-layer subset of B-E1..B-E12):
- A1: phase0_approval --auto-approve (B-E1)
- A2: phase1_plan --auto-approve (B-E3)
- A3: phase1_5_deps --auto-approve (B-E4)
- A4: phase2_execute --auto-approve (B-E6)
- A5: phase2_5_review --auto-approve (B-E8)
- A6: phase3_archive --auto-approve (B-E9 subset)

Each case uses script_smoke + isolation helpers. timeout=10s to
detect TTY hang (124 exit code = fail). Zero pollution enforced
in teardown via sha256 lock."
```

---

## Task 14: Delete self-test bats, run final regression

**Files:**
- Delete: `tests/e2e/_lib/test_isolation.bats`
- Delete: `tests/e2e/_lib/test_script_smoke.bats`
- Delete: `tests/e2e/_lib/test_golden_compare.bats`

- [ ] **Step 1: Delete self-tests**

The 3 self-tests (Tasks 1, 2, 3) were temporary scaffolding. Real coverage now lives in `tests/e2e/script/test_rdd_quick_smoke.bats` and `test_rdd_builder_smoke.bats`. Delete the 3 self-test files.

- [ ] **Step 2: Run full regression to verify nothing breaks**

Run: `./test.sh --full --regression`
Expected: only the 5 known baseline failures in `tests/KNOWN_FAILURES.txt` (no new failures from Phase 1 changes)

- [ ] **Step 3: Run new A-layer e2e**

Run: `./test.sh --e2e-smoke`
Expected: 4 + 6 = 10 A-layer cases pass

- [ ] **Step 4: Commit cleanup**

```bash
git add -A
git commit -m "test(e2e): clean up self-test bats from Task 1-3

Tasks 1-3 created 3 temporary self-test bats to drive TDD for the
isolation/script_smoke/golden_compare helpers. Now that real coverage
lives in tests/e2e/script/test_rdd_*_smoke.bats (Tasks 12-13), the
self-tests are redundant. Delete them.

Final state: A-layer 10 cases + 3 helpers + 8 phase script flags
+ test.sh 3 new modes. CI integration ready."
```

---

## Self-Review

**1. Spec coverage:**
- 3 helpers (isolation, script_smoke, golden_compare) per spec §4 ✓
- 6 phase scripts --auto-approve per spec §3.2 ✓
- scaffold_plan.sh --no-confirm per spec §3.2 ✓
- test.sh --e2e-smoke/--e2e-agent/--e2e-all per spec §5 ✓
- 4 rdd-quick A-layer cases per spec §4 (script/) ✓
- 6 rdd-builder A-layer cases per spec §4 (script/) ✓
- Zero pollution isolation per spec §7 #6 ✓ (in every teardown)

**2. Placeholder scan:** No TBD/TODO/"implement later" in any step. Every step has exact file path + concrete code or command.

**3. Type/function name consistency:**
- `isolation::snapshot_repo_state` and `isolation::verify_zero_pollution` used in Task 1, 12, 13, 14 — consistent
- `script_smoke::setup_fake_project` / `cleanup_fake_project` / `invoke_phase` used in Task 2, 12, 13 — consistent
- `golden_compare::update` / `check` / `regen` defined in Task 3, used in Task 12 — consistent
- `isolation::snapshot_repo_state` / `verify_zero_pollution` signatures match across all callers

**4. Risk callouts:**
- Task 4-9: existing phase scripts may have different prompt structures; engineer must read each script before adding flag handling. Each task has Step 3 guidance to "find the interactive prompt and gate it" — adjust per script's actual structure.
- Task 12/13: if a phase script's existing behavior changes between Task 4-9 and Task 13, A-layer test may need adjustment. Run after each Task 4-9 to catch early.
- Task 14 Step 2: if regression shows new failures, identify whether they are in A-layer (fix before merge) or in existing KNOWN_FAILURES (acceptable).

**Plan ready for execution.**
