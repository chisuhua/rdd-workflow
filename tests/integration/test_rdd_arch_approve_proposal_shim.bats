#!/usr/bin/env bats
# Test that the broken shim skills/rdd-arch/scripts/approve_proposal.sh
# (which exec'd into deleted guide-design/scripts/approve_proposal.sh) is gone
# or re-pointed, per fix-v4-rdd-planner-scope-over-assignment Task 3 / B2.

@test "approve_proposal.sh is either deleted or re-pointed" {
    if [ -f "$REPO_ROOT/skills/rdd-arch/scripts/approve_proposal.sh" ]; then
        run grep -F "guide-design/scripts/approve_proposal.sh" "$REPO_ROOT/skills/rdd-arch/scripts/approve_proposal.sh"
        [ "$output" = "" ]
    else
        skip "approve_proposal.sh deleted; that's also OK"
    fi
}
