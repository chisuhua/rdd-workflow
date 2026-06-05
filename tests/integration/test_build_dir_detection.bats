#!/usr/bin/env bats
# tests/integration/test_build_dir_detection.bats
# P2-2 regression: guide-spec's "构建目录" check used to hardcode `build/`,
# which is wrong for Rust (target/), Node (node_modules/), Python (venv/).
# The audit report flagged this in guide-spec.md:103-107. We now detect the
# project type from manifest files and check the right build dir.
#
# These tests lock the generalization in place:
#   1. guide-spec.md has project type detection logic (not just `[ -d "build" ]`).
#   2. All 4 common project types are supported (Rust, Node.js, Python, C++/Make).
#   3. There is a default fallback ("Unknown" or equivalent) when no manifest
#      matches, so the check still produces a sensible message.

load ../test_helper

@test "guide-spec.md has project type detection (P2-2)" {
  [ -f "$REPO_ROOT/skills/guide-spec.md" ]
  # Detection logic must be present: PROJECT_TYPE variable or any of the
  # canonical manifest filenames used by the if/elif chain.
  grep -qE "PROJECT_TYPE|Cargo\.toml|package\.json" "$REPO_ROOT/skills/guide-spec.md"
}

@test "guide-spec.md has 4 project types supported" {
  [ -f "$REPO_ROOT/skills/guide-spec.md" ]
  grep -q "Rust" "$REPO_ROOT/skills/guide-spec.md"
  grep -qE "Node\.js|package\.json" "$REPO_ROOT/skills/guide-spec.md"
  grep -q "Python" "$REPO_ROOT/skills/guide-spec.md"
  grep -qE "C\+\+/Make|CMakeLists" "$REPO_ROOT/skills/guide-spec.md"
}

@test "guide-spec.md has default fallback for unknown project type" {
  [ -f "$REPO_ROOT/skills/guide-spec.md" ]
  # The else branch must set PROJECT_TYPE to something (Unknown or 默认) so
  # the check still emits a sensible build-dir warning.
  grep -qE "Unknown.*PROJECT_TYPE|PROJECT_TYPE=.*Unknown|默认.*fallback" "$REPO_ROOT/skills/guide-spec.md"
}
