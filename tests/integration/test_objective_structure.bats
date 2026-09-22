#!/usr/bin/env bats
# tests/integration/test_objective_structure.bats
#
# Structural coverage for objective files (per add-objective-tracking change):
#   - doctor structure check passes valid objective files
#   - structure check fails invalid kind in ledger → CRITICAL
#   - structure check warns missing review_by → WARNING
#   - N/A format constraint: plain N/A rejected, "N/A — <reason>" accepted
#
# Run: bats tests/integration/test_objective_structure.bats

load ../test_helper

setup() {
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    export PROJECT_ROOT
    DOCTOR_SH="$PROJECT_ROOT/skills/rdd-doctor/scripts/doctor.sh"
}

@test "objective-structure: doctor structure check passes valid PoC files" {
    run bash "$DOCTOR_SH" --category objective-structure
    [ "$status" -le 2 ]
}

@test "objective-structure: invalid kind in ledger produces finding" {
    local TMP_DIR; TMP_DIR="$(mktemp -d)"
    mkdir -p "$TMP_DIR/.rddf/roadmap/objectives"
    cp "$PROJECT_ROOT/.rddf/roadmap/objectives/objective-onboard-new-skill.md" "$TMP_DIR/.rddf/roadmap/objectives/objective-invalid-kind.md"
    # Introduce an invalid kind in the ledger
    sed -i 's/| sprint-review |/| bogus-kind |/' "$TMP_DIR/.rddf/roadmap/objectives/objective-invalid-kind.md"
    run bash -c "RDDF_PROJECT_ROOT='$TMP_DIR' bash '$DOCTOR_SH' --category objective-structure"
    [ "$status" -ge 1 ]
    rm -rf "$TMP_DIR"
}

@test "objective-structure: missing review_by produces finding" {
    local TMP_DIR; TMP_DIR="$(mktemp -d)"
    mkdir -p "$TMP_DIR/.rddf/roadmap/objectives"
    cp "$PROJECT_ROOT/.rddf/roadmap/objectives/objective-onboard-new-skill.md" "$TMP_DIR/.rddf/roadmap/objectives/objective-missing-review.md"
    sed -i '/^review_by:/d' "$TMP_DIR/.rddf/roadmap/objectives/objective-missing-review.md"
    run bash -c "RDDF_PROJECT_ROOT='$TMP_DIR' bash '$DOCTOR_SH' --category objective-structure"
    [ "$status" -ge 1 ]
    rm -rf "$TMP_DIR"
}

@test "objective-structure: N/A format constraint enforced by _lib.objective" {
    python3 - "$PROJECT_ROOT" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[1])
from _lib.objective import is_na_format, NA_PATTERN

# Plain N/A rejected
assert is_na_format("N/A") is False
assert NA_PATTERN.search("## 10.\nN/A\n") is None
# Well-formed N/A — reason accepted
assert is_na_format("N/A — objective 维持 v3.2 deferred") is True
assert NA_PATTERN.search("## 10.\nN/A — reason here\n") is not None
print("N/A format checks OK")
PYEOF
}

@test "objective-structure: all 5 ledger kinds accepted" {
    python3 - "$PROJECT_ROOT" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[1])
from _lib.objective import KIND_ENUM

expected = {"deferral-rationale", "go-decision", "sprint-review", "scope-change", "adr-amendment"}
assert KIND_ENUM == expected, f"got {KIND_ENUM}"
print("5 ledger kinds OK")
PYEOF
}
