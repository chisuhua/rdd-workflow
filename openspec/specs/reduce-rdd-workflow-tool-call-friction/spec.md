# reduce-rdd-workflow-tool-call-friction Specification

## Purpose
TBD - created by archiving change reduce-rdd-workflow-tool-call-friction. Update Purpose after archive.
## Requirements
### Requirement: Agent 工具选用决策表

系统 MUST 提供 `skills/_lib/AGENT_TOOL_USAGE.md`,含 edit / write / read-offset 三个决策树,作为 Agent 工具调用的决策依据。

#### Scenario: Agent 命中 edit 决策树

- **WHEN** Agent 准备调用 `edit` 工具
- **THEN** 必读 `AGENT_TOOL_USAGE.md` 的 `## Edit 决策树` 段
- **AND** 若目标文件上次 Read > 10 分钟前,先 Read 全文再 edit
- **AND** 若 edit 报 "Could not find oldString",回退为 Read 全文 + 重试 edit 或降级 write

#### Scenario: Agent 命中 write 决策树

- **WHEN** Agent 准备调用 `write` 工具
- **THEN** 必读 `AGENT_TOOL_USAGE.md` 的 `## Write 决策树` 段
- **AND** 若目标文件已存在,改走 edit 而非 write

#### Scenario: Agent 命中 read offset 决策树

- **WHEN** Agent 准备调用 `read` 工具并带 offset
- **THEN** 必读 `AGENT_TOOL_USAGE.md` 的 `## Read Offset 决策树` 段
- **AND** 若行号来自脚本硬编码,改用动态 offset (先取实际行数)

### Requirement: pre_tool_use_check.sh 守卫脚本

系统 MUST 提供 `skills/rdd-workflow-brainstorm/scripts/pre_tool_use_check.sh`,warn-only (永远 exit 0),对 3 类 stale 模式输出 stderr 提示。

#### Scenario: 守卫检测 stale edit

- **WHEN** 守卫收到 `edit <file>` 调用且 `RDDF_GUARD_FILE_STATE=stale`
- **THEN** stderr 输出一行含 `STALE-LIKELY` 的提示
- **AND** 进程退出码为 0 (不阻断)

#### Scenario: 守卫检测 write-existing

- **WHEN** 守卫收到 `write <file>` 调用且 `RDDF_GUARD_TARGET_EXISTS=1`
- **THEN** stderr 输出一行含 `EXISTS` 的提示
- **AND** 进程退出码为 0

#### Scenario: 守卫检测 hardcoded read offset

- **WHEN** 守卫收到 `read <file> <offset>` 调用
- **THEN** stderr 输出一行含 `OFFSET` 的提示
- **AND** 进程退出码为 0

### Requirement: 工具摩擦回归测试

系统 MUST 在 `tests/unit/test_agent_tool_usage_doc.py`、`tests/unit/test_pre_tool_use_check.py`、`tests/integration/test_tool_friction_regression.py` 中覆盖以下场景并全部 PASS:

#### Scenario: AGENT_TOOL_USAGE.md 存在并含 3 决策树

- **WHEN** pytest 跑 `test_agent_tool_usage_doc.py`
- **THEN** doc 存在断言通过
- **AND** 3 个决策树段 (`## Edit 决策树` / `## Write 决策树` / `## Read Offset 决策树`) 全部存在
- **AND** brainstorm SKILL.md 引用 `pre_tool_use_check.sh` 和 `AGENT_TOOL_USAGE.md`

#### Scenario: 守卫脚本 3 类 stale 模式全部可触发

- **WHEN** pytest 跑 `test_pre_tool_use_check.py`
- **THEN** 3 个测试 (stale-edit / write-existing / read-offset) 全部 PASS

#### Scenario: 7 个集成回归测试覆盖 mitigation + anti-spam

- **WHEN** pytest 跑 `tests/integration/test_tool_friction_regression.py`
- **THEN** 4 个 mitigation 验证测试 PASS
- **AND** 3 个 anti-spam 测试 PASS (fresh/0/no-offset 不报警)
- **AND** 连续两次相同 stale 调用不重复报警

