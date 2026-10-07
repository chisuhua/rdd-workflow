#!/usr/bin/env bats
# tests/integration/test_rdd_doctor_skills_md_sync.bats
#
# Doc-sync regression test: lock the invariant that
#   skills/rdd-doctor/SKILL.md "N 类检查概览" table
# has exactly the same category set as
#   skills/rdd-doctor/scripts/doctor_main.py::_CHECKERS
#
# Per fix-x-rdd-doctor-hardcoded-paths-and-skills-md-drift:
#   Drift history — SKILL.md listed 8 categories (state / plan-tdd /
#   roadmap-meta / proposal-table / tasks-checkbox / migration-residue /
#   gitignore / arch-audit) while _CHECKERS has 18. The orphan 10
#   (proposal-section / roadmap-refs / roadmap-feature / docs-consistency /
#   ai-context-bootstrap / bypass-audit / improvement-frontmatter-consistency
#   / objective-lifecycle / objective-structure / orphan-gates) were
#   invisible to users reading the docs.
#
# This test fails if:
#   (a) SKILL.md table is missing rows,
#   (b) any new _CHECKERS category is undocumented,
#   (c) SKILL.md mentions a "phantom" category that's no longer wired.
#
# Pre-patch fail check (AC-8 of the proposal):
#   Pre-patch SKILL.md has 8 rows + uses "5 类" / "cat-5" wording → test
#   should FAIL on the pre-patch SKILL.md (which the proposal fixed).

load '../test_helper'

setup() {
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    SKILL_MD="$PROJECT_ROOT/skills/rdd-doctor/SKILL.md"
    DOCTOR_MAIN="$PROJECT_ROOT/skills/rdd-doctor/scripts/doctor_main.py"
}

# -----------------------------------------------------------------------------
# Test 1: SKILL.md "N 类检查概览" heading is the right number (currently 18)
# -----------------------------------------------------------------------------
@test "doctor SKILL.md: heading says '18 类检查概览'" {
    run grep -nE "^[#]+ 18 类检查概览" "$SKILL_MD"
    [ "$status" -eq 0 ]
}

# -----------------------------------------------------------------------------
# Test 2: SKILL.md 5-类 references are gone
# -----------------------------------------------------------------------------
@test "doctor SKILL.md: no leftover '5 类' or 'cat-5' wording" {
    run grep -nE "5 类|cat-5" "$SKILL_MD"
    if [ "$status" -eq 0 ]; then
        echo "SKILL.md still references 5-class model:"
        echo "$output" | head -5
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Test 3: SKILL.md table has exactly 18 data rows (| `category` | ...)
# -----------------------------------------------------------------------------
@test "doctor SKILL.md: 检查概览 table has exactly 18 category rows" {
    # Extract the section between "## N 类检查概览" and the next "## "
    table_rows=$(sed -n '/^## [0-9]\+ 类检查概览/,/^## /p' "$SKILL_MD" \
        | grep -cE '^\| `\w+(-\w+)*` \|')
    [ "$table_rows" -eq 18 ]
}

# -----------------------------------------------------------------------------
# Test 4: every category in SKILL.md table is wired in _CHECKERS
# -----------------------------------------------------------------------------
@test "doctor SKILL.md: every documented category is in _CHECKERS" {
    # Extract category names from SKILL.md table cells
    md_categories=$(sed -n '/^## [0-9]\+ 类检查概览/,/^## /p' "$SKILL_MD" \
        | grep -oE '^\| `\w+(-\w+)*` \|' \
        | sed -E 's/^\| `(\w+(-\w+)*)` \|$/\1/' \
        | sort -u)

    # Extract _CHECKERS keys via ast-grep-free python
    py_categories=$(python3 -c "
import re, sys
text = open('$DOCTOR_MAIN').read()
m = re.search(r'_CHECKERS\s*=\s*\{(.+?)\n\}', text, re.DOTALL)
if not m:
    sys.exit(2)
block = m.group(1)
# Matches patterns like:  \"state\": state_schema_check.run,
keys = re.findall(r'\"([\w-]+)\":\s*\w+_check\.run', block)
print('\n'.join(sorted(set(keys))))
")

    # Compare sets: documented ⊆ wired
    diff_out=$(comm -23 <(echo "$md_categories") <(echo "$py_categories"))
    if [ -n "$diff_out" ]; then
        echo "Documented categories NOT wired in _CHECKERS:"
        echo "$diff_out"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Test 5: every category wired in _CHECKERS is documented in SKILL.md
# -----------------------------------------------------------------------------
@test "doctor SKILL.md: every wired _CHECKERS category is documented" {
    md_categories=$(sed -n '/^## [0-9]\+ 类检查概览/,/^## /p' "$SKILL_MD" \
        | grep -oE '^\| `\w+(-\w+)*` \|' \
        | sed -E 's/^\| `(\w+(-\w+)*)` \|$/\1/' \
        | sort -u)

    py_categories=$(python3 -c "
import re, sys
text = open('$DOCTOR_MAIN').read()
m = re.search(r'_CHECKERS\s*=\s*\{(.+?)\n\}', text, re.DOTALL)
if not m:
    sys.exit(2)
block = m.group(1)
keys = re.findall(r'\"([\w-]+)\":\s*\w+_check\.run', block)
print('\n'.join(sorted(set(keys))))
")

    # Compare sets: wired ⊆ documented (no orphan _CHECKERS keys)
    diff_out=$(comm -13 <(echo "$md_categories") <(echo "$py_categories"))
    if [ -n "$diff_out" ]; then
        echo "_CHECKERS categories NOT documented in SKILL.md:"
        echo "$diff_out"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Test 6: SKILL.md has a `.rddf/roadmap/` diagnostic quick-reference section
#         (regression-tested against the proposal's "user asks about .rddf/roadmap/"
#          original trigger; prevents future drift hiding roadmap docs)
# -----------------------------------------------------------------------------
@test "doctor SKILL.md: '.rddf/roadmap/' diagnostic quick-reference section exists" {
    # The section spans from heading line through its code-fenced block
    run grep -nA10 "诊断速查" "$SKILL_MD"
    [ "$status" -eq 0 ]
    # Must mention at least roadmap-feature / roadmap-refs / objective-*
    [[ "$output" == *"roadmap-feature"* ]]
    [[ "$output" == *"roadmap-refs"* ]]
    [[ "$output" == *"objective-lifecycle"* ]]
}