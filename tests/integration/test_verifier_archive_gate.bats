#!/usr/bin/env bats
# tests/integration/test_verifier_archive_gate.bats

load 'test_helper'

setup() {
    REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
    cd "$REPO_ROOT"
}

@test "verifier-archive-gate: ADR-0035 file exists" {
    [ -f "docs/adr/ADR-0035-verifier-archive-gate-boundary.md" ]
}

@test "verifier-archive-gate: ADR-0035 documents all 4 scenarios" {
    grep -q "场景 1" docs/adr/ADR-0035-verifier-archive-gate-boundary.md
    grep -q "场景 2" docs/adr/ADR-0035-verifier-archive-gate-boundary.md
    grep -q "场景 3" docs/adr/ADR-0035-verifier-archive-gate-boundary.md
    grep -q "场景 4" docs/adr/ADR-0035-verifier-archive-gate-boundary.md
}

@test "verifier-archive-gate: ADR-0035 documents STRICT_AC_GATE escalation" {
    grep -q "STRICT_AC_GATE" docs/adr/ADR-0035-verifier-archive-gate-boundary.md
}

@test "verifier-archive-gate: archive.sh references ADR-0035" {
    grep -q "ADR-0035" _lib/archive.sh
}

@test "verifier-archive-gate: README.md ADR index includes ADR-0035" {
    grep -q "ADR-0035" docs/adr/README.md
}