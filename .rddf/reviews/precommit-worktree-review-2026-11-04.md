# 提交前工作区审查 — 4 条工作线分批提交

- **日期**：2026-11-04
- **审查角色**：`verifier`（source: user）
- **被审对象**：工作区未提交变更（145 个路径 = 122 个已跟踪改动 + 23 个新增文件）
- **判据来源**：
  1. 用户本次条件：「审查项目变更内容，并分批提交」
  2. 三个已验收 change 的 `proposal.md` / `tasks.md`（见 §2）
  3. `CHANGELOG.md` 未发布段落对每条工作线的自述

## 1. 结论

| # | 判定 | 说明 |
|---|---|---|
| 1 | ⚠️ **1 个必须修的缺陷** | `skills/rdd-planner/SKILL.md` 误删 ADR-0051 要求的 `Boundary ownership` 引用行 → 见 §4 F-1 |
| 2 | ✅ 3 条 change 可提交 | 各自已有独立验收报告（PASS）+ 全量回归 ALL PASSED |
| 3 | ⚠️ 1 条工作线未经验收 | ADR-0060 形态契约 —— 无 change / 无验收报告 → 见 §3 D 批 |
| 4 | ✅ 可拆 5 批提交 | 映射见 §2；3 个文件需 hunk 级拆分 |

## 2. 变更全景 —— 5 批

工作区混着 **4 条独立工作线 + 1 组流程工件**。逐条追溯到 `tasks.md` 的文件清单后，边界清晰。

### 批 A — `fix-test-isolation-and-hygiene`

测试零污染 + 根解析归位 + 仓库卫生 + doctor `plan-tdd` 降噪。验收：`.rddf/reviews/fix-test-isolation-and-hygiene-verify.md`（18 ✅ / 1 ⚠️ 已闭合）。

| 类别 | 文件 |
|---|---|
| 根解析归位 | `_lib/_python_resolve_project_root.py`（自 `skills/_lib/` 搬入）、`_lib/_resolve_project_root_contract.yaml`（同上）、`skills/_lib/_python_resolve_project_root.py`（新 identity-merge shim）、`skills/_lib/_resolve_project_root_contract.yaml`（新指针文件） |
| resolver 锚点 | `_lib/cli/__main__.py`（**hunk 1-3**：`start_dir` 锚点 + `_fallback_root`） |
| 路径修复 | `skills/deps/scripts/cross_repo_cli.py`、`skills/rdd-quick/scripts/append_history.py` |
| doctor 降噪 | `skills/rdd-doctor/scripts/checks/plan_tdd_check.py` |
| 仓库卫生 | `.gitignore`（+`skills/.rddf/`）、删 `python3`、删 `.gitignorebash`（均 0 字节垃圾） |
| 测试 | `tests/integration/test_rddf_cross_repo_cli.bats`、`tests/unit/test_project_root_resolution.py`(新)、`tests/unit/test_quick_history_path.py`(新)、`tests/unit/test_quick_history.py`、`tests/unit/test_doctor_plan_tdd_scope.py`(新) |
| 工件 | `.rddf/roadmap/features/feat-fix-test-isolation-and-hygiene.md`(新)、`CHANGELOG.md`（本节） |

### 批 B — `fix-v4-residue-contract`

契约面 v4 残留修复。验收：`.rddf/reviews/fix-v4-residue-contract-verify.md`（15 ✅ / 0 ⚠️）。

| 类别 | 文件 |
|---|---|
| 失败路由 | `skills/rdd-verifier/scripts/route_loop.sh`、`skills/rdd-verifier/SKILL.md`、`_lib/cli/rdd_verify_cmd.py` |
| schema enum | `_lib/schemas/verifier_loop_schema.json`（**hunk 2** route enum）、`_lib/schemas/iteration_schema.json`（**hunk 3** route enum）、`_lib/schemas/feedback_entry_schema.json`（**hunk 2** source enum） |
| 用户可见文案 | `_lib/gate.py`、`_lib/cli/__main__.py`（**hunk 4** help 文案）、`_lib/cli/__init__.py`（**hunk 2** discover-ship-changes 描述）、`_lib/cli/{sessions,discover_ship_changes,orchestrate,report_issue}_cmd.py`、`skills/execute/scripts/execute_step7.py`、`skills/feature/scripts/{feature_cli,feature_view}.py`、`_lib/schemas/plan_handoff_schema.json`（**hunk 2** description） |
| 守卫 | `skills/rdd-doctor/scripts/checks/v4_residue_check.py`(新)、`skills/rdd-doctor/scripts/{SKILL.md,scripts/doctor_main.py}`、`skills/rdd-doctor/scripts/checks/{state_schema_check.py（hunk 2-4）,tasks_checkbox_check.py}`、`_lib/docs_consistency.py` |
| 测试 | `tests/unit/{test_feedback_schema_sources,test_v4_residue_check,test_verify_route_values}.py`(新)、`tests/unit/{test_docs_consistency,test_rdd_verify_cmd,test_verifier_loop_schema}.py`、`tests/integration/test_feature_skill.bats`、`tests/integration/test_rdd_doctor_skills_md_sync.bats`、`tests/integration/test_rdd_verifier_{e2e,helpers,loop,self_contained}.bats` |
| 工件 | `.rddf/roadmap/features/feat-fix-v4-residue-contract.md`(新)、`CHANGELOG.md`（本节） |

### 批 C — `remove-dead-dup-layer`

删除 `skills/_lib/` 陈旧重复层。验收：`.rddf/reviews/remove-dead-dup-layer-verify.md`（17 ✅ / 1 ⚠️ 无影响）。

| 类别 | 文件 |
|---|---|
| 删副本 | `skills/_lib/iteration/{archive_sidecar,l2,post_archive,render,repair,schema,store}.py`（7）、`skills/_lib/schemas/*.json`（20） |
| 活契约搬移 | `_lib/schemas/{populate_state,populate_supplementary,rfc_draft}_schema.json`（自 `skills/_lib/schemas/` 搬入；内容逐字节不变，`rfc_draft` 仅同步 `$id`） |
| 删失效代理 | `skills/guide_arch.py`、`skills/guide_plan.py`、`skills/populate_roadmap_from_arch.py` |
| 清死注册 | `_lib/cli/__init__.py`（**hunk 1** `_DASH_SKILLS`）、`tests/conftest.py`、`skills/__init__.py` |
| 修路径算术 | `_lib/populate_lib.py`（`parents[2]`→`parents[1]`，恢复被静默跳过的 jsonschema 校验）、`_lib/iteration/schema.py`（docstring 路径） |
| schema 归一 | `_lib/schemas/*.json`（30 个实际变更：34 个补 `{"const":"vN"}` 版本元数据 + `verifier_audit_schema.json` 非法 JSON 修复 + `iteration_schema.json` 补 `cross_repo_dependencies`） |
| 文档 | `docs/schemas/README.md`、`docs/ONBOARDING.md`、`docs/improvement-suggestions-format.md`、`skills/rdd-doctor/scripts/checks/state_schema_check.py`（**hunk 1** docstring） |
| 测试 | `tests/unit/test_no_stale_dup_layer.py`(新)、`tests/unit/test_populate_schema_path.py`(新)、`tests/unit/{test_schema_version_field,test_arch_handoff_schema_v2,test_iteration_v7,test_rfc_interview_flow,test_session_metrics,test_ac_verdict_cache_schema,test_env_bootstrap_report}.py` |
| 工件 | `.rddf/roadmap/features/feat-remove-dead-dup-layer.md`(新)、`CHANGELOG.md`（本节） |

### 批 D — ADR-0060 形态契约 + 门禁降级（**未走 change 流程**）

| 文件 | 说明 |
|---|---|
| `docs/adr/ADR-0060-adr-shape-contract-and-gate-demotion.md`(新) | 99 行；Context / Decision / Consequences（正面·负面·待办）/ Verification / References 齐备；备选方案表 5 行（结论 + 理由）→ 符合「architect 产出形态契约」四要素 |
| `docs/adr/README.md` | ADR 索引同步（含 ADR-0059 既有漂移一并修正） |
| `docs/adr/ADR-0000-template.md` | 模板新增 `## Verification` + 备选方案表改三列 |
| `skills/rdd-arch/SKILL.md` | Phase 2 advisory 模式 + 4 条形态约束锚点 |
| `skills/rdd-arch/scripts/adr_gate.sh` | 新增 `ADR_GATE_MODE=advisory\|block` / `ADR_GATE_CLASS=`；分类逻辑不变 |
| `skills/rdd-arch/scripts/adr_shape_check.sh`(新) | 独立 CLI（`--strict` exit 1） |
| `skills/rdd-arch/scripts/arch_quality_report.sh` | 第 5 项检查 opt-in 说明 |
| `_lib/arch_quality_gate.py` | 新增 `_check_adr_shape()`（行数 / 必备章节 / 过程日志 / Status 长度） |
| `tests/unit/test_arch_quality_gate.py` | +133 行 |
| `tests/integration/test_adr_gate.bats`、`test_adr_gate_flow.bats` | +31 / +43 行 |

### 批 E — 流程工件与聚合文档

| 文件 | 说明 |
|---|---|
| `AGENTS.md`、`.rddf/roadmap.md` | `rddf roadmap --update-agent-md` 自动生成段（feature fragment 索引 + phase 描述同步）→ 聚合产物，放最后一批 |
| `.rddf/reviews/{fix-test-isolation-and-hygiene,fix-v4-residue-contract,remove-dead-dup-layer}-verify.md`(新) | 3 份验收报告 |
| `.rddf/improvements/add-scope-bootstrap-agent.md`(新) | **与上述 4 条工作线无关**的新 improvement 草稿（ChipForge scope-bootstrap 提案）→ 单独成批 |
| `skills/rdd-planner/SKILL.md` | 见 §4 F-1 |

## 3. 需要 hunk 级拆分的文件（3 个）

以下文件同时被两条工作线修改，整文件提交会把 A/B/C 混在一起：

| 文件 | 拆分 | 手法 |
|---|---|---|
| `_lib/cli/__main__.py` | A（hunk 1-3）/ B（hunk 4） | hunk 天然分离（`resolve_project_root` vs `--help` 文案） |
| `_lib/cli/__init__.py` | B（hunk 2）/ C（hunk 1） | hunk 天然分离（`_SUBCOMMAND_DESCRIPTION` vs `_DASH_SKILLS`） |
| `skills/rdd-doctor/scripts/checks/state_schema_check.py` | B（hunk 2-4）/ C（hunk 1） | hunk 天然分离（fix_hint 文案 vs docstring） |

`_lib/schemas/` 下的 4 个 schema 虽然也跨批（version 元数据 = C，enum = B），但 hunk 同样天然分离。

## 4. 发现

### F-1 ⚠️ BLOCKER — `skills/rdd-planner/SKILL.md` 误删 ADR-0051 要求的边界引用行

**改动内容**：删掉了 frontmatter `description` 里的两行：

```
-  Default: auto-decision per ADR-0050; writes `.rddf/state/.planner-handoff.json` at stage exit.
-  Boundary ownership: see role.boundaries.owns / not_owns.
```

**问题分两半**：

1. ✅ 删 `Default:` 那行是**对的** —— ADR-0050 的标题是「rdd-builder / rdd-quick 全自动决策模式」，与 `rdd-planner` 无关（它讲的是 builder/quick 的 P0 自动选 1-5）。rdd-planner 引用 ADR-0050 属于**事实性错误引用**，删掉正确。
2. ❌ 删 `Boundary ownership:` 那行是**错的** —— ADR-0051 Decision 4 明确要求 description 引用 `role.boundaries.owns / not_owns` 作为 SSOT 指针；`tests/integration/test_skill_description_convention.bats` 第 3 个用例（`every SKILL.md description references role.boundaries`）逐文件 grep `role\.boundaries\.owns|see role\.boundaries|Boundary ownership`，**整份文件**都不命中即失败。

**证据**：

```
$ bats tests/integration/test_skill_description_convention.bats
not ok 3 every SKILL.md description references role.boundaries
# MISSING: skills/rdd-env-bootstrap/SKILL.md does not reference role.boundaries
# MISSING: skills/rdd-planner/SKILL.md does not reference role.boundaries
```

- `skills/rdd-env-bootstrap/SKILL.md` 的缺失是 **HEAD 上已存在**的问题（stash 后在 HEAD 复跑确认），与本次变更无关。
- `skills/rdd-planner/SKILL.md` 的缺失是**本次变更引入的新增违规**。
- 该用例在 HEAD 上**本就失败**（不是绿），所以 `report_regression.sh` 的「新增失败 = 0」**测不出来** —— 这类「在已失败用例里新增违规」必须靠人工比对，不能只看回归门。

**修法**：把 `Boundary ownership: see role.boundaries.owns / not_owns.` 一行加回 `skills/rdd-planner/SKILL.md` 的 `description` 块（保留删除 `Default:` 那行）。description 体积从 42 token 涨到约 48 token，仍远低于 ADR-0051 的 200 token 预算。

**归属**：实现修改 → `builder` 角色；`verifier` 不改实现。

### F-2 ⚠️ 观察 — 批 D（ADR-0060）未走 change 流程，无验收报告

ADR-0060 有完整的 ADR + 实现 + 测试，但**没有 openspec change、没有 improvement 提案、没有验收报告**。本批的 4 个 bats + 36 个单测实测全绿（见 §5），且 ADR 形态符合「architect 产出形态契约」四要素，可以提交；但它是**流程外产物**，建议后续补登记 improvement（不阻断本次提交）。

### F-3 ⚠️ 观察 — ADR-0060 自身被自己的形态检查判为不合规

`adr_shape_check.sh` 报 `ADR-0060-...: 过程日志标记 4 处`。逐条核对为**误报**：命中的 4 处都在 Context / Consequences 里**引用**了「第 N 轮 critic / BLOCKER / SHOULD_FIX / NIT」这些词本身（ADR 在描述「什么算过程日志」）。ADR-0060 第 72 行已自陈该启发式的局限（warning 级，可接受）。**不阻断**。

### F-4 ⚠️ 观察 — feature fragment 状态漂移

`.rddf/roadmap/features/feat-{fix-test-isolation-and-hygiene,fix-v4-residue-contract,remove-dead-dup-layer}.md` 的 `status:` 仍是 `proposed`，但三者均已实施并验收通过；对照 `feat-fix-agent-interface-contracts` 已标 `in-progress`。状态推进属 planner 职责，**本次不改**，仅登记。

### F-5 ⚠️ 观察 — `skills/_lib/gh_repo_detect.py`（138 行完整实现）仍住在 shim 层

已在批 C 的守卫豁免清单里显式登记（有单测锁住豁免规模 ≤ 3）。**不在本次范围**，沿用上一轮结论。

## 5. 证据

| 项 | 证据 |
|---|---|
| 全量回归门（上一轮，验收时） | `./test.sh --full --regression` → ALL PASSED（bats 新增失败 0 / unit 3267 passed / integration 201 passed） |
| 本次复核 unit | `python3 -m pytest tests/unit/ -q` → **3267 passed, 2 skipped** in 125.81s |
| 本次复核 ADR-0060 单测 | `pytest tests/unit/test_arch_quality_gate.py -q` → **36 passed** |
| 本次复核 ADR-0060 bats | `bats tests/integration/test_adr_gate.bats tests/integration/test_adr_gate_flow.bats` → 17/17 ok |
| doctor v4-residue | `./rddf doctor --category v4-residue` → ✅ All 1 categories OK |
| 遗留清扫 | 变更文件中无 TODO/FIXME/XXX/HACK、无 `breakpoint()`/`pdb`、无临时 debug print、无被 skip 的新测试 |

## 6. 结论

- **批 A / B / C**：证据齐备（各自独立验收报告 + 回归门全绿 + 本次复核），**可提交**。
- **批 D**：实现与测试齐备、形态合规，**可提交**（流程外产物已登记为 F-2）。
- **批 E**：聚合文档 + 3 份验收报告 + 1 份无关 improvement 草稿，**可提交**。
- **F-1 必须先修**：`skills/rdd-planner/SKILL.md` 加回 `Boundary ownership` 行（1 行改动）。

修复 F-1 后即可按 A → B → C → D → E 顺序分 5 批提交；每批独立 commit message，不使用 `git add -A`。

## 7. 执行结果（2026-11-04，builder 角色）

F-1 已修（`e066f16`），其余按 A → B → C → D → E 拆成 **8 个 commit** 落地：

| commit | 批次 | 内容 |
|---|---|---|
| `2de1ab5` | A | `fix(hygiene): stop tests from writing into real project state` |
| `da9035e` | B | `fix(v4-residue): point the contract surface at v4 skills, and guard it` |
| `d31bfb6` | C | `refactor(_lib): delete the stale duplicate layer under skills/_lib` |
| `4b5a971` | D | `feat(arch): contract the shape of decision documents, demote the keyword gate` |
| `e066f16` | E1 | `fix(skills): drop the wrong ADR reference from rdd-planner's description`（F-1） |
| `fcc39c8` | E2 | `docs(roadmap): sync the feature fragment index` |
| `c8b5be3` | E3 | `docs(review): archive the acceptance reports for the three shipped changes` |
| `fc608c9` | E4 | `docs(improvement): add the scope-bootstrap proposal draft` |

### 7.1 拆分过程中新发现并修复的两个缺陷

审查阶段只做了**静态**分类，提交阶段每批都在 **linked worktree 的暂存区树**里独立跑测试 —— 暴露出两个静态审查看不到的问题：

1. **F-6｜批 A 的新测试不 worktree-safe**：canonical resolver 按 ADR-0033 设计，linked worktree 下返回**主仓根**（不是 worktree 目录）。`test_project_root_resolution.py` 却断言锚点结果等于 `REPO_ROOT`，在 worktree 模式下必失败。→ 改为与 resolver 自身对同一仓库的答案比对（`e066f16` 之前的 `2de1ab5`）。
2. **F-7｜批 A 的 cross-repo bats 在 worktree 模式下误判并污染主仓**：该用例把「项目根」硬编码为 `$REPO_ROOT`，而默认 cache 实际落在主仓 `.rddf/state/`（resolver 语义）。结果：用例在 worktree 目录找不到文件（红），同时把缓存留在**主仓**的 state 里（污染）—— 正是本 change 要消灭的那类污染。→ 改为向 resolver 询问项目根，并按真实落点清理。（`2de1ab5`）

> 两者的共同点：**「项目根」在 worktree 语境下有两个答案**（worktree 目录 vs 主仓根），canonical resolver 选后者。凡是拿 `$REPO_ROOT` 当项目根的断言/路径假设，都要改成问 resolver。

另有 2 处**归批错误**在同轮被发现并纠正（都是版本归一化断言，属于批 C 而非 A/B）：`tests/unit/test_quick_history.py`、`tests/unit/test_verifier_loop_schema.py`。

### 7.2 每批的独立验证

每批提交前，把**暂存区树**（`git write-tree`）建成临时 linked worktree 跑测试 —— 不是跑工作区（工作区含全部 5 批，测不出单批是否自洽）：

| 批 | worktree 模式 unit 失败 | 对比 HEAD 基线（11） |
|---|---|---|
| A | 11 | 无新增 |
| B | 11 | 无新增 |
| C | 11 | 无新增 |
| D | 11 | 无新增 |
| E | 11 | 无新增 |

基线 11 个失败是 **HEAD 上既有的 worktree 脆弱性**（6 个 resolver 契约用例 + 4 个 `doc_contracts` 用例因 `openspec/` 被 gitignore 而看不到 change 目录 + 1 个），与本次 5 批无关。

### 7.3 提交后最终回归门

| 项 | 结果 |
|---|---|
| bats regression | 已知失败 11 / **新增失败 0** / zombie 0 |
| pytest unit | **3267 passed, 2 skipped** |
| pytest integration | **201 passed** |
| 路径完整性 | 最终 diff 的 21 个新增路径 = 提交前 17 个未跟踪文件 + 4 份报告；3 个 rename = 搬移的 schema/resolver。**无路径丢失，无凭空新增** |
| 工作区 | `git status` 干净 |

### 7.4 遗留（不在本次范围，已登记）

- **F-2** ADR-0060 未走 change 流程（无 openspec change / 无 improvement 提案 / 无独立验收报告）→ 建议后续补登记。
- **F-3** ADR-0060 自身被形态检查判为「过程日志标记 4 处」→ 误报（它在 Context 里引用了 "critic / BLOCKER / SHOULD_FIX / NIT" 这些词本身来说明检测什么），ADR 第 72 行已自陈该启发式局限，保持不动。
- **F-4** 3 个 feature fragment 的 `status:` 仍是 `proposed`，但三者均已实施并验收 → 状态推进属 planner 职责，未改。
- **F-5** `skills/_lib/gh_repo_detect.py`（138 行完整实现）仍住在 shim 层 → 已在批 C 的守卫豁免清单中显式登记，沿用上一轮结论。
- **worktree 脆弱性（11 个）** HEAD 既有问题：resolver 契约用例在 linked worktree 下断言 worktree 目录、而 resolver 返回主仓根（与 F-6/F-7 同源）；`doc_contracts` 用例依赖被 gitignore 的 `openspec/`。建议独立立项修，因为它会让 `rdd-builder` 的 worktree 执行模式跑测试时必红。
