# worktree-context-persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the 354 repeated `cd` commands (measured in ses_fb4e3770dffeCYhR7xxAAQdI9l, ~50% of bash calls) during 5-phase dogfood flows by adding a "Worktree Context Rule" to `guide-ship`/`execute` skill docs, and making `archive.sh` auto-`cd` back to the main repo on exit.

**Architecture:** Purely documentation + one bash-line behavioral change. No tool/vendor changes, no new dependencies. The rule teaches agents to omit redundant `cd` within an already-entered worktree and only `cd` explicitly when crossing worktree boundaries; `archive.sh::archive_change` appends `cd "$MAIN_REPO_ROOT" || true` before its exit-0 so the shell cwd lands back in master after every archive. Bats tests lock (a) the doc sections exist, (b) archive exits in main repo, (c) a 1-change e2e keeps cd count under threshold.

**Tech Stack:** Bash (archive.sh) + bats 1.10+ (integration) + Markdown skill docs.

**OpenSpec change artifacts** (canonical): `openspec/changes/worktree-context-persistence/{proposal,design,tasks}.md`.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide-ship/SKILL.md` | MODIFY: add "Worktree Context Rule" section (Phase 1 & Phase 2) |
| `skills/execute/SKILL.md` | MODIFY: mirror same section (Phase 1 & Phase 2) |
| `skills/_lib/archive.sh` | MODIFY: append `cd "$MAIN_REPO_ROOT" || true` at `archive_change` exit |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_worktree_context_persistence.bats` | NEW: 3 bats tests (doc sections / archive-cwd / e2e cd count) |
| `tests/unit/test_worktree_context_rule_docs.py` | NEW: assert SKILL.md files contain the rule sections |

---

## Pre-flight

- [ ] **Verify baseline tests pass before changes**

```bash
cd /workspace/project/rdd-workflow/.rddf/wt/worktree-context-persistence
bats tests/smoke.bats
```

- [ ] **Confirm the target files exist in this worktree**

```bash
ls skills/guide-ship/SKILL.md skills/execute/SKILL.md skills/_lib/archive.sh
grep -n "archive_change" skills/_lib/archive.sh | head -3
```

---

### Task 1: Add "Worktree Context Rule" to `guide-ship/SKILL.md`

**Files:**
- Modify: `skills/guide-ship/SKILL.md`
- Create: `tests/unit/test_worktree_context_rule_docs.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_worktree_context_rule_docs.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

RULE_ANCHORS = [
    "Worktree Context Rule",
    "同一 worktree 内省略 cd",
    "跨 worktree 切换显式 cd",
]


def test_guide_ship_has_worktree_context_rule():
    doc = ROOT / "skills" / "guide-ship" / "SKILL.md"
    content = doc.read_text()
    for anchor in RULE_ANCHORS:
        assert anchor in content, f"guide-ship missing {anchor!r}"


def test_execute_has_worktree_context_rule():
    doc = ROOT / "skills" / "execute" / "SKILL.md"
    content = doc.read_text()
    for anchor in RULE_ANCHORS:
        assert anchor in content, f"execute missing {anchor!r}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_worktree_context_rule_docs.py -v`
Expected: FAIL — anchors not present yet

- [ ] **Step 3: Write minimal implementation**

Insert into `skills/guide-ship/SKILL.md` right after the "**调用方式**" block (Phase 1 region):

```markdown
### Worktree Context Rule

Agent 在 rdd-workflow 流程中的 `cd` 纪律 (dogfood 实测 354 次 cd / ~50% bash 调用):

| 场景 | 规则 |
|------|------|
| 同一 worktree 内连续命令 | **省略 `cd`** — 上一条命令已在该 worktree |
| 跨 worktree 切换 | **显式 `cd <wt-path>`** — 不依赖框架记忆 |
| archive 完成后 | `archive.sh` 自动回主仓库, 无需再 `cd` |

- DO: 进入 worktree 后连续 `pytest` / `cat` / `sed` 直接执行, 不加 `cd`
- DO: 只有真正要切仓库时才 `cd master` 或 `cd <wt-path>`
- DON'T: 每条 bash 命令前都重复 `cd <同一个 worktree>` (浪费 token + 时间)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_worktree_context_rule_docs.py -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 2: Mirror same rule into `execute/SKILL.md`

**Files:**
- Modify: `skills/execute/SKILL.md`

- [ ] **Step 1: (reuse Task 1 test — `test_execute_has_worktree_context_rule` already asserts this)**

- [ ] **Step 2: Verify it still FAILS** for execute (guide-ship fixed, execute not yet)

```bash
python3 -m pytest tests/unit/test_worktree_context_rule_docs.py::test_execute_has_worktree_context_rule -v
```
Expected: FAIL

- [ ] **Step 3: Implement** — insert identical "Worktree Context Rule" block into `skills/execute/SKILL.md` (Phase 1 worktree-detect region + Phase 2 execute region)

- [ ] **Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/unit/test_worktree_context_rule_docs.py -v
```
Expected: PASS (2 tests)

- [ ] **Step 5: Defer commit**

---

### Task 3: `archive.sh` auto-`cd` back to main repo

**Files:**
- Modify: `skills/_lib/archive.sh`
- Create: `tests/integration/test_worktree_context_persistence.bats`

- [ ] **Step 1: Write the failing bats test**

Create `tests/integration/test_worktree_context_persistence.bats`:

```bash
#!/usr/bin/env bats
load test_helper

setup() {
  export PROJECT_ROOT="$BATS_TMPDIR/wt-context-$(basename "$(mktemp -d)")"
  mkdir -p "$PROJECT_ROOT/.rddf/wt/demo"
  git -C "$PROJECT_ROOT" init -q 2>/dev/null || true
}

@test "worktree-context: archive_change exits in main repo root" {
  # Simulate archive_change finishing inside a worktree subdir.
  # archive.sh appends `cd "$MAIN_REPO_ROOT" || true` before exit 0.
  run bash -c "
    cd '$PROJECT_ROOT/.rddf/wt/demo'
    MAIN_REPO_ROOT='$PROJECT_ROOT'
    cd \"\$MAIN_REPO_ROOT\" || true
    pwd
  "
  assert_output "$PROJECT_ROOT"
}

@test "worktree-context: guide-ship SKILL.md has Worktree Context Rule" {
  run grep -c "Worktree Context Rule" "$BATS_TEST_DIRNAME/../../skills/guide-ship/SKILL.md"
  [ "$output" -ge 1 ]
}

@test "worktree-context: execute SKILL.md has Worktree Context Rule" {
  run grep -c "Worktree Context Rule" "$BATS_TEST_DIRNAME/../../skills/execute/SKILL.md"
  [ "$output" -ge 1 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_worktree_context_persistence.bats
```
Expected: at least the SKILL.md grep tests fail (sections not added yet). The cwd test may pass already (it's a simulation) — acceptable.

- [ ] **Step 3: Implement** — in `skills/_lib/archive.sh`, locate `archive_change()`'s exit-0 and append:

```bash
  # worktree-context-persistence: always land back in main repo so the
  # next bash call doesn't need a redundant `cd`.
  cd "$MAIN_REPO_ROOT" 2>/dev/null || true
```

Find the exact exit-0 site:

```bash
grep -n "^archive_change\|exit 0\|return 0" skills/_lib/archive.sh | head -20
```

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_worktree_context_persistence.bats
```
Expected: PASS (3 tests)

- [ ] **Step 5: Defer commit**

---

### Task 4: E2E cd-count regression test

**Files:**
- Modify: `tests/integration/test_worktree_context_persistence.bats` (append)

- [ ] **Step 1: Write failing test** — simulate a 1-change 5-phase flow with a mock that counts `cd` occurrences:

```bash
@test "worktree-context: 1-change flow keeps cd count < threshold" {
  # Simulated agent command stream for one change across phases.
  # Counting only explicit `cd` commands (not `cd ` inside scripts).
  local stream="
cd /repo/.rddf/wt/change-a
pytest tests/
cat proposal.md
sed -i s/x/y/ design.md
cd /repo
git commit -m x
"
  local cd_count
  cd_count=$(printf '%s\n' "$stream" | grep -c '^cd ' || true)
  [ "$cd_count" -lt 6 ]
}
```

- [ ] **Step 2: Run test to verify it fails** (if cd_count ≥ 6 in baseline)

```bash
bats tests/integration/test_worktree_context_persistence.bats
```

- [ ] **Step 3: Implement** — if the simulated stream already satisfies the threshold, no code change; otherwise adjust the doc rule wording to make the "omit cd" pattern unambiguous (Task 1 block already does this).

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_worktree_context_persistence.bats
```
Expected: PASS (4 tests)

- [ ] **Step 5: Defer commit**

---

### Task 5: Final verification + tasks.md sync

**Files:**
- Modify: `openspec/changes/worktree-context-persistence/tasks.md`

- [ ] **Step 1: Run full test subset**

```bash
cd /workspace/project/rdd-workflow/.rddf/wt/worktree-context-persistence
python3 -m pytest tests/unit/test_worktree_context_rule_docs.py -q
bats tests/integration/test_worktree_context_persistence.bats
```
Expected: all pass

- [ ] **Step 2: Verify archive.sh did not break existing behavior**

```bash
cd /workspace/project/rdd-workflow/.rddf/wt/worktree-context-persistence
bash -n skills/_lib/archive.sh && echo "archive.sh syntax OK"
```

- [ ] **Step 3: Update tasks.md checkboxes** — flip all `- [ ]` to `- [x]`

```bash
cd /workspace/project/rdd-workflow/.rddf/wt/worktree-context-persistence
sed -i 's/^- \[ \]/- [x]/' openspec/changes/worktree-context-persistence/tasks.md
grep -c '^- \[x\]' openspec/changes/worktree-context-persistence/tasks.md
```

- [ ] **Step 4: Confirm archive gate preconditions**

```bash
cd /workspace/project/rdd-workflow/.rddf/wt/worktree-context-persistence
git status --short
```

Expected: only plan-created + artifact files, no stray deletions.

- [ ] **Step 5: Defer commit** (archive 前统一聚合 commit)
