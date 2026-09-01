# fix-design-done-gate-status-prefix-match Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: skill_use("execute")

**Goal:** 修复 design-done gate 用精确字符串匹配 `已批准`/`已拒绝`/`延迟`,让带后缀的状态(如 `延迟 (2026-08-28, 维持 v3.2 deferred 决策)`、`已批准 (2026-09-01)`)正确通过。

**Architecture:** 把内联 bash `check_design_done_gate` 从 SKILL.md 提取到 `skills/guide-design/scripts/design_done_check.sh`,用 `case` 前缀匹配替代 `==` 精确比较。

**Tech Stack:** bash 4.x case glob, openspec CLI。

---

## File Structure

| File | Change |
|---|---|
| `skills/guide-design/scripts/design_done_check.sh` | 新 helper (提取内联逻辑 + 前缀匹配) |
| `skills/guide-design/SKILL.md` | Phase 4 改 source helper |
| `tests/unit/test_design_done_gate.sh` | 新 bash 单测 (5 个) |
| `tests/integration/test_design_done_gate.bats` | 新 bats (2 个) |
| `docs/change-quality-guide.md` | 加"proposal 状态后缀"说明 |

---

## Tasks

### Task 1: 提取 design_done_check.sh + 前缀匹配

- [ ] **Step 1: 写 failing bash 单测** `tests/unit/test_design_done_gate.sh` 5 个测试覆盖:`已批准 exact pass` / `已批准 with suffix pass` / `延迟 with suffix pass` (本 bug 回归) / `待审查 fails` / `空 status fails`
- [ ] **Step 2: 跑测试确认 fail** → FAIL (helper missing)
- [ ] **Step 3: 创建 helper** `skills/guide-design/scripts/design_done_check.sh` 含 `check_design_done_gate` 函数,`case "$status" in 已批准*|已拒绝*|延迟*) : ;; *) echo "pending: $status" ;; esac`
- [ ] **Step 4: 跑测试确认 pass** → PASS
- [ ] **Step 5: Defer commit**

### Task 2: SKILL.md 接线 helper + 文档

- [ ] **Step 1**: 修改 `skills/guide-design/SKILL.md` Phase 4 把内联 `check_design_done_gate` 替换为 source helper
- [ ] **Step 2**: 跑 `bash tests/unit/test_design_done_gate.sh` 仍 PASS
- [ ] **Step 3**: 跑 `bats tests/integration/test_design_done_gate.bats` 2 pass
- [ ] **Step 4**: docs/change-quality-guide.md 加"proposal 状态后缀"段
- [ ] **Step 5**: Defer commit

### Task 3: tasks.md + commit + archive

- [ ] **Step 1**: `sed -i 's/- \[ \]/- [x]/' openspec/changes/fix-design-done-gate-status-prefix-match/tasks.md`
- [ ] **Step 2**: `git add -A && git commit -m "fix(design): gate accepts status with suffix"`
- [ ] **Step 3**: `archive_change fix-design-done-gate-status-prefix-match`

## Self-Review
- ✅ 不破坏其他 status 词汇
- ✅ Hub gates (check-hub-pending / check-cross-repo-approvals) 保留
