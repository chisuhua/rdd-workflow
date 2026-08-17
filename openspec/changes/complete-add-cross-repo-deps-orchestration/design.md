# complete-add-cross-repo-deps-orchestration — Design

> Schema: spec-driven
> See: `proposal.md` for motivation, scope and acceptance criteria.

## Context

`add-cross-repo-deps-orchestration` 提案(已归档,commit `add4e2a`)声称完成跨仓库依赖编排实施。审计发现 2 个 AC 未达成:

1. **`STRICT_DEPS_GATE` 环境变量未在任何脚本中 read**(`docs/strict-gate-boundary.md:23` 提到该变量,但 `skills/guide-plan/scripts/plan_done_gate.sh` 和 `skills/_lib/cross_repo_deps.py` 均未读取,`rddf deps cross-repo` 也只静态分析不消费 env var)
2. **README §跨项目协同 章节缺跨仓库依赖示例**(提案 AC #7 要求"README §跨项目协同 章节增加跨仓库依赖示例")

已实现部分(无需重做):

- `skills/_lib/cross_repo_deps.py::kahn_topological_sort`(line 67)
- `skills/_lib/cross_repo_deps_cache.py` 24h TTL JSON 缓存
- `cross_repo_deps_cache_schema.json` SSOT
- `rddf deps cross-repo` CLI 子命令(实测对 10 changes 输出依赖图)
- 14 个单元测试 pass(`tests/unit/test_cross_repo_deps.py`)

本提案补齐 env var 接线 + README 示例 + 新增 `check_cross_repo_deps_blocked()` gate 函数。

## Goals / Non-Goals

**Goals:**

- 在 `skills/guide-plan/scripts/plan_done_gate.sh` 实际 read `STRICT_DEPS_GATE=yes`,调 `rddf deps cross-repo --spokes <list>` 检测跨仓库变更依赖
- 给 `_lib/cross_repo_gate.py` 新增 `check_cross_repo_deps_blocked()` 函数(避免污染 `cross_repo_deps.py` 主逻辑)
- 严格遵循 ADR-0018 gate escalation:默认 warning、`STRICT_*=yes` 升级 error、`SKIP_*=yes` 跳过
- 利用 `cross_repo_deps_cache.py` 缓存机制(避免 plan-done 阶段重复拓扑排序)
- README §跨项目协同 章节末尾新增 `### 跨仓库依赖示例` 子节(Mermaid 图 + 推荐顺序表格 + STRICT 启用方法)
- 新增 `tests/integration/test_strict_deps_gate_wiring.bats` (≥3 用例)
- 新增 `tests/unit/test_cross_repo_gate.py` (5 个关键路径)

**Non-Goals:**

- 不修改 `cross_repo_deps.py::kahn_topological_sort`(已通过 14 测试)
- 不实现 `rddf deps cross-repo --cache-version` 等新 CLI flag(仅补 env var 接线 + README 文档)
- 不修改 `docs/strict-gate-boundary.md`(文档准确,代码缺失)
- 不实现 Hub 端 `[Dependency]` Issue 自动创建(属 `add-rddf-hub-cross-repo-federation` 提案范围,本提案只补本地 gate)
- 不实现跨仓库 cache TTL 调整(24h TTL 已合理)

## Decisions

### 1. 新文件 `_lib/cross_repo_gate.py` 而非修改 `cross_repo_deps.py`

`check_cross_repo_deps_blocked()` 是 gate 逻辑(consume env var, output warning/error),与 `cross_repo_deps.py` 的纯算法逻辑(`kahn_topological_sort`)职责不同。新文件避免污染纯算法模块,便于独立测试和未来扩展。

**Alternatives considered:**

- 直接在 `cross_repo_deps.py` 加 `check_cross_repo_deps_blocked()` 函数:模块职责模糊(纯算法 vs gate 副作用) — 被否。
- 集成到 `plan_done_gate.sh` 内联 bash:失去 Python 单元测试覆盖能力,需 mock `subprocess.run` — 被否。

### 2. plan_done_gate.sh 接线位置

放在 `STRICT_CONTRACT_GATE` 检查(`complete-add-contract-lint-ci-gate` 提案新增,同一文件)之后,作为 gate 5。便于 cross-repo gate 集中管理:

- gate 3: `STRICT_CHANGE_GATE`(run_plan_checks + change_alignment)
- gate 4: `STRICT_CONTRACT_GATE`(rddf contract-check,本提案关联)
- gate 5: `STRICT_DEPS_GATE`(本提案)

**Alternatives considered:**

- 放在 gate 3 之前:`STRICT_CHANGE_GATE` 是核心质量检查,应优先;cross-repo gate 是次级 — 被否。
- 单独抽取 `cross_repo_deps_gate.sh` bash 文件:增加文件数量,与 gate 3/4 风格不一致 — 被否。

### 3. 缓存机制利用策略

`check_cross_repo_deps_blocked()` 调用 `cross_repo_deps_cache.load_cache(project_root, spokes_key)` 先查 24h 缓存。命中直接返回 cache 中已分析的 blocker 列表;未命中才调 `kahn_topological_sort`。

**Alternatives considered:**

- 每次 plan-done 都重算(不查 cache):浪费拓扑排序时间(< 100ms 但累积明显) — 被否。
- 永久 cache(无 TTL):Spoke 端 iteration.json 变化后本地过期,无法检测 — 被否。

### 4. blocker 判定标准

对每个 active change 的 `iteration.json` 的 `blocker` 字段,若包含跨仓库项目(从 Spoke iteration.json 的 `cross_repo_blockers` 派生),视为有跨仓库 blocker。

**Alternatives considered:**

- 所有 `blocker` 字段非空都视为 blocker(本地 + 跨仓库):粒度过粗,本提案只补跨仓库缺失 — 被否。
- 仅当 `blocker` 含 `repo:` 前缀(如 `repo:org/foo#5`)判定为跨仓库:依赖人工标注,易遗漏 — 被否。

### 5. README 示例覆盖 4 个要素

跨仓库依赖示例需包含:

1. `rddf deps cross-repo --spokes X,Y` 命令
2. Mermaid 图(独立 change 用 `subgraph`, 依赖用 `-->`, 冲突用 `-.->|冲突|`)
3. 推荐顺序表格(name / status / parallel_group / blocker)
4. `STRICT_DEPS_GATE=yes` 启用方法(env var + 触发场景)

**Alternatives considered:**

- 仅 Mermaid 图:用户不知如何重现命令 — 被否。
- 仅命令 + 输出,无 Mermaid:可视化不足,与 `rddf deps cross-repo` 默认输出无差异 — 被否。

### 6. test_cross_repo_gate.py 5 个关键路径

1. **无 blocker**: mock `cross_repo_deps_cache.load_cache` 返回无 blocker → `check_cross_repo_deps_blocked()` 返回 `[]`
2. **单 blocker**: mock 单 change `blocker="org/foo"` → 返回 `["change1: blocked by org/foo"]`
3. **跨仓库 chain**: mock 3 change 跨仓库依赖链 A→B→C → 返回所有 chain 节点
4. **cycle-detect**: mock 循环依赖 A↔B → 返回 cycle 警告 + cycle 路径
5. **cache-hit**: 第一次调用 → 调 `kahn_topological_sort` + 写 cache;第二次调用 → 命中 cache,不重算

### 7. test_strict_deps_gate_wiring.bats ≥3 用例

1. 默认 warning: mock 跨仓库 blocker + 无 `STRICT_DEPS_GATE` → `plan_done_gate` exit 0 + stderr warning
2. STRICT 升级: `STRICT_DEPS_GATE=yes` + blocker → exit 1 + stderr "❌ STRICT_DEPS_GATE"
3. SKIP 跳过: `SKIP_DEPS_GATE=yes` + blocker → exit 0,无任何输出

## Risks / Trade-offs

- **缓存过期风险**: 24h TTL 期间 Spoke 端 iteration.json 变化后本地过期。但缓存失效仅意味着下一次 plan-done 重算(< 100ms 开销),不影响正确性。**Mitigation**: 缓存键包含 `spokes_key`(spoke repo URL 列表),spoke 列表变化时自动失效。
- **跨仓库依赖与本地依赖混淆**: 本提案仅校验跨仓库 blocker(通过 `cross_repo_deps.py`),本地 blocker 仍由 gate 3 (`STRICT_CHANGE_GATE`) 处理。两者职责清晰。
- **plan-done 阶段延长 5-10s**: 默认 warning 模式下 `check_cross_repo_deps_blocked()` 调用约 5-10s。**Mitigation**: `SKIP_DEPS_GATE=yes` 提供 escape hatch。
- **`STRICT_DEPS_GATE` 与 `STRICT_CONTRACT_GATE` 命名一致性**: 两提案在同一 plan 批次中,文件位置(`plan_done_gate.sh`)紧邻,降低维护复杂度。