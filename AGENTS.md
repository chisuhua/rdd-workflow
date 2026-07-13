# AGENTS.md — spec-workflow

> OpenSpec 工作流技能包: `propose → plan → execute → status → archive` change lifecycle.
> v2.0 self-contained: 内置 TDD 5 步计划生成与执行, 无外部 skill 依赖.

## 快速命令

```bash
# Bats (shell) 测试 — npm test 只跑这一类
npm test                                # bats tests/ (全量 bats)
bats tests/smoke.bats                   # 快速冒烟 (7 个 smoke cases)
bats tests/_lib/test_skill.bats         # skill.bash parser (8 cases)

# Python 测试 — npm test 不会跑, 必须显式调用
python3 -m pytest tests/unit/ -q --tb=short          # ~46 个 unit 文件 (含 v2.0.1 新增: test_iteration / test_roadmap_sprint / test_deps_output / test_rddf_session / test_arch_handoff_schema / test_discover_arch_artifacts / test_arch_quality_gate / test_change_alignment / test_iteration_concurrency 等)
python3 -m pytest tests/integration/ -q --tb=short   # ~9 个 Python integration (.py, 含 loop / gate / phase_switch / iteration_lifecycle / iteration_archive_hook / guide_ship_iteration_hook / deps_analysis / hook_boundary / trigger_e2e)
pip install -r requirements.txt                      # PyYAML, jsonschema, pytest
```

CI 在 `.github/workflows/test.yml`, 按序执行: 安装 deps → **断言质量门控** → Python unit → Python integration → bats smoke → bats static 子集 → bats git-worktree 子集.

> **重要**: `npm test` 只跑 bats, **不会**捕获 Python 测试失败. 改完 Python 后必须手动 `pytest tests/`.

## 架构

**三阶段架构** (ADR-0003): `arch → plan → ship`

| 阶段 | Skill | 职责 |
|------|-------|------|
| arch | `guide-arch` | 架构定义: ADR, 差距分析, roadmap |
| plan | `guide-plan` | 变更生成: scan, propose, deps |
| ship | `guide-ship` | 变更执行: worktree/轻量, execute, archive, cleanup |

`guide-ship` 自动检测并行冲突:
- 无其他 worktree **且** 仅此一个 change → ⚡ **轻量模式** (创建 branch, 直接在主仓库执行, 跳过 worktree)
- 有活跃 worktree **或** 多个 change → 🔀 **worktree 模式** (创建隔离 worktree)

`guide-spec` 已在 v2.0 移除（原为 60 行别名，内部按序调用 `guide-arch` → `guide-plan`）。请直接使用 `guide-arch` 和 `guide-plan`。
`guide` 是无状态推荐器, 扫描项目状态推荐下一步, 不写文件, 不调 openspec CLI.

## 关键目录

```
skills/                       # Markdown skills (13 个 .md) + loop_engine.py 在根目录
  INSTALL.md                  # 第一入口 (v1.1.0)
  guide.md                    # 推荐器
  guide-arch.md               # arch 阶段 (v1.0)
  guide-plan.md               # plan 阶段 (v1.0)
  guide-ship.md               # ship 阶段 (v2.0) - 包含 v2.0.1 iteration.json hook (创建 worktree 后切 status=in_worktree)
  propose.md / execute.md / status.md / roadmap.md / deps.md / feature.md / rddf-session.md
  spec-workflow-writing-plans.md  # 内置 TDD 5 步 plan 生成器 (v1.0, 自包含)
  loop_engine.py              # v2.0 Loop 引擎入口 (在 skills/ 根, 不在 _lib/)
  _lib/                       # 共享 bash + Python (37 个文件, v2.0.1)
    state.sh                  # ⚠️ STUB (无 production 调用方, 消费者改用 jq/python3 inline)
    worktree.sh / archive.sh  # bash 工具
    state_vector.py / event_log.py / gate.py / tribunal.py / memory.py / session_manager.py
    agents.py / detectors.py / actions.py / sanitizer.py / ...
    iteration.py              # v2.0.1 NEW: 当前 sprint 状态 (.rddf/state/iteration.json)
    deps_output.py            # v2.0.1 NEW: 结构化 deps 输出 (.rddf/state/deps-analysis.json)
    roadmap_sprint.py         # v2.0.1 NEW: roadmap.md AUTO-SPRINT sentinel 渲染器
    schemas/                  # JSON Schema for state files (含 iteration_schema.json, deps_analysis_schema.json)
tests/
  test_helper.bash            # load_lib 解析器 + 断言辅助
  conftest.py                 # 把项目根加进 sys.path (让 `import skills._lib.*` 可解析)
  smoke.bats                  # 基础设施冒烟 (注意: 硬编码 9 个 skill 路径, 已过时)
  unit/                       # ~46 个 Python 单元测试 (含 v2.0.1 新增: test_iteration, test_roadmap_sprint, test_deps_output, test_rddf_session, test_arch_handoff_schema, test_discover_arch_artifacts, test_arch_quality_gate, test_change_alignment, test_iteration_concurrency 等)
  integration/                # ~58 个集成测试 (49 .bats + 9 .py; 含 v2.0.1 新增: test_iteration_lifecycle, test_iteration_archive_hook,
                             #                                                              test_guide_ship_iteration_hook, test_deps_analysis)
  _lib/                       # bash helpers (skill.bash, deps-subagent.bash 等)
docs/adr/                     # ADR-0000 模板 + ADR-0001~0019 (19 个唯一编号 / 20 个实体文件; **ADR-0013 重复**: extract-scan-state + incremental-skeleton-planning)
                             # 关键 ADR: ADR-0003 三阶段架构 / ADR-0010 多会话管理 / ADR-0017 rddf-session / ADR-0018 arch 质量门 / ADR-0019 change-arch-alignment
openspec/                     # OpenSpec CLI 数据 (随项目走)
  changes/                    # active changes + archive/
  specs/                      # 已采纳的 capability specs (25 个)
```

## 关键约定 (容易踩坑)

### 状态文件 (`.rddf/state/`, gitignored)

| 文件 | 用途 | 写入方 |
|------|------|--------|
| `.rddf/state/.arch-handoff.json` | arch→plan 交接 + **ADR-0016 发现契约** v1 (adr_dir/roadmap_path/architecture_dir/adr_pattern/discovered/version) | `guide-arch` (arch-done) / `guide-plan` (Phase 0 intake) + `propose`/`roadmap`/`gate.py`/`detectors.py`/`actions.py`/`scan-state.sh` (handoff readers, fallback to defaults) |
| `.rddf/state/plan-handoff.json` | plan→ship 交接 | `guide-plan` (plan-done 写入) / `guide-ship` (ship-start 读取) |
| `.rddf/state/handoff.json` | spec→ship 软交接 | `guide-plan` / `guide-ship` |
| `.rddf/state/sessions.json` | **rddf-session 生命周期** (ADR-0017) — 跨 OpenCode session 工作流恢复 | `guide-arch`/`guide-plan`/`guide-ship` 入口 + `rddf-session` skill 5 子命令 |
| `.rddf/state/deps-analysis.json` | **结构化** deps 输出 (v2.0.1) | `deps` Step 5b 优先写; Step 6 markdown-fallback 时也写 |
| `.rddf/state/deps-candidates.json` | deps 候选列表 | `guide-plan` (deps 阶段) |
| `.rddf/state/deps-output.md` | deps 人类可读报告 | `deps` Step 5 |
| `.rddf/state/iteration.json` | **当前 sprint 视图** (v2.0.1) | propose/guide-ship/execute/deps/archive hooks |
| `.rddf/state/roadmap-state.json` | roadmap 阶段/category 计数 | `propose` (status 改时) |
| `.rddf/state/index.md` | change 索引 | `guide-arch` / `guide-plan` |
| `.rddf/state/.deps-output.md` | deps 旧路径 (开头有 `.`) | `deps` Step 5 (兼容保留) |

`.rddf/state/`, `.rddf/wt/`, `.rddf/detectors/`, `.rddf/actions/` 全部 gitignored;
`.rddf/plans/` **随 git 版本控制** (执行契约路径).
`iteration.json` 是 **多 hook 写入**的 view 文件, 由 `skills/_lib/iteration.py` 集中管理;
`deps-analysis.json` 同样是 view 文件, 由 `skills/_lib/deps_output.py` 管理.
两者 schema 在 `skills/_lib/schemas/` 下, 改 schema 必须 bump version 字段.
`proposal-suggestions.md` 在项目根目录, 随 git 版本控制, 格式为 **JSON 数组** (用 `json.load()`, 不用 grep).

### Arch Discovery Contract (ADR-0016)

`guide-arch` Phase 1 setup 通过 `skills/_lib/discover-arch-artifacts.sh` 扫描项目布局,
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

### ADR 规范

- 命名: `ADR-NNNN-<kebab-slug>.md` (NNNN 4位零填充, 0000 保留为模板)
- 状态生命周期: `待定 → 已采纳 → 已弃用 / 已替代为 ADR-NNNN`
- 引用格式: `ADR-NNN §N.M` (例如 `ADR-0003 §2.1`)
- 模板: `docs/adr/ADR-0000-template.md` (不要给真实 ADR 分配 0000)
- 当前最新编号: ADR-0012 (`docs/adr/` 取最大值)

### 测试约定

- bats `@test` 命名格式: `"模块: 场景描述"`
- 每个 `.bats` 文件顶部 `load test_helper`
- `load_lib <name>` 按序查找: `tests/_lib/<name>.bash` → `skills/_lib/<name>.sh` → `tests/_lib/<name>.sh`
- 辅助断言: `assert_file_exists`, `assert_file_contains`, `assert_cmd_succeeds`
- **Python 测试**: `tests/conftest.py` 把项目根加进 `sys.path`, 因此 `import skills._lib.xxx` 能解析
- Python unit 在 `tests/unit/`, Python integration 在 `tests/integration/` (`test_loop_flow.py`, `test_gate_transition.py`, `test_phase_switch.py`)
- 集成 bats 测试在 `tests/integration/` (45 个)
- CI 有**恒真断言门控**: `grep -rn "assert.*or True\|assert True" tests/` 命中即 CI FAIL

### 归档流程 (`guide-ship` Phase 3)

`guide-ship` 归档时自动检测模式:
- **worktree 模式**: 调用 `skills/_lib/archive.sh` 的 `archive_change <name>` 执行 full 归档
- **轻量模式**: 直接在 main repo merge branch + 删除分支 + `openspec archive`

`archive_change` 内部步骤:
1. 找到 worktree path + default branch
2. 检查 worktree 分支是否有新提交
3. 切换到 default branch
4. 按是否分叉选择 `--ff-only` 或 `--no-ff` merge
5. 验证 merge 结果 (HEAD 变化或分支是祖先)
6. `openspec archive <name> --yes`
7. 清理 worktree + branch (`-D` 需环境变量 `FORCE_BRANCH_DELETE=yes`)

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
- 配置: `config.py`, `defaults.py`, `phase_templates.yaml`, `schemas/`, `plugins/`

`skills/loop_engine.py` (在 skills/ 根) 是引擎入口, 串联以上模块.

## 常见陷阱

1. **git worktree list branch 在第 3 列** — `awk '$3 ~ /openspec\//'` (不是 `$2`, 不是 `$4`)
2. **`git show HEAD:<path>` 要求 repo 相对路径** — 先 `cd $PROJECT_ROOT`, 再用相对 glob
3. **`main_repo_root()` vs `git rev-parse --show-toplevel`** — worktree 内必须用 `--git-common-dir`, 否则返回 worktree 根
4. **`find_default_branch()` 不从 worktree 的 HEAD 推断** — 优先读 `refs/remotes/origin/HEAD`, 防 self-merge
5. **Execute 只写 `tasks.md`** — 不写 state 文件, guide 从 tasks.md 同步进度
6. **execute 阶段不 commit/push** — commit 留到 archive 阶段
7. **`guide-arch` 不调用 `guide-plan`** — arch-done 后用户必须手动切换
8. **`guide-spec` 已移除** — v2.0 中删除（原为 60 行别名），请直接使用 `guide-arch` → `guide-plan`
9. **Loop 引擎 max_iterations: 100, max_retries: 3** — 配置在 `interaction` 模式配置中
10. **proposal-suggestions.md 格式为 JSON** — 用 `json.load()` 解析, 不用 grep (避免 description 字段误匹配)
11. **`npm test` 不跑 Python** — 改完 Python 必须手动 `pytest tests/`, CI 才会捕获
12. **`skills/_lib/state.sh` 是 stub** — 无 production 调用方, 需要时直接用 `jq` / `python3` inline
13. **`.bats-tmp/` 在仓库根自动生成** — gitignored, 不要手动 commit
14. **`package.json` 是 npm manifest 而非运行时入口** — `"main": "skills/INSTALL.md"`, 用作 skill 分发元数据

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
