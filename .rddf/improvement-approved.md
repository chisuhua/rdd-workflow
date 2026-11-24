# 已批准提案（Plan 阶段输入）

> plan 阶段输入。guide-design 批准后直接落盘 `openspec/changes/<name>/proposal.md`，并写入本索引。guide-plan intake 按链接打开对应 `.rddf/improvements/<name>.md`，并通过 `.rddf/state/.design-handoff.json` v2 的 `changes_pre_created` 数组跳过已落盘的 change（Path A）。

> **supersedes** (2026-07-28): 原始设计（propose Phase 4 自动末尾 + 写 `.rddf/state/propose-review.json`）已被后续 commits 修订：
> - `b4ad917` — relocate to arch Phase 5.5 human-in-loop 节点（**历史**：v2.1+ 已迁移至 guide-design Phase 3，详见 ADR-0025）
> - `a99017b` — refine wording `修复` → `修订`（关联提案 add-change-content-review）
> - 当前最终设计（**已更新** v2.1+，ADR-0025）：`guide-design` Phase 3 拥有 suggestions→approved 迁移的 y/n/d/s 决策；批准动作直接落盘 `openspec/changes/<name>/proposal.md`（Path A，详见 move-proposal-creation-to-design 提案）。Oracle 终端展示 3 级报告（pass/warn/block），不持久化。已实现的孤儿 `skills/_lib/propose_content_review.py` 已删除（`311d497`）。

## 已批准提案

| 提案 | 优先级 | 批准时间 | 批准者 |
|------|--------|----------|--------|

> **批次说明 (2026-11-16 rdd-planner, 第八批)**: 本批 5 项为 `rddf-layout-manifest`（第七批，同日归档）验收/归档过程暴露的产品侧缺陷（原 9 条 follow-up，合并同类 + 撤回 1 条误报）：
> 1. **`fix-p3-verifier-gate`** (P1) — `phase3_archive.sh:26-32` 检查不存在的 `verifier_run.sh` ⇒ 预调用恒跳过，`VERIFIER_EXIT` 初值 0 被当作「验收通过」；且 `run_verification.sh` 是 staging 脚本（`Exit 0 = agent 待验证`），改名也修不好。改为调用既有 `_lib/archive.sh:360-556 archive_gate_check`，并修 `openspec_tracked=false` 分支（`:612-620` 提前 `return 0`，早于 `:629` 的 gate ⇒ 本仓归档路径没有 AC 门）
> 2. **`fix-phase3-cleanup-wiring`** (P1) — `post_archive_cleanup.sh` 155 行只有函数定义、无脚本入口；`phase3_archive.sh:101` 用 `bash` 执行它 ⇒ 函数从未运行（实测零输出 exit 0），`2>/dev/null` 再吞掉一切。原判「参数顺序反」不是症状来源；库被直接执行时改为 fail loud
> 3. **`fix-worktree-archive-path`** (P1) — phase3 在 worktree 里跑 `openspec archive`；本仓 `openspec_tracked=false` 且 `openspec/` 整树 gitignored，worktree 里是普通拷贝 ⇒ 记录与 spec 合流随 worktree 清理丢失。`archive_change` 的 false 分支（回主仓归档）本就正确但被绕过。附 worktree/lightweight × tracked 四格矩阵 + lightweight 已知缺口
> 4. **`register-change-in-iteration`** (P2) — `sync_iteration_after_archive` / `force_mark_archived` 只更新已存在条目，全仓无创建时注册路径；实测未注册 change 的 `rddf status` 返回 `not found`、归档 iteration 回写被跳过。`store.set_status` 本就支持创建 ⇒ 只补调用者，不新建模块
> 5. **`fix-flow-drift-batch-1`** (P2) — `SKILL.md:155` 段头正则缺 `Acceptance`（实现 `protocol.py:34` 已有 ⇒ doc drift，非运行时缺陷）；`layout_check.py:126` 给 file 条目也加尾斜杠（实测 `create .rddf/roadmap.md/`）；`rdd_verify_cmd.py:410` 的 `_migrate_legacy_state` 在 dry-run 判断前无条件执行（fixture 实测真移动文件）
>
> **撤回记录**: 原 F-1「`rdd-verifier` 不认 `## Acceptance` ⇒ 假阴性跳过验收」撤回 —— 实测 staged context `ac_count: 18`，`protocol.py:34` 已支持该段头；原判断读取了错误的 dict key（`acceptance_criteria`，实际为 `acs`）。其残余（SKILL.md 文档正则漂移）并入第 5 项
>
> **审稿记录**: metis 1 轮（2026-11-16，5 份合并一次调用，每份 1 轮在预算内）。4 处 P0 全部采纳并重写草案：① F-9 根因纠偏（库无脚本入口被 `bash` 执行，非参数顺序）；② 删除 D1 的重复实现、改调既有 `archive_gate_check`；③ D3 补模式矩阵 + lightweight 出口（`archive_change` 要求 worktree 存在）；④ D4 的 AC 口径纠偏（`roadmap-feature` CRITICAL 判据与 `changes[]` 无关，实测不受影响）。其余 P1/P2 finding 的逐条处置见各提案「## 审稿记录」段。planner 未开第二轮（预算 1 轮/improvement）
>
> **依赖说明**: `fix-worktree-archive-path` 必须在 `fix-p3-verifier-gate` **之后**实施 —— 前者把归档交给 `archive_change`，后者的 `openspec_tracked=false` 分支补门若未落地，门会被 `archive_change` 的提前 `return 0` 绕过。其余三项相互独立
>
> **实施建议**: 三项 P1 均走 rdd-builder 完整流程（每项 > rdd-quick 阈值 per ADR-0047）。建议顺序：`fix-p3-verifier-gate` → `fix-worktree-archive-path` → `fix-phase3-cleanup-wiring` → `register-change-in-iteration` → `fix-flow-drift-batch-1`（前两项改同一段代码，先 gate 后路径；cleanup 项与归档路径无硬顺序，但合并验证更省）
>
> **重叠检查**: 与 `archive-iteration-sync` / `fix-archive-iteration-sync` / `harden-archive-iteration-sync` 不重叠 —— 本批只补「创建时注册」与「归档 sync 可达性」，不改 sync 本体；与 `post-archive-cleanup-hook` 不重叠 —— 本批只修「库被当脚本执行」与 source 静默，不改 cleanup 清单

> **批次说明 (2026-11-16 rdd-planner, 第七批)**: 本批 1 项 rddf-layout-manifest 为 `.rddf/` 布局建立单一机读真源（消费方提问触发）：
> 1. **`rddf-layout-manifest`** (P1) — `.rddf/` 的「有哪些条目、谁读谁写、是否入库」无单点真源：ADR-0026 已定义 `runtime-only`/`committed` 二分但无机器可执行形态；路径常量仅 `_lib/core/defaults.py:24-32` 的 2 条 DEFAULTS + `:67-71` 的 5 个模块常量；散文只覆盖 handoff 三文件与 `detectors/`/`actions/`；doctor 24 个 category 无布局类（`SKILL.md:4` 仍写「13 file categories」）。修复策略：新增 `_lib/core/rddf_layout.py` 单一清单（`path`/`kind`/`read_by`/`write_by`/`required_when`/`transient`/`class`/`severity`）+ 只读子命令 `rddf layout --json`（清单出口，带 `schema_version`/`tool_version`，无时间戳 ⇒ 字节确定）+ doctor `layout` category（诊断出口，三支判据，只扫一层，永不 CRITICAL）+ `docs/architecture/rddf-layout.md`（表格 + 新增条目三步 + 文件级一节，以代码为源）
>
> **审稿记录**: metis 1 轮（`.rddf/reviews/rddf-layout-manifest-planner-review.md`，13 条 finding 全部采纳）+ build 侧证据核对 1 轮（`.rddf/reviews/rddf-layout-manifest-builder-review.md`，4 BLOCKER + 9 SHOULD_FIX 全部处置）。BLOCKER 处置要点：① 清单出口独立为 `rddf layout --json`，不改共享 `doctor_render.py`（其 `timestamp` 与 24 个 category 的 JSON 契约保持不变）；② 目录条目 ignore 判定改用 `<path>/.probe` 探针（目录含 tracked 文件时 `git check-ignore <dir>/` 假红）；③「文件级」一节改以代码为源，并本次一并修 `state-and-events.md` 的 v3 遗留 handoff 表
>
> **依赖说明**: 无。消费方（opencode-config 的 `workspace.json`）属外部工具私有，不进本清单
>
> **实施建议**: 走 rdd-builder P0-P3 完整流程（7 新增文件 + 7 改动文件 > rdd-quick 阈值 per ADR-0047）。轻量模式（无 worktree，直接 master commit）。`openspec/changes/<name>/proposal.md` 由 rdd-builder P0 生成
>
> **重叠检查**: 与 `add-skills-lib-api-doc`（P2，`skills/_lib/` API 文档化）不重叠 —— 本项只覆盖 `.rddf/` 布局面，不涉及 `skills/_lib/` helper 目录；与 `fix-skill-manifest-drift`（done）不重叠 —— 后者治 skill 清单漂移，本项治 `.rddf/` 布局漂移，机制同源但对象不同
>
> **立项期已知状态（非本项缺陷，rdd-builder P0 后自愈）**: `rddf doctor --category roadmap-feature` 报 1 条 CRITICAL —— `iteration.json feature_view missing active feature 'feat-rddf-layout-manifest'`。根因：`feature_view.features` 由 `iteration.json::changes[]` 按 `parent_feature` 派生（`skills/feature/scripts/feature_view.py:294-330`），而 `feat-rddf-layout-manifest` 名下尚无 change（change 由 rdd-builder P0 创建并注册）。feature fragment 的合法状态只有 `active`/`done`/`archived`（`_lib/roadmap_state.py:610,971`），无 `proposed` 可用 ⇒ 「active 且零 change」必然触发该 CRITICAL。**处置**：保持 `status: active`，待 rdd-builder P0 注册 change 后由 `rddf feature` 自动补齐。已记为待立项的 follow-up（checker 未容忍「active feature 尚无 change」这一过渡态）

> **批次说明 (2026-09-28 rdd-planner, 第六批)**: 本批 1 项 consolidate-resolve-project-root-helpers 为 fix-skill-layer-resolution-bash (P3, 已 ship commit 1bcb8a0) 实施审计时识别的跨语言漂移风险:
> 1. **`consolidate-resolve-project-root-helpers`** (P3) — bash + Python 双语言 helper 现为独立实现,无共享 contract → 行为可能漂移 (如 bash helper 未来支持 RDDF_PROJECT_ROOT override 而 Python 不知道)。修复策略: 单一 contract YAML 文件 (`skills/_lib/_resolve_project_root_contract.yaml`) 定义 4 个 invariant (env override / git probe / cwd fallback / function signature),双语言 helper 都从 contract 推导。比 codegen 更轻量 (不引入 build step),用约束 test (3 impl × 4 invariant = 12 cases) 确保未来修改不破坏 invariant
>
> **依赖说明**: skills/_lib/orchestrator_entry.sh::_resolve_project_root (shipped), skills/_lib/_python_resolve_project_root.py::resolve_project_root (shipped commit 281423d), _lib/cli/__main__.resolve_project_root (per ADR-0033)
>
> **实施建议**: 走 rdd-builder P0-P3 完整流程 (4 files > rdd-quick 阈值 ≤ 2 files per ADR-0047: 1 contract + 2 test files)。轻量模式 (无 worktree,直接 master commit)
>
> **重叠检查**: 无 (新 contract 文件 + 2 新 test files)。3 个 impl 不重写 (per MN-CRP-1,只加约束 test)。与 add-skills-lib-api-doc (P2 proposal) 互补 — 前者是 contract,后者是 docs

> **批次说明 (2026-09-27 rdd-planner, 第五批)**: 本批 1 项 fix-skill-layer-resolution-bash 为 add-skill-layer-resolve-project-root-helper (P2, 已 ship commit 281423d) 实施审计时识别的 bash-side counterpart:
> 1. **`fix-skill-layer-resolution-bash`** (P3) — `skills/rdd-arch/scripts/roadmap_incremental_update.sh:25-33` 手动重新实现 `RDDF_PROJECT_ROOT` env check + git probe fallback,而不调用 `skills/_lib/orchestrator_entry.sh:33` 的现有 bash helper `_resolve_project_root`。修复策略:让该 script 用现有 bash helper,与 Python wrapper 形成双语言对称(5 Python + 3 bash scripts 共用 source of truth)。**澄清 user 描述**: `RDDF_HUB_REPO` 等只在 Python scripts 用,bash 0 hits (grep 验证)
>
> **依赖说明**: skills/_lib/orchestrator_entry.sh::_resolve_project_root (existing), add-skill-layer-resolve-project-root-helper (shipped commit 281423d)
>
> **实施建议**: 走 rdd-quick 旁路 (2 files + 3 tasks 符合 ADR-0047 ≤ 2 + ≤ 3 阈值)。轻量模式 (无 worktree,直接 master commit)
>
> **重叠检查**: 无 (单一 file refactor + 3-case bash test)

> **批次说明 (2026-09-27 rdd-planner, 第四批)**: 本批 1 项 add-skill-layer-resolve-project-root-helper 为 fix-skill-layer-project-root-anti-pattern (P2, 已 ship commit c217cde) 实施审计时识别的 layering violation:
> 1. **`add-skill-layer-resolve-project-root-helper`** (P2) — 5 个 skill scripts 在 fix-skill-layer 实施后都 `from _lib.cli.__main__ import resolve_project_root`(绕开 skills/_lib/),违反 skill layer 自包含约定 (per `skills/_lib/iteration/__init__.py:3-10`)。修复:在 `skills/_lib/_python_resolve_project_root.py` 加 Python wrapper(行为 parity delegate 到 `_lib.cli.__main__.resolve_project_root`),5 个 scripts 改 import 路径。**与 bash 对齐**:bash `_resolve_project_root` 已在 `skills/_lib/orchestrator_entry.sh:33`,Python 端补对应 wrapper 实现双语言对称
>
> **依赖说明**: fix-skill-layer-project-root-anti-pattern (shipped commit c217cde), bash `_resolve_project_root` (existing), `_lib.cli.__main__.resolve_project_root` (per ADR-0033)
>
> **实施建议**: 走 rdd-builder P0-P3 完整流程 (6 files > rdd-quick 阈值 ≤ 2 files per ADR-0047)。机械化 sed 替换 + 新单元测试覆盖 submodule/worktree/非-git edge cases + bash parity test
>
> **重叠检查**: 无 (新 wrapper module + 5 import path 改 + 新 test file)。不修改 `_lib.cli.__main__.resolve_project_root()` (per MN-SLP-3), 不重命名函数 (per MN-SLP-1), 不修改 bash `_resolve_project_root` (per MN-SLP-4)

> **批次说明 (2026-09-26 rdd-planner, 第三批)**: 本批 1 项 fix-skill-layer-project-root-anti-pattern 为 fix-33-handlers-project-root-anti-pattern (P2, 已 ship commit ab5ded7) 显式 scope-out 的 follow-up:
> 1. **`fix-skill-layer-project-root-anti-pattern`** (P2) — 5 个 `skills/*/scripts/*.py` skill scripts 仍用 `os.getcwd()` 作为 project_root fallback (`propose_quality_check.py` + `propose_quality_hook.py` 用 `PROJECT_ROOT` env var; `report_issue_rfc.py` + `sync_hub.py` + `watch_hub.py` 用 `RDDF_PROJECT_ROOT`)。Skill layer 完全不用 `_lib.cli.__main__.resolve_project_root()` (0 hits grep)。关键发现:skill layer 用 env var 双轨制(`PROJECT_ROOT` 来自 bash scripts,`RDDF_PROJECT_ROOT` 来自 Python `__main__.py:203` setdefault)。修复策略保留双轨制 (不重命名 env var),只把 `os.getcwd()` 替换为 `resolve_project_root()` (env var override 优先)
>
> **依赖说明**: fix-33-handlers-project-root-anti-pattern (shipped)
>
> **实施建议**: 走 rdd-builder P0-P3 完整流程 (6 files > rdd-quick 阈值 ≤ 2 files per ADR-0047)。机械化 sed 替换 + 新单元测试覆盖 submodule/worktree/非-git edge cases。轻量模式 (无 worktree,直接 master commit)。Bash scripts 已正确 (`skills/_lib/orchestrator_entry.sh:33` 已有 `_resolve_project_root` helper),不需要改
>
> **重叠检查**: 无 (refactor + 新 test file)。不改 env var 名 (per MN-SL-1 双轨制向后兼容), 不改 bash scripts (per MN-SL-2), 不改 `resolve_project_root()` 本身 (per MN-SL-3)

> **批次说明 (2026-09-25 rdd-planner, 第二批)**: 本批 1 项 fix-33-handlers-project-root-anti-pattern 为 fix-cmd-help-handling (P1, 已 ship commit 200efdd) 实施审计时识别的 follow-up architectural debt:
> 1. **`fix-33-handlers-project-root-anti-pattern`** (P2) — 32 个 `_lib/cli/*.py` handler 文件重复使用 `os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()` 反模式 (~36 处 occurrences),而 `_lib/cli/__main__.py::resolve_project_root()` (per ADR-0033 submodule-aware git 探测) 已实现但**无 handler 使用**。这是 fix-cmd-help-handling 的根因层修复 (dispatcher-level 拦截只解决了 e2e test 6 symptom,32 handler 业务逻辑仍用 anti-pattern:在 git submodule / worktree 内执行时 cwd 解析错误)。修复策略: `_lib/cli/__init__.py` re-export `resolve_project_root` 单点引用 + 32 handler 把 `RDDF_PROJECT_ROOT or os.getcwd()` 改为 `RDDF_PROJECT_ROOT or resolve_project_root()` (保留 env override 向后兼容)
>
> **依赖说明**: fix-cmd-help-handling (shipped)
>
> **实施建议**: 走 rdd-builder P0-P3 完整流程（32 文件 > rdd-quick 阈值 ≤ 2 文件 per ADR-0047）。机械化 sed 替换 + 单点 re-export + 新单元测试覆盖 submodule/worktree/非-git edge cases。轻量模式（无 worktree,直接 master commit）
>
> **重叠检查**: 无 (refactor + 新 test file)。不修改 `resolve_project_root()` 本身 (per MN-PR-1), 不改 `__main__.py:203` 的 `setdefault` (per MN-PR-2 backward compat)

> **批次说明 (2026-09-25 rdd-planner)**: 本批 1 项 fix-cmd-help-handling 为 rdd-workflow-e2e PR #1 merge (commit 6628bb1) 后 CI regression audit (2026-09-25) 暴露的主仓 CLI 契约 bug:
> 1. **`fix-cmd-help-handling`** (P1) — 36 个 `rddf <sub>` 中 2 个 `--help` 违反 argparse 标准契约 (`rddf contract-check --help` EXIT=2 因 handler 自定义 store_true 覆盖 argparse 自动 help; `rddf archive-sync --help` 把 `--help` 当 change name EXIT=1)。修复策略选项 B (推荐): 在 `_lib/cli/__init__.py::route()` 入口统一拦截 `--help`/`-h` + 打印 subcommand-specific usage + EXIT 0,与 argparse 默认行为一致,消除整个类 bug 的可能性
>
> **依赖说明**: 无；后续 follow-up 建议 `fix-33-handlers-project-root-anti-pattern` (33 handler 用 `RDDF_PROJECT_ROOT or os.getcwd()` 反模式,应统一用 `__main__.resolve_project_root()`)
>
> **实施建议**: 走 rdd-builder P0-P3 完整流程。Scope ≤ 2 文件 (`_lib/cli/__init__.py` + `tests/unit/test_route_help_handling.py`)，可能触发 rdd-quick 旁路 per ADR-0048 §Decision 3 (因 scope ≤ 2 + ≤ 3 tasks)
>
> **重叠检查**: 无. fix-cmd-help-handling 仅触及 `_lib/cli/__init__.py::route()` 入口 + 新 test file, 不影响具体 handler 业务逻辑 (34 个 subcommand 已正确)。不修改 33 文件的 `RDDF_PROJECT_ROOT or os.getcwd()` 反模式 (那是 follow-up improvement)

> **批次说明 (2026-09-24 rdd-planner)**: 本批 3 项 Wave 3 提案 (本次批准) 为 `complete-guide-orchestrator-flow` (Wave 2, 已 ship 2026-09-24) 之后的剩余 gap:
> 1. **`wave3-opencode-session-injection`** (P1) — Step A.6 多窗口 owner 区分依赖 OpenCode 平台层 `$OPENCODE_SESSION_ID` 真值注入 (依赖 OpenCode 外部项目, R1 高风险; 方案 B 作为 fallback)
> 2. **`wave3-phase-heartbeat-progressing`** (P2) — Step A.5 `phase_heartbeat` 接入生产路径 + schema context 携带 `tasks_total`/`tasks_completed`, 让 synthesizer 渲染真任务进度 (解决 AC-G3 "0/1" 语义贫弱)
> 3. **`wave3-rddf-session-show-events`** (P2) — Step A.6 `rddf session show --events` 历史回放 CLI (按 owner/session/kind/time-range 过滤 events.jsonl)
>
> **依赖说明**:
> - P1 (opencode-session-injection) **依赖 OpenCode 平台层 API 改动** — 跟踪 OpenCode 排期, 短期不可 ship 时实施方案 B (rdd-workflow-side fallback)
> - P2 (phase-heartbeat) 独立可 ship — schema 扩展在 `context` 子键加 optional 字段, 不改 ADR-0055 7 类 event_type 白名单 (MN-HB1)
> - P2 (rddf-session-show-events) 独立可 ship — 与 P2 heartbeat 软协同 (hard dep on events.jsonl 数据层, 已 ship)
>
> **实施建议**:
> - P2 heartbeat **先 ship** (依赖最少, 独立可测; 提升 AC-G3 体验)
> - P2 show-events **并行 ship** (与 heartbeat 互补; 共享事件 schema)
> - P1 opencode 跟踪 OpenCode 排期 — 不可 ship 时实施方案 B (避免长期 blocking)
>
> **重叠检查**: 无. 3 项触及不同文件 (`rddf_session_hooks.sh` heartbeat heredoc / `_lib/cli/session_show_cmd.py` 新增 / OpenCode 平台层). P2 心跳 schema 扩展不影响 P2 show-events 读取 (向后兼容 optional 字段).

> **批次说明 (2026-09-10 design-done)**: 本批 4 项提案 (本次批准) 为 KNOWN_FAILURES baseline 衍生, 全部为 test-fix / docs-fix 小修, 低风险独立可并行. 计划按下列顺序实施 (合并到 single feature: feat-fix-audit-findings):
> 1. **`fix-parametrize-planner-feedback-id-date`** (P2) — first: 重构 5 个 hardcode 日期测试为 tmp_path fixture, 解决时间炸弹
> 2. **`fix-rebuild-adr-index-for-0049-0050`** (P2) — independent: 重生成 docs/adr/README.md 索引 (缺 ADR-0049/0050)
> 3. **`fix-update-doctor-main-category-count`** (P2) — independent: 测试断言 10→11 (新 gitignore category), 提取 _CATEGORY_NAMES 常量
> 4. **`fix-remove-stale-filled-at-regression-test`** (P3) — independent: 改 TestFilledAtRegression 用 tmp_path fixture (推荐选项 B, 保留意图)
>
> **依赖说明**: 4 项之间**无依赖**, 可并行实施. 唯一共享上下文: 同属 `feat-fix-audit-findings` feature (refs phase-1~4), 实施后合并 KNOWN_FAILURES baseline 减 10 项 (5+2+2+1).
>
> **重叠检查**: 无. 每个 proposal 触及不同测试文件 (`test_planner_feedback_id_uniqueness.py` / `test_adr_index_gate.py` / `test_doctor_main.py` / `test_cli_all_subcommands.py`), 无 file conflict.

> **依赖声明 (2026-08-05 design-done)**: 本批 7 项提案 (本次批准) 形成强依赖链, 计划按下列顺序实施:
> 1. **`fix-archive-iteration-sync`** (P0) — first: 定义 `sync_iteration_after_archive` helper, 装到 `archive.sh::archive_change()` + `archive_on_main.sh` + `rddf status --archive` 3 个入口
> 2. **`fix-archive-on-main-flow`** (P0) — after #1: 给 `archive_on_main.sh` 加 `--confirm-main` 必填 + 失败回滚 (在 #1 的 helper 之上加固)
> 3. **`add-archive-post-commit-hook-and-force-flag`** (P0) — after #1: 凭 #1 的 helper 拦截裸 `git mv` 路径 + `--force` 消除绕过动机 (AC-16 硬约束)
> 4. **`fix-rddf-status-corrupt-message`** (P1) + **`rddf-iteration-strict-schema`** (P1) — 并行: 共修 `status_cmd.py` + `state_reader.py`, 建议合 PR 避免 collision (前者修 read-side 消息折叠, 后者加 `rddf iteration lint` + `allowed-fields` 写前预检)
> 5. **`fix-tasks-md-archive-residue`** (P1) — independent, 推荐与 #1 同 PR (共享 `archive_change()` 末尾 hook 触发点)
> 6. **`collect-l2-violation-count-on-archive`** (P2) — last: 依赖 #4 的 schema 演进策略 (自身需 schema bump, 等 #4 明确 schema 治理流程后实施)
>
> **重叠修正 (2026-08-05 design-done)**:
> - `fix-archive-iteration-sync` 与 `fix-archive-on-main-flow` 在 `archive_on_main.sh` 路径上重叠. 实施时 **#1 先** (helper + 3 个入口), **#2 后** (在该文件加 `--confirm-main` 必填 + 失败回滚 — 不重写 #1 的 sync 调用)
> - `fix-rddf-status-corrupt-message` 与 `rddf-iteration-strict-schema` 在 `status_cmd.py` 上重叠. 前者修 read-side 错误消息折叠, 后者加 write-side `lint` / `allowed-fields` 子命令. 两者都改 `status_cmd.py`, 建议 **同 PR 合并**避免 file conflict
> - `fix-archive-iteration-sync` 与 `fix-tasks-md-archive-residue` 在 `archive_change()` 末尾 hook 上重叠. 推荐 **同 PR 合并实施** (sidecar 生成 + tasks_done 派生都在同一 hook 点)
>
> **bump 合并声明 (2026-08-05 design-done)**: `fix-rddf-status-corrupt-message` (本次批准) 与 `rddf-iteration-strict-schema` (本次批准) **合并为单一 CLI 消息治理 PR** (`unify-status-cmd-iteration-messages`), 一次同时支持 read-side 缺失/损坏区分 + write-side 预检工具. **禁止拆为两次独立 PR**. Plan 阶段必须先实施 #1 (`fix-archive-iteration-sync`) 再启动本 PR.

> **supersedes** (2026-08-02 design-done): `add-rddf-session-status-cmd` (本次批准) **supersedes** 已批准 `add-session-progress-view` (P1, 2026-07-28) — 后者范围是前者的子集 (本提案更广: 表格 + BINDING_LINES + guide 推荐器整合)。Plan 阶段实施时跳过 `add-session-progress-view`, 仅实施 `add-rddf-session-status-cmd`。
>
> **bump 合并声明** (2026-08-02 design-done): `add-rddf-session-sub-phase-heartbeat` (本次批准) 与 `add-rddf-session-workflow-group` (本次批准) **合并为单一 schema v1→v2 bump PR** (`bump-sessions-schema-v2`), 一次同时支持 `sub_phase: str | null` + `workflow_group: str | null` 两个 optional 字段。**禁止拆为两次独立 bump**。Plan 阶段必须先实施 P0 (`fix-rddf-session-owner-stability`) 再启动本 PR。
















































































































## 已实施
| [adr-index-auto-sync](improvements/adr-index-auto-sync.md) | P1 | 2026-09-10 | 已实施 |
| [changelog-usage-sync](improvements/changelog-usage-sync.md) | P1 | 2026-09-10 | 已实施 |
| [add-e2e-test-plan-phase5](improvements/add-e2e-test-plan-phase5.md) | P1 | 2026-09-08 | 已实施 |
| [add-e2e-test-plan-phase4](improvements/add-e2e-test-plan-phase4.md) | P1 | 2026-09-08 | 已实施 |
| [add-e2e-test-plan-phase3](improvements/add-e2e-test-plan-phase3.md) | P1 | 2026-09-08 | 已实施 |
| [add-e2e-test-plan-phase2](improvements/add-e2e-test-plan-phase2.md) | P1 | 2026-09-08 | 已实施 |
| [add-e2e-test-plan-phase1](improvements/add-e2e-test-plan-phase1.md) | P1 | 2026-09-08 | 已实施 |
| [add-rdd-quick-skill](improvements/add-rdd-quick-skill.md) | P1 | 2026-09-07 | 已实施 |
| [rfc-rddf-project-yaml-config-i10](improvements/rfc-rddf-project-yaml-config-i10.md) | P1 | 2026-09-02 | 已实施 |
| [complete-project-yaml-config-gaps](improvements/complete-project-yaml-config-gaps.md) | P1 | 2026-09-02 | 已实施 |
| [worktree-context-persistence](improvements/worktree-context-persistence.md) | P1 | 2026-09-01 | 已实施 |
| [reduce-rdd-workflow-tool-call-friction](improvements/reduce-rdd-workflow-tool-call-friction.md) | P1 | 2026-09-01 | 已实施 |
| [verifier-archive-gate-clarification](improvements/verifier-archive-gate-clarification.md) | P1 | 2026-08-28 | guide-arch |
| [submodule-aware-project-root](improvements/submodule-aware-project-root.md) | P0 | 2026-08-25 | 已实施 |
| [clean-stale-plan-handoff-on-ship-done](improvements/clean-stale-plan-handoff-on-ship-done.md) | P1 | 2026-08-25 | 已实施 |
| [clean-adr-0027-section-5-supersede](improvements/clean-adr-0027-section-5-supersede.md) | P2 | 2026-08-25 | 已实施 |
| [fix-review-debt-recorded-gate](improvements/fix-review-debt-recorded-gate.md) | P2 | 2026-08-25 | 已实施 |
| [fix-post-flow-classifier-ordering](improvements/fix-post-flow-classifier-ordering.md) | P2 | 2026-08-25 | 已实施 |
| [fix-adr-0027-issue-file-frontmatter](improvements/fix-adr-0027-issue-file-frontmatter.md) | P1 | 2026-08-24 | 已实施 |
| [fix-adr-0027-close-hook-dead-code](improvements/fix-adr-0027-close-hook-dead-code.md) | P1 | 2026-08-24 | 已实施 |
| [fix-adr-0027-cli-optin-gate](improvements/fix-adr-0027-cli-optin-gate.md) | P0 | 2026-08-24 | 已实施 |
| [add-cli-coverage-rdd-doctor-roadmap-rdd-hub](improvements/add-cli-coverage-rdd-doctor-roadmap-rdd-hub.md) | P1 | 2026-08-20 | 已实施 |
| [add-hierarchical-roadmap-structure](improvements/add-hierarchical-roadmap-structure.md) | P1 | 2026-08-20 | 已实施 |
> **状态订正 (2026-11-19)**: `fix-generator-scope-extraction` 的「完成时间 2026-08-15」指的是归档 change
> `2026-08-14-fix-generator-scope-extraction` 合流的时间，**不是**需求全部兑现的时间。核对结论：AC 1.3/1.4
> （空段 fallback、Capabilities/Impact 拆分）在 2026-08-14 确实兑现；**AC 1.1/1.2（`## 范围` 段的 numbered
> 列表与子项归并）直到 2026-11-19（commit `68623a4`）才真正兑现** —— 2026-08-14 的实现把 numbered 支持加到了
> `_extract_bullet_items`（技术约束段）而不是 spec/task 指名的 `_extract_scope_items`（范围段），而当次新增的
> 6 个用例也断言的是同一个错误函数 ⇒ 门一直绿、需求一直未满足；那批用例还在 2026-09-06 被删除。
> 已合并的 spec `generator-scope-extraction` 的 Requirement 1/2 从 2026-08-15 到 2026-11-19 一直是未满足状态。
> 逐条核对、根因与残留偏差见该 improvement 文件末尾的「实施状态核对（2026-11-19 补记）」段。
> 顺带记下一个系统性缺口：本仓没有「spec Requirement ⇒ 代码兑现」的交叉检查，这类假绿只能靠人记。

| 提案 | 优先级 | 完成时间 | 状态 |
|------|--------|----------|------|
| [fix-spec-v3-naming-sync](improvements/fix-spec-v3-naming-sync.md) | P2 | 2026-11-24 | 已实施 |
| [add-skills-lib-api-doc](improvements/add-skills-lib-api-doc.md) | P2 | 2026-11-24 | 已实施 |
| [fix-agents-md-worktree-commit-flow](improvements/fix-agents-md-worktree-commit-flow.md) | P1 | 2026-11-24 | 已实施 |
| [fix-bats-per-file-timeout](improvements/fix-bats-per-file-timeout.md) | P2 | 2026-11-18 | 已实施 |
| [bypass-audit-mechanism](improvements/bypass-audit-mechanism.md) | P2 | 2026-09-11 | 已实施 |
| [fix-script-project-root-anchoring](improvements/fix-script-project-root-anchoring.md) | P2 | 2026-11-18 | 已实施 |
| [fix-lightweight-branch-and-archive](improvements/fix-lightweight-branch-and-archive.md) | P1 | 2026-11-18 | 已实施 |
| [fix-worktree-archive-branch-merge](improvements/fix-worktree-archive-branch-merge.md) | P1 | 2026-11-18 | 已实施 |
| [fix-adr-index-generator-dup](improvements/fix-adr-index-generator-dup.md) | P1 | 2026-11-17 | 已实施 |
| [fix-execution-mode-decision](improvements/fix-execution-mode-decision.md) | P1 | 2026-11-17 | 已实施 |
| [fix-iteration-tasks-total](improvements/fix-iteration-tasks-total.md) | P1 | 2026-11-17 | 已实施 |
| [fix-regression-baseline-integrity](improvements/fix-regression-baseline-integrity.md) | P1 | 2026-11-17 | 已实施 |
| [fix-verifier-gate-cache-root](improvements/fix-verifier-gate-cache-root.md) | P1 | 2026-11-17 | 已实施 |
| [fix-flow-drift-batch-1](improvements/fix-flow-drift-batch-1.md) | P2 | 2026-11-16 | 已实施 |
| [register-change-in-iteration](improvements/register-change-in-iteration.md) | P2 | 2026-11-16 | 已实施 |
| [fix-phase3-cleanup-wiring](improvements/fix-phase3-cleanup-wiring.md) | P1 | 2026-11-16 | 已实施 |
| [fix-worktree-archive-path](improvements/fix-worktree-archive-path.md) | P1 | 2026-11-16 | 已实施 |
| [fix-p3-verifier-gate](improvements/fix-p3-verifier-gate.md) | P1 | 2026-11-16 | 已实施 |
| [rddf-layout-manifest](improvements/rddf-layout-manifest.md) | P1 | 2026-11-16 | 已实施 |
| [fix-rdd-doctor-hardcoded-paths-and-skills-md-drift](improvements/fix-rdd-doctor-hardcoded-paths-and-skills-md-drift.md) | P1 | 2026-10-07 | 已实施 |
| [consolidate-resolve-project-root-helpers](improvements/consolidate-resolve-project-root-helpers.md) | P3 | 2026-09-28 | 已实施 |
| [fix-skill-layer-resolution-bash](improvements/fix-skill-layer-resolution-bash.md) | P3 | 2026-09-28 | 已实施 |
| [v2.1-fix-rdd-quick-archive-verifier-gaps](improvements/v2.1-fix-rdd-quick-archive-verifier-gaps.md) | P0 | 2026-09-28 | 已实施 |
| [add-skill-layer-resolve-project-root-helper](improvements/add-skill-layer-resolve-project-root-helper.md) | P2 | 2026-09-27 | 已实施 |
| [fix-skill-layer-project-root-anti-pattern](improvements/fix-skill-layer-project-root-anti-pattern.md) | P2 | 2026-09-26 | 已实施 |
| [fix-33-handlers-project-root-anti-pattern](improvements/fix-33-handlers-project-root-anti-pattern.md) | P2 | 2026-09-26 | 已实施 |
| [fix-33-handlers-project-root-anti-pattern](improvements/fix-33-handlers-project-root-anti-pattern.md) | P2 | 2026-09-26 | 已实施 |
| [fix-cmd-help-handling](improvements/fix-cmd-help-handling.md) | P1 | 2026-09-25 | 已实施 |
| [wave3-rddf-session-show-events](improvements/wave3-rddf-session-show-events.md) | P2 | 2026-09-24 | 已实施 |
| [wave3-phase-heartbeat-progressing](improvements/wave3-phase-heartbeat-progressing.md) | P2 | 2026-09-24 | 已实施 |
| [wave3-opencode-session-injection](improvements/wave3-opencode-session-injection.md) | P1 | 2026-09-24 | 已实施 |
| [fix-guide-close-owner-resolution](improvements/fix-guide-close-owner-resolution.md) | P1 | 2026-09-24 | 已实施 |
| [fix-events-log-blocking-lock](improvements/fix-events-log-blocking-lock.md) | P0 | 2026-09-23 | 已实施 |
| [add-objective-tracking](improvements/add-objective-tracking.md) | P1 | 2026-09-22 | 已实施 |
| [phase-1-general-20260829063800-2](improvements/phase-1-general-20260829063800-2.md) | P1 | 2026-09-22 | 已实施 |
| [add-feature-fragment-command](improvements/add-feature-fragment-command.md) | P1 | 2026-09-22 | 已实施 |
| [fix-skill-post-install-discoverability](improvements/fix-skill-post-install-discoverability.md) | P1 | 2026-09-22 | 已实施 |
| [add-plan-done-reflect-hook](improvements/add-plan-done-reflect-hook.md) | P1 | 2026-09-22 | 已实施 |
| [apply-adr-0051-skill-description-convention-bulk-rewrite](improvements/apply-adr-0051-skill-description-convention-bulk-rewrite.md) | P0 | 2026-09-22 | 已实施 |
| [add-env-bootstrap-skill](improvements/add-env-bootstrap-skill.md) | P1 | 2026-09-22 | 已实施 |
| [fix-remove-stale-filled-at-regression-test](improvements/fix-remove-stale-filled-at-regression-test.md) | P3 | 2026-09-10 | 已实施 |
| [fix-update-doctor-main-category-count](improvements/fix-update-doctor-main-category-count.md) | P2 | 2026-09-10 | 已实施 |
| [fix-rebuild-adr-index-for-0049-0050](improvements/fix-rebuild-adr-index-for-0049-0050.md) | P2 | 2026-09-10 | 已实施 |
| [fix-parametrize-planner-feedback-id-date](improvements/fix-parametrize-planner-feedback-id-date.md) | P2 | 2026-09-10 | 已实施 |
| [fix-doc-drift-followup-3](improvements/fix-doc-drift-followup-3.md) | P1 | 2026-09-09 | 已实施 |
| [fix-plan-intake-stale-pre-created-changes](improvements/fix-plan-intake-stale-pre-created-changes.md) | P1 | 2026-09-01 | 已实施 |
| [add-regression-gate-timeout-protection](improvements/add-regression-gate-timeout-protection.md) | P2 | 2026-09-01 | 已实施 |
| [add-session-metrics-collection](improvements/add-session-metrics-collection.md) | P2 | 2026-09-01 | 已实施 |
| [add-e2e-test-skip-on-missing-hub-auth](improvements/add-e2e-test-skip-on-missing-hub-auth.md) | P1 | 2026-09-01 | 已实施 |
| [fix-cli-all-subcommands-dynamic-sync](improvements/fix-cli-all-subcommands-dynamic-sync.md) | P1 | 2026-09-01 | 已实施 |
| [fix-design-done-gate-status-prefix-match](improvements/fix-design-done-gate-status-prefix-match.md) | P0 | 2026-09-01 | 已实施 |
| [fix-report-regression-sed-double-hash-strip](improvements/fix-report-regression-sed-double-hash-strip.md) | P0 | 2026-09-01 | 已实施 |
| [fix-specs-auto-generate-in-design-precreated](improvements/fix-specs-auto-generate-in-design-precreated.md) | P0 | 2026-09-01 | 已实施 |
| [phase-4-general-20260829063814](improvements/phase-4-general-20260829063814.md) | P1 | 2026-08-30 | 已实施 |
| [phase-3-general-20260829063801](improvements/phase-3-general-20260829063801.md) | P1 | 2026-08-30 | 已实施 |
| [phase-3-general-20260829063814](improvements/phase-3-general-20260829063814.md) | P1 | 2026-08-30 | 已实施 |
| [phase-2-general-20260829063801-2](improvements/phase-2-general-20260829063801-2.md) | P1 | 2026-08-30 | 已实施 |
| [phase-2-general-20260829063801](improvements/phase-2-general-20260829063801.md) | P1 | 2026-08-30 | 已实施 |
| [phase-2-general-20260829063814](improvements/phase-2-general-20260829063814.md) | P1 | 2026-08-30 | 已实施 |
| [phase-1-general-20260829063814](improvements/phase-1-general-20260829063814.md) | P1 | 2026-08-30 | 已实施 |
| [phase-1-general-20260829063800](improvements/phase-1-general-20260829063800.md) | P1 | 2026-08-30 | 已实施 |
| [improve-roadmap-feature-discovery](improvements/improve-roadmap-feature-discovery.md) | P1 | 2026-08-28 | 已实施 |
| [improve-from-roadmap-naming-flexibility](improvements/improve-from-roadmap-naming-flexibility.md) | P1 | 2026-08-28 | 已实施 |
| [add-proposal-source-tracking](improvements/add-proposal-source-tracking.md) | P1 | 2026-08-28 | 已实施 |
| [add-pre-commit-proposal-quality-check](improvements/add-pre-commit-proposal-quality-check.md) | P1 | 2026-08-28 | 已实施 |
| [add-brainstorm-hardgate-enforcement](improvements/add-brainstorm-hardgate-enforcement.md) | P1 | 2026-08-28 | 已实施 |
| [verifier-re-verify-archived-flag](improvements/verifier-re-verify-archived-flag.md) | P1 | 2026-08-28 | 已实施 |
| [design-approve-batch-tool](improvements/design-approve-batch-tool.md) | P1 | 2026-08-28 | 已实施 |
| [plan-batch-fill-tool](improvements/plan-batch-fill-tool.md) | P1 | 2026-08-28 | 已实施 |
| [auto-archive-iteration-and-commit](improvements/auto-archive-iteration-and-commit.md) | P1 | 2026-08-28 | 已实施 |
| [improve-commit-scope-discipline](improvements/improve-commit-scope-discipline.md) | P1 | 2026-08-28 | 已实施 |
| [improve-change-splitting-strategy](improvements/improve-change-splitting-strategy.md) | P1 | 2026-08-28 | 已实施 |
| [improve-execution-mode-per-change](improvements/improve-execution-mode-per-change.md) | P1 | 2026-08-28 | 已实施 |
| [fix-proposal-ac-section-mapping](improvements/fix-proposal-ac-section-mapping.md) | P1 | 2026-08-28 | 已实施 |
| [fix-disk-count-semantic-conflict](improvements/fix-disk-count-semantic-conflict.md) | P1 | 2026-08-28 | 已实施 |
| [fix-ship-plan-untracked-gate](improvements/fix-ship-plan-untracked-gate.md) | P1 | 2026-08-28 | 已实施 |
| [fix-design-preflight-roadmap-format](improvements/fix-design-preflight-roadmap-format.md) | P1 | 2026-08-28 | 已实施 |
| [fix-iteration-archive-sync](improvements/fix-iteration-archive-sync.md) | P1 | 2026-08-28 | 已实施 |
| [reconcile-iteration-after-archive](improvements/reconcile-iteration-after-archive.md) | P1 | 2026-08-28 | 已实施 |
| [rdd-doctor-docs-consistency](improvements/rdd-doctor-docs-consistency.md) | P1 | 2026-08-27 | 已实施 |
| [sync-agents-md-five-stage](improvements/sync-agents-md-five-stage.md) | P1 | 2026-08-27 | 已实施 |
| [sync-package-skills-to-disk](improvements/sync-package-skills-to-disk.md) | P1 | 2026-08-27 | 已实施 |
| [fix-discover-ship-changes-needs-planning-fallback](improvements/fix-discover-ship-changes-needs-planning-fallback.md) | P1 | 2026-08-21 | 已实施 |
| [move-populate-roadmap-into-guide-arch](improvements/move-populate-roadmap-into-guide-arch.md) | P2 | 2026-08-21 | 已实施 |
| [extend-populate-roadmap-with-code-verification](improvements/extend-populate-roadmap-with-code-verification.md) | P1 | 2026-08-21 | 已实施 |
| [add-auto-rfc-from-approve](improvements/add-auto-rfc-from-approve.md) | P0 | 2026-08-19 | 已实施 |
| [add-rfc-interview-flow](improvements/add-rfc-interview-flow.md) | P0 | 2026-08-19 | 已实施 |
| [add-rfc-draft-template](improvements/add-rfc-draft-template.md) | P0 | 2026-08-19 | 已实施 |
| [add-cross-repo-impact-detection](improvements/add-cross-repo-impact-detection.md) | P0 | 2026-08-19 | 已实施 |
| [fix-adr-0031-safety-gate-substantiation](improvements/fix-adr-0031-safety-gate-substantiation.md) | P0 | 2026-08-18 | 已实施 |
| [fix-orphan-hub-gates-wiring](improvements/fix-orphan-hub-gates-wiring.md) | P1 | 2026-08-18 | 已实施 |
| [fix-cli-routing-cross-repo-commands](improvements/fix-cli-routing-cross-repo-commands.md) | P1 | 2026-08-18 | 已实施 |
| [fix-schema-version-field](improvements/fix-schema-version-field.md) | P1 | 2026-08-18 | 已实施 |
| [enforce-tasks-completion-before-archive](improvements/enforce-tasks-completion-before-archive.md) | P2 | 2026-08-18 | 已实施 |
| [complete-add-cross-repo-deps-orchestration](improvements/complete-add-cross-repo-deps-orchestration.md) | P1 | 2026-08-18 | 已实施 |
| [complete-add-contract-lint-ci-gate](improvements/complete-add-contract-lint-ci-gate.md) | P1 | 2026-08-18 | 已实施 |
| [enforce-plan-tdd-5step-new](improvements/enforce-plan-tdd-5step-new.md) | P2 | 2026-08-16 | 已实施 |
| [backfill-proposal-approved-col4](improvements/backfill-proposal-approved-col4.md) | P2 | 2026-08-16 | 已实施 |
| [add-cross-repo-deps-orchestration](improvements/add-cross-repo-deps-orchestration.md) | P1 | 2026-08-16 | 已实施 |
| [add-strict-human-approval-for-cross-repo-changes](improvements/add-strict-human-approval-for-cross-repo-changes.md) | P1 | 2026-08-16 | 已实施 |
| [add-spoke-system-prompt-injection](improvements/add-spoke-system-prompt-injection.md) | P1 | 2026-08-16 | 已实施 |
| [add-mcp-cross-repo-protocol](improvements/add-mcp-cross-repo-protocol.md) | P1 | 2026-08-16 | 已实施 |
| [add-rdd-hub-cross-repo-federation](improvements/add-rdd-hub-cross-repo-federation.md) | P1 | 2026-08-16 | 已实施 |
| [add-rdd-hub-bootstrap](improvements/add-rdd-hub-bootstrap.md) | P0 | 2026-08-16 | 已实施 |
| [issue-driven-proposal-creation](improvements/issue-driven-proposal-creation.md) | P1 | 2026-08-15 | 已实施 |
| [add-phase-role-model](improvements/add-phase-role-model.md) | P1 | 2026-08-14 | 已实施 |
| [preserve-orchestrator-command-stdout](improvements/preserve-orchestrator-command-stdout.md) | P1 | 2026-08-14 | 已实施 |
| [harden-plan-intake-bootstrap-and-design-gate-tests](improvements/harden-plan-intake-bootstrap-and-design-gate-tests.md) | P1 | 2026-08-13 | 已实施 |
| [validate-feature-name](improvements/validate-feature-name.md) | P1 | 2026-08-12 | 已实施 |
| [fix-feature-decision-design-phase](improvements/fix-feature-decision-design-phase.md) | P1 | 2026-08-10 | 已实施 |
| [fix-proposal-approved-missing-after-archive](improvements/fix-proposal-approved-missing-after-archive.md) | P1 | 2026-08-09 | 已实施 |
| [add-rdd-doctor-skill](improvements/add-rdd-doctor-skill.md) | P1 | 2026-08-09 | 已实施 |
| [archive-cleanup-plan-files-extension](improvements/archive-cleanup-plan-files-extension.md) | P2 | 2026-08-08 | 已实施 |
| [fix-design-proposal-review-approved-parsing](improvements/fix-design-proposal-review-approved-parsing.md) | P0 | 2026-08-07 | 已实施 |
| [post-archive-cleanup-hook](improvements/post-archive-cleanup-hook.md) | P0 | 2026-08-06 | 已实施 |
| [fix-rddf-init-broken-layout](improvements/fix-rddf-init-broken-layout.md) | P1 | 2026-08-06 | 已实施 |
| [collect-l2-violation-count-on-archive](improvements/collect-l2-violation-count-on-archive.md) | P2 | 2026-08-06 | 已实施 |
| [fix-tasks-md-archive-residue](improvements/fix-tasks-md-archive-residue.md) | P1 | 2026-08-06 | 已实施 |
| [rddf-iteration-strict-schema](improvements/rddf-iteration-strict-schema.md) | P1 | 2026-08-06 | 已实施 |
| [fix-rddf-status-corrupt-message](improvements/fix-rddf-status-corrupt-message.md) | P1 | 2026-08-06 | 已实施 |
| [add-archive-post-commit-hook-and-force-flag](improvements/add-archive-post-commit-hook-and-force-flag.md) | P0 | 2026-08-06 | 已实施 |
| [fix-archive-on-main-flow](improvements/fix-archive-on-main-flow.md) | P0 | 2026-08-06 | 已实施 |
| [fix-archive-iteration-sync](improvements/fix-archive-iteration-sync.md) | P0 | 2026-08-06 | 已实施 |
| [guide-ship-default-serial-execution](improvements/guide-ship-default-serial-execution.md) | P1 | 2026-08-05 | 已实施 |
| [plan-quality-and-validation](improvements/plan-quality-and-validation.md) | P0 | 2026-08-05 | 已实施 |
| [developer-experience-observability](improvements/developer-experience-observability.md) | P2 | 2026-08-05 | 已实施 |
| [subagent-orchestrator-execution-strategy](improvements/subagent-orchestrator-execution-strategy.md) | P0 | 2026-08-05 | 已实施 |
| [worktree-archive-workflow](improvements/worktree-archive-workflow.md) | P0 | 2026-08-05 | 已实施 |
| [plan-execute-commit-policy-consistency](improvements/plan-execute-commit-policy-consistency.md) | P1 | 2026-08-04 | 已实施 |
| [python-failures-baseline](improvements/python-failures-baseline.md) | P3 | 2026-08-04 | 已实施 |
| [test-isolation-from-repo-state](improvements/test-isolation-from-repo-state.md) | P2 | 2026-08-04 | 已实施 |
| [execute-gate-unified-regression](improvements/execute-gate-unified-regression.md) | P2 | 2026-08-04 | 已实施 |
| [archive-history-keep-semantics](improvements/archive-history-keep-semantics.md) | P2 | 2026-08-04 | 已实施 |
| [extract-rdd-env-check-from-guide-arch](improvements/extract-rdd-env-check-from-guide-arch.md) | P1 | 2026-08-03 | 已实施 |
| [adr-create-interactive-drafting](improvements/adr-create-interactive-drafting.md) | P1 | 2026-08-03 | 已实施 |
| [add-rddf-session-workflow-group](improvements/add-rddf-session-workflow-group.md) | P2 | 2026-08-03 | 已实施 |
| [add-rddf-session-sub-phase-heartbeat](improvements/add-rddf-session-sub-phase-heartbeat.md) | P1 | 2026-08-03 | 已实施 |
| [add-rddf-session-status-cmd](improvements/add-rddf-session-status-cmd.md) | P2 | 2026-08-03 | 已实施 |
| [add-rddf-session-auto-archive-on-entry](improvements/add-rddf-session-auto-archive-on-entry.md) | P1 | 2026-08-03 | 已实施 |
| [refine-plan-openspec-integration](improvements/refine-plan-openspec-integration.md) | P1 | 2026-08-02 | 已实施 |
| [move-proposal-creation-to-design](improvements/move-proposal-creation-to-design.md) | P1 | 2026-08-02 | 已实施 |
| [fix-wt-scanner-strip-bug-and-untracked-coverage](improvements/fix-wt-scanner-strip-bug-and-untracked-coverage.md) | P1 | 2026-08-01 | 已实施 |
| [improve-ship-done-cleanup-orphan-sessions](improvements/improve-ship-done-cleanup-orphan-sessions.md) | P2 | 2026-08-01 | 已实施 |
| [fix-scanner-fallback-and-orphan-archival](improvements/fix-scanner-fallback-and-orphan-archival.md) | P1 | 2026-08-01 | 已实施 |
| [check-project-setup](improvements/check-project-setup.md) | P1 | 2026-08-01 | 已实施 |
| [fix-mark-approved-completed-date-drift](improvements/fix-mark-approved-completed-date-drift.md) | P2 | 2026-08-01 | 已实施 |
| [fix-ship-plan-skill-use-fallback](improvements/fix-ship-plan-skill-use-fallback.md) | P1 | 2026-08-01 | 已实施 |
| [fix-deps-render-report-multi-candidate](improvements/fix-deps-render-report-multi-candidate.md) | P1 | 2026-08-01 | 已实施 |
| [fix-update-proposal-status-data-loss](improvements/fix-update-proposal-status-data-loss.md) | P0 | 2026-08-01 | 已实施 |

| 提案 | 优先级 | 完成时间 | 状态 |
|------|--------|---------- |------|
| [harden-archive-iteration-sync](improvements/harden-archive-iteration-sync.md) | P1 | 2026-08-17 | 已实施 |
| [add-contract-lint-ci-gate](improvements/add-contract-lint-ci-gate.md) | P1 | 2026-08-16 | 已实施 |
| [add-cross-repo-state-schemas](improvements/add-cross-repo-state-schemas.md) | P1 | 2026-08-16 | 已实施 |
| [fix-generator-scope-extraction](improvements/fix-generator-scope-extraction.md) | P1 | 2026-08-15 | 已实施（范围段 2026-11-19 补齐） |
| [complete-third-party-replay-and-upstream-reporting](improvements/complete-third-party-replay-and-upstream-reporting.md) | P0 | 2026-08-13 | 已实施 |
| [sync-changelog-unreleased](improvements/sync-changelog-unreleased.md) | P1 | 2026-08-13 | 已实施 |
| [add-roadmap-proposal-guidance](improvements/add-roadmap-proposal-guidance.md) | P1 | 2026-08-13 | 已实施 |
| [migrate-improvements-to-rddf-namespace](improvements/migrate-improvements-to-rddf-namespace.md) | P0 | 2026-08-12 | 已实施 |
| [add-proposal-how-leakage-warning](improvements/add-proposal-how-leakage-warning.md) | P1 | 2026-08-12 | 已实施 |
| [wire-design-content-review-gate](improvements/wire-design-content-review-gate.md) | P1 | 2026-08-12 | 已实施 |
| [wire-plan-done-quality-gates](improvements/wire-plan-done-quality-gates.md) | P0 | 2026-08-12 | 已实施 |
| [fix-ship-archive-resolve-lib-path](improvements/fix-ship-archive-resolve-lib-path.md) | P1 | 2026-08-07 | 已实施 |
| [fix-bootstrap-fallback-paths](improvements/fix-bootstrap-fallback-paths.md) | P1 | 2026-08-07 | 已实施 |
| [add-env-cache-arch-discovery](improvements/add-env-cache-arch-discovery.md) | P2 | 2026-08-07 | 已实施 |
| [add-known-failures-baseline](improvements/add-known-failures-baseline.md) | P3 | 2026-08-04 | 已实施 |
| [add-skill-registration-checklist](improvements/add-skill-registration-checklist.md) | P2 | 2026-08-04 | 已实施 |
| [fix-execute-change-name-persistence](improvements/fix-execute-change-name-persistence.md) | P1 | 2026-08-04 | 已实施 |
| [fix-rddf-session-owner-stability](improvements/fix-rddf-session-owner-stability.md) | P0 | 2026-08-03 | 已实施 |
| [fix-add-improve-initial-prompt-ux](improvements/fix-add-improve-initial-prompt-ux.md) | P1 | 2026-07-31 | 已实施 |
| [fix-plan-deps-candidates-import-guard](improvements/fix-plan-deps-candidates-import-guard.md) | P0 | 2026-07-31 | 已实施 |
| [fix-rddf-session-lifecycle-binding](improvements/fix-rddf-session-lifecycle-binding.md) | P1 | 2026-07-31 | 已实施 |
| [fix-test-infrastructure-and-skill-registration](improvements/fix-test-infrastructure-and-skill-registration.md) | P2 | 2026-07-31 | 已实施 |
| [deps-driven-execution-mode](improvements/deps-driven-execution-mode.md) | P2 | 2026-07-30 | 已实施 |
| [guide-ship-quick-finish](improvements/guide-ship-quick-finish.md) | P2 | 2026-07-29 | 已实施 |
| [fix-plan-done-gate-zero-stale-count](improvements/fix-plan-done-gate-zero-stale-count.md) | P2 | 2026-07-29 | 已实施 |
| [fix-guide-ship-archive-bats](improvements/fix-guide-ship-archive-bats.md) | P2 | 2026-07-29 | 已实施 |
| [fix-doc-truth-sync](improvements/fix-doc-truth-sync.md) | P2 | 2026-07-29 | 已实施 |
| [archive-cleanup-plan-files](improvements/archive-cleanup-plan-files.md) | P2 | 2026-07-29 | 已实施 |
| [add-proposal-defer-support](improvements/add-proposal-defer-support.md) | P2 | 2026-07-29 | 已实施 |
| [prompt-worktree-cleanup-before-stage](improvements/prompt-worktree-cleanup-before-stage.md) | P3 | 2026-07-29 | 已实施 |
| [detect-suggestions-approved-inconsistency](improvements/detect-suggestions-approved-inconsistency.md) | P3 | 2026-07-29 | 已实施 |
| [filter-guide-ship-when-no-changes](improvements/filter-guide-ship-when-no-changes.md) | P2 | 2026-07-29 | 已实施 |
| [fix-scan-state-integer-comparison](improvements/fix-scan-state-integer-comparison.md) | P2 | 2026-07-29 | 已实施 |
| [pre-checkout-warning](improvements/pre-checkout-warning.md) | P2 | 2026-07-29 | 已实施 |
| [archive-cleanup-plan-handoff](improvements/archive-cleanup-plan-handoff.md) | P1 | 2026-07-29 | 已实施 |
| [add-proposal-deps-and-features](improvements/add-proposal-deps-and-features.md) | P1 | 2026-07-29 | 已实施 |
| [add-change-content-review](improvements/add-change-content-review.md) | P1 | 2026-07-29 | 已实施 |
| [guide-plan-fallback-direct-create](improvements/guide-plan-fallback-direct-create.md) | P1 | 2026-07-29 | 已实施 |
| [fix-arch-handoff-stale-detection](improvements/fix-arch-handoff-stale-detection.md) | P1 | 2026-07-29 | 已实施 |
| [adr-creation-architecture-gate](improvements/adr-creation-architecture-gate.md) | P1 | 2026-07-29 | 已实施 |
| [sync-approved-to-suggestions](improvements/sync-approved-to-suggestions.md) | P1 | 2026-07-29 | 已实施 |
| [fix-skill-tool-cache](improvements/fix-skill-tool-cache.md) | P1 | 2026-07-29 | 已实施 |
| [archive-gate-incomplete-tasks](improvements/archive-gate-incomplete-tasks.md) | P1 | 2026-07-29 | 已实施 |
| [ship-incomplete-archive-change-fallback](improvements/ship-incomplete-archive-change-fallback.md) | P1 | 2026-07-29 | 已实施 |
| [ship-delete-branch-safety](improvements/ship-delete-branch-safety.md) | P1 | 2026-07-29 | 已实施 |
| [fix-rddf-session-owner-cross-call](improvements/fix-rddf-session-owner-cross-call.md) | P1 | 2026-07-29 | 已实施 |
| [RDDF-0001-fix-rddf-session-import-path](improvements/RDDF-0001-fix-rddf-session-import-path.md) | P1 | 2026-07-29 | 已实施 |
| [add-config-validation](improvements/add-config-validation.md) | P0 | 2026-07-28 | 已实施 |
| [add-file-size-quality-gate](improvements/add-file-size-quality-gate.md) | P2 | 2026-07-28 | 已实施 |
| [add-full-regression-gate](improvements/add-full-regression-gate.md) | P0 | 2026-07-28 | 已实施 |
| [add-heartbeat-config](improvements/add-heartbeat-config.md) | P1 | 2026-07-28 | 已实施 |
| [add-openspec-gate](improvements/add-openspec-gate.md) | P0 | 2026-07-28 | 已实施 |
| [add-parent-feature-param](improvements/add-parent-feature-param.md) | P0 | 2026-07-28 | 已实施 |
| [add-plugin-loader-tests](improvements/add-plugin-loader-tests.md) | P2 | 2026-07-28 | 已实施 |
| [add-progressive-linting](improvements/add-progressive-linting.md) | P2 | 2026-07-28 | 已实施 |
| [add-propose-content-review](improvements/add-propose-content-review.md) | P1 | 2026-07-28 | 已实施 |
| [add-rddf-concurrency-tests](improvements/add-rddf-concurrency-tests.md) | P1 | 2026-07-28 | 已实施 |
| [add-session-progress-view](improvements/add-session-progress-view.md) | P1 | 2026-07-28 | 已实施 |
| [add-workflow-reflect-engine](improvements/add-workflow-reflect-engine.md) | P1 | 2026-07-28 | 已实施 |
| [add-workflow-synthesizer](improvements/add-workflow-synthesizer.md) | P0 | 2026-07-28 | 已实施 |
| [agent-completion-contract](improvements/agent-completion-contract.md) | P1 | 2026-07-28 | 已实施 |
| [archive-cleanup-working-tree](improvements/archive-cleanup-working-tree.md) | P1 | 2026-07-28 | 已实施 |
| [archive-iteration-sync](improvements/archive-iteration-sync.md) | P0 | 2026-07-28 | 已实施 |
| [archive-update-proposal-status](improvements/archive-update-proposal-status.md) | P1 | 2026-07-28 | 已实施 |
| [audit-attach-detach-calls](improvements/audit-attach-detach-calls.md) | P0 | 2026-07-28 | 已实施 |
| [auto-skip-archived-proposals](improvements/auto-skip-archived-proposals.md) | P0 | 2026-07-28 | 已实施 |
| [auto-sync-adr-index](improvements/auto-sync-adr-index.md) | P2 | 2026-07-28 | 已实施 |
| [auto-wave-scheduler](improvements/auto-wave-scheduler.md) | P0 | 2026-07-28 | 已实施 |
| [enforce-hook-symmetry](improvements/enforce-hook-symmetry.md) | P2 | 2026-07-28 | 已实施 |
| [fix-append-approved-output](improvements/fix-append-approved-output.md) | P2 | 2026-07-28 | 已实施 |
| [fix-arch-env-check-adr-count-bug](improvements/fix-arch-env-check-adr-count-bug.md) | P2 | 2026-07-28 | 已实施 |
| [fix-attach-detach-symmetry](improvements/fix-attach-detach-symmetry.md) | P1 | 2026-07-28 | 已实施 |
| [fix-deps-render-empty-candidates](improvements/fix-deps-render-empty-candidates.md) | P2 | 2026-07-28 | 已实施 |
| [fix-lsp-dash-bridge](improvements/fix-lsp-dash-bridge.md) | P0 | 2026-07-28 | 已实施 |
| [fix-mark-approved-completed](improvements/fix-mark-approved-completed.md) | P1 | 2026-07-28 | 已实施 |
| [fix-rddf-schema-validation](improvements/fix-rddf-schema-validation.md) | P0 | 2026-07-28 | 已实施 |
| [fix-scan-state-binding](improvements/fix-scan-state-binding.md) | P0 | 2026-07-28 | 已实施 |
| [fix-ship-lightweight-wt-path-pollution](improvements/fix-ship-lightweight-wt-path-pollution.md) | P2 | 2026-07-28 | 已实施 |
| [fix-silent-exception](improvements/fix-silent-exception.md) | P0 | 2026-07-28 | 已实施 |
| [fix-stale-suggestions-warning](improvements/fix-stale-suggestions-warning.md) | P2 | 2026-07-28 | 已实施 |
| [guide-cross-validate](improvements/guide-cross-validate.md) | P1 | 2026-07-28 | 已实施 |
| [guide-plan-noninteractive](improvements/guide-plan-noninteractive.md) | P0 | 2026-07-28 | 已实施 |
| [improve-openspec-test-change-support](improvements/improve-openspec-test-change-support.md) | P0 | 2026-07-28 | 已实施 |
| [parallel-oracle-review](improvements/parallel-oracle-review.md) | P1 | 2026-07-28 | 已实施 |
| [parallel-wave-execution](improvements/parallel-wave-execution.md) | P1 | 2026-07-28 | 已实施 |
| [preship-dirty-check](improvements/preship-dirty-check.md) | P2 | 2026-07-28 | 已实施 |
| [proposal-approval-pipeline](improvements/proposal-approval-pipeline.md) | P0 | 2026-07-28 | 已实施 |
| [propose-quality-autohook](improvements/propose-quality-autohook.md) | P0 | 2026-07-28 | 已实施 |
| [rddf-sessions-gc](improvements/rddf-sessions-gc.md) | P2 | 2026-07-28 | 已实施 |
| [relocate-loop-engine](improvements/relocate-loop-engine.md) | P2 | 2026-07-28 | 已实施 |
| [remove-ci-redundant-bats](improvements/remove-ci-redundant-bats.md) | P1 | 2026-07-28 | 已实施 |
| [skill-name-auto-resolve](improvements/skill-name-auto-resolve.md) | P2 | 2026-07-28 | 已实施 |
| [split-iteration-module](improvements/split-iteration-module.md) | P1 | 2026-07-28 | 已实施 |
| [split-rddf-god-class](improvements/split-rddf-god-class.md) | P2 | 2026-07-28 | 已实施 |
| [task-parallel-throttle](improvements/task-parallel-throttle.md) | P1 | 2026-07-28 | 已实施 |
| [unify-session-kind-naming](improvements/unify-session-kind-naming.md) | P0 | 2026-07-28 | 已实施 |
| [unify-test-entry-points](improvements/unify-test-entry-points.md) | P1 | 2026-07-28 | 已实施 |
| [update-adr-index](improvements/update-adr-index.md) | P2 | 2026-07-28 | 已实施 |
| [update-agents-module-map](improvements/update-agents-module-map.md) | P1 | 2026-07-28 | 已实施 |
| [update-guide-plan-format](improvements/update-guide-plan-format.md) | P1 | 2026-07-28 | 已实施 |
| [fix-scan-state-bats](improvements/fix-scan-state-bats.md) | P2 | 2026-07-23 | 已实施 |
| [complete-third-party-replay-and-upstream-reporting](improvements/complete-third-party-replay-and-upstream-reporting.md) | P0 | 2026-08-13 | 已实施 |
| [reduce-archive-commit-noise](improvements/reduce-archive-commit-noise.md) | P2 | 2026-09-01 | guide-arch |
| [fix-v4-rdd-planner-scope-over-assignment](improvements/fix-v4-rdd-planner-scope-over-assignment.md) | P1 | 2026-09-09 | 已实施 |
| [adr-0048-v4-stage-merge-revision](improvements/adr-0048-v4-stage-merge-revision.md) | P0 | 2026-09-09 | 已实施 |
| [rdd-builder-phase0-llm-integration](improvements/rdd-builder-phase0-llm-integration.md) | P2 | 2026-09-10 | 已实施 |
| [rdd-builder-auto-pick-mode](improvements/rdd-builder-auto-pick-mode.md) | P1 | 2026-09-10 | 已实施 |
| [add-scope-bootstrap-agent](improvements/add-scope-bootstrap-agent.md) | P2 | 2026-11-05 | 已批准（planner 2026-11-05；范围已收窄为 Soft 组 C+D） |

> **附注 (verifier-v2-hardening Phase 7 / oracle Q3)**: 跨阶段外部-LLM/hook 耦合审计建议（advisory, 不实施）：
> 1. **审计 `propose_quality_check.py`** —— 检查是否埋了外部 LLM/hook 假设，按 ADR-0045 模式内联（如有）
> 2. **审计 `arch_quality_gate.py`** —— 同上
> 3. **首个跨阶段协议模板落地** —— 见 `docs/superpowers/specs/verifier-protocol-template.md`，建议首个应用为 `rdd-arch` 的 gap analysis（oracle Q3 建议）
>
> 以上三项不纳入本 change 实施，作为下个 release 决策输入。
