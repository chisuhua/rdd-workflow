#!/usr/bin/env bats

load ../test_helper

@test "fix_doc_truth_sync: package.json skills[] includes add-improve" {
    run python3 -c "
import json
data = json.load(open('$REPO_ROOT/package.json'))
skills = data.get('skills', [])
assert 'add-improve' in skills, 'add-improve not in skills[]'
print('OK')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"OK"* ]]
}

@test "fix_doc_truth_sync: package.json skills[] includes openspec-gate" {
    run python3 -c "
import json
data = json.load(open('$REPO_ROOT/package.json'))
skills = data.get('skills', [])
assert 'openspec-gate' in skills, 'openspec-gate not in skills[]'
print('OK')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"OK"* ]]
}

@test "fix_doc_truth_sync: package.json skills[] includes rdd-workflow-brainstorm" {
    run python3 -c "
import json
data = json.load(open('$REPO_ROOT/package.json'))
skills = data.get('skills', [])
assert 'rdd-workflow-brainstorm' in skills, 'rdd-workflow-brainstorm not in skills[]'
print('OK')
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"OK"* ]]
}

@test "fix_doc_truth_sync: doc_truth_sync test #1 passes after fix" {
    # Verify the originally failing doc_contracts test #1 now passes
    run bash -c "
        cd $REPO_ROOT
        bats tests/integration/test_doc_contracts.bats 2>&1 | grep -E '^(ok|not ok) 1 '
    "
    [[ "$output" == *"ok 1"* ]]
}

@test "fix_doc_truth_sync: package.json skills[] count matches disk count" {
    # v4 stage-merge: skills/*/SKILL.md = 26 sub-skills, package.json::skills[]
    # mirrors this exact 26 (INSTALL.md is bootstrap entry, not a sub-skill).
    # Exclude skills/*.md (the lone INSTALL.md) from the count to match.
    run bash -c "
        disk=\$(ls $REPO_ROOT/skills/*/SKILL.md 2>/dev/null | wc -l)
        pkg=\$(python3 -c 'import json; print(len(json.load(open(\"$REPO_ROOT/package.json\"))[\"skills\"]))')
        echo \"disk=\$disk pkg=\$pkg\"
        [ \"\$disk\" -eq \"\$pkg\" ] || exit 1
        echo 'OK'
    "
    [[ "$output" == *"OK"* ]]
}
