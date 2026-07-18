## Why

CI 的 `bats tests/ --recursive` 已运行全部 704 个 test cases。其后两个显式 `bats tests/integration/test_*.bats` 步骤是冗余的双重运行，浪费 CI 时间约 30-60 秒。

## What Changes

- `.github/workflows/test.yml` 中删除两个显式 bats 步骤
- 保留 `bats tests/ --recursive` 作为唯一 bats 步骤
- 保留 Python 测试、assertion gate、arch/change alignment gate、spec validation gate

## Capabilities

### New Capabilities
- （无——纯删除冗余步骤）

### Modified Capabilities
- （无——不改变测试行为）

## Impact

- **Affected code**: `.github/workflows/test.yml`（约 30 行删除）
- **Scope**: 仅 CI 配置
- **Risk**: 极低——`bats tests/ --recursive` 已在所有 commit 中运行通过
- **Effort**: 5 分钟