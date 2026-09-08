#!/usr/bin/env bats
# Tests for worktree-archive-workflow change
# Verifies explicit documentation of worktree commit flow in AGENTS.md.
# (Reference: .rddf/improvements/worktree-archive-workflow.md)
#
# Note (2026-09-08): the v3 rdd-builder/SKILL.md "Phase 2.7" sub-section tests
# were removed — v4 rdd-builder SKILL.md (per ADR-0042/0043) was slimmed to a
# 52-line spec-style doc (P0/P1/P1.5/P2/P2.5/P3 state machine). The Phase 2.7
# content (5 commit types list, worktree-archive-workflow proposal reference,
# check_worktree_commits mention) is now consolidated in AGENTS.md and verified
# by the @test 1-6 above.

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

