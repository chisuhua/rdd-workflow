#!/usr/bin/env bats

load ../test_helper

_make_state_sh() {
  local target="$1"
  mkdir -p "$(dirname "$target")"
  cat > "$target" <<'EOF'
check_dirty_key_files() { return 0; }
detect_approved_inconsistency() { return 0; }
sweep_stale_suggestions() { return 0; }
SCANNER_FALLBACK_SOURCE_PATH="${BASH_SOURCE[0]}"
EOF
}

_run_scan_state() {
  local repo="$1"
  bash -c '
    cd "$1"
    source "$REPO_ROOT/skills/guide/scripts/scan-state.sh"
    scan_state "$1"
    echo "SOURCE=$SCANNER_FALLBACK_SOURCE_PATH"
    echo "RECOMMEND=$RECOMMEND"
    echo "REASON=$REASON"
  ' _ "$repo"
}

setup() {
  repo=$(mktemp -d)
  home=$(mktemp -d)
  git init -q "$repo"
  git -C "$repo" config user.email "t@t"
  git -C "$repo" config user.name "t"
  touch "$repo/init"
  git -C "$repo" add init
  git -C "$repo" commit -q -m init
  export HOME="$home"
}

teardown() {
  rm -rf "$repo" "$home"
}

@test "scanner fallback: local state.sh used when both exist" {
  _make_state_sh "$repo/_lib/state.sh"
  _make_state_sh "$home/.agents/_lib/state.sh"

  run _run_scan_state "$repo"

  [ "$status" -eq 0 ]
  [[ "$output" == *"SOURCE=$repo/_lib/state.sh"* ]]
  [[ "$output" == *"RECOMMEND=guide-arch"* ]]
}

@test "scanner fallback: global state.sh used when local is missing" {
  _make_state_sh "$home/.agents/_lib/state.sh"

  run _run_scan_state "$repo"

  [ "$status" -eq 0 ]
  [[ "$output" == *"SOURCE=$home/.agents/_lib/state.sh"* ]]
  [[ "$output" == *"RECOMMEND=guide-arch"* ]]
}

@test "scanner fallback: warning when both copies are missing" {
  run bash -c 'source "$REPO_ROOT/skills/guide/scripts/scan-state.sh"; scan_state "$1" 2>&1' _ "$repo"

  [ "$status" -eq 0 ]
  [[ "$output" == *"rdd-workflow not installed"* ]]
  [[ "$output" == *"INSTALL.md"* ]]
}

@test "scanner fallback: local and global produce identical recommendation" {
  _make_state_sh "$repo/_lib/state.sh"
  local local_out
  local_out=$(_run_scan_state "$repo")
  rm "$repo/_lib/state.sh"
  _make_state_sh "$home/.agents/_lib/state.sh"
  local global_out
  global_out=$(_run_scan_state "$repo")

  [ "$(printf '%s\n' "$local_out" | grep -E '^(RECOMMEND|REASON)=')" = "$(printf '%s\n' "$global_out" | grep -E '^(RECOMMEND|REASON)=')" ]
}

_run_guide_entry() {
  local repo="$1"
  local home="$2"
  bash -c '
    export HOME="$1"
    cd "$2"
    source "$3/skills/guide/scripts/guide_entry.sh"
    guide_entry --no-binding
  ' _ "$home" "$repo" "$REPO_ROOT"
}

@test "guide_entry fallback: global state.sh used when local is missing" {
  _make_state_sh "$home/.agents/_lib/state.sh"

  run _run_guide_entry "$repo" "$home"

  [ "$status" -eq 0 ]
  [[ "$output" == *"Workflow Entry"* ]]
  [[ "$output" != *"rdd-workflow not installed"* ]]
}

@test "guide_entry fallback: warning when both copies are missing" {
  run _run_guide_entry "$repo" "$home"

  [ "$status" -eq 0 ]
  [[ "$output" == *"rdd-workflow not installed"* ]]
  [[ "$output" == *"INSTALL.md"* ]]
}
