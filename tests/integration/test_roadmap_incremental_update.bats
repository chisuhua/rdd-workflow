#!/usr/bin/env bats
# Test guide-arch/scripts/roadmap_incremental_update.{sh,py,env.py}
# (move-populate-roadmap-into-guide-arch, Task D).
#
# Covers the cross-call chain: sh wrapper -> env validator -> main module ->
# populate_lib 7-function API -> .rddf/state/.populate-state.json (schema v2).
#
# Oracle C1: all values flow via env vars; no bash $VAR interpolation into python.

load ../test_helper

SCRIPT_SH="$REPO_ROOT/skills/rdd-arch/scripts/roadmap_incremental_update.sh"
SCRIPT_ENV_PY="$REPO_ROOT/skills/rdd-arch/scripts/roadmap_incremental_update.env.py"

setup() {
    TEST_TMPDIR="$(mktemp -d)"
    cd "$TEST_TMPDIR"
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"
    mkdir -p docs/adr
    cat > docs/adr/ADR-0001-test.md <<'EOF'
---
status: 已采纳
title: Test ADR
---
# ADR-0001 Test
EOF
    git add . && git commit -q -m "init"
}

teardown() {
    cd /
    rm -rf "$TEST_TMPDIR" 2>/dev/null || true
}

run_updater() {
    RDDF_PROJECT_ROOT="$TEST_TMPDIR" \
    RDDF_CODEBASE_COMMIT="$(git -C "$TEST_TMPDIR" rev-parse HEAD)" \
    RDDF_ROADMAP_UPDATE="${RDDF_ROADMAP_UPDATE:-on}" \
    RDDF_INCREMENTAL="${RDDF_INCREMENTAL:-on}" \
    run bash "$SCRIPT_SH"
}

@test "roadmap_incremental_update: sh wrapper rejects missing RDDF_PROJECT_ROOT" {
    run env -u RDDF_PROJECT_ROOT \
        RDDF_CODEBASE_COMMIT="$(git rev-parse HEAD)" \
        bash "$SCRIPT_SH"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "RDDF_PROJECT_ROOT"
}

@test "roadmap_incremental_update: env.py rejects malformed CODEBASE_COMMIT" {
    RDDF_PROJECT_ROOT="$TEST_TMPDIR" \
    RDDF_CODEBASE_COMMIT="not-a-hex-commit!" \
    RDDF_ROADMAP_UPDATE=on \
    RDDF_INCREMENTAL=on \
        run python3 "$SCRIPT_ENV_PY"
    [ "$status" -eq 2 ]
    echo "$output" | grep -q "❌"
}

@test "roadmap_incremental_update: full run on empty state.json writes baseline state" {
    run_updater
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Mode: full"
    [ -f "$TEST_TMPDIR/.rddf/state/.populate-state.json" ]
    python3 - "$TEST_TMPDIR/.rddf/state/.populate-state.json" <<'PYEOF'
import json, sys
data = json.load(open(sys.argv[1]))
assert data["version"] == 2, f"expected version=2, got {data['version']}"
assert "ADR-0001" in data["adrs"], f"ADR-0001 missing: {list(data['adrs'])}"
assert len(data["adrs"]["ADR-0001"]["file_hash"]) == 64
assert data["codebase_commit"], "codebase_commit empty"
PYEOF
}

@test "roadmap_incremental_update: T10 cross-call chain (--incremental=off forces full mode)" {
    # First run establishes baseline.
    run_updater
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMPDIR/.rddf/state/.populate-state.json" ]

    # Second run with RDDF_INCREMENTAL=off must force full mode even with a valid baseline.
    RDDF_INCREMENTAL=off run_updater
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Mode: full"
}

@test "roadmap_incremental_update: --roadmap-update=off skips entirely" {
    RDDF_ROADMAP_UPDATE=off run_updater
    [ "$status" -eq 0 ]
    [ ! -f "$TEST_TMPDIR/.rddf/state/.populate-state.json" ]
}

@test "roadmap_incremental_update: idempotent — second run detects no changes → mode=skip" {
    run_updater
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Mode: full"

    run_updater
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Mode: skip"
}

# --- Task G: cross-call chain tests (T10-T12, T17-T18) + edge cases ---

@test "roadmap_incremental_update: T10 Phase-6-style repeat call exits 0, verifies 0 ADRs, state commit == HEAD" {
    # First call establishes the baseline (simulates arch-done Phase 6 hook).
    run_updater
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Mode: full"

    # Second call with the same commit must be a cheap no-op.
    run_updater
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Mode: skip"
    echo "$output" | grep -q "ADRs to verify: 0"

    # State file records the exact HEAD commit of the project.
    python3 - "$TEST_TMPDIR/.rddf/state/.populate-state.json" "$TEST_TMPDIR" <<'PYEOF'
import json, subprocess, sys
data = json.load(open(sys.argv[1]))
head = subprocess.run(
    ["git", "-C", sys.argv[2], "rev-parse", "HEAD"],
    capture_output=True, text=True, check=True,
).stdout.strip()
assert data["codebase_commit"] == head, (
    f"state commit {data['codebase_commit']!r} != HEAD {head!r}"
)
PYEOF
}

@test "roadmap_incremental_update: T11 --roadmap-update=off leaves an existing state file untouched" {
    # Establish baseline state first.
    run_updater
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMPDIR/.rddf/state/.populate-state.json" ]
    before="$(sha256sum "$TEST_TMPDIR/.rddf/state/.populate-state.json" | awk '{print $1}')"

    # off must short-circuit before any write — state stays byte-identical.
    RDDF_ROADMAP_UPDATE=off run_updater
    [ "$status" -eq 0 ]
    after="$(sha256sum "$TEST_TMPDIR/.rddf/state/.populate-state.json" | awk '{print $1}')"
    [ "$before" = "$after" ]
}

@test "roadmap_incremental_update: T12 --roadmap-update=force forces full mode even with a valid baseline" {
    run_updater
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMPDIR/.rddf/state/.populate-state.json" ]

    RDDF_ROADMAP_UPDATE=force run_updater
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Mode: full"
    echo "$output" | grep -q "Reason: force flag"
}

@test "roadmap_incremental_update: T17 first run without baseline reports reason 'no baseline'" {
    [ ! -f "$TEST_TMPDIR/.rddf/state/.populate-state.json" ]
    run_updater
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Mode: full"
    echo "$output" | grep -q "Reason: no baseline"
}

@test "roadmap_incremental_update: T18 stale codebase_commit auto-resets to full mode and rewrites state with HEAD" {
    # Hand-write a schema-v2 state whose commit does not exist in git history.
    mkdir -p "$TEST_TMPDIR/.rddf/state"
    cat > "$TEST_TMPDIR/.rddf/state/.populate-state.json" <<'EOF'
{
  "version": 2,
  "generated_at": "2026-08-21T00:00:00+00:00",
  "codebase_commit": "0000000deadbeef",
  "codegraph_fingerprint": null,
  "adrs": {},
  "reverse_index": {},
  "phases": {}
}
EOF

    run_updater
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Mode: full"
    echo "$output" | grep -q "git baseline invalid"

    # Auto-reset: state now records the real HEAD commit.
    python3 - "$TEST_TMPDIR/.rddf/state/.populate-state.json" "$TEST_TMPDIR" <<'PYEOF'
import json, subprocess, sys
data = json.load(open(sys.argv[1]))
head = subprocess.run(
    ["git", "-C", sys.argv[2], "rev-parse", "HEAD"],
    capture_output=True, text=True, check=True,
).stdout.strip()
assert data["codebase_commit"] == head, (
    f"state commit {data['codebase_commit']!r} != HEAD {head!r}"
)
PYEOF
}

@test "roadmap_incremental_update: edge third consecutive run is still mode=skip (T1 stability)" {
    run_updater
    [ "$status" -eq 0 ]
    run_updater
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Mode: skip"

    run_updater
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Mode: skip"
    echo "$output" | grep -q "Reason: no changes"
    echo "$output" | grep -q "ADRs to verify: 0"
}

# --- Task E: guide-arch/SKILL.md Phase 6 integration ---

@test "guide_arch_phase6: contains Roadmap Sync internal step" {
    grep -q "Roadmap Sync (internal)" "$REPO_ROOT/skills/rdd-arch/SKILL.md"
    grep -q "roadmap_incremental_update.sh" "$REPO_ROOT/skills/rdd-arch/SKILL.md"
}

@test "guide_arch_phase6: frontmatter owns .populate-state.json (ADR-0028)" {
    grep -q '\.rddf/state/\.populate-state\.json' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
    grep -q '\.rddf/roadmap/phases/\*\.md' "$REPO_ROOT/skills/rdd-arch/SKILL.md"
}
