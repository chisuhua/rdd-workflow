#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TMP="$(mktemp -d)"
  export RDDF_PROJECT_ROOT="$TMP"
  mkdir -p "$TMP/openspec/changes/test-cross-repo"
  cat > "$TMP/openspec/changes/test-cross-repo/roadmap-meta.yaml" <<EOF
name: test-cross-repo
category: cross-repo-federation
EOF
}

teardown() { rm -rf "$TMP"; }

@test "approve --auto-accept on cross-repo exits 3 (blocked)" {
  cd "$TMP"
  run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --auto-accept
  [ "$status" -eq 3 ]
  [[ "$output" =~ "manual" || "$output" =~ "Hub" ]]
}

@test "approve --manual --hub-issue on cross-repo requires interactive input" {
  cd "$TMP"
  mkdir -p "$TMP/.rddf/improvements"
  echo "# test-cross-repo" > "$TMP/.rddf/improvements/test-cross-repo.md"
  # Run without stdin pipe - script will read from /dev/null
  run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --manual --hub-issue "fake-org/rdd-hub#42" < /dev/null
  # Exit should NOT be 3 (cross-repo blocked)
  # status 1 = missing proposal-approved.md (expected in isolated test env)
  # status 0 = success
  [ "$status" -ne 3 ]
}

@test "approve non-cross-repo with --auto-accept still works" {
  cd "$TMP"
  cat > "$TMP/openspec/changes/test-cross-repo/roadmap-meta.yaml" <<EOF
name: test-cross-repo
category: core
EOF
  # Should succeed (or fail on Hub fetch if --hub-issue required, but exit != 3)
  run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --auto-accept
  [ "$status" -ne 3 ]
}

@test "design-done gate blocks when cross-repo proposal lacks audit log" {
  cd "$TMP"
  cat > "$TMP/openspec/changes/test-cross-repo/roadmap-meta.yaml" <<EOF
name: test-cross-repo
category: cross-repo-federation
EOF
  # No audit log entry exists
  run env RDDF_PROJECT_ROOT="$TMP" STRICT_DESIGN_GATE=yes python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills.guide_design.scripts.design_done_gate import check_cross_repo_approvals
result = check_cross_repo_approvals()
sys.exit(1 if result else 0)
"
  [ "$status" -ne 0 ]
}
