#!/usr/bin/env bats
# Integration: verify report_regression.sh sed strip 修复对 ## / # ADR-NNNN baseline 描述无影响

load ../test_helper

@test "report_regression: strip 保留 ## 决策 / ## Decision 描述" {
    desc="every real ADR has a ## 决策 or ## Decision section"
    stripped=$(echo "$desc" | sed -E 's/[[:space:]]+# (pre-existing|historical)[^a-zA-Z0-9_].*$//')
    [ "$stripped" = "$desc" ]
}

@test "report_regression: strip 保留 # ADR-NNNN: header 描述" {
    desc="every real ADR has # ADR-NNNN: header"
    stripped=$(echo "$desc" | sed -E 's/[[:space:]]+# (pre-existing|historical)[^a-zA-Z0-9_].*$//')
    [ "$stripped" = "$desc" ]
}

@test "report_regression: strip 仍正确 strip # pre-existing: 注释" {
    desc="some test # pre-existing: legacy WIP"
    stripped=$(echo "$desc" | sed -E 's/[[:space:]]+# (pre-existing|historical)[^a-zA-Z0-9_].*$//')
    [ "$stripped" = "some test" ]
}
