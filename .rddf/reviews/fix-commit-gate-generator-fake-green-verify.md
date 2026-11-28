# 验收报告 — fix-commit-gate-generator-fake-green

- **判据来源**：`openspec/changes/fix-commit-gate-generator-fake-green/proposal.md` 的 `## Acceptance`（9 条 AC1–AC9）
- **实现锚点**：`openspec/fix-commit-gate-generator-fake-green` @ `f7c90aca19c1d78cbb1629090582ddd51226b1be`
- **判定载体**：`.rddf/state/verifier/.ac-verdict-fix-commit-gate-generator-fake-green.json`（verdict cache v2，`verification_state=passed`，`failed_acs=[]`）
- **已用轮次**：verifier 第 1 轮（`RDDF_VERIFIER_MAX_LOOPS=3`）

## 逐条判定

| AC | 判定 | 证据（命令 / 输出摘要） |
|---|---|---|
| AC1 脚本类不推导 ⇒ rc=3 | **pass** 0.95 | `bats tests/integration/test_commit_gate_bootstrap_noop.bats` 7/7（case 1）；变异 ③ 下 `not ok 1` |
| AC2 显式来源沿用 | **pass** 0.90 | case 4（rc=0 / 「未重新推导」/ 声明仍含 `--verify` / 实跑生成 `RAN`）；真仓 `init --force` md5 不变 |
| AC3 工具链零测试件 ⇒ rc=3 | **pass** 0.85 | case 7（`未找到 go 测试件`）；3 个单测；变异 ② 下 3 red。caveat：本机无 go/cargo，零测试 rc 按书面行为 |
| AC4 拒绝不改既有声明 | **pass** 0.95 | case 5（`cmp -s` 字节相等） |
| AC5 spec 侧 MODIFIED 替代 | **pass** 0.90 | delta 重生成后同名场景 `grep -c` = **1**（原 2）；`openspec validate --strict` valid；A/B/C/D 四变体实证 |
| AC6 旧判据改写 + design 举证 | **pass** 0.90 | design **D-7**（逐条：旧 fixture / 旧期望 / 为什么错）；变异 ① 下新断言立即红 |
| AC7 文案同步 | **pass** 0.90 | `test_commit_gate_doctor.py` 7 passed（含 `test_fix_hint_offers_both_paths`）；`SKILL.md` 行；`--help` 列 0/1/2/3 |
| AC8 三条变异 | **pass** 0.90 | ① `test_script_entry_points_are_not_auto_derived` red；② 3 red；③ bats `not ok 1/3/5` ⇒ 全部 revert（工作树干净） |
| AC9 门 | **partial** 0.60 | `--gates` ✅；unit 3826 ✅；integration 195 ✅；**bats 4 已知 + 8 既有红** ⇒ 字面「全绿」未达 |

## AC9 的 caveat（必须随归档一起读）

8 条「新增失败」全部是 verifier 队列发现判据（`test_rdd_verifier_{helpers,skip,hook_provider}.bats`）：

- 它们**只写 `iteration.json` fixture、不建 change 目录**，而 `fix-verifier-discovery-disk-derive`（11-27）已改 disk 派生 ⇒ 恒红；
- **`master` HEAD 上同样失败**（本次实测两处），且 `git diff master..HEAD` 不含任何 verifier 文件 ⇒ **不是本 change 引入**；
- 已按 `add-deferral-registration-guard` 登记：`.rddf/improvements/fix-verifier-discovery-stale-assertions.md`（待审查）。

⇒ 本 change 引入的回归 = **0**；AC9 判 `partial` 而非 `fail`，归档带此 caveat。

## 失败项与路由建议

无 fail 项。两条 `partial`/风险项：

1. AC9 的 8 条既有红 ⇒ 路由 `fix-verifier-discovery-stale-assertions`（已登记，独立 change）。
2. go/cargo 零测试 rc 未实跑（环境缺工具）⇒ 真机确认时若与书面行为不符，需回炉 AC3。

## 遗留清扫

| 检查 | 结果 |
|---|---|
| 本 change 范围内的 TODO / 半截实现 | 无。`_lib/commit_gate_declaration.py` 的两个已无调用方的辅助函数（`_package_has_test_script` / `_makefile_has_test_target`）在改造中**已删除**（保留的副本仅供 `detect_unresolved_entries` 判定脚本类入口） |
| 注释掉的代码 / 临时调试日志 | 无 |
| 被 skip 的测试 | 无新增 skip（pytest 3 skipped 为既有） |
| 未替换的 mock | 无 |
| 未登记的「另案」 | 0 条（两条 deferral 均已登记成 improvement） |

## 环境侧记录（非本 change 缺陷）

- **执行模式中途改判** worktree → lightweight：worktree 内 6 条 `resolve_project_root` 判据恒红（按 ADR-0033，linked worktree 的解析结果是**主仓根**）⇒ `commit-gate` 拒绝一切 worktree 提交。已登记 `fix-worktree-commit-gate-deadlock.md`，理由写进 `builder-handoff.execution_mode_decision`。
- 写类工具曾被租约围栏拒绝（`claim_gen 不匹配（我持有 1 ≠ 当前 38）`：`claims` 与 `holders` 两侧 gen 不同步），经一次 `role-switch.sh builder --by user` 复位（未改角色）。

## 归档后补正（2026-11-29 · AC5 的 caveat 落地）

归档后的主 spec 一度出现**两条同名、THEN 互相矛盾**的场景（旧「写 `./test.sh`」+ 新「拒绝」），
而 `openspec validate` 仍报 valid —— 即 D-1 亲手描述的那个 D 形态。

**根因（本 change 的过程错误，不是产品缺陷）**：delta 的修正在 **worktree 副本**里完成并验证（同名场景 1 条），
而归档读的是**主仓**的 `openspec/changes/<change>/specs/…`（P2 搬进 worktree 是单向的，见
`phase2_execute.sh::_carry_artifacts`）⇒ 主仓副本仍是 P0 生成的 D 形态。

**处置**：已直接修正主 spec（删掉被替代的旧场景，保留 delta 的新语义），`openspec validate --specs` 169 passed；
本报告 AC5 的判定对**工作树**成立、对**归档产物**需以本段为准。
**另案登记**：`.rddf/improvements/fix-worktree-change-artifact-drift.md`（worktree 内改 change artifacts 不回主仓）。
