#!/usr/bin/env bats
# tests/integration/test_frontmatter_yaml_parse.bats
#
# Regression lock: every SKILL.md frontmatter must parse as valid YAML.
#
# Background: commit fcfc850 (ADR-0048 skill surface, 2026-09-10) shipped
# rdd-planner/SKILL.md with a 2-space-indent on `description:` (under
# `name:`), making `description` invisible to PyYAML. The bug was caught
# by chisuhua/rdd-workflow-e2e external testbed's frontmatter validation.
#
# This test would have caught the bug locally at `make test` time. Use
# `python3 -c "import yaml; yaml.safe_load(open(...).read().split('---',2)[1])"`
# to detect any indentation / structural breakage that PyYAML silently
# ignores (e.g., mapping under scalar).

load ../test_helper

setup() {
  cd "$REPO_ROOT"
}

@test "all SKILL.md: frontmatter parses as valid YAML" {
  local failures=()
  while IFS= read -r -d '' f; do
    if ! python3 -c "
import sys, yaml
content = open('$f').read()
parts = content.split('---', 2)
if len(parts) < 3:
    sys.exit('no frontmatter delimiters')
try:
    data = yaml.safe_load(parts[1])
except yaml.YAMLError as e:
    sys.exit(f'YAML parse error: {e}')
if not isinstance(data, dict):
    sys.exit('frontmatter is not a mapping')
for required in ('name', 'description', 'license'):
    if required not in data:
        sys.exit(f'missing required field: {required}')
sys.exit(0)
" 2>/dev/null; then
      failures+=("$f")
    fi
  done < <(find skills -name SKILL.md -print0)
  if [ "${#failures[@]}" -gt 0 ]; then
    printf 'FAIL: frontmatter YAML parse error in:\n'
    printf '  %s\n' "${failures[@]}"
    return 1
  fi
}

@test "all SKILL.md: description is non-empty (catches silent indent bugs)" {
  # Even if YAML parses, an indentation bug can cause required fields to
  # vanish silently (PyYAML treats nested mapping under string field as
  # parse error, but some tools may still extract partial data).
  # This test guarantees the parsed `description` is truthy.
  local failures=()
  while IFS= read -r -d '' f; do
    local desc
    desc=$(python3 -c "
import sys, yaml
content = open('$f').read()
parts = content.split('---', 2)
if len(parts) < 3:
    sys.exit(1)
data = yaml.safe_load(parts[1]) or {}
desc = data.get('description') or ''
if not desc.strip():
    sys.exit(2)
sys.stdout.write(desc[:60])
" 2>/dev/null)
    if [ -z "$desc" ]; then
      failures+=("$f")
    fi
  done < <(find skills -name SKILL.md -print0)
  if [ "${#failures[@]}" -gt 0 ]; then
    printf 'FAIL: empty/missing description in:\n'
    printf '  %s\n' "${failures[@]}"
    return 1
  fi
}