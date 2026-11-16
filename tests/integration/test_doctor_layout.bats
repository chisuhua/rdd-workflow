#!/usr/bin/env bats
# Doctor category "layout": three judgement branches + the zero-finding
# invariants (this repository, and a project without .rddf/).
#
# The doctor reads the project root from RDDF_PROJECT_ROOT (doctor_main.py
# resolves it at import time), so each test points it at its own fixture.

setup() {
    REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/../.." && pwd)"
    TMP="$(mktemp -d)"
    export RDDF_PROJECT_ROOT="$TMP"
    mkdir -p "$TMP/.rddf/state" "$TMP/.rddf/improvements" "$TMP/.rddf/plans" \
             "$TMP/.rddf/roadmap" "$TMP/.rddf/wt"
    : > "$TMP/.rddf/roadmap.md"
    : > "$TMP/.rddf/project.yaml"
    printf '.rddf/state/\n.rddf/wt/\n.rddf/detectors/\n.rddf/actions/\n.rddf/issues/\n' \
        > "$TMP/.gitignore"
    cd "$TMP"
    git init -q . && git config user.email t@t && git config user.name t
}

teardown() {
    cd "$REPO_ROOT"
    rm -rf "$TMP"
}

run_layout() {
    run python3 "$REPO_ROOT/skills/rdd-doctor/scripts/doctor_main.py" --category layout
}

@test "layout: missing always-entry yields WARNING" {
    rm -rf "$TMP/.rddf/improvements"
    run_layout
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "layout.missing-required"
    echo "$output" | grep -q "improvements"
}

@test "layout: unregistered top-level entry yields INFO" {
    mkdir -p "$TMP/.rddf/unknown-dir"
    run_layout
    echo "$output" | grep -q "layout.unregistered"
    echo "$output" | grep -q "unknown-dir"
}

@test "layout: class mismatch with .gitignore yields WARNING" {
    sed -i '/\.rddf\/state\//d' "$TMP/.gitignore"
    run_layout
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "layout.class-mismatch"
}

@test "layout: no .rddf directory yields zero findings" {
    rm -rf "$TMP/.rddf"
    run_layout
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "All 1 categories OK"
}

@test "layout: this repository yields zero findings" {
    export RDDF_PROJECT_ROOT="$REPO_ROOT"
    run python3 "$REPO_ROOT/skills/rdd-doctor/scripts/doctor_main.py" --category layout
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "All 1 categories OK"
}

@test "layout: category never emits CRITICAL" {
    rm -rf "$TMP/.rddf/improvements" "$TMP/.rddf/plans"
    mkdir -p "$TMP/.rddf/unknown-dir"
    sed -i '/\.rddf\/state\//d' "$TMP/.gitignore"
    run_layout
    [ "$status" -eq 1 ]
    echo "$output" | grep -qv "CRITICAL"
}

@test "layout: architecture doc exists and is indexed" {
    [ -f "$REPO_ROOT/docs/architecture/rddf-layout.md" ]
    grep -q "rddf-layout.md" "$REPO_ROOT/docs/architecture/README.md"
    grep -q "rddf layout --json" "$REPO_ROOT/docs/architecture/rddf-layout.md"
}

@test "layout: state-and-events handoff table uses v4 names" {
    run grep -nE "^\| .*(guide-design|guide-plan|guide-ship|design-handoff|plan-handoff)" \
        "$REPO_ROOT/docs/architecture/state-and-events.md"
    [ "$status" -ne 0 ]
    run grep -nE "^\s+H[0-9]\[.*(design-handoff|plan-handoff)" \
        "$REPO_ROOT/docs/architecture/state-and-events.md"
    [ "$status" -ne 0 ]
    grep -q "planner-handoff.json" "$REPO_ROOT/docs/architecture/state-and-events.md"
}

@test "layout: ADR-0026 points at the machine-readable form" {
    grep -q "rddf layout --json" \
        "$REPO_ROOT/docs/adr/ADR-0026-internal-metadata-namespace-convention.md"
}

@test "layout: rdd-doctor SKILL.md carries no hardcoded category count" {
    run grep -nE "[0-9]+ (file )?categories" "$REPO_ROOT/skills/rdd-doctor/SKILL.md"
    [ "$status" -ne 0 ]
}

@test "layout: rdd-doctor usage line lists every registered category" {
    python3 - "$REPO_ROOT" <<'PY'
import re, sys
root = sys.argv[1]
src = open(f"{root}/skills/rdd-doctor/scripts/doctor_main.py", encoding="utf-8").read()
block = re.search(r"_CHECKERS: dict\[str, Union\[str, Callable\]\] = \{(.*?)\n\}", src, re.S).group(1)
registered = set(re.findall(r'"([a-z0-9\-]+)":\s*"checks\.', block))
skill = open(f"{root}/skills/rdd-doctor/SKILL.md", encoding="utf-8").read()
usage = re.search(r"--category \{([^}]*)\}", skill).group(1)
listed = {x.strip() for x in usage.split(",")}
missing = registered - listed
assert not missing, f"usage 行漏列 category: {sorted(missing)}"
PY
}
