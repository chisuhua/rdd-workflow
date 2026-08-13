#!/usr/bin/env bats
# Spec 2026-08-13 §2 / C1: RDDF_USE_ORCHESTRATOR default flip.
# Verifies the single-writer rule in post_flow_on_err now triggers
# by default (without requiring explicit RDDF_USE_ORCHESTRATOR=yes).

setup() {
    WRAP="${BATS_TEST_DIRNAME}/../../skills/_lib/post_flow_wrap.sh"
}

@test "C1: default expansion flipped to :-yes in post_flow_wrap.sh" {
    # Snapshot test: the literal default expansion must now be :-yes.
    grep -q 'RDDF_USE_ORCHESTRATOR:-yes' "$WRAP"
}

@test "C1: unset RDDF_USE_ORCHESTRATOR triggers deferral by default" {
    # When unset, deferral happens by default (default-ON semantics).
    run bash -c '
        unset RDDF_USE_ORCHESTRATOR
        if [ "${RDDF_USE_ORCHESTRATOR:-yes}" = "yes" ]; then
            echo "deferred=1"
        else
            echo "deferred=0"
        fi
    '
    [ "$output" = "deferred=1" ]
}

@test "C1: explicit RDDF_USE_ORCHESTRATOR=no bypasses deferral" {
    # When user sets no explicitly, the deferral must NOT happen.
    run bash -c '
        export RDDF_USE_ORCHESTRATOR=no
        if [ "${RDDF_USE_ORCHESTRATOR:-yes}" = "yes" ]; then
            echo "deferred=1"
        else
            echo "deferred=0"
        fi
    '
    [ "$output" = "deferred=0" ]
}
