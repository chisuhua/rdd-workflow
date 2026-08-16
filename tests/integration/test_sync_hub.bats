#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  cd "$REPO_ROOT"
}

@test "sync_hub.py --help shows usage" {
  run python3 skills/sync-hub/scripts/sync_hub.py --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ "--contract" ]]
}

@test "sync_hub.py --dry-run exits 0 without network" {
  export RDDF_HUB_REPO="fake-org/rdd-hub"
  export RDDF_SYNC_DRY_RUN=yes
  run python3 skills/sync-hub/scripts/sync_hub.py --contract auth-v2.yaml
  [ "$status" -eq 0 ]
  [[ "$output" =~ "DRY-RUN" ]]
}

@test "sync_hub.py rejects missing --contract" {
  run python3 skills/sync-hub/scripts/sync_hub.py
  [ "$status" -ne 0 ]
}
