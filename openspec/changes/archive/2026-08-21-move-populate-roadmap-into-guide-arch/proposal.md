# move-populate-roadmap-into-guide-arch

## Why

### 动机（来自 2026-08-21 实施复盘）

| 当前状况 | 用户痛点 |
|---------|---------|
| `guide-arch` Phase 6 (arch-done) 完成后，路线图更新需用户手动调用 `skill_use("populate-roadmap-from-arch")` | 流程断点：arch-done 验收 ↔ 路线图更新被人为分割；用户经常忘记跑 |
| `populate-roadmap-from-arch` v1.1 默认全量 grep，33 ADR 跑 4s | ADR 单文件微改也触发全量；Mermaid 图、phase fragment 全部无意义重写 |
| 无 baseline 概念——两次运行之间不知道"哪些变了" | 即使新 ADR 不引用任何代码符号，也无法识别"本次只是改了一个 typo" |
| `guide-arch` 当前不调用 `populate-roadmap-from-arch` | 架构漂移风险：ADR 与 roadmap 状态逐步脱节 |
| `populate_lib.py::catalog_sources()` (line 194) 已能扫 ADR + 元数据 | 但 catalog_sources 是 populate-roadmap-from-arch 内部函数，guide-arch 不直接调用 |

**Oracle 评估 (2026-08-21)**：在 4s/33 ADR 数据点下，全量跑"远未触及需要缓存的阈值"。但用户的核心诉求是 **"arch-done 后自动更新路线图"**（不一定要"快"），增量逻辑是手段，集成点是目的。

**复用 vs 自建**（来自 Oracle 同步咨询）：
- ✅ 复用 `populate_lib.py::catalog_sources()` (line 194) — ADR 元数据格式对齐；提升到 `_lib/adr_catalog.py` 消除跨 skill scripts 依赖（ADR-0021）
- ✅ 复用 git diff — 锚定 `codebase_commit`（无需 MCP）
- ⚠️ codegraph signal **env-var 注入**（由 agent 侧调 codegraph_explore 后写入 `RDDF_CODEGRAPH_FINGERPRINT`，populate_lib.py 只读取，不发起 MCP 调用——subprocess 上下文无法访问 MCP session）
- ❌ 不复用 `code-review-graph` 整框架 — 它是 PR 视角，长期 diff 不适用
- ❌ 不依赖 `codebase-memory-mcp` 索引判断"符号是否存在" — 索引陈旧性引入假阴性（Oracle 已警示），且 Python 里调不了

### 设计决策（待批准）

| 决策点 | 选择 | 备选 |
|--------|------|------|
| 集成点 | `guide-arch` Phase 6 (arch-done) 退出前新增**内部 Step：Roadmap Sync**（不是 Phase 5.5 — 该编号 v2.1 已废弃） | 单独 skill（当前）/ Phase 6.5 |
| 触发条件 | Phase 6 退出前自动调用（无 opt-out flag — arch-done 必然包含 roadmap-up-to-date） | 仅手动调用 / 每次 git commit |
| Gate 语义 | **warning 级**（与 ADR-0007 gate 哲学、ADR-0018 arch 质量门一致）：last_generated_at < git HEAD 时间戳时在 `.arch-quality-report.json` 新增 warning；不阻断 arch-done | 硬门控（需先立 ADR 修订 0007/0018） |
| 增量判定 | git HEAD + ADR file hash + reverse index 三源（**codegraph 是 env-var 注入信号，不是 MCP 调用**） | 仅 file hash / 仅 git HEAD |
| skip 模式输出 | `exit 0` + stderr 写"No changes detected" + stdout 写 last_generated_at | `exit 0` + 静默 / `exit 64` + warning |
| 全量 fallback 触发 | 无 baseline / schema 不匹配 / `git_commit_exists(last_commit)=false` / `RDDF_CODEGRAPH_FINGERPRINT=stale` / 用户显式 `--roadmap-update=force` | 永远全量 / 永远增量（冒险） |
| CLI flag 集 | `--roadmap-update=on\|off\|force`（默认 on）、`--incremental`（默认 on，可 off 强制全量） | 仅 `--incremental` / 无 flag |
| 独立 skill 命运 | 保留为 thin wrapper（v1.2 标记 deprecated），可通过 `--standalone` flag 直接调用 | 完全删除（破坏 v1.1 现有引用） |
| state 文件位置 | `.rddf/state/.populate-state.json`（独立于 `.populate-supplementary.json`） | 合并到 supplementary.json / 合并到 `.arch-handoff.json` |
| 反向索引存储 | 嵌入 `populate-state.json` 的 `reverse_index` 字段 | 单独 `.populate-reverse-index.json` |
| 写入顺序 | 先 `save_supplementary`（v1.1）后 `save_populate_state`（v2 新增）—— state 是 baseline 指针，最后写保证 crash 时 state 偏旧 → 保守 fallback | 并发写 / 无顺序约束 |
| 跨工作区行为 | **per-working-directory state**：每个 worktree 独立 .rddf/state/；切 worktree 首次跑永远 full（4s），切回后 state mismatch → 自动 fallback full | 单 repo 共享 state（会 torn pair 写覆盖） |
| 索引陈旧阈值 | `RDDF_CODEGRAPH_STALE_DAYS=7`（env var 可覆盖，默认 7 天） | 硬编码 7 天 |
| 紧急 reset | AGENTS.md + populate-roadmap-from-arch/SKILL.md troubleshooting 加一行 `rm .rddf/state/.populate-state.json` | 不提供 reset 路径 |

## What Changes

**In Scope**:

- **`guide-arch/SKILL.md` Phase 6 (arch-done exit)** 在写 handoff 之前新增**内部 Step: Roadmap Sync**
- 调 `guide-arch/scripts/roadmap_incremental_update.sh`
- 默认行为：自动触发（与 `--code-verify=on` 默认值对齐）
- **不修改 arch-done 双重门控**（ADR ≥ 1 + roadmap.md 存在）—— `roadmap-up-to-date` 检查作为 warning 写入 `.arch-quality-report.json`（与现有 4 个 warning 检查同等级），与 ADR-0018 / ADR-0007 哲学一致
- `STRICT_ARCH_GATE=yes` 时升级为 error（继承 ADR-0018 严格模式语义，不引入新门控维度）
- **`guide-arch/scripts/roadmap_incremental_update.{sh,py,env.py}`** 新建（3 文件 split，与 Round A/B 一致的 env-var 模式）
- **sh wrapper**: env var 装填 + Python 调用 + stderr 重定向
- **py 主模块**: 实现四模式算法（skip / adr_only / code_only / full）
- **env.py**: 集中校验 env vars（Oracle C1 安全：消除 bash `$VAR` 字符串注入）
- **`skills/_lib/adr_catalog.py`** 新建 — 把 `populate_lib.py::catalog_sources()` 提升到此（消除跨 skill scripts 依赖，ADR-0021）
- 返回 dict：`{adr_id: {file_path, file_hash (sha256), title, status, phase, category}}`
- 原 `populate_lib.py::catalog_sources()` 改为 `from _lib.adr_catalog import scan_adr_catalog` 的 wrapper（保持向后兼容）
- guide-arch 的 `roadmap_incremental_update.py` 直接 import 此模块
- **`populate_lib.py`** 新增 7 个 public 函数（导出到 `__all__`）：
- `load_populate_state_or_default(project_root)` — 读 `.populate-state.json` 或返回 None
- `save_populate_state(state, project_root, codebase_commit)` — atomic write
- `detect_adr_changes(state, project_root, scan_adr_catalog_fn)` — 返回 `(changed, new, deleted)`
- `detect_code_changes(state, project_root)` — 返回 `(changed_symbols, changed_files, status)`；codegraph signal 只读 env var `RDDF_CODEGRAPH_FINGERPRINT`，不调 MCP
- `decide_update_mode(adr_changes, code_changes)` — 返回 `(mode, reason, extra)`
- `select_adrs_for_incremental_verify(adrs, state, mode, extra)` — 返回 `(to_verify, to_reuse)`
- `should_rewrite_phase_fragment(phase_id, prev_state, new_state, mode)` — bool
- **`skills/populate-roadmap-from-arch/scripts/populate.sh`** 改为 thin wrapper
- 不再自己写 Step 1.5 编排；直接 `source $PROJECT_ROOT/.agents/skills/rdd-workflow/skills/guide-arch/scripts/roadmap_incremental_update.sh` 或调 Python 入口
- 保留 CLI 兼容性：`--code-verify=off|on|strict` 仍生效；新增 `--incremental`（默认 on）、`--standalone`（标记 deprecated path）
- v1.2 SKILL.md frontmatter 加 `evolved-from: populate-roadmap-from-arch`，`version: 1.2`
- SKILL.md 加 deprecation banner："本 skill 在 v2.3+ 将被 guide-arch 内置功能取代，新项目请直接调 guide-arch"
- **`skills/_lib/schemas/populate_state_schema.json`** 新建
- 顶层 `{version: {const: 2}}`
- 字段：`generated_at`, `codebase_commit`, `codegraph_fingerprint`(optional), `adrs[adr_id]`, `reverse_index`, `phases[phase_id]`
- 与 v1.1 `populate_supplementary_schema.json` 完全独立 schema（不合并）
- **schema 版本兼容**：v1 state 文件存在时，第一次运行强制 `full` 模式重建；不读 v0/缺失 schema 的 state（fail loud）
- **`populate_lib.py::catalog_sources()` (line 194)** 提取到 `skills/_lib/adr_catalog.py`
- 现有 `arch_gap_analysis.sh` 只有 `generate_gap_analysis()` 和 `list_gap_analyses()` 两个 viewer/generator 函数，**没有 `scan_adr_files()`** —— 本提案不向 arch_gap_analysis 加新接口
- `skills/_lib/adr_catalog.py::scan_adr_catalog(project_root) -> dict[adr_id, AdrMeta]` 是新模块的 public 函数
- 返回 dict 包含 `file_path`、`file_hash (sha256)`、`title`、`status`、`phase`、`category`
- populate_lib.py 用此 dict 格式构建 `populate-state.json` 的 `adrs` 字段
- guide-arch 的 `roadmap_incremental_update.py` 也 import 此模块（消除跨 skill scripts 依赖）
- 8 个现有 `arch_gap_analysis` bats 测试不受影响（不修改 sh wrapper）
- `docs/proposal-suggestions-format.md` 加示例（增量 state schema）
- `AGENTS.md` "常见陷阱" 节加一条："切分支后第一次 arch-done 会自动 fallback full（state 绑 codebase_commit）"
- `README.md` "v2.2 新特性" 节加 roadmap incremental 节
- **不修改** `rdd-workflow` 核心事件/状态引擎（`_lib/state.py` / `_lib/event_log.py` / `_lib/gate.py`）
- **不实现** 工作区级（per-workspace）state 多副本——单 repo 单 state
- **不接入** CI/pre-commit hook 触发——仅 arch-done gate 触发
- **不实现** 跨分支同步 state——切分支自动 full 重建（接受 4s 一次性成本）
- **不实现** 反向索引的代码图谱化存储——保持 JSON 文件，避免 mcp 依赖
- **不实现** `--watch` 长驻模式——单次调用，exit 后无副作用
- **不修改** 现有 `populate_supplementary_schema.json` v1（独立文件，独立升级路径）

### 关键场景

### 场景 1：标准 arch-done 流程

- **GIVEN** 用户完成 `guide-arch` Phase 4 (roadmap-define)，ADR-0023 已创建并归档到 `docs/adr/`
- **WHEN** Phase 5 (arch validation) gate 通过、进入 Phase 6 (arch-done exit)
- **THEN** Phase 6 内部 Step: Roadmap Sync 自动调 `roadmap_incremental_update.sh --code-verify=on`
  - 检测到 1 个新 ADR + 0 个代码改动 → mode = `adr_only`
  - 仅重生成引用了 ADR-0023 的 phase fragment（假设 phase-4）
  - 其他 phase fragment 不被 touch（无 git diff）
  - state.json 更新 `codebase_commit` 和 ADR-0023 entry
  - 输出："Mode: adr_only | Processed: 1 ADR | Phases rewritten: 1 | Elapsed: 0.5s"
  - `.arch-quality-report.json` 新增 warning `roadmap-stale: false`（不阻断 Phase 6）

### 场景 2：零变更跳过

- **GIVEN** state.json 已存在，`codebase_commit` = HEAD，state 中所有 `adr_file_hash` 与当前 ADR 文件 sha256 一致
- **WHEN** 用户跑 `guide-arch` Phase 6 内部 Roadmap Sync（或手动调 populate-roadmap-from-arch）
- **THEN** 立即 exit 0，stderr 写 `✓ Roadmap up-to-date. Last generated: <ts>. Code commit: <hash>.`
  - 不调 git diff（已优化：先比较 codebase_commit + 任意 adr_file_hash；都不变直接 skip）
  - 不写 state.json（幂等）
  - phase fragment 文件 mtime 不变

### 场景 3：代码改但 ADR 未改

- **GIVEN** state.json 存在，ADR 文件未动，但用户 push 了 5 个 commit 改 `skills/guide/SKILL.md`、`skills/_lib/state.py` 等
- **WHEN** Phase 6 内部 Roadmap Sync 触发
- **THEN** 流程：
  1. `detect_adr_changes` 返回 `(changed=[], new=[], deleted=[])` — ADR 全部 file_hash 一致
  2. `detect_code_changes` 调用 `git diff <last_commit>..HEAD` 得 N 个 changed files
  3. 提取这些文件中的符号定义（rg 扫 `^(def|class|function) `）
  4. 查 `state.reverse_index[changed_symbol]`，得受影响 ADR 列表
  5. mode = `code_only`
  6. 只对这些 ADR 重跑 `verify_adr_by_code`，其余 ADR 状态保留
  7. 重写受影响 phase 的 fragment
  8. state.json 写新 codebase_commit

### 场景 4：codegraph 不可用兜底

- **GIVEN** agent 侧通过 `RDDF_CODEGRAPH_FINGERPRINT=stale` 注入陈旧标识（或 env var 未设置）
- **WHEN** `detect_code_changes` 读 env var 判定为 stale
- **THEN** 自动 fallback 到 mode = `full`（即使技术上可以增量）
  - stderr 写 `⚠️  RDDF_CODEGRAPH_FINGERPRINT=stale, falling back to full verification`
  - 退出码 0（不阻断 arch-done Phase 6）
  - 同时把 `codegraph_fingerprint = "stale"` 写入 state，下次仍可识别
  - 阈值由 `RDDF_CODEGRAPH_STALE_DAYS` env var 控制（默认 7 天，0 = 永不 stale）

### 场景 5：v1 state 文件迁移

- **GIVEN** `.populate-state.json` 不存在（v1.1 没生成过）
- **WHEN** Phase 6 内部 Roadmap Sync 首次触发
- **THEN** `load_populate_state_or_default` 返回 None → mode = `full`
  - 第一次跑全量（4s），生成 v2 state.json
  - 第二次起进入增量路径
  - 旧 `.populate-supplementary.json` v1 文件保留不动（独立 schema）

**Out of Scope**:

- (no items specified)

## Capabilities

- **MUST** `roadmap-up-to-date` 检查是 **warning 级**（与 ADR-0018 / ADR-0007 一致），不阻断 arch-done
- **MUST** `roadmap_incremental_update.sh` 用 env-var 传递参数（Oracle C1 — 禁止 `python3 -c "...$VAR..."` 内联）
- **MUST** state.json schema 版本不匹配时 fail loud（exit 1 + stderr "schema version X unsupported, expected 2"）
- **MUST** git diff 范围严格限定 `<state.codebase_commit>..HEAD`（避免误判 uncommitted）
- **MUST** ADR file_hash 用 sha256
- **MUST** `detect_code_changes` 在 `git_commit_exists(last_commit)=false` 时 fallback full（T13 验证）
- **MUST** codegraph signal 通过 env var 注入（`RDDF_CODEGRAPH_FINGERPRINT`），populate_lib 不发起 MCP 调用
- **MUST** 写入顺序固定为：先 `save_supplementary`（v1.1），后 `save_populate_state`（v2 新增）—— state 是 baseline 指针，最后写保证 crash 时 state 偏旧 → 保守 fallback
- **MUST NOT** 修改 `guide-arch` Phase 5 双重门控（ADR ≥ 1 + roadmap.md 存在）
- **MUST NOT** 删除或重命名 `.populate-supplementary.json`（v1.1 用户已依赖）
- **MUST NOT** 写 `codebase_commit` 之外的 git ref（如 branch name，跨分支不可靠）
- **MUST NOT** 用"Step 5.5"或任何复用已废弃编号的命名（v2.1 已迁移到 guide-design）
- **MUST NOT** 引入新的运行时依赖（保持 Python 3.11 stdlib + 现有 requirements）
- **SHOULD** 增量路径耗时 ≤ 全量 50%（4s → 2s 目标）
- **SHOULD** state.json 文件 size ≤ 100KB
- **SHOULD NOT** 用 codegraph 索引判断"符号是否存在"（Oracle 警示：索引陈旧性引入假阴性）
- **SHOULD NOT** 把 state.json 写入 git tracked 路径（保持 `.rddf/state/` gitignored 约定）

## Impact

- (no items specified)

## Acceptance

- `guide-arch/SKILL.md` Phase 6 含 **内部 Step: Roadmap Sync**（不叫 Step 5.5/Phase 5.5/Phase 6.5）
- `guide-arch/scripts/roadmap_incremental_update.{sh,py,env.py}` 三个文件存在且通过 `bats tests/integration/test_roadmap_incremental_update.bats`
- `skills/_lib/adr_catalog.py` 新建，`populate_lib.py::catalog_sources()` 改为 wrapper import 此模块
- `populate_lib.py` 含 7 个新 public 函数（`load_populate_state_or_default` / `save_populate_state` / `detect_adr_changes` / `detect_code_changes` / `decide_update_mode` / `select_adrs_for_incremental_verify` / `should_rewrite_phase_fragment`）
- `skills/_lib/schemas/populate_state_schema.json` v2 schema 存在
- `populate-roadmap-from-arch/SKILL.md` frontmatter 标 `version: 1.2` + deprecation banner + troubleshooting 加 `rm .rddf/state/.populate-state.json` reset 命令
- `populate-roadmap-from-arch/scripts/populate.sh` 改为 thin wrapper
- `tests/unit/test_populate_lib_incremental.py` 含 ≥ 18 个测试覆盖 T1-T9 + T13-T16 决策矩阵（**必须含 T13 force-push ref missing 验证**）
- `tests/integration/test_roadmap_incremental_update.bats` 含 ≥ 12 个 @test（T10-T12 + T17-T18 + 跨调用链路）
- `tests/unit/test_schema_version_field.py` 列表加 populate_state_schema (20 → 21 schemas)
- `guide-arch/SKILL.md` frontmatter `role.boundaries.owns` 加入 `.rddf/state/.populate-state.json` 和 `.rddf/roadmap/phases/*.md`（ADR-0028 边界修正）
- 所有现有测试通过（baseline: 2018 passed / 4 pre-existing failures unrelated）
- T1 场景（零变更）实测耗时 < 0.1s（vs 全量 4s，节省 40x）
- T13 场景实测：人为 `git update-ref -d` 删除 `state.codebase_commit` 后跑 → mode=full + stderr warning + exit 0
- T17 场景实测：在 `$BATS_TMPDIR/wt/` 创建 worktree 后跑 → mode=full（无 state）+ exit 0
- AGENTS.md "常见陷阱" 节增 3 条：
  - "切分支/切 worktree 后第一次 arch-done 自动 fallback full（per-worktree state 隔离）"
  - "codegraph signal 必须由 agent 侧通过 RDDF_CODEGRAPH_FINGERPRINT env var 注入，Python 内部不能调 MCP"
  - "reset roadmap 增量 state：`rm .rddf/state/.populate-state.json`（无 baseline → 下次 full）"
- proposal-suggestions-format.md 加 v2 schema 示例

