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
