#!/usr/bin/env bats
# ------------------------------------------------------------------------------
# 真实 GitHub 集成测试: detect_cross_repo_impact against chisuhua/rdd-hub
#
# 覆盖 AC-1/AC-2/AC-3/AC-4:
#   - 单契约匹配 → warning + report JSON
#   - 无匹配 → silent
#   - RDDF_SKIP_CROSS_REPO_DETECTION=yes → 跳过
#   - 多契约匹配 → stakeholders union
#
# 前置:
#   - gh auth OK
#   - chisuhua/rdd-hub 存在且有 contracts/*.yaml (or 空)
#
# 运行:
#   bats tests/integration/test_cross_repo_impact_detection.bats
# ------------------------------------------------------------------------------

load ../test_helper

setup_file() {

  # Skip-not-fail (add-e2e-test-skip-on-missing-hub-auth): 
  # gh/auth/Hub 不可达时优雅 skip
  if ! command -v gh >/dev/null 2>&1; then
    skip "gh CLI not available; skipping E2E (requires real GitHub Hub)"
  fi
  if ! gh auth status >/dev/null 2>&1; then
    skip "gh not authenticated; skipping E2E (requires chisuhua/rdd-hub access)"
  fi
  if ! gh repo view "$E2E_HUB_REPO" >/dev/null 2>&1; then
    skip "Hub $E2E_HUB_REPO unreachable; skipping E2E"
  fi

  E2E_HUB_REPO="${E2E_HUB_REPO:-chisuhua/rdd-hub}"
  export E2E_HUB_REPO
  export RDDF_HUB_REPO="$E2E_HUB_REPO"

  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT

  # 确保 Hub 至少有一个 contract 以触发匹配 (push 一个测试 contract)
  CONTRACT_NAME="e2e-detect-test.yaml"
  CONTENT="openapi: 3.0.0\ninfo:\n  title: E2E Detect Test\n  version: 1.0.0\nx-owners: [chisuhua/test-repo]\npaths:\n  /e2e/detect:\n    get:\n      responses:\n        '200':\n          description: ok\n"
  CONTENT_B64=$(printf '%s' "$CONTENT" | base64 -w0)

  if ! gh api "repos/$E2E_HUB_REPO/contents/contracts/$CONTRACT_NAME" >/dev/null 2>&1; then
    gh api -X PUT "repos/$E2E_HUB_REPO/contents/contracts/$CONTRACT_NAME" \
      -f message="e2e detect test contract" \
      -f content="$CONTENT_B64" >/dev/null 2>&1 || true
  fi

  : > "$BATS_TMPDIR/cleanup-contracts"
  echo "$CONTRACT_NAME" > "$BATS_TMPDIR/cleanup-contracts"
}

teardown_file() {
  if [ -f "$BATS_TMPDIR/cleanup-contracts" ]; then
    while IFS= read -r name; do
      [ -z "$name" ] && continue
      sha=$(gh api "repos/$E2E_HUB_REPO/contents/contracts/$name" 2>/dev/null \
            | grep -oE '"sha":\s*"[^"]+"' | head -1 | sed 's/.*"sha":\s*"\([^"]*\)".*/\1/' || true)
      [ -z "$sha" ] && continue
      gh api -X DELETE "repos/$E2E_HUB_REPO/contents/contracts/$name" \
        -f message="e2e cleanup" -f sha="$sha" >/dev/null 2>&1 || true
    done < "$BATS_TMPDIR/cleanup-contracts"
  fi
}

setup() {
  TEST_DIR="$BATS_TMPDIR/test-$BATS_TEST_NUMBER"
  mkdir -p "$TEST_DIR"
  export TEST_DIR
}

@test "01_single_contract_match_returns_warning_and_report" {
  cat > "$TEST_DIR/proposal.md" <<EOF
# Test Proposal

**阶段**: v2.2
**分类**: cross-repo-federation
**类型**: feature
**特性**: __ungrouped__

## Why

Need to update e2e-detect flow with new field.
EOF

  run env RDDF_HUB_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/add-improve/scripts/detect_cross_repo_impact.py" \
      --proposal "$TEST_DIR/proposal.md" \
      --hub-repo "$E2E_HUB_REPO" \
      --output "$TEST_DIR/report.json"
  echo "$output"
  [ "$status" -eq 0 ]

  [ -f "$TEST_DIR/report.json" ]
  run jq -r '.matches[0].contract_name' "$TEST_DIR/report.json"
  [ "$status" -eq 0 ]
  [[ "$output" == *"e2e-detect-test.yaml"* ]]

  run jq -r '.suggested_stakeholders | length' "$TEST_DIR/report.json"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]
}

@test "02_no_match_returns_silent" {
  # Avoid words matching Hub contracts: no "e2e", "detect", or "test" in body
  cat > "$TEST_DIR/proposal.md" <<EOF
# Routine Refactor Proposal

**阶段**: v2.2
**分类**: general
**类型**: feature
**特性**: __ungrouped__

## Why

A CLI argument parser refactor for clarity and Python 3.12 compatibility.
EOF

  run env RDDF_HUB_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/add-improve/scripts/detect_cross_repo_impact.py" \
      --proposal "$TEST_DIR/proposal.md" \
      --hub-repo "$E2E_HUB_REPO" \
      --output "$TEST_DIR/report.json"
  [ "$status" -eq 0 ]

  run jq -r '.matches | length' "$TEST_DIR/report.json"
  [ "$status" -eq 0 ]
  [ "$output" -eq 0 ]

  run jq -r '.suggested_category' "$TEST_DIR/report.json"
  [ "$status" -eq 0 ]
  [ "$output" == "null" ]
}

@test "03_opt_out_env_disables_detection" {
  cat > "$TEST_DIR/proposal.md" <<EOF
# Test Proposal

**阶段**: v2.2
**分类**: cross-repo-federation
**类型**: feature
**特性**: __ungrouped__

## Why

Should match e2e-detect if detection ran.
EOF

  run env RDDF_SKIP_CROSS_REPO_DETECTION=yes RDDF_HUB_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/add-improve/scripts/detect_cross_repo_impact.py" \
      --proposal "$TEST_DIR/proposal.md" \
      --hub-repo "$E2E_HUB_REPO" \
      --output "$TEST_DIR/report.json"
  [ "$status" -eq 0 ]

  # Output file should NOT exist (opt-out early return)
  [ ! -f "$TEST_DIR/report.json" ]
}

@test "04_multi_contract_match_returns_stakeholders_union" {
  # Push second test contract
  CONTRACT2="e2e-detect-test2.yaml"
  CONTENT2="openapi: 3.0.0\ninfo:\n  title: E2E Detect Test 2\n  version: 1.0.0\nx-owners: [chisuhua/test-repo-2, chisuhua/test-repo-3]\npaths:\n  /e2e/detect2:\n    get:\n      responses:\n        '200':\n          description: ok\n"
  CONTENT_B64=$(printf '%s' "$CONTENT2" | base64 -w0)
  gh api -X PUT "repos/$E2E_HUB_REPO/contents/contracts/$CONTRACT2" \
    -f message="e2e detect test 2" -f content="$CONTENT_B64" >/dev/null 2>&1 || true
  echo "$CONTRACT2" >> "$BATS_TMPDIR/cleanup-contracts"

  cat > "$TEST_DIR/proposal.md" <<EOF
# Test Proposal

**阶段**: v2.2
**分类**: cross-repo-federation
**类型**: feature
**特性**: __ungrouped__

## Why

Update both e2e-detect-test and e2e-detect-test2 contracts.
EOF

  run env RDDF_HUB_REPO="$E2E_HUB_REPO" \
    python3 "$REPO_ROOT/skills/add-improve/scripts/detect_cross_repo_impact.py" \
      --proposal "$TEST_DIR/proposal.md" \
      --hub-repo "$E2E_HUB_REPO" \
      --output "$TEST_DIR/report.json"
  [ "$status" -eq 0 ]

  run jq -r '.matches | length' "$TEST_DIR/report.json"
  [ "$status" -eq 0 ]
  [ "$output" -ge 2 ]

  run jq -r '.suggested_stakeholders | length' "$TEST_DIR/report.json"
  [ "$status" -eq 0 ]
  [ "$output" -ge 3 ]
}