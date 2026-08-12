# add-issue-reporter-tests

> **优先级**: P1
> **来源**: ADR-0027 实施拆分
> **前置依赖**: `add-issue-reporter-prereqs` + `add-issue-reporter`（必须先合并）
> **关联**: `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` In Scope 末段 "测试与文档"

## Why

`change-a` 写了 14 个 unit test（sanitizer 4 + config 4 + dedup 6），`change-b` 写了 ≥14 unit + ≥5 bats integration test。但两者均聚焦"自己代码"，**缺乏跨切面 + end-to-end + docs**：

1. **End-to-end integration tests**（≥3）：完整 5 环（detect → buffer → submit → close）跑一遍，验证 issue file 创建 + 权限探测 + 关闭全链路
2. **双模式 archive 集成测试**（≥2）：worktree + lightweight 各跑一次，验证 hook 都在 line 340/346 和 231/237 触发
3. **CI 抑制 + retention 端到端测试**（≥2）：`CI=true` 时 L2 降级、31 天前 closed file 被 prune
4. **第三方项目集成测试**（≥1）：模拟外部项目用 `~/.agents/skills/_lib/` 路径调用，与 `test_global_install_external_project.bats` 模式一致
5. **跨切面 unit test**（≥2）：CLI 路由 + env cache schema 联合验证
6. **docs 更新**：`docs/architecture/extension-points.md`（新增"添加上报触发点"小节）、`docs/architecture/historical-evolution.md`（新增 v2.1.x 条目）、`CHANGELOG.md`（Unreleased 段）

**为什么独立成一个 change**: 13+ 个 test + 3 个 doc 文件的纯"测试与文档"工作，与代码功能正交，应在 a/b 落地后单独 ship，便于 review 时聚焦"是否覆盖完整"。

## What Changes

**In Scope**:

- **新增 `tests/integration/test_issue_reporter_e2e.bats`**：≥3 个 end-to-end test（write → submit → close 全链路）
- **新增 `tests/integration/test_archive_close_dual_mode.bats`**：≥2 个双模式 archive hook 测试
- **新增 `tests/integration/test_ci_suppression_and_retention.bats`**：≥2 个 CI 抑制 + retention 测试
- **新增 `tests/integration/test_issue_reporter_external_project.bats`**：≥1 个第三方项目全局安装测试
- **新增 `tests/unit/test_cli_env_cache_integration.py`**：≥2 个 CLI 路由 + env cache schema 联合测试
- **改造 `docs/architecture/extension-points.md`**：新增"添加上报触发点"小节
- **改造 `docs/architecture/historical-evolution.md`**：v2.1.x 段记录 ADR-0027 落地时间线
- **改造 `CHANGELOG.md`**：Unreleased 段记录 issue reporter 实施
- **改造 `docs/adr/README.md`**：把 ADR-0027 从"已采纳（v2.1.x+ 候选）"更新为"已实施（v2.1.x+）"

**Out of Scope**:

- 不写新代码（仅测试与文档）
- 不改任何 `_lib/` 或 `skills/` 实现文件
- 不写 performance benchmark（`change-c` 关注覆盖完整，不关注性能）

### 关键场景

- GIVEN end-to-end test, WHEN 完整 5 环跑一遍, THEN issue file 创建 + gh submit mock + close hook 调用都被记录
- GIVEN worktree 模式 archive 测试, WHEN 跑 mock archive, THEN `_lib/archive.sh` 在 line 340 后调用 `close_issues_for_change`
- GIVEN lightweight 模式 archive 测试, WHEN 跑 mock archive, THEN `ship_archive.sh` 在 line 231 后调用 `close_issues_for_change`
- GIVEN `CI=true` 测试, WHEN reporter 触发, THEN L2 跳过，issue 仅写本地
- GIVEN retention 测试, WHEN 31 天前 closed file + 30 天前 closed file + 5 天前 closed file 混合, THEN 仅 31 天前的被删除
- GIVEN 外部项目测试, WHEN 通过 `~/.agents/skills/_lib/` 路径调用 reporter, THEN 走 shim 路径生效
- GIVEN docs 更新, WHEN `docs-restructure` 校验, THEN architecture snapshots 包含新增 §上报触发点

## Capabilities

### 1. End-to-end integration tests

- MUST 覆盖 5 环全链路：detect → buffer → submit (mock) → archive → close
- MUST 用 bats + python helper 混合（bash orchestration + python subprocess mock）
- MUST 每次测试前后清理 `.rddf/issues/`、`gh` mock 状态
- MUST ≥3 e2e test

### 2. 双模式 archive 测试

- MUST 验证 `_lib/archive.sh` worktree 模式 hook 触发
- MUST 验证 `ship_archive.sh` lightweight 模式 hook 触发
- MUST 验证 hook 失败时 archive 仍成功
- MUST ≥2 dual-mode test

### 3. CI 抑制 + retention 测试

- MUST 验证 `CI=true` 时 L2 降级
- MUST 验证 retention 边界（30/31 天）
- MUST 验证 unsubmitted file 不被 prune
- MUST ≥2 test

### 4. 第三方项目测试

- MUST 复用 `test_global_install_external_project.bats` 的 `$BATS_TMPDIR` 模式
- MUST 验证 shim 路径发现
- MUST 验证 shim 缺失时降级
- MUST ≥1 test

### 5. CLI + env cache 联合测试

- MUST 验证 4 个 CLI 子命令与 `gh_available` env cache 字段交互
- MUST 验证 `gh_available=false` 时 CLI 提示 "gh not available"
- MUST ≥2 test

### 6. Docs 更新

- MUST `extension-points.md` 新增"添加上报触发点"小节
- MUST `historical-evolution.md` v2.1.x 段记录 ADR-0027
- MUST `CHANGELOG.md` Unreleased 段记录 issue reporter
- MUST `docs/adr/README.md` 把 ADR-0027 标记为已实施

## Impact

- 影响文件：
  - 新增: `tests/integration/test_issue_reporter_e2e.bats`（~150 行）
  - 新增: `tests/integration/test_archive_close_dual_mode.bats`（~80 行）
  - 新增: `tests/integration/test_ci_suppression_and_retention.bats`（~80 行）
  - 新增: `tests/integration/test_issue_reporter_external_project.bats`（~100 行）
  - 新增: `tests/unit/test_cli_env_cache_integration.py`（~80 行）
  - 修改: `docs/architecture/extension-points.md`（+30 行）
  - 修改: `docs/architecture/historical-evolution.md`（+20 行）
  - 修改: `CHANGELOG.md`（+15 行）
  - 修改: `docs/adr/README.md`（+2 行）
- 兼容性：所有现有 test 保持通过
- 风险：低 — 纯测试与文档，无新功能

## Acceptance

- 5 个新 test file 全部通过（≥10 e2e + bats cases）
- 现有 `./test.sh --full --regression` 0 new failure
- 4 个 doc 文件更新无 lint error
- `openspec validate add-issue-reporter-tests --type change --json` 0 errors
- commit message: `test(reporter): add end-to-end + dual-mode + docs`
