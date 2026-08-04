## Context

**背景**: `bats tests/integration/` 在 master 与 worktree 各有 41 个失败（历史遗留/环境敏感用例，如 `adr_index`、`scan_state`、`doc_truth_sync` 等）。为证明每个 change 零回归，当前需完整跑两遍全量（约 10 分钟），再用 `comm -23` 手工对比失败清单——此成本每个 change 重复支付。CI 门控 `.github/workflows/test.yml` 按序执行全量 bats（`bats tests/ --recursive`），这些已知失败必然 red；本地无"已知失败清单"基线文件，无法区分"本次引入"与"历史遗留"。

**当前状态**: `tests/README.md` 描述测试布局与运行方式，但无失败基线管理。bats-core 支持 `--filter` / `--filter-out` 参数，可用于排除已知失败。仓库无 `tests/scripts/` 目录（将新建）。CI 最后一个步骤直接跑 `bats tests/ --recursive`，无增量失败对比逻辑。

**约束**:
- MUST KNOWN_FAILURES.txt 用测试名（bats 的 `@test` 名称）标识，不用行号（行号易漂移）
- MUST 增量失败报告只报告"不在基线中的失败"，基线中的失败仅统计数量不 fail
- MUST 基线刷新命令生成格式与 KNOWN_FAILURES.txt 完全一致（可反向 diff）
- MUST NOT 静默吞掉基线中的失败（报告仍显示"N 个已知失败"）
- MUST NOT 将增量失败自动加入基线（必须人工确认后刷新）
- SHOULD CI 与本地使用同一套对比脚本（单一来源）

## Goals / Non-Goals

**Goals**:
- 新增 `tests/KNOWN_FAILURES.txt`：已知失败测试名清单（当前 41 项，来自 master 基线），每行一个测试名 + 注释（原因/环境依赖）
- 新增辅助脚本 `tests/scripts/report_regression.sh`：跑全量 → 对比 KNOWN_FAILURES.txt → 输出"增量失败"报告（仅列出不在基线中的失败）
- `tests/README.md` 增加 KNOWN_FAILURES 维护说明（如何添加/移除/更新基线）
- CI 门控（.github/workflows/test.yml）增加增量失败检查步骤：全量跑完对比基线，仅当存在**新增**失败时 fail
- 提供基线刷新命令（`bash tests/scripts/refresh_known_failures.sh`）生成当前全量失败清单
- 本地回归甄别耗时从 ~10 分钟降至 ~1 分钟

**Non-Goals**:
- 不修复任何已知失败用例本身（留作各自 change 处理）
- 不修改现有测试内容（除非基线刷新需要）
- 不引入新测试框架或 mocking 层
- 不改变 bats 的运行方式（仍跑全量，只是报告对比基线）

## Decisions

### 决策 1: 基线文件用 bats `@test` 测试名标识，行级注释说明原因

`tests/KNOWN_FAILURES.txt` 每行一个测试名（bats `@test` 名称，格式 `file.bats: test name` 或纯测试名），后接 `#` 注释说明失败原因/环境依赖。不用行号（行号随文件编辑漂移）。基线刷新命令生成格式与人工维护格式完全一致，可反向 diff。

### 决策 2: 单一对比脚本 `report_regression.sh`，CI 与本地共用

新建 `tests/scripts/report_regression.sh`：跑全量 bats → 提取失败测试名集合 → `comm -23 <实际失败> <基线>` 计算增量失败 → 输出报告（0 新增时 exit 0；有新增时 exit 非 0 并列出）。`refresh_known_failures.sh` 生成当前全量失败清单写入 KNOWN_FAILURES.txt。CI 与本地调用同一脚本，杜绝两套逻辑漂移。

### 决策 3: CI 增量失败门控插在 `bats tests/ --recursive` 之后

`.github/workflows/test.yml` 在最后一步 bats 之后新增步骤：运行 `report_regression.sh`（或等效 bats 收集器），仅当存在**新增**失败（不在 KNOWN_FAILURES.txt 中）时 fail。基线中的失败仍显示"N 个已知失败"但不算 fail，避免已知失败让每个 change 的 CI 必然 red。刷新基线是显式人工操作，CI 不自动写入。

### 决策 4: 失败集合提取依赖 bats 输出格式，需先锁定解析规则

bats 输出格式（`not ok N test name` 或 TAP 格式）在 bats-core 1.10+ 下稳定，但需先实测确认当前 41 个失败的精确提取规则（`bats tests/ --recursive 2>&1 | grep '^not ok'`），并以解析脚本单测锁定。若 bats 版本差异导致格式变化，解析脚本保留 fallback 并输出告警而非静默误判。

## Risks

- **测试名格式漂移**: bats 版本升级改变失败输出格式 → 解析规则以单测锁定，格式变化时解析脚本告警而非静默误判
- **基线陈旧**: KNOWN_FAILURES.txt 与当前失败集合不一致（环境变化） → 基线刷新命令提供显式收敛路径；报告显示基线中"已修复"的条目，提示刷新
- **增量失败被误判**: 解析错误把已知失败算作新增 → 增量失败必须用 `comm` 集合差（与基线逐条对比），并有单测覆盖边界
- **CI 与本地行为不一致**: CI 环境（ubuntu-latest）与本地 bats 版本差异 → 单一脚本 + CI 与本地共用，测试先在本机验证再上 CI
- **刷新命令覆盖人工注释**: 自动刷新覆盖手动维护的原因注释 → 刷新命令保留既有注释（按测试名 merge），仅新增/删除条目
- **已知失败静默**: 报告吞掉基线失败 → 报告始终显示"N 个已知失败"统计，不 fail 但可见

## Open Questions

- 无；基线文件格式、对比脚本、CI 门控位置与刷新语义均由 proposal 和 improvement source 明确约束。
