## Context

把 `populate-roadmap-from-arch` v1.1 的全量路线图生成能力嵌入 `guide-arch` Phase 6 退出流程，并改造为四模式增量更新（skip / adr_only / code_only / full）。背景详见 `proposal.md` 的 Why 段。当前实现为单进程全量 grep 33 ADR 跑 4s，无 baseline 概念，arch-done 后用户必须手动调 `skill_use("populate-roadmap-from-arch")` 才会更新路线图——这是流程断点。

本提案经 Oracle 高 IQ 审查（2026-08-21, ses_fdc8980bfffeB8q2wpOqYqOEGi）确认 2 CRITICAL + 3 HIGH 设计缺陷，已在 `proposal.md` 设计决策表中修复（gate 语义统一为 warning 级、`scan_adr_files()` 复用点替换为真实存在的 `catalog_sources()`、codegraph 信号改 env-var 注入、Step 5.5 改名为 Phase 6 内部 Step、补 T13-T18 测试）。

## Goals / Non-Goals

**Goals:**

- arch-done Phase 6 退出前自动调用 roadmap 更新，无需用户手动介入
- 增量判定基于 git HEAD + ADR file hash + reverse index 三源；两方皆不变时 exit 0 不重写任何文件
- 新增 `--roadmap-update={on,off,force}` + `--incremental` + `--standalone` CLI flag 集
- 复用 `populate_lib.py::catalog_sources()` 的真实 ADR 元数据扫描能力，提取到 `skills/_lib/adr_catalog.py` 消除跨 skill scripts 依赖（ADR-0021）
- 写入顺序固定为先 `save_supplementary`（v1.1）后 `save_populate_state`（v2）；state 是 baseline 指针，最后写保证 crash 时 state 偏旧 → 保守 fallback
- 新增 `.populate-state.json` schema v2（独立于 v1.1 `.populate-supplementary.json`，互不影响）
- 提供一行 reset 命令 `rm .rddf/state/.populate-state.json`（无 baseline → 下次 full）
- 保留 `populate-roadmap-from-arch` standalone skill 为 thin wrapper（v1.2 标记 deprecated），通过 `--standalone` flag 直接调用
- 18 个测试场景覆盖 T1-T18（force-push / rebase / cherry-pick / merge / worktree 首跑 / 切 worktree mismatch 等边界）

**Non-Goals:**

- 不修改 `guide-arch` Phase 5 双重门控（ADR ≥ 1 + roadmap.md 存在）—— `roadmap-up-to-date` 仅作为 warning 写入 `.arch-quality-report.json`，与 ADR-0018 / ADR-0007 哲学一致
- 不实现工作区级（per-workspace）state 多副本——单 repo 每个 working-directory 独立 state（per-worktree 隔离由 `.rddf/state/` gitignored + worktree 物理隔离自动实现）
- 不接入 CI/pre-commit hook 触发——仅 Phase 6 触发
- 不实现跨分支同步 state——切分支/worktree 自动 full 重建（接受 4s 一次性成本）
- 不实现反向索引的代码图谱化存储——保持 JSON 文件，避免 mcp 依赖
- 不修改 `rdd-workflow` 核心事件/状态引擎（`_lib/state.py` / `_lib/event_log.py` / `_lib/gate.py`）
- 不引入新的运行时依赖（保持 Python 3.11 stdlib + 现有 requirements）

## Decisions

### 1. 集成点：Phase 6 内部 Step: Roadmap Sync

**决策**：在 `guide-arch` Phase 6 (arch-done exit) 写 handoff 之前新增内部 Step "Roadmap Sync"，调 `roadmap_incremental_update.sh --code-verify=on`。不叫 Step 5.5 / Phase 5.5 / Phase 6.5（v2.1 已废弃）。

**理由**：
- 路线图更新是 arch-done 的自然收尾步骤（ADR + roadmap.md 已完成 → 自动生成 roadmap），属于 Phase 6 的语义范围
- Phase 5 (validation gate) 只做 check，不应执行副作用
- 不叫 "Step 5.5" 是因为该编号与 v2.1 刚废弃的提案审批节点冲突，会让 grep/测试/文档产生歧义

**备选**：
- 单独 skill（当前）→ 用户手动调用，流程断点 ❌
- Phase 6.5 → 与 Phase 5.5 同样存在文档歧义 ❌

### 2. Gate 语义：warning 级（不阻断）

**决策**：`roadmap-up-to-date` 检查作为 warning 写入 `.arch-quality-report.json`，与现有 4 个 warning 级质量检查（ADR-0018）同级。

**理由**：
- ADR-0018（arch 质量门）和 ADR-0007（gate 哲学）均采用 warning 级 + 可硬化的设计
- 不修改 arch-done 双重门控（ADR ≥ 1 + roadmap.md 存在）
- `STRICT_ARCH_GATE=yes` 继承现有 ADR-0018 严格模式语义，不引入新门控维度

**备选**：
- 硬门控 → 需要先立 ADR 修订 ADR-0007/0018，否则单方面改变 ADR 语义 ❌
- 完全无检查 → 失去增量更新的可见性 ❌

### 3. 真实复用点：`populate_lib.py::catalog_sources()` 提升到 `_lib/adr_catalog.py`

**决策**：把 `skills/populate-roadmap-from-arch/scripts/populate_lib.py::catalog_sources()` (line 194) 提取到 `skills/_lib/adr_catalog.py`，作为共享扫描层。

**理由**：
- Oracle 验证：`arch_gap_analysis.sh` 只有 `generate_gap_analysis()` 和 `list_gap_analyses()` 两个 viewer/generator 函数，**没有 `scan_adr_files()`**（proposal 初版错误引用）
- 真实复用目标就是 `catalog_sources()`——已实现 ADR 元数据扫描（`AdrRecord` 包含 file_path / title / status / phase / category）
- 提升到 `_lib/` 同时消除跨 skill scripts 依赖（ADR-0021）：原 `populate_lib.py::catalog_sources()` 改为 `from _lib.adr_catalog import scan_adr_catalog` 的 wrapper

**备选**：
- 在 `arch_gap_analysis.sh` 新建 `scan_adr_files()` → 与现有两个函数职责重叠 ❌
- 复制实现 → 维护成本 ❌

### 4. codegraph 信号：env-var 注入（不调 MCP）

**决策**：codegraph 信号由 agent 侧通过 env var `RDDF_CODEGRAPH_FINGERPRINT` 注入；`populate_lib.py` 只读取 env var，不发起 MCP 调用。

**理由**：
- Python subprocess 上下文无法访问 agent 侧 MCP session（Oracle 验证：现有 v1.1 的 `_try_mcp_search()` 本质也是探测后 fallback 到 rg）
- 阈值由 `RDDF_CODEGRAPH_STALE_DAYS` env var 控制（默认 7 天，0 = 永不 stale）
- agent 侧在调 `roadmap_incremental_update.sh` 前决定 codegraph 新鲜度，写入 env var（Oracle C1 风格）

**备选**：
- Python 内调 MCP → subprocess 不可达 ❌
- 完全不引入 codegraph signal → 失去"代码侧变更快速路径"，每次必须 git diff + rg 扫符号（code_only 模式无法触发） ❌

### 5. State schema v2 + 独立文件

**决策**：新增 `skills/_lib/schemas/populate_state_schema.json` v2 schema；state 文件路径 `.rddf/state/.populate-state.json`，与 v1.1 `.populate-supplementary.json` 完全独立。

**理由**：
- 两个 view 文件职责不同：supplementary 记录单次 verify 结果（v1.1 已有），state 记录增量基线（v2 新增）
- 独立 schema 允许独立升级路径——v1.1 用户不被 v2 schema 强制迁移
- 互不破坏：v1.1 supplementary 由 v1.1 代码写，v2 state 由 v2 代码写，写入顺序固定

**备选**：
- 合并到 supplementary.json → 单文件膨胀 + 升级耦合 ❌
- 合并到 `.arch-handoff.json` → 阶段边界破坏 ❌

### 6. 写入顺序固定：先 supplementary 后 state

**决策**：`save_supplementary` (v1.1) 必须先写，`save_populate_state` (v2) 必须后写。

**理由**：
- state 是 baseline 指针，最后写保证 crash 时 state 偏旧 → 下次跑 fallback full（保守正确）
- 反向顺序下 crash 时 state 已新而 supplementary 偏旧 → 下次误判 code_only → 漏报

**备选**：
- 并发写 → torn pair 风险
- 无顺序约束 → crash 时不确定性

### 7. CLI flag 集：`--roadmap-update={on,off,force}` + `--incremental` + `--standalone`

**决策**：统一 CLI flag 集，避免 proposal 初版 flag 集不一致（`--force-incremental` 出现在 fallback 触发表但未列入 In Scope）。

- `--roadmap-update=on|off|force`：默认 on（自动触发），off 跳过，force 强制全量
- `--incremental`：默认 on（启用增量），off 等价于 force
- `--standalone`：仅 populate-roadmap-from-arch 单独 skill 使用，标记 deprecated path

**理由**：
- flag 语义清晰不重叠
- `--incremental=off` 与 `--roadmap-update=force` 等价但保留两者以便渐进式迁移
- `--standalone` 显式标记 v1.1 用户的退出路径

**备选**：
- 仅 `--incremental` flag → 难以区分"完全跳过" vs "强制全量"
- 无 flag → 用户无法 opt-out（arch-done 必然执行）❌

## Risks / Trade-offs

| 风险 | 严重度 | 缓解 |
|------|--------|------|
| state.json 损坏导致 skip 错判 | LOW | 启动时 JSON schema 校验 + checksum 字段；校验失败 fallback full |
| codegraph 索引陈旧导致 code_only 漏报 | MEDIUM | `RDDF_CODEGRAPH_FINGERPRINT=stale` 时 fallback full（agent 侧注入）；阈值由 env var 控制 |
| force-push / branch reset 后 last_commit 不存在 | HIGH | `git_commit_exists(last_commit)` 检查（T13 锁定）；ref 不存在 fallback full |
| 写入并发导致 torn pair（supplementary 新 / state 旧） | MEDIUM | 顺序固定为先 supplementary 后 state；state 偏旧 → 下次保守 fallback |
| 反向索引在 100+ ADR 时膨胀 | LOW | 单文件 size 上限 100KB（约束）；超出时拆分 `.populate-state-reverse-index.json`（v2.1+ follow-up） |
| 状态"有效但语义错"（codebase_commit 指向错误祖先）无自动检测 | LOW | 提供一行 reset 命令 `rm .rddf/state/.populate-state.json`（AGENTS.md + SKILL.md troubleshooting） |
| Python subprocess 上下文无法访问 MCP session | 已规避 | codegraph signal 改 env-var 注入；populate_lib 不发起 MCP 调用 |
| 跨 skill scripts import 触发 ADR-0021 边界违例 | 已规避 | `catalog_sources()` 提升到 `skills/_lib/adr_catalog.py`，消除跨 skill 依赖 |

## Implementation Plan (Tasks 概览)

完整 tasks 拆分见 `tasks.md`。10 个 Phase × N tasks，覆盖：

1. **A. 共享扫描层**：`_lib/adr_catalog.py` 新建；`populate_lib.py::catalog_sources()` 改 wrapper
2. **B. State schema v2**：`populate_state_schema.json` 新建
3. **C. populate_lib.py 7 个新函数**：`load/save_populate_state`、`detect_adr_changes`、`detect_code_changes`、`decide_update_mode`、`select_adrs_for_incremental_verify`、`should_rewrite_phase_fragment`
4. **D. guide-arch 集成脚本**：`roadmap_incremental_update.{sh,py,env.py}` 3 文件 split
5. **E. guide-arch SKILL.md 修改**：Phase 6 内部 Step + frontmatter role.boundaries.owns 更新
6. **F. populate-roadmap-from-arch 重构**：v1.2 frontmatter + deprecation banner + thin wrapper populate.sh + troubleshooting reset 命令
7. **G. 测试**：18 个 T1-T18 场景（≥ 18 unit + ≥ 12 bats），包含 T13 force-push、T17 worktree 首跑、T18 切 worktree mismatch
8. **H. 文档**：AGENTS.md 陷阱节增 3 条；proposal-suggestions-format.md v2 schema 示例
9. **I. 注册**：tests/unit/test_schema_version_field.py 列表加 populate_state_schema (20→21 schemas)
10. **J. 全量回归**：archive 前 `./test.sh --full --regression` 确认无新增失败