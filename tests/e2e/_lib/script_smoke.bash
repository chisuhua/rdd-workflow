#!/usr/bin/env bash
# tests/e2e/_lib/script_smoke.bash
# A-layer (CI必跑) helper: fake project setup + phase script invocation.
# Wraps `bash skills/<skill>/scripts/<phase>.sh <args>` for non-interactive use.

# script_smoke::setup_fake_project <root>
# Initialize fake git repo + openspec skeleton + .rddf/ at <root>.
script_smoke::setup_fake_project() {
    local root="$1"
    mkdir -p "$root/openspec/changes" "$root/openspec/specs" "$root/.rddf/state"
    : > "$root/openspec/changes/.gitkeep"
    : > "$root/openspec/specs/.gitkeep"
    : > "$root/.rddf/state/.gitkeep"
    git -C "$root" init -q -b main
    git -C "$root" config user.email "e2e@test.local"
    git -C "$root" config user.name "e2e test"
    git -C "$root" add -A
    git -C "$root" commit -q -m "e2e: initial fake project"
}

# script_smoke::cleanup_fake_project <root>
script_smoke::cleanup_fake_project() {
    local root="$1"
    [ -d "$root" ] && rm -rf "$root"
}

# script_smoke::invoke_phase <phase_script> <change_name> <fake_root> [extra_args...]
# Run phase script in fake project context. Returns script's exit code.
# Requires phase scripts to support --auto-approve flag (added in Tasks 4-9).
script_smoke::invoke_phase() {
    local phase_script="$1"
    local change_name="$2"
    local fake_root="$3"
    shift 3
    local script_path="$SMOKE_REPO_ROOT/skills/rdd-builder/scripts/$phase_script"
    if [ ! -x "$script_path" ]; then
        echo "ERROR: $script_path not found or not executable" >&2
        return 127
    fi
    ( cd "$fake_root" && CHANGE_NAME="$change_name" bash "$script_path" "$change_name" "$@" )
}
