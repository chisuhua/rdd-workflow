#!/usr/bin/env bash
# tests/e2e/_lib/isolation.bash
# E2E isolation primitives: snapshot repo state, verify zero pollution.
# Locked files (per 2026-09-08-e2e-test-plan-design.md §7 #6):
#   $REPO_ROOT/.rddf/
#   $REPO_ROOT/openspec/
#   $REPO_ROOT/.rddf/wt/

# Locked paths relative to REPO_ROOT
_ISOLATION_LOCKED_PATHS=(
    ".rddf"
    "openspec"
    ".rddf/wt"
    ".rddf/state/iteration.json"
    ".rddf/state/sessions.json"
    ".rddf/state/roadmap-state.json"
)

# isolation::snapshot_repo_state <output_file>
# Compute sha256 of locked paths (or "ABSENT:<path>" if not exist) and write
# one line per path to <output_file>. Format: "<sha256>  <path>"
isolation::snapshot_repo_state() {
    local out="$1"
    : > "$out"
    local p sha
    for p in "${_ISOLATION_LOCKED_PATHS[@]}"; do
        if [ -e "$REPO_ROOT/$p" ]; then
            if [ -d "$REPO_ROOT/$p" ]; then
                # tar stream avoids per-file xargs overhead on large dirs
                sha=$(cd "$REPO_ROOT" && tar -cf - "$p" 2>/dev/null | sha256sum | awk '{print $1}')
            else
                sha=$(cd "$REPO_ROOT" && sha256sum "$p" 2>/dev/null | awk '{print $1}')
            fi
        else
            sha="ABSENT"
        fi
        echo "$sha  $p" >> "$out"
    done
}

# isolation::verify_zero_pollution <baseline_file>
# Recompute current sha256 of locked paths and diff against baseline.
# Returns 0 if all match, 1 if any differ, 2 on internal error.
isolation::verify_zero_pollution() {
    local baseline="$1"
    local current
    current=$(mktemp)
    isolation::snapshot_repo_state "$current"
    if diff -q "$baseline" "$current" >/dev/null 2>&1; then
        rm -f "$current"
        return 0
    else
        diff "$baseline" "$current" >&2 || true
        rm -f "$current"
        return 1
    fi
}
