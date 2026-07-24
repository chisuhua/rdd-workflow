---
name: add-improve
description: "交互式创建 rdd-workflow 改进提案。调用 rdd-workflow-brainstorm 进行头脑风暴，生成 improvements/<name>.md 并注册到 proposal-suggestions.md。"
license: MIT
compatibility: Requires rdd-workflow 项目结构（improvements/ 目录、proposal-suggestions.md）
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
  └─→ 创建 improvements/<name>.md
  └─→ 注册到 proposal-suggestions.md
  └─→ 引导下一步
```

## 前置条件

确认项目根目录存在以下文件/目录，如缺失则提示创建：
- `improvements/` 目录
- `proposal-suggestions.md`（或自动创建索引模版）

## 使用方式

```bash
# 直接调用，交互式创建提案
skill_use("add-improve")

# 或直接指定名称（跳过命名环节）：
# skill_use("add-improve fix-login-timeout")
```

## 执行流程

### Phase 1：加载 rdd-workflow-brainstorm

加载 `rdd-workflow-brainstorm` 技能，按照其 checklist 执行：

1. 探索项目上下文
2. 提出澄清问题（一次一个）
3. 提出 2-3 种方案
4. 呈现 5 段设计（逐段确认）
5. 用户批准设计

**在 Phase 1 完成前，不得进入 Phase 2。**

<HARD-GATE>
在 rdd-workflow-brainstorm 完成且用户批准设计之前，不得创建 proposal-suggestions.md 或 improvements/<name>.md。
</HARD-GATE>

### Phase 2：创建提案文件

rdd-workflow-brainstorm 的设计获得批准后：

1. 确定提案名称（kebab-case）— 如果用户未提前指定，从上一步的设计内容中提取
2. 用批准的 5 段内容创建 `improvements/<name>.md`
3. 在 `proposal-suggestions.md` 表格末尾追加行
4. 展示最终成果

### Phase 3：引导下一步

建议用户后续操作：

1. **审查提案** — 检查 `improvements/<name>.md` 内容是否完整准确
2. **批准流程** — 运行 `guide-arch` 进入 Phase 5.5 审查该提案
3. **跳转到 guide** — `skill_use("guide")` 查看当前项目状态

## 输出示例

### `improvements/fix-login-timeout.md`

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
| [fix-login-timeout](improvements/fix-login-timeout.md) | P1 | 用户反馈 | 2026-07-25 |
```

## 错误处理

| 情况 | 处理方式 |
|------|----------|
| `improvements/` 目录不存在 | 自动创建 |
| `proposal-suggestions.md` 不存在 | 创建带标准表头的索引文件 |
| 提案名称已存在 | 提示用户并用不同的名称、或者确认覆盖 |
| 用户中途放弃 | 不创建任何文件，保持项目状态不变 |