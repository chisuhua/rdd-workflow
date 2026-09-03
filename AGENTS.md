# AGENTS.md — rdd-workflow

> OpenSpec 工作流技能包: `propose → plan → execute → status → archive` change lifecycle.
> v2.0 self-contained: 内置 TDD 5 步计划生成与执行, 无外部 skill 依赖.

## 快速命令

```bash
# 统一入口（推荐）— ./test.sh 包裹 npm test, 自带彩色 + summary
./test.sh --quick                        # 快速: smoke + pytest unit (~45s)
./test.sh --full                         # 全量: bats recursive + pytest unit+integration (~8min)
./test.sh --bats                         # 只跑 bats recursive
./test.sh --python                       # pytest unit + integration
./test.sh --unit                         # 只跑 pytest unit
./test.sh --integration                  # 只跑 pytest integration

# 高级选项 (可与上面模式组合)
./test.sh --full --regression            # bats 改用 report_regression.sh 对比 KNOWN_FAILURES baseline (区分已知失败 vs 新增失败)
./test.sh --full --stop-on-failure       # 任一 step 失败立即停止 (默认继续跑拿完整图)
./test.sh --full --no-color              # 禁用颜色 (适合日志/管道)
./test.sh <file.bats|file.py>            # 单文件入口 (绕过 mode)

# 单独跑某类 (绕过 test.sh, 用于调试)
npm test                                # = bats tests/ --recursive (全量 bats, 不跑 pytest)
bats tests/smoke.bats                   # 快速冒烟 (7 个 smoke cases)
bats tests/_lib/test_skill.bats         # skill.bash parser (8 cases)
bats tests/integration/test_global_install_external_project.bats  # 全局安装测试 (11 cases)

# Python (npm test 不会跑, 必须显式调用)
python3 -m pytest tests/unit/ -q --tb=short          # 57 个 unit 文件
python3 -m pytest tests/integration/ -q --tb=short   # 10 个 Python integration (.py)
pip install -r requirements.txt                      # PyYAML, jsonschema, pytest

# 对比 baseline (CI 等价; ./test.sh --bats --regression 已包含)
bash tests/scripts/report_regression.sh
```

**退出码**: `0`=全绿 / `1`=有失败 / `2`=参数错 / `127`=缺依赖. 详见 `./test.sh --help`.

CI 在 `.github/workflows/test.yml`, 按序执行: 安装 deps → **断言质量门控** → Python unit → Python integration → bats smoke → bats static 子集 → bats git-worktree 子集.

> **重要**: `npm test` 只跑 bats, **不会**捕获 Python 测试失败. 改完 Python 后必须手动 `pytest tests/` 或 `./test.sh --python`/`--unit`/`--integration`.

### Archive 前全量回归门（MANDATORY）

**行为规则**: 完成 `openspec/changes/<name>/tasks.md` 的所有 task 后、archive change 之前，必须跑一次全量测试（`./test.sh --full --regression`）确认没有新增失败。

```
完成所有 task
    ↓
./test.sh --full --regression    ← 必须全绿或仅 baseline 已知失败
    ↓
git commit (worktree-internal)
    ↓
archive change (guide-ship Phase 3)
```

- **新失败** (`report_regression.sh` 报的"新增失败") 必须修：可能是新引入的 regression
- **已知失败**（在 `tests/KNOWN_FAILURES.txt` baseline 中）可放行
- **紧急跳过**: `SKIP_REGRESSION=1` 仅供 hotfix，且必须在 commit message / change 日志中标注

**实现状态**: 此规则已通过 [`add-full-regression-gate`](.rddf/improvements/add-full-regression-gate.md) 提案（`proposal-approved.md` P0, 2026-07-28）正式批准。当前 `guide-ship` 的 `archive_gate_check()`（`_lib/archive.sh`）只检查 `tasks.md` 完成度，**未自动化强制回归门**。在 `guide-ship` 实施该提案之前，本节作为 agent 的硬性行为约束。

### 全局安装测试（`tests/integration/test_global_install_external_project.bats`）

模拟第三方项目使用全局安装（`~/.agents/skills/`）的能力。**19 个用例**覆盖:
- `rddf` CLI: `--help`、非 rdd-workflow 项目友好退出、读取外部 `package.json`
- 解析器 fallback: `resolve_rdd_skill_dir` / `resolve_rdd_lib_dir` 都回退到 `~/.agents/skills/`
- 文档化的双层 bootstrap 模式 (`source ... || source $HOME/.agents/skills/...`)
- Python `_lib` 模块通过 `.pth` 发现
- bash `source ~/.agents/skills/_lib/state.sh` 加载运行时 helper
- 27 个子技能 symlink 完整性

测试在 `$BATS_TMPDIR` 创建独立的 git 仓库, **不**修改源 repo 的 `.rddf/` (其他 bats 测试依赖 stale state, 删除会级联失败)。

```bash
bats tests/integration/test_global_install_external_project.bats   # 11/11 pass
```

**Skip-not-fail 策略**: 全局安装缺失时 (`~/.agents/skills/_lib/skill_root.sh` 不存在) 自动 skip, 适合 CI 在 `install.sh --global` 未执行的环境跑。

## 架构

**五阶段架构** (v3.0+): `arch → design → plan → ship → verify`

> ⚠️ **v2.0.6+ 变更 (move-proposal-creation-to-design)**: design 阶段升级为「批准即创建 + 内容审查」(approve 后生成完整 proposal.md → 用户确认 → 落盘 + 状态写入)。详见 ADR-0025。

| 阶段 | Skill | 职责 |
|------|-------|------|
| arch | `rdd-arch` | 架构定义: ADR, 差距分析, roadmap |
| design | `guide-design` | 设计管理 + 内容审查: 提案创建, 审查, 批准/拒绝/延迟; approve 即落盘完整 proposal.md |
| plan | `guide-plan` | 变更生成: intake (含 changes_pre_created 跳过), fill (specs/design/tasks), deps |
| ship | `guide-ship` | 变更执行: worktree/轻量, execute, archive, cleanup |
| verify | `rdd-verifier` | 验证回环: 批量调 ac-verifier, 启发式分类 AC pass/fail, 失败回 plan/ship, 最多 3 次 (ADR-0034) |

`guide-ship` 自动检测并行冲突:
- 无其他 worktree **且** 仅此一个 change → ⚡ **轻量模式** (创建 branch, 直接在主仓库执行, 跳过 worktree)
- 有活跃 worktree **或** 多个 change → 🔀 **worktree 模式** (创建隔离 worktree)

`guide-spec` 已在 v2.0 移除（原为 60 行别名，内部按序调用 `rdd-arch` → `guide-plan`）。请直接使用 `rdd-arch` 和 `guide-plan`。
`guide` 是无状态推荐器, 扫描项目状态推荐下一步, 不写文件, 不调 openspec CLI.

## 关键目录

```
_lib/                          # ⭐ 真实实现层 (commit c3a90fe "flatten package layout")
  state.sh / worktree.sh / archive.sh / status_helpers.sh / discover-arch-artifacts.sh / env_checks.sh / parallel_throttle.sh / resolve_skill_name.sh / sessions_count.sh / ship_execution_mode.sh / ship_parallel.sh / skill_root.sh / wave_scheduler_hooks.sh / discover_ship_changes.sh / discover_roadmap_fragments.sh / post_archive_cleanup.sh / check_project_setup.sh / orchestrator_entry.sh / post_flow_wrap.sh  # bash 工具 (~19 files)
  cli/                         # 28 个 `rddf` 子命令 (ac_verify/archive/cleanup/contract_check/dashboard/deps/discover_ship_changes/doctor/feature/guide/init/issue/iteration_strict/l2_trend/migrate_improvements/monitor/orchestrate/rdd_hub_bootstrap/report_issue/roadmap/sessions/status/sync_hub/validate/version/watch_hub/archive_sync 等)
  gate.py / roadmap_state.py / config.py / session.py / session_base.py / session_manager.py / session_stats.py  # 跨切核心模块 (会话 + 状态)
  arch_quality_gate.py / change_alignment.py / dependency_scheduler.py / event_context.py / rate_limiter.py / roadmap_sprint.py / trigger_engine.py / trigger_registry.py / triggers.py / validate_delta_targets.py / validate_report.py  # 其余顶层模块
  adr_catalog.py / cleanup_plan_handoff.py / contract_diff.py / cross_repo_audit.py / cross_repo_deps.py / cross_repo_deps_cache.py / cross_repo_gate.py / cross_repo_state.py / gh_hub_client.py / hub_issue.py  # P1-1a 迁移的 10 个跨 repo 模块
  core/                        # 运行时内核 (6 .py): event_log, event_types, state_vector, defaults, lock, atomic_write
  loop/                        # v2.0 loop 引擎 (15 .py): actions, agents, design_phase, detectors, event_queue, flow_customizer, flowchart, human_nodes, interaction_modes, loop_state, memory, plugin_loader, sanitizer, step_pipeline, tribunal
  iteration/                   # iteration 视图管理 (render, schema, store, repair, l2, archive_sidecar, post_archive)
  schedulers/                  # 调度器 (4 .py): cron_scheduler, fs_watcher, git_hook, webhook_receiver
  schemas/                     # JSON schema (19 files): arch_handoff, config, deps_analysis, design_handoff, feature_view, iteration, plan_handoff, sessions, state_vector, trigger 等
  loop_engine.py               # v2.0 Loop 引擎入口（向后兼容 shim 实际实现在 _lib/loop_engine.py）
skills/                        # Markdown skills (27 SKILL.md + INSTALL.md) + per-skill scripts/
  INSTALL.md                   # 第一入口 (v1.1.0)
  guide/SKILL.md               # 推荐器
  rdd-arch/SKILL.md          # arch 阶段 (v2.0.8 Phase 2 重组)
  guide-design/SKILL.md        # design 阶段 (v2.1 新增)
  guide-plan/SKILL.md          # plan 阶段
  guide-ship/SKILL.md          # ship 阶段 (v2.0)
  propose/SKILL.md / execute/SKILL.md / status/SKILL.md / roadmap/SKILL.md / deps/SKILL.md / feature/SKILL.md / rddf-session/SKILL.md  # 子技能
  rdd-workflow-writing-plans/SKILL.md  # 内置 TDD 5 步 plan 生成器
  loop_engine.py               # v2.0 Loop 引擎入口（向后兼容 shim）
  _lib/                        # ⭐ shim 层 (post-c3a90fe flatten layout, 2026-08-25 P1-1b identity-merge)
    *.sh (15 个)               # 13 行 shim: 本地 `${_PARENT_DIR}/_lib/X.sh` 优先,降级到 `~/.agents/skills/_lib/X.sh`
    core/loop/schedulers/...   # 4 行 __init__.py path-widening shim (向后兼容历史 import)
    adr_catalog.py ... hub_issue.py  # 10 个 P1-1a 迁移模块的 identity-merge shim (做 `sys.modules[__name__] = _lib.X`)
  rdd-arch/scripts/          # arch 阶段辅助脚本 (arch_env_check, write_arch_handoff, arch_gap_analysis 等)
  guide-plan/scripts/          # plan 阶段辅助脚本 (plan_intake, plan_done_gate, plan_deps_candidates 等)
  guide-ship/scripts/          # ship 阶段辅助脚本 (ship_plan, ship_review, ship_archive, ship_monitor 等)
  execute/scripts/             # execute 辅助脚本 (select_worktree, tasks_writeback, execute_step7 等)
  deps/scripts/                # deps 辅助脚本 (deps_output, deps_render_report 等)
  propose/scripts/             # propose 辅助脚本 (propose_change 等)
  feature/scripts/             # feature 辅助脚本 (feature_summary, feature_graph 等)
  status/scripts/              # status 辅助脚本 (status_render_mode_a 等)
tests/
  test_helper.bash            # load_lib 解析器 + 断言辅助
  conftest.py                 # 把项目根加进 sys.path (P1-1b: `skills._lib` 路由到 `_lib` + 10 个身份合并 shim)
  smoke.bats                  # 基础设施冒烟 (v2.0.3 起: 动态 glob + v1.x regression, 覆盖全部 skill)
  unit/                       # 210 个 Python 单元测试文件 (~2017 测试函数, 含 P1-1b 新增 test_p1_1_identity_merge)
  integration/                # 281 bats + 15 py 集成测试 (~1789 bats 测试用例)
  _lib/                       # bash helpers (skill.bash, deps-subagent.bash 等)
docs/adr/                     # ADR-0000 模板 + ADR-0001~0035 (35 个唯一编号, 36 个实体文件; v2.0.2 重编号 ADR-0013 → ADR-0020; v2.0.8+ 持续追加)
                             # 关键 ADR: ADR-0003 三阶段架构 / ADR-0010 多会话管理 / ADR-0016 arch 发现契约 / ADR-0017 rddf-session / ADR-0018 arch 质量门 / ADR-0019 change-arch-alignment / ADR-0022 manual_deps 字段 / ADR-0024 deps-driven execution mode / ADR-0025 design 阶段独立化 / ADR-0027 continuous evolution / ADR-0028 role-model / ADR-0029 issue-driven / ADR-0030 hub-spoke / ADR-0031 cross-repo human-in-loop / ADR-0032 hub deepening / ADR-0033 submodule-aware / ADR-0034 rdd-verifier / ADR-0035 verifier-archive-gate boundary
                             # **Note**: 此关键 ADR 列表人工维护(策展判断,只列"已实施"+"已采纳"的 ADR)。
                             # 完整 ADR 索引由 `_lib/adr_index_generator.py` 自动生成,见 `docs/adr/README.md` 中
                             # `<!-- ADR_INDEX_START --> ... <!-- ADR_INDEX_END -->` 段 (per adr-index-auto-sync change 2026-08-28)。
docs/change-quality-guide.md  # change 质量等级指南 (Bronze/Silver/Gold); 阈值与 Plan B `propose_quality_check.py` 对齐, 反模式以 ADR-0019 为准
openspec/                     # OpenSpec CLI 数据 (随项目走)
  changes/                    # active changes + archive/
  specs/                      # 已采纳的 capability specs (28 个)
```

## D3 design-pre-created 协同 (v2.2+)

`guide-design` 批准的 change 自动落盘 `openspec/changes/<name>/specs/<name>/spec.md` (D3 design-pre-created 协同)。

| proposal.md 段 (D2 输出) | specs/<sub>/spec.md 段 | 映射函数 |
|---|---|---|
| `## Acceptance` checkbox `- [ ]` | `### Requirement: acceptance-N` + `#### Scenario:` (Given-When-Then) | `generate_spec_delta()` |
| `## Capabilities` MUST/MUST NOT | `### Requirement: capability-N` + `#### Scenario:` (openspec v1.4 要求每 Requirement 含 Scenario) | `generate_spec_delta()` |
| 顶部段头 | `## ADDED Requirements` | (v1.4 强制) |

**生成路径**: `approve_proposal.sh` 在写 `proposal.md` 后调用 `generate_spec_delta()`(从 proposal.md 读,确保段头为英文 D2 输出),写入 `specs/<name>/spec.md`。

**Idempotency**: `openspec/changes/<name>/specs/<name>/` 已存在则跳过(手工补过的 case 不被覆盖)。

**Commit 示例**:
```
feat(guide-design): auto-generate specs/ on approve
fix(guide-design): correct inverted git add logic in approve_proposal.sh
```

## Active Feature Fragments (v2.2+)

Feature fragments (`rddf roadmap add-feature`) 跨阶段追踪多 phase 改进项。AI agent session 启动时应扫读此段以了解 in-flight 工作流。

**当前活跃 feature**（手动维护，来源：`rddf roadmap list-features` 或扫描 `.rddf/roadmap/features/*.md`）：

| feature id | 主题 | phase_refs | 状态 | 源文件 |
|---|---|---|---|---|
| `feat-fix-audit-findings` | 2026-08-26 文档与代码一致性审计后续修复（18 个 audit-followup 提案） | phase-1, phase-2, phase-3, phase-4 | active | `.rddf/roadmap/features/feat-fix-audit-findings.md` |
| `feat-fix-archive-gaps-v2` | 第二波归档治理改进（ADR 索引自动同步 / CHANGELOG-USAGE 同步 / verifier-archive-gate 边界明确化，3 个 P2→P1 升级提案） | phase-1, phase-2, phase-3 | proposed | `.rddf/roadmap/features/feat-fix-archive-gaps-v2.md` |

**自动化进展（per `improve-roadmap-feature-discovery` 提案）**：
- ✅ `skills/guide-design/scripts/feature_discovery.py::list_active_features` 已实现（commit 9c4e668），可在 `guide-design` Phase 1 preflight 调用
- ⏳ AGENTS.md 自动段生成（CLI `rddf roadmap --update-agent-md`）未实现 — 当前为手维护
- ⏳ `rdd-arch` Phase 1 输出 feature fragments 列表作为 context 未实现

**注意事项**：
- 创建新 feature 时同步在本表登记行（避免失去 traceability）
- feature 状态变 `done`/`archived` 时更新本表

## 关键约定 (容易踩坑)

### Skill 角色模型 (ADR-0028)

5 个阶段技能 (`rdd-arch`, `guide-design`, `guide-plan`, `guide-ship`, `rdd-verifier`) 的 frontmatter 包含 `role:` 字段（per ADR-0028 + ADR-0034 §10），定义角色、视角、边界：
- `role.title`: 双语角色名（如 "Architect (架构治理者)"）
- `role.perspective`: 思考视角（1-2 句）
- `role.boundaries.owns`: 文件路径清单（此阶段拥有）
- `role.boundaries.not_owns`: 明确禁止的文件路径
- `role.boundaries.human_involvement`: 高/中/低（对应 ADR-0003 梯度）

详见 [ADR-0028](docs/adr/ADR-0028-role-model-per-phase.md)。

### 状态文件 (`.rddf/state/`, gitignored)

| 文件 | 用途 | 写入方 |
|------|------|--------|
| `.rddf/state/.arch-handoff.json` | arch→plan 交接 + **ADR-0016 发现契约** v1 (adr_dir/roadmap_path/architecture_dir/adr_pattern/discovered/version) | `rdd-arch` (arch-done) / `guide-plan` (Phase 0 intake) + `propose`/`roadmap`/`gate.py`/`detectors.py`/`actions.py`/`scan-state.sh` (handoff readers, fallback to defaults) |
| `.rddf/state/.plan-handoff.json` | plan→ship 交接 + **execution_mode_decisions** (ADR-0024) | `guide-plan` (plan-done 写入) / `guide-ship` (ship-start 读取) |
| `.rddf/state/sessions.json` | **rddf-session 生命周期** (ADR-0017) — 跨 OpenCode session 工作流恢复 | `rdd-arch`/`guide-plan`/`guide-ship` 入口 + `rddf-session` skill 5 子命令 |
| `.rddf/state/deps-analysis.json` | **结构化** deps 输出 (v2.0.1) + **execution_mode_recommendations** (ADR-0024) | `deps` Step 5b 优先写; Step 6 markdown-fallback 时也写 |
| `.rddf/state/deps-candidates.json` | deps 候选列表 | `guide-plan` (deps 阶段) |
| `.rddf/state/deps-output.md` | deps 人类可读报告 | `deps` Step 5 |
| `.rddf/state/iteration.json` | **当前 sprint 视图** (v2.0.1) | propose/guide-ship/execute/deps/archive hooks |
| `.rddf/state/roadmap-state.json` | roadmap 阶段/category 计数 | `propose` (status 改时) |
| `.rddf/state/index.md` | change 索引 | `rdd-arch` / `guide-plan` |
| `.rddf/state/.deps-output.md` | deps 旧路径 (开头有 `.`) | `deps` Step 5 (兼容保留) |
| `roadmap-meta.yaml` (in `openspec/changes/<name>/`) | Per-change metadata (含 `manual_deps`/`manual_blocks` 字段, ADR-0022) | `propose` (change creation) | `deps` (manual_deps merge), iteration sync |

`.rddf/state/`, `.rddf/wt/`, `.rddf/detectors/`, `.rddf/actions/` 全部 gitignored;
`.rddf/plans/` **随 git 版本控制** (执行契约路径).
`iteration.json` 是 **多 hook 写入**的 view 文件, 由 `skills/_lib/iteration/` 包集中管理;
`deps-analysis.json` 同样是 view 文件, 由 `skills/deps/scripts/deps_output.py` 管理.
两者 schema 在 `skills/_lib/schemas/` 下, 改 schema 必须 bump version 字段.
`proposal-suggestions.md` 在项目根目录, 随 git 版本控制, 格式为 **Markdown 表格** (索引到 `.rddf/improvements/*.md`). 审查通过后添加到 `proposal-approved.md` (同为 Markdown 表格格式). 详见 `docs/proposal-suggestions-format.md` 和 `docs/proposal-approved-format.md`.

### Arch Discovery Contract (ADR-0016)

`rdd-arch` Phase 1 setup 通过 `skills/_lib/discover-arch-artifacts.sh` 扫描项目布局,
将发现的 ADR 目录、roadmap 文件、architecture 目录写入 `.arch-handoff.json` 的
`adr_dir` / `roadmap_path` / `architecture_dir` / `adr_pattern` / `discovered` 字段.

**下游消费者** (`guide-plan`, `propose`, `roadmap`, `gate.py`, `detectors.py`,
`actions.py`, `scan-state.sh`) 优先读 handoff, 缺失时回退到 v2.0 默认约定:

| 字段 | 默认 fallback |
|------|---------------|
| `adr_dir` | `docs/adr` |
| `roadmap_path` | `roadmap.md` |
| `architecture_dir` | `docs/architecture` |
| `adr_pattern` | `ADR-*.md` |

**环境变量优先级最高** (覆盖 handoff):
- `SPEC_WORKFLOW_ADR_DIR`
- `SPEC_WORKFLOW_ROADMAP_PATH`
- `SPEC_WORKFLOW_ARCHITECTURE_DIR`
- `SPEC_WORKFLOW_ADR_PATTERN`

**Schema 版本**: v1 (字段定义见 `skills/_lib/schemas/arch_handoff_schema.json`).
字段定义改必须 bump version; 消费者拒绝 version=0 payload.

**测试**: 6 schema tests + 10 discover tests + 8 bats integration tests
(默认/自定义/缺失布局 + handoff 读写 + env var override + schema 校验).

- `SKIP_ADR_CONFIRM=yes` — 跳过 rdd-arch Phase 2 选项 1 adr-create 草稿确认直接落盘 (作用域: ARCHITECTURE 分支段 3; 与既有 `SKIP_ADR_GATE=yes` 语义独立, 可组合使用)

### Session Binding Policy (ADR-0017 + spec 2026-07-14)

Every workflow session generated by `rdd-arch`/`guide-plan`/`guide-ship` MUST bind to a rddf-session via `owner_opencode_session_id`. The `guide` recommender surfaces this binding via `BINDING_LINES` (no state mutation). Users running raw skills can check their binding via `skill_use("rddf-session current")`. Manual skill invocation without binding is allowed but the user is responsible for resolving any cross-session conflicts (4-option soft prompt per ADR-0017 §3).

### Skill 文件规范

- 每个 `skills/*.md` 以 YAML frontmatter 开头 (`---` 分隔)
- **顶层字段**: `name`, `description`, `license`, `compatibility`
- **`metadata:` 嵌套字段**: `author`, `version`, `evolved-from`, `user-invocable`
- `version: X.Y` semver, `evolved-from: "..."` 记录重构历史来源
- frontmatter 是**只读**的 — metadata/version/name/user-invocable 不可修改

### 分支与 Worktree

- Branch 命名: `openspec/<change-name>`
- Worktree 路径: `.rddf/wt/<change-name>`
- Plan 文件路径: `.rddf/plans/<name>.md` (git tracked)
- **COMMIT GATE**: `git worktree add` 之前必须 commit — worktree 创建需要看到 artifacts
- 创建 worktree 时必须在 default branch (master/main/develop)
- `find_default_branch()` (在 `skills/_lib/worktree.sh`) 动态检测, 不要硬编码
- `main_repo_root()` 用 `git rev-parse --git-common-dir` 获取主仓库路径 (worktree 安全)
- `main_repo_root()` / `resolve_project_root()` **submodule-aware** (ADR-0033): 在 git submodule 内用 `git rev-parse --show-superproject-working-tree` 检测,优先返回 `git rev-parse --show-toplevel` (submodule 自身根),保留 worktree 分支。**语义**: rddf 把每个 submodule 当独立项目对待 (用户期望就地管理 `.rddf/state/`)。

### ADR 规范

- 命名: `ADR-NNNN-<kebab-slug>.md` (NNNN 4位零填充, 0000 保留为模板)
- 状态生命周期: `待定 → 已采纳 → 已弃用 / 已替代为 ADR-NNNN`
- 引用格式: `ADR-NNN §N.M` (例如 `ADR-0003 §2.1`)
- 模板: `docs/adr/ADR-0000-template.md` (不要给真实 ADR 分配 0000)
- 当前最新编号: **ADR-0035** (verifier-archive-gate boundary, 2026-08-28; `docs/adr/` 取最大值)
- **架构指针 (P1-2 sync, 2026-08-28)**: 较新的关键 ADR 包括 ADR-0023 (rename spec-workflow→rdd-workflow)、ADR-0024 (deps-driven execution mode)、ADR-0025 (design proposal creation)、ADR-0028 (role model per phase)、ADR-0030 (hub-and-spoke federation)、ADR-0033 (submodule-aware)、ADR-0034 (rdd-verifier 5th phase)、ADR-0035 (verifier-archive-gate 双轨边界)。任何 agent 在做架构决策前应至少扫读这三篇。

### 测试约定

- bats `@test` 命名格式: `"模块: 场景描述"`
- 每个 `.bats` 文件顶部 `load test_helper`
- `load_lib <name>` 按序查找: `tests/_lib/<name>.bash` → `skills/_lib/<name>.sh` → `tests/_lib/<name>.sh`
- 辅助断言: `assert_file_exists`, `assert_file_contains`, `assert_cmd_succeeds`
- **Python 测试**: `tests/conftest.py` 把项目根加进 `sys.path`, 因此 `import skills._lib.xxx` 能解析
- Python unit 在 `tests/unit/`, Python integration 在 `tests/integration/` (`test_loop_flow.py`, `test_gate_transition.py`, `test_phase_switch.py`)
- 集成 bats 测试在 `tests/integration/` (45 个)
- CI 有**恒真断言门控**: `grep -rn "assert.*or True\|assert True" tests/` 命中即 CI FAIL

### Worktree Commit Flow (v2.0.5+ 显式规则)

每个 change 在 worktree 内执行时遵循以下三段式流程:

1. **Phase 2 execute**: 修改文件 + 跑测试 + 更新 tasks.md checkboxes (`- [ ]` → `- [x]`)。**不逐任务 commit** (遵循现有约定 — 仓库的 commit 集中在 archive 阶段)。

2. **Phase 2 完成(全部 task 通过后)**: 在 **worktree 内**用 conventional commit message commit working tree:
   - `feat(<scope>): <description>` — 新功能
   - `fix(<scope>): <description>` — bug 修复
   - `refactor(<scope>): <description>` — 重构(无行为变化)
   - `test(<scope>): <description>` — 测试变更
   - `chore(<scope>): <description>` — 工具/基础设施
   - 文档化变更 (`docs(<scope>)`) 视情况归入 `chore` 或 `feat`

   scope 命名参考 `archive-history-keep-semantics` 的 commit `50950c5 feat(rddf-session): add --archive-orphans flag to archive-history` 风格。

2.5. **Post-archive cleanup hook (post-archive-cleanup-hook)** — 在 archive 主体完成后,自动 idempotent 清扫残留(deleted tracked `.rddf/plans/<name>.md` 等 + modified critical `proposal-approved.md`)。详见 `_lib/post_archive_cleanup.sh` 与 `.rddf/improvements/post-archive-cleanup-hook.md`。SKIP via `SKIP_POST_ARCHIVE_CLEANUP=yes`; debug via `DRY_RUN_POST_ARCHIVE_CLEANUP=yes`。

3. **Phase 3 archive**: 由 `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode` 自动 merge → `openspec archive` → cleanup worktree + branch。

> **关键约束**: worktree 分支**必须有 commits 才能 archive** — `_lib/archive.sh::archive_change` 的 `check_worktree_commits` 步骤会检查这一点,无 commits 时拒绝 merge。

### 归档流程 (`guide-ship` Phase 3)

`guide-ship` 归档时自动检测模式:
- **worktree 模式**: 调用 `skills/_lib/archive.sh` 的 `archive_change <name>` 执行 full 归档
- **轻量模式**: 直接在 main repo merge branch + 删除分支 + `openspec archive`

`archive_change` 内部步骤:
1. 找到 worktree path + default branch
2. 检查 worktree 分支是否有新提交 (`check_worktree_commits` — 引用上方 "Worktree Commit Flow" 第 2 步)
3. 切换到 default branch
4. 按是否分叉选择 `--ff-only` 或 `--no-ff` merge
5. 验证 merge 结果 (HEAD 变化或分支是祖先)
6. `openspec archive <name> --yes`
7. 清理 worktree + branch (`-D` 需环境变量 `FORCE_BRANCH_DELETE=yes`)
7.5. 自动 commit archive 文件移动 (见下方 "Archive Auto-Commit")

### Archive Auto-Commit (v2.0.4 新增)

`openspec archive <name> --yes` 移动文件后,`archive.sh::commit_archive_moves <name> <main_root>` 自动 stage + commit:

- **Default ON**:每个 archive 产生 1 个新 commit,subject 为 `archive(<name>): archive completed`(匹配 `0d6ba45 archive(status-guide-revision)` 的 repo convention)。
- **Opt-out**:export `SKIP_ARCHIVE_AUTO_COMMIT=yes` 跳过 helper(适用:用户想手工构造 commit message、或与多个变更合一个 commit)。
- **Idempotent**:已 commit 后再调用,working tree 干净 → 立即 exit 0,无新 commit。
- **Coverage**:在 worktree 模式 (`archive_change`) 和 lightweight 模式 (`guide-ship.md` Phase 3 inline 调用) 都生效。
- **Failure tolerance**:helper 调用是 `|| true` 包裹的。archive 主体成功但 auto-commit 失败时,moves 留在 working tree 供人工处理,不会让 ship 流程整体失败。
- **Strict scope**:helper 只 stage 3 个明确路径 (`openspec/changes/<name>/`、`openspec/changes/archive/`、`openspec/specs/`),**不会**意外 stage 同级其他 dirty 文件。

无需手工 `git add openspec/...` + 手工 commit message 了。

### Ship 阶段 `guide-ship/scripts/ship_*.sh` 提取（v2.0.5 新增，v2.0.8 Phase 2 迁至 per-skill scripts/）

`guide-ship.md` v2.0 起按 Phase 把超过 50 行的内联 bash 块提取为 3 个脚本 (v2.0.8 前在 `_lib/`，Phase 2 重组后迁至 `guide-ship/scripts/`):

| Script | Source Phase | Public functions |
|--------|-------------|------------------|
| `skills/guide-ship/scripts/ship_plan.sh` | Phase 1 (plan) | `check_artifacts_committed`, `detect_execution_mode`, `setup_execution_workspace`, `share_submodules_to_worktree`, `generate_implementation_plan`, `record_iteration_status` |
| `skills/guide-ship/scripts/ship_review.sh` | Phase 2.5 (review) | `handle_review_action` (4-option dispatch) |
| `skills/guide-ship/scripts/ship_archive.sh` | Phase 3 (archive) | `detect_archive_mode`, `check_feature_integrity`, `archive_change_for_mode` |

`guide-ship.md` 由 1361 → 842 行（净减 519 行）。每个 script 都通过 `bats tests/integration/test_ship_*_extraction.bats` 锁定（功能性测试 + 结构性 grep 双保险），遵循 P1-14 archive.sh 提取的同款模式。Phase 2 的 54 行"读取所有 tasks.md 进度"块是后续 P3-3 候选提取目标。

### Guide-Ship 执行契约 (v2.0.7+ 固化)

`tasks.md` 是 OpenSpec 的范围与完成清单;`.rddf/plans/<change>.md` 是 **唯一** 可执行实现契约;`execute` 消费 plan 并把进度回写到 `tasks.md`;`guide-ship` 不直接执行 `tasks.md`。

完整契约见 `docs/superpowers/specs/2026-08-05-guide-ship-execution-contract.md`。要点:

- `guide-ship` Phase 1 通过 `rddf discover-ship-changes` 统一发现候选,单 change 自动选择;多 change 显示菜单。
- `guide-ship::setup_execution_workspace` 通过 `$RDDF_EXECUTION_ROOT` 把选定工作区交给 `execute`,`execute` 不再自行探测。
- `SKIP_PROMETHEUS_PLANNING=yes` 必须配 `QUICK_FINISH_DETECTED=yes` 才能跳过 plan 生成(否则 fail closed)。
- `archive_gate_check` 在 worktree 和 lightweight 两种模式都生效;无 commits 阻断 archive。
- `archive_gate_check` 在 worktree 和 lightweight 两种模式都生效;`archive.sh::archive_change` 路径中调用 `check_worktree_commits`(worktree merge 前);lightweight 模式由 `archive_change_for_mode` 用 `rev-list` 检测新提交且 0 个新提交时硬阻断。

### Python 后端 (v2.0)

`skills/_lib/` 包含完整的 Python 模块:
- `state_vector.py` — 原子化状态持久化 (JSON schema + checksum, < 10ms 读写)
- `event_log.py` — 追加式事件日志 (10K 事件 < 100ms 查询)
- `gate.py` — 插件式质量门控 (error/warning)
- `tribunal.py` — 多 agent 交叉验证 + 加权评分
- `sanitizer.py` — API key/密码/敏感路径脱敏 (< 10ms/次)
- `memory.py` — LoopMemory 历史追踪 + 中断恢复 + 容量归档
- `session_manager.py` — Session 协调器 + 父子 session 追踪
- `agents.py` — Planner/Executor/Verifier 协调
- `detectors.py` / `actions.py` — 8 内置检测器 + 7 内置动作 + 插件机制
- `propose_change.py` (v2.0.6 新增) — Phase 4 状态写入 (实际位置: skills/propose/scripts/propose_change.py)
- `deps_output.py` (v2.0.6 新增 `render_markdown_report`) — Step 5 markdown 报告渲染 (实际位置: skills/deps/scripts/deps_output.py)

### Deps 阶段 `_lib/deps_render_report.sh` 提取（v2.0.6 新增）

`deps.md` Step 5 v2.0.6 起把 160 行内联 PYEOF heredoc 拆分到 `skills/deps/scripts/deps_output.py::render_markdown_report` + `_lib/deps_render_report.sh` bash wrapper (v2.0.8 迁至 `skills/deps/scripts/deps_render_report.sh`):

| Python function | Source lines | Responsibility |
|------------------|--------------|----------------|
| `render_markdown_report` | 483-642 | Generate complete .deps-output.md (header, mermaid, precheck, status, recommended, conflicts, AI) |

| Bash function | Purpose |
|---------------|---------|
| `render_deps_report` | Env-var setup + Python call + mkdir + write to $DEPS_OUTPUT |

`deps.md` 由 786 → 637 行（净减 149 行，-19%）。17 Python unit + 6 bats integration tests 锁定契约。

### Propose 阶段 `_lib/propose_change.{sh,py}` 提取（v2.0.6 新增）

`propose.md` Phase 4 v2.0.6 起把 353 行内联代码拆分到 `_lib/propose_change.py` 5 个函数 + `_lib/propose_change.sh` bash wrapper (v2.0.8 迁至 `skills/propose/scripts/propose_change.{sh,py}`):

| Python function | Source lines | Responsibility |
|------------------|--------------|----------------|
| `set_suggestion_status` | 531-548 | Update proposal-approved.md entry status |
| `create_skeleton_change` | 486-551 | Write proposal.md + roadmap-meta.yaml + iteration.json (planned) |
| `update_roadmap_meta` | 617-686 | Lookup phase/category + ALWAYS fallback to 'general' + write yaml |
| `update_roadmap_state` | 688-711 | Append change to roadmap-state.json via `update_change_count` |
| `update_iteration_proposed` | 713-760 | Sync iteration.json (status=proposed) with env-var safety |

| Bash function | Purpose |
|---------------|---------|
| `propose_create_change <name> --skeleton <phase> <category> <priority>` | Skeleton branch entry |
| `propose_finalize_change <name> <phase> <category> <priority> <valid_categories>` | Full create finalization |

`propose.md` 由 942 → 686 行（净减 256 行，-27%）。21 Python 单元测试 + 9 bats 集成测试锁定契约。

**Known limitation**: The artifact creation loop at original lines 580-608 is HALF-IMPLEMENTED (starts with real bash `openspec status --json` + `jq` for `applyRequires`, but the actual artifact creation body uses pseudo-code `for each artifact_id in artifact_order:` that is not bash). This loop is preserved as-is in propose.md and NOT extracted — see commit history for context.

**Security note**: The new pattern uses env-var passing via `os.environ` instead of bash string interpolation, eliminating Oracle C1's bash string-interpolation injection risk entirely.

### Round A: 6-任务内联 Bash 提取 (v2.0.6 新增)

`skills/*.md` 提取第二批 — 6 个内联 bash 块横跨 4 个 skill 文件 (~580 行) 迁移到 `_lib/`（v2.0.8 Phase 2 重组后迁至各 skill 的 `scripts/` 目录）:

| Task | Skill | Lines | Helper(s) | Tests | 备注 |
|------|-------|-------|-----------|-------|------|
| 1 | `rdd-arch.md` Phase 1 Steps 1-5 | 96 | `rdd-arch/scripts/arch_env_check.sh` | 9 bats | openspec CLI 检查 + 工件发现 |
| 2 | `rdd-arch.md` handoff writer | 88 | `rdd-arch/scripts/write_arch_handoff.{sh,py,env.py}` | 10 unit + 8 bats | 3 文件 env-var pattern |
| 3 | `guide-plan.md` Phase 0 intake | 79 | `guide-plan/scripts/plan_intake.sh` | 7 bats | Oracle C1 fix：去 bash string interp |
| 4 | `guide-plan.md` plan-done gate + handoff | 150 | `guide-plan/scripts/plan_done_gate.{sh,py,env.py}` | 8 unit + 9 bats | 双闸门 + handoff 写入 |
| 5 | `guide-ship.md` Phase 2 monitor | 54 | `guide-ship/scripts/ship_monitor.sh` | 7 bats | P3-3 maintainer-flagged target |
| 6 | `execute.md` worktree auto-detect | 113 | `execute/scripts/select_worktree.sh` | 8 bats | 大块，type-1 helper |
| **总计** | 4 skill files | **580** | **10 helpers** | **66 tests** | 5 修正 commits (review-found bugs) |

**关键 bug 修复**:

- `arch_env_check.sh` (Task 1) — POSIX 尾随换行符 + `local PROJECT_ROOT` 一致性 + 缺失 fallback 测试
- `write_arch_handoff.py` (Task 2) — `glob.glob` 过滤目录 (`os.path.isfile`) + 简化 `import glob` 替代单字符别名
- `plan_intake.sh` (Task 3) — **`SKIP_ARCH_HANDOFF=yes` 是死代码**:原始文档告知用户设置此 env var 但代码从未读取。已 wired 增加回归测试。
- `plan_done_gate.sh` (Task 4) — Gate 0 skip 语义:原始 `exit 0` 终止整个 plan-done 块(防止 handoff 写入);新 `return 0` 仅退出函数——已修复使用 `PLAN_GATE_0_SKIPPED` 哨兵 env var。
- `ship_monitor.sh` (Task 5) — `grep -c || echo 0` 双重输出:零匹配时 grep 输出 `0`,然后 `|| echo 0` 添加另一个零。已修复用 `| head -n1`。
- `select_worktree.sh` (Task 6) — `exit 1` → `return 1` (匹配代码库 59 实例约定) + 移除 `WT_COUNT`/`WORKTREE_COUNT` 双计数
- `write_arch_handoff.sh` (Round A 终审) — **`roadmap_exists` 始终为 false**:env var `ROADMAP_EXISTS_BOOL` 不能跨 `rdd-arch.md` 中两个 bash 代码块传播(AI 代理在独立 shell 调用中执行)。已修复：helper 内部从文件系统直接计算。

**Oracle C1 安全**:Round A 强制使用 env-var 传递模式 (Task 2/4 的 3 文件 split + Task 3 内联 env-var) 消除所有 bash `$VAR` 字符串注入风险。

**提取后总成果 (含 Oracle 7-步优先序列)**:

```
skills/*.md 行数 (累计):
  arch: 962 → 784 (-178)
  plan: 886 → 655 (-231)
  ship: 1361 → 751 (-610)
  execute: 516 → 409 (-107)
  total reduction: ~1100 行
```

新 helpers (Round A 贡献 10 个):
- `rdd-arch/scripts/arch_env_check.sh`, `rdd-arch/scripts/write_arch_handoff.{sh,py,env.py}`, `guide-plan/scripts/plan_intake.sh`, `guide-plan/scripts/plan_done_gate.{sh,py,env.py}`, `guide-ship/scripts/ship_monitor.sh`, `execute/scripts/select_worktree.sh`

合并到 master: 13 commits (1 plan + 6 refactor + 5 review-fix + 1 final-bug-fix)。

### Round B: 10-任务内联 Bash 提取 (v2.0.7 新增)

`skills/*.md` 提取第三批 — 10 个内联 bash 块横跨 4 个 skill 文件 (~480 行) 迁移到 `_lib/`:

| Task | Skill | Lines | Helper(s) | Tests | 备注 |
|------|-------|-------|-----------|-------|------|
| B1 | `rdd-arch.md` gap analysis | 85 | `rdd-arch/scripts/arch_gap_analysis.sh` | 8 bats | generator + viewer |
| B2 | `rdd-arch.md` Phase 5 dual gate | 38 | `rdd-arch/scripts/arch_done_gate.sh` | 6 bats | ADR + roadmap gate |
| B3 | `guide-plan.md` deps-candidates | 38 | `guide-plan/scripts/plan_deps_candidates.{sh,py,env.py}` | 6 unit + 6 bats | **SECURITY FIX**: oracle C1 |
| B4 | `guide-plan.md` queue overview | 50 | `guide-plan/scripts/plan_queue_overview.sh` | 6 bats | 5-state summary |
| B5 | `guide-plan.md` feature progress | 34 | `guide-plan/scripts/plan_feature_progress.sh` | 5 bats | per-feature |
| B6 | `status.md` render_status Mode A | 45 | `status/scripts/status_render_mode_a.sh` | 6 bats | iteration + fallback |
| B7 | `execute.md` tasks writeback | 34 | `execute/scripts/tasks_writeback.sh` | 6 bats | **BUG FIX**: sub() regex issue |
| B8 | `execute.md` roadmap progress | 50 | `execute/scripts/update_roadmap_progress.{sh,py,env.py}` | 7 unit + 6 bats | **SECURITY FIX**: oracle C1 |
| B9 | `execute.md` Step 7 report | 88 | `execute/scripts/execute_step7.{sh,py,env.py}` | 6 unit + 8 bats | final report + sync |
| B10 | `rdd-arch.md` arch-quality-report | 32 | `rdd-arch/scripts/arch_quality_report.sh` | 4 bats | thin wrapper |
| **总计** | 4 skill files | **494** | **14 helpers** | **68 tests** | 2 SECURITY + 1 BUG FIX |

**关键 bug / 安全修复**:

- **B3 SECURITY**: `python3 -c "..."` 内联 `$PROJECT_ROOT` 字符串插值 → 提取到 `_lib/plan_deps_candidates.{sh,py,env.py}` 模式
- **B7 BUG FIX**: `sub()` 正则表达式解释 `[ ]` 字符类导致静默失败 → 改用 `index()` + `substr()` 字面量重建
- **B8 SECURITY**: 同样的 oracle C1 字符串插值 → `_lib/update_roadmap_progress.{sh,py,env.py}` 模式

**提取后总成果 (含 Round A + Round B)**:

```
skills/*.md 行数 (累计):
  arch: 962 → 671 (-291)
  plan: 886 → 564 (-322)
  ship: 1361 → 751 (-610)  [Round A only]
  execute: 516 → 265 (-251)
  status: 566 → 531 (-35)
  total reduction: -1509 行
```

新 helpers (Round B 贡献 11 个):
- `rdd-arch/scripts/arch_gap_analysis.sh`, `rdd-arch/scripts/arch_done_gate.sh`, `rdd-arch/scripts/arch_quality_report.sh`
- `guide-plan/scripts/plan_deps_candidates.{sh,py,env.py}`, `guide-plan/scripts/plan_queue_overview.sh`, `guide-plan/scripts/plan_feature_progress.sh`
- `status/scripts/status_render_mode_a.sh`
- `execute/scripts/tasks_writeback.sh`, `execute/scripts/update_roadmap_progress.{sh,py,env.py}`, `execute/scripts/execute_step7.{sh,py,env.py}`

合并到 master: 11 commits (1 plan + 10 refactor)。

### Round C: feature.md 重构 (v2.0.7 新增)

`skills/feature.md` (183 行) 重构 — 整个文件转写为 4 个 per-subcommand helper + 1 个 Python 模块 (v2.0.8 Phase 2 迁至 `skills/feature/scripts/`):

| Subcommand | Bash helper | Python function |
|-----------|-------------|-----------------|
| `feature [summary]` | `skills/feature/scripts/feature_summary.sh` → `render_feature_summary()` | `skills/feature/scripts/feature_cli.py::render_summary()` |
| `feature graph` | `skills/feature/scripts/feature_graph.sh` → `render_feature_graph()` | `skills/feature/scripts/feature_cli.py::render_graph()` |
| `feature status <name>` | `skills/feature/scripts/feature_status.sh` → `render_feature_status()` | `skills/feature/scripts/feature_cli.py::render_status()` |
| `feature order` | `skills/feature/scripts/feature_order.sh` → `render_feature_order()` | `skills/feature/scripts/feature_cli.py::render_order()` |

**关键改进**:

- **DRY**: 4 个 subcommand 共享 `_load_feature_view()` helper (消除 ~15 行 boilerplate × 4 = 60 行重复)
- **结构清晰**: 每 subcommand 一个文件 (1 .py + 4 .sh + 16 bats tests),而不是 152 行连续 bash
- **Oracle C1 保持**: 原始 `python3 - <<'PYEOF'` (引用型 heredoc) — 已安全,无需修复
- **命令行兼容**: 4 个 subcommand 沿用相同的 `skill_use("feature ...")` 调用方式

**`feature.md` 行数**: 183 → ~45 行 (-75%).

**测试**: 16 bats integration tests (4 × 4 subcommand × 4 维度: helper存在/inline移除/invoke/边界)

合并到 master: 7 commits (1 module + 4 helper + 1 migrate + 1 tests)。

- 配置: `config.py`, `defaults.py`, `phase_templates.yaml`, `schemas/`, `plugins/`

`skills/loop_engine.py` (在 skills/ 根) 是引擎入口 (向后兼容 shim; 实际实现在 `skills/_lib/loop_engine.py`), 串联以上模块.

## rdd-doctor (manual diagnostic skill)

When to invoke `bash skills/rdd-doctor/scripts/doctor.sh` (manual trigger only):
1. After completing a phase, before moving to the next — quick sanity check that no file drift has accumulated
2. After modifying `_lib/schemas/*.json` — verify no `.rddf/state/*.json` files are stuck on the old schema (`--category state`)
3. Before upgrading `STRICT_ARCH_GATE=yes` or `STRICT_DESIGN_GATE=yes` — preview how many issues the strict mode would surface
4. When troubleshooting a workflow that "feels broken" but no specific error is showing

NOT to run rdd-doctor:
- As part of an automated phase entry (v1 is manual only)
- To fix files (doctor is read-only; for fixes use the relevant skill like `rdd-arch` or `guide-plan`)
- To replace any existing gate (`rdd-env-check`, `arch-quality-gate`, etc.)

Flags: `--json` (write `.rddf/state/.doctor-report.json`), `--category <name>` (run only one of 5 categories: `state`, `plan-tdd`, `roadmap-meta`, `proposal-table`, `tasks-checkbox`), `--quiet` (single-line output). Exit codes: 0/1/2/3 matching `openspec validate`.

## 常见陷阱

1. **git worktree list branch 在第 3 列** — `awk '$3 ~ /openspec\//'` (不是 `$2`, 不是 `$4`)
2. **`git show HEAD:<path>` 要求 repo 相对路径** — 先 `cd $PROJECT_ROOT`, 再用相对 glob
3. **`main_repo_root()` vs `git rev-parse --show-toplevel`** — worktree 内必须用 `--git-common-dir`, 否则返回 worktree 根
4. **`find_default_branch()` 不从 worktree 的 HEAD 推断** — 优先读 `refs/remotes/origin/HEAD`, 防 self-merge
5. **Execute 只写 `tasks.md`** — 不写 state 文件, guide 从 tasks.md 同步进度
6. **execute 阶段不逐任务 commit** — 但**必须在 worktree 内做 1 个聚合 commit** 在 archive 之前
   - 详细流程见上方 "Worktree Commit Flow" (3 步: execute → worktree-internal commit → archive)
   - `rdd-workflow-writing-plans` 生成的 plan 默认在 Step 5 不执行 commit；如需逐任务 commit，设置 `COMMIT_IN_EXECUTE=yes`（不推荐）
   - **冲突来源**: AGENTS.md 历史上写"execute 不 commit"但 `_lib/archive.sh::check_worktree_commits` 又要求 commits — 本提案显式规则化解此矛盾
7. **`rdd-arch` 不调用 `guide-plan`** — arch-done 后用户必须手动切换
8. **`guide-spec` 已移除** — v2.0 中删除（原为 60 行别名），请直接使用 `rdd-arch` → `guide-plan`
9. **Loop 引擎 max_iterations: 100, max_retries: 3** — 配置在 `interaction` 模式配置中
10. **proposal-suggestions.md 格式为 Markdown 表格** — 索引到 `.rddf/improvements/*.md`, 用 `list_improvements()` 或 `read_improvement_entries()` 读取, 审查通过后添加到 `proposal-approved.md`
11. **`npm test` 不跑 Python** — 改完 Python 必须手动 `pytest tests/`, CI 才会捕获
12. **`skills/_lib/state.sh` 是共享工具** — 有 6 个活跃函数（safe_python_json, read_suggestions, write_suggestions, count_pending_suggestions 等），被 propose/roadmap/status/plan_queue_overview 调用，不是 STUB
13. **`.bats-tmp/` 在仓库根自动生成** — gitignored, 不要手动 commit
14. **`package.json` 是 npm manifest 而非运行时入口** — `"main": "skills/INSTALL.md"`, 用作 skill 分发元数据
15. **`check_stale_workflow_state` 是 read-only sentinel** — 不写文件、不递归。`scan_state` 在 priority 9/10 default fallback 调用它;若函数挂死,scanner 也会挂死(历史教训:line 220 self-call bug 修复于 2026-07-15 fix-scan-state-recursion)。
16. **manual_deps 人工依赖声明 (ADR-0022)**: `roadmap-meta.yaml` 支持 `manual_deps: [change_name]` 和 `manual_blocks: [change_name]` 字段。deps 分析时人工声明优先于静态分析 — 若 manual_deps 声明 A→B 但静态无证据，标注 "manual override"。详见 ADR-0022。
17. **deps-driven execution mode (ADR-0024)**: 执行模式（lightweight vs worktree）在 plan 阶段的 deps 分析时就决定，并写入 `.plan-handoff.json`。`guide-ship` 的 `detect_execution_mode()` 优先读取 handoff 决策，fallback 到并行冲突检测。决策维度：文件数（≤2 → lightweight）、任务数（≤3 → lightweight）、风险关键词（refactor/migration → worktree）、文件冲突（有冲突 → worktree）。
18. **Scanner state.sh fallback**: `skills/guide/scripts/scan-state.sh` and `guide_entry.sh` first try `$PROJECT_ROOT/skills/_lib/state.sh`, then fall back to `${HOME}/.agents/skills/_lib/state.sh`. If both are missing, a non-blocking stderr warning is printed; stdout and exit code remain unchanged. Do not add symlinks or runtime path resolution.
19. **主题状态词汇 (roadmap-proposal-guidance, v2.2+)**: 
    | 状态 | 含义 | coverage 分母 |
    |------|------|---------------|
    | `未覆盖` | roadmap 定义但无 proposal 匹配 | 计入 |
    | `已覆盖` | 至少一个 proposal 的 `**主题**:` 字段精确匹配 | 不计入 |
    | `~skipped~` | 用户显式标记豁免 (在 cell 末尾追加 `~skipped~`) | 不计入 |

    由 `_lib/roadmap_state.py::get_phase_themes()` 解析,由 `guide-design/scripts/design_preflight.py::compute_theme_coverage()` 计算。
20. **env-var 命名规范 (Oracle C1)**: 
    - 所有 add-improve/brainstorm 间传参 env-var MUST 大写蛇形: `ADD_IMPROVE_FROM_ROADMAP`, `ADD_IMPROVE_THEME`, `BRAINSTORM_RATIONALE_DRAFT`
    - 调用结束 MUST `unset` env-var (避免污染 shell),用 `trap cleanup EXIT`
    - 禁止 `python3 -c "...$VAR..."` 内联 bash 字符串插值
    - 详见 `skills/add-improve/scripts/from_roadmap.env.py` 校验逻辑
21. **STRICT_PROPOSAL_COVERAGE 门控 (v2.2+)**: 
    - 默认 OFF (warning only) — `guide-design` Phase 1 preflight 显示未覆盖主题但允许通过
    - `STRICT_PROPOSAL_COVERAGE=yes` 升级为严格阻断 (与 `STRICT_DESIGN_GATE` 模式对齐)
    - `SKIP_PROPOSAL_COVERAGE=yes` 临时绕过 (紧急情况)
    - 由 `skills/guide-design/scripts/check_theme_coverage_gate.sh` 执行
22. **roadmap 增量 state 隔离**: 切分支/切 worktree 后第一次 arch-done 自动 fallback full (per-worktree `.rddf/state/` 隔离；state 绑 codebase_commit)
23. **codegraph signal 必须 env-var 注入**: Python subprocess 上下文无法访问 MCP session — populate_lib 内部**禁止**调 MCP；agent 侧通过 `RDDF_CODEGRAPH_FINGERPRINT` env var 注入 signal
24. **reset roadmap 增量 state**: `rm .rddf/state/.populate-state.json` (无 baseline → 下次 full)；用于分支切换残留、codegraph 索引陈旧、人工强制全量
25. **`_lib/` vs `skills/_lib/` 双路由 (P1-1b, 2026-08-25)**: 真实代码在仓库根 `_lib/`；`skills/_lib/` 是 shim 层 (15 个 6 行 bash shim 优先本地路径、10 个 identity-merge Python shim、若干 path-widening `__init__.py`)。`import skills._lib.X is _lib.X` 为 True（10 个迁移模块已锁定，详见 `tests/unit/test_p1_1_identity_merge.py`）；其余子模块身份仍分裂（已记入 P2 follow-up）。新增代码 **必须 import `_lib.X`** (canonical, 真正实现)，历史 `skills._lib.X` 调用继续兼容。

## 前置条件

- `openspec` CLI v1.3.1+ (package.json `engines.openspec-cli`)
- `git` 2.25+
- `cmake` 3.16+ (来自 README; 本仓库不直接调用 cmake, 可能仅作为上游约束)
- `bats-core` 1.10+ (可选, 用于跑 bats 测试)
- Python 3.11+ (v2.0 Loop 引擎 + 单元测试, CI 固定 3.11)

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
| ------ | ---------- |
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
