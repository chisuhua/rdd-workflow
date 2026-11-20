#!/usr/bin/env bats
# tests/integration/test_v4_drift_guards.bats
#
# 2026-11-20 (fix-v4-doc-drift-live-invocations)
#
# Two guard surfaces that were uncovered before this change:
#
#   1. Non-fenced user-facing surfaces — `install.sh` (comment block),
#      `improvement-suggestions.md` (blockquote), and the Layer-0 template
#      injected by `rddf setup ai-context`.  Test 13 in
#      `test_v4_doc_drift_contracts.bats` only scans markdown *fenced* blocks
#      of README.md / USAGE.md, so these three kept live invocations of
#      retired skills without any resident guard.
#
#   2. `skills/*/SKILL.md` prose — the stage skills' own instructions carried
#      live `skill_use("guide")` / `skill_use("guide-design")` etc.  Agent
#      reads SKILL.md and follows it, so a stale call there is the most
#      damaging kind of drift.
#
# Both guards match the *call shape* only (`skill_use("name")`).  Historical
# notes such as `evolved-from: "renamed from guide-arch.md"`, `Stage 3
# (2026-09-03)`, or a migration guide's `sed -e 's/skill_use("guide-design")/…/'`
# never appear in that shape, so they are not flagged.

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"

# Retired skill names.  `guide-spec` / `guide-arch` / `guide-design` /
# `guide-plan` / `guide-ship` were removed in ADR-0044 (Wave 3 hard removal);
# `guide` was archived in ADR-0063; `execute` and `status` were archived on
# 2026-11-20.  Bare `guide` is listed last so the alternation prefers the
# longer `guide-*` names first.
BANNED='guide-arch|guide-design|guide-plan|guide-ship|guide-spec|execute|status|guide'

@test "drift_guards: non-fenced user surfaces have no live retired-skill invocations" {
  cd "$REPO_ROOT"
  local hits=""
  for file in install.sh improvement-suggestions.md _lib/templates/layer0_rdd_workflow_usage.md; do
    [ -f "$file" ] || continue
    local h
    h=$(perl -ne 'print "$ARGV:$.: $_" if /\bskill_use\(["\x27]('"$BANNED"')["\x27]\)/' "$file" 2>/dev/null)
    [ -n "$h" ] && hits="$hits$h"
  done
  if [ -n "$hits" ]; then
    echo "live retired-skill invocation(s) on a non-fenced user surface:"
    echo "$hits"
    return 1
  fi
}

@test "drift_guards: skills/*/SKILL.md have no live retired-skill invocations" {
  cd "$REPO_ROOT"
  local hits
  hits=$(perl -ne 'print "$ARGV:$.: $_" if /\bskill_use\(["\x27]('"$BANNED"')["\x27]\)/' skills/*/SKILL.md 2>/dev/null)
  if [ -n "$hits" ]; then
    echo "live retired-skill invocation(s) in SKILL.md prose:"
    echo "$hits"
    return 1
  fi
}
