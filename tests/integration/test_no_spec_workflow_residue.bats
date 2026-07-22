#!/usr/bin/env bats
#
# test_no_spec_workflow_residue.bats — v3.0.0 rename regression guard

load ../test_helper

REPO_ROOT_ORIGIN="${REPO_ROOT}"

@test "no 'spec-workflow' references remain anywhere in repo (v3.0.0 rename guard)" {
    result=$(grep -rn "spec-workflow" \
        --include="*.md" --include="*.json" --include="*.yaml" --include="*.yml" \
        --include="*.py" --include="*.sh" --include="*.bash" --include="*.toml" \
        --include="*.jsonc" --include="*.cfg" --include="*.txt" \
        "$REPO_ROOT_ORIGIN/" 2>/dev/null \
        | grep -v "\.rddf/wt/" \
        | grep -v "\.git/" \
        | grep -v "__pycache__" \
        || true)

    # Intentional references (allowed):
    # - CHANGELOG.md v3.0.0 migration guide
    # - ADR v3.0.0 footnotes
    # - ADR-0023 decision document
    # - .rddf/plans/v3-rename-*.md rename plan
    intentional=$(echo "$result" \
        | grep -v "CHANGELOG\.md:" \
        | grep -v "v3\.0\.0 note" \
        | grep -v "Originally authored" \
        | grep -v "ADR-0023" \
        | grep -v "\.rddf/plans/v3-rename" \
        || true)

    [ -z "$intentional" ] || {
        echo "Found stale spec-workflow refs:"
        echo "$intentional"
        false
    }
}
