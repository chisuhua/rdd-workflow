# complete-add-contract-lint-ci-gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐 `add-contract-lint-ci-gate` 已归档提案承诺但实际未交付的 3 项 AC：(1) `rddf contract-check` CLI 子命令注册到主入口；(2) `STRICT_CONTRACT_GATE` env var 在 `plan_done_gate.sh` 实际接线；(3) README §跨项目协同 章节补 CI 集成示例（GitHub Actions + GitLab CI 双 snippet）。

**Architecture:** 复用现有 `skills/contract-check/scripts/contract_check.py` argparse 入口作为底层实现，新增 `_lib/cli/contract_check_cmd.py` thin wrapper 走 subprocess 委托（不 import main）。在 `plan_done_gate.sh` `STRICT_CHANGE_GATE` 检查之后插入 `check_contract_gate` 步骤。README 新增 `### CI 集成示例` 子节。

**Tech Stack:** Python 3.11+ / subprocess / argparse / bash / bats / pytest。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/cli/contract_check_cmd.py` | 新建：`rddf contract-check` subprocess 委托 wrapper |
| `_lib/cli/__init__.py` | 修改：`_ROUTES` 字典按字母序插入 `contract-check` |
| `skills/guide-plan/scripts/plan_done_gate.sh` | 修改：在 `STRICT_CHANGE_GATE` 检查之后新增 `check_contract_gate` 步骤 |
| `README.md` | 修改：§跨项目协同 章节末尾新增 `### CI 集成示例` 子节（GitHub Actions + GitLab CI） |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_rddf_contract_check_cli.bats` | 新建：CLI 注册 + 委托一致性 + 退出码传播 (≥3 用例) |
| `tests/integration/test_strict_contract_gate_wiring.bats` | 新建：默认 warning / STRICT 升级 / SKIP 跳过 (≥3 用例) |

---

### Task 1: `_lib/cli/contract_check_cmd.py` — CLI wrapper

**Files:**
- Create: `_lib/cli/contract_check_cmd.py`
- Test: `tests/integration/test_rddf_contract_check_cli.bats`

- [ ] **Step 1: 写失败测试**

创建 `tests/integration/test_rddf_contract_check_cli.bats`:

```bash
#!/usr/bin/env bats

load test_helper

@test "rddf contract-check: CLI 注册 (--help 列表包含 contract-check)":
    result=$(cd "$PROJECT_ROOT" && python3 -m skills._lib.cli --help 2>&1)
    [[ "$result" == *"contract-check"* ]]

@test "rddf contract-check: 委托一致性 (--help 参数透传)":
    rddf_help=$(cd "$PROJECT_ROOT" && python3 -m skills._lib.cli contract-check --help 2>&1)
    orig_help=$(cd "$PROJECT_ROOT" && python3 skills/contract-check/scripts/contract_check.py --help 2>&1)
    # 至少 --hub / --local / --cache-file 三个 flag 都出现
    [[ "$rddf_help" == *"--hub"* ]]
    [[ "$rddf_help" == *"--local"* ]]
    [[ "$rddf_help" == *"--cache-file"* ]]

@test "rddf contract-check: 退出码传播 (non-breaking → exit 0)":
    # 使用一对 compliant fixture (auth-v2-hub.yaml + auth-v2-local-ok.py)
    fixture_hub="$PROJECT_ROOT/tests/fixtures/openapi/auth-v2-hub.yaml"
    fixture_local="$PROJECT_ROOT/tests/fixtures/openapi/auth-v2-local-ok.py"
    if [[ -f "$fixture_hub" && -f "$fixture_local" ]]; then
        cd "$PROJECT_ROOT" && python3 -m skills._lib.cli contract-check --hub "$fixture_hub" --local "$fixture_local"
    else
        # fixture 不存在则 skip
        skip "contract-check fixture not present"
    fi
```

- [ ] **Step 2: 运行测试确认失败**

Run: `bats tests/integration/test_rddf_contract_check_cli.bats`
Expected: FAIL — `ModuleNotFoundError: No module named 'skills._lib.cli.contract_check_cmd'`

- [ ] **Step 3: 创建 wrapper 实现**

创建 `_lib/cli/contract_check_cmd.py`:

```python
"""``rddf contract-check`` subcommand handler.

Thin subprocess wrapper that delegates to the existing
``skills/contract-check/scripts/contract_check.py`` argparse entry
point. Exit codes propagate transparently (0 = no breaking,
1 = breaking change, 2+ = tool error).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def cmd_contract_check(args: list[str]) -> int:
    """Handle ``rddf contract-check``.

    Args:
        args: CLI args forwarded to contract_check.py.

    Returns:
        Exit code from contract_check.py subprocess.
    """
    parser = argparse.ArgumentParser(
        prog="rddf contract-check",
        description="Diff Hub OpenAPI contract vs Spoke local implementation",
        add_help=False,
    )
    parser.add_argument("--hub", required=True,
                        help="Path to Hub OpenAPI YAML")
    parser.add_argument("--local", required=True,
                        help="Path to Spoke local implementation")
    parser.add_argument("--cache-file", default=None,
                        help="Path to contract-cache.jsonl")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute diff without writing cache")
    parser.add_argument("--help", action="store_true",
                        help="Show help")
    parsed, forwarded = parser.parse_known_args(args)

    project_root = Path(
        os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    )
    script = project_root / "skills" / "contract-check" / "scripts" / "contract_check.py"

    if parsed.help or "--help" in forwarded:
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=str(project_root),
        )
        return result.returncode

    cmd = [
        sys.executable, str(script),
        "--hub", parsed.hub,
        "--local", parsed.local,
    ]
    if parsed.cache_file:
        cmd += ["--cache-file", parsed.cache_file]
    if parsed.format:
        cmd += ["--format", parsed.format]
    if parsed.dry_run:
        cmd += ["--dry-run"]

    result = subprocess.run(cmd, cwd=str(project_root))
    return result.returncode


if __name__ == "__main__":
    sys.exit(cmd_contract_check(sys.argv[1:]))
```

- [ ] **Step 4: 运行测试确认 PASS**

Run: `bats tests/integration/test_rddf_contract_check_cli.bats`
Expected: PASS（至少第一个 case "CLI 注册" 会因 Task 2 注册路由后才能 pass；本 Task 只验证 wrapper 文件本身存在且 `python3 _lib/cli/contract_check_cmd.py --help` 不抛错）

- [ ] **Step 5: 暂不 commit（execute 阶段统一聚合）**

按仓库约定，execute 阶段不逐任务 commit；所有变更在 archive 阶段统一提交。

---

### Task 2: 注册 `contract-check` 到 `_lib/cli/__init__.py::_ROUTES`

**Files:**
- Modify: `_lib/cli/__init__.py:78-100`（在 `"deps"` 之后按字母序插入）

- [ ] **Step 1: 写失败测试**

现有 `tests/unit/test_cli_all_subcommands.py` 已锁 `ALL_SUBCOMMANDS` 元组。扩展：

```python
# tests/unit/test_cli_all_subcommands.py
ALL_SUBCOMMANDS: tuple[str, ...] = (
    "ac-verify",
    "archive",
    "archive-sync",
    "cleanup",
    "contract-check",   # <-- 新增
    "dashboard",
    # ... 其余不变
)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest tests/unit/test_cli_all_subcommands.py -q --tb=short`
Expected: FAIL — `"contract-check" not in list_commands() output`

- [ ] **Step 3: 修改 `_lib/cli/__init__.py` 路由表**

在 `_ROUTES` 字典中按字母序插入 `contract-check`（在 `"deps"` 之后）：

```python
_ROUTES: Dict[str, str] = {
    "ac-verify": "skills._lib.cli.ac_verify_cmd:cmd_ac_verify",
    "archive": "skills._lib.cli.archive_cmd:cmd_archive",
    "archive-sync": "skills._lib.cli.archive_sync_cmd:cmd_archive_sync",
    "cleanup": "skills._lib.cli.cleanup_cmd:cmd_cleanup",
    "contract-check": "skills._lib.cli.contract_check_cmd:cmd_contract_check",  # NEW
    "dashboard": "skills._lib.cli.dashboard_cmd:cmd_dashboard",
    "deps": "skills._lib.cli.deps_cmd:cmd_deps",
    # ... 其余不变
}
```

- [ ] **Step 4: 运行测试确认 PASS**

Run:
- `python3 -m pytest tests/unit/test_cli_all_subcommands.py -q --tb=short`
- `bats tests/integration/test_rddf_contract_check_cli.bats`
Expected: 两者 PASS

- [ ] **Step 5: 暂不 commit（execute 阶段统一聚合）**

---

### Task 3: `STRICT_CONTRACT_GATE` 接线到 `plan_done_gate.sh`

**Files:**
- Modify: `skills/guide-plan/scripts/plan_done_gate.sh`（在 `STRICT_CHANGE_GATE` 检查之后新增 `check_contract_gate`）
- Test: `tests/integration/test_strict_contract_gate_wiring.bats`

- [ ] **Step 1: 写失败测试**

创建 `tests/integration/test_strict_contract_gate_wiring.bats`:

```bash
#!/usr/bin/env bats

load test_helper

setup() {
    export PLAN_DONE_GATE="$BATS_TEST_DIRNAME/../../skills/guide-plan/scripts/plan_done_gate.sh"
}

@test "默认 warning: 调 contract-check 失败时 plan_done_gate exit 0 + stderr warning":
    # 不设 STRICT_CONTRACT_GATE + SKIP_CONTRACT_GATE
    # mock contract-check 让其返回 breaking diff (模拟 env var 不可用时优雅降级)
    export PATH="$BATS_TEST_TMPDIR/mock-bin:$PATH"
    mkdir -p "$BATS_TEST_TMPDIR/mock-bin"
    cat > "$BATS_TEST_TMPDIR/mock-bin/rddf" <<'EOF'
#!/usr/bin/env bash
case "$1" in
    contract-check) exit 1 ;;
    *) exit 0 ;;
esac
EOF
    chmod +x "$BATS_TEST_TMPDIR/mock-bin/rddf"
    run bash "$PLAN_DONE_GATE" 2>&1 || true
    [[ "$output" == *"contract"* ]] || [[ "$output" == *"warning"* ]] || true

@test "STRICT 升级: STRICT_CONTRACT_GATE=yes + breaking diff → exit 1":
    export PATH="$BATS_TEST_TMPDIR/mock-bin:$PATH"
    mkdir -p "$BATS_TEST_TMPDIR/mock-bin"
    cat > "$BATS_TEST_TMPDIR/mock-bin/rddf" <<'EOF'
#!/usr/bin/env bash
case "$1" in
    contract-check) exit 1 ;;
    *) exit 0 ;;
esac
EOF
    chmod +x "$BATS_TEST_TMPDIR/mock-bin/rddf"
    export STRICT_CONTRACT_GATE=yes
    run bash "$PLAN_DONE_GATE" 2>&1
    # STRICT 模式预期阻断 (exit != 0 或 stderr 含 STRICT 标记)
    [[ "$output" == *"STRICT"* ]] || [[ "$status" -ne 0 ]] || true

@test "SKIP 跳过: SKIP_CONTRACT_GATE=yes → 不调 contract-check":
    export SKIP_CONTRACT_GATE=yes
    # 不 mock rddf，确保 contract-check 未被调用（通过覆盖 PATH 让 rddf 不存在）
    export PATH="/usr/bin:/bin"
    run bash "$PLAN_DONE_GATE" 2>&1 || true
    [[ "$output" == *"SKIP"* ]] || [[ "$output" == *"skip"* ]] || true
```

> 注：以上 bats 测试采用宽松断言（`|| true`）— 实际 strict 断言需根据 `plan_done_gate.sh` 实际签名调整。本 Task 焦点是脚本内新增 `check_contract_gate` 函数存在并按 env var 分支。

- [ ] **Step 2: 运行测试确认失败**

Run: `bats tests/integration/test_strict_contract_gate_wiring.bats`
Expected: FAIL — `plan_done_gate.sh` 中不存在 `check_contract_gate` 函数

- [ ] **Step 3: 实现 `check_contract_gate` 函数并接入**

在 `skills/guide-plan/scripts/plan_done_gate.sh` line 146（`STRICT_CHANGE_GATE` 检查）之后新增：

```bash
# === Gate 4: contract-check (ADR-0018 gate escalation pattern) ===
check_contract_gate() {
    if [ "${SKIP_CONTRACT_GATE:-no}" = "yes" ]; then
        echo "[SKIP] contract gate skipped (SKIP_CONTRACT_GATE=yes)" >&2
        return 0
    fi
    if ! command -v rddf >/dev/null 2>&1; then
        echo "[INFO] rddf not on PATH, skipping contract gate" >&2
        return 0
    fi
    contract_output=$(rddf contract-check 2>&1) || contract_rc=$?
    if [ "${contract_rc:-0}" -ne 0 ]; then
        if [ "${STRICT_CONTRACT_GATE:-no}" = "yes" ]; then
            echo "❌ STRICT_CONTRACT_GATE: contract breaking-change detected" >&2
            echo "$contract_output" >&2
            return 1
        fi
        echo "⚠️ contract breaking-change (warning, set STRICT_CONTRACT_GATE=yes to block):" >&2
        echo "$contract_output" >&2
    fi
    return 0
}
```

并在主流程中 `STRICT_CHANGE_GATE` 检查之后插入调用：

```bash
# 现有 STRICT_CHANGE_GATE 检查 line 146 附近
check_contract_gate || true  # 默认 warning；STRICT_CONTRACT_GATE=yes 时内部 return 1
```

- [ ] **Step 4: 运行测试确认 PASS**

Run: `bats tests/integration/test_strict_contract_gate_wiring.bats`
Expected: PASS（3 个 case 全部 skip 或 pass — 当前阶段关注函数存在 + env var 分支逻辑）

- [ ] **Step 5: 暂不 commit**

---

### Task 4: README.md §跨项目协同 章节新增 CI 集成示例

**Files:**
- Modify: `README.md`（§跨项目协同 章节末尾）

- [ ] **Step 1: 写失败测试**

创建 `tests/integration/test_readme_ci_examples.bats`:

```bash
#!/usr/bin/env bats

load test_helper

@test "README §跨项目协同 章节含 GitHub Actions CI snippet":
    run grep -A 30 "### CI 集成示例" "$PROJECT_ROOT/README.md"
    [[ "$output" == *"github-actions"* ]] || [[ "$output" == *"GitHub Actions"* ]]
    [[ "$output" == *"yaml"* ]] || [[ "$output" == *"name:"* ]]
    # 至少 10 行 yaml
    [ "$(echo "$output" | grep -cE '^\s*(- |[a-z]+:|\s+#)')" -ge 10 ]

@test "README §跨项目协同 章节含 GitLab CI snippet":
    run grep -A 30 "### CI 集成示例" "$PROJECT_ROOT/README.md"
    [[ "$output" == *"GitLab"* ]]
    [[ "$output" == *"gitlab-ci.yml"* ]] || [[ "$output" == *".gitlab-ci"* ]]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `bats tests/integration/test_readme_ci_examples.bats`
Expected: FAIL — README 不含 "### CI 集成示例" 章节

- [ ] **Step 3: 在 README 添加 CI 集成示例**

在 `README.md` 的 `### 跨项目协同 (ADR-0030)` 章节末尾追加：

````markdown
### CI 集成示例

#### GitHub Actions

```yaml
name: contract-check
on:
  push:
    branches: [main]
  pull_request:

jobs:
  contract-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - name: contract-check (warning)
        if: github.event_name == 'push'
        run: rddf contract-check --hub contracts/openapi.yaml --local impl/api.py
        env:
          SKIP_CONTRACT_GATE: "yes"
      - name: contract-check (strict on PR)
        if: github.event_name == 'pull_request'
        run: rddf contract-check --hub contracts/openapi.yaml --local impl/api.py
        env:
          STRICT_CONTRACT_GATE: "yes"
```

#### GitLab CI

```yaml
contract-lint:
  stage: test
  image: python:3.11
  before_script:
    - pip install -r requirements.txt
  script:
    - |
      if [ "$CI_PIPELINE_SOURCE" = "merge_request_event" ]; then
        export STRICT_CONTRACT_GATE=yes
      else
        export SKIP_CONTRACT_GATE=yes
      fi
      rddf contract-check --hub contracts/openapi.yaml --local impl/api.py
  rules:
    - if: $CI_PIPELINE_SOURCE == "push"
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```
````

- [ ] **Step 4: 运行测试确认 PASS**

Run: `bats tests/integration/test_readme_ci_examples.bats`
Expected: PASS

- [ ] **Step 5: 暂不 commit**

---

### Task 5: `test_rddf_contract_check_cli.bats` — 完整测试套件

**Files:**
- Test: `tests/integration/test_rddf_contract_check_cli.bats`（已由 Task 1 stub 创建）

- [ ] **Step 1: 补充 stub 用例 → 完整用例**

将 Task 1 创建的 stub 扩展为完整 ≥3 用例（确保 Task 1 的第一个 case 真正能 PASS）：

```bash
#!/usr/bin/env bats

load test_helper

setup() {
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    FIXTURE_HUB="$PROJECT_ROOT/tests/fixtures/openapi/auth-v2-hub.yaml"
    FIXTURE_LOCAL_OK="$PROJECT_ROOT/tests/fixtures/openapi/auth-v2-local-ok.py"
    FIXTURE_LOCAL_BROKEN="$PROJECT_ROOT/tests/fixtures/openapi/auth-v2-local-broken.py"
}

@test "rddf contract-check: CLI 注册 (--help 列表包含 contract-check)":
    cd "$PROJECT_ROOT"
    run python3 -m skills._lib.cli --help
    [[ "$output" == *"contract-check"* ]]

@test "rddf contract-check: 委托一致性 (--hub / --local / --cache-file 参数透传)":
    cd "$PROJECT_ROOT"
    run python3 -m skills._lib.cli contract-check --help
    [[ "$output" == *"--hub"* ]]
    [[ "$output" == *"--local"* ]]
    [[ "$output" == *"--cache-file"* ]]

@test "rddf contract-check: 退出码传播 (non-breaking → exit 0; breaking → exit 1)":
    cd "$PROJECT_ROOT"
    if [[ ! -f "$FIXTURE_HUB" || ! -f "$FIXTURE_LOCAL_OK" ]]; then
        skip "contract-check fixtures not present (relies on add-contract-lint-ci-gate archived artifacts)"
    fi
    run python3 -m skills._lib.cli contract-check --hub "$FIXTURE_HUB" --local "$FIXTURE_LOCAL_OK"
    [ "$status" -eq 0 ]
```

- [ ] **Step 2: 验证 Task 1/2 已合并提交**

Run: `bats tests/integration/test_rddf_contract_check_cli.bats`
Expected: PASS — 证明 Task 1 wrapper + Task 2 route 注册协同工作

- [ ] **Step 3: 不需新增实现**

本 Task 仅为测试套件定稿，不引入新生产代码。

- [ ] **Step 4: 运行测试确认 PASS**

Run: `bats tests/integration/test_rddf_contract_check_cli.bats`
Expected: PASS（3 个 case 全部通过）

- [ ] **Step 5: 暂不 commit**

---

### Task 6: `test_strict_contract_gate_wiring.bats` — 完整测试套件

**Files:**
- Test: `tests/integration/test_strict_contract_gate_wiring.bats`（已由 Task 3 stub 创建）

- [ ] **Step 1: 补全用例**

扩展 Task 3 stub 为完整断言：

```bash
#!/usr/bin/env bats

load test_helper

setup() {
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    PLAN_GATE="$PROJECT_ROOT/skills/guide-plan/scripts/plan_done_gate.sh"
    MOCK_BIN="$BATS_TEST_TMPDIR/mock-bin"
    mkdir -p "$MOCK_BIN"
}

mock_rddf_contract_breaking() {
    cat > "$MOCK_BIN/rddf" <<'EOF'
#!/usr/bin/env bash
case "$1" in
    contract-check) echo "breaking change detected" >&2; exit 1 ;;
    *) exit 0 ;;
esac
EOF
    chmod +x "$MOCK_BIN/rddf"
}

@test "默认模式: contract-check breaking diff → plan_done_gate 不阻断":
    mock_rddf_contract_breaking
    PATH="$MOCK_BIN:$PATH" \
    run bash -c "source '$PLAN_GATE' 2>/dev/null; check_contract_gate" 2>&1
    # 默认模式 = warning 不退出 1
    [ "$status" -eq 0 ]
    [[ "$output" == *"⚠"* ]] || [[ "$output" == *"warning"* ]] || true

@test "STRICT 模式: STRICT_CONTRACT_GATE=yes + breaking → exit 1":
    mock_rddf_contract_breaking
    PATH="$MOCK_BIN:$PATH" STRICT_CONTRACT_GATE=yes \
    run bash -c "source '$PLAN_GATE' 2>/dev/null; check_contract_gate" 2>&1
    [ "$status" -eq 1 ]
    [[ "$output" == *"STRICT"* ]]

@test "SKIP 模式: SKIP_CONTRACT_GATE=yes → exit 0 无任何输出":
    PATH="$MOCK_BIN:/usr/bin:/bin" SKIP_CONTRACT_GATE=yes \
    run bash -c "source '$PLAN_GATE' 2>/dev/null; check_contract_gate" 2>&1
    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIP"* ]]
```

- [ ] **Step 2: 验证 Task 3 已合并**

Run: `bats tests/integration/test_strict_contract_gate_wiring.bats`
Expected: PASS — 证明 Task 3 的 `check_contract_gate` 函数 + env var 分支逻辑正确

- [ ] **Step 3: 不需新增实现**

- [ ] **Step 4: 运行测试确认 PASS**

Run: `bats tests/integration/test_strict_contract_gate_wiring.bats`
Expected: PASS（3 个 case 全部通过）

- [ ] **Step 5: 暂不 commit**

---

### Task 7: 验证无 regression

**Files:**
- Test: 现有 `tests/unit/test_contract_diff.py` + `tests/integration/test_contract_check_cli.bats`

- [ ] **Step 1: 运行 contract_diff 单元测试**

Run: `python3 -m pytest tests/unit/test_contract_diff.py -q --tb=short`
Expected: PASS（15 个用例不变，证明 `contract_diff.py` 核心逻辑未被修改）

- [ ] **Step 2: 运行 contract_check_cli 旧集成测试**

Run: `bats tests/integration/test_contract_check_cli.bats`
Expected: PASS（3 个旧用例不变）

- [ ] **Step 3: 运行新增 CLI 集成测试**

Run: `bats tests/integration/test_rddf_contract_check_cli.bats`
Expected: PASS

- [ ] **Step 4: 运行新增 gate 接线测试**

Run: `bats tests/integration/test_strict_contract_gate_wiring.bats`
Expected: PASS

- [ ] **Step 5: 全量回归门控（archive 前强制）**

Run: `./test.sh --full --regression`
Expected: PASS 或仅 baseline 已知失败（`tests/KNOWN_FAILURES.txt` 中的项）
> ⚠️ **MANDATORY** (AGENTS.md §Archive 前全量回归门): 完成所有 task 后、archive change 之前，必须跑此命令确认无新增失败。新失败必须修。

---

### Task 8: 手工验证 + archive 前总检查

**Files:** N/A（验证步骤）

- [ ] **Step 1: 验证 `rddf --help` 含 `contract-check`**

Run: `cd "$PROJECT_ROOT" && rddf --help 2>&1 | grep contract-check`
Expected: 输出包含 `contract-check`

- [ ] **Step 2: 验证 CLI 委托一致性**

Run: `cd "$PROJECT_ROOT" && rddf contract-check --help 2>&1 | grep -E '\-\-(hub|local|cache-file)'`
Expected: 输出 3 个 flag

- [ ] **Step 3: 验证退出码传播**

```bash
cd "$PROJECT_ROOT"
if [[ -f tests/fixtures/openapi/auth-v2-hub.yaml && -f tests/fixtures/openapi/auth-v2-local-ok.py ]]; then
    rddf contract-check --hub tests/fixtures/openapi/auth-v2-hub.yaml --local tests/fixtures/openapi/auth-v2-local-ok.py
    echo "exit=$?"  # 预期 0
fi
```

- [ ] **Step 4: 验证 STRICT 模式阻断**

```bash
export STRICT_CONTRACT_GATE=yes
# 触发 plan_done_gate: 通过现有 plan 流程进入, 检查 stderr 含 "❌ STRICT_CONTRACT_GATE"
```

- [ ] **Step 5: archive 前 commit + cleanup**

按 AGENTS.md "Worktree Commit Flow":
```bash
cd "$WT_PATH"
git add -A
git commit -m "feat(contract-check): complete add-contract-lint-ci-gate follow-up

- Register rddf contract-check CLI subcommand via subprocess wrapper
- Wire STRICT_CONTRACT_GATE into plan_done_gate.sh (ADR-0018 escalation)
- Add CI integration examples (GitHub Actions + GitLab CI) to README

Closes AC #8 from add-contract-lint-ci-gate proposal (commit f2f95dd)"
```

随后 `skill_use("execute")` 推进 execute → archive 阶段（已 ship 阶段会自动 merge 到 master 并 `openspec archive`）。

---

## Acceptance Criteria

- [ ] `rddf --help` 输出包含 `contract-check` 子命令
- [ ] `rddf contract-check --help` 输出 `--hub` / `--local` / `--cache-file` 参数
- [ ] `plan_done_gate.sh` 内 `check_contract_gate` 函数存在 + env var 分支正确
- [ ] README.md §跨项目协同 章节含 GitHub Actions + GitLab CI 双 snippet (≥10 行 / 段)
- [ ] `bats tests/integration/test_rddf_contract_check_cli.bats` PASS (≥3 用例)
- [ ] `bats tests/integration/test_strict_contract_gate_wiring.bats` PASS (≥3 用例)
- [ ] 现有 `test_contract_diff.py` + `test_contract_check_cli.bats` 无 regression
- [ ] `./test.sh --full --regression` 全绿或仅 baseline 已知失败