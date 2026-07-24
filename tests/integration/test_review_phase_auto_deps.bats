#!/usr/bin/env bats
# Tests for guide-ship.md review Phase 2.5 option 2 auto-deps (v2.0.1)
# - 文件冲突检测 -> 自动增量 re-deps
# - 无冲突 -> safe deferred
#
# v2.0.8 update: review auto-deps logic was extracted from guide-ship.md
# inline bash into scripts/ship_review.sh (_review_create_debt_change).
# Tests now grep the script file where the logic lives, and assert the
# SKILL.md references the helper via handle_review_action.

# Shared path to the extracted review helper script
REVIEW_SCRIPT="$BATS_TEST_DIRNAME/../../skills/guide-ship/scripts/ship_review.sh"
SHIP_SKILL="$BATS_TEST_DIRNAME/../../skills/guide-ship/SKILL.md"

@test "review option 2: 包含自动增量 deps 逻辑" {
    [ -f "$REVIEW_SCRIPT" ]
    grep -q "自动增量 deps" "$REVIEW_SCRIPT"
}

@test "review option 2: 使用 iteration.list_active 获取活跃 change" {
    [ -f "$REVIEW_SCRIPT" ]
    grep -q "it.list_active" "$REVIEW_SCRIPT"
}

@test "review option 2: 冲突时追加到 .deps-candidates.json" {
    [ -f "$REVIEW_SCRIPT" ]
    grep -q ".deps-candidates.json" "$REVIEW_SCRIPT"
}

@test "review option 2: 冲突时调用 skill_use deps" {
    [ -f "$REVIEW_SCRIPT" ]
    # The script uses skill_use "deps" (bash form), not skill_use("deps")
    grep -q 'skill_use "deps"' "$REVIEW_SCRIPT"
}

@test "review option 2: 无冲突时 safe deferred" {
    [ -f "$REVIEW_SCRIPT" ]
    grep -q "安全 deferred" "$REVIEW_SCRIPT"
    grep -q "无文件冲突" "$REVIEW_SCRIPT"
}

@test "review option 2: 提取 debt_keyword 用于冲突检测" {
    [ -f "$REVIEW_SCRIPT" ]
    # The variable is lowercase debt_keyword in the script (not DEBT_KEYWORD)
    grep -q "debt_keyword" "$REVIEW_SCRIPT"
}

@test "review option 2: guide-ship.md references ship_review.sh helper" {
    # v2.0.8: SKILL.md is a thin orchestrator that sources ship_review.sh
    [ -f "$SHIP_SKILL" ]
    grep -q "ship_review.sh" "$SHIP_SKILL"
    grep -q "handle_review_action" "$SHIP_SKILL"
}

@test "frontmatter: guide-ship.md 仍合法" {
    python3 -c "
import yaml
with open('skills/guide-ship/SKILL.md') as f:
    content = f.read()
assert content.startswith('---')
meta = yaml.safe_load(content.split('---', 2)[1])
assert meta['name'] == 'guide-ship'
assert meta['metadata']['user-invocable'] is True
print('OK')
"
}
