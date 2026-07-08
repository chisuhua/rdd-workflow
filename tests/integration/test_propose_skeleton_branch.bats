#!/usr/bin/env bats
# Tests for propose.md name-pattern skeleton branching (v2.0.1)
# - debt/fix-/prefix- 前缀→自动 skeleton 模式
# - proposal-suggestions.md status 更新

@test "phase 4: 包含 name-pattern skeleton 分流逻辑" {
    grep -qi "skeleton.*branching" "$BATS_TEST_DIRNAME/../../skills/propose.md" || return 1
    grep -q "debt|fix-|prefix-" "$BATS_TEST_DIRNAME/../../skills/propose.md" || return 1
    return 0
}

@test "phase 4: name-pattern 只触发于 SKELETON_MODE=false 时" {
    grep -qi "SKELETON_MODE.*false" "$BATS_TEST_DIRNAME/../../skills/propose.md" || return 1
    return 0
}

@test "phase 4: 匹配后设置 SKELETON_MODE=true" {
    grep -qi "SKELETON_MODE.*true" "$BATS_TEST_DIRNAME/../../skills/propose.md" || return 1
    return 0
}

@test "skeleton branch: 更新 proposal-suggestions.md status 为 skeleton" {
    grep -A 3 "待创建.*→.*skeleton" "$BATS_TEST_DIRNAME/../../skills/propose.md" || return 1
    return 0
}

@test "skeleton branch: proposal-suggestions 更新使用 json.load" {
    grep -q "proposal-suggestions.md" "$BATS_TEST_DIRNAME/../../skills/propose.md" || return 1
    grep -q 'json.load\|json.dump' "$BATS_TEST_DIRNAME/../../skills/propose.md" || return 1
    return 0
}

@test "frontmatter: propose.md 仍合法" {
    python3 -c "
import yaml
with open('skills/propose.md') as f:
    content = f.read()
assert content.startswith('---')
meta = yaml.safe_load(content.split('---', 2)[1])
assert meta['name'] == 'propose'
assert meta['metadata']['version'] is not None
print('OK')
"
}