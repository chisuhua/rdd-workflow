#!/usr/bin/env bats
# tests/integration/test_phase2_install_full.bats
#
# Phase 2 regression test: verify INSTALL.md's install logic actually copies
# per-skill scripts/ contents to the target project (per ADR-0021 Decision 4).
# This test simulates a full install into a temp dir and checks the result.

load ../test_helper

setup() {
  cd "$REPO_ROOT"
  TEST_DEST=$(mktemp -d)
}

teardown() {
  [ -n "$TEST_DEST" ] && rm -rf "$TEST_DEST"
}

@test "phase2_install: INSTALL.md copy loop populates scripts/ in target" {
  # Extract the for-loop from INSTALL.md L99-115 (or wherever after Phase 2 update)
  # and run it against TEST_DEST
  SKILLS_DIR="$TEST_DEST/.opencode/skills/rdd-workflow"
  PACKAGE_DIR="$REPO_ROOT"

  # Source the relevant INSTALL.md bash block — extract L88-143 (Phase 1 layout)
  # plus any new Phase 2 additions
  bash -c "
    PACKAGE_DIR='$PACKAGE_DIR'
    SKILLS_DIR='$SKILLS_DIR'
    $(awk '/^# 复制所有子技能/,/^# 复制 skills\/_lib/' skills/INSTALL.md)
    if [ -d \"\$PACKAGE_DIR/skills/_lib\" ]; then
        mkdir -p \"\$SKILLS_DIR/_lib/schemas\"
        find \"\$PACKAGE_DIR/skills/_lib\" \
            -type d \\( -name __pycache__ -o -name plugins -o -name schedulers \\) -prune \
            -o -type f \\( -name '*.py' -o -name '*.json' -o -name '*.sh' \\) -print 2>/dev/null | while read -r src; do
            rel=\"\${src#\$PACKAGE_DIR/}\"
            mkdir -p \"\$SKILLS_DIR/\$(dirname \"\$rel\")\"
            cp -f \"\$src\" \"\$SKILLS_DIR/\$rel\"
        done
    fi
  " 2>/dev/null

  # Check: per-skill scripts/ in target has at least 1 file (per skill)
  for skill in guide guide-arch guide-plan guide-ship propose execute feature status deps rddf-session; do
    [ -d "$SKILLS_DIR/skills/$skill/scripts" ] || {
      echo "FAIL: $skill/scripts/ not created in target"
      return 1
    }
    local n
    n=$(find "$SKILLS_DIR/skills/$skill/scripts" -maxdepth 1 -type f | wc -l)
    [ "$n" -ge 1 ] || {
      echo "FAIL: $skill/scripts/ has $n files (expected >= 1) after INSTALL"
      return 1
    }
  done
}

@test "phase2_install: install preserves _lib/ shared files (state.sh, worktree.sh)" {
  SKILLS_DIR="$TEST_DEST/.opencode/skills/rdd-workflow"
  PACKAGE_DIR="$REPO_ROOT"
  bash -c "
    PACKAGE_DIR='$PACKAGE_DIR'
    SKILLS_DIR='$SKILLS_DIR'
    $(awk '/^# 复制所有子技能/,/^# 复制 skills\/_lib/' skills/INSTALL.md)
    if [ -d \"\$PACKAGE_DIR/skills/_lib\" ]; then
        mkdir -p \"\$SKILLS_DIR/_lib/schemas\"
        find \"\$PACKAGE_DIR/skills/_lib\" \
            -type d \\( -name __pycache__ \\) -prune \
            -o -type f \\( -name '*.py' -o -name '*.sh' \\) -print 2>/dev/null | while read -r src; do
            rel=\"\${src#\$PACKAGE_DIR/}\"
            mkdir -p \"\$SKILLS_DIR/\$(dirname \"\$rel\")\"
            cp -f \"\$src\" \"\$SKILLS_DIR/\$rel\"
        done
    fi
  " 2>/dev/null

  # Shared files should be in _lib/ of target
  [ -f "$SKILLS_DIR/_lib/state.sh" ] || return 1
  [ -f "$SKILLS_DIR/_lib/worktree.sh" ] || return 1

  # Moved files should NOT be in _lib/ of target (they belong in per-skill scripts/)
  ! [ -f "$SKILLS_DIR/_lib/ship_plan.sh" ] || {
    echo "FAIL: ship_plan.sh still in _lib/ (should be in guide-ship/scripts/)"
    return 1
  }
  # And should BE in per-skill scripts/ of target
  [ -f "$SKILLS_DIR/skills/guide-ship/scripts/ship_plan.sh" ] || {
    echo "FAIL: ship_plan.sh not in guide-ship/scripts/ of target"
    return 1
  }
}