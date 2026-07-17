#!/usr/bin/env bats
# Tests for guide-ship.md review Phase 2.5 option 2 auto-deps (v2.0.1)
# - 文件冲突检测 → 自动增量 re-deps
# - 无冲突 → safe deferred

@test "review option 2: 包含自动增量 deps 逻辑" {
    grep -q "自动增量 deps" "$BATS_TEST_DIRNAME/../../skills/guide-ship/SKILL.md" || return 1
    return 0
}

@test "review option 2: 使用 iteration.list_active 获取活跃 change" {
    grep -q "it.list_active" "$BATS_TEST_DIRNAME/../../skills/guide-ship/SKILL.md" || return 1
    return 0
}

@test "review option 2: 冲突时追加到 .deps-candidates.json" {
    grep -q ".deps-candidates.json" "$BATS_TEST_DIRNAME/../../skills/guide-ship/SKILL.md" || return 1
    return 0
}

@test "review option 2: 冲突时调用 skill_use deps" {
    grep -q 'skill_use("deps")' "$BATS_TEST_DIRNAME/../../skills/guide-ship/SKILL.md" || return 1
    return 0
}

@test "review option 2: 无冲突时 safe deferred" {
    grep -q "安全 deferred" "$BATS_TEST_DIRNAME/../../skills/guide-ship/SKILL.md" || return 1
    grep -q "无文件冲突" "$BATS_TEST_DIRNAME/../../skills/guide-ship/SKILL.md" || return 1
    return 0
}

@test "review option 2: 提取 DEBT_KEYWORD 用于冲突检测" {
    grep -q "DEBT_KEYWORD" "$BATS_TEST_DIRNAME/../../skills/guide-ship/SKILL.md" || return 1
    return 0
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