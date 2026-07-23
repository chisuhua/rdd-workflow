# remove-ci-redundant-bats

**优先级**: P1 | **来源**: Oracle 代码审查 2026-07-19 #1 降级版
**阶段**: default | **分类**: general
**类型**: test-only

## 架构依据
- Oracle 验证：CI 的 `bats tests/ --recursive` 已运行全部 704 个 test cases。后续两个显式 `bats tests/integration/test_*.bats` 步骤是冗余的双重运行（静态分类 + worktree 分类），浪费 CI 时间。

## 范围
- **In Scope**:
  - .github/workflows/test.yml 中删除两个显式 bats 步骤
  - 保留 `bats tests/ --recursive` 作为唯一 bats 步骤
- **Out Scope**:
  - 不修改 Python 测试步骤
  - 不修改 assertion quality gate
  - 不修改其他 CI 配置

## 关键场景
- GIVEN CI 运行, WHEN 进入 bats 阶段, THEN 只运行一次 `bats tests/ --recursive`, 所有 704 个 test cases 被覆盖

## 技术约束
- MUST 保留 Python unit + integration 测试步骤
- MUST 保留 assertion tautology gate
- MUST 保留 arch/change alignment gate
- MUST 保留 spec validation gate

## 验收标准
- CI 配置删除 2 个显式 bats 步骤
- CI 运行时间缩短约 30-60 秒
- 所有 704 个 bats test cases 仍通过 `--recursive` 覆盖
