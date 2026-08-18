# complete-add-contract-lint-ci-gate — Design

> Schema: spec-driven
> See: `proposal.md` for motivation, scope and acceptance criteria.

## Context

`add-contract-lint-ci-gate` 提案(已归档,commit `f2f95dd`)声称完成跨仓库契约 lint CI 门控实施。审计发现 3 个 AC 未达成:

1. **README §跨项目协同 章节缺 CI 集成示例**(原提案 AC #8 要求"README §跨项目协同 章节增加 CI 集成示例")
2. **`rddf contract-check` CLI 子命令未在主入口注册**(用户必须 `python3 skills/contract-check/scripts/contract_check.py`,与 `rddf` CLI 体系不一致)
3. **`STRICT_CONTRACT_GATE` 环境变量未在任何脚本中 read**(`docs/strict-gate-boundary.md` 提到该变量,但 `plan_done_gate.sh` / `ship_monitor.sh` / `archive.sh` 均未读取,等"文档存在但无效果")

已实现部分(`skills/contract-check/scripts/contract_check.py` 主脚本 + `contract_diff.py::DiffEngine` + `contract_cache_schema.json` SSOT + 15 unit + 3 bats 集成测试全 pass)无需重做。本提案补齐 CLI 注册、env var 接线、README CI 示例 3 个未完成 AC。

## Goals / Non-Goals

**Goals:**

- 实现 `rddf contract-check` CLI 子命令(委托 `skills/contract-check/scripts/contract_check.py`,不重复实现 DiffEngine)
- 在 `skills/guide-plan/scripts/plan_done_gate.sh` 实际 read `STRICT_CONTRACT_GATE=yes`,调 `rddf contract-check` 校验活跃 changes 关联的 Hub-Spoke 契约对
- 严格遵循 ADR-0018 gate escalation:默认 warning、`STRICT_*=yes` 升级 error、`SKIP_*=yes` 跳过
- README §跨项目协同 章节增加 CI 集成示例(GitHub Actions + GitLab CI 两段 snippet)
- 新增 `tests/integration/test_rddf_contract_check_cli.bats` (≥3 用例)
- 新增 `tests/integration/test_strict_contract_gate_wiring.bats` (≥3 用例)

**Non-Goals:**

- 不修改 `skills/contract-check/scripts/contract_check.py` 核心逻辑(已 18/18 test 通过)
- 不实现 `add-mcp-cross-repo-protocol` 等其他 cross-repo 提案的 `STRICT_*_GATE` 变量(仅补本提案承诺的 `STRICT_CONTRACT_GATE`)
- 不修改 `docs/strict-gate-boundary.md`(文档准确,只需代码补齐)
- 不引入新外部依赖(CI 示例仅描述配置模式,不嵌实际 GitHub Action)
- 不实现 Hub 端契约自动同步(`sync-hub` 已存在,本提案只补本地 CI 校验)

## Decisions

### 1. CLI 注册策略:模仿 ac-verify 子命令模式

`_lib/cli/contract_check_cmd.py` 创建独立 cmd handler(不直接 import `contract_check.py::main` 进入 `_ROUTES`,因 `contract_check.py` 已有完整 `argparse` 入口,委托 subprocess 方式更稳定)。

**Alternatives considered:**

- 直接 import `contract_check.main` 到 `_ROUTES`:破坏模块封装,`contract_check.py` 的 argparse exit 可能污染 CLI 流程 — 被否。
- 完全重写 `contract_check` 为 `_lib/cli` 内置:违反"不修改现有逻辑"约束(18/18 test 通过) — 被否。
- 走 `python3 -m` 方式而非 `bash script`:依赖 Python module path,工作树隔离下不稳定 — 被否(模仿 ac-verify 选择 bash wrapper)。

### 2. plan_done_gate.sh 中 STRICT_CONTRACT_GATE 接线位置

放在现有 `STRICT_CHANGE_GATE` 检查(line 146 附近)之后,作为独立的 gate 4 步骤。这样:

- 现有 plan quality checks(run_plan_checks + change_alignment)不受影响
- 新增 contract-check 调用是可独立禁用的(per env var)
- 与 `STRICT_DEPS_GATE` (`complete-add-cross-repo-deps-orchestration`) 同一文件位置,便于 cross-repo gate 集中管理

**Alternatives considered:**

- 在 `plan_done_gate.sh` 入口处(`run_plan_intake`)检查:与 ship / archive 阶段无 gate 一致性 — 被否。
- 创建新文件 `_lib/cross_repo_contract_gate.sh`:增加文件数量,与 `_lib/cross_repo_deps_gate.py` (planned by 关联提案)命名风格不一致 — 被否。

### 3. contract-check 调用粒度

仅校验活跃(active)changes 关联的契约对,不校验已归档(archived)changes。归档 change 已 lock-in 契约,无需重检。

**Alternatives considered:**

- 校验全部 changes(active + archived):CI 性能开销大,归档契约不应随时间变化 — 被否。
- 仅校验 cross-repo-federation category changes:其他 category 的 change 也可能引用 Hub 契约(如 `add-rddf-session-status-cmd` 引用 Hub audit log) — 被否。

### 4. breaking-change 判定标准

复用 `contract_diff.py::DiffEngine.BREAKING_KINDS`(已定义):`removed_endpoint`, `removed_field`, `type_changed`, `required_added`。其他变更视为 non-breaking。

**Alternatives considered:**

- 自定义 breaking 列表:违反 DRY,与现有 DiffEngine 逻辑不一致 — 被否。
- 所有 diff 都视为 breaking:过于激进,失去 gate escalation 分级意义 — 被否。

### 5. README CI 示例覆盖两个主流 CI 系统

GitHub Actions(`.github/workflows/*.yml`)和 GitLab CI(`.gitlab-ci.yml`),各 ≥10 行可复制 snippet。两个系统覆盖 ≥ 90% 用户群。

**Alternatives considered:**

- 仅 GitHub Actions:忽略 GitLab 用户(企业项目大量使用) — 被否。
- 加 CircleCI / Travis / Jenkins:扩展性低,示例膨胀,且提案范围仅承诺两个 — 被否。
- 嵌入真实 GitHub Action:引入外部依赖,与"配置模式示例"提案范围冲突 — 被否。

### 6. test_rddf_contract_check_cli.bats 关键场景

≥3 个 case:

1. CLI 注册: `python3 -m skills._lib.cli --help` 输出包含 `contract-check`
2. 委托一致性: `python3 -m skills._lib.cli contract-check --help` 输出参数与原脚本一致(`--hub`, `--local`, `--cache-file`)
3. 退出码传播: `python3 -m skills._lib.cli contract-check <breaking_diff>` 退出码 = 1

### 7. test_strict_contract_gate_wiring.bats 关键场景

≥3 个 case:

1. 默认 warning: 无 STRICT_CONTRACT_GATE + breaking diff → exit 0 + stderr warning
2. STRICT 升级: `STRICT_CONTRACT_GATE=yes` + breaking diff → exit 1 + stderr error
3. SKIP 跳过: `SKIP_CONTRACT_GATE=yes` + breaking diff → exit 0,无 warning

## Risks / Trade-offs

- **`contract-check` 退出码语义依赖现有 `contract_check.py` 行为**: 若未来 `contract_check.py` 调整退出码语义(0=无breaking, 1=breaking),本提案的 `rddf contract-check` CLI 透明传播,无影响。
- **plan_done_gate 新增 1 步延长 plan 阶段耗时**: 默认 warning 模式下 `rddf contract-check` 调用可能 5-10s(取决于 contract 数量)。**Mitigation**: `SKIP_CONTRACT_GATE=yes` 提供 escape hatch。
- **README 双 CI 示例膨胀**: README 增加 ≥20 行示例。**Mitigation**: 折叠为单一子节 `### CI 集成示例`,不展开其他 CI 系统。
- **跨提案命名一致性**: `STRICT_CONTRACT_GATE` 与 `STRICT_DEPS_GATE` (关联提案 `complete-add-cross-repo-deps-orchestration`) 命名风格一致,便于 cross-repo gate 集中管理。