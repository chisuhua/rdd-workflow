# changelog-usage-sync

## Why

CHANGELOG.md 是权威的"变更日志"——记录每个 release / 阶段的变更条目。USAGE.md 是用户视角的"完整使用指南"——它需要在每个版本变更后同步更新。

2026-08-26 审计发现 USAGE.md 顶部明确写：

> **当前版本: v2.0 / v2.0.1**（三阶段架构 arch → plan → ship + ...）

但实际 v3.0.0 已发布，五阶段架构已上线。CHANGELOG.md 的 [Unreleased] 段（line 5-16）已记录 rdd-verifier 5th phase，但 USAGE.md 没跟进。

这是"文档同步"问题的典型例子——CHANGELOG 改得快，USAGE 改得慢（或忘了改）。

## What Changes

**In Scope**:

- 在 `_lib/doctor.py`（或新建 `_lib/changelog_usage_sync.py`）新增检查：CHANGELOG [Unreleased] 段的"Added/Changed/Fixed"段落 → USAGE.md 是否提及相应内容
- pre-commit hook：当 CHANGELOG.md 改动时，强制要求 USAGE.md 顶部"当前版本"段更新
- `tests/integration/test_changelog_usage_sync.bats`：基础一致性测试
- USAGE.md 顶部 banner 改为 auto-generated（来自 package.json version + CHANGELOG latest tag）

**Out of Scope**:

- 自动修改 USAGE.md（保持 human-in-loop）
- CHANGELOG 格式变更（保持现有 `[Unreleased]` + `## [vX.Y.Z]` 格式）

## Capabilities

- (no items specified)

## Impact

- (no items specified)

## Acceptance

- [ ] USAGE.md 含 `<!-- VERSION_BANNER_START --> ... <!-- VERSION_BANNER_END -->` 占位符
- [ ] `_lib/sync_usage_banner.py` 实现
- [ ] pre-commit hook 安装指引（不强制，可选）
- [ ] `tests/integration/test_changelog_usage_sync.bats` PASS
- [ ] CHANGELOG.md [Unreleased] 改动时，CI 跑 `python3 _lib/sync_usage_banner.py --check` 验证 USAGE.md 是否需更新

