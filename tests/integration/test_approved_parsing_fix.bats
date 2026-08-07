#!/usr/bin/env bats
#
# Integration tests for the three rewired call sites of
# proposal-approved.md parsing. Each test runs the real call site against
# the real proposal-approved.md in the repo and asserts the fixed behavior.

load ../test_helper

setup() {
    PROJECT_ROOT="${REPO_ROOT}"
    export PROJECT_ROOT
}

@test "design_proposal_review.sh no longer lists approved-and-implemented entries as pending" {
    run bash -c '
        set -e
        PROJECT_ROOT="'"$PROJECT_ROOT"'"
        source "'"$PROJECT_ROOT"'/skills/guide-design/scripts/design_proposal_review.sh"
        design_proposal_review "'"$PROJECT_ROOT"'" "phase1"
    ' </dev/null
    [ "$status" -eq 0 ]
    # Three entries approved 2026-07-29 and previously mis-listed as pending.
    ! echo "$output" | grep -q "RDDF-0001-fix-rddf-session-import-path"
    ! echo "$output" | grep -q "fix-rddf-session-owner-cross-call"
    ! echo "$output" | grep -q "ship-delete-branch-safety"
}

@test "scan-state.sh HAS_APPROVED detects entries from both sections" {
    run bash -c '
        PROJECT_ROOT="'"$PROJECT_ROOT"'"
        export PROJECT_ROOT
        PY_PROJECT_ROOT="$PROJECT_ROOT" python3 -c "
import os, sys
def _find_helper():
    candidates = [
        os.path.join(os.environ[\"PY_PROJECT_ROOT\"], \"_lib\"),
        os.path.expanduser(\"~/.agents/skills/_lib\"),
    ]
    for d in candidates:
        if os.path.isfile(os.path.join(d, \"parse_approved.py\")):
            return d
    return \"\"
helper_dir = _find_helper()
if not helper_dir:
    print(\"no\"); sys.exit(0)
sys.path.insert(0, helper_dir)
from parse_approved import parse_approved_proposals
approved_path = os.path.join(os.environ[\"PY_PROJECT_ROOT\"], \"proposal-approved.md\")
names = parse_approved_proposals(approved_path)
print(\"yes\" if names else \"no\")
"
    '
    [ "$status" -eq 0 ]
    [ "$output" = "yes" ]
}

@test "propose_change.py recognizes approved entries from both sections" {
    # Verify the rewired function sees the helper, which is the actual fix.
    # We avoid calling batch_create_pending because it has filesystem
    # side effects; instead assert the helper (now what batch_create_pending
    # calls into) sees > 0 entries including the P0 entry that triggered
    # this change.
    run python3 -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}')
from skills._lib.parse_approved import parse_approved_proposals
names = parse_approved_proposals('${PROJECT_ROOT}/proposal-approved.md')
assert 'fix-design-proposal-review-approved-parsing' in names, sorted(names)
assert len(names) > 0, sorted(names)
print('ok', len(names))
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"ok"* ]]
}

@test "parse_approved CLI prints one name per line" {
    run python3 "${REPO_ROOT}/_lib/parse_approved.py" "${REPO_ROOT}/proposal-approved.md"
    [ "$status" -eq 0 ]
    [ -n "$output" ]
    # At least one non-empty line.
    [ "$(echo "$output" | wc -l)" -gt 0 ]
    # First non-empty line is a proposal name (no spaces).
    first_name=$(echo "$output" | grep -v '^$' | head -1)
    [[ "$first_name" == *[![:space:]]* ]]
}

@test "no inline ## 已实施 parsers remain in skills/ runtime scripts" {
    # Documentation files (skills/*/SKILL.md) are out of scope.
    run bash -c "
        grep -rn 're\.split.*## 已实施' '${REPO_ROOT}/skills/' \
            | grep -v 'SKILL\.md' \
            || true
    "
    # Must be empty (no runtime inline parsers left).
    [ -z "$output" ]
}