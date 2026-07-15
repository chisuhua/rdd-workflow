---
SCOPE: shared
STATUS: PROPOSED
---

# Tasks: status-guide-revision

> **Goal**: Resolve 15 audit findings in `skills/guide.md` and `skills/status.md`, ordered by severity (P0 → P1 → P2), with every change gated by a bats regression test.
> **Risk**: medium (two behavior changes: stale-state warning + archive confirmation gate; rest is doc-only).
> **Estimated effort**: ~5-6 hours.

## Tier 1 — P0 (correctness)

### 1.1 Eliminate duplicate `version:` keys in skill frontmatter (G1 + C1)

- [x] 1.1.1 Add `tests/integration/test_frontmatter_dupkey.bats` (3 cases: guide, status, semver-resolve)

```bash
cat > tests/integration/test_frontmatter_dupkey.bats <<'BATSEOF'
#!/usr/bin/env bats
load ../test_helper

assert_no_dup_version() {
  local f="$1"
  local n
  n=$(awk '/^metadata:/{f=1;next} f && /^---$/{exit} f && /^[[:space:]]+version:/{print}' "$f" | wc -l)
  [ "$n" -le 1 ] || { echo "FAIL: $f has $n version keys (want <=1)"; return 1; }
}

@test "guide.md frontmatter has at most one version key" {
  assert_no_dup_version skills/guide.md
}

@test "status.md frontmatter has at most one version key" {
  assert_no_dup_version skills/status.md
}

@test "guide.md metadata.version matches skill_field semver pattern" {
  run python3 -c "
import yaml,sys
d=yaml.safe_load(open('skills/guide.md').read().split('---',2)[1])
v=d.get('metadata',{}).get('version','')
import re
sys.exit(0 if re.match(r'^\d+\.\d+(\.\d+)?$', str(v)) else 2)
"
  [ "$status" -eq 0 ]
}
BATSEOF
```

Run: `bats tests/integration/test_frontmatter_dupkey.bats`
Expected: at least 2 failures (tests 1 & 2). Test 3 may pass pre-fix (YAML keeps last).

- [x] 1.1.2 In `skills/guide.md` lines 6-11, remove duplicate `version:` (keep line 7 `version: "2.0"` as source-of-truth; move "v1.1 rddf-session binding scan" note into `evolved-from:` string).

- [x] 1.1.3 In `skills/status.md` lines 6-10, remove duplicate `version:` (keep line 9 `version: "2.0.2"`; move v1.x note into `evolved-from:`).

- [x] 1.1.4 Verify `bats tests/integration/test_frontmatter_dupkey.bats` all green; existing `test_guide_skill.bats` + `test_status_skill.bats` still green.

- [x] 1.1.5 Commit:
```bash
git add tests/integration/test_frontmatter_dupkey.bats skills/guide.md skills/status.md
git commit -m "fix(skills): eliminate duplicate version keys in frontmatter (G1, C1)

YAML silent-keep-last was hiding the metadata.version from source-of-truth.
Migrated evolution notes into metadata.evolved-from.
Lock invariant with tests/integration/test_frontmatter_dupkey.bats (3 cases)."
```

### 1.2 Unify Mode A status column with iteration.json states (S1 + S2)

- [x] 1.2.1 Add `tests/integration/test_status_state_table.bats` (4 cases).

```bash
cat > tests/integration/test_status_state_table.bats <<'BATSEOF'
#!/usr/bin/env bats
load ../test_helper

@test "status.md Mode A dynamic block lists iteration.json states" {
  for s in planned proposed in_worktree completed archived; do
    grep -qE "\\b$s\\b" skills/status.md
  done
}

@test "status.md mentions committed-but-no-worktree state" {
  grep -qE "commit.{0,15}(no|无|未).{0,15}worktree|已 commit.{0,30}(未|无).{0,30}执行|💼" skills/status.md
}

@test "status.md Mode A does not hardcode '⏸ 暂停' as a state" {
  ! grep -E "⏸\s*暂停" skills/status.md
}

@test "iteration.json schema declared states match Mode A list" {
  for s in planned proposed in_worktree completed archived; do
    grep -qE "\\b$s\\b" skills/_lib/schemas/iteration_schema.json
  done
}
BATSEOF
```

- [x] 1.2.2 Verify red (≥1 fail).

- [x] 1.2.3 Rewrite `skills/status.md` lines 100-160 (dynamic status block + table) to include 6-state `📋 💼 ✅ 🔧 ✔ 📦` vocabulary; remove `"⏸ 暂停"` placeholder.

- [x] 1.2.4 Verify green + commit:
```bash
git add tests/integration/test_status_state_table.bats skills/status.md
git commit -m "fix(status): unify Mode A status column with iteration.json states (S1, S2)"
```

### 1.3 Add archive confirmation prompt (S7)

- [x] 1.3.1 Add `tests/integration/test_archive_confirmation.bats` (2 cases).

- [x] 1.3.2 Verify red.

- [x] 1.3.3 Insert "Step 0: 用户确认 gate" before `archive_change` invocation in `skills/status.md` Mode C; support `--yes`/`-y` bypass for CI.

- [x] 1.3.4 Verify green + commit.

## Tier 2 — P1 (usability)

### 2.1 scan-state.sh — clarify exported vars + fix priority count claim (G2 + G4)

- [x] 2.1.1 Add `tests/integration/test_scan_state_doc.bats` (3 cases).

- [x] 2.1.2 Verify red.

- [x] 2.1.3 Patch `skills/_lib/scan-state.sh` header to add `# EXPORTED_VARS: {RECOMMEND REASON}` line; patch `skills/guide.md` line 41 to say "12 条" instead of "11 条".

- [x] 2.1.4 Verify green + commit.

### 2.2 Add top-level mode router to status.md (S8)

- [x] 2.2.1 Add `tests/integration/test_status_mode_router.bats` (3 cases).

- [x] 2.2.2 Verify red (expect 1 fail, not 3: tests 2/3 already pass because input table documents the mapping; test 1 fails because no `case "$1"` code).

- [x] 2.2.3 Insert `status_router()` case block after "## 输入" subsection in `skills/status.md`.

- [x] 2.2.4 Verify green + commit.

### 2.3 Mode B cleanup — paths, dead source, comment (S4 + S5 + S6)

- [x] 2.3.1 Add `tests/integration/test_status_mode_b_path_hygiene.bats` (4 cases; last case uses **revised** awk pattern — see plan §2.3 R4 fix).

- [x] 2.3.2 Verify red (expect 3 failures; the awk-comment test fails correctly because the comment indeed omits `$1`).

- [x] 2.3.3 Patch `skills/status.md`: remove dead `source _lib/worktree.sh` block (lines 38-41), change `PLAN_FILE` to `$PROJECT_ROOT`-anchored, rewrite the line 382 awk comment to include `$1`.

- [x] 2.3.4 Verify green + commit.

### 2.4 Mode D — drop `$PROJECT_ROOT` interpolation into Python source (S12)

- [x] 2.4.1 Add `tests/integration/test_status_mode_d_env_safe.bats` (1 case).

- [x] 2.4.2 Verify red.

- [x] 2.4.3 Rewrite the two `python3 -c "..."` blocks in Mode D to use `os.environ["PROJECT_ROOT"]` per v2.0.2 convention.

- [x] 2.4.4 Verify green + commit.

### 2.5 Mode E — remove `exec $0` and consolidate `iteration.json` reads (S9 + S10)

- [x] 2.5.1 Add `tests/integration/test_status_mode_e_exec_safe.bats` (2 cases — **not 3**; the `list_planned` test would already pass and is therefore dropped per Oracle review R2).

```bash
cat > tests/integration/test_status_mode_e_exec_safe.bats <<'BATSEOF'
#!/usr/bin/env bats
# S9: Mode E step 3 uses `exec $0 --iteration` which fails because
#     this is markdown, not a script. Replace with explanatory text.
# S10: Mode E step 2b opens iteration.json a second time. Must call
#      a single iteration.py function instead.
# Note (Oracle R2): `iteration.list_planned` already exists at
#   skills/_lib/iteration.py:350 — dropped the redundant test in v2.0.3.

load ../test_helper

@test "status.md Mode E does NOT call exec \$0" {
  ! grep -E 'exec[[:space:]]+\$0' skills/status.md
}

@test "status.md Mode E consolidates iteration.json reads via iteration.py" {
  json_load_opens=$(grep -cE 'json\.load\(open\(' skills/status.md)
  [ "$json_load_opens" -le 1 ]
}
BATSEOF
```

- [x] 2.5.2 Verify red (expect 2 failures).

- [x] 2.5.3 Patch `skills/status.md` Mode E Step 3 (replace `exec $0`) and Step 2b (use `iteration.list_planned()`).

- [x] 2.5.4 Verify green + commit (no iteration.py change — function already exists).

## Tier 3 — P2 (consistency)

### 3.1 Mode A — dedup worktree list + add `i` handler (S3 + S11)

- [ ] 3.1.1 Add `tests/integration/test_status_mode_a_polish.bats` (2 cases).

- [ ] 3.1.2 Verify red.

- [ ] 3.1.3 Patch `skills/status.md`: remove the redundant "Step 1：获取 worktree 列表" subsection (lines 71-82); expand Mode A's case handler to include `i|` branch.

- [ ] 3.1.4 Verify green + commit.

### 3.2 guide.md — graceful binding skip + `--help`/`--no-binding` flags (G3 + G5)

- [ ] 3.2.1 Add `tests/integration/test_guide_binding_skip.bats` (3 cases).

- [ ] 3.2.2 Verify red.

- [ ] 3.2.3 Patch `skills/guide.md` lines 22-46: add input parser with `--help` / `--no-binding`; document graceful-skip semantics.

- [ ] 3.2.4 Verify green + commit.

### 3.3 Promote stale `workflow-state.md` warning into scan-state.sh (G6)

- [ ] 3.3.1 Add `tests/integration/test_stale_workflow_state.bats` (3 cases).

- [ ] 3.3.2 Verify red.

- [ ] 3.3.3 Append `check_stale_workflow_state()` to `skills/_lib/scan-state.sh`; invoke from `scan_state()`; trim doc in `skills/guide.md` lines 69-79.

- [ ] 3.3.4 Smoke: create temp repo with stale file, verify warning prints.

- [ ] 3.3.5 Verify green + commit.

### 3.4 Add a unified output style guide subsection (C2)

- [ ] 3.4.1 Add `tests/integration/test_skill_style_guide.bats` (4 cases).

- [ ] 3.4.2 Verify red (expect ≥1 failure).

- [ ] 3.4.3 Insert "## 输出风格指南" subsection in `skills/status.md` before "## 关键约束".

- [ ] 3.4.4 Verify green + `npm test` smoke still passes.

- [ ] 3.4.5 Commit.

## Final Lock-in

- [ ] FL0 Run full test sweep (16 baseline + 30 new = ≥46 cases)
- [ ] FL1 Run `python3 -m pytest tests/unit/ -q --tb=short`
- [ ] FL2 `git status --short` clean (only intended files)
- [ ] FL3 Sync `.rddf/state/iteration.json` to mark this change `status=completed` after all tier work done
- [ ] FL4 Final commit:
```bash
git commit -m "chore(status-guide-revision): all 12 work-units complete, 46+ tests green"
```

## Acceptance Criteria (mirror of `proposal.md`)

1. All 12 plan work-units complete in **strict tier order**: Tier 1 (1.1, 1.2, 1.3) → Tier 2 (2.1, 2.2, 2.3, 2.4, 2.5) → Tier 3 (3.1, 3.2, 3.3, 3.4) → Final Lock-in (FL0, FL1, FL2, FL3, FL4)
2. Every change preceded by a bats test that fails red → passes green
3. Baseline tests (16 cases) remain green
4. New bats test files total ≥ 30 cases
5. Python unit tests pass
6. `metadata.version` resolves to the most-recent semver in both skill files
7. Mode C archive flow requires y/n (or `--yes`) confirmation
8. Status Mode A unified with iteration.json 6-state enum incl. `review` + `committed-no-wt` display classification
9. Mode E drops `exec $0` and uses `iteration.list_planned()` (existing helper at `iteration.py:350`)
10. guide.md top-level `case "$1"` router + `--help`/`--no-binding` flags
11. `check_stale_workflow_state()` runtime warning emitted by `scan_state()`
12. Change archived via `openspec archive status-guide-revision --yes` after completion
