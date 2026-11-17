# 验收报告 —— `fix-execution-mode-decision`（ADR-0036 修订的落地）

> 验收者：verifier 角色（opencode build agent 的角色矩阵）
> 判据来源：① 用户「继续推进直到完成剩余任务」；② `.rddf/improvements/fix-execution-mode-decision.md` 的 `## Acceptance`（14 条，含 AC #1/#4/#10 的 plan_drift 修订）；③ `docs/adr/ADR-0036-rddf-project-yaml-config.md` 的 `## Verification`（V-A~V-I）
> 已用轮次：2（第 2 轮只验 F-1 闭合）
> 结论：**14/14 pass**（F-1 已在第 2 轮闭合）

## 一、验证顺序

与 B 项同批跑过（同一 `./test.sh --full --regression`）：
静态 ✅ / 单测 ✅ 52 passed / 集成 ✅ 82 ok / **全量门 ✅ ALL PASSED**（pytest unit 3413 passed）/ 遗留清扫见 §四。

## 二、逐条判定 + 证据

| AC | 判定 | 证据 |
|---|---|---|
| ① lightweight 定义 + 波次解耦 | ✅ pass | `skills/rdd-builder/SKILL.md` 的「执行模式契约」表（lightweight = 主仓 `openspec/<change>` 分支 + 无 worktree）+ `docs/architecture/workflow-phases.md` 同表；`_lib/ship_execution_mode.sh` 的 `parse_wave_mode`（:52）与 `parse_execution_mode` 别名（:120）；注释不再写「forces lightweight」 |
| ② `compute_mode_inputs` + 签名不变 | ✅ pass | `builder_deps.py:110`；`test_signature_is_unchanged` 断言参数表 == `[file_count, task_count, risk_keywords]`；`test_absolute_paths_only`（chdir 到 `/` 后仍得同样结果） |
| ③ task_count = checkbox total + fail-closed | ✅ pass | `decide_execution_mode(2, None, [])` ⇒ `worktree` / `tasks=unknown`（实测）；3 个单测（含 `## Task` 反例） |
| ④ 夹具断言（两段验收） | ✅ pass | 单测 + E2E 7/10 按 `LIGHTWEIGHT_EXECUTION_READY` 分叉；现在断言 worktree + 「lightweight 未落地」 |
| ⑤ file_count 来自 plan `**Files:**` | ✅ pass | `builder_deps.py::_plan_files`（剥反引号/行号、去重）；plan 缺失 ⇒ `files=unknown` 且不参与判定（实测 `decide(None,2,[])` ⇒ `files=unknown`） |
| ⑥ risk 结构化声明 | ✅ pass | `RISK_LEVEL_KEYWORDS`（:19）+ 读 `roadmap-meta.yaml` 的 `risk:`；3 个单测；无文本扫描 |
| ⑦ reason 诚实 | ✅ pass | `task_count = 5` 已从 `phase1_5_deps.sh` 消失（grep 0 命中）；`test_reason_never_contains_a_constant_five`；端到端 handoff 实测 `reason: "files=3>2"`（真实值） |
| ⑧ 冲突维度 | ✅ pass | `compute_conflict`（Files 交集 / 活跃 worktree）+ 4 个单测 |
| ⑨ LEGACY_EXEC_MODE 降级 | ✅ pass | `phase1_5_deps.sh:120` 的 WARN + 保留计算判定（不覆盖） |
| ⑩ 三方一致性 | ✅ pass（第 2 轮闭合） | `config_schema.json` 描述已收窄 ✓ / `README.md:87/100` ✓ / 退役清单 R1/R2/R3/R5/R6/R7/R8/R9/R10a 已处置 ✓ / R4 由 ADR-0061 主责 ✓ / R10b 属允许清单 ✓。**F-1 已闭合**：描述改为「which execution mode runs the change (worktree isolation vs. the main repository)」⇒ V-A 的字面判据（不含 `lightweight` 子串）与意图（不承诺 lightweight 模式）**都满足**（实测 `'lightweight' in d == False`、`'NOT influence' in d == True`），`pytest -k "config or schema"` 294 passed |
| ⑪ 计数口径共用 | ✅ pass | `builder_deps.py:123` 的 `from _lib.tasks_count import count_tasks`（与 `fix-iteration-tasks-total` 同一标准） |
| ⑫ 同名函数防护 | ✅ pass | `test_no_same_name_function_with_a_different_signature`（对照 `_lib/subagent_strategy.py`） |
| ⑬ 不新增 phase* 脚本 | ✅ pass | `ls skills/rdd-builder/scripts/phase*.sh \| wc -l` ⇒ 6（未变） |
| ⑭ 全量门 | ✅ pass | ALL PASSED |

## 三、失败项与路由建议（第 1 轮；第 2 轮已全部闭合）

**无 ac-fail 项。1 条 SHOULD_FIX —— 第 2 轮复验：已闭合。**

- **F-1（D-AC10 / ADR-0036 V-A 字面不满足）**：
  `_lib/schemas/config_schema.json` 的 `git.openspec_tracked.description` 含 `lightweight` 子串
  （出现在「does NOT influence the execution mode (worktree vs lightweight)」这一**否定从句**里）。
  V-A 的字面判据是「**不含** 该子串」。
  ⇒ **判定：意图满足（描述不再承诺 lightweight 模式），字面不满足。**
  ⇒ **建议**（二选一，由 build 决策）：① 改写描述，用「the execution mode (which mode runs the
  change)」替掉括号内容；② 修改 V-A 的判据为「不含 `force lightweight` / `lightweight mode` 这类
  **承诺**表述」，并在 ADR 里说明「提到该词不构成承诺」。我倾向 ①（不碰已签批 ADR 的判据）。
  ⇒ **路由：build**（`implementation_gap`，1 行文案）。
  ⇒ **第 2 轮复验**：build 采纳方案 ①（改写描述，未碰已签批 ADR 的判据）⇒ V-A 字面与意图
  **都满足**；`pytest -k "config or schema"` ⇒ 294 passed / 1 skipped。**F-1 闭合。**

## 四、遗留清扫复核

| 项 | 结果 |
|---|---|
| 新增 TODO / FIXME | ✅ 无。`LIGHTWEIGHT_EXECUTION_READY = False` **不是** TODO 标记：它被 `decide_execution_mode` 读取、有 owner（`fix-lightweight-branch-and-archive`）、且 fail-safe（忘了翻正 ⇒ 模式保持禁用） |
| 新增 skip | ✅ 无 |
| 死代码 | ✅ `RISK_LEVEL_KEYWORDS` / `_plan_files` / `compute_conflict` 均被调用；`parse_execution_mode` 是**有意的**废弃别名（CLI 分派里仍接受） |
| 临时日志 | ✅ 无 |
| 测试污染 | ✅ 已清理（见 B 项报告） |
| 边界路径 | ✅ tasks 缺失 / tasks 零 checkbox / plan 缺失 / plan 无 Files 块 / risk 缺省 / risk 未知级别 / 冲突 / 无冲突 / 绝对路径 —— 均有单测 |

## 五、结论

**D 项 14/14 AC pass。** F-1 在第 2 轮闭合。**归档就绪。**
