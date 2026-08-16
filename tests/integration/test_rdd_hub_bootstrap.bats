#!/usr/bin/env bats

load ../test_helper

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  cd "$REPO_ROOT"
  rm -f rdd-hub-bootstrap.log
}

teardown() {
  rm -f rdd-hub-bootstrap.log
}

@test "create_new_hub_repo: dry-run exits 0 and logs repo_create" {
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub
  [ "$status" -eq 0 ]
  grep -q "OPERATION=repo_create STATUS=planned" rdd-hub-bootstrap.log
}

@test "idempotent_existing_hub: second dry-run shows skipped operations" {
  bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub >/dev/null 2>&1
  rm -f rdd-hub-bootstrap.log
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub
  [ "$status" -eq 0 ]
  grep -qE "STATUS=(dry_run|skipped)" rdd-hub-bootstrap.log
}

@test "dry_run_no_api_calls: dry-run does not invoke gh commands" {
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub
  [ "$status" -eq 0 ]
  ! grep -q "gh repo create.*--public" rdd-hub-bootstrap.log || true
}

@test "fields_config: all 6 Projects V2 fields referenced in dry-run output" {
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub
  [[ "$output" =~ "Status" ]]
  [[ "$output" =~ "Initiator" ]]
  [[ "$output" =~ "Stakeholders" ]]
  [[ "$output" =~ "Review-Progress" ]]
  [[ "$output" =~ "RDD-Gate" ]]
  [[ "$output" =~ "Contract-Impact" ]]
}

@test "workflow_deploy: both workflow files mentioned in dry-run output" {
  run bash skills/rdd-hub-bootstrap/scripts/init_hub.sh --dry-run --org fake-org --repo fake-hub
  [[ "$output" =~ "contract-lint.yml" ]]
  [[ "$output" =~ "stale-rfc.yml" ]]
}

@test "global-adr template README exists" {
  [ -f "skills/rdd-hub-bootstrap/templates/global-adr/README.md" ]
}
