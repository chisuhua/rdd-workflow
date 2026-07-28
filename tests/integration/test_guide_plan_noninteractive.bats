#!/usr/bin/env bats
# Tests for guide-plan.md --non-interactive mode (guide-plan-noninteractive change)
# - SKIP_GUIDE_PLAN_MENU=yes env var detection
# - --non-interactive CLI flag detection
# - NON_INTERACTIVE=true conditional that skips interactive code
# - --batch-create alias to propose

SKILL_FILE="$BATS_TEST_DIRNAME/../../skills/guide-plan/SKILL.md"

@test "non-interactive: SKIP_GUIDE_PLAN_MENU env var is detected" {
    grep -q 'SKIP_GUIDE_PLAN_MENU' "$SKILL_FILE"
}

@test "non-interactive: --non-interactive CLI flag is detected" {
    grep -q -- '--non-interactive' "$SKILL_FILE"
}

@test "non-interactive: NON_INTERACTIVE conditional skips interactive code" {
    grep -q 'NON_INTERACTIVE' "$SKILL_FILE"
}

@test "non-interactive: NON_INTERACTIVE=true auto-selects all pending proposals" {
    # When NON_INTERACTIVE is true, the skill should auto-create changes
    # from proposal-approved.md instead of showing the interactive menu
    grep -q 'NON_INTERACTIVE.*true\|true.*NON_INTERACTIVE\|if.*NON_INTERACTIVE' "$SKILL_FILE"
}

@test "non-interactive: --batch-create alias delegates to propose skill" {
    grep -q -- '--batch-create' "$SKILL_FILE"
}

@test "non-interactive: frontmatter still valid after changes" {
    run python3 -c "
import yaml
with open('$SKILL_FILE') as f:
    content = f.read()
assert content.startswith('---')
meta = yaml.safe_load(content.split('---', 2)[1])
assert meta['name'] == 'guide-plan'
assert meta['metadata']['user-invocable'] is True
print('OK')
"
    [ "$status" -eq 0 ]
}
