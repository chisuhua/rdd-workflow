# 提案池（待架构讨论）

> design 阶段输入。guide-design 逐个审查，批准后添加到 `proposal-approved.md`。
>
> **生命周期**: 提案从此文件创建 → design 审查 → 批准/拒绝/延迟 → 移至 `proposal-approved.md` 等待实施 → 实施后归档。
> **自动清理**: 提案被批准或实施后，`sync_suggestions()` 会自动从本表移除该行（不再停留）。
> **手动审计**: 发现过期条目时，运行 `skill_use("guide")` 的审计功能自动清理。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [fix-schema-version-field](.rddf/improvements/fix-schema-version-field.md) | P1 | 审计 add-cross-repo-state-schemas 验收时发现 17 schema 缺 version 字段，doctor 报 5 个 CRITICAL 根因 | 2026-08-17 | pending |
| [complete-add-contract-lint-ci-gate](.rddf/improvements/complete-add-contract-lint-ci-gate.md) | P1 | 审计 add-contract-lint-ci-gate 验收时发现 3 个 AC 未实现（README CI 示例 / rddf CLI / STRICT_CONTRACT_GATE） | 2026-08-17 | pending |
| [complete-add-cross-repo-deps-orchestration](.rddf/improvements/complete-add-cross-repo-deps-orchestration.md) | P1 | 审计 add-cross-repo-deps-orchestration 验收时发现 2 个 AC 未实现（STRICT_DEPS_GATE / README 跨仓库依赖示例） | 2026-08-17 | pending |
| [enforce-tasks-completion-before-archive](.rddf/improvements/enforce-tasks-completion-before-archive.md) | P2 | 审计 9 个归档 change 时发现 tasks.md 完成度参差不齐（0/55、34/41、8/10），无 gate 兜底 | 2026-08-17 | pending |
