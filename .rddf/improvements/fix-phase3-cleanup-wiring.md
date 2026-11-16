---
优先级: P1
priority: P1
来源: 2026-11-16 rddf-layout-manifest 归档过程发现（follow-up F-9 + F-8）——post_archive_cleanup.sh
  没有脚本入口却被 bash 执行（函数从未运行），且 source 失败被 2>/dev/null || true 静默吞掉
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

# fix-phase3-cleanup-wiring

**主题**: 阶段步骤化执行

## 审稿记录

metis 1 轮（2026-11-16，planner 阶段 gap 分析）。逐条处置：

- **采纳 P0-1（根因纠偏，最重要）**：原草案把根因写成「参数顺序反了」——错。实测
  `bash _lib/post_archive_cleanup.sh "$(pwd)" rddf-layout-manifest` → 零输出 exit 0；该文件
  155 行只有函数定义、无脚本入口 ⇒ **函数从未被调用**，参数顺序在「函数不执行」时不成症状。
  「架构依据」与「Why」已整体重写；参数顺序降为次要事实。
- **采纳（删除 scope creep）**：原草案提议给该库加 `--project-root` / `--change` 键名参数 +
  位置参数兼容分支。该库只有两个调用点（`archive.sh:725` 正确、`phase3:101` 错误）⇒ 收益为 0，
  已删除该备选。
- **采纳 P2-2（严重级一致）**：cleanup 失败**不改变**归档退出码（与 `archive.sh:725` 的 `|| true`
  一致），只要求 stderr 可见 ⇒ 写入 AC。
- **采纳（测试写成镜像）**：原 AC「断言第一个参数是含 `/` 的路径」是对实现的镜像 ⇒ 换成行为断言
  （`improvement-approved.md` 真被同步、`proposal-section` 无 CRITICAL）。
- **采纳（fixture 假绿风险）**：本仓 `openspec/` 整树 gitignored ⇒ e2e fixture 必须造「archive
  目录存在但不被 git 跟踪」的形态，已写入 What Changes 第 3 条与 AC。
- **采纳（双跑）**：与 `fix-worktree-archive-path` 的重叠（phase3 的 cleanup 调用）明确交后者删除；
  本项 Out Scope 声明不修该调用点。

## 架构依据

`_lib/post_archive_cleanup.sh` 共 155 行，**只定义 `post_archive_cleanup(project_root, change_name)`
（签名在 `:62-64`），文件末行即函数闭合 `}`，没有任何脚本入口 / dispatcher**。因此：

- 正确用法只有 `source` 后调用 —— `_lib/archive.sh:74` source 它，`:725` 以
  `post_archive_cleanup "$main_root" "$name"` 正确顺序调用（唯一正确路径）。
- `skills/rdd-builder/scripts/phase3_archive.sh:101` 用
  `bash _lib/post_archive_cleanup.sh "$CHANGE_NAME" "$PROJECT_ROOT" 2>/dev/null || echo "(cleanup script deferred)"`
  **把库当脚本执行** ⇒ **函数从未被调用**，cleanup 完全空转；`2>/dev/null` + 兜底 echo 把
  「什么都没做」伪装成 exit 0。

实测：`bash _lib/post_archive_cleanup.sh "$(pwd)" rddf-layout-manifest` → **零输出、exit 0**。

该行同时把两个参数顺序也传反了（脚本签名 `(project_root, change_name)`，调用传
`(change_name, project_root)`），但在「函数从未执行」的前提下**不构成症状** —— 只修参数顺序会得到
「参数位置对了、依然什么都不做」的假修复。

第二层掩盖在 `_lib/post_archive_cleanup.sh:76-79`：
`if [ -f "$project_root/_lib/state.sh" ]; then source "$project_root/_lib/state.sh" 2>/dev/null || true; fi`
—— source 失败（路径错 / 语法错 / 依赖缺）被完全吞掉，`sweep_implemented_proposals` 静默不跑。

净效果（本次实测）：归档后 `improvement-approved.md` 里该提案仍留在「已批准提案」段，doctor 报
`proposal-section` CRITICAL：

```
❌ [proposal-section] improvement-approved.md
   'rddf-layout-manifest' is in '## 已批准提案' but openspec/changes/archive/<date>-rddf-layout-manifest/ exists
Summary: 1 CRITICAL · 0 WARNING · 0 INFO
```

## 范围

- **In Scope**：`post_archive_cleanup.sh` 的**库侧**可用性与故障可见性 —— ① 被当脚本执行时 fail loud（而非静默空转）；② `source ... || true` 静默改为 WARN；③ e2e 断言正确的调用路径能同步 `improvement-approved.md`。
- **Out Scope**：不改 `phase3_archive.sh` 侧的调用点（该调用由 `fix-worktree-archive-path` 删除，本项不修它的参数顺序）；不重写 cleanup 的 deleted/whitelist 清理清单；不改 `sweep_implemented_proposals` 的匹配规则；不新增键名参数解析（只有两个调用点，收益为 0）。

## Why

同一类失败在两处重复出现：**「没做事」被伪装成「做完了」**。首先是库被当脚本跑（零输出 exit 0），
其次是 source 失败被 `2>/dev/null || true` 吞掉。两者叠加后，cleanup 的每一次静默失败在日志里都长得像成功。

这类缺陷的发现成本极高：症状出现在几步之后（doctor 的 `proposal-section` CRITICAL），与病因
（`_lib/post_archive_cleanup.sh` 没有入口 + `phase3:101` 的 bash 调用）相隔很远。本次若不是归档后顺手
跑了 doctor 全量，会一直漏到下一次审计。

## What Changes

1. **库被直接执行时 fail loud**：`_lib/post_archive_cleanup.sh` 末尾加最小守卫 ——
   当 `BASH_SOURCE[0] == $0`（被当脚本执行）时，向 stderr 输出「这是库，请 source 后调用
   `post_archive_cleanup <project_root> <change_name>`」并 `exit 2`。**不加功能、不猜参数**，
   只把「静默空转」变成「明确报错」。
2. **source 失败可见**：`:76-79` 改为 —— `_lib/state.sh` 不存在 ⇒ stderr WARN「跳过 proposal 同步：
   state.sh 缺失」；存在但 source 返回非零 ⇒ stderr WARN 并带失败原因（去掉 `2>/dev/null`）。
   不清洗退出码（与 `archive.sh:725` 的 `|| true` 语义一致：cleanup 不阻断归档）。
3. **e2e 断言正确路径真的生效**：fixture（一个已批准 improvement + 对应 archive 目录）下调用
   `post_archive_cleanup <root> <change>`，断言 `improvement-approved.md` 该条目进入「已实施」段。
   注意 fixture 必须造出「`openspec/changes/archive/<date>-<name>/` 存在但不被 git 跟踪」的形态
   （本仓 `openspec/` 整树 gitignored），否则 e2e 会假绿。

## Acceptance

- [ ] `bash _lib/post_archive_cleanup.sh ...` 直接执行时**非零退出**并说明「库，需 source」（不再静默 exit 0）
- [ ] `_lib/state.sh` 缺失 / source 失败时向 stderr 输出 WARN（`2>/dev/null || true` 不再吞错）
- [ ] cleanup 失败**不改变**归档结果（与 `archive.sh:725` 一致：exit 0 + stderr 可见）
- [ ] e2e：按正确方式调用后 `improvement-approved.md` 中该提案移入「已实施」，`rddf doctor --category proposal-section` 无 CRITICAL
- [ ] 幂等：对已同步状态重复调用不产生重复行（以 `improvement-approved.md` 中该名出现的行数为断言）
- [ ] `git.openspec_tracked=false` 形态下 e2e 仍为真绿（fixture 使用未被跟踪的 archive 目录）
- [ ] `./test.sh --unit` + `bats tests/integration/test_post_archive_cleanup*.bats`（若无则新建）全绿

## Capabilities

- 「库被当脚本执行」这一整类误用在首次发生时就报错，而不是静默跳过
- cleanup 的失败可自解释（WARN），不再表现为「exit 0 + 无输出」
- 归档后 `improvement-approved.md` 的同步有 e2e 保护，不再依赖手工 `sweep_implemented_proposals`

## Impact

- **影响面**：`_lib/post_archive_cleanup.sh`（守卫 + source 告警）+ e2e/bats。
- **风险**：加 fail-loud 守卫后，`phase3_archive.sh:101` 的调用会立刻变成「exit 2 + stderr 提示」，
  由该行的 `|| echo "(cleanup script deferred)"` 转成一行可见提示 —— 比现状（静默）更可观测，但
  在 `fix-worktree-archive-path` 落地前，归档后仍不会自动同步。这是**有意的中间态**，不要用「让报错
  也别响」的方式掩盖。
- **顺序**：与 `fix-worktree-archive-path` 无硬顺序；但两项都落地后，`phase3` 不再有该调用，
  只剩 `archive_change:725` 这一条正确路径。
- **兼容性**：不改任何函数签名；`_lib/archive.sh` 的调用不受影响。
