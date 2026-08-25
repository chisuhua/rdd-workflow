# 提案池（待架构讨论）

> design 阶段输入。guide-design 逐个审查，批准后添加到 `proposal-approved.md`。
>
> **生命周期**: 提案从此文件创建 → design 审查 → 批准/拒绝/延迟 → 移至 `proposal-approved.md` 等待实施 → 实施后归档。
> **自动清理**: 提案被批准或实施后，`sync_suggestions()` 会自动从本表移除该行（不再停留）。
> **手动审计**: 发现过期条目时，运行 `skill_use("guide")` 的审计功能自动清理。
> **依赖记录**: `fix-orphan-hub-gates-wiring`（P1）阻塞于 `fix-adr-0031-safety-gate-substantiation`（P0）— audit log 须先非空，`check_cross_repo_approvals` 才能验证。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [add-feature-fragment-command](.rddf/improvements/add-feature-fragment-command.md) | P1 | user request (add-feature 选项) + 2 轮 Oracle 评审 (bg_03696e35, bg_b16179e9) + add-hierarchical-roadmap-structure 场景 3 补全 | 2026-08-25 | 待审查 |
