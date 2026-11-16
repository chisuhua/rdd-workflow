---
优先级: P1
priority: P1
来源: 2026-11-16 rddf-layout-manifest 归档过程发现（follow-up F-3 + F-4）——P3 的 verifier 预调用既不执行、且退出码语义被误读；叠加
  openspec_tracked=false 分支提前 return 跳过 AC 门
阶段: phase-2
分类: bugfix
类型: bugfix
状态: approved
approved_at: 2026-11-16
approved_by: rdd-planner
review_notes: "metis 1 轮（2026-11-16，5 份合并调用，每份 1 轮在预算内）；4 处 P0 采纳并重写草案，逐条处置见正文「## 审稿记录」；7 段 + 主题校验 PASS；已 attach 到 阶段步骤化执行/phase-2"

生成时间: 2026-11-16
roadmap_ref:
  project_id: 阶段步骤化执行
  phase: phase-2
---

# fix-p3-verifier-gate

**主题**: 阶段步骤化执行

## 审稿记录

metis 1 轮（2026-11-16，planner 阶段 gap 分析）。逐条处置：

- **采纳 P0-2（删除重复实现）**：原草案准备新写「读 cache + 判 sha + 分类 problems」，而
  `_lib/archive.sh:360-556 archive_gate_check` 已实现全部判据（sha 绑定 / cache 完整性 /
  `STRICT_AC_GATE` / bypass 审计 / 三条出路文案）⇒ 改为「P3 调既有门，不新写逻辑」。
- **采纳（新增更深缺陷）**：`archive_gate_check` 唯一调用点在 `:629`，而
  `openspec_tracked=false` 分支 `:612-620` 提前 `return 0` ⇒ 本仓归档路径无 AC 门。已写入
  「架构依据」并在 What Changes 第 2 条单独修。
- **采纳（隐藏意图：删输入却不给替代）**：`route_verifier_verdict` 的唯一输入被删后，ADR-0034 的
  「失败回 P2 + 三次上限」会失去执行点 ⇒ What Changes 第 4 条要求把 failed-AC 路由写死。
- **采纳（fail-closed 语义歧义）**：AC 明确 `STRICT_AC_GATE` 两态各自的期望，避免「验收通过」
  在未开 strict 时仍可带 failed AC 归档。
- **采纳（AC-1 不可满足）**：「全局无 `verifier_run` 残留」在 `.rddf/plans/**`、`.rddf/reviews/**`
  等历史工件上必然为假 ⇒ 收窄到 `skills/` + `_lib/`。
- **采纳（缺 bats 落点）**：`test_rdd_builder_phase3_archive.bats` 在树中不存在 ⇒ AC 写明「新建」
  与 fixture 形态（不再写「其 bats」）。
- **采纳 P1-1（bypass 缺口）**：补 `SKIP_RDD_VERIFIER` 无理由 fail-closed / 有理由写
  `.bypass-audit.jsonl` 两条 AC；错误文案复用 `:551-555`，不另写。
- **采纳 P2-1（行号纠偏）**：`:24` → `:26-32`。
- **记录未改**：不改 `archive_gate_check` 自身判据（Out Scope），否则门有两个真源。

## 架构依据

`_lib/archive.sh::archive_gate_check`（`:360-556`）**已经实现**了完整的归档前验收门：

- sha 绑定（`:470` / `:531`）
- cache 不完整 ⇒ 拒绝（`:501`）
- `STRICT_AC_GATE=yes` 时 failed AC ⇒ 拒绝，否则只 WARNING（`:514` / `:528`）
- `SKIP_RDD_VERIFIER=yes` 需配 `RDDF_VERIFIER_BYPASS_REASON`，否则 fail closed，并写
  `.rddf/state/.bypass-audit.jsonl`（`:539-547`）
- 无 cache ⇒ 拒绝 + 三条出路文案（`:551-555`）

但这个门在两个地方失效：

1. **P3 不调用它**。`skills/rdd-builder/scripts/phase3_archive.sh:26-32` 改为预调用一个**不存在**的脚本
   ——`[ -f skills/rdd-verifier/scripts/verifier_run.sh ]`，而该目录实为 `classify_failure.sh` /
   `route_loop.sh` / `run_verification.sh` / `scan_queue.sh`。⇒ 整块恒跳过，`VERIFIER_EXIT` 保持初值 0
   （`:25`），`route_verifier_verdict(verifier_exit_code=$VERIFIER_EXIT)` 把 0 当作「验收通过」。
2. **门在 `openspec_tracked=false` 分支不可达**。`archive_gate_check` 全仓唯二调用点是
   `_lib/archive.sh:629`；而同一函数里 `openspec_tracked=false` 分支在 `:612-620` **提前 `return 0`**，
   早于 `:629`。本仓 `.rddf/project.yaml` 即 `git.openspec_tracked: false` ⇒ **本仓的归档路径上根本
   没有 AC 门**。

即使把文件名改对也不成立：`run_verification.sh` 头注明写
`Exit: 0 = context staged (agent verification pending)` —— 它是 **staging** 脚本，exit 0 只表示
「已生成待验证上下文」。ADR-0045 已确立「executing AI agent IS the LLM」⇒ bash 层不可能自行产出 verdict。

## 范围

- **In Scope**：P3 改为调用既有 `archive_gate_check`（不新写校验）；修 `archive_change` 的 `openspec_tracked=false` 分支使其也过门；删除失效的 verifier 预调用与错误的 exit-code 输入；failed-AC 时的路由写明；建 P3 的 bats（当前不存在）。
- **Out Scope**：不改 `archive_gate_check` 自身的判据与文案；不改 `run_verification.sh` 的 staging 语义；不新写「读 cache / 判 sha / 分类 problems」的第二套逻辑（`validate_cache_for_archive` 继续只当 `archive_gate_check` 的子步骤）；不动 lightweight 模式的归档入口（见 `fix-worktree-archive-path` 的已知缺口）。

## Why

本次 `rddf-layout-manifest` 归档时 P3 的 verifier 环节完全空转：脚本认为验收通过，实际没有任何验收
发生过，且**零告警**（exit 0 + 无 stderr）。验收是 agent 显式走 `rdd-verifier` skill 才完成的 —— 若
agent 忘了走，change 会带着未验过的实现直接归档。

更深一层：即使 P3 改对了，本仓这条路仍然没有门，因为 `openspec_tracked=false` 分支提前 return。
两层叠加的净效果是「本仓的归档质量门 = 不存在」，而这一点在任何日志里都看不出来。

## What Changes

1. **P3 调用既有门**：`phase3_archive.sh` 在进入归档动作前显式调用
   `archive_gate_check "$CHANGE_NAME" "${WT_PATH:-.}"`，按返回码决定继续/中止。**不新写校验逻辑** ——
   sha 绑定、cache 完整性、bypass 审计、错误文案全部复用 `:360-556`。
2. **修 `openspec_tracked=false` 分支**：`_lib/archive.sh:612-620` 在 `openspec archive` 之前补
   `archive_gate_check`，使该分支与 tracked 分支的门一致（本仓唯一真实路径）。
3. **删除失效预调用**：移除 `phase3_archive.sh:26-32` 的 `verifier_run.sh` 守卫与 `VERIFIER_EXIT`
   初值放行；`route_verifier_verdict(verifier_exit_code=...)` 的当前接法一并移除（函数本体保留，
   供未来外部 verifier 使用，需在实施时确认无其他调用方）。
4. **写明 failed-AC 路由**：cache 存在但含 `status=fail` 时——默认按 `archive_gate_check` 现状
   只 WARNING；若 P3 决定阻断，则回 P2 并走 `increment_retry`（保持 ADR-0034 的三次上限）。
   二者选一必须写死并在 AC 中体现，不得留空。
5. **建 P3 bats**：`tests/integration/test_rdd_builder_phase3_archive.bats`（当前树中不存在，设计文档
   `docs/superpowers/specs/2026-09-04-*.md:729` 曾提及但未落地）。fixture 需构造 proposal + verdict cache
   + `codebase_commit` 与 HEAD 一致。

## Acceptance

- [ ] `phase3_archive.sh` 在归档前调用 `archive_gate_check`，且不存在「`VERIFIER_EXIT` 初值 0 ⇒ 直接放行」的路径
- [ ] `skills/` 与 `_lib/` 下无 `verifier_run` 引用残留（历史工件 `.rddf/plans/**`、`.rddf/reviews/**` 不在检查范围）
- [ ] `openspec_tracked=false` 路径上 `archive_gate_check` 被执行（fixture 断言：无 cache 时归档被拒绝）
- [ ] cache 缺失 / 不完整时 P3 非零退出，错误文案复用 `:551-555`（含三条出路：走 `rdd-verifier` / `SKIP_RDD_VERIFIER` + REASON / 检查 cache 路径）
- [ ] `SKIP_RDD_VERIFIER=yes` 无 `RDDF_VERIFIER_BYPASS_REASON` 时 P3 仍 fail closed；有理由时写入 `.bypass-audit.jsonl`
- [ ] cache `codebase_commit` 与 HEAD 不符（stale）时 P3 不放行（`:531` 分支在 P3 路径生效）
- [ ] failed-AC 的期望行为按第 4 条写死，并有对应用例（`STRICT_AC_GATE` 两态各一）
- [ ] `tests/integration/test_rdd_builder_phase3_archive.bats` 覆盖 complete / missing / stale-sha 三态并通过
- [ ] `run_verification.sh` 的 staging 语义与既有测试不变（`./test.sh --unit` + `bats tests/integration/test_rdd_verifier_*.bats` 全绿）

## Capabilities

- P3 归档前的验收成为真实生效的门（此前 P3 空转 + 本仓分支无门，双重失效）
- 验收结论来源单一化：只认 `rdd-verify` 写的 verdict cache
- bypass 走既有审计通道（`.bypass-audit.jsonl`），不新增旁路
- P3 有了自己的回归测试（此前只有「存在且可执行」的冒烟）

## Impact

- **影响面**：`skills/rdd-builder/scripts/phase3_archive.sh`（verifier 段）、`_lib/archive.sh`（false 分支补门）、新建 bats。
- **风险**：fail-open → fail-closed 后，任何在途、无 verdict cache 的 change 会**无法归档**。错误文案复用
  `:551-555` 已给出三条出路，但需在 release note 说明首次遇到时的处理顺序。
- **与 `fix-worktree-archive-path` 的耦合**：两项都改 `phase3_archive.sh` 的 gate/archive 段。
  **执行顺序固定为本项先、archive-path 后** —— 否则 gate 会被 `archive_change` 的
  `openspec_tracked=false` 分支绕过（本项第 2 条修的正是那个分支，两处必须一致）。
- **兼容性**：verdict cache schema 不变（v2）；`archive_gate_check` 的判据不变。
