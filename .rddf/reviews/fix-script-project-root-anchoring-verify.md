# fix-script-project-root-anchoring — 验收报告

- **change**：`fix-script-project-root-anchoring`（C2 根因）
- **验收日期**：2026-11-18
- **验收角色**：builder（角色内建 verifier）
- **判据来源**：`.rddf/improvements/fix-script-project-root-anchoring.md` 的 `## Acceptance`（14 条）
  与 `openspec/changes/fix-script-project-root-anchoring/proposal.md` 的 `## Acceptance`（同一份）
- **实现**：`a3df546`（worktree）→ `443f689`（合入 master）
- **归档**：`openspec/changes/archive/2026-11-18-fix-script-project-root-anchoring`（specs +13 需求）

---

## 0. 立项时纠正了原归因（这一节是本次验收最需要复核的部分）

C2 此前被记成「`tests/integration/test_approve_proposal.bats` 用 `cd "$REPO_ROOT"` 只隔离
`TMP_STATE` ⇒ 真实 `openspec/` 被写」。**实测不成立**：

```bash
marker=$(mktemp); sleep 1
bats tests/integration/test_approve_proposal.bats
find openspec .rddf -newer "$marker" -type f     # → 空
```

原因（读代码即可确认）：用例 1 在参数校验处就 `exit 2`（早于任何写盘）；用例 2 设了
`RDDF_PROJECT_ROOT`；而 `scripts/approve_proposal.sh` 只写 `$RDDF_PROJECT_ROOT/.rddf/state/`，
**从不碰 `openspec/`**。同轮扫描的 21 个「archive / phase / approve」候选 bats 文件里，
**没有一个写 `openspec/`**。

⇒ 立项改成**已证实**的那一层：脚本不锚定 `PROJECT_ROOT`。范围、验收标准、门禁设计随之重写。

## 1. 逐条判定（14 AC，全 pass）

| # | 判据 | 判定 | 证据 |
|---|---|---|---|
| AC-A | 读方向：`phase1_plan.sh` 读 `$PROJECT_ROOT` 的 proposal | ✅ | 用例「PROJECT_ROOT 指向假仓 ⇒ 读假仓的 proposal」：改前 rc=2（`proposal.md not found`，它在真仓里找），改后进入后续步骤并在假仓生成 `tasks.md` |
| AC-B | 写方向：写落点跟随 `$PROJECT_ROOT` | ✅ | 用例断言假仓出现 `tasks.md` 与 `.rddf/plans/`；真仓那两条路径零写入（marker + `find`，**只扫这两条路径** —— 全仓扫描会被并联 session 的写误判，本次立项时已实证） |
| AC-C | `phase1_5_deps.sh` 的 legacy 读取锚定 | ✅ | 用例：真仓与假仓各放一份不同 `execution_mode`，断言 stderr 的 `legacy ... execution_mode='lightweight'` 反映**假仓**那份 |
| AC-D | `phase2` 降级路径（**活 bug**） | ✅ | 用例「lightweight 降级回 worktree ⇒ worktree 建在 PROJECT_ROOT」。**改前该用例是红的，并真的在真仓留下 `openspec/demo` 分支 + 一个 prunable worktree 条目**（已手工清理）。修法比计划多一步：路径锚定**不够** —— `git worktree add` 注册到**当前目录**的仓 ⇒ 降级路径补 `cd "$PROJECT_ROOT"` |
| AC-E | 门禁正例：未锚定 ⇒ `exit 1` 且报 `file:line` | ✅ | 用例（单 check 模式 `RDDF_ISOLATION_ONLY`）：`status != 0` 且输出含 `x.sh:` |
| AC-F | 门禁豁免 + 变异 | ✅ | 用例：行尾 `# isolation-ok:` ⇒ 放行。**变异**：删掉 `phase2_execute.sh:100` 的标记 ⇒ 「豁免恰好 2 条」用例变红 ⇒ 豁免机制真的生效 |
| AC-G | token 级判定（防门空转） | ✅ | 用例：同行混有未锚定与已锚定 token 时仍报。**变异**：把判定改成行级（同行有锚点即整行放行）⇒ 该用例变红 |
| AC-G2 | 新 check 单独跑在本仓 ⇒ `exit 0` | ✅ | `RDDF_ISOLATION_ONLY=check_no_unanchored_repo_paths bash tests/scripts/check_test_isolation.sh` ⇒ exit 0（豁免恰好 2 条） |
| AC-H | 豁免预算 = 2 条且理由 ≥10 字 | ✅ | 用例断言 `grep -h '# isolation-ok' skills/rdd-builder/scripts/*.sh` 恰为 2 条；实际：`phase2_execute.sh:100`（相对片段）、`phase0_approval.sh:327`（描述字段） |
| AC-I | bypass 可计量 | ✅ | 用例：输出含 `skipped: check_no_unanchored_repo_paths` **且** `.rddf/state/.bypass-audit.jsonl` 新增一条 |
| AC-J | 生产路径不退化 | ✅ | 用例在「`tasks.md` **不存在**」场景断言生成内容一致（已存在时脚本根本不写，断言会恒真）；既有 `test_phase_auto_approve.bats` / `test_phase0_auto_approve.bats` / `test_rdd_builder_phases.bats` / `test_phase0_iteration_register.bats` / `test_lightweight_branch_and_archive.bats` 全绿（59 例） |
| AC-K | 既有测试 | ✅ | 上列 5 个文件 59 例全绿 + 本 change 新文件 11 例全绿 |
| AC-L | 全量门 | ✅ | `./test.sh --full --regression --no-color`（master，`443f689` 之后）：`评估 257/257 个文件`、`未评估 0`、`已知失败 11`、`新增失败 0`、`已修复 0`；pytest unit 3424 passed / 2 skipped；pytest integration 196 passed；**ALL PASSED / EXIT=0** |
| AC-M | 不改 CI | ✅ | `git diff bc2c96b..443f689 --stat -- .github/workflows/test.yml` ⇒ 空（新 check 挂在 `test.yml` 已调用的脚本里） |

## 2. 全量回归门

```
=== bats regression (baseline-aware) ===
📊 评估 257/257 个文件（scope: tests/integration/*.bats；仓库另 27 个 .bats 不在本门范围）
   未评估: 0 个文件
已知失败: 11
新增失败: 0
已修复 (zombie): 0

✅ 0 新增失败
✅ bats regression (baseline-aware) OK (508s)
✅ pytest unit OK (100s)          ← 3424 passed, 2 skipped
✅ pytest integration OK (102s)    ← 196 passed
✅ ALL PASSED / EXIT=0
```

> 注：在 **worktree** 里跑同一道门会有 10 条 pytest unit 失败
> （`test_doc_contracts.py` ×4、`test_resolve_project_root_contract_python.py` ×6、
> `test_skills_lib_python_resolve_project_root.py` ×1）。已核实它们**与本改动无关**：
> `openspec/` 被 gitignore ⇒ worktree 里没有 `openspec/specs/general/spec.md`；
> 而 canonical resolver 返回**主仓**根、测试却拿 worktree 的 `PROJECT_ROOT` 去比。
> 在 master 上这 3 个文件 **37 passed**。⇒ 本仓惯例：**合入 master 后在 master 上跑全量门**。

## 3. 变异测试

| # | 变异 | 结果 |
|---|---|---|
| M1 | 删掉 `phase2_execute.sh:100` 的 `# isolation-ok:` 标记 | ✅ 「豁免恰好 2 条」用例变红 |
| M2 | token 级判定改成行级（同行有锚点即整行放行） | ✅ 「token 级」用例变红 |

## 4. 遗留清扫

| 项 | 结论 |
|---|---|
| TODO / FIXME / 占位符 | 本次改动内 0 处 |
| 注释掉的代码 / 临时调试日志 | 0 |
| 被 skip 的测试 | 0（未新增 skip） |
| 未替换的 mock | 无 |
| 临时代码 | 测量脚本、门禁备份都在 `/tmp/opencode/`，未入库 |
| 计划外的改动 | **有 1 处并已记录**：AC-D 的修法比计划多一步 —— 计划只说「`WT_PATH` 用 `$PROJECT_ROOT/...`」，实测发现 `git worktree add` 注册到**当前目录**的仓 ⇒ 追加 `cd "$PROJECT_ROOT"`。这是同一个 bug 的第二层，不追加则降级路径仍会污染调用方的仓 |
| 顺带修掉的既有污染 | `phase2` 降级路径修好后，既有测试 `test_lightweight_branch_and_archive.bats` **不再**在真仓留下 `openspec/<name>` 分支 + prunable worktree 条目（此前每次跑都会产生、无人清理） |
| 范围外的发现 | 见 §5 第 1 条（master 的隔离门已经红了，CI 也就红了）—— 记录，未在本项修 |

## 5. 本次不做（留给后续）

1. **master 的隔离门已经红了**（9 处历史违规），CI 的「断言质量门」因同一批 `or True` 也红
   ⇒ **CI 在 master 上已经是红的**；而 `./test.sh` 不跑隔离门 ⇒ 本地全量门看不到 ⇒ 变红无人发现。
   清单：`tests/unit/test_project_root_resolution.py:11`、
   `tests/unit/test_proposal_source_tracking.py:48/:57`、
   `tests/integration/test_guide_cross_container.bats:75`、
   `tests/unit/test_bypass_audit.py:31`、4 处 `assert ... or True`
   （`test_cli_migrate_improvements.py:120`、`test_planner_feedback_id_uniqueness.py:223`、
   `test_roadmap_state_objectives_index.py:69`、`test_skill_layer_project_root_resolution.py:78`）。
   改动面在 `tests/unit`，与本项无关 ⇒ 另案（约 9 行）。
2. **已知残留清单**（本项刻意不修，扫描面被冻结在 `skills/rdd-builder/scripts`）：
   `skills/rdd-planner/scripts/planner_stage_{entry,exit}.sh:13/:21`、
   `skills/roadmap/scripts/roadmap_migrate.sh:21-25/:61`、
   `_lib/gate.py:168/:178/:197` —— 其中 `_lib/gate.py` 那三处尤其值得单独处理：**它就是质量门本身**，
   判错 = 验收结论不可信。
3. **运行期写盘检测**（CI 跑 integration 子集 + 前后 mtime 快照）：本次 marker 扫描实证它会被
   并联 session 的写误判；归属判定未解决前会制造假红。
4. **`generate_full_proposal.py` 的段映射失真**：P0 生成 proposal 时把 `## 范围` 的 Out of Scope
   **重复输出了一遍**（本次手工修正了生成的 proposal.md，未改生成器）。

## 6. 已用轮次

- 验收轮次：**1 / 3**（`RDDF_VERIFIER_MAX_LOOPS=3`）
- 本轮结论：**pass**（无 partial、无 deviation）

## 7. 路由建议

无失败项 ⇒ 无需回 builder / planner。
