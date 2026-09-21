#!/usr/bin/env bats
# tests/unit/test_layer0_template_sso.bats
# Verify rendered Layer 0 block matches the SSOT template.

load ../test_helper

bats_require_minimum_version 1.5.0

setup() {
  export TMPDIR="/tmp/rddf-ssot-$$"
  mkdir -p "$TMPDIR"
}

teardown() {
  rm -rf "$TMPDIR" 2>/dev/null || true
}

@test "layer0-ssot: deployed block matches template content" {
  # Get the RDD-WORKFLOW-CORE-USAGE-START..END block from the SSOT template
  local template_block
  template_block=$(sed -n '/RDD-WORKFLOW-CORE-USAGE-START/,/RDD-WORKFLOW-CORE-USAGE-END/p' \
    "$REPO_ROOT/_lib/templates/layer0_rdd_workflow_usage.md")
  [ -n "$template_block" ] || skip "template not found"

  # Deploy block to test project
  python3 -m _lib.cli setup ai-context --yes --target "$TMPDIR"

  # Get deployed block from AGENTS.md
  local deployed_block
  deployed_block=$(sed -n '/RDD-WORKFLOW-CORE-USAGE-START/,/RDD-WORKFLOW-CORE-USAGE-END/p' \
    "$TMPDIR/AGENTS.md")
  [ -n "$deployed_block" ] || { echo "No deployed block found"; false; }

  # Compare — the template is the canonical source
  [ "$template_block" = "$deployed_block" ] || {
    echo "TEMPLATE:"
    echo "$template_block"
    echo "---"
    echo "DEPLOYED:"
    echo "$deployed_block"
    false
  }
}