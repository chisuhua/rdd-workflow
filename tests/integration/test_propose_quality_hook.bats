#!/usr/bin/env bats

load ../test_helper

@test "propose-quality-hook: wrapper exists and exposes function" {
  assert_file_exists "$REPO_ROOT/skills/propose/scripts/propose_quality_hook.sh"
  assert_file_contains "$REPO_ROOT/skills/propose/scripts/propose_quality_hook.sh" "invoke_propose_quality_hook"
}

@test "propose-quality-hook: propose.md Phase 4 invokes the hook" {
  assert_file_contains "$REPO_ROOT/skills/propose/SKILL.md" "propose_quality_hook.sh"
}

@test "propose-quality-hook: gate.py registers propose_quality_checks" {
  assert_file_contains "$REPO_ROOT/skills/_lib/gate.py" "propose_quality_checks"
}

@test "propose-quality-hook: hook runs against a valid proposal" {
  local root="$BATS_TMPDIR/hook-valid-$$"
  mkdir -p "$root/openspec/changes/c1"
  cat > "$root/openspec/changes/c1/proposal.md" <<'EOF'
## Why

EOF
  printf 'x%.0s' {1..500} >> "$root/openspec/changes/c1/proposal.md"
  cat >> "$root/openspec/changes/c1/proposal.md" <<'EOF'

Refs ADR-0019.

## In Scope

do thing

## Out of Scope

not doing
EOF
  cat > "$root/openspec/changes/c1/tasks.md" <<'EOF'
## Tasks

- [ ] one
- [ ] two
EOF
  printf '%s
' "# Roadmap" "" "- c1" > "$root/roadmap.md"

  run env PROJECT_ROOT="$root" CHANGE_NAME="c1" python3 "$REPO_ROOT/skills/propose/scripts/propose_quality_hook.py"
  [ "$status" -eq 0 ]
  [ -f "$root/.rddf/state/propose-quality.json" ]
}

@test "propose-quality-hook: hook with broken proposal default exits 0" {
  local root="$BATS_TMPDIR/hook-broken-$$"
  mkdir -p "$root/openspec/changes/c1"
  printf '%s
' "## Why" "" "short" > "$root/openspec/changes/c1/proposal.md"

  run env PROJECT_ROOT="$root" CHANGE_NAME="c1" python3 "$REPO_ROOT/skills/propose/scripts/propose_quality_hook.py"
  [ "$status" -eq 0 ]
  [ -f "$root/.rddf/state/propose-quality.json" ]
}

@test "propose-quality-hook: hook with broken proposal strict exits 1" {
  local root="$BATS_TMPDIR/hook-strict-$$"
  mkdir -p "$root/openspec/changes/c1"
  printf '%s
' "## Why" "" "short" > "$root/openspec/changes/c1/proposal.md"

  run env PROJECT_ROOT="$root" CHANGE_NAME="c1" STRICT_PROPOSE_GATE="yes" python3 "$REPO_ROOT/skills/propose/scripts/propose_quality_hook.py"
  [ "$status" -eq 1 ]
}
