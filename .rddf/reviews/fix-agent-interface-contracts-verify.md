# 验收报告 — fix-agent-interface-contracts

- **日期**：2026-11-05
- **验收角色**：`verifier`（source: user）
- **被验对象**：`openspec/changes/fix-agent-interface-contracts`（已实施并提交，4 个 commit：`ab7c3ac` / `bf07943` / `ac96d9f` / `078f341`，base = `96af162`）
- **已用轮次**：1 / 3

## 判据来源

1. 用户本次验收条件：无单独声明（「按建议路径实施」）
2. `proposal.md` 的 `## 验收标准`（**20 条 AC**）
3. `tasks.md`：6 Task / **26 个 Step 全部勾选**
4. `specs/` delta：9 条 Requirement（`agent-interface-contracts` 7 + `skill-role-model` 2）

## 分流判定

| 条件 | 结果 |
|---|---|
| change 有 `## 验收标准` 段 | ✅ |
| P3 archive gate（`discover_eligible()` 口径：`status ∈ {in_worktree, completed}` + `tasks_done == tasks_total > 0` + 未归档） | ❌ 该 change 未登记 `iteration.json`（`changes[]` 里 15 条全是历史 archived） |
| `rdd-verifier` 可加载 | ✅ |

→ **走本地验收 1–5 步**（`rddf rdd-verify --dry-run` = `No eligible changes to verify (empty queue)`，与上表一致）。「额外门」由 `tasks.md` 取证：未勾选 Step = 0。

## 逐条判定

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 v4 arch-only → 三处一致返回 `rdd-planner` | ✅ | `bats tests/_lib/test_scan_state.bats tests/integration/scan_state.bats` → 29/29 ok；`pytest test_workflow_synthesizer_planner_path.py test_stage_consumers_agreement.py` → 含 arch-only → `synthesize().suggested_action == "rdd-planner"` |
| AC-2 v4 arch+planner → 三处一致 `rdd-builder`，REASON 不含「设计阶段」「残留」 | ✅ | 同上 bats 集；`pytest` 覆盖 planner-handoff 路径 |
| AC-3 本仓形态 → guide 推荐非「残留 → ship 清理」 | ✅ | `rddf guide` → `💡 建议: rdd-builder`（无「残留」字样）；`grep -iE '残留'` 无命中 |
| AC-4 v3 项目 → `rdd-builder` + 输出含 `legacy` | ✅ | bats 用例 `scan_state: v3 plan-handoff without planner-handoff falls back with warning` 断言 `RECOMMEND=rdd-builder` 且输出含 `legacy` |
| AC-5 损坏 `.planner-handoff.json` → 不当完成 | ✅ | 截断 JSON 实跑：`💡 建议: rdd-planner` + `planner-handoff 损坏（JSON 无法解析）→ 视为 planner 未完成，回到 planner 阶段`；bats 用例 `corrupt planner-handoff → rdd-planner (not treated as complete)` |
| AC-6 `rddf guide` 端到端（v4 arch-only 临时项目） | ✅ | 临时项目仅放 `.arch-handoff.json` → `💡 建议: rdd-planner` |
| AC-7 owns 行内括注清零 | ✅ | `grep -rnP '^\s*-\s*"[^"]*\(' skills/*/SKILL.md` → **0 行** |
| AC-8 schema 拒绝括号 / 接受 4 种合法形态 | ✅ | `owns.items.pattern = ^[^()]+$`；直接实测 6/6 与期望一致：`{tasks,design}.md` / `a/*` / `a/**` / `<name>.md` ACCEPT，`x(y).md` / `a.md (note)` REJECT |
| AC-9 全部含 `role:` 的 SKILL.md 通过 schema 校验 | ✅ | 实跑 7 个 skill（`rdd-arch` / `rdd-builder` / `rdd-env-bootstrap` / `rdd-planner` / `rdd-quick` / `rdd-session-bootstrap` / `rdd-verifier`）→ 校验失败 **0** |
| AC-10 `rdd-builder` owns 不含 `design.md` + 正文有归属说明 | ✅ | `sed -n '/^role:/,/^---/p' skills/rdd-builder/SKILL.md \| grep design` → 无输出；`SKILL.md:53` 「`design.md` —— **不由本 skill 生成**（P1 `phase1_plan.sh` 只补 `tasks.md`）；`SKILL.md:17` 同步更新为 P1 fill outputs |
| AC-11 `rddf status` 总览表有 `BUILDER` 列 | ✅ | 表头 `NAME … STATUS TASKS PLAN BUILDER` 可见；archived 行显示 `-` |
| AC-12 builder state 损坏 → `BUILDER` 显示 `-`，exit 0 | ✅ | `pytest test_status_builder_column.py` 5 例通过，含 `test_builder_phase_corrupt_state_is_dash` / `test_builder_phase_missing_state_is_dash` / `test_builder_phase_archived_is_dash` |
| AC-13 `rddf builder status <change>` 输出不变 | ✅ | `rddf builder status add-guide-polling-loop-implementation` → `phase: phase-3` / `retry_count: 0 / 3` / `pause_history entries: 0`（既有入口未破坏） |
| AC-14 无关脏文件 → P2 继续执行 | ✅ | `bats tests/integration/test_phase2_commit_gate.bats` → `ok 1 unrelated dirty file does not block Phase 2` |
| AC-15 产物未 commit / 未 staged → P2 继续 | ✅ | 同上 `ok 2 uncommitted change artifacts do not block Phase 2`；`ok 3 script no longer mentions COMMIT GATE` |
| AC-16 `check_worktree_commits` 仍拒绝无新 commit 分支 | ✅ | 同上 `ok 7 archive: check_worktree_commits still refuses a branch with no new commits` + `ok 8 … accepts a branch with new commits` |
| AC-17 pytest unit / integration **无新增失败** | ✅ | unit：`3267 passed, 2 skipped`（172.87s，0 failed）；integration：`201 passed`（186.17s，0 failed） |
| AC-18 bats 全量新增失败 = 0 | ✅ | `bash tests/scripts/report_regression.sh` → 已知失败 11 / **新增失败 0** / zombie 0，exit 0 |
| AC-19 实改路径 == File Map（双向差集） | ✅ | `git diff --name-only 96af162..078f341` = 32 条，File Map File 列 = 32 条；`comm -23`（改了不在 Map）空、`comm -13`（在 Map 未改）空 |
| AC-20 `openspec validate` | ✅ | `Change 'fix-agent-interface-contracts' is valid`（exit 0） |

**合计：20 ✅ / 0 ⚠️ / 0 ❌**

## 验证顺序与边界覆盖

| 步骤 | 内容 | 结果 |
|---|---|---|
| 1 静态检查 | `openspec validate` + schema 全量校验（7 skill） | ✅ |
| 2 单元测试 | `pytest tests/unit/` 3267 passed；本 change 相关 4 文件 29 passed | ✅ |
| 3 集成 / 端到端 | `pytest tests/integration/` 201 passed；bats 全量 269 文件新增失败 0；`rddf guide` 端到端（临时 v4 arch-only 项目 + 损坏 handoff 项目） | ✅ |
| 4 边界与错误路径 | 损坏 planner-handoff（AC-5）、缺失 / 损坏 / archived 的 builder state（AC-12）、无关脏文件 + 未提交产物（AC-14/15）、worktree 产物带出的 2 个边界（dst 已存在 / src==dst，见 `test_phase2_commit_gate.bats` ok 4–6）、`check_worktree_commits` 正反两向（AC-16） | ✅ |
| 5 遗留清扫 | 见下 | ✅ |

## 遗留清扫（本 change 实改的 32 个路径）

| 项 | 结果 |
|---|---|
| `TODO` / `FIXME` / `XXX` / `HACK` 标记 | 2 处命中，均在 `CHANGELOG.md`（第 223 / 514 行）—— **历史变更记述**，不是遗留标记 |
| 调试残留（`breakpoint()` / `import pdb` / `set_trace()`） | 0 |
| 被 skip 的测试（`@pytest.mark.skip` / `skipif` / `xit`） | 0 —— 4 处文本命中均为普通代码（`cd "$repo" \|\| exit 1` 等） |
| 未替换的 mock | 未发现新增 mock |

## 观察项（不影响判定）

1. **`iteration.json` 缺该 change 条目** —— 直接后果：`rdd-verifier` skill 路径的判据条件 2 不成立（`discover_eligible()` 空队列），本报告走本地验收。归档时 `verifier_contract_check` 会返回 `verification missing` → 默认 legacy fallback（`RDDF_REQUIRE_VERIFIER_CONTRACT=no`）仅 warning，不阻断；但 `mark_iteration_archived` 同样找不到条目 → 归档后 iteration.json 仍缺该记录。**归档前应先补 iteration 条目**（`status=completed` + `tasks_done == tasks_total`）。
2. **tasks Step 6.3 的外部 e2e 测试床 `<rdd-workflow-e2e-repo>` 在本机不存在** → 该项无法执行（AC-17/18 未列该判据，故不影响判定）。
3. **`skills/_lib/schemas/` 已随批 C（`remove-dead-dup-layer`）删除** —— AC-9 的取证走 canonical `_lib/schemas/skill_role_schema.json`，与现状一致。

## 结论

**PASS** —— 20 条 AC 全部满足，遗留清扫干净，全量回归（bats / pytest unit / pytest integration）零新增失败。

按审查配对规则，本 change 的 verifier 环节完成。归档（rdd-builder P3）前需先补 `iteration.json` 条目（见观察项 1）。
