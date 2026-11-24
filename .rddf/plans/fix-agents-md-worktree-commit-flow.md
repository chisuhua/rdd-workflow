# fix-agents-md-worktree-commit-flow Implementation Plan (P0-1)

> **For agentic workers:** Implement this plan task-by-task, following the TDD 5-step structure below. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `AGENTS.md` 补上 `### Worktree Commit Flow` 与 `### 归档流程` 两段，使既有的 6 条 bats 断言由红转绿，并把 `tests/KNOWN_FAILURES.txt` 的对应 6 条基线条目移除（基线 10 → 4）。

**Architecture:** 本 change **只改两个文件**：`AGENTS.md`（加两段正文）与 `tests/KNOWN_FAILURES.txt`（移除 6 条已转绿的基线条目）。**不改任何 `.sh` / `.py` / `.bats` 文件** —— 断言 `tests/integration/test_worktree_archive_workflow_docs.bats`（6 个用例）早已存在且当前为红；本 change 让实现追上断言。

**Tech Stack:** Markdown（AGENTS.md）+ 纯文本基线文件（KNOWN_FAILURES.txt）+ bats 1.13（既有断言，只跑不改）。

---

## File Structure

### Production Code (MODIFY)

| File | Responsibility |
|---|---|
| `AGENTS.md` | 新增 `### Worktree Commit Flow`（含 5 种 conventional commit type）+ `### 归档流程`（交叉引用 `check_worktree_commits`）两段 —— 位置紧邻现有的 `### Archive 前全量回归门（MANDATORY）`，**不得**插入 `<!-- AUTO: feature fragments start -->` / `<!-- AUTO: objectives start -->` 哨兵段内部 |
| `tests/KNOWN_FAILURES.txt` | 移除 6 条 AGENTS.md 族基线条目（其余 4 条不动），并补一条 refresh summary 注释 |

### Tests (既有，不改)

| File | Responsibility |
|---|---|
| `tests/integration/test_worktree_archive_workflow_docs.bats` | 6 个用例 —— 本 change 的验收断言，由红转绿。**只跑不改** |

---

## Pre-flight

- [ ] **Step 0.1: 确认断言当前为红（基线事实）**

```bash
bats tests/integration/test_worktree_archive_workflow_docs.bats
```

Expected: 6 failed（当前 AGENTS.md 无 `### Worktree Commit Flow` / `### 归档流程` 段）
⚠️ 这 6 条是 `tests/KNOWN_FAILURES.txt` 里已登记的已知失败 —— 它们**转绿不构成「新增失败」**。

---

### Task 1: AGENTS.md 新增 `### Worktree Commit Flow` 段

**Files:**
- Modify: `AGENTS.md`（在 `### Archive 前全量回归门（MANDATORY）` 段之后插入）

- [ ] **Step 1.1: 写下目标文本（满足 5 条断言的最小形态）**

断言与文本的对应关系（**按测试的真实语义写，不是按直觉写**）：

| 断言 | 测试里的实际命令 | 文本必须满足 |
|---|---|---|
| `section exists` | `grep -c "^### Worktree Commit Flow"` | **H3**（3 个 `#`）标题行，恰好 `### Worktree Commit Flow` |
| `mentions execute and archive phases` | `grep -E "Phase 2 execute\|Phase 3 archive"` | 出现**字面量** `Phase 2 execute` 与 `Phase 3 archive` |
| `lists 5 conventional commit types` | `grep -cE "^   - \`[a-z]+\(<scope>\):"` | **≥ 5 行**，且每行是 **3 空格**缩进 + `- ` + 反引号包裹的 `` `<type>(<scope>):` ``（4 空格缩进不匹配） |
| `trap #6 updated to mention worktree-internal commit` | `grep "execute 阶段不逐任务 commit"`（**无 `-A`**） | 「execute 阶段不逐任务 commit」**所在那一行本身**含 `worktree-internal commit`（或 `worktree 内做 1 个聚合 commit`） |
| `trap #6 cross-references Worktree Commit Flow` | `grep -A 2 "execute 阶段不逐任务 commit"` | 该行 + 其后 2 行内出现 `Worktree Commit Flow` |

> ⚠️ **措辞约束（实施期发现）**：AGENTS.md 受 `tests/unit/test_doc_contracts.py::test_docs_do_not_hardcode_directory_composition_counts` 守卫 —— 不得硬编码「N 个 / N 条 / N 用例」这类会随文件增删漂移的构成计数。故目标文本用「做**聚合** commit」而非「做 **1 个** 聚合 commit」（`worktree-internal commit` 仍保留，满足 bats 断言 4）。

> ⚠️ **`trap #6` 是历史命名**：当前仓库**没有**编号陷阱列表（全仓 grep 无「trap #6」列表）。测试只锚「execute 阶段不逐任务 commit」这一行字面文本。**不要**去恢复一个编号陷阱列表。

- [ ] **Step 2: 插入到 AGENTS.md**

插入位置：`### Archive 前全量回归门（MANDATORY）` 段**之后**、`### 全局安装测试` 段**之前**。

目标文本（逐字）：

```markdown
### Worktree Commit Flow

每个 change 在 worktree 内执行时：

1. **Phase 2 execute**：修改文件 + 运行测试 + 更新 plan checkboxes（`-[ ]` → `-[x]`）。
   - execute 阶段不逐任务 commit；Phase 2 全部 task 通过后，在 worktree 内做聚合 commit（worktree-internal commit），详见 Worktree Commit Flow
   - `feat(<scope>): <description>` for new features
   - `fix(<scope>): <description>` for bug fixes
   - `test(<scope>): <description>` for test changes
   - `chore(<scope>): <description>` for tooling changes
   - `docs(<scope>): <description>` for documentation changes

2. **Phase 3 archive**：由 `archive_change_for_mode` 自动 merge → openspec archive → cleanup worktree/branch。
```

- [ ] **Step 3: 跑断言，确认 5 条中的前 5 条转绿**

```bash
bats tests/integration/test_worktree_archive_workflow_docs.bats
```

Expected: 5 passed / 1 failed（只剩 `归档流程 cross-references check_worktree_commits` —— 下一 task 处理）

---

### Task 2: AGENTS.md 新增 `### 归档流程` 段

**Files:**
- Modify: `AGENTS.md`（紧邻 Task 1 插入的 `### Worktree Commit Flow` 段之后）

- [ ] **Step 1: 写下目标文本**

| 断言 | 测试里的实际命令 | 文本必须满足 |
|---|---|---|
| `归档流程 cross-references check_worktree_commits` | `grep -A 8 "^### 归档流程"` | **H3** 标题行 `### 归档流程`，且其**后 8 行内**出现 `check_worktree_commits` |

目标文本（逐字）：

```markdown
### 归档流程

归档前由 `check_worktree_commits` 强制 worktree 分支相对默认分支有新 commit，否则拒绝归档（per ADR-0061）。
```

> ⚠️ **不得**在段内写「per ADR-00XX」这类**未经核对**的 ADR 引用 —— `rddf doctor --category docs-consistency` 会扫 AGENTS.md 的 ADR 编号引用并对磁盘缺失报 WARNING。ADR-0061 已在磁盘上（`docs/adr/ADR-0061-archive-gate-refuses-unmerged-branch.md`），确认后再写。

- [ ] **Step 2: 插入到 AGENTS.md**

- [ ] **Step 3: 跑断言，确认 6/6 通过**

```bash
bats tests/integration/test_worktree_archive_workflow_docs.bats
```

Expected: 6 passed

---

### Task 3: 刷新 `tests/KNOWN_FAILURES.txt`

**Files:**
- Modify: `tests/KNOWN_FAILURES.txt`

- [ ] **Step 1: 先跑回归对比，确认「新增失败 = 0」**

```bash
bash tests/scripts/report_regression.sh
```

Expected: `新增失败: 0`
⚠️ **顺序不可颠倒**：selective refresh 会把实施窗口内的任何新失败一并吸收进基线。先 refresh 后跑回归，被吸收的新失败就从「新增失败」里消失了 —— 基线会把新回归洗白。

- [ ] **Step 2: dry-run 刷新，核对 diff**

```bash
bash tests/scripts/refresh_known_failures.sh --dry-run
```

Expected: diff 只含 **6 条 AGENTS.md 条目的移除 + 一条 summary 注释**；summary 应为 `removed=6, added=0`（`kept=4`）；**无非注释新增行**。

- [ ] **Step 3: 核对通过后实跑 refresh**

```bash
bash tests/scripts/refresh_known_failures.sh
```

- [ ] **Step 4: 核对结果**

```bash
grep -vE '^\s*(#|$)' tests/KNOWN_FAILURES.txt | wc -l   # 期望 4
git diff tests/KNOWN_FAILURES.txt                       # 期望只有 6 条移除 + 1 条 summary 注释
```

---

### Task 4: 收口验证

- [ ] **Step 1: doctor 无新增 finding**

```bash
rddf doctor --category docs-consistency
```

Expected: 无新增 finding。

- [ ] **Step 2: 全量回归门（归档前必跑）**

```bash
BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression
```

Expected: `ALL PASSED`，且 bats regression 段 `新增失败: 0` / `未评估: 0`。

- [ ] **Step 3: 逐条勾回 proposal.md 的 10 条 AC**

- [ ] **Step 4: 归档**

```bash
bash skills/rdd-builder/scripts/phase3_archive.sh fix-agents-md-worktree-commit-flow
```

---

## 回滚

还原 `AGENTS.md` 的两段 + 恢复 `tests/KNOWN_FAILURES.txt` 的 6 条条目。无副作用（纯文档 + 纯基线文本）。

## 不做（明确排除）

- 任何 `.sh` / `.py` / `.bats` 文件
- `_lib/archive.sh::check_worktree_commits` 的 commit type 白名单校验（AGENTS.md 承诺 5 种 type **不**构成实现约束）
- 其余 4 条已知失败条目（各自独立根因，另案处理）
- 补建 `feat-doc-drift-cleanup` fragment —— 它是**从未创建**的虚构跟踪项，本 change 通过移除基线条目**消除**该引用
