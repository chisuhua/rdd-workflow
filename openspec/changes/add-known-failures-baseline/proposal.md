# add-known-failures-baseline

## Why

- **2026-08-03 会话实测**: `bats tests/integration/` 在 master 与 worktree 各有 41 个失败（历史遗留/环境敏感用例，如 `adr_index`、`scan_state`、`doc_truth_sync` 等）。为证明本 change 零回归，需完整跑两遍全量（约 10 分钟），再用 `comm -23` 对比失败清单。此成本每个 change 重复支付。
- **CI 门控现状**: `.github/workflows/test.yml` 按序执行全量 bats 子集，这些已知失败必然 red；本地无"已知失败清单"基线文件，无法区分"本次引入"与"历史遗留"。
- **既有模式**: 仓库已有 `tests/README.md` 描述测试布局与运行方式，但无失败基线管理。bats-core 支持 `--filter` / `--filter-out` 参数，可用于排除已知失败。
- **效率动机**: 回归甄别从 ~10 分钟（两遍全量 + 手工 diff）压缩到 ~1 分钟（一遍全量 + 自动 diff 基线）。

## What Changes

**In Scope**:

- **In Scope**:
- 新增 `tests/KNOWN_FAILURES.txt`：已知失败测试名清单（当前 41 项，来自 master 基线），每行一个测试名 + 注释（原因/环境依赖）
- 新增辅助脚本 `tests/scripts/report_regression.sh`（或等效 bats helper）：跑全量 → 对比 KNOWN_FAILURES.txt → 输出"增量失败"报告（仅列出不在基线中的失败）
- `tests/README.md` 增加 KNOWN_FAILURES 维护说明（如何添加/移除/更新基线）
- CI 门控（.github/workflows/test.yml）增加增量失败检查步骤：全量跑完对比基线，仅当存在**新增**失败时 fail
- 提供基线刷新命令（`bash tests/scripts/refresh_known_failures.sh`）生成当前全量失败清单
- **Out Scope**:
- 不修复任何已知失败用例本身（留作各自 change 处理）
- 不修改现有测试内容（除非基线刷新需要）
- 不引入新测试框架或 mocking 层
- 不改变 bats 的运行方式（仍跑全量，只是报告对比基线）

### 关键场景

- **GIVEN** 开发者完成一个 change 且仅修改了受影响的测试
  **WHEN** 运行 `npm test` 或 CI
  **THEN** 增量失败报告显示"0 个新增失败"（41 个已知失败被基线过滤），CI 通过

- **GIVEN** 开发者引入真实回归（新增一个失败用例）
  **WHEN** 运行增量失败报告
  **THEN** 该用例被标记为"新增失败"，CI fail，提示修复或确认为已知后加入基线

- **GIVEN** 环境变化导致某已知失败被修复（如 ADR 索引补齐）
  **WHEN** 运行基线刷新命令
  **THEN** 该用例从 KNOWN_FAILURES.txt 移除（基线自动收敛）

- **GIVEN** 开发者想了解当前已知失败清单
  **WHEN** 查看 `tests/KNOWN_FAILURES.txt`
  **THEN** 能看到 41 项及其环境依赖原因注释

**Out of Scope**:

- design 阶段不生成 tasks.md / design.md / specs (留在 plan fill)
- 不修改 ADR-0003 (另起 ADR 记录本次职责再分配)


## Capabilities

- `design-proposal-creation`: design 审批批准即创建完整 openspec change
- `design-content-review`: 两层内容审查 (improvements 5 段 + openspec validate), warning / strict 双模式


## Impact

- **受影响文件**: `skills/guide-design/SKILL.md` + 4 个 scripts, `skills/guide-plan/scripts/plan_intake.sh`, `docs/adr/ADR-0025-*.md` (新增)
- **兼容性**: `SKIP_DESIGN_HANDOFF=yes` 存量路径行为不变
- **硬约束**: 批准动作幂等; env-var 传参 (Oracle C1)


## Acceptance

- `tests/KNOWN_FAILURES.txt` 存在且包含当前 41 项已知失败（带原因注释）
- 全量跑完后增量失败报告在零回归时输出"0 新增"且 exit 0
- 人为制造一个失败（如临时改坏一个文件）时报告标出"1 新增失败"且 exit 非 0
- 基线刷新命令可生成与当前失败清单一致的基线文件
- 本地回归甄别耗时从 ~10 分钟降至 ~1 分钟
- CI 门控集成后，已知失败不再导致 red（仅新增失败 red）

