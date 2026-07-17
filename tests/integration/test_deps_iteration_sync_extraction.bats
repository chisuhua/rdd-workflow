#!/usr/bin/env bats
# tests/integration/test_deps_iteration_sync_extraction.bats
# P3-4d: deps.md Step 6 was a 97-line inline PYEOF heredoc that did 4 things:
#   1. Read deps-analysis.json (preferred) or parse .deps-output.md fallback
#   2. Write deps-analysis.json (always — refresh updated_at)
#   3. Sync iteration.json from deps-analysis.json
#   4. Print status messages
# Extracted to _lib/deps_iteration_sync.sh as 1 bash function
# `deps_iteration_sync` that delegates to deps_output.py + iteration.py.
#
# These tests lock:
#   1. Helper exists with deps_iteration_sync function
#   2. deps.md no longer inlines the 97-line PYEOF heredoc
#   3. Runtime: deps-analysis.json present -> JSON path used
#   4. Runtime: deps-analysis.json missing -> markdown fallback parses
#   5. Runtime: both deps-analysis.json AND iteration.json updated

load ../test_helper

@test "skills/_lib/deps_iteration_sync.sh exists with deps_iteration_sync function" {
  [ -f "$REPO_ROOT/skills/_lib/deps_iteration_sync.sh" ]
  grep -q '^deps_iteration_sync()' "$REPO_ROOT/skills/_lib/deps_iteration_sync.sh"
}

@test "deps.md Step 6 no longer inlines the 97-line PYEOF heredoc" {
  [ -f "$REPO_ROOT/skills/deps/SKILL.md" ]
  # Original heredoc had this exact regex pattern; after extraction, gone.
  ! grep -qE '## Change 状态表.*status_table = re\.search' "$REPO_ROOT/skills/deps/SKILL.md"
}

@test "deps.md Step 6 invokes deps_iteration_sync helper" {
  [ -f "$REPO_ROOT/skills/deps/SKILL.md" ]
  grep -q '_lib/deps_iteration_sync.sh' "$REPO_ROOT/skills/deps/SKILL.md"
  grep -q 'deps_iteration_sync' "$REPO_ROOT/skills/deps/SKILL.md"
}

@test "deps_iteration_sync: skips gracefully when .deps-output.md missing" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  source "$REPO_ROOT/skills/_lib/deps_iteration_sync.sh"
  output=$(deps_iteration_sync 2>&1 || true)
  echo "$output" | grep -qE '跳过|skip'
  # No deps-analysis.json should be created
  [ ! -f .rddf/state/deps-analysis.json ]
  rm -rf "$TEST_REPO"
}

@test "deps_iteration_sync: uses deps-analysis.json when present" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  mkdir -p .rddf/state
  # Pre-create deps-analysis.json with one change
  python3 -c "
import sys
sys.path.insert(0, '$TEST_REPO')
from skills._lib.deps_output import build_analysis, write_analysis
analysis = build_analysis([{'name': 'c1', 'blocker': None, 'parallel_group': 0, 'conflicts': []}])
write_analysis('$TEST_REPO', analysis)
print('pre-analysis written')
"
  # Create iteration.json so sync has something to update
  python3 -c "
import sys
sys.path.insert(0, '$TEST_REPO')
from skills._lib import iteration as it
it.save('$TEST_REPO', it.create_empty())
"
  source "$REPO_ROOT/skills/_lib/deps_iteration_sync.sh"
  deps_iteration_sync 2>&1
  # iteration.json should have c1 entry now
  python3 -c "
import json
with open('.rddf/state/iteration.json') as f:
    data = json.load(f)
changes = [c for c in data['changes'] if c['name'] == 'c1']
assert len(changes) >= 1, f'Expected c1 in iteration.json, got: {data[\"changes\"]}'
print('OK')
"
  rm -rf "$TEST_REPO"
}

@test "deps_iteration_sync: falls back to markdown when deps-analysis.json missing" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  mkdir -p .rddf/state
  # Write .deps-output.md with one change (no deps-analysis.json yet)
  cat > .rddf/state/.deps-output.md <<'EOF'
# Deps Report

## Change 状态表

| Change | Status | Blocker | Parallel Group | Conflicts |
|--------|--------|---------|----------------|-----------|
| c1 | ready | — | 0 | — |
EOF
  # Empty iteration.json
  python3 -c "
import sys
sys.path.insert(0, '$TEST_REPO')
from skills._lib import iteration as it
it.save('$TEST_REPO', it.create_empty())
"
  source "$REPO_ROOT/skills/_lib/deps_iteration_sync.sh"
  deps_iteration_sync 2>&1
  # deps-analysis.json should now exist (created from markdown fallback)
  [ -f .rddf/state/deps-analysis.json ]
  python3 -c "
import json
with open('.rddf/state/deps-analysis.json') as f:
    data = json.load(f)
assert 'c1' in data['changes'], f'Expected c1 in changes, got: {list(data[\"changes\"].keys())}'
assert data['changes']['c1']['confidence'] == 'low', 'Expected low confidence (markdown fallback)'
assert data.get('fallback') is True, 'Expected fallback=True marker'
print('OK')
"
  rm -rf "$TEST_REPO"
}

@test "deps_iteration_sync: updates iteration.json deps fields" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  mkdir -p .rddf/state
  # Pre-create deps-analysis.json with c1 blocker c2
  python3 -c "
import sys
sys.path.insert(0, '$TEST_REPO')
from skills._lib.deps_output import build_analysis, write_analysis
analysis = build_analysis([
    {'name': 'c1', 'blocker': 'c2', 'parallel_group': 1, 'conflicts': []},
    {'name': 'c2', 'blocker': None, 'parallel_group': 0, 'conflicts': []},
])
write_analysis('$TEST_REPO', analysis)
"
  python3 -c "
import sys
sys.path.insert(0, '$TEST_REPO')
from skills._lib import iteration as it
it.save('$TEST_REPO', it.create_empty())
"
  source "$REPO_ROOT/skills/_lib/deps_iteration_sync.sh"
  deps_iteration_sync 2>&1
  python3 -c "
import json
with open('.rddf/state/iteration.json') as f:
    data = json.load(f)
by_name = {c['name']: c for c in data['changes']}
assert by_name['c1']['blocker'] == 'c2', f'c1 blocker: {by_name[\"c1\"][\"blocker\"]}'
assert by_name['c1']['parallel_group'] == 1, f'c1 group: {by_name[\"c1\"][\"parallel_group\"]}'
assert by_name['c2']['blocker'] is None, f'c2 blocker: {by_name[\"c2\"][\"blocker\"]}'
print('OK')
"
  rm -rf "$TEST_REPO"
}

@test "deps_iteration_sync: prints source label (JSON or MARKDOWN-FALLBACK)" {
  TEST_REPO=$(mktemp -d)
  cd "$TEST_REPO"
  ln -s "$REPO_ROOT/skills" "$TEST_REPO/skills"
  export PROJECT_ROOT="$TEST_REPO"
  mkdir -p .rddf/state
  # Set up scenario A: deps-analysis.json present
  python3 -c "
import sys
sys.path.insert(0, '$TEST_REPO')
from skills._lib.deps_output import build_analysis, write_analysis
write_analysis('$TEST_REPO', build_analysis([{'name': 'c1'}]))
from skills._lib import iteration as it
it.save('$TEST_REPO', it.create_empty())
"
  source "$REPO_ROOT/skills/_lib/deps_iteration_sync.sh"
  output=$(deps_iteration_sync 2>&1)
  echo "$output" | grep -qE '来源: JSON|JSON'
  rm -rf "$TEST_REPO"
}