#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  export REPO_ROOT
  TMP="$(mktemp -d)"
  export RDDF_PROJECT_ROOT="$TMP"
  mkdir -p "$TMP/openspec/changes/test-cross-repo"
  mkdir -p "$TMP/.rddf/improvements"
  # SSOT for category detection (ADR-0031 §分类传递契约):
  # .rddf/improvements/<name>.md `**分类**:` head field.
  cat > "$TMP/.rddf/improvements/test-cross-repo.md" <<'EOF'
# test-cross-repo

**优先级**: P1 | **来源**: test
**阶段**: v2.1.x | **分类**: cross-repo-federation | **类型**: feature
EOF
  cat > "$TMP/openspec/changes/test-cross-repo/roadmap-meta.yaml" <<EOF
name: test-cross-repo
category: cross-repo-federation
EOF
  # gh CLI stub: GH_STUB_MODE controls the fake Hub Issue state.
  mkdir -p "$TMP/bin"
  cat > "$TMP/bin/gh" <<'EOF'
#!/usr/bin/env bash
case "${GH_STUB_MODE:-approved}" in
  approved)  echo '{"state":"OPEN","labels":[{"name":"approved"},{"name":"rfc"}]}' ;;
  no-label)  echo '{"state":"OPEN","labels":[{"name":"rfc"}]}' ;;
  closed)    echo '{"state":"CLOSED","labels":[{"name":"approved"}]}' ;;
  network)   echo "dial tcp: network unreachable" >&2; exit 1 ;;
  auth)      echo "HTTP 401: bad credentials, authentication required" >&2; exit 1 ;;
esac
EOF
  chmod +x "$TMP/bin/gh"
  export PATH="$TMP/bin:$PATH"
}

teardown() { rm -rf "$TMP"; }

@test "approve --auto-accept on cross-repo exits 3 (blocked)" {
  cd "$TMP"
  run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --auto-accept
  [ "$status" -eq 3 ]
  [[ "$output" =~ "manual" || "$output" =~ "Hub" ]]
}

@test "approve --manual --hub-issue on cross-repo requires interactive input" {
  cd "$TMP"
  # Run without stdin pipe - script will read from /dev/null
  run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --manual --hub-issue "fake-org/rdd-hub#42" < /dev/null
  # Exit should NOT be 3 (cross-repo blocked)
  # status 4 = missing human username (ADR-0031 exit code)
  # status 1 = missing proposal-approved.md (expected in isolated test env)
  # status 0 = success
  [ "$status" -ne 3 ]
}

@test "approve non-cross-repo with --auto-accept still works" {
  cd "$TMP"
  cat > "$TMP/.rddf/improvements/test-cross-repo.md" <<'EOF'
# test-cross-repo

**优先级**: P1 | **来源**: test
**阶段**: v2.1.x | **分类**: core | **类型**: feature
EOF
  # Should succeed (or fail on Hub fetch if --hub-issue required, but exit != 3)
  run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --auto-accept
  [ "$status" -ne 3 ]
}

@test "design-done gate blocks when cross-repo proposal lacks audit log" {
  cd "$TMP"
  # No audit log entry exists
  run env RDDF_PROJECT_ROOT="$TMP" STRICT_DESIGN_GATE=yes python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from skills.guide_design.scripts.design_done_gate import check_cross_repo_approvals
result = check_cross_repo_approvals()
sys.exit(1 if result else 0)
"
  [ "$status" -ne 0 ]
}

# --- ADR-0031 substantiation (5 new cases) ---

@test "fail-open defense: --auto-accept blocked without change dir (improvements SSOT)" {
  cd "$TMP"
  # roadmap-meta.yaml does NOT exist on first approve — detection must use
  # .rddf/improvements/<name>.md only.
  rm -rf "$TMP/openspec/changes/test-cross-repo"
  run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --auto-accept
  [ "$status" -eq 3 ]
}

@test "username forced: empty stdin exits 4" {
  cd "$TMP"
  run bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --manual --hub-issue "fake-org/rdd-hub#42" < /dev/null
  [ "$status" -eq 4 ]
}

@test "RDDF_REQUIRE_HUB_APPROVAL=yes without approved label exits 5" {
  cd "$TMP"
  run env GH_STUB_MODE=no-label RDDF_REQUIRE_HUB_APPROVAL=yes RDDF_APPROVE_ACTOR=alice \
    bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --manual --hub-issue "fake-org/rdd-hub#42"
  [ "$status" -eq 5 ]
}

@test "hub re-fetch: closed issue exits 6; network error warns but proceeds" {
  cd "$TMP"
  run env GH_STUB_MODE=closed RDDF_APPROVE_ACTOR=alice \
    bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --manual --hub-issue "fake-org/rdd-hub#42"
  [ "$status" -eq 6 ]

  run env GH_STUB_MODE=network RDDF_APPROVE_ACTOR=alice \
    bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --manual --hub-issue "fake-org/rdd-hub#42"
  [ "$status" -ne 6 ]
  [ "$status" -ne 5 ]
  [[ "$output" =~ "⚠" || "$output" =~ "warning" || "$output" =~ "WARNING" ]]
}

@test "audit write: accept appends entry with actor/hub_state/hub_labels/decision" {
  cd "$TMP"
  git init -q .
  cat > "$TMP/proposal-approved.md" <<'EOF'
# Approved

| 提案 | 优先级 | 日期 | 来源 |
|------|--------|------|------|

## 已实施

| 提案 | 优先级 | 日期 | 来源 |
|------|--------|------|------|
EOF
  run env GH_STUB_MODE=approved RDDF_APPROVE_ACTOR=alice SKIP_DESIGN_HANDOFF=yes \
    SKIP_CONTENT_REVIEW=yes \
    bash "$REPO_ROOT/skills/guide-design/scripts/approve_proposal.sh" \
    test-cross-repo --manual --hub-issue "fake-org/rdd-hub#42"
  [ "$status" -eq 0 ]
  local audit="$TMP/.rddf/state/.cross-repo-audit.jsonl"
  [ -f "$audit" ]
  grep -q '"actor": "alice"' "$audit"
  grep -q '"decision": "approve"' "$audit"
  grep -q '"hub_state": "OPEN"' "$audit"
  grep -q '"hub_labels":' "$audit"
  grep -q '"proposal_name": "test-cross-repo"' "$audit"
}
