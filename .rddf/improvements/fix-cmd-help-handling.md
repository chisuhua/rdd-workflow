---
优先级: P1
来源: 2026-09-25 rdd-verifier re-verify audit of rdd-workflow-e2e (PR #1 merge) — CI 报
  `test 6 (archive/cleanup/build --help)` 新增失败,实际暴露 2 个主仓 CLI handler 的 `--help`
  处理 bug:`rddf contract-check --help` 返回 EXIT=2 (argparse 自动 exit 被自定义 store_true 覆盖),
  `rddf archive-sync --help` 把 `--help` 当 change name 查找 iteration.json (EXIT=1)
阶段: v4.1 follow-up
分类: bug-fix
类型: fix
主题: 跨项目 CLI 契约一致性
依赖: 任何使用 `rddf --help` 的脚本（含 CI / 第三方集成）
---

**优先级**: P1 | **来源**: 2026-09-25 cross-repo e2e CI regression audit
**阶段**: v4.1 follow-up | **分类**: bug-fix
**类型**: fix | **主题**: 跨项目 CLI 契约一致性
**依赖**: rdd-workflow-e2e CI (PR #1 merged 2026-09-25), `bypass-audit-mechanism` (P2, deferred)

> **症状**: 多个 `rddf <subcommand> --help` 调用返回非零退出码，违反 argparse/argparse-style CLI 通用契约。CI 在 e2e 测试床捕获:
>
> | Subcommand | 期望 EXIT | 实际 EXIT | 行为 |
> |------------|-----------|-----------|------|
> | `rddf contract-check --help` | 0 | 2 | argparse "required args missing: --hub, --local" |
> | `rddf archive-sync --help` | 0 | 1 | "change '--help' not found in iteration.json" |
>
> **直接证据** (`rdd-workflow-e2e/tests/integration/test_rddf_cli_all_subcommands.bats::AC-6`):
> ```
> not ok 27 rddf archive/cleanup/build --help: returns usage info without running
> #   `return 1' failed
> # ❌ rddf contract-check: --help failed
> ```
>
> **根因 1（contract-check）**:`_lib/cli/contract_check_cmd.py:39-44`
> ```python
> parser.add_argument("--help", action="store_true", help="Show help")
> ```
> argparse **自动** 添加 `-h/--help` action=`help`(打印 usage + sys.exit(0))。但 handler 显式 override 为 `store_true`,argparse 检测到 conflict 后保留用户 override,**导致 `--help` 被当作普通 flag,触发 required args 校验,EXIT=2**。
>
> **根因 2（archive-sync）**:`_lib/cli/archive_sync_cmd.py:67`
> ```python
> if not args:
>     print("❌ archive-sync: no change names provided...")
>     return 2
> ```
> **完全无 `--help` 处理**:`--help` 直接进入业务路径当 change name 去查 iteration.json + archive dir,EXIT=1。

## 架构依据

rdd-workflow CLI 的 **API 契约** 是 argparse 风格（36 个子命令）。Python argparse 的 `--help` 标准语义是**打印 usage + EXIT 0**,所有用户/CI 都依赖这一约定。**2 个 handler 实现偏离**导致:

1. **CI 阻断**: rdd-workflow-e2e PR #1 的 `bats (Ubuntu 22.04)` job fail (虽然 PR net 改善 2 fails → 1 fail,GitHub `新增失败: 1` 报告机械判 fail)
3. **第三方集成脆性**: 任何写 `rddf <sub> --help && do_something` 的脚本会误触发业务逻辑
4. **用户困惑**:`rddf --help` 工作但 `rddf <sub> --help` 在某些 sub 不工作,违反最少惊讶原则

**修复策略选项**:

| 选项 | 改动范围 | 一致性 | 风险 |
|------|----------|--------|------|
| **A. 修 2 个 handler 单独加 `--help` 处理** | 2 文件 | 局部 | 低,scope 清晰 |
| **B. `_lib/cli/__init__.py::route()` 入口统一拦截 `--help`** | 1 文件 | 全局一致 | 中,需测所有 36 个 subcommand |
| **C. 替换 33 文件 `os.environ.get(...) or os.getcwd()` 反模式** (顺带发现,非本 bug 直接修复) | 33 文件 | 架构正确 | 高,scope creep; 拆为单独 improvement |

**推荐选项 B**: `_lib/cli/route()` 入口在分发到具体 handler 前先 print subcommand-specific usage + EXIT 0。这与 argparse 默认行为一致,handler 无需改动;同时为未来 36+ 个 subcommand 提供统一 help 处理,**消除整个类 bug 的可能性**。

## 范围

### In Scope
- `_lib/cli/__init__.py::route()` 入口加 `--help`/`-h` 探测 → print argparse usage (通过临时 ArgumentParser + add_help=True) + EXIT 0
- 若选项 B 测试覆盖率不足,fallback 到选项 A (修 2 个 handler)
- 加单元测试 `tests/unit/test_route_help_handling.py` 验证 36 个 subcommand `--help` 全 EXIT 0
- 更新 rdd-workflow-e2e `tests/KNOWN_FAILURES.txt` 移除 `archive/cleanup/build --help` (master 实测显示该 case 已 PASS;从 baseline 移除)

### Out of Scope
- ❌ 不改 rdd-workflow-e2e test 6 的 setup() (已在前置 PR #1 commit `efe89dd` 修复)
- ❌ 不改 `_lib/cli/__init__.py::route()` 的 dispatcher 逻辑(仅加 help short-circuit)
- ❌ 不修 33 文件 `RDDF_PROJECT_ROOT or os.getcwd()` 反模式(已识别为单独 improvement `fix-33-handlers-project-root-anti-pattern`)
- ❌ 不引入新依赖

## Why

`rddf <sub> --help` 应统一返回 EXIT 0 (argparse 风格标准契约)。CI、第三方脚本、用户文档生成器都依赖此行为。2 个 handler 偏离导致 CI fail + 用户困惑。

## What Changes

### 选项 B（推荐）— `_lib/cli/__init__.py::route()` 入口加 `--help` short-circuit

```python
# In _lib/cli/__init__.py::route()
def route(subcommand: str, args: list[str]) -> int:
    """..."""
    if subcommand not in _ROUTES:
        raise KeyError(subcommand)

    # NEW: --help / -h short-circuit at dispatch layer.
    # argparse's --help behavior (print usage + EXIT 0) is the canonical CLI
    # contract; some handlers (contract_check, archive_sync) override it
    # incorrectly. Intercepting here gives uniform behavior across all 36
    # subcommands without touching individual handler code.
    if args and args[0] in ("--help", "-h"):
        # Build a per-subcommand ArgumentParser that prints usage on --help.
        # We use argparse's built-in help machinery (add_help=True, default).
        # The handler's actual sub-parser isn't needed; just expose name + brief.
        import argparse
        epilog = _SUBCOMMAND_EPILOG.get(subcommand, "")
        parser = argparse.ArgumentParser(
            prog=f"rddf {subcommand}",
            description=_SUBCOMMAND_DESCRIPTION.get(subcommand, ""),
            epilog=epilog,
        )
        parser.add_argument("--help", action="help", default="==SUPPRESS==")
        # The above triggers argparse's default --help handler when --help
        # appears in args (prints usage to stdout/stderr + sys.exit(0)).
        try:
            parser.parse_args(args)
        except SystemExit as e:
            return int(e.code) if isinstance(e.code, int) else 0
        return 0  # Should be unreachable; --help triggers SystemExit.

    module_path, _, func_name = _ROUTES[subcommand].partition(":")
    # ... existing import + dispatch ...
```

#### `_SUBCOMMAND_DESCRIPTION` 数据

最小实现: 从 `_ROUTES[subcommand].module` 反射读取 module docstring + argparse parser description(若可获得)。Phase 1: 写 2 个 entry (`contract-check`, `archive-sync`) — 其他 subcommand 维持 argparse 默认行为 (已正确)。

#### 2 handler sync 修复 (选项 A fallback)

`_lib/cli/contract_check_cmd.py:39-44`:
```diff
- parser.add_argument("--help", action="store_true", help="Show help")
+ # REMOVE: argparse default --help handles this correctly
```

`_lib/cli/archive_sync_cmd.py:67-72` 加 help short-circuit:
```python
if args and args[0] in ("--help", "-h"):
    print("Usage: rddf archive-sync <name1> [name2 ...] [--all]")
    print("  Reconciles drift between openspec/changes/<name>/ and openspec/changes/archive/")
    return 0
```

## Acceptance

- [ ] `rddf contract-check --help` → EXIT 0 (现 EXIT 2)
- [ ] `rddf archive-sync --help` → EXIT 0 (现 EXIT 1)
- [ ] 现有 33 个 subcommand `--help` 行为不变 (回归门)
- [ ] rdd-workflow 主仓 `./test.sh --quick` 仍 2947+ passed
- [ ] rdd-workflow-e2e PR #1 + 本 fix 后 `bats (Ubuntu 22.04)` green (0 新增失败)
- [ ] `tests/KNOWN_FAILURES.txt` 移除 `rddf archive/cleanup/build --help` (master 实测显示 pass)
- [ ] 新增单元测试 `test_route_help_handling.py` 覆盖 36 个 subcommand

## Capabilities

### MUST
- `_lib/cli/__init__.py::route()` 统一处理 `--help`/`-h`,保证 EXIT 0
- 修复 `contract-check` 和 `archive-sync` 子命令的 `--help` 处理

### MUST NOT
- ❌ 不修改 handler 的业务逻辑 (只是 help 处理)
- ❌ 不引入新 CLI 解析库 (继续用 argparse)
- ❌ 不破坏现有 `rddf <sub> --help` 已 EXIT 0 的 34 个 subcommand

## Impact

| 维度 | 当前 | 修复后 |
|------|------|--------|
| rdd-workflow-e2e CI | 1 fail (test 6) | 0 fail |
| 第三方 CI 集成 | 脆性 (2/36 sub 有 bug) | 健壮 (0/36) |
| 用户 UX | `--help` 行为不一致 | 一致 argparse 风格 |
| 主仓代码改动 | — | 1-2 文件,~20-40 行 |
| 测试覆盖 | — | +1 unit file,~36 cases |

**后续 follow-up improvement 建议**:
- `fix-33-handlers-project-root-anti-pattern` (33 handler 用 `RDDF_PROJECT_ROOT or os.getcwd()` 反模式,应统一用 `__main__.resolve_project_root()`)
- `add-rddf-help-metadata-registry` (各 subcommand 添加 `_SUBCOMMAND_DESCRIPTION` 元数据,文档化 + `--help` 增强)