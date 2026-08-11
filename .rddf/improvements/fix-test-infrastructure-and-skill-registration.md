# fix-test-infrastructure-and-skill-registration

**优先级**: P2 | **来源**: 会话复盘 2026-07-31 — bats 基础设施损坏 + 9 个 Python 测试持续失败
**阶段**: default | **分类**: core-test
**类型**: fix

## 架构依据

- 会话复盘 2026-07-31: `npm test` 报错 `bats_load_safe: Could not find 'tests/integration/test_helper'[.bash]`，bats 测试套件完全不可运行
- 9 个 Python 测试持续失败：4 个 concurrency 测试（`test_rddf_session_concurrency`）、4 个 cross-session recovery 测试（`test_rddf_session_cross_session_recovery`）、1 个 skill 计数测试（`test_doc_contracts`）
- `guide-design` skill 存在于磁盘但未注册到 skill 系统，导致 `test_install_description_skill_count_matches_disk` 断言失败

## 范围

- **In Scope**:
  - `tests/integration/test_helper.bash` 的路径解析修复（当前 `bats_load_safe` 找不到它）
  - 或 `tests/integration` 下所有 `.bats` 文件的 `load test_helper` 路径修正
  - `tests/unit/test_doc_contracts.py` 的 skill 计数断言更新为包含 `guide-design`
  - 4 个 concurrency 测试的环境依赖检查（如需要 `pytest-xdist` 或特定文件锁实现）
  - 4 个 cross-session recovery 测试的 timeout 配置检查
- **Out Scope**:
  - 不修改 concurrency 测试的核心逻辑（可能依赖特定 OS 的原语）
  - 不修改 `rddf_session` 模块本身（如果测试失败是测试环境问题而非代码问题）
  - 不修改 `guide-design/SKILL.md` 内容

## 关键场景

- GIVEN `npm test` 执行, WHEN bats 加载测试文件, THEN `bats_load_safe` 找不到 `test_helper` — 路径解析失败
- GIVEN `pytest tests/unit/` 执行, WHEN `test_doc_contracts.py` 枚举 skill 数量, THEN 断言 73 个但磁盘有 74 个（含 `guide-design`）
- GIVEN concurrency 测试执行, WHEN 100 个 worker 并发创建 session, THEN 可能因文件锁竞争超时——取决于宿主环境

## 技术约束

- MUST 修复 `npm test` 使其能运行 bats 测试（至少 smoke 和主要 integration 测试）
- MUST 更新 `test_doc_contracts.py` 的 skill 计数（可动态扫描磁盘而非硬编码）
- MUST NOT 删除或修改 concurrency 测试的断言逻辑（它们是 valid 的契约测试）
- SHOULD 使 concurrency 测试在单 worker 环境可跳过而非 FAIL
- SHOULD 使 bats test_helper 路径解析使用 `BATS_TEST_DIRNAME` 派生而非硬编码相对路径

## 验收标准

- `npm test` 退出码 0（至少 smoke.bats 通过）
- `python3 -m pytest tests/unit/test_doc_contracts.py -q --tb=short` 通过
- `python3 -m pytest tests/unit/ -q --tb=short` 通过（concurrency 测试可跳过但不可 FAIL）
- `skill_use("guide-design")` 在 skill 工具中可用（由 test 覆盖或手动验证）