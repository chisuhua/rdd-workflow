#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  cd "$REPO_ROOT"
}

@test "report_issue_rfc.py --help shows usage" {
  run python3 skills/report-issue/scripts/report_issue_rfc.py --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ "--category" ]]
  [[ "$output" =~ "--title" ]]
}

@test "report_issue_rfc.py --dry-run exits 0 and prints plan" {
  export RDDF_REPORT_GH_REPO="fake-org/rdd-hub"
  export RDDF_REPORT_DRY_RUN=yes
  run python3 skills/report-issue/scripts/report_issue_rfc.py \
    --category=rfc \
    --title "[RFC] Test RFC" \
    --stakeholders "org/repo-a,org/repo-b" \
    --gate "Design-Gate" \
    --contract-impact "Breaking-Change"
  [ "$status" -eq 0 ]
  [[ "$output" =~ "would create Issue" ]]
}

@test "report_issue_rfc.py rejects missing --title" {
  run python3 skills/report-issue/scripts/report_issue_rfc.py --category=rfc
  [ "$status" -ne 0 ]
}
