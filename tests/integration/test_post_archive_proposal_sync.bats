#!/usr/bin/env bats
# tests/integration/test_post_archive_proposal_sync.bats
#
# Regression coverage for fix-proposal-approved-sync (P0, 2026-08-21):
# After post_archive_cleanup runs, proposal-approved.md should reflect
# the archive status — entries with a matching archive/<date>-<name>/
# directory MUST be moved from "## 已批准提案" to "## 已实施".
#
# Background: `_lib/state.sh::sweep_implemented_proposals` exists and
# does the right thing, but no caller invokes it. This test pins the
# contract that `post_archive_cleanup <root> <name>` MUST trigger this
# scan so proposal-approved.md stays consistent with the archive/ tree.
#
# Without the fix: this test fails — the entry stays in "## 已批准提案"
# even after archive dir is created + post_archive_cleanup runs.
# With the fix: this test passes — the entry is moved to "## 已实施".
load ../test_helper

setup() {
  TEST_TMPDIR="$(mktemp -d)"
  export PROJECT_ROOT="$TEST_TMPDIR/fake-repo"
  mkdir -p "$PROJECT_ROOT"/{_lib,openspec/changes,openspec/specs,.rddf/state,.rddf/improvements}
  cd "$PROJECT_ROOT"
  git init -q -b master
  git config user.email "test@example.com"
  git config user.name "Test"
  git commit --allow-empty -m "init" -q

  # Source the post-archive hook under test (with state.sh scratch copy)
  cp "$BATS_TEST_DIRNAME/../../_lib/state.sh" "$PROJECT_ROOT/_lib/state.sh"
  source "$BATS_TEST_DIRNAME/../../_lib/post_archive_cleanup.sh"
  source "$PROJECT_ROOT/_lib/state.sh"
}

teardown() { rm -rf "$TEST_TMPDIR"; }

# helper: build a proposal-approved.md with one approved entry
# AND seed the matching archive dir so sweep_implemented_proposals
# will detect the mismatch.
seed_approved_proposal() {
  local name="$1"
  local priority="$2"
  local proposal_dir="$PROJECT_ROOT/openspec/changes/archive/2026-08-21-${name}"
  mkdir -p "$proposal_dir"
  echo "marker" > "$proposal_dir/.marker"
  # proposal-approved.md: entry sits in ## 已批准提案 section
  cat > "$PROJECT_ROOT/proposal-approved.md" <<EOF
## 已批准提案

| [${name}](.rddf/improvements/${name}.md) | ${priority} | 2026-08-21 | guide-arch |

## 已实施

| 提案 | 优先级 | 完成时间 | 状态 |
|------|--------|----------|------|
EOF
  git add proposal-approved.md openspec/changes/archive/2026-08-21-${name}
  git commit -q -m "seed"
}

@test "post_archive_cleanup: sync proposal-approved.md — archived entry moves from approved to implemented" {
  seed_approved_proposal "fix-ship-orphan" "P1"

  # Pre-condition: entry in ## 已批准提案 section
  run python3 -c "
content = open('$PROJECT_ROOT/proposal-approved.md').read()
section = content.split('## 已实施')[0]
print('PRESENT_IN_APPROVED' if 'fix-ship-orphan' in section else 'GONE_FROM_APPROVED')
"
  [ "$output" = "PRESENT_IN_APPROVED" ]

  # Run the hook under test
  run post_archive_cleanup "$PROJECT_ROOT" "fix-ship-orphan"
  [ "$status" -eq 0 ]

  # Post-condition: entry moved to ## 已实施 section
  # Specifically: NO MORE occurrence of the proposal name above
  # the "## 已实施" heading.
  run python3 -c "
content = open('$PROJECT_ROOT/proposal-approved.md').read()
section = content.split('## 已实施')[0]
print('PRESENT_IN_APPROVED' if 'fix-ship-orphan' in section else 'GONE_FROM_APPROVED')
"
  [ "$output" = "GONE_FROM_APPROVED" ]

  # And the entry appears in ## 已实施 section
  run python3 -c "
content = open('$PROJECT_ROOT/proposal-approved.md').read()
printed = content.split('## 已实施')[1] if '## 已实施' in content else ''
print('PRESENT_IN_IMPLEMENTED' if 'fix-ship-orphan' in printed else 'MISSING_FROM_IMPLEMENTED')
"
  [ "$output" = "PRESENT_IN_IMPLEMENTED" ]
}

@test "post_archive_cleanup: idempotent — second run on same archive dir produces no change" {
  seed_approved_proposal "fix-double-archive" "P2"

  # First run: should move the entry
  post_archive_cleanup "$PROJECT_ROOT" "fix-double-archive"
  local content_after_first
  content_after_first=$(cat "$PROJECT_ROOT/proposal-approved.md")

  # Second run: should NOT add a duplicate entry
  SKIP_POST_ARCHIVE_CLEANUP_AUTO_COMMIT=yes post_archive_cleanup "$PROJECT_ROOT" "fix-double-archive"
  local content_after_second
  content_after_second=$(cat "$PROJECT_ROOT/proposal-approved.md")

  [ "$content_after_first" = "$content_after_second" ]

  # Verify exactly one occurrence in the file
  local count
  count=$(grep -c "fix-double-archive" "$PROJECT_ROOT/proposal-approved.md" || true)
  [ "$count" -eq 1 ]
}

@test "post_archive_cleanup: SKIP_POST_ARCHIVE_CLEANUP=yes preserves approved entry" {
  seed_approved_proposal "fix-skip-test" "P1"

  SKIP_POST_ARCHIVE_CLEANUP=yes run post_archive_cleanup "$PROJECT_ROOT" "fix-skip-test"
  [ "$status" -eq 0 ]

  # The entry should still be in ## 已批准提案 (sync is part of hook)
  run python3 -c "
content = open('$PROJECT_ROOT/proposal-approved.md').read()
section = content.split('## 已实施')[0]
print('PRESENT_IN_APPROVED' if 'fix-skip-test' in section else 'GONE_FROM_APPROVED')
"
  [ "$output" = "PRESENT_IN_APPROVED" ]
}

@test "post_archive_cleanup: handles multiple archived proposals in one go" {
  seed_approved_proposal "fix-bulk-a" "P1"
  # Insert a second approved entry (no archive dir) BEFORE the ## 已实施 section
  python3 -c "
content = open('$PROJECT_ROOT/proposal-approved.md').read()
marker = '| [fix-bulk-pending](.rddf/improvements/fix-bulk-pending.md) | P2 | 2026-08-21 | guide-arch |'
before, after = content.split('## 已实施', 1)
new_content = before + marker + '\n\n' + '## 已实施' + after
with open('$PROJECT_ROOT/proposal-approved.md', 'w') as f:
    f.write(new_content)
print('OK')
"
  git add proposal-approved.md
  git commit -q -m "add fix-bulk-pending"

  post_archive_cleanup "$PROJECT_ROOT" "fix-bulk-a"

  # fix-bulk-a should be moved
  run python3 -c "
content = open('$PROJECT_ROOT/proposal-approved.md').read()
section = content.split('## 已实施')[0]
print('STILL_APPROVED' if 'fix-bulk-a' in section else 'MOVED')
"
  [ "$output" = "MOVED" ]

  # fix-bulk-pending (no archive dir) should remain
  run python3 -c "
content = open('$PROJECT_ROOT/proposal-approved.md').read()
section = content.split('## 已实施')[0]
print('STILL_APPROVED' if 'fix-bulk-pending' in section else 'MOVED')
"
  [ "$output" = "STILL_APPROVED" ]
}
