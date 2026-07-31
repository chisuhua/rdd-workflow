# fix-add-improve-initial-prompt-ux Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `skill_use("add-improve")` no-argument UX where question tool blocks free-text input — modify 3 SKILL.md files to enforce open-prompt first interaction.

**Architecture:** Pure documentation change — no code changes. Modify 3 SKILL.md files to add interaction rules: Phase 0 for no-arg mode (add-improve), open-prompt-first rule (brainstorm), and question-tool applicability guide (guide). Each file is independent, so tasks can be done in any order.

**Tech Stack:** Markdown only

---

## File Structure

| File | Responsibility |
|---|---|
| `skills/add-improve/SKILL.md` | Add Phase 0 — no-argument mode UX flow |
| `skills/rdd-workflow-brainstorm/SKILL.md` | Fix line 95: "首选选择题" → open-prompt first |
| `skills/guide/SKILL.md` | Add "输入模式判别" section with decision tree |

---

### Task 1: add-improve/SKILL.md — Phase 0 无参数模式

**Files:**
- Modify: `skills/add-improve/SKILL.md` (before existing Phase 1)

- [ ] **Step 1: Read the current file**

Read `skills/add-improve/SKILL.md` to find the insertion point before Phase 1.

- [ ] **Step 2: Add Phase 0 section**

Add a new section after the frontmatter and overview, before Phase 1:

```markdown
## Phase 0 — 无参数模式

**入口条件**：`skill_use("add-improve")` 无参数调用。

**<HARD-GATE>**：无参数模式下第一轮**不得**使用 `question` 工具弹出多选菜单。

**行为**：

1. AI 必须使用纯文本 prompt 向用户收集改进描述。
2. prompt 模板：
   > "请用自然语言描述你想改进的内容（包含: 症状/痛点/期望效果/优先级/是否引用 ADR）"
3. 禁用清单：
   - 不允许把"描述改进"做成多选题
   - 不允许假设用户会用 `<name>` CLI 参数

**后续澄清**：用户描述改进后，后续的优先级/范围/分类等子项可以使用 `question` 工具选择题。
```

- [ ] **Step 3: Verify the insertion**

Run: `grep -c "Phase 0" skills/add-improve/SKILL.md`
Expected: 1 (the new heading)

- [ ] **Step 4: Commit**

```bash
git add skills/add-improve/SKILL.md
git commit -m "feat: add Phase 0 no-arg mode to add-improve SKILL.md"
```

---

### Task 2: rdd-workflow-brainstorm/SKILL.md — 第 95 行规则重写

**Files:**
- Modify: `skills/rdd-workflow-brainstorm/SKILL.md` (line 95)

- [ ] **Step 1: Read line 95 context**

Read `skills/rdd-workflow-brainstorm/SKILL.md` around line 95 to find the exact text.

- [ ] **Step 2: Replace "首选选择题" rule**

Replace the text at line 95 (or wherever "首选选择题" appears):

Old: `"首选选择题"`
New: `"初始描述收集必须开放；后续澄清可选择题"`

Then add after it:
```markdown
**OPEN-PROMPT 触发条件**（以下场景必须使用开放 prompt，禁用 question 工具）：
- 无参数调用 skill
- 用户首次表达意图
- 初始需求收集阶段
```

- [ ] **Step 3: Verify the change**

Run: `grep -n "首选选择题" skills/rdd-workflow-brainstorm/SKILL.md`
Expected: no output (replaced)

- [ ] **Step 4: Commit**

```bash
git add skills/rdd-workflow-brainstorm/SKILL.md
git commit -m "fix: replace '首选选择题' with open-prompt-first rule in brainstorm SKILL.md"
```

---

### Task 3: guide/SKILL.md — 输入模式判别章节

**Files:**
- Modify: `skills/guide/SKILL.md` (before the menu section)

- [ ] **Step 1: Read the current file**

Read `skills/guide/SKILL.md` to find the right insertion point (before the interactive menu section).

- [ ] **Step 2: Add "输入模式判别" section**

Add a new section before the interactive menu:

```markdown
## 输入模式判别

AI 必须根据场景选择合适的输入收集方式：

**`question` 工具适用场景**：
- 阶段选择（guide-arch / guide-plan / guide-ship）
- session 选择（resume rds_xxx）
- 固定结构化选项（优先级 P0/P1/P2）

**`question` 工具不适用场景**：
- 用户首次描述需求（必须用纯文本 prompt）
- 用户主动要求自由输入时
- 初始需求收集阶段

**判别决策树**：
1. 用户输入是菜单编号或选项名称？→ 视为选中，执行对应 action
2. 用户输入是自然语言问题？→ 进入自由讨论模式
3. 用户连续 2 次未选择明确类别？→ 切换到开放 prompt
4. 否则 → 默认使用 question 工具
```

- [ ] **Step 3: Verify the insertion**

Run: `grep -c "输入模式判别" skills/guide/SKILL.md`
Expected: 1

- [ ] **Step 4: Commit**

```bash
git add skills/guide/SKILL.md
git commit -m "feat: add input mode discrimination section to guide SKILL.md"
```

---

### Task 4: 验证

**Files:**
- No file changes — verification only

- [ ] **Step 1: Verify add-improve keywords**

Run: `grep -E "Phase 0|无参数模式|open prompt" skills/add-improve/SKILL.md`
Expected: all 3 keywords present

- [ ] **Step 2: Verify brainstorm fix**

Run: `grep -n "首选选择题" skills/rdd-workflow-brainstorm/SKILL.md`
Expected: no output (phrase removed)

- [ ] **Step 3: Verify guide section**

Run: `grep -c "输入模式判别" skills/guide/SKILL.md`
Expected: 1

- [ ] **Step 4: Run tests**

Run: `npm test 2>&1 && pytest tests/ -q --tb=short 2>&1`
Expected: all tests pass