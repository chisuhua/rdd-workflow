# 提案池（待架构讨论）

> design 阶段输入。guide-design 逐个审查，批准后添加到 `proposal-approved.md`。
>
> **生命周期**: 提案从此文件创建 → design 审查 → 批准/拒绝/延迟 → 移至 `proposal-approved.md` 等待实施 → 实施后归档。
> **自动清理**: 提案被批准或实施后，`sync_suggestions()` 会自动从本表移除该行（不再停留）。
> **手动审计**: 发现过期条目时，运行 `skill_use("guide")` 的审计功能自动清理。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [fix-generator-scope-extraction](.rddf/improvements/fix-generator-scope-extraction.md) | P1 | Oracle 审查 + dogfooding 实战发现 | 2026-08-13 | 延迟 |
| [issue-driven-proposal-creation](.rddf/improvements/issue-driven-proposal-creation.md) | P1 | Oracle 评估 + 当前缺口分析 | 2026-08-13 | 待审查 |
