#!/usr/bin/env bats
#
# test_v4_doc_drift_contracts.bats
#
# Doc-contract tests locking the v4 4-stage architecture + rdd-quick bypass
# representation in user-facing and architectural documentation.
#
# Origin: per `openspec/changes/fix-doc-drift-v4-architecture/proposal.md`
# (audit 2026-09-09). Each test below corresponds to one AC or one Scenar# io
# in `openspec/changes/fix-doc-drift-v4-architecture/specs/doc-architecture-v4-sync/spec.md`.
#
# Pre-patch fail check (AC-6): all 10 tests should FAIL on the pre-patch tree
# (run after `git stash` of the doc edits) and PASS on the post-patch tree.
# This locks the test as a meaningful regression detector rather than a
# "passes on both sides" no-op.

setup() {
  REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  cd "$REPO_ROOT"
}

# -----------------------------------------------------------------------------
# Test 1: README.md does not contain "五阶段" (stale v3 wording)
# Corresponds to: AC-1, AC-2
# -----------------------------------------------------------------------------
@test "doc_drift_v4: README.md does not contain '五阶段' (stale v3 wording)" {
  run grep -nE "五阶段" README.md
  if [ "$status" -eq 0 ]; then
    echo "README.md still references '五阶段':"
    echo "$output" | head -5
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 2: README.md does not contain "five-phase" (English stale wording)
# Corresponds to: AC-2
# -----------------------------------------------------------------------------
@test "doc_drift_v4: README.md does not contain 'five-phase' or '5 phases'" {
  run grep -niE "five-phase|five phase|5 phases" README.md
  if [ "$status" -eq 0 ]; then
    echo "README.md still references 5-phase model:"
    echo "$output" | head -5
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 3: README.md directory tree includes rdd-planner and rdd-quick
# Corresponds to: AC-1 (directory tree)
# -----------------------------------------------------------------------------
@test "doc_drift_v4: README.md directory tree includes rdd-planner and rdd-quick" {
  # Extract the directory tree section using sed (awk range has subtle issues
  # when start pattern matches end pattern's prefix).
  tree_section=$(sed -n '/^## 目录结构/,/^## /p' README.md | head -n -1)
  if ! echo "$tree_section" | grep -q "rdd-planner"; then
    echo "README.md directory tree missing rdd-planner"
    return 1
  fi
  if ! echo "$tree_section" | grep -q "rdd-quick"; then
    echo "README.md directory tree missing rdd-quick"
    return 1
  fi
  # Ensure rdd-builder appears at most once in directory tree (was 3x in pre-patch)
  builder_count=$(echo "$tree_section" | grep -c "rdd-builder/SKILL.md")
  if [ "$builder_count" -gt 1 ]; then
    echo "README.md directory tree has $builder_count rdd-builder/SKILL.md entries (expected at most 1)"
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 4: docs/architecture/overview.md does not contain "five-phase" or "5 phases"
# Corresponds to: AC-2, AC-5
# -----------------------------------------------------------------------------
@test "doc_drift_v4: docs/architecture/overview.md does not contain 'five-phase' or '5 phases'" {
  run grep -niE "five-phase|five phase|5 phases" docs/architecture/overview.md
  if [ "$status" -eq 0 ]; then
    echo "docs/architecture/overview.md still references 5-phase model:"
    echo "$output" | head -5
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 5: docs/architecture/overview.md L123 region does not contain inverted rule
# Corresponds to: AC-5
# The inverted rule said "four phases is stale" but v4 IS four stages.
# -----------------------------------------------------------------------------
@test "doc_drift_v4: docs/architecture/overview.md L123 inverted rule is corrected" {
  # The inverted rule appears in the "Why Five Phases" section's last paragraph.
  # After the fix, the heading should be "Why Four Stages" and the rule text
  # should mention "four stages" as the current model, not as "stale".
  if grep -nE "any doc that still says .three phases. or .four phases. is stale" docs/architecture/overview.md > /dev/null 2>&1; then
    echo "docs/architecture/overview.md still has the inverted rule 'four phases is stale':"
    grep -n "four phases.*stale\|stale.*four phases" docs/architecture/overview.md
    return 1
  fi
  # Also check for "Why Five Phases" heading (should be renamed)
  if grep -nE "^## Why Five Phases" docs/architecture/overview.md > /dev/null 2>&1; then
    echo "docs/architecture/overview.md still has 'Why Five Phases' heading (should be 'Why Four Stages')"
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 6: docs/architecture/workflow-phases.md does not reference guide-* skill names
# Corresponds to: AC-3, AC-10
# -----------------------------------------------------------------------------
@test "doc_drift_v4: docs/architecture/workflow-phases.md does not reference guide-* skill names" {
  # Match both `Entry skill:` and `**Entry skill**:` (markdown bold variants).
  # Pre-patch workflow-phases.md used `**Entry skill**: \`guide-*\`` (bold) which
  # the previous regex missed — fixed 2026-09-09 per Oracle review.
  for skill in guide-arch guide-design guide-plan guide-ship; do
    if grep -nE "\*\*?Entry skill\*\*?: \`$skill\`|skill_use.*\"$skill\"" docs/architecture/workflow-phases.md > /dev/null 2>&1; then
      echo "docs/architecture/workflow-phases.md still references $skill"
      grep -n "$skill" docs/architecture/workflow-phases.md | head -3
      return 1
    fi
  done
}

# -----------------------------------------------------------------------------
# Test 7: skills/rdd-arch/SKILL.md L34 does not contain self-reference bug
# Corresponds to: AC-4
# -----------------------------------------------------------------------------
@test "doc_drift_v4: skills/rdd-arch/SKILL.md L34 does not contain self-reference bug" {
  if grep -nE "从 .rdd-arch. 重命名为 .rdd-arch." skills/rdd-arch/SKILL.md > /dev/null 2>&1; then
    echo "skills/rdd-arch/SKILL.md L34 still has self-reference bug:"
    grep -n "从 .rdd-arch. 重命名为" skills/rdd-arch/SKILL.md
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 8: skills/rdd-arch/SKILL.md does not contain "五阶段"
# Corresponds to: AC-4
# -----------------------------------------------------------------------------
@test "doc_drift_v4: skills/rdd-arch/SKILL.md does not contain '五阶段'" {
  run grep -nE "五阶段" skills/rdd-arch/SKILL.md
  if [ "$status" -eq 0 ]; then
    echo "skills/rdd-arch/SKILL.md still references '五阶段':"
    echo "$output" | head -5
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 9: skills/ has 5 rdd-* stage skills and 0 guide-* stage skills
# Corresponds to: AC-8 (skills directory layout)
# -----------------------------------------------------------------------------
@test "doc_drift_v4: skills/ has 5 rdd-* stage skills and 0 guide-* stage skills" {
  # Expected rdd-* stage skills
  for skill in rdd-arch rdd-planner rdd-builder rdd-verifier rdd-quick; do
    if [ ! -d "skills/$skill" ]; then
      echo "skills/$skill directory missing"
      return 1
    fi
    if [ ! -f "skills/$skill/SKILL.md" ]; then
      echo "skills/$skill/SKILL.md missing"
      return 1
    fi
  done
  # Deprecated guide-* stage skills (excludes guide/ which is the standalone recommender)
  for skill in guide-arch guide-design guide-plan guide-ship guide-spec; do
    if [ -d "skills/$skill" ]; then
      echo "skills/$skill directory exists (should have been removed by Wave 3 per ADR-0044)"
      return 1
    fi
  done
}

# -----------------------------------------------------------------------------
# Test 10: docs/architecture/workflow-phases.md references canonical verifier state path
# Corresponds to: AC-3
# Canonical path per rdd-verifier/SKILL.md is .rddf/state/verifier/<change>.json
# -----------------------------------------------------------------------------
@test "doc_drift_v4: docs/architecture/workflow-phases.md uses canonical verifier state path" {
  # The deprecated path was .rdd/state/.rdd-verifier-state.json
  if grep -nE "\.rdd/state/\.rdd-verifier-state\.json" docs/architecture/workflow-phases.md > /dev/null 2>&1; then
    echo "docs/architecture/workflow-phases.md still references deprecated .rdd-verifier-state.json path:"
    grep -n "\.rdd-verifier-state" docs/architecture/workflow-phases.md
    return 1
  fi
  # The canonical path should be referenced
  if ! grep -nE "\.rddf/state/verifier/.*<change>" docs/architecture/workflow-phases.md > /dev/null 2>&1; then
    echo "docs/architecture/workflow-phases.md does not reference canonical .rddf/state/verifier/<change>.json path"
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Bonus Test 11: ac-verifier is not cited as a sub-skill in workflow-phases.md
# Corresponds to: AC-3 (deprecation per ADR-0045)
# -----------------------------------------------------------------------------
@test "doc_drift_v4: docs/architecture/workflow-phases.md does not reference deprecated ac-verifier as a sub-skill" {
  # Match `**Sub-skills**: <content>` lines that include ac-verifier as a LIVE
  # sub-skill (not in a "deprecated/gone" historical note).
  # Pre-patch had `**Sub-skills**: \`ac-verifier\`` (live reference); the post-patch
  # prose mention in a "The deprecated ac-verifier" sentence is allowed.
  # Use `|| true` to prevent bats `set -e` from mis-reporting empty grep as failure.
  hits=$(grep -nE '\*\*Sub-skills\*\*:' docs/architecture/workflow-phases.md | grep 'ac-verifier' | { grep -v 'deprecated\|gone\|removed' || true; })
  if [ -n "$hits" ]; then
    echo "docs/architecture/workflow-phases.md still cites ac-verifier as a live sub-skill:"
    echo "$hits"
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Bonus Test 12: AC-10 enforcement — no guide-* skill references in
# docs/architecture/ files modified by this change.
# Corresponds to: AC-10 (scoped to this change's file set)
# Oracle review 2026-09-09: previously the test only checked workflow-phases.md
# in isolation. This test extends to the other 2 docs/architecture/ files
# this change edits (overview.md, README.md). The remaining docs/architecture/
# files (extension-points.md, improvement-check-mechanisms.md, etc.) are
# deferred to the follow-up change `docs-v4-sync-followup-v2`.
# -----------------------------------------------------------------------------
@test "doc_drift_v4: docs/architecture/ files in this change's scope have no live guide-* skill references (AC-10 scoped)" {
  for file in docs/architecture/overview.md docs/architecture/workflow-phases.md docs/architecture/README.md; do
    [ -f "$file" ] || continue
    hits=$(grep -nE "skill_use\(\"(guide-arch|guide-design|guide-plan|guide-ship|guide-spec)\"\)|Entry skill\*\*?: \`(guide-arch|guide-design|guide-plan|guide-ship)\`|skills/(guide-arch|guide-design|guide-plan|guide-ship|guide-spec)/" "$file" 2>/dev/null || true)
    if [ -n "$hits" ]; then
      echo "AC-10 violation in $file:"
      echo "$hits" | head -5
      return 1
    fi
  done
}

# -----------------------------------------------------------------------------
# Bonus Test 13: AC-11 enforcement — no live guide-* skill invocations
# in README.md + USAGE.md (both modified by this change).
# Corresponds to: AC-11
# Oracle review 2026-09-09: USAGE.md L328/708/709/724/765 had 5 active
# `skill_use("guide-ship")` / `skill_use("guide-plan")` / `skill_use("execute")`
# invocations that would
# fail for users reading the docs. This test enforces the invariant.
# 2026-11-20 (fix-status-retirement-residue): `status` joined the banned
# list — that skill was retired on the same day (archived to
# docs/legacy/skills/status/).
# 2026-11-20 (fix-v4-doc-drift-live-invocations): bare `guide` joined the
# banned list — the recommender skill was archived on 2026-11-19 (ADR-0063);
# its capability now lives in the `rddf guide` CLI.
# -----------------------------------------------------------------------------
@test "doc_drift_v4: README.md + USAGE.md have no live guide*/execute/status skill invocations (AC-11)" {
  # Look for skill_use("guide-*") invocations inside code blocks (live commands).
  # Use perl with multi-line mode to handle markdown ``` blocks.
  for file in README.md USAGE.md; do
    hits=$(perl -0777 -ne 'while (/```.*?\n(.*?)\n```/gs) { my $block = $1; while ($block =~ /\bskill_use\(["\x27](guide-arch|guide-design|guide-plan|guide-ship|guide-spec|execute|status|guide)["\x27]\)/g) { print "AC-11 violation: live skill_use(\"$1\") in code block of $ARGV\n"; } }' "$file" 2>/dev/null)
    if [ -n "$hits" ]; then
      echo "$hits"
      return 1
    fi
  done
}

# -----------------------------------------------------------------------------
# Bonus Test 14: AC-3 extended — no live guide-* skill references in ANY
# docs/architecture/*.md file (extended scope per follow-up change).
# Corresponds to: AC-3 of docs-v4-sync-followup-v2.
# Oracle review 2026-09-09: extends Test 12 to all docs/architecture/ files
# (parent change only checked 3 files; this catches drift in unchanged files).
# Excludes rdd-arch-rdd-planner-integration.md shim-doc mentions via grep -v.
# 2026-11-20 (arch-docs-drift-sync): the exemption list now also covers the
# newer wording 「已移除 / retired / hard removal / removed」 — a compatibility
# matrix row saying "no compat shim, removed per ADR-0044" is a lineage note,
# not a live reference. Exemptions apply to prose and tables ONLY: fenced code
# blocks are executable examples, so the next test hard-zeroes them.
# -----------------------------------------------------------------------------
@test "doc_drift_v4: ALL docs/architecture/*.md have no live guide-* skill references (AC-3 follow-up)" {
  hits=$(grep -rnE 'skill_use\(\"(guide-arch|guide-design|guide-plan|guide-ship|guide-spec)\"\)|\*\*?Entry skill\*\*?: \`(guide-arch|guide-design|guide-plan|guide-ship)\`|skills/(guide-arch|guide-design|guide-plan|guide-ship|guide-spec)/' docs/architecture/ 2>/dev/null | grep -vE 'shim|DEPRECATED|deprecated|compat|已移除|已废弃|retired|hard removal|removed' || true)
  if [ -n "$hits" ]; then
    echo "AC-3 follow-up violation (live guide-* in docs/architecture/):"
    echo "$hits" | head -10
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Test 14b: fenced code blocks in docs/architecture/*.md must not invoke a
# retired skill. A code block is an executable example — if it says
# `skill_use("guide-*")`, a reader will copy it and fail. Lineage notes never
# live inside code fences, so this test tolerates zero occurrences (the
# prose/table exemption above does not apply here).
# -----------------------------------------------------------------------------
@test "doc_drift_v4: docs/architecture/*.md fenced code blocks invoke no retired skill" {
  hits=$(perl -0777 -ne 'while (/```.*?\n(.*?)\n```/gs) { my $b = $1; while ($b =~ /\bskill_use\(["\x27](guide[a-z-]*)["\x27]/g) { print "$ARGV: skill_use(\"$1\")\n" } }' docs/architecture/*.md 2>/dev/null || true)
  if [ -n "$hits" ]; then
    echo "AC-3b violation (retired skill invoked in a fenced code block):"
    echo "$hits" | head -10
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Bonus Test 15: AC-7 cross-user-facing — no live skill_use("guide-*")
# invocations in ONBOARDING.md (new user entry point).
# Corresponds to: AC-7 of docs-v4-sync-followup-v2.
# Oracle review 2026-09-09: ONBOARDING.md L194 had live
# `skill_use("guide-plan")` that would 404 new users. This test enforces.
# -----------------------------------------------------------------------------
@test "doc_drift_v4: ONBOARDING.md has no live guide-* skill invocations (AC-7 follow-up)" {
  hits=$(perl -0777 -ne 'while (/```.*?\n(.*?)\n```/gs) { my $block = $1; while ($block =~ /\bskill_use\(["\x27](guide-arch|guide-design|guide-plan|guide-ship|guide-spec)["\x27]\)/g) { print "AC-7 follow-up violation: live skill_use(\"$1\") in ONBOARDING.md code block\n"; } }' docs/ONBOARDING.md 2>/dev/null)
  if [ -n "$hits" ]; then
    echo "$hits"
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Bonus Test 16: AC-6 — no guide-* skill name references in skills/INSTALL.md.
# Corresponds to: AC-6 of docs-v4-sync-followup-v2.
# Oracle review 2026-09-09: INSTALL.md L34/L186 had `guide-plan`/`guide-ship`
# references that misdirected install-step documentation.
# -----------------------------------------------------------------------------
@test "doc_drift_v4: skills/INSTALL.md has no guide-* skill name references (AC-6 follow-up)" {
  hits=$(grep -nE 'guide-design|guide-plan|guide-ship|guide-arch|guide-spec' skills/INSTALL.md 2>/dev/null || true)
  if [ -n "$hits" ]; then
    echo "AC-6 follow-up violation in skills/INSTALL.md:"
    echo "$hits" | head -5
    return 1
  fi
}

# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# fix-doc-drift-followup-3 Bonus Test 18: AC-2 — 7 sub-skill SKILL.md files
# have no active skill_use("guide-*") invocations.
# Corresponds to: AC-2 of fix-doc-drift-followup-3.
# -----------------------------------------------------------------------------
@test "doc_drift_v4: 7 sub-skill SKILL.md files have no live skill_use(\"guide-*\") invocations (AC-2 follow-up)" {
  for f in skills/deps/SKILL.md \
           skills/add-improve/SKILL.md skills/feature/SKILL.md skills/sync-hub/SKILL.md \
           skills/rddf-session/SKILL.md skills/openspec-gate/SKILL.md skills/rdd-env-check/SKILL.md; do
    hits=$(grep -nE 'skill_use\("(guide-arch|guide-design|guide-plan|guide-ship|guide-spec)"\)' "$f" 2>/dev/null || true)
    if [ -n "$hits" ]; then
      echo "AC-2 follow-up violation in $f:"
      echo "$hits" | head -5
      return 1
    fi
  done
}

# -----------------------------------------------------------------------------
# fix-doc-drift-followup-3 Bonus Test 19: AC-3 — docs/migration/v3-to-v4.md
# exists with ≥ 80 lines and all required H2 sections.
# Corresponds to: AC-3 of fix-doc-drift-followup-3.
# -----------------------------------------------------------------------------
@test "doc_drift_v4: docs/migration/v3-to-v4.md exists, ≥80 lines, has 7 required sections (AC-3 follow-up)" {
  test -f docs/migration/v3-to-v4.md || { echo "AC-3 follow-up violation: docs/migration/v3-to-v4.md missing"; return 1; }
  lines=$(wc -l < docs/migration/v3-to-v4.md)
  [ "$lines" -ge 80 ] || { echo "AC-3 follow-up violation: docs/migration/v3-to-v4.md has $lines lines, expected ≥80"; return 1; }
  for section in "## 阶段数变化" "## Skill 重命名映射" "## Removed skills" "## 工作流变更" "## 升级步骤" "## FAQ" "## 参考"; do
    grep -qF "$section" docs/migration/v3-to-v4.md || { echo "AC-3 follow-up violation: section missing: $section"; return 1; }
  done
}

# -----------------------------------------------------------------------------
# fix-doc-drift-followup-3 Bonus Test 20: AC-4 — README.md L13-19 npm install
# section has no v1.x or v2.0-beta; labels v4.0+ as latest stable.
# Corresponds to: AC-4 of fix-doc-drift-followup-3.
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# fix-spec-v3-naming-sync: 活规范归属断言
#
# 活规范 = 约束**当前** SKILL.md frontmatter 的能力 spec。历史 change 的 spec 快照里
# 的旧表述是**当时正确**的记录，不归本守卫管（否则等于要求重写 47 份历史快照）。
#
# 本守卫与 doctor 的 v4-residue 守卫**不抢判据**：前者查**归属**，后者查**豁免标注**。
# 新增活规范时在此追加；历史快照不追加。
# -----------------------------------------------------------------------------
ACTIVE_ROLE_SPECS=(
  "openspec/specs/skill-role-model/spec.md"
)

@test "doc_drift_v4: 活规范的 rdd-arch owns 断言与 SKILL.md 逐项一致，且不含 roadmap" {
  for spec in "${ACTIVE_ROLE_SPECS[@]}"; do
    [ -f "$spec" ] || { echo "活规范清单指向的文件不存在: $spec"; return 1; }

    # 负向 1：不得把 roadmap 归给 rdd-arch（Scenario 标题也算）
    if grep -nE "owns ADR \+ roadmap" "$spec" >/dev/null 2>&1; then
      echo "$spec 仍把 roadmap 归给 rdd-arch 的 owns："
      grep -nE "owns ADR \+ roadmap" "$spec" | head -3
      return 1
    fi

    # 负向 2：owns 断言行不得含 roadmap
    then_line=$(grep -n "THEN it contains" "$spec" | head -1)
    [ -n "$then_line" ] || { echo "$spec 找不到 rdd-arch 的 owns 断言行（THEN it contains ...）"; return 1; }
    case "$then_line" in
      *roadmap*) echo "$spec 的 owns 断言仍含 roadmap:"; echo "$then_line"; return 1 ;;
    esac

    # 正向：owns 断言的条目必须与 skills/rdd-arch/SKILL.md 的 owns: 逐项一致
    mapfile -t owns_entries < <(sed -n '/^    owns:/,/^    not_owns:/p' skills/rdd-arch/SKILL.md | grep -E '^\s+- ' | sed -E 's/^\s+- "(.*)"$/\1/')
    [ "${#owns_entries[@]}" -ge 1 ] || { echo "读不到 skills/rdd-arch/SKILL.md 的 owns: 条目"; return 1; }
    for entry in "${owns_entries[@]}"; do
      case "$then_line" in
        *"$entry"*) ;;
        *) echo "$spec 的 owns 断言缺少 SKILL.md owns: 里的条目: $entry"; echo "$then_line"; return 1 ;;
      esac
    done

    # 改名历史注记必须仍带合法豁免标注（本守卫不删它，只保证它仍被放行）
    while IFS= read -r hit; do
      [ -n "$hit" ] || continue
      ln=${hit%%:*}
      next=$(sed -n "$((ln+1))p" "$spec")
      case "$next" in
        *"<!-- v4-residue:allow=rename-history -->"*) ;;
        *) echo "$spec:$ln 的改名历史注记下一行缺少 rename-history 豁免标注："; echo "$next"; return 1 ;;
      esac
    done < <(grep -nE "guide-arch|guide-design|guide-plan|guide-ship" "$spec" || true)
  done
}