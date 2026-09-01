# add-regression-gate-timeout-protection

**优先级**: P2 | **来源**: 2026-08-31 ship 阶段复盘 — 回归门 `./test.sh --full --regression` 一次 ~8 分钟，期间无法有效监控/中断
**阶段**: v2.2 | **分类**: infra-setup / 测试基建
**类型**: feature / robustness

> **症状**：回归门 `./test.sh --full --regression` 单次运行 ~8 分钟（bats 全量），多次重跑时（本 session 4 轮）总耗时 ~32 分钟，且运行期间进度不可观测、无法优雅中断。
> **根因**：`test.sh` 的 `run_bats_recursive` 直接用 `bash tests/scripts/report_regression.sh`（内部跑完整 `bats tests/ --recursive`），无超时/进度/中断控制。

## 架构依据

**症状 (2026-08-31 ship 阶段, 2 个 P1 change)**:

- 本 session 跑 4 轮 `./test.sh --full --regression`：
  - 第 1 轮：新增失败 2（KNOWN_FAILURES drift）
  - 第 2 轮：新增失败 1（specs/ 缺失 + ADR 结构）
  - 第 3 轮：新增失败 1（cli_all_subcommands + setup_file failed）
  - 第 4 轮：pytest 全绿 + bats baseline 收敛
- 每轮 ~8 分钟（bats 全量 515-707s）+ pytest ~80s
- 4 轮合计 ~32 分钟回归门时间
- 运行期间 `tail -f` 只能看到 `=== bats regression (baseline-aware) ===` 一行（bats 内部输出被吞），无法观察进度
- 120s bash 默认超时强制早停，无法有效长跑

**根因分析**:

`test.sh::run_bats_recursive()`:

```bash
run_bats_recursive() {
  if [ "$WITH_REGRESSION" = "1" ]; then
    run_step "bats regression (baseline-aware)" \
      bash tests/scripts/report_regression.sh
  else
    run_step "bats recursive" bats tests/ --recursive "$@"
  fi
}
```

- `report_regression.sh` 内部 `bats tests/ --recursive` 的输出被重定向到临时文件（`> "$TMP_DIR/bats-output"`），只有最终 summary（已知/新增/基线中已修复）输出
- 运行 8 分钟内**零进度输出**，无法判断是「正常运行」还是「挂死」
- 无 `--max-duration` 超时，无「部分 results 保存」机制
- 无优雅中断（SIGINT 直接 kill，无中间结果落盘）

**影响范围**:

- 多次重跑（4 轮）总耗时长且不可观测
- 无法判断「是否应等待」vs「是否挂死」→ 需人工 `ps` 检查
- 无中间结果保存，重跑无法复用已通过部分
- 对后续 `add-session-metrics-collection` (P2-6) 形成依赖：metrics 需 phase 时间戳，而回归门无阶段断点

## 范围

### In Scope

**A. `./test.sh --full` 增加 `--max-duration` 参数**:

- 默认 600s（10 分钟）？否——保持向后兼容（默认无超时），opt-in `--max-duration=600`
- 超时行为：优雅退出 + 保存当前结果到 `.rddf/state/.regression-partial.json`（或临时文件）
- `timeout` 命令包裹 bats 调用，超时后 kill bats + 输出部分 progress

**B. 进度输出（bats 内部 progress 透传）**:

- 修改 `report_regression.sh`：`bats tests/ --recursive` 输出追加到 stdout（而非仅 TMP 文件）
  - 或用 `--report-formatter`（bats 支持 TAP13 增量输出）透传到 stdout
- `run_bats_recursive` 输出 bats 每文件进度（`ok 1/23 ...` / `not ok`），让 8 分钟内可观察
- 最终 summary 保留（已知/新增/基线已修复）

**C. 部分结果保存（重跑可复用）**:

- 新增 `tests/scripts/report_regression.sh --partial <dir>` 模式：读取 `.rddf/state/.regression-partial.json` 中已通过结果，跳过重跑已通过文件（增量）
- 或简化：超时/中断时把 `$TMP_DIR/bats-output` 保留到 `.rddf/state/last-bats-output.txt`（可手动检查）
- 目标：中断后重跑时，已知通过的文件不再重跑（节省时间）

**D. 文档化**:

- `docs/change-quality-guide.md` 加"回归门超时与进度"段
- `AGENTS.md` "快速命令"段补充 `--max-duration` 示例

### Out Scope

- **不修改** bats 本身（`--report-formatter` 是 bats 已有能力，直接复用）
- **不实现** 并行回归门（bats `--jobs` 是另一提案范围，本提案只做超时/进度）
- **不修改** `report_regression.sh` 的新增失败判定语义（comm -23）
- **不修改** KNOWN_FAILURES 基线格式

## 关键场景

### 场景 1: 超时保护

- **GIVEN** 回归门运行超过 `--max-duration=600`
- **WHEN** timeout 触发
- **THEN**
  - bats 进程被 kill
  - 已完成的 bats 输出保存到 `.rddf/state/last-bats-output.txt`
  - stdout 输出 `⏱️ Regression gate timed out after 600s; partial results saved`
  - exit code 非 0（超时不算 pass）

### 场景 2: 进度可观测

- **GIVEN** 回归门运行中
- **WHEN** 观察 stdout
- **THEN** 看到每个 bats 文件进度（`ok 1/23 ...` 逐步输出）
- **AND** 最终 summary 保留（已知/新增/基线已修复）

### 场景 3: 中断后部分结果可复用

- **GIVEN** 回归门中断（超时/手动 Ctrl+C）
- **WHEN** 重跑 `./test.sh --full --regression --reuse-partial`
- **THEN** 已通过的文件不重跑（从 partial 结果读取），只跑未完成部分

### 场景 4: 默认行为不变

- **GIVEN** 不传 `--max-duration` / `--reuse-partial`
- **WHEN** 跑 `./test.sh --full --regression`
- **THEN** 行为与现状完全一致（无超时，全量跑，summary 正常）

## 技术约束

- **MUST NOT**: 改变 `report_regression.sh` 的退出码语义（0=无新增=pass）
- **MUST NOT**: 改变 KNOWN_FAILURES baseline 格式
- **MUST NOT**: 引入新依赖（timeout 命令 / bats 内置 flag 即可）
- **MUST**: 默认行为向后兼容（不传参时无超时）
- **SHOULD**: 进度透传用 bats 原生 `--report-formatter tap13`（若版本支持）或 stdout 重定向
- **SHOULD**: 部分结果保存用 `.rddf/state/` 目录（gitignored）

## 验收标准

### 单元与集成测试

- [ ] `tests/unit/test_test_sh_flags.py`（或 bats）覆盖 `--max-duration` 参数解析
- [ ] `tests/integration/test_regression_timeout.bats` 新增 3 个测试
  - [ ] `regression-timeout: --max-duration=1 times out gracefully`
  - [ ] `regression-timeout: partial results saved on timeout`
  - [ ] `regression-timeout: default behavior unchanged (no timeout)`
- [ ] 进度透传测试：`bats --report-formatter` 输出逐步可见

### 端到端验证

- [ ] `./test.sh --full --regression --max-duration=5` 5 秒后优雅超时 + 保存 partial
- [ ] 正常全量跑（无超时）behavior 不变
- [ ] 中断后 `--reuse-partial` 复用已通过文件（跑完未完成部分）

### 文档化

- [ ] `docs/change-quality-guide.md` 加"回归门超时与进度"段
- [ ] `AGENTS.md` 快速命令段补 `--max-duration` 示例

### 兼容性验证

- [ ] 与 `report_regression.sh` 既有逻辑不冲突（summary 输出不变）
- [ ] 与 `--regression` / `--stop-on-failure` 组合可用
- [ ] 与 P0-2（`report_regression.sh` sed bug 修复）不冲突（独立改动）

### 副作用监测

- [ ] ship 后 30 天：回归门平均等待时间下降（可观测进度 + 复用 partial）
- [ ] 不引入新的 KNOWN_FAILURES 条目

## Why

- **现状痛点**：回归门 8 分钟不可观测（无进度）、不可中断（超时无保护）、不可复用（重跑全量）。本 session 4 轮重跑合计 32 分钟，其中大部分是等待 + 手工 `ps` 检查是否挂死。
- **修复价值**：让回归门可观测（进度透传）、可保护（超时）、可复用（partial）。低成本（timeout flag + bats report formatter + partial 保存）。
- **Why now**: 2026-08-31 session 4 轮回归门触发，暴露等待/不可观测痛点。P2 而非 P1 因为它不阻塞 flow（仅体验/效率），且与 P2-6（session metrics）形成配套。

## What Changes

- `test.sh`: 新增 `--max-duration` / `--reuse-partial` flag 解析（~15 行）
- `tests/scripts/report_regression.sh`: bats 进度透传（stdout）+ 部分结果保存（~10 行）
- `.rddf/state/last-bats-output.txt`: 超时保存的 bats 输出（运行时生成）
- `docs/change-quality-guide.md` + `AGENTS.md`: 文档更新
- `tests/integration/test_regression_timeout.bats`: 新测试（3 cases）

## Capabilities

- MUST: `--max-duration` 超时优雅退出 + 保存 partial
- MUST: bats 进度逐步透传（可观察）
- MUST: 默认行为向后兼容（无超时）
- MUST NOT: 改变回归门 pass/fail 语义

## Impact

- MUST: `report_regression.sh` summary 输出保留（已知/新增/基线已修复）
- MUST: 超时不误判为 pass（exit 非 0）
- SHOULD: partial 复用显著减少重跑时间
- MUST NOT: 与 P0-2（sed 修复）冲突

## Acceptance

- [ ] `./test.sh --full --regression --max-duration=5` 优雅超时 + partial 保存
- [ ] 正常全量跑 behavior 不变
- [ ] `--reuse-partial` 复用已通过文件
- [ ] bats 进度逐步输出可见
- [ ] 3 个集成测试 PASS
- [ ] 文档同步更新