#!/usr/bin/env bats
# tests/integration/test_root_anchoring_residue.bats
#
# fix-path-anchoring-residue — the residue left by
# fix-script-project-root-anchoring (which anchored skills/rdd-builder/scripts
# and froze the static gate's scan surface).
#
# These contracts are about the same thing everywhere: **the read/write landing
# point must be derived from the project root, not from the process cwd**. In
# all cases below cwd is the REAL repo and the root points at a FAKE one, so
# "it happened to work because cwd == root" cannot mask a regression — and a
# leak would land in the real repo, which the assertions also check.

load ../test_helper

setup() {
    FAKE="$BATS_TEST_TMPDIR/fake-repo"
    mkdir -p "$FAKE/openspec/changes/demo"
    printf -- '## Why\n\ndemo\n' > "$FAKE/openspec/changes/demo/proposal.md"
    printf -- '## Tasks\n- [x] one\n' > "$FAKE/openspec/changes/demo/tasks.md"
    AUDIT_FILE="$REPO_ROOT/.rddf/state/.bypass-audit.jsonl"
    [ -f "$AUDIT_FILE" ] || : > "$AUDIT_FILE"
}

# ── planner_stage_entry.sh / planner_stage_exit.sh（Task 2）───────────────
#
# Both scripts declare PROJECT_ROOT on line 6 and then used cwd for
# openspec/changes/<name> and .rddf/state/.planner-state.json. The assertions
# below are on the "not found" MESSAGE rather than the exit code, because the
# exit code also reflects later stages (handoff emission, double gate) that are
# not under test here.

@test "planner_stage_entry: 读/写落点都在 PROJECT_ROOT（change 目录 + handoff）" {
  marker="$BATS_TEST_TMPDIR/marker"; : > "$marker"; sleep 1
  run env PROJECT_ROOT="$FAKE" bash "$REPO_ROOT/skills/rdd-planner/scripts/planner_stage_entry.sh" demo
  [ "$status" -eq 0 ]
  [[ "$output" != *"not found"* ]]
  # 写方向：handoff 落在假仓，真仓那份不得被碰
  [ -f "$FAKE/.rddf/state/.planner-handoff.json" ]
  [ -z "$(find "$REPO_ROOT/.rddf/state/.planner-handoff.json" -newer "$marker" 2>/dev/null)" ]
}

@test "planner_stage_entry: cwd 有该 change 而 PROJECT_ROOT 没有 ⇒ 仍报 not found（不读 cwd）" {
  LOCAL="$BATS_TEST_TMPDIR/cwd-repo"
  mkdir -p "$LOCAL/openspec/changes/demo"
  run env PROJECT_ROOT="$BATS_TEST_TMPDIR/empty-root" \
      bash -c "cd '$LOCAL' && bash '$REPO_ROOT/skills/rdd-planner/scripts/planner_stage_entry.sh' demo"
  [ "$status" -eq 2 ]
  [[ "$output" == *"not found"* ]]
}

@test "planner_stage_exit: 读 PROJECT_ROOT 下的 change 目录（不是 cwd）" {
  run env PROJECT_ROOT="$FAKE" bash "$REPO_ROOT/skills/rdd-planner/scripts/planner_stage_exit.sh" demo
  [[ "$output" != *"not found"* ]]
}

@test "planner_stage_exit: 门控1 认 \$PROJECT_ROOT/.rddf/roadmap.md" {
  mkdir -p "$FAKE/.rddf"
  printf '# Roadmap\n' > "$FAKE/.rddf/roadmap.md"
  # cwd 是另一个假仓：有 change 目录、**没有** roadmap。改前门控1 读 cwd 那份 ⇒
  # 报门控1；改后读 PROJECT_ROOT 那份 ⇒ 门控1 通过，停在门控2。
  CWD_REPO="$BATS_TEST_TMPDIR/cwd-repo-no-roadmap"
  mkdir -p "$CWD_REPO/openspec/changes/demo"
  run env PROJECT_ROOT="$FAKE" \
      bash -c "cd '$CWD_REPO' && bash '$REPO_ROOT/skills/rdd-planner/scripts/planner_stage_exit.sh' demo"
  [[ "$output" != *"门控1"* ]]
  [[ "$output" == *"门控2"* ]]
}

@test "planner_stage_exit: PROJECT_ROOT 下没有 roadmap ⇒ 门控1 仍拒绝（真仓有也救不了）" {
  # 真仓（cwd）确实有 .rddf/roadmap.md —— 门控1 必须只看 PROJECT_ROOT 那份
  NO_ROADMAP="$BATS_TEST_TMPDIR/no-roadmap"
  mkdir -p "$NO_ROADMAP/openspec/changes/demo"
  [ -f "$REPO_ROOT/.rddf/roadmap.md" ]

  run env PROJECT_ROOT="$NO_ROADMAP" \
      bash "$REPO_ROOT/skills/rdd-planner/scripts/planner_stage_exit.sh" demo
  [ "$status" -eq 2 ]
  [[ "$output" == *"门控1"* ]]
}

# ── _lib/archive.sh 的 SKIP_RDD_VERIFIER 审计落点（Task 4）─────────────────
#
# archive_gate_check used to leave the audit in ${RDDF_PROJECT_ROOT:-$PWD},
# while verifier_contract_check UNSETS RDDF_PROJECT_ROOT on its way out ⇒ the
# effective root was always the cwd. rdd doctor's bypass-audit threshold counts
# <project root>/.rddf/state/.bypass-audit.jsonl, so an entry written to cwd is
# an audit nobody reads.

@test "archive_gate_check: SKIP_RDD_VERIFIER 审计落进 canonical 主仓根（不是 cwd）" {
  MAIN="$BATS_TEST_TMPDIR/fake-main"
  WT="$BATS_TEST_TMPDIR/fake-wt"
  mkdir -p "$MAIN"
  git -C "$MAIN" init -q -b main
  git -C "$MAIN" config user.email t@t.local
  git -C "$MAIN" config user.name t
  printf 'seed\n' > "$MAIN/seed.txt"
  git -C "$MAIN" add -A >/dev/null
  git -C "$MAIN" commit -q -m init
  git -C "$MAIN" worktree add -q "$WT" -b openspec/demo
  mkdir -p "$WT/openspec/changes/demo"
  printf -- '## Tasks\n- [x] one\n' > "$WT/openspec/changes/demo/tasks.md"
  printf -- '## Acceptance Criteria\n- AC-1: works\n' > "$WT/openspec/changes/demo/proposal.md"

  before_real=$(wc -l < "$AUDIT_FILE")

  run env SKIP_RDD_VERIFIER=yes RDDF_VERIFIER_BYPASS_REASON="residue contract" \
      bash -c "source '$REPO_ROOT/_lib/archive.sh' && archive_gate_check 'demo' '$WT'"

  # 1) 审计落进 canonical 主仓根（$state_root），且恰好一条
  [ -f "$MAIN/.rddf/state/.bypass-audit.jsonl" ]
  [ "$(wc -l < "$MAIN/.rddf/state/.bypass-audit.jsonl")" -eq 1 ]
  grep -q '"env_var": "SKIP_RDD_VERIFIER"' "$MAIN/.rddf/state/.bypass-audit.jsonl"
  # 2) 真仓（cwd）零写入
  [ "$(wc -l < "$AUDIT_FILE")" -eq "$before_real" ]
  # 3) 也不落 worktree（归档后它就没了）
  [ ! -f "$WT/.rddf/state/.bypass-audit.jsonl" ]
}
