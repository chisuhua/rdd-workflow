## Context

实测 rdd-workflow 5 阶段流程的 opencode 会话(`ses_fb4e3770dffeCYhR7xxAAQdI9l`,1 天 11 小时,492 个 tool calls)发现 7 个工具错误(1.4%)都属同类可避免摩擦,每类错误触发 1-3 个补救 tool call(Read 全文 / Write 整文件 / 重试),估计浪费 15-25 tool calls + 3-5K tokens。

3 类根因:
1. `edit` "Could not find oldString" × 3 — Agent 基于过期文件缓存估算 oldString,与实际内容不一致
2. `write` "File already exists" × 3 — 误用 write 替代 edit 覆盖已存在文件
3. `read` "Offset out of range" × 1 — Python 脚本硬编码行号(1104),实际文件仅 79 行

rdd-workflow 已进入 production use,工具错误率每 1% 都能放大成真实卡顿。本提案在 rdd-workflow 自己 dogfood 中先行修复 7 类根因。

## Goals / Non-Goals

**Goals:**
- 修 7 个实测工具错误的根因,主要通过 (1) skill 内部 Agent 行为约束 + (2) rdd-workflow 提供的修复脚本
- 端到端复测 5 阶段流程 1 个 change: 0 个 tool error
- 把工具选用决策表沉淀到 `skills/_lib/AGENT_TOOL_USAGE.md`

**Non-Goals:**
- 工具调用频率本身(`cd` 重复) → 单独的 P1 提案 `worktree-context-persistence`
- LLM 决策质量(选 write 还是 edit) → 超出工程范畴,属 prompt engineering
- 改 rdd-workflow core 工作流(arch / design / plan / ship / verify)
- 改 opencode / Claude Code 工具 schema(由 vendor 决定)

## Decisions

### 1. AGENT_TOOL_USAGE.md 决策表优先,pre-tool-check script 辅助

新增 `skills/_lib/AGENT_TOOL_USAGE.md`,内含 edit / write / read offset 选用决策树。同步新增 `skills/rdd-workflow-brainstorm/scripts/pre_tool_use_check.sh`,在 3 类高频错误模式触发时输出 stderr 提醒。

**Alternatives considered:**
- 仅修改系统 prompt:无上下文感知,无法在 skill 层区分场景 → 拒绝
- 仅引入 pre-tool-check:文档跟不上,新人无法复现决策 → 拒绝
- 文档 + 脚本 双轨:覆盖 Agent 决策 + 工具调用边界 → 采用

### 2. pre_tool_use_check.sh 集成到 rdd-workflow-brainstorm skill(不是 execute skill)

Agent 在工具调用前的 hint 应绑定到"造提案"的脑暴阶段,不是"执行 plan"的阶段。brainstorm skill 加载 pre-tool-check 钩子 → 在 edit / write / read 调用前 stdout 一行提示。

**Alternatives considered:**
- 集成到 execute skill:放错阶段(执行时 edit 已 fixed in proposal) → 拒绝
- 全局 hook (`~/.config/opencode/hooks/`):跨项目影响,scope 太大 → 拒绝

### 3. 7 个 regression test 写入同一文件 `tests/integration/test_tool_friction_regression.py`

每个 tool error 类别一个 test case,集中管理。命名约定 `test_<tool>_<failure_mode>_<fix_path>`(例: `test_edit_stale_string_falls_back_to_read_write`)。

**Alternatives considered:**
- 分 7 个独立 .py 文件:oversplit 同样场景的测试 → 拒绝
- 写入现有 bats 测试:bats 不擅长 Python tool-call 模拟 → 拒绝

## Risks / Trade-offs

- **Risk: pre-tool-check 反向干扰 Agent 行为**:输出过多 hint 可能让 Agent 犹豫。**Mitigation**:只在确认是 stale-state 模式时输出警告(用 heuristic 检测 file mtime),不无脑刷屏。
- **Risk: 测试在 CI 跑不稳定**:tool-call 模拟依赖 mock 文件系统。**Mitigation**:用 `tmp_path` fixture 隔离 + 100% deterministic seed + 不依赖 wall-clock。
- **Trade-off**:文档更新到 `AGENT_TOOL_USAGE.md` 需要后续会话主动读,如果 Agent 不主动 Read 仍然失效。**Acceptance**:文档路径在 design-time 提示,后续监控看工具错误率是否降到 ≤0.5%。
