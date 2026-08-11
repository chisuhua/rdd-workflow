# add-propose-content-review

**优先级**: P1 | **来源**: Oracle 架构分析 2026-07-21 — arch 阶段 proposal-suggestions.md → proposal-approved.md 迁移的内容审查
**阶段**: v2.1 | **分类**: quality
**类型**: feature

## 架构依据
- Oracle 审查结论: arch 阶段提案迁移 (suggestions → approved) 需要内容审查辅助，但不应强行自动化
- ADR-0003 三阶段架构: 此审查发生在 arch 阶段 Phase 5.5，是 arch → plan 衔接前的最后质量门
- ADR-0005 human-in-loop 节点: Oracle 仅辅助决策，最终 y/n/d/s 由用户决定
- ADR-0007 gate 哲学: warning 级不阻断，block 级强烈建议但不强制
- ADR-0015 决策 1 拒绝 Tribunal — 内容审查只用单次 Oracle 调用

## 范围
- **In Scope**:
  - 新建 `propose_content_review.py`: 单次 Oracle 调用 + 结构化输出 + 终端展示
  - Oracle 检查 4 项: scope 清晰度 / ADR 引用相关性 / 验收标准可测性 / 范围边界合理性
  - **guide-arch Phase 5.5 触发点**: 用户在 suggestions→approved 迁移界面按编号选中提案后、y/n/d/s 菜单之前，自动调用 Oracle 展示报告
  - `SKIP_CONTENT_REVIEW=yes` 跳过 Oracle 审查，直接进入 y/n/d/s
  - Oracle 输出 `pass` / `warn: <具体问题>` / `block: <无法判定的重大歧义>` 三级结果，供人工参考
  - 对应 unit test
- **Out Scope**:
  - 不引入 Tribunal (ADR-0015 约束)
  - 不做自动批准/拒绝 — Oracle 只出报告，人工 y/n/d/s 决策（ADR-0005 human-in-loop）
  - 不做 plan 阶段 change artifact 内容审查 (另见 add-change-content-review)
  - 不持久化审查结果到 .rddf/state/ — 终端展示足够（决策是即时的人工审批）

## 关键场景
- GIVEN arch Phase 5.5 显示 suggestions→approved 迁移界面, WHEN 用户按编号选中一个提案, WHEN SKIP_CONTENT_REVIEW != yes, THEN Oracle 审查 4 项并展示报告，然后用户看到 y/n/d/s 选项
- GIVEN Oracle 报告 `warn: scope 不清晰`, WHEN 用户阅读报告后, THEN 用户自行决定 y(批准)/n(拒绝)/d(延迟)/s(跳过)
- GIVEN Oracle 报告 `block: 验收标准无法从描述中提取`, WHEN 报告标记为 block, THEN 强烈建议用户选 n 或 d，但不强制阻断
- GIVEN SKIP_CONTENT_REVIEW=yes, WHEN Phase 5.5 选中提案, THEN 跳过 Oracle 审查直接进入 y/n/d/s
- GIVEN Oracle 调用超时或失败, WHEN 异常发生, THEN 输出 "Oracle 审查不可用，跳过" 并继续审批交互 (非致命)

## 技术约束
- MUST 使用单次 Oracle 调用 (非 Tribunal)
- MUST NOT 阻断审批流程 (人工最终决策)
- MUST Oracle prompt 包含 improvements/<name>.md 全文 (5 段结构)
- SHOULD Oracle 输出结构化 JSON `{scope_clarity, adr_relevance, acceptance_testability, boundary_reasonableness, overall}` 以便格式化展示
- SHOULD 终端展示使用表格格式，清晰标注 pass/warn/block

## 验收标准
- arch Phase 5.5 在 suggestions→approved 迁移界面选中提案后、y/n/d/s 审批前自动调用 Oracle
- SKIP_CONTENT_REVIEW=yes 跳过
- Oracle 4 项结果以格式化表格展示到终端
- Oracle 超时/失败不阻断审批流程
- 所有现有测试通过