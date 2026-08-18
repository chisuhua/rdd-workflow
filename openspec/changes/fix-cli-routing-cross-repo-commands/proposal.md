# fix-cli-routing-cross-repo-commands

## Why

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

## What Changes

**In Scope**:

- **注册 `rddf sync-hub`**: `_lib/cli/__init__.py::_ROUTES` 追加 entry, 调用 `sync_hub.main(argv)`
- **注册 `rddf watch-hub`**: 同上, 调用 `watch_hub.main(argv)`
- **注册 `rddf deps cross-repo`**: 升级 `skills/deps/scripts/deps_cmd.py::main()`, 增加 argparse `--cross-repo` 子路由分发（含 `--spokes` 参数）
- **bats 集成测试**: `tests/integration/test_rddf_cli_routing.bats` 覆盖 3 个命令（rddf sync-hub / rddf watch-hub / rddf deps cross-repo）
- **单元测试**: `tests/unit/test_deps_cmd.py` 新增 cross-repo 子路由 3 个 case
- **README 同步**: 在 README §跨项目协同 章节由 `python3 skills/sync-hub/scripts/sync_hub.py` 改为 `rddf sync-hub`

### 关键场景

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

**Out of Scope**:

- **不修改** 3 个命令的业务逻辑（仅注册, 调用既有 main 实现）
- **不修改** 已注册 22 个命令的路由
- **不实现** 长驻 daemon（`rddf watch-hub` 仍为一次性轮询, 调度由 CI/cron 负责）
- **不创建** 新的 env var（沿用既有 `RDDF_HUB_REPO` / `RDDF_SYNC_HUB_INTERVAL` 等）

## Capabilities

- **路由样板**: 复用 `contract_check_cmd.py` 注册模式（已通过 `complete-add-contract-lint-ci-gate` 验证）
- **参数透传**: 子命令 `--contract` / `--hub-issue` / `--spokes` 等原样透传到 `main()`
- **env var 兼容**: `RDDF_HUB_REPO` 等既有 env var 不变, 仅增加路由
- **错误信息**: unknown command 错误信息保持一致（开发体验不退化）
- **CI 兼容**: bats 测试在 `BATS_TMPDIR` 创建临时 git 仓库模拟 Hub
- **Schema 不变**: `--spokes` 参数解析为逗号分隔的 `org/repo` 列表
- **既有回归**: `tests/unit/test_deps_cmd.py` 既有 case 必须继续通过

## Impact

- (no items specified)

## Acceptance

- [ ] `_lib/cli/__init__.py::_ROUTES` 新增 3 条 entry（sync-hub / watch-hub / deps.cross-repo）
- [ ] `tests/integration/test_rddf_cli_routing.bats` 新增, 3 个 case 全绿
- [ ] `tests/unit/test_deps_cmd.py` 新增 cross-repo 路由分发 3 个 case
- [ ] 实跑 `rddf sync-hub --help` 返回帮助（不再是 "unknown command"）
- [ ] 实跑 `rddf watch-hub --help` 返回帮助
- [ ] 实跑 `rddf deps cross-repo --help` 返回帮助
- [ ] **既有回归**: `tests/integration/test_cli_routing.bats` 既有 22 个命令 case 全绿
- [ ] **既有回归**: `tests/unit/test_deps_cmd.py` 全绿
- [ ] **既有回归**: `./test.sh --full --regression` 通过
- [ ] **README 同步**: README §跨项目协同 章节示例命令更新为 `rddf sync-hub` / `rddf watch-hub` / `rddf deps cross-repo`
- [ ] **GitHub Actions 同步**: `.github/workflows/contract-check.yml` 若引用旧命令路径需更新

