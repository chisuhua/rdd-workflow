#!/usr/bin/env bats
# tests/integration/test_legacy_guide_arch_shim.bats
# Stage 3 Change 1: backward-compat shim contract.
# Verifies skill_use("guide-arch") forwards to rdd-arch.

load ../test_helper

@test "legacy guide-arch shim: skill file exists at skills/guide-arch/SKILL.md" {
    [ -f "$REPO_ROOT/skills/guide-arch/SKILL.md" ]
}

@test "legacy guide-arch shim: frontmatter name is guide-arch" {
    run python3 -c "
import yaml
with open('$REPO_ROOT/skills/guide-arch/SKILL.md') as f:
    parts = f.read().split('---', 2)
print(yaml.safe_load(parts[1])['name'])
"
    [ "$status" -eq 0 ]
    [[ "$output" == "guide-arch" ]]
}

@test "legacy guide-arch shim: metadata.deprecated is set" {
    run python3 -c "
import yaml
with open('$REPO_ROOT/skills/guide-arch/SKILL.md') as f:
    parts = f.read().split('---', 2)
print(yaml.safe_load(parts[1])['metadata']['deprecated'])
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "rdd-arch" ]]
}

@test "legacy guide-arch Python import resolves to skills/rdd-arch/scripts" {
    cd "$REPO_ROOT"
    run python3 -c "
import skills.guide_arch.scripts as legacy
import skills.rdd_arch.scripts as canonical
assert legacy.__path__ == canonical.__path__, f'paths diverge: {legacy.__path__} vs {canonical.__path__}'
print('OK')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "OK" ]]
}