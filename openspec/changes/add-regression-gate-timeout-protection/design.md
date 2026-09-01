# add-regression-gate-timeout-protection

## Context

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

## Goals

**In Scope**:

- 默认 600s（10 分钟）？否——保持向后兼容（默认无超时），opt-in `--max-duration=600`
- 超时行为：优雅退出 + 保存当前结果到 `.rddf/state/.regression-partial.json`（或临时文件）
- `timeout` 命令包裹 bats 调用，超时后 kill bats + 输出部分 progress
- 修改 `report_regression.sh`：`bats tests/ --recursive` 输出追加到 stdout（而非仅 TMP 文件）
- 或用 `--report-formatter`（bats 支持 TAP13 增量输出）透传到 stdout
- `run_bats_recursive` 输出 bats 每文件进度（`ok 1/23 ...` / `not ok`），让 8 分钟内可观察
- 最终 summary 保留（已知/新增/基线已修复）
- 新增 `tests/scripts/report_regression.sh --partial <dir>` 模式：读取 `.rddf/state/.regression-partial.json` 中已通过结果，跳过重跑已通过文件（增量）
- 或简化：超时/中断时把 `$TMP_DIR/bats-output` 保留到 `.rddf/state/last-bats-output.txt`（可手动检查）
- 目标：中断后重跑时，已知通过的文件不再重跑（节省时间）
- `docs/change-quality-guide.md` 加"回归门超时与进度"段
- `AGENTS.md` "快速命令"段补充 `--max-duration` 示例
- **不修改** bats 本身（`--report-formatter` 是 bats 已有能力，直接复用）
- **不实现** 并行回归门（bats `--jobs` 是另一提案范围，本提案只做超时/进度）
- **不修改** `report_regression.sh` 的新增失败判定语义（comm -23）
- **不修改** KNOWN_FAILURES 基线格式

### 关键场景

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

**Out of Scope**:

- (no items specified)

## Decisions

- **MUST NOT**: 改变 `report_regression.sh` 的退出码语义（0=无新增=pass）
- **MUST NOT**: 改变 KNOWN_FAILURES baseline 格式
- **MUST NOT**: 引入新依赖（timeout 命令 / bats 内置 flag 即可）
- **MUST**: 默认行为向后兼容（不传参时无超时）
- **SHOULD**: 进度透传用 bats 原生 `--report-formatter tap13`（若版本支持）或 stdout 重定向
- **SHOULD**: 部分结果保存用 `.rddf/state/` 目录（gitignored）

## Risks

- (no items specified)
