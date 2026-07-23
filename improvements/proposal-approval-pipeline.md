# proposal-approval-pipeline

**优先级**: P0 &nbsp;|&nbsp; **来源**: 架构改进 — 提案审批管线缺失
**阶段**: v2.1 &nbsp;|&nbsp; **分类**: core
**类型**: feature

## 架构依据

- 当前 `proposal-suggestions.md` 是一个 474 行的单体 JSON 文件，承载双重职责：既是"待讨论的提案池"，又是"plan 阶段直接可用的创建输入"
- `guide-arch` 完全不参与提案的审查/审批流程（0 次引用 `proposal-suggestions.md`）
- 提案从扫描到创建缺少架构评审网关：用户勾选即创建，无质量把关
- ADR-0003 三阶段架构中，arch 阶段应拥有"提案审批"职责但实际未实现

## 范围

- **In Scope**:
  - 新建 `improvements/` 目录，每个提案为独立 `.md` 文件（5-section 格式）
  - `proposal-suggestions.md` 降级为 Markdown 表格索引，仅存链接+元数据
  - 新建 `proposal-approved.md` 作为 plan 阶段的批准提案索引
  - `guide-arch` 新增 Phase 5.5：逐文件审查 improvements/，批准/拒绝/延迟
  - `guide-plan` propose 从 `proposal-approved.md` 读链接（替代原 JSON 解析）
  - `propose` skill `propose_change.py` 中 `set_suggestion_status` 改为读取 improvements/ 目录其文件 frontmatter
  - `archive.sh` 归档后更新 `proposal-approved.md` 条目状态
  - `skills/_lib/state.sh` 新增 `list_improvements()` / `list_approved()` 替代 `read_suggestions`
  - `guide/scripts/scan-state.sh` 双索引扫描，优先推荐合适的阶段
  - 迁移脚本将现有 27 个 JSON 提案转为独立文件
- **Out Scope**:
  - 不修改 `propose_content_review.py`（已存在但未集成）
  - 不修改 `proposal-suggestions-format.md` 文档（保留作为历史参考，标注 deprecated）
  - 不引入 Tribunal 多 agent 交叉审查（ADR-0015 约束）

## 关键场景

- GIVEN guide-arch Phase 5 完成架构定义, WHEN 进入 Phase 5.5, THEN 展示 `improvements/` 下待讨论提案并支持逐文件批准/拒绝
- GIVEN 提案被批准, WHEN 写入 `proposal-approved.md`, THEN 仅添加一行链接无需复制内容
- GIVEN guide-plan propos, WHEN 读取 `proposal-approved.md`, THEN 按链接打开对应 `improvements/xxx.md` 完成 change 创建

## 技术约束

- MUST 每个 improvements/ 文件自包含完整 5-section 内容（架构依据、范围、关键场景、技术约束、验收标准）
- MUST `proposal-suggestions.md` 和 `proposal-approved.md` 仅做索引不嵌入内容
- MUST 提案文件不包含 status 字段（状态由所在索引文件决定）
- SHOULD 索引文件追加新条目时保持表格按优先级排序
- MUST NOT 在 `proposal-approved.md` 中复制提案内容（仅链接）

## 验收标准

- `improvements/` 目录存在，所有提案为独立 `.md` 文件
- `proposal-suggestions.md` 为 Markdown 表格索引，< 60 行
- `proposal-approved.md` 为 Markdown 表格索引，< 30 行
- `guide-arch` Phase 5.5 支持逐文件审批
- `guide-plan` propose 从 `proposal-approved.md` 读取
- 所有现有 consumers（guide/scan-state.sh, dashboard, workflow_synthesizer, status）适配双索引
- 迁移脚本完成 27 个现有提案的转换
- 所有现有测试适配并通过
