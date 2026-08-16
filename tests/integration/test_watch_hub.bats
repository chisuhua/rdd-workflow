#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  cd "$REPO_ROOT"
  TMP_STATE="$(mktemp -d)"
  mkdir -p "$TMP_STATE/.rddf/state"
}

teardown() {
  rm -rf "$TMP_STATE"
}

@test "watch_hub.py --help shows usage" {
  run python3 skills/watch-hub/scripts/watch_hub.py --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ "--once" ]]
}

@test "watch_hub.py --dry-run --once exits 0 without network" {
  export RDDF_HUB_REPO="fake-org/rdd-hub"
  export RDDF_WATCH_DRY_RUN=yes
  export RDDF_PROJECT_ROOT="$TMP_STATE"
  run python3 skills/watch-hub/scripts/watch_hub.py --once --owner=fake-org/rdd-hub
  [ "$status" -eq 0 ]
  [[ "$output" =~ "DRY-RUN" ]]
}

@test "watch_hub.py requires --once flag" {
  run python3 skills/watch-hub/scripts/watch_hub.py --owner=foo/bar
  [ "$status" -ne 0 ]
}
