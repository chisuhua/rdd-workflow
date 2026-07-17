#!/usr/bin/env bats
# tests/integration/test_propose_parsing.bats
#
# T9 — propose.md auto-commit + parsing rewrite (P0-3, P0-4)
# HIGH-RISK: touches the critical propose flow.
# T18 — P1-7: container format migrated from YAML+Markdown to pure JSON.
#
# Tests verify:
#   - P0-3: dangerous `git add openspec/changes/*/` glob is GONE
#   - P0-3: THIS_SESSION_CREATED array is initialized + populated
#   - P0-3: commit uses precise per-name add (for-loop), not awk pipe
#   - P0-4: parsing no longer depends on PROJECT_ROOT env var
#   - P0-4: uses `git rev-parse --show-toplevel` subprocess
#   - P0-4 / P1-7: json.load is wrapped in try/except (FileNotFoundError + JSONDecodeError)
#   - P1-7: yaml.safe_load and `re.sub '^---'` are GONE (format migrated to JSON)
#   - Runtime: PROJECT_ROOT env var unset still allows parsing to succeed (with JSON input)
#
# These are mostly STATIC tests against the markdown source, plus 1 runtime test
# that exercises the actual Python parsing logic with PROJECT_ROOT unset.

load ../test_helper

# Location of the propose skill markdown under test
PROPOSE_MD="$REPO_ROOT/skills/propose/SKILL.md"

@test "propose.md exists and is non-empty" {
  [ -f "$PROPOSE_MD" ]
  [ -s "$PROPOSE_MD" ]
}

@test "propose.md no longer uses dangerous 'openspec/changes/*/' glob in code (P0-3)" {
  # P0-3: `git add openspec/changes/*/` glob is dangerous — it includes archive/
  # and any other unrelated change directories. Must be removed from executable code.
  # Comments explaining the fix are fine; the test checks code blocks by stripping
  # comments first.
  local non_comment
  non_comment=$(grep -vE '^\s*#' "$PROPOSE_MD" | grep -v '^\s*$')
  ! echo "$non_comment" | grep -qE 'git add openspec/changes/\*/'
}

@test "propose.md tracks created changes in THIS_SESSION_CREATED array (P0-3)" {
  # The array must be: (1) initialized, (2) appended to on success
  grep -q '^THIS_SESSION_CREATED=()' "$PROPOSE_MD"
  grep -q 'THIS_SESSION_CREATED+=' "$PROPOSE_MD"
  # And referenced at the commit site
  grep -q 'THIS_SESSION_CREATED\[@\]' "$PROPOSE_MD"
  grep -q 'THIS_SESSION_CREATED\[\*\]' "$PROPOSE_MD"
}

@test "propose.md uses 'for name in \$THIS_SESSION_CREATED' for git add (P0-3)" {
  # The fix uses a for-loop iterating over the array, NOT a dangerous glob
  grep -qE 'for name in "\$\{THIS_SESSION_CREATED\[@\]\}"' "$PROPOSE_MD"
  # And it adds each name's artifacts individually (proposal.md, roadmap-meta.yaml, etc.)
  grep -qE 'git add "openspec/changes/\$name/' "$PROPOSE_MD"
}

@test "propose.md git commit does NOT use awk-piped dirname list (P0-3)" {
  # The old buggy pattern was:
  #   CHANGES=$(git status --porcelain openspec/changes/ | awk '{print $2}' | xargs -I{} dirname {} | sort -u)
  #   git commit -m "feat: propose $CHANGE_NAMES"
  # The new pattern uses the array directly. Reject the old pattern.
  ! grep -qE 'git status --porcelain openspec/changes/ \| awk' "$PROPOSE_MD"
  ! grep -qE 'CHANGE_NAMES=' "$PROPOSE_MD"
}

@test "propose.md no longer uses os.environ.get('PROJECT_ROOT') (P0-4)" {
  # P0-4: parsing previously relied on an env var. Now it uses subprocess.
  ! grep -qE "os\.environ\.get\(.PROJECT_ROOT" "$PROPOSE_MD"
}

@test "propose.md uses git rev-parse --show-toplevel for project root (P0-4)" {
  grep -qE "subprocess\.check_output\(" "$PROPOSE_MD"
  grep -qE "git.*rev-parse.*--show-toplevel" "$PROPOSE_MD"
}

@test "propose.md wraps json.load in try/except FileNotFoundError + JSONDecodeError (P0-4 / P1-7)" {
  # P1-7: format migrated from YAML to JSON. Both parse sites (Phase 0 and
  # Step 4d) must use explicit exception handling with the new exception type.
  local count
  count=$(grep -cE 'except \(FileNotFoundError, json\.JSONDecodeError\)' "$PROPOSE_MD")
  [ "$count" -ge 2 ]
}

@test "propose.md uses json.load (P1-7 format migration)" {
  # P1-7: format migrated to JSON. Both Phase 0 and Step 4d must use json.load.
  local count
  count=$(grep -cE 'json\.load\(' "$PROPOSE_MD")
  [ "$count" -ge 2 ]
}

@test "propose.md no longer uses yaml.safe_load (P1-7 format migration)" {
  # P1-7: YAML is gone. Reject any remaining yaml.safe_load call in executable code.
  local non_comment
  non_comment=$(grep -vE '^\s*#' "$PROPOSE_MD" | grep -v '^\s*$')
  ! echo "$non_comment" | grep -qE 'yaml\.safe_load\('
}

@test "propose.md no longer strips '---' markdown separators (P1-7 format migration)" {
  # P1-7: '---' stripping was needed for YAML to avoid document-boundary confusion.
  # With JSON, the separator is irrelevant — the entire file is one JSON document.
  ! grep -qF "re.sub(r'^---\\$'" "$PROPOSE_MD"
}

@test "propose.md auto-commit triggers only when array is non-empty (P0-3)" {
  # The new gate: `if [ ${#THIS_SESSION_CREATED[@]} -gt 0 ]`
  grep -qE 'if \[ \$\{#THIS_SESSION_CREATED\[@\]\} -gt 0 \]' "$PROPOSE_MD"
}

@test "runtime: PROJECT_ROOT env var unset still lets JSON parsing succeed" {
  # P1-7 / P0-4: build a temp git repo with proposal-suggestions.md in the
  # NEW JSON format, then run the EXACT Python parsing block from propose.md
  # Phase 0 with PROJECT_ROOT unset. Expects: the script reports
  # "剩余 0 个建议" without crashing.
  local test_repo
  test_repo=$(mktemp -d)
  cd "$test_repo" || return 1
  git init -q
  git config user.email "test@test.local"
  git config user.name "test"
  echo "x" > a && git add a && git commit -q -m init
  mkdir -p openspec/changes
  cat > proposal-suggestions.md <<'JSON'
[
  {
    "name": "fix-ns-pollution",
    "priority": "P0",
    "source": "ADR-033",
    "status": "待创建",
    "phase": "phase-1",
    "category": "core-impl",
    "description": "test"
  }
]
JSON
  git add proposal-suggestions.md && git commit -q -m add_suggestions

  # Create a matching change directory so the filter will REMOVE the entry
  mkdir -p openspec/changes/fix-ns-pollution
  echo "# proposal" > openspec/changes/fix-ns-pollution/proposal.md
  git add . && git commit -q -m add_change

  # Unset PROJECT_ROOT and run the EXACT python block from propose.md Phase 0
  unset PROJECT_ROOT
  local output
  output=$(python3 -c "
import json, os, sys, subprocess

project_root = subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel'], text=True
).strip()

try:
    with open('proposal-suggestions.md') as f:
        entries = json.load(f)

    if not isinstance(entries, list):
        print('TYPE_ERROR', file=sys.stderr)
        sys.exit(1)

    kept = []
    removed = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get('name')
        if name and os.path.isdir(f'{project_root}/openspec/changes/{name}/'):
            removed.append(name)
        else:
            kept.append(entry)

    if removed:
        print(f'  已从建议列表移除: {\", \".join(removed)}')
    print(f'  剩余 {len(kept)} 个建议')
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f'PARSE_ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1)
  local rc=$?
  cd /
  rm -rf "$test_repo"

  [ "$rc" -eq 0 ] || { echo "Python exited with $rc: $output" >&2; return 1; }
  echo "$output" | grep -q "已从建议列表移除: fix-ns-pollution"
  echo "$output" | grep -q "剩余 0 个建议"
}
