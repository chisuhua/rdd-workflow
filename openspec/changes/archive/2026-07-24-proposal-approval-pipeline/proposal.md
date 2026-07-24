## Why

当前 `proposal-suggestions.md` 是一个 474 行单体 JSON 文件，承载双重职责——既是"待架构讨论的提案池"，又是"plan 阶段直接可用的创建输入"。`guide-arch` 完全不参与提案审查（0 次引用），提案从扫描到创建缺少架构评审网关。需要将单体 JSON 拆分为：独立提案文件 + 双索引（suggestions/approved），使 arch 和 plan 阶段各司其职。

## What Changes

- **BREAKING**: `proposal-suggestions.md` 从 JSON 数组格式改为 Markdown 表格索引，仅存链接+元数据
- 新建 `improvements/` 目录，每个提案为独立 `.md` 文件（5-section 格式）
- 新建 `proposal-approved.md` 作为 plan 阶段的批准提案索引（Markdown 表格）
- `guide-arch` 新增 Phase 5.5：逐文件审查 improvements/，批准写入 approved.md
- `guide-plan` propose 改为从 `proposal-approved.md` 读链接，替代原 JSON 解析
- `propose` skill 中 `read_suggestions`/`write_suggestions` 改为基于文件扫描的 `list_improvements`/`list_approved`
- `archive.sh` 归档后更新 `proposal-approved.md` 条目状态
- `guide/scripts/scan-state.sh` 双索引扫描，推荐合适的阶段
- `skills/_lib/state.sh` 新增 `list_improvements()` / `list_approved()` 函数
- 迁移脚本将现有 27 个 JSON 提案转为独立文件

## Capabilities

### New Capabilities
- `improvement-index`: 提案索引机制——Markdown 表格索引替代 JSON 内嵌，每个提案为独立 `.md` 文件
- `proposal-approval-gate`: 提案审批网关——guide-arch Phase 5.5 逐文件审查，批准写入 proposal-approved.md

### Modified Capabilities
- `proposal-scan`: 从 JSON 内嵌改为文件扫描，状态由所在索引文件决定（不变更文件内容）
- `archive-status-sync`: 归档状态同步目标从 proposal-suggestions.md 改为 proposal-approved.md

## Impact

- 所有 17 个引用 `proposal-suggestions.md` 的消费者需适配双索引格式
- `skills/_lib/state.sh` 的 `read_suggestions`/`write_suggestions` 将标记 deprecated
- `docs/proposal-suggestions-format.md` 标记 deprecated，新增 `docs/proposal-approved-format.md`
- 现有 27 个提案需通过迁移脚本转换为 improvements/ 目录下的独立文件