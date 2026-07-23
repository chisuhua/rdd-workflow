# add-propose-content-review

**优先级**: P1 | **来源**: Oracle 架构分析 2026-07-21 — Proposal 内容审查机制
**阶段**: v2.1 | **分类**: quality
**类型**: feature

## 架构依据
- Oracle 审查结论: Proposal 需要内容审查 (主观判断)，但不应强行自动化
- ADR-0015 决策 1 拒绝 Tribunal 做 plan critique — 内容审查同样不应引入多 agent 交叉验证
- 推荐: 单次 Oracle 调用做 4 项内容审查 (scope 清晰度、ADR 引用相关性、验收标准可测性、范围边界合理性)
- proposal-suggestions.md 的 5 段式 description 结构适合被审查
- 与 ADR-0007 gate 哲学一致: warning 级 + 可跳过 (SKIP_CONTENT_REVIEW=yes)

## 范围
- **In Scope**:
  - 新建 propose_content_review.py: 单 Oracle 调用 + 结构化输出 + 写 .rddf/state/propose-review.json
  - Oracle 检查 4 项: scope 清晰度 / ADR 引用相关性 / 验收标准可测性 / 范围边界合理性
  - propose.md Phase 4 末尾可选调用 (SKIP_CONTENT_REVIEW=yes 跳过)
  - 输出 warning 级不阻断流程
  - 对应 unit test
- **Out Scope**:
  - 不引入 Tribunal (ADR-0015 约束)
  - 不做批准/拒绝/打回 (human-in-loop 节点留待后续 ADR)
  - 不做 plan 阶段内容审查 (仅 proposal 阶段)

## 关键场景
- GIVEN propose 创建完 change, WHEN SKIP_CONTENT_REVIEW != yes, THEN Oracle 检查 4 项并输出结果到终端 + .rddf/state/propose-review.json
- GIVEN Oracle 发现 scope 不清晰, WHEN 输出 warning, THEN 不阻断流程 (用户自行决定是否修改)
- GIVEN SKIP_CONTENT_REVIEW=yes, WHEN propose 完成, THEN 跳过 content review

## 技术约束
- MUST 使用单次 Oracle 调用 (非 Tribunal)
- MUST 输出 warning 级不阻断
- MUST NOT 引入新的 event type (写到 propose-review.json 足矣)
- SHOULD Oracle prompt 包含 proposal 的 5 段 description 全文

## 验收标准
- propose_content_review.py 含 4 项检查 + Oracle prompt
- SKIP_CONTENT_REVIEW=yes 跳过内容审查
- 输出写入 .rddf/state/propose-review.json
- 所有现有测试通过
