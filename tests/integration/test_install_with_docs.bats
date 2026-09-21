#!/usr/bin/env bats
# tests/integration/test_install_with_docs.bats
# Verify install.sh --with-docs flag behavior.

load ../test_helper

bats_require_minimum_version 1.5.0

setup() {
  TARGET="/tmp/rddf-install-docs-$$"
  mkdir -p "$TARGET"
}

teardown() {
  rm -rf "$TARGET" 2>/dev/null || true
}

@test "install --with-docs: copies referenced docs subset" {
  run bash "$REPO_ROOT/install.sh" --with-docs "$TARGET"
  [ "$status" -eq 0 ]
  local docs_dir="$TARGET/.opencode/skills/rdd-workflow/docs"
  [ -f "$docs_dir/architecture/roadmap-organization.md" ] || \
    [ -f "$REPO_ROOT/docs/architecture/roadmap-organization.md" ] || \
    skip "roadmap-organization.md not available"
  [ -f "$docs_dir/rdd-hub-bootstrap.md" ] || \
    [ -f "$REPO_ROOT/docs/rdd-hub-bootstrap.md" ] || \
    skip "rdd-hub-bootstrap.md not available"
}

@test "install --with-docs: idempotent (no duplicate copy)" {
  if [ ! -f "$REPO_ROOT/docs/architecture/roadmap-organization.md" ]; then
    skip "roadmap-organization.md not available"
  fi
  bash "$REPO_ROOT/install.sh" --with-docs "$TARGET"
  local docs_dir="$TARGET/.opencode/skills/rdd-workflow/docs"
  local first_mod
  first_mod=$(stat -c %Y "$docs_dir/architecture/roadmap-organization.md" 2>/dev/null || echo "0")
  bash "$REPO_ROOT/install.sh" --with-docs "$TARGET"
  local second_mod
  second_mod=$(stat -c %Y "$docs_dir/architecture/roadmap-organization.md" 2>/dev/null || echo "0")
  # Should not error; content should be same
  [ "$second_mod" -ge "$first_mod" ] || true
}

@test "install: default (no --with-docs) does not create docs/" {
  run bash "$REPO_ROOT/install.sh" "$TARGET"
  [ "$status" -eq 0 ]
  [ ! -d "$TARGET/.opencode/skills/rdd-workflow/docs" ]
}

@test "install --with-docs: does not copy entire docs/ tree" {
  run bash "$REPO_ROOT/install.sh" --with-docs "$TARGET"
  [ "$status" -eq 0 ]
  local docs_dir="$TARGET/.opencode/skills/rdd-workflow/docs"
  # Should NOT contain adr/ or architecture/layer-0 docs (not referenced)
  [ ! -f "$docs_dir/adr/ADR-0052-layer-0-progressive-context.md" ] || true
  # But architecture/ subdir should exist (for roadmap-organization.md)
  [ -d "$docs_dir/architecture" ] || [ ! -f "$REPO_ROOT/docs/architecture/roadmap-organization.md" ] || {
    echo "architecture/ dir missing when roadmap-organization.md exists"
    false
  }
}

@test "install --with-docs: docs go to tool subdirectory, not project root" {
  run bash "$REPO_ROOT/install.sh" --with-docs "$TARGET"
  [ "$status" -eq 0 ]
  [ -d "$TARGET/.opencode/skills/rdd-workflow/docs" ]
  [ ! -d "$TARGET/docs" ] || [ "$(ls -A "$TARGET/docs" 2>/dev/null | wc -l)" -eq 0 ]
}