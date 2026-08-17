# complete-add-contract-lint-ci-gate — Tasks

> Schema: spec-driven
> See: `proposal.md` (motivation/scope) + `design.md` (technical decisions).

## Implementation

- [ ] 1.1 创建 `_lib/cli/contract_check_cmd.py`(参照 `_lib/cli/ac_verify_cmd.py` 模板)
  - 函数签名: `cmd_contract_check(args: list[str]) -> int`
  - argparse 参数透传: `--hub`, `--local`, `--cache-file`(与 `contract_check.py::main` 完全对齐)
  - 委托方式: `subprocess.run(["python3", "<project_root>/skills/contract-check/scripts/contract_check.py", *args], cwd=project_root)`
  - 退出码透明传播: `return result.returncode`
- [ ] 1.2 在 `_lib/cli/__init__.py` 的 `_ROUTES` 字典中插入 `"contract-check"` 路由
  - 位置: 字典按字母序插入,在 `"deps"` 之后
  - 值: `"contract-check": "skills._lib.cli.contract_check_cmd:cmd_contract_check"`
  - 验证: `list_commands()` 自动包含新条目
- [ ] 1.3 在 `skills/guide-plan/scripts/plan_done_gate.sh` 实现 `STRICT_CONTRACT_GATE` 接线
  - 在 line 146(`STRICT_CHANGE_GATE` 检查)之后新增 `check_contract_gate` 调用
  - 函数体(默认 warning):
    ```bash
    if [ "${SKIP_CONTRACT_GATE:-no}" = "yes" ]; then
      echo "[SKIP] contract gate skipped"
      return 0
    fi
    contract_output=$(rddf contract-check 2>&1) || contract_rc=$?
    if [ "${contract_rc:-0}" -ne 0 ]; then
      if [ "${STRICT_CONTRACT_GATE:-no}" = "yes" ]; then
        echo "❌ STRICT_CONTRACT_GATE: contract breaking-change detected" >&2
        return 1
      fi
      echo "⚠️ contract breaking-change: $contract_output" >&2
    fi
    ```
  - 现有 plan quality checks(`run_plan_checks` + `change_alignment`)不受影响
- [ ] 1.4 README.md §跨项目协同 章节末尾新增 `### CI 集成示例` 子节
  - GitHub Actions snippet(≥10 行):
    ```yaml
    name: contract-check
    on: [push, pull_request]
    jobs:
      contract-lint:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: actions/setup-python@v5
            with: { python-version: "3.11" }
          - run: pip install -r requirements.txt
          - run: rddf contract-check --hub contracts/openapi.yaml --local impl/api.py
            env:
              STRICT_CONTRACT_GATE: ${{ github.event_name == 'pull_request' }}
              SKIP_CONTRACT_GATE: ${{ github.event_name == 'push' }}
    ```
  - GitLab CI snippet(≥10 行): 同样结构,翻译为 `.gitlab-ci.yml` 格式
- [ ] 1.5 新增 `tests/integration/test_rddf_contract_check_cli.bats`(≥3 用例)
  - Case 1: CLI 注册 — `python3 -m skills._lib.cli --help` 输出包含 `contract-check`
  - Case 2: 委托一致性 — `python3 -m skills._lib.cli contract-check --help` 与原脚本 `--help` 参数列表一致
  - Case 3: 退出码传播 — mock breaking diff → exit 1;non-breaking diff → exit 0
- [ ] 1.6 新增 `tests/integration/test_strict_contract_gate_wiring.bats`(≥3 用例)
  - Case 1: 默认 warning — mock breaking diff + 无 STRICT_CONTRACT_GATE → `plan_done_gate` exit 0 + stderr warning
  - Case 2: STRICT 升级 — `STRICT_CONTRACT_GATE=yes` + breaking diff → exit 1 + stderr "❌ STRICT_CONTRACT_GATE"
  - Case 3: SKIP 跳过 — `SKIP_CONTRACT_GATE=yes` + breaking diff → exit 0,无任何输出
- [ ] 1.7 验证现有 contract-check 测试保持 pass(无 regression)
  - `tests/unit/test_contract_diff.py` 15 个测试保持 pass
  - `tests/integration/test_contract_check_cli.bats` 3 个测试保持 pass
  - 验证 contract_check.py 核心逻辑未被本提案修改(只通过 subprocess 委托)
- [ ] 1.8 手工验证
  - 在第三方项目目录运行 `rddf --help` 输出包含 `contract-check`
  - 运行 `rddf contract-check --hub <openapi.yaml> --local <impl.py>` 退出码 = 0(无 breaking)/ 1(breaking)
  - 设置 `STRICT_CONTRACT_GATE=yes` + breaking 场景 → plan_done_gate exit 1
  - 设置 `SKIP_CONTRACT_GATE=yes` → 所有 plan-done 流程 bypass contract gate
  - 默认模式下 breaking diff → exit 0 + stderr warning(可继续 plan-done)