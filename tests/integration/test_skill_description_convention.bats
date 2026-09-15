#!/usr/bin/env bats
# tests/integration/test_skill_description_convention.bats
# Enforce ADR-0051 skill description convention: ≤ 200 tokens / no anti-trigger / references role.boundaries

load test_helper

@test "every SKILL.md description is under 200 tokens" {
    local skill_count=0
    local fail_count=0
    for f in skills/*/SKILL.md skills/INSTALL.md; do
        [ -f "$f" ] || continue
        skill_count=$((skill_count + 1))
        local desc_tokens
        # awk: capture description block content only (YAML block scalar ends when indentation drops to 0)
        desc_tokens=$(awk '/^description: \|/{capture=1;next} capture && /^[^ ]/{exit} capture' "$f" | wc -w)
        if [ "$desc_tokens" -gt 200 ]; then
            echo "FAIL: $f has $desc_tokens tokens (>200)"
            fail_count=$((fail_count + 1))
        fi
    done
    [ "$fail_count" -eq 0 ]
    [ "$skill_count" -eq 27 ]
}

@test "no SKILL.md description contains anti-trigger phrasing" {
    local hits
    hits=$(grep -rnE '\*\*DO NOT use\*\*|\*\*Prefer .* instead\*\*|\*\*Legacy entry\*\*' skills/*/SKILL.md skills/INSTALL.md 2>/dev/null | wc -l)
    [ "$hits" -eq 0 ]
}

@test "every SKILL.md description references role.boundaries" {
    local missing=0
    for f in skills/*/SKILL.md skills/INSTALL.md; do
        [ -f "$f" ] || continue
        if ! grep -qE 'role\.boundaries\.owns|see role\.boundaries|Boundary ownership' "$f"; then
            echo "MISSING: $f does not reference role.boundaries"
            missing=$((missing + 1))
        fi
    done
    [ "$missing" -eq 0 ]
}
