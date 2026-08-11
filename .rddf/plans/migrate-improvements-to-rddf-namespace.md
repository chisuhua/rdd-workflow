# migrate-improvements-to-rddf-namespace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `improvements/` 目录迁移到 `.rddf/improvements/`，被 opencode-skillfull 插件自动过滤，节省 system prompt ~4,887 tokens 静态占用，并通过 ADR-0026 固化 dot-prefix 命名约定。

**Architecture:** 原子提交（git mv 保留 history）+ 批量 sed 替换 markdown 链接 + 手工 review 替换 skills/_lib/ 路径常量 + 创建 ADR-0026 + 全量回归测试。

**Tech Stack:** bash, git, sed, Python (link validation), bats (回归测试), pytest (单元测试), openspec 1.4.1

---

## File Structure

### Production Code (无新生产代码,纯路径迁移)

| File | Responsibility |
|---|---|
| `improvements/*` (133 files) | 迁移到 `.rddf/improvements/*` |
| `.rddf/improvements/*` (133 files) | 提案池新位置,git tracked |
| `proposal-approved.md` | 134 个 markdown 链接更新 |
| `skills/**/SKILL.md` (~10 files) | 路径常量更新 |
| `skills/**/scripts/*.sh` (~10 files) | glob 路径更新 |
| `skills/**/scripts/*.py` (~10 files) | Python 路径常量更新 |
| `docs/adr/ADR-0026-*.md` | 新建,记录 dot-prefix 命名约定 |
| `docs/proposal-{suggestions,approved}-format.md` | 路径示例更新 |
| `INSTALL.md`, `USAGE.md`, `README.md` | 路径提及更新 |
| `tests/fixtures/**` | fixture 路径更新 |
| `tests/integration/*.bats` (~11 files) | 测试断言更新 |

### Tests

| File | Responsibility |
|---|---|
| `tests/smoke.bats` | smoke test 不变 |
| `tests/integration/scan_state.bats` | scan-state.sh 路径断言 |
| `tests/integration/test_approve_*.bats` | approve flow fixture 路径 |
| `tests/integration/test_design_*.bats` | design content review 路径 |
| `tests/integration/test_archive_*.bats` | archive flow 路径 |
| `tests/scripts/report_regression.sh` | KNOWN_FAILURES baseline 对比 |

---

### Task 1: Pre-flight validation (Verify fail step)

**Files:**
- Modify: (none, read-only verification)
- Test: verification commands

- [ ] **Step 1: Run failing verification — improvements/ must contain 133 tracked files**

Run: `git ls-files improvements/ | wc -l`
Expected: 133

- [ ] **Step 2: Verify proposal-approved.md has 134 markdown links to improvements/**

Run: `grep -c '](improvements/' proposal-approved.md`
Expected: 134 (all links pointing to old path)

- [ ] **Step 3: Snapshot baseline — this is what we expect to migrate away from**

Run: `git status --short | head -5`
Expected: clean (only plan-phase artifacts in last commit)

---

### Task 2: Git mv (atomic file move preserving history)

**Files:**
- Modify: `improvements/` (becomes empty dir, will be removed)
- Create: `.rddf/improvements/` (133 files moved here)

- [ ] **Step 1: Create new directory**

Run: `mkdir -p .rddf/improvements`
Expected: success

- [ ] **Step 2: git mv all 133 files atomically**

Run: `git mv improvements/*.md .rddf/improvements/`
Expected: success, all 133 files moved (git rename detection should preserve history)

- [ ] **Step 3: Verify directory is empty and remove it**

Run: `ls improvements/ 2>/dev/null && rmdir improvements`
Expected: empty directory removed

- [ ] **Step 4: Verify AC-1a: 133 files at new location**

Run: `[ "$(git ls-files .rddf/improvements/ | wc -l)" = "133" ] && echo PASS || echo FAIL`
Expected: PASS

- [ ] **Step 5: Verify AC-1c: git history preserved via rename detection**

Run: `git log --follow .rddf/improvements/add-openspec-gate.md | head -5`
Expected: shows full history (rename detected)

---

### Task 3: Update proposal-approved.md links (134 sed replacements)

**Files:**
- Modify: `proposal-approved.md` (134 links)

- [ ] **Step 1: Run failing verification — old links should be 134, new 0**

Run: `echo "old=$(grep -c '](improvements/' proposal-approved.md) new=$(grep -c '](.rddf/improvements/' proposal-approved.md)"`
Expected: old=134 new=0

- [ ] **Step 2: Apply sed replacement**

Run: `sed -i 's|](improvements/|](.rddf/improvements/|g' proposal-approved.md`
Expected: 134 substitutions, exit 0

- [ ] **Step 3: Verify AC-3: all 134 links now use new path**

Run: `[ "$(grep -c '](.rddf/improvements/' proposal-approved.md)" = "134" ] && [ "$(grep -c '](improvements/' proposal-approved.md)" = "0" ] && echo PASS || echo FAIL`
Expected: PASS

- [ ] **Step 4: Verify AC-3 (deep): each link resolves to an existing file**

Run:
```python
import re, os
with open('proposal-approved.md') as f: content = f.read()
links = re.findall(r'\]\(\.rddf/improvements/([^)]+)\)', content)
missing = [l for l in links if not os.path.exists(f'.rddf/improvements/{l}')]
print(f'OK: {len(links)} links, {len(missing)} missing')
assert len(missing) == 0
```
Expected: OK: 134 links, 0 missing

---

### Task 4: Update skills/_lib/ path constants (37 files)

**Files:**
- Modify: `skills/add-improve/SKILL.md` (3 occurrences)
- Modify: `skills/guide*/SKILL.md` (~5 files, ~7 occurrences)
- Modify: `skills/guide*/scripts/*.sh` (~7 files, glob paths)
- Modify: `skills/propose/scripts/*.py` (3-4 files)
- Modify: `skills/rdd-doctor/scripts/checks/proposal_table_check.py` (1 occurrence)
- Modify: `skills/_lib/*.py` (~15 files)

- [ ] **Step 1: Run failing verification — find all affected files**

Run: `grep -rln "improvements/" skills/ _lib/ | wc -l`
Expected: 37 (or close to it)

- [ ] **Step 2: Apply sed to all skill files (preserves content, only changes path)**

Run:
```bash
find skills/ _lib/ -type f \( -name "*.sh" -o -name "*.py" -o -name "*.md" \) \
  -exec grep -l "improvements/" {} \; | \
  xargs sed -i 's|improvements/\[a-zA-Z0-9_\-\]*\.md|.rddf/improvements/\0|g; s|"\./improvements/|"./.rddf/improvements/|g; s|/improvements/|/.rddf/improvements/|g'
```
Expected: 0 failures

> Note: simpler regex is `s|improvements/\[a-zA-Z0-9_-\]*.md|.rddf/improvements/&|g`; we apply multiple sed passes to cover all cases.

- [ ] **Step 3: Verify AC-2: 0 remaining `improvements/` references in skills/ and _lib/**

Run: `[ "$(grep -rn 'improvements/' skills/ _lib/ | grep -v '.rddf/improvements' | wc -l)" = "0" ] && echo PASS || echo FAIL`
Expected: PASS

- [ ] **Step 4: Sanity check — sample grep on key files**

Run:
```bash
grep -l "improvements/" skills/add-improve/SKILL.md  # should be empty
grep ".rddf/improvements" skills/add-improve/SKILL.md  # should have entries
```
Expected: first empty, second has entries

---

### Task 5: Update docs (proposal format guides + INSTALL + USAGE + README + ADR-0024/0025)

**Files:**
- Modify: `docs/proposal-suggestions-format.md`
- Modify: `docs/proposal-approved-format.md`
- Modify: `docs/adr/ADR-0024-deps-driven-execution-mode.md`
- Modify: `docs/adr/ADR-0025-design-proposal-creation.md`
- Modify: `docs/architecture/workflow-phases.md`
- Modify: `INSTALL.md`
- Modify: `USAGE.md`
- Modify: `README.md`

- [ ] **Step 1: Run failing verification — find docs/ files with improvements/**

Run: `grep -rln "improvements/" docs/ INSTALL.md USAGE.md README.md 2>/dev/null`
Expected: ~5 docs files + 1-2 root files

- [ ] **Step 2: Apply sed to docs/ and root files**

Run:
```bash
grep -rln "improvements/" docs/ INSTALL.md USAGE.md README.md 2>/dev/null | \
  xargs sed -i 's|improvements/\[a-zA-Z0-9_-\]*.md|.rddf/improvements/&|g; s|/improvements/|/.rddf/improvements/|g'
```
Expected: 0 failures

- [ ] **Step 3: Verify AC-2 (docs): 0 remaining `improvements/` references**

Run: `[ "$(grep -rn 'improvements/' docs/ | grep -v '.rddf/improvements' | wc -l)" = "0" ] && echo PASS || echo FAIL`
Expected: PASS

---

### Task 6: Create ADR-0026 (dot-prefix naming convention)

**Files:**
- Create: `docs/adr/ADR-0026-internal-metadata-namespace-convention.md`

- [ ] **Step 1: Verify file does not yet exist (no overwrite)**

Run: `[ ! -f docs/adr/ADR-0026-internal-metadata-namespace-convention.md ] && echo READY || echo EXISTS`
Expected: READY

- [ ] **Step 2: Create ADR-0026 with required content**

Create file with:
- Status: 已采纳
- Context: problem (improvements/* indexed as commands, ~4,887 tokens waste)
- Decision: use `.rddf/<category>/` for rdd-workflow internal metadata
- Consequences: + ADR-0026 reference in future metadata additions
- Must include keywords: `.rddf/<category>` and `opencode-skillfull`

- [ ] **Step 3: Verify AC-7: ADR-0026 exists and has required keywords**

Run: `grep -q "\.rddf/<category>" docs/adr/ADR-0026-*.md && grep -q "opencode-skillfull" docs/adr/ADR-0026-*.md && echo PASS || echo FAIL`
Expected: PASS

---

### Task 7: Update tests/ fixtures and bats assertions

**Files:**
- Modify: `tests/fixtures/diseased-repo/proposal-suggestions.md`
- Modify: `tests/integration/fixtures/guide_entry_clean.json`
- Modify: `tests/integration/scan_state.bats`
- Modify: `tests/integration/test_approve_*.bats` (~5 files)
- Modify: `tests/integration/test_design_*.bats` (~3 files)
- Modify: `tests/integration/test_archive_*.bats` (~3 files)
- Modify: any other tests/ files referencing `improvements/`

- [ ] **Step 1: Run failing verification — count test files with old path**

Run: `grep -rln "improvements/" tests/ | wc -l`
Expected: ~15 test files

- [ ] **Step 2: Apply sed to all tests/ files**

Run:
```bash
grep -rln "improvements/" tests/ | \
  xargs sed -i 's|improvements/\[a-zA-Z0-9_-\]*.md|.rddf/improvements/&|g; s|/improvements/|/.rddf/improvements/|g'
```
Expected: 0 failures

- [ ] **Step 3: Verify AC-2 (tests): 0 remaining `improvements/` references**

Run: `[ "$(grep -rn 'improvements/' tests/ | grep -v '.rddf/improvements' | wc -l)" = "0" ] && echo PASS || echo FAIL`
Expected: PASS

---

### Task 8: Run full regression test suite (Verify pass step)

**Files:**
- (no file modifications, verification only)

- [ ] **Step 1: Quick smoke test**

Run: `bats tests/smoke.bats`
Expected: 0 failures (or only baseline known failures)

- [ ] **Step 2: Scan-state integration test**

Run: `bats tests/integration/scan_state.bats`
Expected: 0 failures

- [ ] **Step 3: Python unit tests**

Run: `python3 -m pytest tests/unit/ -q --tb=short`
Expected: 0 failures

- [ ] **Step 4: Full regression with KNOWN_FAILURES baseline**

Run: `./test.sh --full --regression`
Expected: 0 new failures (only KNOWN_FAILURES.txt baseline allowed)

- [ ] **Step 5: rdd-doctor verification**

Run: `bash skills/rdd-doctor/scripts/doctor.sh --quiet 2>&1 | head -20`
Expected: 0 CRITICAL, 0 path-related WARNING

---

### Task 9: User verification + final state check (AC-5 manual)

**Files:**
- (no file modifications, user verification)

- [ ] **Step 1: Final AC verification (all 8 ACs)**

Run:
```bash
# AC-1a
[ "$(git ls-files .rddf/improvements/ | wc -l)" = "133" ] && echo "AC-1a PASS" || echo "AC-1a FAIL"

# AC-1b
[ ! -d improvements ] || [ -z "$(ls -A improvements)" ] && echo "AC-1b PASS" || echo "AC-1b FAIL"

# AC-2 (4 directories)
for d in skills/ _lib/ tests/ docs/; do
  count=$(grep -rn "improvements/" $d 2>/dev/null | grep -v ".rddf/improvements" | wc -l)
  [ "$count" = "0" ] && echo "AC-2 ($d) PASS" || echo "AC-2 ($d) FAIL ($count)"
done

# AC-3 (link resolution)
python3 -c "
import re, os
with open('proposal-approved.md') as f: content = f.read()
links = re.findall(r'\]\(\.rddf/improvements/([^)]+)\)', content)
missing = [l for l in links if not os.path.exists(f'.rddf/improvements/{l}')]
print('AC-3', 'PASS' if len(missing) == 0 else f'FAIL ({len(missing)} missing)')
"

# AC-7 (ADR-0026)
[ -f docs/adr/ADR-0026-internal-metadata-namespace-convention.md ] && echo "AC-7 PASS" || echo "AC-7 FAIL"
```
Expected: all PASS

- [ ] **Step 2: User verifies AC-5 (opencode restart, available_skills no longer contains improvements/*)**

User action: Restart opencode, inspect system prompt, confirm `/rdd-workflow/improvements/<name>` entries are GONE.

- [ ] **Step 3: rdd-doctor final pass**

Run: `bash skills/rdd-doctor/scripts/doctor.sh`
Expected: 0 CRITICAL, no path-related WARNING

---

## Aggregate commit (execute → archive transition)

**Per the v2.0.5+ Worktree Commit Flow rule, all task changes aggregate into a SINGLE commit.**

After all 9 tasks complete:
- [ ] **Step 1: git add -A in worktree**

Run: `cd .rddf/wt/migrate-improvements-to-rddf-namespace && git add -A`
Expected: all changes staged

- [ ] **Step 2: Verify single commit candidate**

Run: `git status --short | wc -l`
Expected: should match expected file count (134 moves + ~50 modifications + 1 new ADR = ~185)

- [ ] **Step 3: Aggregate commit**

Run: `git commit -m "refactor(rdd-workflow): migrate improvements/ → .rddf/improvements/ for plugin filter (saves ~4,887 tokens)

- 133 improvement files moved to .rddf/improvements/ (git rename preserves history)
- 134 markdown links in proposal-approved.md updated
- 37 skills/_lib/ path constants updated
- 11 test fixture files updated
- 5 docs/ files updated
- ADR-0026 created (dot-prefix internal metadata namespace convention)
- All 8 acceptance criteria verified"
`
Expected: 1 commit created

- [ ] **Step 4: Verify commit on branch**

Run: `git log --oneline -3`
Expected: HEAD on openspec/migrate-improvements-to-rddf-namespace, our commit on top of ce44eed

---

## Final state

After completion, guide-ship Phase 3 (archive) takes over:
- merge worktree branch to master (--no-ff)
- openspec archive migrate-improvements-to-rddf-namespace
- cleanup worktree + branch
- AC-5 verified by user (opencode restart, available_skills shrunk)
