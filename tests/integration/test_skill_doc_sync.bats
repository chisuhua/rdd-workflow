#!/usr/bin/env bats
# tests/integration/test_skill_doc_sync.bats
# 验证 skills/rddf-session/SKILL.md L250-252 反映 P0 fix 的 3-layer fallback

load "../test_helper"

@test "SKILL.md owner identity 反映 3-layer fallback 链" {
  # 验证 4 层 source 都明确列出 (SKILL.md 用反引号包裹变量)
  grep -qE '\$OPENCODE_SESSION_ID.*env var' skills/rddf-session/SKILL.md
  grep -q '~/.cache/rddf-session-owner' skills/rddf-session/SKILL.md
  grep -q 'proc-cmdline' skills/rddf-session/SKILL.md
  grep -q 'shell-pid' skills/rddf-session/SKILL.md
  grep -q 'cached-file' skills/rddf-session/SKILL.md
}

@test "SKILL.md 显式 DEPRECATED 旧 \$PPID stable 承诺 (含 FALSE 标记)" {
  # 旧承诺在 DEPRECATED 段中, 必须含 "FALSE" 标记才算安全废弃
  grep -q "DEPRECATED" skills/rddf-session/SKILL.md
  grep -q "is FALSE" skills/rddf-session/SKILL.md
}

@test "SKILL.md 引用 P0 修复提案" {
  grep -q "fix-rddf-session-owner-stability" skills/rddf-session/SKILL.md
}
