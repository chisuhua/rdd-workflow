---
优先级: P1
priority: P1
来源: 2026-11-16 rddf-layout-manifest 归档过程发现（follow-up F-7）——phase3 在 worktree 里跑 openspec archive，openspec_tracked=false 时记录随 worktree 清理丢失
阶段: phase-2
分类: bugfix
类型: bugfix
状态: pending
生成时间: 2026-11-16
---

# fix-worktree-archive-path

**主题**: 阶段步骤化执行

## 架构依据

归档动作当前有**两份实现**，且 phase3 那份绕过了唯一实现的所有收尾动作。

`_lib/archive.sh::archive_change`（`:582-`）是唯一具备完整收尾的实现：merge 回主仓 → `check_worktree_commits` → `archive_gate_check` → `openspec archive` → `post_archive_cleanup` → `commit_archive_moves` → `cleanup_worktree_and_branch` → `mark_iteration_archived`。它对两种 `openspec_tracked` 配置都有分支：

- `true`：worktree 提交 → merge → gate（`:629`）→ archive → cleanup。
- `false`（`:612-620`，本仓配置）：`switch_to_default_branch` 后在**主仓**归档 → cleanup → `mark_iteration_archived` → `return 0`（该分支跳过 gate，由 `fix-p3-verifier-gate` 修）。

而 `skills/rdd-builder/scripts/phase3_archive.sh:91-99` 自己实现归档：

```bash
if [ "$EXEC_MODE" = "worktree" ]; then
    WT_PATH=".rddf/wt/$CHANGE_NAME"
    cd "$WT_PATH" || exit 3
fi
openspec archive "$CHANGE_NAME" --yes || exit 7
```

在 `openspec_tracked=false` 时 `openspec/` 是**不入库的独立目录**（本仓 `.gitignore` 整树忽略 `openspec/`），
worktree 里的 `openspec/` 是创建时的**普通拷贝**（实测：`readlink -f` 两侧同值但 `[ -L ]` 为假）。
⇒ 归档结果只写进 worktree 里那份拷贝，随后 cleanup 删掉 worktree ⇒ **归档记录与 spec 合流全部丢失**。

本次 `rddf-layout-manifest` 是在**主仓**手工跑 `openspec archive` 才保住
`openspec/changes/archive/2026-11-16-rddf-layout-manifest` 与
`openspec/specs/rddf-layout-manifest/spec.md`（+25 Requirements）。按 phase3 原样执行会两者皆无。

`archive_change` 还要求 worktree 存在（`:589-592`：`wt_path` 为空即 `return 1`），因此**轻量模式无法
使用它** —— 这是本项必须显式处理的边界，不是可以顺手带过的细节。相关旁证：`_lib/archive.sh:688`
与 `:626` 的注释仍指向 `ship_archive.sh::archive_change_for_mode`，而该文件与函数在本仓**已不存在**
（全仓仅历史 improvement 文档残留），即曾经的双模式 funnel 已被删除、phase3 的 inline 实现是补偿。

## 范围

- **In Scope**：worktree 模式的归档动作改调 `archive_change`；删除 phase3 自己的 `openspec archive` 与 `post_archive_cleanup` 调用（避免双跑）；明确 lightweight 模式的现状与出口；建模式矩阵并按其写 AC。
- **Out Scope**：不改 `archive_change` 内部逻辑（gate 见 `fix-p3-verifier-gate`）；不给 `archive_change` 加 lightweight 支持（已知缺口，见「已知缺口」段）；不改 worktree 生命周期；不清理 `_lib/archive.sh` 里指向已删除 `ship_archive.sh` 的注释（记 backlog）。

## 模式矩阵（本项的行为契约）

模式由 `_lib/builder_deps.py::decide_execution_mode(file_count, task_count, risk_keywords)`
决定（`files>2` 或 `tasks>3` 或风险词 ⇒ worktree；否则 lightweight），**与 `openspec_tracked` 无关**。

| 模式 | `openspec_tracked` | 现状 | 本项后 |
|---|---|---|---|
| worktree | `true` | phase3 在 wt 内 archive，从不 merge 回主仓 | 调 `archive_change`：merge → gate → archive → cleanup → iteration |
| worktree | `false`（本仓） | 在 wt 的拷贝里 archive ⇒ 记录丢失 | 调 `archive_change`：`switch_to_default_branch` 后**在主仓** archive ⇒ 记录保住 |
| lightweight | `true` | phase3 在 cwd（主仓）archive；无 merge/commit、无 gate、无 cleanup、无 iteration sync | **不变**（已知缺口，见下） |
| lightweight | `false` | 同上（位置正确，收尾全缺） | **不变**（已知缺口） |

## 已知缺口（本项不修，但必须写明）

`archive_change` 要求 worktree 存在，lightweight 模式因此**无法**委托给它；lightweight 的
gate / cleanup / iteration sync 三项收尾都没有执行点。本项保留 phase3 的 lightweight inline 分支，
并在代码注释里写明这是「架构上尚未统一」的缺口，另立改善项（不在本提案范围）。

## Why

同一个动作存在两份实现，且副本只在「仓库恰好把 `openspec/` 排除出版本控制」时才出问题 ——
tracked 仓库里一切正常，只有 `openspec_tracked=false` 的项目会静默丢记录。

这类缺陷最难发现：归档命令 exit 0、日志正常、change 确实「消失」了（因为 worktree 被删），
只有去 `openspec/changes/archive/` 找产物时才会发现空白。spec 合流丢了则意味着
`openspec/specs/` 与实现永久脱节，而后续 change 会基于过时 spec 做 delta。

## What Changes

1. **worktree 模式改调 `archive_change`**：删除 `phase3_archive.sh:91-99` 的 inline
   `cd "$WT_PATH"` + `openspec archive`，改为 `source _lib/archive.sh` 后调用
   `archive_change "$CHANGE_NAME"`，并把返回码映射到 phase3 既有语义（见第 3 条）。
2. **删除 phase3 自己的 cleanup 调用**（`:101`）：`archive_change` 内部已在 `:725` 调用
   `post_archive_cleanup`，保留会产生双跑（对已干净的树是 no-op，但会重复取 `git status` 快照并再次
   `git add`，可能把 `archive_change` 之后的改动一并 stage）。
3. **返回码映射（先写表，不留「实施时映射」）**：

   | `archive_change` 返回 | 原因 | phase3 应返回 |
   |---|---|---|
   | 0 | 成功 | 0（写入 `archive_status=archived`） |
   | 1 | 找不到 worktree / 找不到主仓 / merge 或 `check_worktree_commits` 失败 | 3（既有「worktree/前置不满足」语义） |
   | 3 | `archive_gate_check` 拒绝（`_lib/archive.sh:629`） | 7（既有「归档失败」语义）+ 原样透传 gate 的错误文案 |

4. **lightweight 分支加注释说明缺口**，并确保它仍能归档（行为不变）。
5. **建 bats**：worktree × `openspec_tracked=false` 的归档断言产物在**主仓**；worktree × `true`
   的归档断言 merge + cleanup 生效。

## Acceptance

- [ ] `phase3_archive.sh` 的 worktree 分支不再直接执行 `cd .rddf/wt/*` + `openspec archive`（grep / bats 断言）
- [ ] `phase3_archive.sh` 不再调用 `post_archive_cleanup`（避免与 `archive_change:725` 双跑）
- [ ] worktree × `openspec_tracked=false`：归档后主仓 `openspec/changes/archive/<date>-<name>/` 存在
- [ ] 同场景下 `openspec/specs/<name>/spec.md` 已按 delta 合流
- [ ] 同场景下 worktree 目录与 `openspec/<name>` 分支均已清理
- [ ] worktree × `openspec_tracked=true`：merge 回主仓生效，worktree/分支清理生效（既有 archive bats 全绿）
- [ ] 返回码映射按第 3 条表格实现，且 gate 拒绝（`archive_change` 返回 3）时 phase3 返回 7 并透传 gate 文案
- [ ] lightweight 模式行为不变，且代码注释写明 gate/cleanup/iteration sync 未覆盖
- [ ] `iteration.json` 的 `archive_path` / `archive_commit_sha` 写入仍由 `archive_change` 侧完成（不因迁走而丢字段）
- [ ] `./test.sh --unit` + `bats tests/integration/test_rdd_builder_phases.bats` +
      `bats tests/integration/test_archive*.bats` 全绿

## Capabilities

- 归档只有一份实现（`archive_change`），配置相关分支不再被绕过
- `openspec_tracked=false` 的项目（含本仓）归档记录与 spec 合流不再丢失
- cleanup / iteration sync / commit 等收尾动作在 worktree 模式下不再是漏项
- 双模式与配置的四格行为矩阵成文，替代散落在两个文件里的隐式假设

## Impact

- **影响面**：`skills/rdd-builder/scripts/phase3_archive.sh`（archive 段 + cleanup 调用）+ 新建/扩展 bats；
  `_lib/archive.sh` 只被调用、不改。
- **风险**：phase3 的 exit code 语义（3 = worktree/前置不满足、7 = 归档失败）被
  `route_verifier_verdict` / `increment_retry` 依赖，映射表（第 3 条）必须先落地再改代码。
- **与 `fix-p3-verifier-gate` 的耦合**：两项都改 phase3 的 gate/archive 段。**执行顺序固定为
  verifier-gate 先、本项后** —— 否则 `archive_change` 的 `openspec_tracked=false` 分支会绕过
  gate，把前一项目修复的门又关掉。
- **兼容性**：tracked 路径行为不变（仍 merge + cleanup）；`false` 路径从「丢记录」变为「正确归档」。
