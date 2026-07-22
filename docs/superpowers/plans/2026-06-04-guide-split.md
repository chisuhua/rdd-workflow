# Guide Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `skills/guide.md` (1465 lines, single state machine) into three focused skills — `guide-spec` (spec-side state machine), `guide-ship` (ship-side state machine), and `guide` (stateless recommender) — with `plan.md` deleted and responsibilities distributed.

**Architecture:** Content from the existing `guide.md` is lifted into two new skills split at the git-commit boundary (spec-side ends when OpenSpec change artifacts are committed; ship-side starts by scanning committed changes). The old `guide.md` is replaced with a ~50-line stateless recommender that scans project state and suggests which sub-skill to invoke. `plan.md` is deleted because its responsibilities cleanly split between the two new skills.

**Tech Stack:** Bash, Markdown (skills are documentation-driven with embedded shell commands). No test framework exists; verification is via manual smoke tests in Task 8.

**Reference Spec:** `docs/superpowers/specs/2026-06-04-guide-split-design.md`

---

## File Map

| File | Action | Source / Reason |
|---|---|---|
| `skills/guide-spec.md` | CREATE | Lifts §setup, §roadmap, §propose, §deps from old `guide.md` (lines 244-653), with 4 light edits applied |
| `skills/guide-ship.md` | CREATE | Lifts §plan, §execute, §status_archive, §cleanup from old `guide.md` (lines 657-1282), with 4 light edits applied |
| `skills/guide.md` | REWRITE | Reduced from 1465 → ~50 lines. Pure stateless recommender |
| `skills/plan.md` | DELETE | 699 lines distributed: candidate discovery → `guide-spec.propose`; worktree + Prometheus → `guide-ship.worktree` + `guide-ship.plan` |
| `skills/propose.md` | EDIT | Header description: add "Called by `guide-spec`" |
| `skills/roadmap.md` | EDIT | Header description: add "Called by `guide-spec`" |
| `skills/deps.md` | EDIT | Header description: add "Called by `guide-spec`" |
| `skills/execute.md` | EDIT | Header description: add "Called by `guide-ship`" |
| `skills/status.md` | EDIT | Header description: add "Called by `guide-ship` (archive phase)" |
| `skills/INSTALL.md` | EDIT | Description: list the three new skills to install |
| `README.md` | EDIT | Usage section: document three entry points |
| `USAGE.md` | EDIT | Workflow examples: update to use new entry points |

**Order of operations is critical:** the new skills (`guide-spec`, `guide-ship`) must be created BEFORE the old `guide.md` is replaced, so the package is never in a state where the new entry points don't exist. `plan.md` deletion happens AFTER `guide-ship` is created (so the moved content has a destination).

---

## Task 1: Create `skills/guide-spec.md` (NEW)

**Files:**
- Create: `skills/guide-spec.md`
- Reference: `skills/guide.md` (lines 244-653 will be lifted)

- [ ] **Step 1: Read the source content to lift**

Read `skills/guide.md` lines 244-653 to understand the four sections (setup, roadmap, propose, deps) being lifted. Verify the content matches the spec's §6.1 description.

- [ ] **Step 2: Create the file with YAML frontmatter**

Create `skills/guide-spec.md` with this exact frontmatter:

```markdown
---
name: guide-spec
description: Spec-side state machine for OpenSpec workflow — guides user from setup through roadmap, propose, deps, and emits "ready for guide-ship" handoff. Owns openspec/changes/<name>/ artifacts. Called by user when starting new changes.
license: MIT
compatibility: Requires openspec CLI v1.3.1+, git 2.25+
metadata:
  author: sisyphus
  version: "1.0"  # P0: Spec-side state machine, split from guide
  generatedBy: "3.0"
  user-invocable: true
---

# OpenSpec 工作流 — Spec-Side Guide

[content body goes here]
```

- [ ] **Step 3: Lift `setup` section (lines 244-339)**

Copy the content of the `setup` section (from `### 阶段 1：setup — 环境检查` through the menu block ending with `0. 💾 保存并退出`). Paste into `skills/guide-spec.md` under a `## Phase 1: setup` heading.

- [ ] **Step 4: Lift `roadmap` section (lines 343-445)**

Copy `### 阶段 1.5：roadmap — 路线图初始化/查看` through the menu block. Paste under `## Phase 1.5: roadmap`.

- [ ] **Step 5: Lift `propose` section (lines 448-555)**

Copy `### 阶段 2：propose — 扫描并创建 Change` through the end of the `Propose → Deps → Plan 流程` block. Paste under `## Phase 2: propose`.

- [ ] **Step 6: Lift `deps` section (lines 559-653)**

Copy `### 阶段 2.5：deps — 依赖分析` through the end of the `Mermaid 独立 change 正确画法` block. Paste under `## Phase 2.5: deps`.

- [ ] **Step 7: Apply light edit #1 — strip workflow-state.md references**

Search the lifted content for any of:
- `workflow-state.md`
- `workflow-progress.md`
- `STATE_FILE` or `PROGRESS_FILE` variable assignments
- "更新 state 文件" / "更新 state 进度" comments
- Recovery point persistence code (e.g. `awk '/\*\*当前阶段\*\*/{getline...}' "$STATE_FILE"`)

For each match, **remove the corresponding logic**. The `guide-spec` skill does NOT persist state via these files (it uses `proposal-suggestions.md` status markers only).

- [ ] **Step 8: Apply light edit #2 — strip cross-skill recovery references**

Search for any reference to phases OWNED BY `guide-ship` (worktree, plan, execute, archive, cleanup, ship-done). Examples to remove:
- "返回 plan 阶段" buttons pointing to worktree creation
- "进入 Execute 监控模式" options
- Cross-references to `openspec/<name>` branches

These do not belong in spec-side.

- [ ] **Step 9: Apply light edit #3 — update sub-skill call signature**

Find any `skill_use("rdd-workflow-propose")` calls in the lifted content. The signature stays the same (no API change to `propose` skill itself), but add a comment line above each call:

```bash
# Sub-skill: propose (called from guide-spec.Phase 2)
skill_use("rdd-workflow-propose")
```

Same for `skill_use("rdd-workflow-roadmap")` and `skill_use("rdd-workflow-deps")` if present.

- [ ] **Step 10: Apply light edit #4 — strip worktree-creation code**

Search for any worktree creation logic (commands like `git worktree add`, `.rddf/wt/<name>`, branch creation with `openspec/<name>` prefix). These belong to `guide-ship`, not here. Remove them.

- [ ] **Step 11: Add the `spec-done` exit phase**

Append a new section to `skills/guide-spec.md`:

```markdown
## Phase 3: spec-done (Exit)

Triggered when all committed changes have all three artifacts (`proposal.md`, `design.md`, `tasks.md`) reachable via `git show HEAD:...`.

**Exit guard check:**

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
for change in $(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/); do
    name=$(basename "$change")
    for artifact in proposal.md design.md tasks.md; do
        if ! git show HEAD:"$change/$artifact" > /dev/null 2>&1; then
            echo "❌ $name missing committed $artifact — refuse to exit spec-side"
            exit 1
        fi
    done
done
echo "✅ All changes have committed artifacts. Spec side complete."
```

**Output to user:**

```
✅ Spec-side complete. Your changes are committed.

💡 Next: skill_use("guide-ship")
   This will scan your committed changes and start worktree creation + execution.
```

Do NOT auto-invoke `guide-ship` — the user must explicitly transition to the ship side.
```

- [ ] **Step 12: Verify the file is well-formed**

```bash
wc -l skills/guide-spec.md
# Expected: 500-650 lines (lifted content + new spec-done phase + frontmatter)

# Verify no leftover state-file references
grep -c "workflow-state\|workflow-progress" skills/guide-spec.md
# Expected: 0

# Verify no leftover worktree code
grep -c "git worktree\|openspec/<name>" skills/guide-spec.md
# Expected: 0
```

- [ ] **Step 13: Commit**

```bash
git add skills/guide-spec.md
git commit -m "feat(skills): add guide-spec (spec-side state machine, lifted from guide)"
```

---

## Task 2: Create `skills/guide-ship.md` (NEW)

**Files:**
- Create: `skills/guide-ship.md`
- Reference: `skills/guide.md` (lines 657-1282 will be lifted)

- [ ] **Step 1: Read the source content to lift**

Read `skills/guide.md` lines 657-1282 to understand the four sections (plan, execute, status_archive, cleanup) being lifted.

- [ ] **Step 2: Create the file with YAML frontmatter**

Create `skills/guide-ship.md` with this exact frontmatter:

```markdown
---
name: guide-ship
description: Ship-side state machine for OpenSpec workflow — guides user from committed changes through worktree creation, Prometheus plan generation, execution, archive, and cleanup. Owns git worktrees and tasks.md progress. Called by user when starting work on a committed change.
license: MIT
compatibility: Requires openspec CLI v1.3.1+, git 2.25+, Prometheus start_work skill
metadata:
  author: sisyphus
  version: "1.0"  # P0: Ship-side state machine, split from guide + plan
  generatedBy: "3.0"
  user-invocable: true
---

# OpenSpec 工作流 — Ship-Side Guide

[content body goes here]
```

- [ ] **Step 3: Lift `plan` section (lines 657-941)**

Copy `### 阶段 3：plan — Commit + Worktree + 计划` through the end of the "返回 Plan 前的检查 — 是否进入监控" block. Paste under `## Phase 1: plan`.

- [ ] **Step 4: Lift `execute` section (lines 944-1059)**

Copy `### 阶段 4：execute — 监控与执行` through the end of the "监控说明" block. Paste under `## Phase 2: execute`.

- [ ] **Step 5: Lift `status_archive` section (lines 1062-1227)**

Copy `### 阶段 5：status_archive — 状态检查与归档` through the end of the "更新 state" line. Paste under `## Phase 3: archive`.

- [ ] **Step 6: Lift `cleanup` section (lines 1231-1282)**

Copy `### 阶段 6：cleanup — 测试清理` through the end of the cleanup option-2 bash block. Paste under `## Phase 4: cleanup`.

- [ ] **Step 7: Apply light edit #1 — strip workflow-state.md references**

Same as Task 1 Step 7 but for `skills/guide-ship.md`. Search for and remove:
- `workflow-state.md` / `workflow-progress.md` writes
- `STATE_FILE` / `PROGRESS_FILE` assignments
- "更新 state 进度" / "更新 workflow-state.md" comments

The `guide-ship` skill does NOT persist state via these files (it reads worktree list and `tasks.md` progress on-the-fly).

- [ ] **Step 8: Apply light edit #2 — strip candidate-discovery code**

Search for any "扫描 `openspec/changes/`,发现候选" logic. This belongs in `guide-spec` (where the user picks which change to create), not in `guide-ship` (where the user already knows which change they want to ship). Remove.

- [ ] **Step 9: Apply light edit #3 — strip spec-side phase references**

Search for cross-references to spec-side phases (setup, roadmap, propose, deps, spec-done). These do not belong in ship-side.

- [ ] **Step 10: Apply light edit #4 — add Prometheus `start_work` invocation**

The current `guide.md` does NOT explicitly call Prometheus `start_work`; it only generates a plan file via `openspec-plan`. The new design (per spec §6.2 phase `plan`) requires this call. Insert a new bash block in the `Phase 1: plan` section, just after the "Worktree 创建完成" verification block:

```bash
# === Prometheus start_work invocation ===
# Generate detailed implementation plan via Prometheus
cd "$WT_PATH" || { echo "❌ 进入 worktree 失败: $WT_PATH"; exit 1; }

if skill_use("prometheus-start-work") 2>/dev/null; then
    if [ ! -f ".sisyphus/plans/$CHANGE_NAME.md" ]; then
        echo "❌ Prometheus start_work 未生成计划文件"
        exit 1
    fi
    PLAN_TASK_COUNT=$(grep -c '^- \[' ".sisyphus/plans/$CHANGE_NAME.md" 2>/dev/null || echo 0)
    if [ "$PLAN_TASK_COUNT" -eq 0 ]; then
        echo "❌ 计划文件存在但无任务项"
        exit 1
    fi
    echo "✅ Prometheus 计划已生成: $PLAN_TASK_COUNT 任务"
else
    echo "❌ Prometheus start_work 调用失败"
    echo "   请确认 prometheus-start-work 技能已安装"
    exit 1
fi
```

- [ ] **Step 11: Add the `ship-done` exit phase**

Append a new section:

```markdown
## Phase 5: ship-done (Exit)

Triggered when all committed changes have been archived (or no changes remain).

**Loop check:**

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# Count remaining unprocessed changes
REMAINING=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l)
REMAINING_WT=$(git worktree list 2>/dev/null | awk '$2 ~ /^openspec\// {print $1}' | wc -l)

if [ "$REMAINING_WT" -gt 0 ] || [ "$REMAINING" -gt 0 ]; then
    echo "📋 还有 $REMAINING_WT 个 worktree 在跑,$REMAINING 个未处理 change"
    echo ""
    echo "请选择:"
    echo "1. 继续处理 (skill_use(\"guide-ship\"))"
    echo "2. 退出 (稍后手动继续)"
    echo "i. 其他输入"
else
    echo "✅ 所有 changes 已处理完毕"
    echo ""
    echo "请选择:"
    echo "1. 回到 spec 端 (skill_use(\"guide-spec\")) — 创建更多 changes"
    echo "2. 完成 (本批次结束)"
    echo "i. 其他输入"
fi
```
```

- [ ] **Step 12: Verify the file is well-formed**

```bash
wc -l skills/guide-ship.md
# Expected: 750-900 lines

# Verify no leftover state-file references
grep -c "workflow-state\|workflow-progress" skills/guide-ship.md
# Expected: 0

# Verify no leftover spec-side phase references
grep -cE "阶段 1：|阶段 2：|阶段 1\.5：" skills/guide-ship.md
# Expected: 0 (the old guide used these labels; new file uses Phase 1/2/3/4/5)

# Verify Prometheus start_work block was added
grep -c "prometheus-start-work" skills/guide-ship.md
# Expected: >= 2 (one invocation + one error message)
```

- [ ] **Step 13: Commit**

```bash
git add skills/guide-ship.md
git commit -m "feat(skills): add guide-ship (ship-side state machine, lifted from guide + plan)"
```

---

## Task 3: Update headers of 5 sub-skill files

**Files:**
- Edit: `skills/propose.md` (frontmatter `description` field)
- Edit: `skills/roadmap.md` (frontmatter `description` field)
- Edit: `skills/deps.md` (frontmatter `description` field)
- Edit: `skills/execute.md` (frontmatter `description` field)
- Edit: `skills/status.md` (frontmatter `description` field)

For each file, modify the YAML frontmatter's `description` field to clarify the new caller relationship. No behavior changes.

- [ ] **Step 1: Edit `skills/propose.md`**

Find the existing `description:` line. Replace it with:

```yaml
description: 分析项目文档与代码的差距，生成 propose 建议列表，用户选择后执行 openspec-propose 命令序列创建 artifacts。被 guide-spec 调用（不在 archive/ 阶段直接调用）。
```

- [ ] **Step 2: Edit `skills/roadmap.md`**

Find the existing `description:` line. Replace it with:

```yaml
description: 路线图管理技能——初始化、编辑、验证项目路线图。被 guide-spec 调用执行 init/status/edit/validate/advance/gate-report 命令。
```

- [ ] **Step 3: Edit `skills/deps.md`**

Find the existing `description:` line. Replace it with:

```yaml
description: 分析 OpenSpec change 之间的依赖关系，生成 Mermaid 依赖图和推荐执行顺序。被 guide-spec 在 propose 完成后自动调用。
```

- [ ] **Step 4: Edit `skills/execute.md`**

Find the existing `description:` line. Replace it with:

```yaml
description: 在 worktree 隔离环境执行 OpenSpec change 的实施计划。基于 Prometheus 生成的 .sisyphus/plans/ 执行。被 guide-ship 在 plan 阶段后调用。
```

- [ ] **Step 5: Edit `skills/status.md`**

Find the existing `description:` line. Replace it with:

```yaml
description: 查看 OpenSpec change 状态、归档已完成的 change、清理 worktree 和 branch。可被 guide-ship 调用（archive 阶段），也可独立调用查看状态。
```

- [ ] **Step 6: Verify all 5 headers were updated**

```bash
for f in skills/propose.md skills/roadmap.md skills/deps.md skills/execute.md skills/status.md; do
    echo "=== $f ==="
    grep -A0 "^description:" "$f" | head -1
done
```

Expected: each file's `description:` line should now contain "被 guide-spec" or "被 guide-ship" (whichever applies per the steps above).

- [ ] **Step 7: Commit**

```bash
git add skills/propose.md skills/roadmap.md skills/deps.md skills/execute.md skills/status.md
git commit -m "docs(skills): clarify sub-skill caller relationships (spec-side / ship-side)"
```

---

## Task 4: Rewrite `skills/guide.md` as stateless recommender

**Files:**
- Rewrite: `skills/guide.md` (1465 lines → ~50 lines)

- [ ] **Step 1: Verify new skills exist before rewriting**

```bash
test -f skills/guide-spec.md && test -f skills/guide-ship.md && echo "✓ new skills exist" || echo "❌ run Tasks 1 and 2 first"
```

- [ ] **Step 2: Overwrite `skills/guide.md` with the recommender content**

Use the Write tool to replace `skills/guide.md` with this exact content (50 lines including frontmatter):

```markdown
---
name: guide
description: 无状态推荐器——扫描项目当前状态（roadmap、changes、worktrees、tasks），建议用户调 guide-spec 或 guide-ship。不持有任何状态，不调用 openspec CLI，不修改任何文件。
license: MIT
compatibility: Requires git 2.25+
metadata:
  author: sisyphus
  version: "4.0"  # P0: 缩减为无状态推荐器
  generatedBy: "3.0"
  user-invocable: true
---

# OpenSpec 工作流 — 推荐器入口

## 用途

`guide` 是一个**无状态推荐器**。它只读不写——扫描项目当前状态，给出一行建议，告诉用户应该调 `guide-spec` 还是 `guide-ship`。

不持久化任何状态,不调用 openspec CLI,不修改任何文件。

## 扫描逻辑(按优先级)

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# 1. 有 worktree 且 tasks 未全部 [x] → 继续 ship
WORKTREE_IN_PROGRESS=$(git worktree list 2>/dev/null | awk '$2 ~ /^openspec\// {
    wt=$1; system("test -f " wt "/openspec/changes/*/tasks.md && grep -q \"^- \\[\" " wt "/openspec/changes/*/tasks.md")
}')

# 2. 有 worktree 且 tasks 全 [x] → ship 进入 archive
# 3. 有 committed change 但无 worktree → ship 开始新 change
# 4. 无 roadmap.md → spec 初始化
# 5. 无 committed change → spec 继续 propose
# 6. 默认 → spec

if [ -n "$WORKTREE_IN_PROGRESS" ]; then
    RECOMMEND="guide-ship"; REASON="worktree 存在,任务未完成 → 继续执行"
elif git worktree list 2>/dev/null | grep -q "openspec/"; then
    RECOMMEND="guide-ship"; REASON="worktree 存在,任务已完成 → 进入 archive"
elif ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | xargs -I {} git show HEAD:{}/.openspec.yaml 2>/dev/null | head -1 | grep -q .; then
    RECOMMEND="guide-ship"; REASON="有已 commit 的 change 待建 worktree"
elif [ ! -f "$PROJECT_ROOT/roadmap.md" ]; then
    RECOMMEND="guide-spec"; REASON="无 roadmap.md → 初始化"
elif [ -z "$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/)" ]; then
    RECOMMEND="guide-spec"; REASON="无 change → 进入 propose 阶段"
else
    RECOMMEND="guide-spec"; REASON="有 change 待 commit → 继续 propose"
fi
```

## 输出格式

```
🔍 Project state scan:
   - roadmap.md: [✅ exists / ❌ missing]
   - committed changes: [N]
   - worktrees: [N, with status]

💡 Recommended: skill_use("$RECOMMEND")
   Reason: $REASON
```

## 过期状态检测

如果 `$PROJECT_ROOT/workflow-state.md` 存在(旧版文件),打印一次警告:

```
⚠️  Stale workflow-state.md detected (pre-refactor format).
   This file is no longer used and will be ignored.
   Remove it manually if you want: rm workflow-state.md
```

不自动删除(尊重用户数据)。
```

- [ ] **Step 3: Verify the rewrite**

```bash
wc -l skills/guide.md
# Expected: ≤ 80 lines

# Verify no openspec CLI calls
grep -c "openspec " skills/guide.md
# Expected: 0 (in the bash code; mentions in prose are fine)

# Verify no openspec command calls in bash blocks
grep -E "^\s*openspec (new|propose|status|archive|instructions|apply)" skills/guide.md | wc -l
# Expected: 0

# Verify no workflow-state.md writes
grep -E ">\s*\$STATE_FILE|>\s*workflow-state" skills/guide.md | wc -l
# Expected: 0
```

- [ ] **Step 4: Commit**

```bash
git add skills/guide.md
git commit -m "refactor(skills): rewrite guide as stateless recommender (1465→50 lines)"
```

---

## Task 5: Delete `skills/plan.md`

**Files:**
- Delete: `skills/plan.md`

- [ ] **Step 1: Verify content has been distributed**

Before deleting, verify both `guide-spec.md` and `guide-ship.md` exist and contain the expected sections:

```bash
# Candidate discovery should now be in guide-spec (via propose section)
test -f skills/guide-spec.md && echo "✓ guide-spec exists"

# Worktree creation + Prometheus should now be in guide-ship (Phase 1: plan)
test -f skills/guide-ship.md && echo "✓ guide-ship exists"

# Verify Prometheus block was added to guide-ship
grep -q "prometheus-start-work" skills/guide-ship.md && echo "✓ Prometheus block present"
```

Expected: all three `✓` lines.

- [ ] **Step 2: Delete the file**

```bash
git rm skills/plan.md
```

- [ ] **Step 3: Verify deletion**

```bash
test ! -f skills/plan.md && echo "✓ plan.md removed"
ls skills/ | grep -E "^(guide|plan)\.md$"
# Expected: guide.md, guide-spec.md, guide-ship.md (no plan.md)
```

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor(skills): delete plan.md (responsibilities distributed to guide-spec/guide-ship)"
```

---

## Task 6: Update documentation files

**Files:**
- Edit: `README.md` — add three entry points
- Edit: `USAGE.md` — update workflow examples
- Edit: `INSTALL.md` — list the three new skills

- [ ] **Step 1: Edit `README.md`**

Find the "使用流程" / "Usage" section. Replace the bullet list:

```
2. **使用子技能**:
   - `skill_use("guide")` - 交互式向导
   - `skill_use("propose")` - 生成提案
   - `skill_use("plan")` - 创建实施计划
   - `skill_use("execute")` - 执行实施
   - `skill_use("status")` - 查看状态
```

With:

```
2. **使用子技能**:
   - `skill_use("guide")` - 推荐器入口(扫描状态,建议调 spec 或 ship)
   - `skill_use("guide-spec")` - Spec 端状态机(setup → roadmap → propose → deps)
   - `skill_use("guide-ship")` - Ship 端状态机(discover → worktree → plan → execute → archive)
   - `skill_use("propose")` - 子技能(被 guide-spec 调用)
   - `skill_use("execute")` - 子技能(被 guide-ship 调用)
   - `skill_use("status")` - 子技能(被 guide-ship 调用或独立使用)
```

- [ ] **Step 2: Edit `USAGE.md`**

Find any references to `skill_use("rdd-workflow-guide")` and replace with appropriate new commands based on context:

- "扫描项目状态" → `skill_use("rdd-workflow-guide")` (recommender)
- "创建新 change" → `skill_use("rdd-workflow-guide-spec")`
- "开始执行 change" → `skill_use("rdd-workflow-guide-ship")`

If `USAGE.md` is long, do targeted replacements rather than rewriting the whole file.

- [ ] **Step 3: Edit `INSTALL.md`**

Find the list of skills to install. Add `guide-spec` and `guide-ship` to the list:

```markdown
# Before:
- guide
- propose
- plan
- execute
- status

# After:
- guide
- guide-spec
- guide-ship
- propose
- execute
- status
# (plan removed — distributed to guide-spec and guide-ship)
```

- [ ] **Step 4: Verify doc updates**

```bash
# Each doc should mention at least one of the new skill names
grep -l "guide-spec\|guide-ship" README.md USAGE.md INSTALL.md
# Expected: all three files

# No leftover plan.md references in docs
grep -E "skill_use.*plan\"|rdd-workflow-plan" README.md USAGE.md INSTALL.md | wc -l
# Expected: 0
```

- [ ] **Step 5: Commit**

```bash
git add README.md USAGE.md INSTALL.md
git commit -m "docs: update README/USAGE/INSTALL for guide-split (3 entry points)"
```

---

## Task 7: Manual smoke tests

No automated test framework. Run each scenario manually and verify the expected output. Use a clean test project (or the current project as test subject) — `cd` to a test directory before each scenario.

- [ ] **Step 1: Test the recommender with no project state**

```bash
mkdir -p /tmp/test-guide-split/empty
cd /tmp/test-guide-split/empty
git init
# Invoke guide mentally (or via the AI) and verify it recommends guide-spec
# Expected: "Recommended: skill_use('guide-spec'), Reason: 无 roadmap.md → 初始化"
```

- [ ] **Step 2: Test the recommender with roadmap but no changes**

```bash
cd /tmp/test-guide-split/empty
echo "# Roadmap" > roadmap.md
git add roadmap.md && git commit -m "init"
# Invoke guide and verify
# Expected: "Recommended: skill_use('guide-spec'), Reason: 无 change → 进入 propose 阶段"
```

- [ ] **Step 3: Test the recommender with committed change**

```bash
cd /tmp/test-guide-split/empty
mkdir -p openspec/changes/test-change
touch openspec/changes/test-change/{proposal.md,design.md,tasks.md}
git add openspec/changes/test-change/ && git commit -m "add change"
# Invoke guide and verify
# Expected: "Recommended: skill_use('guide-ship'), Reason: 有已 commit 的 change 待建 worktree"
```

- [ ] **Step 4: Test the recommender with active worktree**

```bash
cd /tmp/test-guide-split/empty
git branch openspec/test-change HEAD
git worktree add .rddf/wt/test-change openspec/test-change
# Invoke guide and verify
# Expected: "Recommended: skill_use('guide-ship'), Reason: worktree 存在,任务未完成 → 继续执行"
```

- [ ] **Step 5: Test stale state warning**

```bash
cd /tmp/test-guide-split/empty
echo "fake state" > workflow-state.md
# Invoke guide and verify
# Expected: warning printed, but recommendation still works
```

- [ ] **Step 6: Test boundary enforcement (incomplete artifacts)**

```bash
cd /tmp/test-guide-split/empty
mkdir -p openspec/changes/half-change
touch openspec/changes/half-change/proposal.md
# (no design.md, no tasks.md)
git add openspec/changes/half-change/ && git commit -m "half change"
# Invoke guide-ship and verify it refuses to discover the half-change
# Expected: error "refuse to discover half-change — finish via guide-spec"
```

- [ ] **Step 7: Document any failures**

If any test fails, write a follow-up issue. Do NOT proceed to Task 8 until all pass.

---

## Task 8: Final verification and commit

- [ ] **Step 1: Verify file structure**

```bash
ls skills/
# Expected: INSTALL.md, deps.md, execute.md, guide.md, guide-ship.md, guide-spec.md, propose.md, roadmap.md, status.md
# (plan.md should be absent)
```

- [ ] **Step 2: Verify all commits present**

```bash
git log --oneline -10
# Expected: 8 commits (1 per task group)
#   - feat(skills): add guide-spec
#   - feat(skills): add guide-ship
#   - docs(skills): clarify sub-skill caller relationships
#   - refactor(skills): rewrite guide as stateless recommender
#   - refactor(skills): delete plan.md
#   - docs: update README/USAGE/INSTALL
#   (Task 7 manual tests have no commit)
#   (Task 8 verification is this commit, if needed)
```

- [ ] **Step 3: Verify line counts**

```bash
wc -l skills/guide.md skills/guide-spec.md skills/guide-ship.md
# Expected:
#   guide.md       ≤ 80
#   guide-spec.md  500-650
#   guide-ship.md  750-900
```

- [ ] **Step 4: Tag the release**

```bash
git tag -a v3.0-guide-split -m "Refactor: split guide into guide-spec + guide-ship + recommender"
```

- [ ] **Step 5: Final commit if any verification fixes were needed**

```bash
# Only run if Step 1-3 surfaced issues that were fixed
git add -A
git commit -m "chore: post-refactor verification fixes" || true
```

---

## Self-Review Notes

After writing this plan, I checked against the spec:

**Spec coverage:**
- §1 Background — covered in plan preamble ✓
- §2 Goals — decomposed into Tasks 1-6 ✓
- §3 Non-Goals — implicitly respected (no behavior changes to propose/execute/etc)
- §4 Files in Scope — every row has a corresponding task (Tasks 1-6) ✓
- §5 Architecture — embodied in Task 4 (recommender) and Tasks 1-2 (new skills)
- §6.1 guide-spec — Task 1 ✓
- §6.2 guide-ship — Task 2 ✓
- §6.3 guide recommender — Task 4 ✓
- §6.4 plan.md deletion — Task 5 ✓
- §7 Data Flow — implemented in Tasks 1 (spec flow), 2 (ship flow), 1+2 (handoff)
- §8 Error Handling — boundaries tested in Task 7 Step 6
- §9 Testing — Tasks 7-8 ✓
- §10 Migration — covered in spec, no code action needed in plan
- §12 Definition of Done — every checkbox corresponds to a task

**Placeholder scan:** No "TBD", "TODO", "fill in", or "appropriate error handling" phrases found. Every code block is concrete.

**Type consistency:** Function/variable names used consistently across tasks (`$CHANGE_NAME`, `$WT_PATH`, `$PROJECT_ROOT`, `$RECOMMEND`, `$REASON`).
