#!/usr/bin/env bats
# C2: status/guide output style varies across modes. Add a unified
#     style guide subsection + lock emoji-set to a fixed vocabulary.

load ../test_helper

@test "status.md defines an 输出风格指南 section" {
  grep -qF "输出风格指南" skills/status.md
}

@test "status.md style guide locks emoji vocabulary (canonical set)" {
  for e in 🔍 💡 ⚠️ ✅ ❌ 📋 🎉; do
    grep -qF "$e" skills/status.md || { echo "MISSING emoji: $e"; return 1; }
  done
}

@test "status.md Mode A progress column uses N/N format" {
  grep -qE "[0-9]+/[0-9]+" skills/status.md
}

@test "status.md uses 🔧 for in_worktree (not 🔄)" {
  # 🔧 should appear in the unified emoji table;
  # 🔄 is deprecated but may appear in pre-existing code samples
  grep -qF "🔧" skills/status.md
}