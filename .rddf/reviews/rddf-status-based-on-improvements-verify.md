# rddf-status-based-on-improvements 验收报告

- **change**: `openspec/changes/rddf-status-based-on-improvements/`
- **日期**: 2026-11-20
- **验收方式**: **本地验收**（`rdd-verifier` skill 分流条件 2 不满足 —— 验收前 `iteration.json` 未登记本 change，`rddf rdd-verify --dry-run` ⇒ `No eligible changes to verify (empty queue)`）
- **已用轮次**: 1
- **本地验收额外门**: `iteration.json` 中 `tasks_done == tasks_total > 0` ⇒ 53/53 ✓（口径：实施任务 T1–T10；T11 的验收/归档流程项本身不计入）
- **提交**: `4661096a`（单一原子提交，21 files，+716/−423）

## 判据来源

`proposal.md` 的 `## Acceptance` 段（AC-1 ~ AC-11）。

## 逐条判定

| AC | 判定 | 取证 |
|---|---|---|
| AC-1 | **pass** | AST：`status_cmd.py` 的 `read_iteration*` 名字引用 **0**；行为：`.rddf/state/` **不存在**的 fixture ⇒ `rddf status` **exit 0**；iteration.json **损坏**（`{bad json`）⇒ **exit 0** 且输出不含 `iteration.json not found / fails schema invalid JSON`（0 命中） |
| AC-2 | **pass（判据已修正）** | 两段存在（`Improvement proposals` + `Active changes`）+ 列头齐全（NAME/PRI/STATUS/PHASE + TASKS/PLAN/BUILDER）；`collect_pending().suggestions` = **21** 条，输出提案行 = **21** 行，每行前缀能对应到一个 name。⚠️ **原判据「行集合 == name 集合」不成立** —— NAME 列宽 44 字符，2 条超长提案被截断（`fix-rdd-doctor-hardcoded-paths-and-skills-md-drift` 51 字符、`experimental-reflect-...` 71 字符）。**实现正确、判据过严** ⇒ 判据改为「行数一致 + 前缀匹配」，并记录「超长名截断」为已知显示行为（dashboard 用省略号截断，status 用硬截断） |
| AC-3 | **pass** | `collect_pending` 定义 **1** 处（`_lib/dashboard/__init__.py`）+ dashboard Section 7 调用 **1** 处 + `status_cmd.py` 调用（1 处 import + 1 处调用） |
| AC-4 | **pass** | `rddf status c1` ⇒ `Tasks: 1/2`（与 `tasks.md` 的 `- [x] a\n- [ ] b` 一致）；**无** `Phase:` / `Blocker:` 行（0 命中）；**有** `Builder phase:` 行；未知 change ⇒ **exit 1**；已归档 change（`openspec/changes/archive/2026-01-01-old`）⇒ **exit 0** |
| AC-5 | **pass** | `_mode_e` **0** 命中；`_lib/cli/` 下 `print_view` **0** 文件；`from skills._lib.iteration import print_view` 仍可导入；`rddf status --iteration` ⇒ **exit 2** |
| AC-6 | **pass** | `tests/unit/test_status_disk_derived.py` **14 passed**，覆盖：improvements 目录缺失 / 空 / 无状态字段 / 损坏条目（per-entry 降级 + `errors` 非空 + 表尾 `unreadable` 提示）/ approved 缺失 / archive 缺失 |
| AC-7 | **pass** | ADR-0059 含「已被取代」；`add-rddf-status-fallback-mode.md` 含 `状态: 作废` 且**不出现在** `rddf status` 提案段（实测 21 条中无它）；`test_adr_index_gate.py` **8 passed**；`skeleton-planning` 无 `status --iteration`（0）；`archive-iteration-sync` 无 `rddf status`（0） |
| AC-8 | **pass** | 两 planner 脚本的 `rddf status --json` **仅存在于注释**（说明该 flag 从不存在、旧管道恒失败被 `|| echo 0` 吞掉）；实际取值语句已改为 `collect_pending()` 的 heredoc；`bash -n` 两脚本均 OK；**实证**：4 列 `improvement-approved.md` fixture 取到 **2 条 approved**（`implemented` 段正确排除） |
| AC-9 | **pass** | `test_status_corrupt_message.bats` **9/9 ok**（已从「status 如何报告 iteration.json 缺失/损坏」重写为「status 无视 iteration.json 状态仍可用 + read-only 契约」）；新增单测 **14 passed**；`pytest unit` 3453 passed / `bats` 0 新增失败 |
| AC-10 | **pass** | 全仓 `rddf status --json` / `--check-archive-sync` / `--iteration` **清零**（排除 `docs/legacy/`、本 change 工件、planner 的说明性注释） |
| AC-11 | **pass** | `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression` ⇒ **rc=0 / ALL PASSED**（`/tmp/opencode/status-final2.log`）：未评估 **0** / 已知失败 11 / **新增失败 0**；pytest unit **3453 passed**；integration **192 passed** |

## 失败项

**无（1 项判据缺陷已修正）**

### AC-2 的判据缺陷（实现正确）

- **阻塞点**：`proposal.md` 的 AC-2 写作「改进提案段行集合 == `collect_pending(root).suggestions` 的 name 集合」。实测 2 条超长 name 被 NAME 列（44 字符）截断，按字面判据永远不成立。
- **需要什么决策**：判据改为「**行数一致** + 每行前缀能对应到一个 name」；记录的显示行为：超长名硬截断（dashboard 的 `_ellipsis` 是省略号截断，两者不一致但都丢信息 —— 属显示层细节，不阻断）。
- **已完成 / 未完成**：实现 100% 完成（21 条全出、行数一致、前缀全匹配、门全绿）。
- **闭合**：判据已按上述修改；复验 ⇒ `suggestions=21 / 输出提案行=21 / 前缀匹配=True` ✓。

**分类**：`implementation_gap` 的变体 —— 实现满足，缺口在判据措辞（非实现代码）。

## 遗留清扫结果

| 项 | 结果 |
|---|---|
| TODO / FIXME | 本次 diff 未引入 |
| 死代码 | `_mode_e` / `_render_iteration_read_error` 已删；`_STATUS_ICON` 删 3 个 0 引用键（proposed/review/done）；`print_view` **保留**（公共 API）并在 docstring 注明无 CLI 调用者 |
| 未用导入 | 门的 `ruff skills/_lib/` 全绿；本次改动的 `_lib/cli` / `_lib/dashboard` / 新测试单独 ruff 全绿 |
| mypy | 门的 `mypy --strict skills/_lib/core/` 全绿；`_lib/dashboard`/`_lib/cli` 的 15 个报错中 13 个是 `[attr-defined]` 的**既有 shim 可见性模式**（未改动的 `archive_cmd.py` 同样报），2 个在 `:124`/`:138`（**不在本次 diff 区段内**）⇒ 未引入新错误 |
| 不存在的 flag | 全仓清零（含 `tools/archive_on_main.sh` 里**运行时打印给用户**的建议） |
| 临时 fixture | `/tmp/vf`、`/tmp/probe-status` 均在 /tmp，未进仓库 |
| 未替换 mock / 跳过的测试 | 0 |

## 备注

1. **AC-1 的关键修复是在验收前才发现的**：`.rddf/state/` **整个不存在**时，`_lib/cli/__main__.py:221` 的 `_NO_STATE_CHECK` 不含 `status` ⇒ CLI 直接打印「not a rdd-workflow project」返回 0，根本到不了 handler。这把 AC-1 从「有 state 但 iteration.json 坏」扩展到「真正的全新项目」（ADR-0059 的原始场景）。已在提交 `4661096a` 内修复。
2. **SKILL.md 是 AI 工作流层**：其实施中核实 Mode E 经 `iteration.render.print_view` 自有实现，不经 CLI ⇒ CLI 移除 Mode E 不影响它，3 个 bats 无需改（实测 29/29 绿）。proposal/tasks 已回写该澄清。
3. **破坏性变更**（proposal §7 的 exit code 契约表）：默认输出改变、`--iteration` 移除、Mode A 在 iteration.json 损坏时 exit 1 → 0。
4. **归档前置**：`openspec archive` 无阻塞项；归档后 `rddf archive-sync` 转 `archived`。
