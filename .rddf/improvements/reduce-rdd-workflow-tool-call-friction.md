# reduce-rdd-workflow-tool-call-friction

**优先级**: P1 | **来源**: opencode session retrospective (ses_fb4e3770dffeCYhR7xxAAQdI9l) | **阶段**: ship | **分类**: ship
**类型**: refactor
**主题**: 多方对称与回归

## 架构依据

实测 rdd-workflow 5 阶段流程的 opencode 会话(`ses_fb4e3770dffeCYhR7xxAAQdI9l`,1 天 11 小时,492 个 tool calls)发现 7 个工具错误(1.4%)都属同类可避免摩擦:

- `edit` "Could not find oldString" × 3 — Agent 基于过期文件缓存估算 oldString,与实际内容不一致
- `write` "File already exists" × 3 — 误用 write 替代 edit 覆盖已存在文件
- `read` "Offset out of range" × 1 — Python 脚本硬编码行号(1104),实际文件仅 79 行

每个错误触发 1-3 个补救 tool call(Read 全文 / Write 整文件 / 重试)。本会话 7 个错误估计浪费 15-25 个 tool calls(~3-5 min wall-clock)+ ~3-5K tokens LLM 输出。**Why now**:rdd-workflow 进入 production use(本会话即首个 5 阶段完整链路),tool 错误率从 0 越低越好;1.4% 对应 100 次 ship/verify 流程中 1-2 次卡顿。rdd-workflow 自身是 rdd-workflow 用户,先在 dogfood 中修。

## 范围

- **In Scope**: 修 7 个实测错误的根因,主要通过 (1) skill 内部 Agent 行为约束 + (2) rdd-workflow 提供的修复脚本
- **Out Scope**: 工具调用频率本身(`cd` 重复) — 单独的 P1 提案 `worktree-context-persistence`;LLM 决策质量(选 write 还是 edit)— 超出工程范畴,属 prompt engineering

## 关键场景

- GIVEN Agent 在 worktree 内 Edit 文件,oldString 与现状不匹配
  WHEN 调用 edit 工具
  THEN edit 直接 fail,Agent 必须先 Read 全文 + 重试或降级 Write
- GIVEN Agent 想覆盖已存在文件
  WHEN 调用 write 工具
  THEN write fail,Agent 必须改用 edit 或先 Read 再 Write
- GIVEN Agent 写 Python 脚本读文件某行
  WHEN 硬编码行号
  THEN read 工具报 "out of range",Agent 必须重读获取实际行数

## 技术约束

- MUST NOT: 改 rdd-workflow core 工作流(arch/design/plan/ship/verify),只修工具调用层
- MUST NOT: 改 opencode/Claude Code 工具 schema(由 vendor 决定)
- MUST NOT: 引入新依赖

## 验收标准

- 7 个错误类型全部消失(基于会话历史每个的根因)
- 端到端复测 5 阶段流程 1 个 change: 0 个 tool error
- `tests/integration/test_tool_friction_regression.py` 跑通 7 个新场景,验证提示词能引导 Agent 避开这些错误
- 文档化的"工具选用决策表"(edit vs write vs read offset)合并到 `skills/_lib/AGENT_TOOL_USAGE.md`

## Why

工具错误率 1.4% 在 dogfood 阶段已是可避免的浪费,随生产使用会放大 3-5 倍。修这 7 类错误的成本约 1 小时工作量(改 system prompt + 写约束脚本),长期可消除 90%+ 工具层卡顿。

## What Changes

- `skills/_lib/AGENT_TOOL_USAGE.md` 新文件:含 edit/write/read 选用决策表
- `skills/rdd-workflow-brainstorm/scripts/pre_tool_use_check.sh` 新脚本:检测 3 类常见错误模式,提醒 Agent 修正
- `tests/integration/test_tool_friction_regression.py` 新测试:7 个场景验证提示词有效

## Capabilities

- MUST: Agent 收到 edit 失败时,自动 fallback 到 Read 全文 + Write 整文件
- MUST NOT: 改 rdd-workflow core 工作流(已在"技术约束"中重复)


## Impact

- MUST: 文档化每个修复的 rationale,方便后续维护(在 `AGENT_TOOL_USAGE.md` 注明)
- SHOULD: 与 30+ sessions 元数据集成,自动检测未来的同模式错误

## Acceptance

- [ ] 7 个错误类型全部消失(基于会话历史每个的根因)
- [ ] 端到端复测 5 阶段流程 1 个 change: 0 个 tool error
- [ ] `tests/integration/test_tool_friction_regression.py` 跑通 7 个新场景,验证提示词能引导 Agent 避开这些错误
- [ ] 文档化的"工具选用决策表"(edit vs write vs read offset)合并到 `skills/_lib/AGENT_TOOL_USAGE.md`
