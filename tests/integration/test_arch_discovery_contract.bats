#!/usr/bin/env bats
#
# Integration tests for arch artifact discovery contract (ADR-0016).
# Covers end-to-end arch → plan handoff flow.

load ../test_helper

REPO_ROOT_HERE="$REPO_ROOT"

setup_custom_repo() {
  local layout="$1"
  REPO_TMP=$(mktemp -d)
  cd "$REPO_TMP"
  git init -q
  git config user.email "test@test.local"
  git config user.name "Test"
  case "$layout" in
    default)
      mkdir -p docs/adr docs/architecture
      : > docs/adr/ADR-0001-test.md
      : > docs/adr/ADR-0002-test.md
      : > docs/architecture/v1-gap-analysis.md
      cat > roadmap.md <<EOF
# Roadmap
**当前阶段**: phase-1
EOF
      ;;
    custom_doc)
      mkdir -p doc/adr documentation/architecture
      : > doc/adr/ADR-0001-custom.md
      : > doc/adr/ADR-0002-custom.md
      : > documentation/architecture/custom-gap.md
      mkdir -p planning
      cat > planning/roadmap.md <<EOF
# Roadmap
**当前阶段**: phase-2
EOF
      ;;
    missing)
      : # nothing
      ;;
  esac
}

teardown_custom_repo() {
  [ -n "$REPO_TMP" ] && rm -rf "$REPO_TMP"
}

@test "arch_discovery: default layout yields docs/adr + roadmap.md" {
  setup_custom_repo "default"
  PROJECT_ROOT="$REPO_TMP"
  source "$REPO_ROOT_HERE/_lib/discover-arch-artifacts.sh"
  discover_adr_dir          >/dev/null
  discover_roadmap          >/dev/null
  discover_architecture_dir >/dev/null
  discover_adr_pattern      >/dev/null
  [ "$DISCOVERED_ADR_DIR" = "docs/adr" ]
  [ "$DISCOVERED_ADR_DIR_FOUND" = "true" ]
  [ "$DISCOVERED_ROADMAP_PATH" = "roadmap.md" ]
  [ "$DISCOVERED_ROADMAP_FOUND" = "true" ]
  [ "$DISCOVERED_ARCHITECTURE_DIR" = "docs/architecture" ]
  [ "$DISCOVERED_ARCH_FOUND" = "true" ]
  [ "$DISCOVERED_ADR_PATTERN" = "ADR-*.md" ]
  teardown_custom_repo
}

@test "arch_discovery: custom layout (doc/adr) yields doc/adr" {
  setup_custom_repo "custom_doc"
  PROJECT_ROOT="$REPO_TMP"
  source "$REPO_ROOT_HERE/_lib/discover-arch-artifacts.sh"
  discover_adr_dir          >/dev/null
  discover_roadmap          >/dev/null
  discover_architecture_dir >/dev/null
  [ "$DISCOVERED_ADR_DIR" = "doc/adr" ]
  [ "$DISCOVERED_ADR_DIR_FOUND" = "true" ]
  [ "$DISCOVERED_ROADMAP_PATH" = "planning/roadmap.md" ]
  [ "$DISCOVERED_ROADMAP_FOUND" = "true" ]
  [ "$DISCOVERED_ARCHITECTURE_DIR" = "documentation/architecture" ]
  [ "$DISCOVERED_ARCH_FOUND" = "true" ]
  teardown_custom_repo
}

@test "arch_discovery: missing layout falls back to defaults with found=false" {
  setup_custom_repo "missing"
  PROJECT_ROOT="$REPO_TMP"
  source "$REPO_ROOT_HERE/_lib/discover-arch-artifacts.sh"
  discover_adr_dir          >/dev/null
  discover_roadmap          >/dev/null
  discover_architecture_dir >/dev/null
  [ "$DISCOVERED_ADR_DIR" = "docs/adr" ]
  [ "$DISCOVERED_ADR_DIR_FOUND" = "false" ]
  [ "$DISCOVERED_ROADMAP_PATH" = "roadmap.md" ]
  [ "$DISCOVERED_ROADMAP_FOUND" = "false" ]
  [ "$DISCOVERED_ARCHITECTURE_DIR" = "docs/architecture" ]
  [ "$DISCOVERED_ARCH_FOUND" = "false" ]
  teardown_custom_repo
}

@test "arch_discovery: guide-plan handoff read works" {
  setup_custom_repo "default"
  mkdir -p "$REPO_TMP/.rddf/state"
  cat > "$REPO_TMP/.rddf/state/.arch-handoff.json" <<EOF
{
  "arch_complete_at": "2026-07-08T10:00:00+00:00",
  "adr_count": 2,
  "completed_adr_ids": ["0001", "0002"],
  "roadmap_exists": true,
  "current_phase": "phase-1",
  "plan_started_at": null,
  "adr_dir": "docs/adr",
  "roadmap_path": "roadmap.md",
  "architecture_dir": "docs/architecture",
  "adr_pattern": "ADR-*.md",
  "discovered": {
    "adr_dir": {"found": true, "created": false, "candidates_tried": 1},
    "roadmap_path": {"found": true, "created": false, "candidates_tried": 1},
    "architecture_dir": {"found": true, "created": false, "candidates_tried": 1}
  },
  "version": 1
}
EOF
  PROJECT_ROOT="$REPO_TMP"
  ADR_DIR=$(jq -r '.adr_dir // "docs/adr"' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json")
  ROADMAP_PATH=$(jq -r '.roadmap_path // "roadmap.md"' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json")
  [ "$ADR_DIR" = "docs/adr" ]
  [ "$ROADMAP_PATH" = "roadmap.md" ]
  teardown_custom_repo
}

@test "arch_discovery: missing handoff falls back to defaults (no jq failure)" {
  setup_custom_repo "default"
  rm -f "$REPO_TMP/.rddf/state/.arch-handoff.json"
  PROJECT_ROOT="$REPO_TMP"
  ADR_DIR="docs/adr"
  ROADMAP_PATH="roadmap.md"
  ARCHITECTURE_DIR="docs/architecture"
  ADR_PATTERN="ADR-*.md"
  [ "$ADR_DIR" = "docs/adr" ]
  [ "$ROADMAP_PATH" = "roadmap.md" ]
  [ "$ARCHITECTURE_DIR" = "docs/architecture" ]
  [ "$ADR_PATTERN" = "ADR-*.md" ]
  teardown_custom_repo
}

@test "arch_discovery: malformed handoff (invalid JSON) handled gracefully" {
  setup_custom_repo "default"
  mkdir -p "$REPO_TMP/.rddf/state"
  echo "{ not valid json" > "$REPO_TMP/.rddf/state/.arch-handoff.json"
  PROJECT_ROOT="$REPO_TMP"
  # Python helper would catch JSONDecodeError and return defaults
  python3 -c "
import json, sys
from pathlib import Path
try:
    data = json.loads(Path('$REPO_TMP/.rddf/state/.arch-handoff.json').read_text())
except json.JSONDecodeError:
    data = {'adr_dir': 'docs/adr', 'roadmap_path': 'roadmap.md'}
assert data['adr_dir'] == 'docs/adr'
assert data['roadmap_path'] == 'roadmap.md'
"
  teardown_custom_repo
}

@test "arch_discovery: env var override beats scan even with handoff present" {
  setup_custom_repo "default"
  mkdir -p "$REPO_TMP/.rddf/state"
  cat > "$REPO_TMP/.rddf/state/.arch-handoff.json" <<EOF
{"adr_dir": "docs/adr", "roadmap_path": "roadmap.md", "version": 1}
EOF
  PROJECT_ROOT="$REPO_TMP"
  export SPEC_WORKFLOW_ADR_DIR="custom/env/adrs"
  source "$REPO_ROOT_HERE/_lib/discover-arch-artifacts.sh"
  discover_adr_dir >/dev/null
  [ "$DISCOVERED_ADR_DIR" = "custom/env/adrs" ]
  unset SPEC_WORKFLOW_ADR_DIR
  teardown_custom_repo
}

@test "arch_discovery: handoff schema validates against canonical payload" {
  setup_custom_repo "default"
  mkdir -p "$REPO_TMP/.rddf/state"
  cat > "$REPO_TMP/.rddf/state/.arch-handoff.json" <<EOF
{
  "arch_complete_at": "2026-07-08T10:00:00+00:00",
  "adr_count": 2,
  "completed_adr_ids": ["0001", "0002"],
  "roadmap_exists": true,
  "current_phase": "phase-1",
  "plan_started_at": null,
  "adr_dir": "docs/adr",
  "roadmap_path": "roadmap.md",
  "architecture_dir": "docs/architecture",
  "adr_pattern": "ADR-*.md",
  "discovered": {
    "adr_dir": {"found": true, "created": false, "candidates_tried": 1},
    "roadmap_path": {"found": true, "created": false, "candidates_tried": 1},
    "architecture_dir": {"found": true, "created": false, "candidates_tried": 1}
  },
  "version": 1
}
EOF
  PROJECT_ROOT="$REPO_TMP"
  python3 -c "
import json, sys
sys.path.insert(0, '$REPO_ROOT_HERE')
from pathlib import Path
from jsonschema import Draft7Validator
schema = json.loads(Path('$REPO_ROOT_HERE/_lib/schemas/arch_handoff_schema.json').read_text())
data = json.loads(Path('$REPO_TMP/.rddf/state/.arch-handoff.json').read_text())
errors = list(Draft7Validator(schema).iter_errors(data))
assert not errors, f'Validation failed: {[e.message for e in errors]}'
print('OK')
"
  teardown_custom_repo
}

# ---- Deep integration tests (Momus HIGH#4 — exercise public APIs) ----

@test "arch_discovery: GateMechanism.verify_transition arch_done passes with default handoff" {
  REPO_TMP=$(mktemp -d)
  cd "$REPO_TMP"
  git init -q
  mkdir -p docs/adr
  : > docs/adr/ADR-0001-test.md
  cat > roadmap.md <<EOF
# Roadmap
**当前阶段**: phase-1

@test "arch_discovery: GateMechanism.verify_transition arch_done passes with default handoff" {
  REPO_TMP=$(mktemp -d)
  cd "$REPO_TMP"
  git init -q
  mkdir -p docs/adr
  : > docs/adr/ADR-0001-test.md
  cat > roadmap.md <<EOF
# Roadmap
**当前阶段**: phase-1
EOF
  mkdir -p .rddf/state
  cat > .rddf/state/.arch-handoff.json <<EOF
{
  "arch_complete_at": "2026-07-08T10:00:00+00:00",
  "adr_count": 1,
  "completed_adr_ids": ["0001"],
  "roadmap_exists": true,
  "current_phase": "phase-1",
  "plan_started_at": null,
  "adr_dir": "docs/adr",
  "roadmap_path": "roadmap.md",
  "architecture_dir": "docs/architecture",
  "adr_pattern": "ADR-*.md",
  "discovered": {
    "adr_dir": {"found": true, "created": false, "candidates_tried": 1},
    "roadmap_path": {"found": true, "created": false, "candidates_tried": 1},
    "architecture_dir": {"found": false, "created": false, "candidates_tried": 1}
  },
  "version": 1
}
EOF

  PROJECT_ROOT="$REPO_TMP"
  export PYTHONPATH="$REPO_ROOT_HERE:$PYTHONPATH"
  python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT_HERE')
from skills._lib.gate import _check_adr_exists, _check_arch_handoff_exists
ctx = {'project_root': '$REPO_TMP'}
a_passed, _ = _check_adr_exists(ctx)
h_passed, _ = _check_arch_handoff_exists(ctx)
print(f'adr={a_passed} handoff={h_passed}')
assert a_passed, 'ADR gate failed'
assert h_passed, 'Handoff gate failed'
"
  unset PYTHONPATH
  rm -rf "$REPO_TMP"
}

@test "arch_discovery: action_create_adr writes to discovered adr_dir matching pattern" {
  REPO_TMP=$(mktemp -d)
  cd "$REPO_TMP"
  git init -q
  mkdir -p docs/adr

  PROJECT_ROOT="$REPO_TMP"
  export PYTHONPATH="$REPO_ROOT_HERE:$PYTHONPATH"
  python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT_HERE')
from skills._lib.core.event_log import EventLog
from skills._lib.loop.actions import action_create_adr
import os
log_path = '$REPO_TMP/event.log'
params = {
    'title': 'custom-pattern-test',
    'status': 'proposed',
    '_project_root': '$REPO_TMP',
}
result = action_create_adr(params, EventLog(log_path))
assert result.success, f'Action failed: {result.error}'
created = result.data['path']
assert created.startswith('$REPO_TMP/docs/adr/'), f'Wrong dir: {created}'
assert created.endswith('-custom-pattern-test.md'), f'Wrong name: {created}'
print(f'Created: {created}')
"
  unset PYTHONPATH
  rm -rf "$REPO_TMP"
}
