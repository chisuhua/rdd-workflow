## Context

**背景**

Oracle 2026-08-18 审查 ADR-0030 发现: README + spec 文档化为 MUST 级 CLI 命令的 3 个 cross-repo 子命令, 在 `_lib/cli/__init__.py::_ROUTES`（22 个命令）**未注册**, 实跑返回 "❌ unknown command" exit 2。当前仅 `python3 skills/<name>/scripts/<name>.py` 脚本入口可用。

**已修先例**

`complete-add-contract-lint-ci-gate` change 为 `rddf contract-check` 完成同款修复（注册子命令 + 调整 routing）。本 change 复用相同模式补齐剩余 3 个命令。

**3 个未注册 CLI 子命令**

1. **`rddf sync-hub`** — 拉取 Hub 契约到本地 `openspec/specs/<name>/spec.md`
   - 实现存在: `skills/sync-hub/scripts/sync_hub.py` + bats 测试
   - 路由缺失: `_lib/cli/__init__.py` 无 entry

2. **`rddf watch-hub`** — 一次性轮询 Hub Issue 状态 (cron/CI 调度)
   - 实现存在: `skills/watch-hub/scripts/watch_hub.py` + bats 测试
   - 路由缺失: 同上

3. **`rddf deps cross-repo`** — 跨仓库依赖图分析
   - 实现存在: `skills/deps/scripts/deps_cmd.py` 已包含 handler 函数
   - 但 `deps_cmd.py` 完全**未注册** cross-repo 子路由分发, 需补 argparse 子命令路由

**已有机制（注册而非重写）**

- `skills/_lib/cli/__init__.py::_ROUTES` 注册表（参考 `contract_check_cmd.py` 注册样板）
- `bash install.sh` 已创建 `~/.local/bin/rddf` CLI 入口
- 22 个已注册命令的路由约定

## Goals / Non-Goals

**Goals:**

**In Scope**:

- **注册 `rddf sync-hub`**: `_lib/cli/__init__.py::_ROUTES` 追加 entry, 调用 `sync_hub.main(argv)`
- **注册 `rddf watch-hub`**: 同上, 调用 `watch_hub.main(argv)`
- **注册 `rddf deps cross-repo`**: 升级 `skills/deps/scripts/deps_cmd.py::main()`, 增加 argparse `--cross-repo` 子路由分发（含 `--spokes` 参数）
- **bats 集成测试**: `tests/integration/test_rddf_cli_routing.bats` 覆盖 3 个命令（rddf sync-hub / rddf watch-hub / rddf deps cross-repo）
- **单元测试**: `tests/unit/test_deps_cmd.py` 新增 cross-repo 子路由 3 个 case
- **README 同步**: 在 README §跨项目协同 章节由 `python3 skills/sync-hub/scripts/sync_hub.py` 改为 `rddf sync-hub`

**Non-Goals:**

**Out Scope**:

- **不修改** 3 个命令的业务逻辑（仅注册, 调用既有 main 实现）
- **不修改** 已注册 22 个命令的路由
- **不实现** 长驻 daemon（`rddf watch-hub` 仍为一次性轮询, 调度由 CI/cron 负责）
- **不创建** 新的 env var（沿用既有 `RDDF_HUB_REPO` / `RDDF_SYNC_HUB_INTERVAL` 等）

## Decisions

### Decision 1: Approach from proposal 关键场景

The proposal's 5 key scenarios drive the implementation:

### 场景 1 — `rddf sync-hub` 注册

```bash
# 修复前
$ rddf sync-hub --contract auth-v2.yaml
# ❌ unknown command: sync-hub
#    exit code: 2

# 修复后
$ RDDF_HUB_REPO=org/rdd-hub rddf sync-hub --contract auth-v2.yaml
# ✅ 从 org/rdd-hub 拉取 contracts/auth-v2.yaml 到 openspec/specs/auth-v2/spec.md
#    exit code: 0
```

### 场景 2 — `rddf watch-hub` 注册

```bash
# 修复前
$ rddf watch-hub --once --owner=org/rdd-hub
# ❌ unknown command: watch-hub

# 修复后
$ RDDF_HUB_REPO=org/rdd-hub rddf watch-hub --once --owner=org/rdd-hub
# ✅ 一次性轮询 Hub Issue 状态, 输出变更摘要
#    exit code: 0/1（取决于是否有变更）
```

### 场景 3 — `rddf deps cross-repo` 注册

```bash
# 修复前
$ rddf deps cross-repo --spokes org/foo,org/bar,org/baz
# ❌ unknown command: cross-repo

# 修复后
$ rddf deps cross-repo --spokes org/foo,org/bar,org/baz
# ✅ 输出 Mermaid 跨仓库依赖图 + 推荐执行顺序（wave-based）
#    exit code: 0
```

### 场景 4 — 路由集成测试

```bash
$ bats tests/integration/test_rddf_cli_routing.bats
# ✅ 3 个 test:
#    1. rddf sync-hub exists → exit 0 + 输出拉取报告
#    2. rddf watch-hub exists → exit 0 + 输出变更摘要
#    3. rddf deps cross-repo exists → exit 0 + 输出 Mermaid
```

### Decision 2: Technical Constraints Adherence

1. **路由样板**: 复用 `contract_check_cmd.py` 注册模式（已通过 `complete-add-contract-lint-ci-gate` 验证）
2. **参数透传**: 子命令 `--contract` / `--hub-issue` / `--spokes` 等原样透传到 `main()`
3. **env var 兼容**: `RDDF_HUB_REPO` 等既有 env var 不变, 仅增加路由
4. **错误信息**: unknown command 错误信息保持一致（开发体验不退化）
5. **CI 兼容**: bats 测试在 `BATS_TMPDIR` 创建临时 git 仓库模拟 Hub
6. **Schema 不变**: `--spokes` 参数解析为逗号分隔的 `org/repo` 列表
7. **既有回归**: `tests/unit/test_deps_cmd.py` 既有 case 必须继续通过

## Risks / Trade-offs

- **Test failure on existing approve_proposal.sh suite**: 既有 4 个 bats 测试 (`test_strict_human_approval.bats`) 必须保持通过,新增 ≥ 5 个 case 锁定新行为
- **CI 兼容性**: `read -s` 在非交互终端需 fallback (用 `RDDF_APPROVE_ACTOR` env var)
- **Audit log crash-safety**: `append_audit_log_entry` 必须在 accept 前同步写入, atomic_write 保证
- **Hub Issue re-fetch network error**: 区分 network (fail-open + warning) vs auth (fail-closed)
- **Schema backward compatibility**: iteration.json v7 字段添加但不破坏 v6 现有消费者 (字段缺省默认为空)

## References

- `.rddf/improvements/fix-cli-routing-cross-repo-commands.md` — 完整 5 段 proposal
- `openspec/changes/fix-cli-routing-cross-repo-commands/proposal.md` — 落盘的完整 proposal
- ADR-0030 / ADR-0031 — Hub-and-Spoke 联邦架构 + 跨项目 RFC 人类决策
