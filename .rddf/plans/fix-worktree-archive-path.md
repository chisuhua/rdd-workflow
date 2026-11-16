# fix-worktree-archive-path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让归档只有一份实现（`_lib/archive.sh::archive_change`），并让 worktree 模式的归档结果落在**主仓**的权威 `openspec/`（本仓 `openspec/` 整树 gitignored，worktree 里那份是拷贝 ⇒ 归档记录与 spec 合流会随 worktree 清理一起丢失）。

**Architecture:** `phase3_archive.sh` 在 worktree 模式改为委托 `archive_change`（它已具备 gate / merge / openspec archive / cleanup / iteration sync 全套）；lightweight 模式保留 phase3 现有 inline 分支，并在代码注释里写明这是「架构上尚未统一」的已知缺口（`archive_change` 强制要求 worktree 存在，见 `_lib/archive.sh:589-592`）。

**本 change 必须一并处理的两处**：

1. `phase3_archive.sh` 自己的 `bash _lib/post_archive_cleanup.sh ...` 调用必须删除 —— `archive_change:725` 已经调过一次，保留会双跑（重复取 `git status` 快照、重复 `git add`，可能把 archive 之后的改动一并 stage）。
2. `phase3_archive.sh` 自己的 `cd .rddf/wt/* && openspec archive` 必须删除 —— 那是在 worktree 的**拷贝**里归档（F-7：记录随 worktree 清理丢失）。

**明确不在本 change 范围、但必须记录的缺口（分支合并没有执行点）**：

`archive_change` 的 `openspec_tracked=false` 分支**从不合并** `openspec/<name>` 分支（既有契约：`tests/integration/test_archive_with_openspec_tracked_false.bats` 的文件头写明「false 分支 SHALL NOT execute git merge AND commit_archive_moves」）。因此 worktree 模式的代码提交必须**在归档之前**由别的执行点合入默认分支，否则 `cleanup_worktree_and_branch` 会因 `git branch -d` 拒绝删除未合并分支而把提交搁浅在悬空分支上。

把 merge 塞进 `archive_change` 的 false 分支会**违反已签批契约**（该契约有源文本守卫 + 行为断言各一条），本 change 因此不做；正确解法是给流程补一个「合并分支」的执行点（P2 末尾或 P3 之前），属另一项提案。

同时，false 分支的门绑定**默认分支的 HEAD** ⇒ verdict cache 必须在合并**之后**打戳，否则门判 stale。这条约束也写进本 change 的 fixture（先合并、再打戳、再归档）。

**Tech Stack:** bash（`_lib/archive.sh` / `skills/rdd-builder/scripts/phase3_archive.sh`）+ bats。

---

## File Structure

### Production Code

| File | 类型 | Responsibility |
|---|---|---|
| `skills/rdd-builder/scripts/phase3_archive.sh` | 改 | worktree 模式改调 `archive_change` + 返回码映射；删除自带的 cleanup 调用；lightweight 分支保留 inline 并加缺口注释 |

### Tests

| File | 类型 | Responsibility |
|---|---|---|
| `tests/integration/test_phase3_archives_in_main_repo.bats` | 新 | F-7 的直接证明：归档发生在**主仓**（stub 记录 cwd）而非 worktree；worktree 被清理；handoff 记 archived |
| `tests/integration/test_phase3_archive_delegation.bats` | 新 | phase3 的委托与返回码映射（0→0 / 3→7 / 1→3）；worktree 模式下 phase3 不再自己调 `openspec archive` / `post_archive_cleanup` |
| `tests/integration/test_phase3_return_code_mapping.bats` | 新 | **行为级**返回码断言：门拒绝 ⇒ 7、分支无新提交 ⇒ 3、成功 ⇒ 0 且分支已合并进默认分支 |

---

### Task 1: 委托后归档落在主仓（F-7 的直接证明）

**Files:**
- Modify: `skills/rdd-builder/scripts/phase3_archive.sh`（与 Task 2 同一文件，先写测试）
- Test: `tests/integration/test_phase3_archives_in_main_repo.bats`

- [ ] **Step 1: Write the failing test**

fixture（git repo + `openspec_tracked=false` + worktree + 分支已合并 + 主仓侧 verdict cache），
用一个记录 `pwd` 的 `openspec` 桩：

```bash
@test "phase3: the archive runs in the MAIN repo, not in the worktree" {
    run env PROJECT_ROOT="$TEST_TMP" PATH="$TEST_TMP/bin:$PATH" \
        OPENSPEC_CALL_LOG="$TEST_TMP/calls.log" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/calls.log" ]
    grep -q "CWD=$TEST_TMP" "$TEST_TMP/calls.log"
    ! grep -q "CWD=$TEST_TMP/.rddf/wt/demo" "$TEST_TMP/calls.log"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_phase3_archives_in_main_repo.bats`
Expected: **FAIL** —— 旧实现 `cd $WT_PATH && openspec archive` ⇒ 桩记录的 cwd 是 worktree

- [ ] **Step 3: Write minimal implementation**

见 Task 2（委托 `archive_change`）。本 Task 的断言由该实现满足。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_phase3_archives_in_main_repo.bats`
Expected: 3/3 PASS

---

### Task 2: `phase3` 在 worktree 模式委托 `archive_change`

**Files:**
- Modify: `skills/rdd-builder/scripts/phase3_archive.sh`
- Test: `tests/integration/test_phase3_archive_delegation.bats`

- [ ] **Step 1: Write the failing test**

```bash
#!/usr/bin/env bats
# tests/integration/test_phase3_archive_delegation.bats
#
# P3 must delegate worktree-mode archiving to archive_change (the single
# implementation) and map its return codes:
#   0 → 0 (archived)   3 → 7 (gate refused)   1 → 3 (precondition/merge failed)

load ../test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    cd "$TEST_TMP"
    git init -q .
    git config user.email t@t.invalid
    git config user.name tester
    mkdir -p .rddf/state/builder openspec/changes/demo bin
    ln -s "$REPO_ROOT/_lib" _lib
    printf '# demo\n\n## Acceptance\n\n- [ ] AC one\n' > openspec/changes/demo/proposal.md
    printf '## Tasks\n\n- [x] task one\n' > openspec/changes/demo/tasks.md
    printf '{"execution_mode_decision": {"mode": "worktree"}}\n' > .rddf/state/builder/demo.json
    printf '#!/bin/sh\nexit 0\n' > bin/openspec
    chmod +x bin/openspec
    git add -A && git commit -q -m fixture
}

teardown() {
    cd /
    rm -rf "$TEST_TMP"
}

@test "phase3: worktree mode without a worktree exits 3" {
    run env PROJECT_ROOT="$TEST_TMP" PATH="$TEST_TMP/bin:$PATH" \
        bash "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh" demo
    [ "$status" -eq 3 ]
}

@test "phase3: no longer calls 'openspec archive' itself in worktree mode" {
    # The delegation owns the archive; a second call would archive twice.
    run grep -c "openspec archive" "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh"
    # exactly one occurrence: the lightweight branch
    [ "$output" -eq 1 ]
}

@test "phase3: no longer calls post_archive_cleanup itself (archive_change does)" {
    run grep -c "post_archive_cleanup" "$REPO_ROOT/skills/rdd-builder/scripts/phase3_archive.sh"
    [ "$output" -eq 0 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_phase3_archive_delegation.bats`
Expected: 后两条 **FAIL**（当前 phase3 仍自己调 `openspec archive` 与 `post_archive_cleanup`）

- [ ] **Step 3: Write minimal implementation**

`phase3_archive.sh` 的归档段改为：

```bash
if [ "$EXEC_MODE" = "worktree" ]; then
    # Single implementation: archive_change owns gate / merge / openspec
    # archive / cleanup / iteration sync. Delegating also fixes the F-7
    # record loss: it archives in the MAIN repo (the authoritative
    # openspec/), not in the worktree copy.
    archive_change "$CHANGE_NAME"
    rc=$?
    case "$rc" in
        0) ;;
        3) echo "❌ archive gate refused the archive for $CHANGE_NAME" >&2; exit 7 ;;
        *) echo "❌ archive_change failed for $CHANGE_NAME (exit $rc)" >&2; exit 3 ;;
    esac
else
    # lightweight mode: inline archive (archive_change requires a worktree,
    # see _lib/archive.sh:589-592). KNOWN GAP: the gate, the cleanup and the
    # iteration sync of this branch are not the archive_change ones —
    # documented in .rddf/improvements/fix-worktree-archive-path.md.
    archive_gate_check "$CHANGE_NAME" "$TASKS_ROOT" || exit 7
    openspec archive "$CHANGE_NAME" --yes 2>/dev/null || {
        echo "openspec archive FAIL for $CHANGE_NAME" >&2
        exit 7
    }
fi
```

并删除 phase3 原有的 `bash _lib/post_archive_cleanup.sh ...` 一行（archive_change 内部已调）。

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_phase3_archive_delegation.bats`
Expected: 3/3 PASS

---

### Task 3: 遗留清扫 + 全量回归

- [ ] **Step 1: 泄漏清扫**

```bash
grep -rn "post_archive_cleanup\|openspec archive" skills/rdd-builder/scripts/phase3_archive.sh
git diff --stat master..HEAD
```

- [ ] **Step 2: 本 change 测试**

```bash
bats tests/integration/test_phase3_archives_in_main_repo.bats \
     tests/integration/test_phase3_archive_delegation.bats \
     tests/integration/test_phase3_return_code_mapping.bats \
     tests/integration/test_archive*.bats \
     tests/integration/test_rdd_builder_phase3_archive.bats
python3 -m pytest tests/unit/test_phase3_verifier_wiring.py -q
```

- [ ] **Step 3: 全量回归（archive 前门）**

```bash
./test.sh --full --regression
```
Expected: 无新增失败（既有 11 项已知失败 + 2 项已归因的既有失败保持不变）

- [ ] **Step 4: doctor 全量**

```bash
bash skills/rdd-doctor/scripts/doctor.sh
```
Expected: 0 CRITICAL

---

## 审稿记录（critic 第 1 轮，REJECT → 修复）

critic 第 1 轮结论 **REJECT（mergeable: no）**，1 BLOCKER + 3 SHOULD_FIX。逐条处置：

- **BLOCKER（返回码映射是死代码）**：`set -euo pipefail` 下裸调用 `archive_change` 返回非零时 shell 立即按该状态退出，`rc=$?` 与 `case` 映射**从不执行** ⇒ 门拒绝（3）实际退出 3、merge 失败实际退出 1，与本脚本头声明的「7 = archive gate」和 improvement 的 AC 冲突。
  修法：`archive_change "$CHANGE_NAME" || rc=$?`。
  **并补行为级测试**（critic 指出原断言是 grep 源文本的「假绿」）：新增 `test_phase3_return_code_mapping.bats`，三例分别断言门拒绝 ⇒ 7、分支无新提交 ⇒ 3、成功 ⇒ 0（且分支已合并进默认分支）。
- **SHOULD_FIX（头注释与映射表自相矛盾）**：头注释原写「7 = archive gate **or openspec archive failure**」，而映射表把 worktree 模式的 openspec 失败归到 3。已改写头注释，明确列出 2/3/7 三个码各自的含义。
- **SHOULD_FIX（CONTRACT 注释给错指引）**：注释原说「worktree 模式 ⇒ 在 worktree 打戳」，但委托后 false 配置的门绑**主仓** HEAD ⇒ 该配置下必须在主仓打戳。已改为按 `openspec_tracked` 两格分述（true → worktree / false → 主仓），并说明 lightweight 模式用 `$TASKS_ROOT`。
- **SHOULD_FIX（委托前缺 cwd 锚定）**：`archive_change` 内部的 `openspec archive` 以**调用方 cwd** 为项目根。已在委托前加 `cd "$PROJECT_ROOT"`，把隐式契约变成显式。
- **附带修复**：`archive_change` 的 tracked 分支把门静默了（`>/dev/null`），导致门拒绝时调用方看不到原因（false 分支不静默，两边不一致）。已改为不静默 —— 这样 phase3 的「透传 gate 文案」AC 才成立。

**被 critic 确认成立的一项取舍**：把「合并 worktree 分支」加进 `archive_change` 的 false 分支会违反已签批契约（既有测试文件头引用 complete-project-yaml-config-gaps L254「false 分支 SHALL NOT execute git merge AND commit_archive_moves」，且有行为断言 + 源文本守卫），因此该项被否决并留在范围外（计划「已知缺口」段有记录）。critic 同时指出：**本仓自身就是 false 配置 ⇒ 本仓 worktree 模式的代码提交在 P3 后确实没有执行点合回主干** —— 该 follow-up 的优先级应偏高。
