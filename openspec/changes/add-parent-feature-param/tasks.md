## 1. Add `--parent-feature` argument to `propose_create_change` bash function (T1)

- [ ] 1.1 **Write failing test**: Create bats test in `tests/integration/test_propose_skill.bats` — invoke `propose_create_change test --skeleton phase1 core P0 --parent-feature feature-rddf` (in a temp dir with skeleton artifacts) and assert `PARENT_FEATURE=feature-rddf` is passed through to Python heredoc
- [ ] 1.2 **Verify fail**: Run `bats tests/integration/test_propose_skill.bats` — confirm the test fails (current code only reads env var, no CLI arg parsing)
- [ ] 1.3 **Implement**: Add `--parent-feature` argument parsing to `propose_create_change()` in `skills/propose/scripts/propose_change.sh`:
  ```bash
  propose_create_change() {
    local parent_feature=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --parent-feature) parent_feature="$2"; shift 2 ;;
        *) break ;;
      esac
    done
    local name="$1" mode="$2" current_phase="$3" category="$4" priority="$5"
    # ... existing code, then:
    if [ -n "$parent_feature" ]; then
      PARENT_FEATURE="$parent_feature" \
    fi
    # ... python3 heredoc
  }
  ```
- [ ] 1.4 **Verify pass**: Re-run the bats test — confirm it passes
- [ ] 1.5 **Commit**: `git add skills/propose/scripts/propose_change.sh tests/integration/test_propose_skill.bats && git commit -m "feat(propose): add --parent-feature arg to propose_create_change"`

## 2. Add `--parent-feature` argument to `propose_finalize_change` bash function (T2)

- [ ] 2.1 **Write failing test**: Add bats test — invoke `propose_finalize_change test phase1 core P0 "cat1:name" --parent-feature feature-stream` and assert env var is set in Python heredoc
- [ ] 2.2 **Verify fail**: Run the test — confirm it fails (no CLI arg parsing for finalize either)
- [ ] 2.3 **Implement**: Add `--parent-feature` argument parsing to `propose_finalize_change()` in `propose_change.sh` (same pattern as T1)
- [ ] 2.4 **Verify pass**: Re-run — confirm it passes
- [ ] 2.5 **Commit**: `git add skills/propose/scripts/propose_change.sh && git commit -m "feat(propose): add --parent-feature arg to propose_finalize_change"`

## 3. Add Phase 3 interactive menu integration (T3)

- [ ] 3.1 **Write failing test**: Add bats test — propose Phase 3 flow with a user selection, confirm that after "归属 feature" prompt the `PARENT_FEATURE` env var is set before Phase 4
- [ ] 3.2 **Verify fail**: Run the test — confirm it fails (no interactive prompt yet)
- [ ] 3.3 **Implement**: Add interactive prompt in `propose.md` Phase 3 — after user selects a propose, ask "是否需要将此 change 归属到某个 feature 组？(可选，直接回车跳过)":
  ```markdown
  After user selects propose(s), for each selection:
  - Ask: "将此 change 归属到哪个 feature 组？(可选，回车跳过)"
  - If user provides a value, set `PARENT_FEATURE=<value>`
  - If user presses Enter, keep `PARENT_FEATURE` unset (backward compatible)
  - If user enters `__ungrouped__`, reject with "保留字，请输入其他名称或留空"
  ```
- [ ] 3.4 **Verify pass**: Re-run — confirm it passes
- [ ] 3.5 **Commit**: `git add skills/propose/SKILL.md && git commit -m "feat(propose): add Phase 3 interactive parent-feature prompt"`

## 4. Add unit test: `parent_feature` in skeleton call (T4)

- [ ] 4.1 **Write failing test**: Add to `tests/unit/test_propose_change.py` — call `create_skeleton_change` with `parent_feature="feature-rddf"`, assert `roadmap-meta.yaml` contains `parent_feature: "feature-rddf"` and `iteration.json` has the field
- [ ] 4.2 **Verify fail**: Run `python3 -m pytest tests/unit/test_propose_change.py::test_skeleton_with_parent_feature -xvs` — confirm it fails (file doesn't exist yet)
- [ ] 4.3 **N/A** (Python backend already supports `parent_feature` parameter — the test should pass immediately)
- [ ] 4.4 **Verify pass**: Run the test — confirm it passes
- [ ] 4.5 **Commit**: `git add tests/unit/test_propose_change.py && git commit -m "test: add skeleton with parent_feature unit test"`

## 5. Add unit test: `__ungrouped__` rejection in finalize (T5)

- [ ] 5.1 **Write failing test**: Add to `tests/unit/test_propose_change.py` — call `update_iteration_proposed` with `parent_feature="__ungrouped__"`, assert `ValueError` with "reserved" in message
- [ ] 5.2 **Verify fail**: Run the test — confirm it fails
- [ ] 5.3 **N/A** (Python backend already rejects `__ungrouped__` — test should pass immediately)
- [ ] 5.4 **Verify pass**: Run — confirm it passes
- [ ] 5.5 **Commit**: `git add tests/unit/test_propose_change.py && git commit -m "test: add __ungrouped__ rejection unit test"`

## 6. Add integration test: feature summary grouping (T6)

- [ ] 6.1 **Write failing test**: Add bats test in `tests/integration/test_propose_skill.bats` — create a change with `parent_feature="feature-rddf"`, run `skill_use("feature", "summary")`, assert the change appears under `feature-rddf` group (not `__ungrouped__`)
- [ ] 6.2 **Verify fail**: Run `bats tests/integration/test_propose_skill.bats` — confirm it fails
- [ ] 6.3 **N/A** (feature summary is pure derived view from iteration.json — if `parent_feature` is set, it auto-works)
- [ ] 6.4 **Verify pass**: Run — confirm it passes
- [ ] 6.5 **Commit**: `git add tests/integration/test_propose_skill.bats && git commit -m "test: add feature summary grouping integration test"`