#!/usr/bin/env bats
# tests/integration/test_layer0_sentinel_order.bats
# Verify Hub sentinel and Layer 0 sentinel coexist stably.

load ../test_helper

bats_require_minimum_version 1.5.0

setup() {
  export TMPDIR="/tmp/rddf-sentinel-$$"
  mkdir -p "$TMPDIR"
  # Create a .cursorrules with just a Hub sentinel (spoke-style)
  cat > "$TMPDIR/.cursorrules" << 'EOF'
some existing config

<!-- RDD-HUB-PROTOCOL-START -->
Hub protocol block content
<!-- RDD-HUB-PROTOCOL-END -->

more existing config
EOF
}

teardown() {
  rm -rf "$TMPDIR" 2>/dev/null || true
}

@test "sentinel-order: Layer 0 does not disrupt existing Hub sentinel" {
  cd "$TMPDIR"
  # Deploy Layer 0
  python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"
  # Both sentinels should be present
  grep -q "RDD-HUB-PROTOCOL-START" "$TMPDIR/.cursorrules"
  grep -q "RDD-WORKFLOW-CORE-USAGE-START" "$TMPDIR/.cursorrules"
  # The order should be deterministic: original content first
  run grep -n "RDD-HUB-PROTOCOL-START\|RDD-WORKFLOW-CORE-USAGE-START" "$TMPDIR/.cursorrules"
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 2 ]
}

@test "sentinel-order: repeated setup does not move Hub block" {
  cd "$TMPDIR"
  python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"
  # Record Hub block position
  local hub_line1
  hub_line1=$(grep -n "RDD-HUB-PROTOCOL-START" "$TMPDIR/.cursorrules" | cut -d: -f1)
  # Run setup again
  python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"
  # Hub block should still be in same position
  local hub_line2
  hub_line2=$(grep -n "RDD-HUB-PROTOCOL-START" "$TMPDIR/.cursorrules" | cut -d: -f1)
  [ "$hub_line1" = "$hub_line2" ]
}

@test "sentinel-order: uninstall removes only Layer 0 block" {
  cd "$TMPDIR"
  python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"
  grep -q "RDD-HUB-PROTOCOL-START" "$TMPDIR/.cursorrules"
  grep -q "RDD-WORKFLOW-CORE-USAGE-START" "$TMPDIR/.cursorrules"
  python3 -m _lib.cli setup ai-context --uninstall --yes --target "$TMPDIR"
  # Hub sentinel should remain
  grep -q "RDD-HUB-PROTOCOL-START" "$TMPDIR/.cursorrules"
  # Layer 0 sentinel should be gone
  run grep -c "RDD-WORKFLOW-CORE-USAGE-START" "$TMPDIR/.cursorrules"
  [ "$output" -eq 0 ]
}