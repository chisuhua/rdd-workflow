# complete-add-cross-repo-deps-orchestration

## Why

- `add-cross-repo-deps-orchestration` 提案（已归档，commit `add4e2a`）声称完成跨仓库依赖编排实施。
- 实际审计发现 2 个 AC 未达成：
  1. **`STRICT_DEPS_GATE` 环境变量未在任何脚本中 read**（`docs/strict-gate-boundary.md:23` 提到该变量，但 `plan_done_gate.sh` / `_lib/dependency_scheduler.py` 均未读取，`rddf deps cross-repo` 也只静态分析不消费 env var）。
  2. **README §跨项目协同 章节缺跨仓库依赖示例**（提案 AC #7 要求"README §跨项目协同 章节增加跨仓库依赖示例"）。
- 已实现部分（无需重做）：`_lib/cross_repo_deps.py::kahn_topological_sort`、`cross_repo_deps_cache.py`、`cross_repo_deps_cache_schema.json` SSOT、`rddf deps cross-repo` CLI 子命令（10 changes 测试输出）、14 个单元测试 pass。

## What Changes

**In Scope**:

- 在 `skills/guide-plan/scripts/plan_done_gate.sh` 中 read `STRICT_DEPS_GATE=yes`，调 `rddf deps cross-repo --spokes <list>` 检查跨仓库变更依赖；存在跨仓库 blocker 时默认 warning，`STRICT_*` 升级 error。
- 给 `_lib/dependency_scheduler.py` 或新文件 `_lib/cross_repo_gate.py` 增加 `check_cross_repo_deps_blocked()` 函数，被 plan_done_gate 调用。
- 给 README §跨项目协同 章节增加跨仓库依赖示例（含输出格式、Mermaid 图、推荐顺序、strict 模式开关）。
- 新增 `tests/integration/test_strict_deps_gate_wiring.bats` 验证 env var 在 plan-done gate 中实际生效（≥3 用例）。
- 新增 `tests/unit/test_cross_repo_gate.py` 覆盖 `check_cross_repo_deps_blocked()` 5 个关键路径（无 blocker / 单 blocker / 跨仓库 chain / cycle-detect / cache-hit）。

### 关键场景

- GIVEN `STRICT_DEPS_GATE=yes` + plan 阶段活跃 changes 包含跨仓库 blocker（如 `add-cross-repo-state-schemas` 被 `add-mcp-cross-repo-protocol` block）, WHEN `plan_done_gate` 执行, THEN 调 `rddf deps cross-repo` 检测，发现 blocker → 升级 error 并阻断 plan-done。
- GIVEN 默认环境 + 同上跨仓库 blocker, WHEN `plan_done_gate` 执行, THEN 仅 warning 输出，plan-done 继续成功（与 `STRICT_CHANGE_GATE` 默认语义对齐）。
- GIVEN 用户阅读 README §跨项目协同 章节, WHEN 看到新增跨仓库依赖示例, THEN 看到示例输出（Mermaid 图 + 推荐顺序表格）+ `STRICT_DEPS_GATE` 启用方法。
- GIVEN `cross_repo_deps_cache.py` 缓存命中, WHEN `check_cross_repo_deps_blocked()` 调用, THEN 不重复执行 `kahn_topological_sort`，直接读 cache（避免每次 plan-done 阻塞性能）。

**Out of Scope**:

- 不修改 `cross_repo_deps.py::kahn_topological_sort`（已通过 14 测试）。
- 不实现 `rddf deps cross-repo --cache-version` 等新 CLI flag（仅补 env var 接线 + README 文档）。
- 不修改 `docs/strict-gate-boundary.md`（文档准确，代码缺失）。
- 不实现 Hub 端 `[Dependency]` Issue 自动创建（属 `add-rdd-hub-cross-repo-federation` 提案范围，本提案只补本地 gate）。

## Capabilities

- MUST 在 `plan_done_gate.sh` 实际 read `STRICT_DEPS_GATE` env var（参照 `STRICT_CHANGE_GATE` 已实现的 escalation pattern）。
- MUST 严格遵守 ADR-0018 gate escalation 模式：默认 warning、`STRICT_*=yes` 升级 error、`SKIP_*=yes` 跳过。
- MUST 利用 `cross_repo_deps_cache.py` 缓存机制（避免 plan-done 阶段重复拓扑排序）。
- SHOULD 让 README 示例能直接 `bash` 复制运行（含具体 change 名 + 期望输出）。
- SHOULD NOT 在本提案修改 docs/strict-gate-boundary.md（文档本身准确，只是代码缺失）。

## Impact

- MUST NOT 修改 `kahn_topological_sort` 算法本身（已测试覆盖）。

## Acceptance

- `tests/integration/test_strict_deps_gate_wiring.bats` 新增 ≥3 用例：默认 warning / `STRICT_DEPS_GATE=yes` error / `SKIP_DEPS_GATE=yes` skip 全部 pass。
- `tests/unit/test_cross_repo_gate.py` 新增 5 个测试用例（无 blocker / 单 blocker / 跨仓库 chain / cycle-detect / cache-hit）全部 pass。
- README.md §跨项目协同 章节末尾新增 `### 跨仓库依赖示例` 子节，含 `rddf deps cross-repo --spokes X,Y` 命令 + Mermaid 图 + 推荐顺序表格 + `STRICT_DEPS_GATE` 启用示例（≥15 行）。
- 现有 `tests/unit/test_cross_repo_deps.py` 14 个测试保持 pass（无 regression）。
- 手工验证：设置 `STRICT_DEPS_GATE=yes` 后跑 `guide-plan` plan-done 阶段，遇到跨仓库 blocker 时退出码非零；未设置时退出码 0。

