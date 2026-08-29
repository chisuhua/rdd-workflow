# phase-1-general-20260829063800-2

## Why

`ADR-0009` (scheduled triggers) + `ADR-0011` (phase step pipeline) 已定义 cron/fs-watcher/git-hook/webhook 4 种 scheduler,但 `_lib/schedulers/` 4 个模块测试覆盖不全,git-hook 自动安装未对接 `install.sh`,webhook 接收端缺 auth。**Why now**: 启用 watch-hub 时 cron 调度需要稳定基线,否则 hub issue 同步会 silently skip。

## What Changes

**In Scope**:

- **Out Scope**: 分布式调度;scheduler UI 控制台

### 关键场景

- GIVEN cron 调度 `*/5 * * * * rddf watch-hub`
  WHEN 系统时间到达  THEN watch-hub 在 5 秒内执行完成,无重复触发 (idempotent lock)
- GIVEN git commit 修改 `.rddf/state/iteration.json`
  WHEN post-commit hook 触发
  THEN run_guide_state_sync 入口被调用,state 文件更新

**Out of Scope**:

- (no items specified)

## Capabilities

- MUST: 4 个 scheduler 启动幂等,重复实例不冲突 (pid file + lock)
- SHOULD: 提供 `rddf scheduler status` 一次性查询4 个 scheduler 状态

## Impact

- MUST NOT: 引入新依赖 (沿用 `croniter`/`watchdog`/`python-dotenv`)

## Acceptance

- 4 scheduler × 3 场景 = 12 测试用例全部 pass
- `install.sh --git-hooks` 安装后 hooks 生效实测
- webhook HMAC 验签单元测试覆盖4 种异常路径

