# add-spec-validation-gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 2 validator utilities (`validate_baseline.py` + `validate_delta_targets.py`) and wire them into `propose`/`guide-plan`/`guide-ship` skill entry points. Catches fabricated baseline claims (e.g., `g-gpu-client-default-stub-init` v1) and invalid MODIFIED/RENAMED delta targets (e.g., `g-gpu-client-meyers-singleton-fallback` v2) **before** commit/archive.

**Architecture:** Each validator is an independent CLI tool (`python3 <validator> <change-name>`) reading from `.openspec.yaml` baseline segment + `specs/<cap>/spec.md` delta sections. Validators call into existing `gate.py::Check` API for severity-segregated gating. Fail-fast at propose / plan-done / archive pre-flight. Pure Python stdlib (subprocess, pathlib, re, json, yaml) — no new deps.

**Tech Stack:** Python 3.11+ stdlib + `pyyaml` (already in requirements.txt). Bats 1.10+ for shell-level tests. OpenSpec CLI v1.4.1+.

**OpenSpec change artifacts**: `openspec/changes/add-spec-validation-gates/{proposal,design,tasks}.md` (canonical spec). This plan is the **execution contract** — see tasks.md for full code blocks.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/validate_baseline.py` | NEW: Verify `.openspec.yaml` baseline claims (file/symbol/git-history prefixes) |
| `skills/_lib/validate_delta_targets.py` | NEW: Verify spec.md MODIFIED/RENAMED target capabilities exist in main specs/ |
| `skills/_lib/gate.py` | MODIFY: Add `spec_baseline_verified` + `spec_delta_targets_verified` default checks |
| `skills/propose.md` | MODIFY: Call `validate_baseline.py` before writing artifacts |
| `skills/guide-plan.md` | MODIFY: Phase 4 plan-done gate calls both validators |
| `skills/guide-ship.md` | MODIFY: Phase 3 archive pre-flight calls `validate_delta_targets.py` |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_validate_baseline.py` | NEW: 7 unit tests covering file-exists/symbol-exists/git-history prefixes + free-text + v1 regression |
| `tests/unit/test_validate_delta_targets.py` | NEW: 5 unit tests covering ADDED/MODIFIED/RENAMED + v2 regression |

### CI

| File | Responsibility |
|---|---|
| `.github/workflows/test.yml` | MODIFY: New step runs validators on all active changes before pytest/bats |

---

## Pre-flight

- [ ] **Verify baseline tests pass before changes**

Run: `cd /workspace/project/rdd-workflow && python3 -m pytest tests/unit/ -q --tb=short`
Expected: all existing tests pass.

- [ ] **Verify bats smoke tests pass**

Run: `bats tests/smoke.bats`
Expected: all smoke cases green.

- [ ] **Locate gate.py hook points**

Run: `grep -n "plan_done\|ship_done\|default_checks" skills/_lib/gate.py | head -10`
Expected: locate `default_checks` dict where new checks register.

- [ ] **Identify baseline claim patterns in active changes**

Run: `for f in openspec/changes/*/.openspec.yaml; do echo "=== $f ==="; awk '/^baseline:/,/^[a-z]/{print}' "$f" 2>/dev/null | head -10; done`
Expected: observe free-text baseline segments, no structured prefixes yet.

---

### Task 1: Create `validate_baseline.py` with TDD

**Files:**
- Create: `skills/_lib/validate_baseline.py`
- Create: `tests/unit/test_validate_baseline.py`

Implements 7 unit tests for: file-exists pass/fail, symbol-exists pass/fail, git-history pass, free-text pass-with-warning, v1 regression (`CudaStub g_cuda_stub` not in git history).

- [ ] **Step 1.1: Write the failing test**

Create `tests/unit/test_validate_baseline.py` per tasks.md Task 2.1 Step 1. Test cases:
1. `test_file_exists_claim_passes_when_path_exists`
2. `test_file_exists_claim_fails_when_path_missing`
3. `test_symbol_exists_claim_passes_when_match`
4. `test_symbol_exists_claim_fails_when_no_match`
5. `test_git_history_claim_passes_for_existing_symbol`
6. `test_free_text_baseline_passes_with_warning`
7. `test_v1_g_gpu_client_baseline_fails_regression`

- [ ] **Step 1.2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_validate_baseline.py -v --tb=short`
Expected: all 7 tests fail (validator script doesn't exist yet → `ModuleNotFoundError`).

- [ ] **Step 1.3: Implement minimal `validate_baseline.py`**

Implement supporting functions:
- `find_change_dir(change_name, search_root)` — locate `openspec/changes/<name>`
- `verify_file_exists(rel_path, change_root)` — check FS
- `verify_symbol_exists(rel_path, pattern, change_root)` — read file + regex
- `verify_git_history(symbol, change_root, timeout=10)` — `git log -S "<symbol>" --all --oneline`
- `validate_baseline(change_name, search_root=None)` — orchestrator: parse YAML, iterate claims, exit 0/1/2

Recognized prefixes:
- `file-exists:<path>` → FS check
- `symbol-exists:<file>:<regex>` → grep check
- `git-history:<symbol>` → git log check
- (no prefix) → free-text, log warning, pass

Exit codes: 0 = pass, 1 = hard fail (block), 2 = soft warn (pass with unverifiable claims).

- [ ] **Step 1.4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_validate_baseline.py -v --tb=short`
Expected: all 7 tests pass.

- [ ] **Step 1.5: Commit**

Run:
```bash
git add skills/_lib/validate_baseline.py tests/unit/test_validate_baseline.py
git commit -m "feat(_lib): add validate_baseline.py with TDD tests

- Validates .openspec.yaml baseline claims (file/symbol/git-history prefixes)
- Catches fabricated baselines (e.g., g-gpu-client-default-stub-init v1)
- Exit codes: 0=pass, 1=hard fail, 2=soft warn
- 7 unit tests covering all claim patterns + regression for v1 incident"
```

---

### Task 2: Create `validate_delta_targets.py` with TDD

**Files:**
- Create: `skills/_lib/validate_delta_targets.py`
- Create: `tests/unit/test_validate_delta_targets.py`

Implements 5 unit tests for: ADDED passes-without-target, MODIFIED fails-on-missing-target, MODIFIED passes-on-existing-target, RENAMED fails-on-missing-source, v2 regression.

- [ ] **Step 2.1: Write the failing test**

Create `tests/unit/test_validate_delta_targets.py` per tasks.md Task 2.2 Step 1. Test cases:
1. `test_added_section_passes_when_no_main_spec`
2. `test_modified_section_fails_when_target_spec_missing`
3. `test_modified_section_passes_when_target_spec_exists`
4. `test_renamed_section_fails_when_source_spec_missing`
5. `test_v2_g_gpu_client_meyers_fallback_regression`

- [ ] **Step 2.2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_validate_delta_targets.py -v --tb=short`
Expected: all 5 tests fail (`ModuleNotFoundError`).

- [ ] **Step 2.3: Implement minimal `validate_delta_targets.py`**

Implement supporting functions:
- `find_change_dir`, `find_change_capability` (read `.openspec.yaml` `name` field), `find_main_specs_dirs` (list `openspec/specs/<name>/spec.md`)
- `parse_delta_sections(spec_md)` — split by `## ADDED|MODIFIED|RENAMED|REMOVED Requirements` headers
- `extract_target_from_body(body_lines, change_cap)` — default = change_cap; override via `modifies: <cap>` or `target: <cap>` in first 5 lines
- `extract_rename_source(body_lines)` — parse `### Requirement: old-name -> new-name` header
- `validate_delta_targets(change_name)` — main entry: iterate `specs/<cap>/spec.md`, validate each MODIFIED/RENAMED target exists in main specs

- [ ] **Step 2.4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_validate_delta_targets.py -v --tb=short`
Expected: all 5 tests pass.

- [ ] **Step 2.5: Commit**

Run:
```bash
git add skills/_lib/validate_delta_targets.py tests/unit/test_validate_delta_targets.py
git commit -m "feat(_lib): add validate_delta_targets.py with TDD tests

- Validates spec.md MODIFIED/RENAMED sections target existing capabilities
- Catches archive aborts (e.g., g-gpu-client-meyers-singleton-fallback v2)
- Exit codes: 0=pass, 1=hard fail
- 5 unit tests covering ADDED/MODIFIED/RENAMED + regression for v2 incident"
```

---

### Task 3: Wire `validate_baseline.py` into `propose.md`

**Files:**
- Modify: `skills/propose.md`

- [ ] **Step 3.1: Find insertion point**

Run: `grep -n "openspec new change\|echo.*Created change" skills/propose.md | head -5`
Expected: find line where artifacts are first written.

- [ ] **Step 3.2: Insert validator call BEFORE first artifact write**

Find the line that writes `proposal.md` or `.openspec.yaml` body. Insert just BEFORE:
```bash
if ! python3 "$(dirname "${BASH_SOURCE[0]:-$(pwd)/skills/propose.md}")/_lib/validate_baseline.py" "$target_name" 2>/dev/null; then
    echo "❌ Baseline validation failed for $target_name"
    echo "   See errors above. Fix .openspec.yaml baseline claims before continuing."
    python3 "$(dirname "${BASH_SOURCE[0]:-$(pwd)/skills/propose.md}")/_lib/validate_baseline.py" "$target_name"
    exit 1
fi
```

Note: use `_lib/validate_baseline.py` resolved relative to the proposing skill file.

- [ ] **Step 3.3: Smoke test (positive path)**

Create temp change with valid free-text baseline, run validator directly:
```bash
mkdir -p /tmp/test-prop/openspec/changes/test/specs/test
cat > /tmp/test-prop/openspec/changes/test/.openspec.yaml <<'EOF'
schema: spec-driven
name: test
baseline:
  free-text: "any description"
EOF
echo "# TBD" > /tmp/test-prop/openspec/changes/test/specs/test/spec.md
python3 /workspace/project/rdd-workflow/skills/_lib/validate_baseline.py test
echo "exit=$?"
```
Expected: exit 0 (or 2 with unverifiable warning).

For `/tmp/test-prop` run, cd into it; the validator script searches `<cwd>/openspec/changes` so just `cd /tmp/test-prop && python3 /workspace/project/rdd-workflow/skills/_lib/validate_baseline.py test`.

- [ ] **Step 3.4: Smoke test (failure path)**

Create temp change with false `file-exists` claim:
```bash
mkdir -p /tmp/test-prop/openspec/changes/bad/specs/bad
cat > /tmp/test-prop/openspec/changes/bad/.openspec.yaml <<'EOF'
schema: spec-driven
name: bad
baseline:
  fake-symbol: "file-exists:does/not/exist.cpp"
EOF
cd /tmp/test-prop && python3 /workspace/project/rdd-workflow/skills/_lib/validate_baseline.py bad
echo "exit=$?"
```
Expected: exit 1 with "❌ file-exists:does/not/exist.cpp FAILED".

- [ ] **Step 3.5: Verify propose.md still parses YAML**

Run: `head -5 skills/propose.md && grep -c "^---" skills/propose.md`
Expected: frontmatter intact.

- [ ] **Step 3.6: Commit**

Run:
```bash
git add skills/propose.md
git commit -m "feat(propose): call validate_baseline.py before writing artifacts

- Blocks propose flow when .openspec.yaml baseline claim is fabricated
- Prevents g-gpu-client-default-stub-init v1 class incidents"
```

---

### Task 4: Wire both validators into `guide-plan.md` Phase 4 plan-done gate

**Files:**
- Modify: `skills/guide-plan.md`

- [ ] **Step 4.1: Find plan-done handoff write**

Run: `grep -n "cat >.*HANDOFF_FILE\|plan-handoff\|all_artifacts_committed" skills/guide-plan.md | head -10`
Expected: locate line that writes `.rddf/state/.plan-handoff.json`.

- [ ] **Step 4.2: Insert validator calls BEFORE handoff write**

Insert just before the `cat > "$HANDOFF_FILE" << EOF` line:
```bash
# Pre-handoff: validate all active changes' baseline + delta targets
VALIDATION_FAILED=0
for d in "$PROJECT_ROOT"/openspec/changes/*/; do
    [ -d "$d" ] || continue
    case "$d" in */archive/) continue ;; esac
    name=$(basename "$d")
    if ! python3 "$PROJECT_ROOT/skills/_lib/validate_baseline.py" "$name" >/dev/null 2>&1; then
        echo "❌ plan-done gate: $name failed baseline validation"
        python3 "$PROJECT_ROOT/skills/_lib/validate_baseline.py" "$name" || true
        VALIDATION_FAILED=1
    fi
    if ! python3 "$PROJECT_ROOT/skills/_lib/validate_delta_targets.py" "$name" >/dev/null 2>&1; then
        echo "❌ plan-done gate: $name failed delta target validation"
        python3 "$PROJECT_ROOT/skills/_lib/validate_delta_targets.py" "$name" || true
        VALIDATION_FAILED=1
    fi
done
if [ "$VALIDATION_FAILED" -ne 0 ]; then
    echo "❌ plan-done gate blocked: fix validation errors above"
    exit 1
fi
```

- [ ] **Step 4.3: Verify guide-plan.md still parses**

Run: `head -5 skills/guide-plan.md && grep -c "^---" skills/guide-plan.md`
Expected: frontmatter intact.

- [ ] **Step 4.4: Smoke test on current active change**

Run from project root (changes/ has 1 active change with all-free-text baseline, ADDED-only specs):
```bash
cd /workspace/project/rdd-workflow
python3 skills/_lib/validate_baseline.py add-spec-validation-gates
python3 skills/_lib/validate_delta_targets.py add-spec-validation-gates
```
Expected: both exit 0 (or 2 for baseline due to free-text warnings).

- [ ] **Step 4.5: Commit**

Run:
```bash
git add skills/guide-plan.md
git commit -m "feat(guide-plan): validate all active changes before plan-done handoff

- Calls validate_baseline.py + validate_delta_targets.py on each change
- Blocks plan-done handoff write when any change fails validation
- Prevents v1/v2 class incidents from reaching ship phase"
```

---

### Task 5: Wire `validate_delta_targets.py` into `guide-ship.md` Phase 3 archive pre-flight

**Files:**
- Modify: `skills/guide-ship.md`

- [ ] **Step 5.1: Find archive invocation**

Run: `grep -n 'openspec archive' skills/guide-ship.md | head -5`
Expected: locate `openspec archive "$CHANGE_NAME" --yes`.

- [ ] **Step 5.2: Insert validator call BEFORE archive**

Insert just before the `openspec archive` line:
```bash
# Pre-archive: validate delta targets to avoid archive abort
if ! python3 "$PROJECT_ROOT/skills/_lib/validate_delta_targets.py" "$CHANGE_NAME" 2>/dev/null; then
    echo "❌ Archive pre-flight failed for $CHANGE_NAME"
    echo "   Delta targets invalid. Run validate_delta_targets.py for details."
    python3 "$PROJECT_ROOT/skills/_lib/validate_delta_targets.py" "$CHANGE_NAME"
    exit 1
fi
```

- [ ] **Step 5.3: Verify guide-ship.md still parses**

Run: `head -5 skills/guide-ship.md && grep -c "^---" skills/guide-ship.md`
Expected: frontmatter intact.

- [ ] **Step 5.4: Smoke test**

Run: `python3 /workspace/project/rdd-workflow/skills/_lib/validate_delta_targets.py add-spec-validation-gates`
Expected: exit 0.

- [ ] **Step 5.5: Commit**

Run:
```bash
git add skills/guide-ship.md
git commit -m "feat(guide-ship): validate delta targets before archive

- Calls validate_delta_targets.py before openspec archive
- Avoids 6-step recovery chain (commit spec fix + push + bump + push + retry)"
```

---

### Task 6: Add CI workflow step

**Files:**
- Modify: `.github/workflows/test.yml`

- [ ] **Step 6.1: Locate CI workflow steps**

Run: `cat .github/workflows/test.yml | head -50`
Expected: find steps after checkout / pip install where to insert.

- [ ] **Step 6.2: Insert validator step after pytest, before bats**

Add new step:
```yaml
      - name: Validate spec baseline + delta targets
        run: |
          set -e
          VALIDATION_FAILED=0
          for d in openspec/changes/*/; do
            [ -d "$d" ] || continue
            case "$d" in */archive/) continue ;; esac
            name=$(basename "$d")
            echo "=== Validating $name ==="
            python3 skills/_lib/validate_baseline.py "$name" || VALIDATION_FAILED=1
            python3 skills/_lib/validate_delta_targets.py "$name" || VALIDATION_FAILED=1
          done
          if [ "${VALIDATION_FAILED:-0}" -ne 0 ]; then
            echo "❌ Spec validation failed"
            exit 1
          fi
          echo "✅ All active changes pass spec validation"
```

- [ ] **Step 6.3: Validate CI YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml'))"`
Expected: no YAML parse error.

- [ ] **Step 6.4: Commit**

Run:
```bash
git add .github/workflows/test.yml
git commit -m "ci: run validate_baseline.py + validate_delta_targets.py on all changes

- Adds spec validation step to CI workflow
- Catches fabricated baselines and invalid MODIFIED targets before merge"
```

---

### Task 7: Final verification

- [ ] **Step 7.1: Full pytest suite**

Run: `python3 -m pytest tests/unit/ -q --tb=short`
Expected: all existing + 2 new test files pass (28+2 existing + 2 new = 30+ test files).

- [ ] **Step 7.2: bats smoke tests**

Run: `bats tests/smoke.bats`
Expected: all smoke cases green.

- [ ] **Step 7.3: bats full suite**

Run: `npm test`
Expected: full bats suite green (no regression).

- [ ] **Step 7.4: End-to-end regression test: v1 incident**

Manually verify `validate_baseline.py` catches the v1 pattern by constructing a fake change with `git-history:` for an absent symbol; expect exit 1.

- [ ] **Step 7.5: End-to-end regression test: v2 incident**

Manually verify `validate_delta_targets.py` catches the v2 pattern by constructing a fake change with `## MODIFIED Requirements` targeting non-existent capability; expect exit 1.

- [ ] **Step 7.6: Update iteration.json tasks_done counter**

Update `iteration.json` to reflect all tasks complete. After all commits land:
```bash
python3 -c "
import sys, os
sys.path.insert(0, '/workspace/project/rdd-workflow')
from skills._lib import iteration as it_mod
data = it_mod.load('/workspace/project/rdd-workflow')
data = it_mod.add_or_update_change(data, name='add-spec-validation-gates', status='completed')
it_mod.save('/workspace/project/rdd-workflow', data)
print('✅ iteration.json: status=completed')
"
```

---

## Acceptance Criteria

- [ ] `validate_baseline.py <change>` correctly identifies false file-existence claims (regression-tested against v1)
- [ ] `validate_baseline.py <change>` correctly identifies false symbol-existence via git log -S
- [ ] `validate_delta_targets.py <change>` correctly identifies MODIFIED/RENAMED targeting non-existent capabilities
- [ ] `propose.md` aborts commit when `validate_baseline.py` returns exit 1
- [ ] `guide-plan.md` blocks plan-done when any active change fails validation
- [ ] `guide-ship.md` blocks archive when `validate_delta_targets.py` fails
- [ ] All existing skills/propose.md, guide-plan.md, guide-ship.md functionality unchanged when validation passes
- [ ] Pytest suite passes: 28+ existing test files + 2 new validator test files (12 new tests)
- [ ] bats smoke tests pass
- [ ] CI workflow runs validators on all changes

## Commit History Expected

```
0d6ba45 (master) [incoming from master]
feat(_lib): add validate_baseline.py with TDD tests
feat(_lib): add validate_delta_targets.py with TDD tests
feat(propose): call validate_baseline.py before writing artifacts
feat(guide-plan): validate all active changes before plan-done handoff
feat(guide-ship): validate delta targets before archive
ci: run validate_baseline.py + validate_delta_targets.py on all changes
```
