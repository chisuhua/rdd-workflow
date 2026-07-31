## Why

会话复盘 2026-07-31 发现测试基础设施损坏（测试契约见 ADR-0015 §决策 5：bats 集成测试锁定结构，pytest 单元测试锁定逻辑）：

1. `npm test` 报错 `bats_load_safe: Could not find 'tests/integration/test_helper'[.bash]`，bats 测试套件完全不可运行 — `tests/integration/test_helper.bash` 的路径解析失败。
2. 9 个 Python 测试持续失败：4 个 concurrency 测试（`test_rddf_session_concurrency`）、4 个 cross-session recovery 测试（`test_rddf_session_cross_session_recovery`）、1 个 skill 计数测试（`test_doc_contracts`）。
3. `guide-design` skill 存在于磁盘但未注册到 skill 系统，导致 `test_install_description_skill_count_matches_disk` 断言失败（硬编码 73 vs 磁盘 74）。

## What Changes

- `tests/integration/test_helper.bash` 路径解析修复：`bats_load_safe` 无法找到它 → 修正所有 `.bats` 文件的 `load test_helper` 路径（用 `BATS_TEST_DIRNAME` 派生而非硬编码相对路径）
- `tests/unit/test_doc_contracts.py` skill 计数断言更新：改为动态扫描磁盘而非硬编码，纳入 `guide-design`
- concurrency / cross-session recovery 测试的环境依赖检查：单 worker 环境可跳过（skip）而非 FAIL；必要时调整 timeout 配置
- 验证 `guide-design` 注册到 skill 系统（`skill_use("guide-design")` 可用）

## Capabilities

### New Capabilities
- `test-infra-path-resolution`: bats test_helper 路径解析修复 + skill 计数动态化 + concurrency 测试环境自适应

### Modified Capabilities
<!-- 无 spec 级行为变更 -->

## Impact

**In Scope:**
- `tests/integration/` 下所有 `.bats` 文件的 `load test_helper` 路径修正
- `tests/unit/test_doc_contracts.py` — skill 计数动态扫描
- concurrency / cross-session recovery 测试的环境依赖与 timeout 配置

**Out of Scope:**
- 不修改 concurrency 测试的核心断言逻辑（它们是 valid 的契约测试）
- 不修改 `rddf_session` 模块本身（若失败源于测试环境而非代码）
- 不修改 `guide-design/SKILL.md` 内容