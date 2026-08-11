#!/usr/bin/env bats
# Tests for worktree-archive-workflow change
# Verifies explicit documentation of worktree commit flow in AGENTS.md and guide-ship/SKILL.md
# (Reference: .rddf/improvements/worktree-archive-workflow.md)

load ../test_helper

# === AGENTS.md 验证 ===

@test "AGENTS.md: Worktree Commit Flow section exists" {
  run grep -c "^### Worktree Commit Flow" AGENTS.md
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]
}

@test "AGENTS.md: Worktree Commit Flow mentions execute and archive phases" {
  run grep -E "Phase 2 execute|Phase 3 archive" AGENTS.md
  [ "$status" -eq 0 ]
  [[ "$output" == *"Phase 2 execute"* ]]
  [[ "$output" == *"Phase 3 archive"* ]]
}

@test "AGENTS.md: Worktree Commit Flow lists 5 conventional commit types" {
  run grep -cE "^   - \`[a-z]+\(<scope>\):" AGENTS.md
  [ "$status" -eq 0 ]
  [ "$output" -ge 5 ]
}

@test "AGENTS.md: trap #6 updated to mention worktree-internal commit" {
  run grep "execute 阶段不逐任务 commit" AGENTS.md
  [ "$status" -eq 0 ]
  [[ "$output" == *"worktree-internal commit"* ]] || [[ "$output" == *"worktree 内做 1 个聚合 commit"* ]]
}

@test "AGENTS.md: trap #6 cross-references Worktree Commit Flow" {
  run grep -A 2 "execute 阶段不逐任务 commit" AGENTS.md
  [ "$status" -eq 0 ]
  [[ "$output" == *"Worktree Commit Flow"* ]]
}

@test "AGENTS.md: 归档流程 cross-references check_worktree_commits" {
  run grep -A 8 "^### 归档流程" AGENTS.md
  [ "$status" -eq 0 ]
  [[ "$output" == *"check_worktree_commits"* ]]
}

# === guide-ship/SKILL.md 验证 ===

@test "guide-ship/SKILL.md: Phase 2.7 section exists" {
  run grep -c "^## Phase 2.7" skills/guide-ship/SKILL.md
  [ "$status" -eq 0 ]
  [ "$output" -eq 1 ]
}

@test "guide-ship/SKILL.md: Phase 2.7 references worktree-archive-workflow proposal" {
  run grep -A 4 "Phase 2.7" skills/guide-ship/SKILL.md
  [ "$status" -eq 0 ]
  [[ "$output" == *"worktree-archive-workflow"* ]]
}

@test "guide-ship/SKILL.md: Phase 2.7 lists 5 commit message conventions" {
  run grep -E "^   - \`[a-z]+\(<scope>\):" skills/guide-ship/SKILL.md
  [ "$status" -eq 0 ]
  [[ "$output" == *"feat(<scope>):"* ]]
  [[ "$output" == *"fix(<scope>):"* ]]
  [[ "$output" == *"refactor(<scope>):"* ]]
  [[ "$output" == *"test(<scope>):"* ]]
  [[ "$output" == *"chore(<scope>):"* ]]
}

@test "guide-ship/SKILL.md: Phase 2.7 mentions archive.sh check_worktree_commits" {
  run grep -A 30 "Phase 2.7" skills/guide-ship/SKILL.md
  [ "$status" -eq 0 ]
  [[ "$output" == *"check_worktree_commits"* ]]
}

@test "guide-ship/SKILL.md: Phase 2.7 has 5-step operational workflow" {
  run grep -A 60 "Phase 2.7" skills/guide-ship/SKILL.md
  [ "$status" -eq 0 ]
  [[ "$output" == *"# 1."* ]]
  [[ "$output" == *"# 2."* ]]
  [[ "$output" == *"# 3."* ]]
  [[ "$output" == *"# 4."* ]]
  [[ "$output" == *"# 5."* ]]
}
