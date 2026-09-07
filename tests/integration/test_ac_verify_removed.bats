#!/usr/bin/env bats
# -----------------------------------------------------------------------------
# test_ac_verify_removed.bats — locks the friendly-error stub for the removed
# `rddf ac-verify` subcommand (remove-ac-verifier-completely, 2026-09-07).
#
# Per ADR-0045 (inline-ac-verifier-into-rdd-verifier) + ADR-0045 closure
# (verifier-v2-hardening, archived 2026-09-07):
#   1. `ac-verifier` skill is fully removed from `skills/`.
#   2. `rddf ac-verify` is retained ONLY as a friendly-error stub: exit 4
#      + migration hint to `rddf rdd-verify`.
#   3. `ac-verify` MUST NOT appear in `rddf --help` as an active subcommand.
#
# All `skill_use("ac-verifier", ...)` / `rddf ac-verify ...` calls MUST
# migrate to `rdd-verifier` / `rddf rdd-verify`.
# -----------------------------------------------------------------------------

load test_helper

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
}

@test "rddf ac-verify --help exits 4 with migration hint (no flag parsing)" {
  run python3 "$REPO_ROOT/_lib/cli/ac_verify_cmd.py" --help
  [ "$status" -eq 4 ]
  [[ "$output" == *"removed per ADR-0045"* ]]
  [[ "$output" == *"rddf rdd-verify"* ]]
}

@test "rddf ac-verify <change-name> exits 4 (no caching, no staging)" {
  run python3 "$REPO_ROOT/_lib/cli/ac_verify_cmd.py" my-change --strict --dry-run
  [ "$status" -eq 4 ]
  [[ "$output" == *"removed per ADR-0045"* ]]
  [[ "$output" != *"Staged verification context"* ]]
  [[ "$output" != *"Reusing verdict cache"* ]]
}

@test "rddf ac-verify exit 4 is distinct from exit 0/1/2/3" {
  # exit 4 was reserved per ADR-0045 verifier-v2-hardening for "command removed"
  # (distinct from exit 2 = skipped, exit 1 = verification failed)
  run python3 "$REPO_ROOT/_lib/cli/ac_verify_cmd.py" anything
  [ "$status" -eq 4 ]
  # Negative regression: must NOT return 0 (would mean silent success)
  [ "$status" -ne 0 ]
  [ "$status" -ne 1 ]
  [ "$status" -ne 2 ]
  [ "$status" -ne 3 ]
}

@test "ac-verify is not registered in _lib/cli/__init__.py _ROUTES" {
  # The stub is intentionally NOT registered in the CLI route table so it does
  # not appear in `rddf --help`. It is invoked only via direct python path.
  run grep -c '"ac-verify"' "$REPO_ROOT/_lib/cli/__init__.py"
  [ "$output" -eq 0 ]
}

@test "_lib/cli/ac_verify_cmd.py is retained as a friendly-error stub" {
  # The file MUST still exist (rddf ac-verify command path is preserved for
  # migration UX), but the handler MUST be the stub.
  [ -f "$REPO_ROOT/_lib/cli/ac_verify_cmd.py" ]
  run grep -c "REMOVED stub" "$REPO_ROOT/_lib/cli/ac_verify_cmd.py"
  [ "$output" -ge 1 ]
}

@test "skills/ac-verifier/ does not exist (skill fully removed)" {
  [ ! -d "$REPO_ROOT/skills/ac-verifier" ]
}

@test "_default_runner alias removed from rdd_verify_cmd.py" {
  # All callers must use _stage_context_runner directly.
  run grep -c '_default_runner' "$REPO_ROOT/_lib/cli/rdd_verify_cmd.py"
  # Only the explanatory comment line should match (1 line).
  [ "$output" -le 1 ]
}

@test "_default_runner has no callers anywhere in _lib/ skills/ tests/" {
  # Count non-comment occurrences of the symbol across the source tree.
  # Strategy: filter by file extension, then strip lines whose payload starts
  # with `#` (after the path:line:colon prefix).
  # Excludes:
  #   - Comment lines (payload starts with `#` after path:line: prefix)
  #   - Self-references in this removal-lock test
  #   - Pyc/__pycache__/ artifacts (filtered by --include)
  hits=$(grep -rn '_default_runner' \
    "$REPO_ROOT/_lib/" "$REPO_ROOT/skills/" "$REPO_ROOT/tests/" \
    --include='*.py' --include='*.bats' --include='*.sh' 2>/dev/null \
    | awk -F: '
        {
          payload=$3
          for (i=4; i<=NF; i++) payload=payload ":" $i
          if (payload ~ /^[[:space:]]*#/) next
          if ($0 ~ /test_ac_verify_removed\.bats/) next
          print
        }
      ' | wc -l)
  [ "$hits" -eq 0 ]
}