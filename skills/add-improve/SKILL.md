---
name: add-improve
description: "交互式创建 rdd-workflow 改进提案。调用 rdd-workflow-brainstorm 进行头脑风暴，生成 .rddf/improvements/<name>.md 并注册到 proposal-suggestions.md。"
license: MIT
compatibility: Requires rdd-workflow 项目结构（.rddf/improvements/ 目录、proposal-suggestions.md）
metadata:
  version: "1.0"
  author: sisyphus
  evolved-from: "rdd-workflow-brainstorm — 入口包装器"
  user-invocable: true
---

# Add Improve — 添加改进提案

创建格式规范的改进提案。流程：

```
add-improve
  └─→ rdd-workflow-brainstorm  — 探索需求、设计方案、输出 5 段内容
  └─→ 创建 .rddf/improvements/<name>.md
  └─→ 注册到 proposal-suggestions.md
  └─→ 引导下一步
```

## 前置条件

确认项目根目录存在以下文件/目录，如缺失则提示创建：
- <a href=".rddf/improvements/` 目录
- `proposal-suggestions.md`（或自动创建索引模版）

## 使用方式

```bash
# 直接调用，交互式创建提案
skill_use("add-improve")

# 或直接指定名称（跳过命名环节）：
# skill_use("add-improve fix-login-timeout")
```

## 执行流程

### Phase 0 — 无参数模式

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

### Phase 1：加载 rdd-workflow-brainstorm

加载 `rdd-workflow-brainstorm` 技能，按照其 checklist 执行：

1. 探索项目上下文
2. 提出澄清问题（一次一个）
3. 提出 2-3 种方案
4. 呈现 5 段设计（逐段确认）
5. 用户批准设计

**在 Phase 1 完成前，不得进入 Phase 2。**

<HARD-GATE>
在 rdd-workflow-brainstorm 完成且用户批准设计之前，不得创建 proposal-suggestions.md 或 .rddf/improvements/<name>.md。
</HARD-GATE>

### Phase 2：创建提案文件

rdd-workflow-brainstorm 的设计获得批准后：

1. 确定提案名称（kebab-case）— 如果用户未提前指定，从上一步的设计内容中提取
2. 用批准的 5 段内容创建 <a href=".rddf/improvements/<name>.md`
3. 在 `proposal-suggestions.md` 表格末尾追加行
4. 展示最终成果

### Phase 3：引导下一步

建议用户后续操作：

1. **审查提案** — 检查 <a href=".rddf/improvements/<name>.md` 内容是否完整准确
2. **批准流程** — 运行 `guide-design` 审查该提案
3. **跳转到 guide** — `skill_use("guide")` 查看当前项目状态

## 输出示例

### <a href=".rddf/improvements/fix-login-timeout.md`

```markdown
# fix-login-timeout

**优先级**: P1 | **来源**: 用户反馈
**阶段**: default | **分类**: core-impl
**类型**: feature

## 架构依据
...

## 范围
...
```

### `proposal-suggestions.md` 新增行

```
| [fix-login-timeout](.rddf/improvements/fix-login-timeout.md) | P1 | 用户反馈 | 2026-07-25 |
```

## 错误处理

| 情况 | 处理方式 |
|------|----------|
| <a href=".rddf/improvements/` 目录不存在 | 自动创建 |
| `proposal-suggestions.md` 不存在 | 创建带标准表头的索引文件 |
| 提案名称已存在 | 提示用户并用不同的名称、或者确认覆盖 |
| 用户中途放弃 | 不创建任何文件，保持项目状态不变 |

## Env-var 隔离约定

`add-improve` 支持 3 种提案创建模式（free / from-roadmap / from-issue），各模式使用**互不重叠**的 env-var 前缀：

| 模式 | Env-var 前缀 |
|------|-------------|
| free（交互式brainstorm） | `ADD_IMPROVE_` + `BRAINSTORM_` |
| from-roadmap | `ADD_IMPROVE_FROM_ROADMAP_*` + `ADD_IMPROVE_THEME` + `BRAINSTORM_RATIONALE_DRAFT` |
| from-issue | `ADD_IMPROVE_FROM_ISSUE` + `ADD_IMPROVE_GH_REPO` + `ADD_IMPROVE_ISSUE_TITLE` + `ADD_IMPROVE_ISSUE_BODY` |

**隔离保证**：
- 每个脚本的 bash wrapper 在 `EXIT` 时 `trap cleanup` 自动 `unset` 仅属于自己的 env-vars。
- 运行 `from-roadmap` 后再运行 `from-issue`（反之亦然），不会产生 env-var 污染。
- 跨模式交叉调用时，被调脚本只读取自己的前缀，不会误读其他模式的变量。

**验证**：见 `tests/integration/test_from_issue_env_isolation.bats`（3 个隔离测试，全部 pass）。