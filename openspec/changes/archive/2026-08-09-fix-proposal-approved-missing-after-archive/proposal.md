# fix-proposal-approved-missing-after-archive

## Why

执行 `archive-cleanup-plan-files-extension` 完整 lifecycle (approve → plan → ship → archive) 后, dashboard 仍报该提案为 📋 待讨论。Root cause 是 **proposal-approved.md 的 plan-phase commit 漏档**:

1. **Design 阶段**: `approve_proposal.sh` patch `proposal-approved.md` (主表格) 写入新行 ✅
2. **Plan 阶段**: 我 (AI 编排者) `git add openspec/changes/<name>/` + `improvements/<name>.md` 但**忘了 `proposal-approved.md`** ❌
3. **Archive 阶段**: `mark_approved_completed` 查找主表格无对应条目 → 跳过 → `## 已实施` section 未更新 ❌
4. **Dashboard 读取**: `proposal-approved.md` 用 regex `r"\|\s*\[([^\]]+)\]\(improvements/"` 提取所有 approved 集合; `improvements/<name>.md` 文件存在 → filter 不命中 → 报 pending

完整复盘路径 (6 commits, 31 task, archive 全绿):

```
26e30e9 feat(plan): add archive-cleanup-plan-files-extension change
   ⚠️  只 add: openspec/changes/<name>/ + openspec/specs/ + improvements/<name>.md
   ❌  漏 add: proposal-approved.md (含 design 阶段 approve_proposal.sh 写入的行)
a4f8e38 fix(plan): restructure spec body for openspec validate + delta-target
1ad864e feat(ship): add implementation plan for archive-cleanup-plan-files-extension
fcf3cfa feat(post-archive-cleanup): extend scope to openspec/changes/<name>/
fc05d9b fix(spec): change main spec heading from MODIFIED to Requirements
c5b3c5a fix(spec): canonical post-archive-cleanup-hook spec uses ## Requirements
29bb72c merge: archive-cleanup-plan-files-extension change
a6da054 chore(post-archive): clean residue from archive-cleanup-plan-files-extension
b8073a8 archive(archive-cleanup-plan-files-extension): archive completed
3dc1b03 fix(proposal-approved): manually add archive-cleanup-plan-files-extension to 已实施
```

最终 dashboard 修复需要**手工补一行**到 `## 已实施` section — 这是修复症状, 没根除 bug。

## What Changes

**In Scope**:

- `approve_proposal.sh` (design 阶段) 改进: 写 `proposal-approved.md` 后立即 `git add proposal-approved.md` + echo "已 git add" 提示
- `guide-plan.md` Phase 2 fill 完成时: 检测 `proposal-approved.md` 是否脏, 若脏则强制 commit
- `mark_approved_completed` (archive 阶段) 改进: 找不到主表格行时 fallback 检测 `improvements/<name>.md` 是否存在 + `openspec/changes/archive/*-<name>/` 是否存在 → 若全命中则强制 append 到 `## 已实施`
- dashboard `_lib/dashboard/__init__.py` 改进: pending 判定加 fallback — 即使 `proposal-approved.md` 没该名,若 `openspec/changes/archive/*-<name>/` 存在则跳过
- 加 1 个 regression test (bats): "approve_proposal immediately stages proposal-approved.md"
- 加 1 个 unit test: "dashboard filters archived changes from pending"
- **Out of Scope**:
- 不修改 `proposal-suggestions.md` 同步逻辑 (那是 plan 阶段另一回事)
- 不修 `iteration.json` 同步 (那是 deps 阶段任务)
- 不动 `archive-cleanup-plan-files-extension` 已提交的 9 commits (history 已存在, 不做回填)

### 关键场景

- **GIVEN** AI 编排者运行 `approve_proposal.sh <name>`, **WHEN** patch 写入 `proposal-approved.md`, **THEN** 立即 `git add proposal-approved.md` 并退出提示
- **GIVEN** Plan 阶段完成 fill, **WHEN** `proposal-approved.md` 脏, **THEN** plan-done gate 提示 "请先 commit proposal-approved.md", 否则不写 plan-handoff
- **GIVEN** archive 阶段 `mark_approved_completed <name>`, **WHEN** 主表格找不到该名, **THEN** fallback 检测 archive/<date>-<name>/ 存在 → 强制 append 到 `## 已实施` 末尾
- **GIVEN** dashboard 读取 pending, **WHEN** 某名不在 `proposal-approved.md` 但 `openspec/changes/archive/*-<name>/` 存在, **THEN** 跳过 (按 archived 处理)

**Out of Scope**:

- (TBD)

## Capabilities

- `git add proposal-approved.md` 必须在 approve_proposal.sh 退出**前**调用 (fail-fast on git error)
- fallback 检测必须用 `compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-<name>"` 模式 (与 post-archive-cleanup 一致)
- dashboard filter 优先级: 已实施 section > 主表格 > archive/ 派生 > 报 pending
- `proposal-approved.md` 格式按 docs/proposal-approved-format.md (Markdown 表格)

## Impact

- `git add proposal-approved.md` 必须在 approve_proposal.sh 退出**前**调用 (fail-fast on git error)
- fallback 检测必须用 `compgen -G "openspec/changes/archive/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-<name>"` 模式 (与 post-archive-cleanup 一致)
- dashboard filter 优先级: 已实施 section > 主表格 > archive/ 派生 > 报 pending
- `proposal-approved.md` 格式按 docs/proposal-approved-format.md (Markdown 表格)

## Acceptance

- [ ] approve_proposal.sh 退出时 `git status --porcelain proposal-approved.md` 包含 `M proposal-approved.md`
- [ ] plan 阶段 plan-done gate 加 proposal-approved.md 脏检查 (warning 级别)
- [ ] mark_approved_completed 加 archive/ fallback 检测
- [ ] dashboard pending 逻辑: archived 变化永不被报为 pending
- [ ] 1 个新增 bats regression test: `tests/integration/test_approve_proposal_staging.bats`
- [ ] 1 个新增 unit test: `tests/unit/test_dashboard_pending_filter.py`
- [ ] 跑 `./test.sh --full --regression` 0 新增失败

