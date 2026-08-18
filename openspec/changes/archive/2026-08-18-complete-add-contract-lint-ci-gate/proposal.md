# complete-add-contract-lint-ci-gate

## Why

- `add-contract-lint-ci-gate` 提案（已归档，commit `f2f95dd`）声称完成跨仓库契约 lint CI 门控实施。
- 实际审计发现 3 个 AC 未达成：
  1. **README §跨项目协同 章节缺 CI 集成示例**（提案 AC #8 要求"README §跨项目协同 章节增加 CI 集成示例"）。
  2. **`rddf contract-check` CLI 子命令未在主入口注册**（用户必须调用 `python3 skills/contract-check/scripts/contract_check.py`，与 `rddf` CLI 体系不一致）。
  3. **`STRICT_CONTRACT_GATE` 环境变量未在任何脚本中 read**（`docs/strict-gate-boundary.md` 提到该变量，但 `plan_done_gate.sh` / `ship_monitor.sh` / `archive.sh` 均未读取，等于"文档存在但无效果"）。
- 已实现部分（无需重做）：`skills/contract-check/scripts/contract_check.py` 主脚本、`contract_diff.py::DiffEngine`、`contract_cache_schema.json` SSOT、15 个单元测试 + 3 个 bats 集成测试全 pass。

## What Changes

**In Scope**:

- 在 `_lib/cli/contract_check_cmd.py` 实现 `rddf contract-check` 子命令（委托给 `skills/contract-check/scripts/contract_check.py`），注册到 `__main__.py` dispatch table。
- 在 `skills/guide-plan/scripts/plan_done_gate.sh` 中 read `STRICT_CONTRACT_GATE=yes`，调 `rddf contract-check` 校验活跃 changes 关联的 Hub-Spoke 契约对；breaking-change 默认 warning，`STRICT_*` 模式下升级为 error。
- 给 README §跨项目协同 章节增加 CI 集成示例（GitHub Actions、GitLab CI 两段 snippet）。
- 新增 `tests/integration/test_rddf_contract_check_cli.bats` 验证 CLI 注册（≥3 用例：help / exit code / 子命令列表）。
- 新增 `tests/integration/test_strict_contract_gate_wiring.bats` 验证 env var 在 plan-done gate 中实际生效（≥3 用例）。

### 关键场景

- GIVEN `add-contract-lint-ci-gate` 已实施但 `rddf contract-check` 不存在, WHEN 用户在第三方项目运行 `rddf --help`, THEN 看到 `contract-check` 子命令；运行 `rddf contract-check --hub X --local Y` 输出与 `python3 skills/contract-check/scripts/contract_check.py` 一致。
- GIVEN `STRICT_CONTRACT_GATE=yes` + 某个活跃 change 关联的契约对存在 breaking-change, WHEN `plan_done_gate` 执行, THEN 调 `rddf contract-check` 校验，发现 breaking → 升级为 error 并阻断 plan-done。
- GIVEN 默认环境（无 STRICT_*_GATE）+ 同上 breaking-change, WHEN `plan_done_gate` 执行, THEN 调 `rddf contract-check` 校验，仅 warning 输出，plan-done 继续成功。
- GIVEN 用户阅读 README §跨项目协同 章节, WHEN 看到新增 CI 集成示例, THEN 可直接复制 GitHub Actions / GitLab CI snippet 在自家项目复用（包含 `rddf contract-check` 触发时机、缓存策略、strict 模式开关）。

**Out of Scope**:

- 不修改 `skills/contract-check/scripts/contract_check.py` 核心逻辑（已实现完整）。
- 不实现 `add-mcp-cross-repo-protocol` 等其他 cross-repo 提案的 `STRICT_*_GATE` 变量（仅补本提案承诺的 `STRICT_CONTRACT_GATE`）。
- 不修改 `docs/strict-gate-boundary.md`（文档已对齐，只需代码补齐）。
- 不引入新外部依赖（CI 示例仅描述配置模式，不嵌实际 GitHub Action）。

## Capabilities

- MUST 实现 `rddf contract-check` CLI 子命令（delegating 现有 `skills/contract-check/scripts/contract_check.py`），不重复实现 DiffEngine。
- MUST 在 `plan_done_gate.sh` 实际 read `STRICT_CONTRACT_GATE` env var（参照 `STRICT_CHANGE_GATE` 已实现的 escalation pattern）。
- MUST 严格遵守 ADR-0018 gate escalation 模式：默认 warning、`STRICT_*=yes` 升级 error、`SKIP_*=yes` 跳过。
- SHOULD 让 README CI 示例既能用于 GitHub Actions 也能用于 GitLab CI（双 snippet，不偏 AI 编程助手）。
- SHOULD NOT 在本提案修改 docs/strict-gate-boundary.md（文档本身准确，只是代码缺失）。

## Impact

- MUST NOT 修改 `contract_check.py` / `contract_diff.py` 主逻辑（已 18/18 test 通过，不动实现）。

## Acceptance

- `rddf --help` 输出包含 `contract-check` 子命令；`rddf contract-check --help` 输出与原 `python3 skills/contract-check/scripts/contract_check.py --help` 等价（参数、format、cache-file 一致）。
- `tests/integration/test_rddf_contract_check_cli.bats` 新增 ≥3 用例：`cli register` / `delegation consistency` / `exit code propagation` 全部 pass。
- `tests/integration/test_strict_contract_gate_wiring.bats` 新增 ≥3 用例：默认 warning / `STRICT_CONTRACT_GATE=yes` error / `SKIP_CONTRACT_GATE=yes` skip 全部 pass。
- README.md §跨项目协同 章节末尾新增 `### CI 集成示例` 子节，含 GitHub Actions + GitLab CI 两段配置（≥10 行 / 段）。
- 现有 `tests/unit/test_contract_diff.py` 15 个 + `tests/integration/test_contract_check_cli.bats` 3 个测试保持 pass（无 regression）。
- 手工验证：在第三方项目目录运行 `rddf contract-check --hub <openapi.yaml> --local <impl.py>` 退出码 = 0（无 breaking）/ 1（breaking），与原脚本一致。

