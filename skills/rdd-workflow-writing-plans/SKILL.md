---
name: rdd-workflow-writing-plans
description: 自包含的 OpenSpec 实施计划生成器。为 OpenSpec change 生成 TDD 5 步结构的实施计划(.rddf/plans/<name>.md)。基于 superpowers/writing-plans 改写,完全自包含于 rdd-workflow,不依赖任何外部 skill。被 guide-ship 在 Phase 1 plan 阶段调用。
license: MIT
compatibility: Requires git 2.25+, openspec CLI 1.3.1+. 无外部 skill 依赖。
metadata:
  version: "3.0"  # v3.0 rename (BREAKING) — see ADR-0023
  author: sisyphus
  evolved-from: "superpowers/writing-plans v152 行核心 TDD 纪律 + OpenSpec change 上下文适配; v2.0 自包含"
  user-invocable: false
---

# Writing Plans (rdd-workflow-writing-plans)

为 OpenSpec change 生成实施计划,采用 TDD 5 步结构。

## 概述

写出完整的实施计划,**假设工程师对代码库零背景、品味存疑**。记录他们需要知道的一切:每个任务要触碰哪些文件、代码、测试、可能需要查阅的文档、如何测试。给出 bite-sized 任务。**DRY. YAGNI. TDD. Frequent commits.**

假设他们是有能力的开发者,但对我们工具集和问题域知之甚少。假设他们不太懂好的测试设计。

**调用方式**:
```
skill_use("rdd-workflow-writing-plans")   # 无参数,依赖 git context 获取 CHANGE_NAME / WT_PATH
```

## 输入上下文(由 guide-ship 自动注入)

调用方应在 cd 到 worktree 后调用本技能,以下变量可由 git 自动推导:
- `CHANGE_NAME`: 当前 OpenSpec change 名称
- `WT_PATH`: 当前 worktree 路径(也即 $(pwd))

需读取的 OpenSpec change 文件:
- `openspec/changes/<CHANGE_NAME>/proposal.md`
- `openspec/changes/<CHANGE_NAME>/design.md`
- `openspec/changes/<CHANGE_NAME>/tasks.md`

**输出路径(强制)**:
```
.rddf/plans/<CHANGE_NAME>.md
```

## Plan 文档头部(必备)

每个 plan 必须以以下头部开始:

```markdown
# <Change Name> Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [一句话描述这个变更构建什么]

**Architecture:** [2-3 句话描述方法]

**Tech Stack:** [关键技术/库]

---

## File Structure

[列出将创建或修改的文件及各自职责]

### Production Code

| File | Responsibility |
|---|---|
| `path/to/file.py` | 单职责说明 |

### Tests

| File | Responsibility |
|---|---|
| `tests/path/test_x.py` | 测试覆盖说明 |

---
```

## 任务结构(TDD 5 步 — 每步 2-5 分钟)

````markdown
### Task N: [组件名]

**Files:**
- Create: `path/to/new_file.py`
- Modify: `path/to/existing.py:123-145`
- Test: `tests/path/test_x.py`

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test_x.py::test_specific_behavior -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test_x.py::test_specific_behavior -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test_x.py path/to/new_file.py
git commit -m "feat: add specific feature"
```
````

## 禁止的占位符

每一步必须包含工程师需要的实际内容。以下是 **plan 失败** 标志:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above"(不给出实际测试代码)
- "Similar to Task N"(必须重复代码 — 工程师可能跳读)
- 描述做什么但不展示如何做的步骤
- 引用任何 task 中未定义类型/函数/方法

## 范围检查

如果 spec 涵盖多个独立子系统,应先拆分为子项目 spec。如果未拆,**建议先拆分再生成 plan** — 每个 plan 应独立产出可工作的、可测试的软件。

## 文件结构原则

定义任务前,先映射文件结构。这是分解决策落定之处。

- 单元设计有清晰边界和明确接口。每个文件应有单一职责。
- 你在 context 中能完整持有的代码推理最可靠,小而专注的文件编辑更可靠。**优先小文件,反之大文件做太多事**。
- 一起变化的文件应住在一起。按职责拆,而非按技术层。
- 在现有代码库,遵循既定模式。如果代码库用大文件,不要单方面重构 — 但如果你正在修改的文件变得笨重,在 plan 中包含拆分是合理的。

## 任务粒度

**每步一个动作(2-5 分钟)**:
- "Write the failing test" - 一步
- "Run it to make sure it fails" - 一步
- "Implement the minimal code to make the test pass" - 一步
- "Run the tests and make sure they pass" - 一步
- "Commit" - 一步

## 自检(Self-Review)

写完完整 plan 后,以全新视角对照 spec 检查。这是自查清单 — 不是调度子代理。

**1. Spec 覆盖**:浏览 spec 每个 section/需求。能指出实现它的 task 吗?列出任何空缺。

**2. 占位符扫描**:搜索 plan 中的危险信号 — 任何 "No Placeholders" 部分列出的模式。修复它们。

**3. 类型一致性**:后续 task 中使用的类型、方法签名、属性名是否与早期 task 中定义的一致?Task 3 调 `clearLayers()`,Task 7 调 `clearFullLayers()` 是 bug。

如果发现问题,直接修复。无须再 review — 修复并继续。如果发现 spec 需求没有对应 task,添加 task。

## 执行交接(可选)

写完 plan 后,如果直接由当前 AI 助手执行,可以继续。否则交接给 skill_use("execute")。

**执行选项**:

1. **当前 session 执行**(推荐用于小 plan):
   - 直接按 plan 步骤执行 task-by-task
   - 每个 task 完成后用 sed 更新 openspec/changes/<name>/tasks.md 的 `- [x]`

2. **skill_use("execute") 技能**(推荐用于复杂 plan):
   - 加载本 plan 文件
   - 按 Task 顺序执行
   - 每个 Task 完成后 commit
   - 全部完成后通过 status.md 检查进度

## 与 execute.md 的契约

生成的 `.rddf/plans/<name>.md` 必须满足:

- **路径**: `.rddf/plans/<CHANGE_NAME>.md`(强制)
- **Task 数量**: 至少 1 个 `### Task N:`
- **Step 数量**: 至少 1 个 `- [ ]` checkbox
- **Header**: Goal / Architecture / Tech Stack 必备
- **Files 行**: 每个 Task 必须有 `**Files:**` 列出 Create/Modify/Test 路径

下游 `execute.md` 通过 `grep -c '^### Task'` 和 `grep -c '^- \[ \]'` 验证,**不需要**深入解析每个 Step 内容。

## 变更历史

| 版本 | 改动 | 来源 |
|---|---|---|
| v1.0 | 自包含版本,fork 自 superpowers/writing-plans 核心 TDD 5 步纪律,适配 OpenSpec change 上下文 | superpowers/writing-plans (152 行) |