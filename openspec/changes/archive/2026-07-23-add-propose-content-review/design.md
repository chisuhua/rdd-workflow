# Design: add-propose-content-review

## Context
Oracle 审查结论驱动，遵循 ADR-0015 不引入 Tribunal。propose 阶段生成建议后，由单次 Oracle 调用验证内容质量，输出结构化审查结果供用户参考。

## Goals / Non-Goals
- **Goals**: 单次 Oracle 调用检查 scope/ADR 对齐/验收标准完整性/边界条件; 输出 `.rddf/state/propose-review.json`; 支持 `SKIP_CONTENT_REVIEW=yes` 环境变量跳过审查
- **Non-Goals**: 不做批准/拒绝/打回决策; 不修改 propose 生成的文件; 不引入多 agent 交叉验证

## Decisions
- 使用单 Oracle（非 Tribunal）——与 ADR-0015 一致
- warning 级别问题不阻断流程——与 ADR-0007 gate 哲学一致，用户可自行判断
- 审查结果仅作为参考信息展示，不改变 propose 阶段的状态机

## Risks / Trade-offs
- 低风险，纯附加机制，不影响现有 propose 流程
- Oracle 调用增加 propose 阶段耗时（约 5-10s），但用户可通过 `SKIP_CONTENT_REVIEW=yes` 跳过
- 审查结果可能包含误报，用户需自行判断是否采纳