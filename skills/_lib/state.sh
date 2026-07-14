# skills/_lib/state.sh
# Shell helpers for safe JSON/YAML operations via python3.
# Used by propose.md and roadmap.md (and other skills/_lib consumers).
#
# Restored in v2.0.3 (fix-debt-audit-2026-07-14): the prior
# general-harden-doc-consistency change removed these helpers claiming
# "no production callers" — but propose.md and roadmap.md actually
# source this file and call safe_python_json. Restoring the helpers
# preserves the contract that T22 (json.load error handling) introduced.
#
# Contract verified by:
#   - tests/integration/test_json_safety.bats  (safe_python_json)
#   - tests/integration/test_suggestions_format.bats  (read_suggestions / write_suggestions)

# safe_python_json <json_file> <key>
# Reads a key from a JSON file. Returns "unknown" on any failure
# (missing file, malformed JSON, missing key).
safe_python_json() {
  local file="$1"
  local key="$2"
  python3 -c "
import json, sys
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        print('unknown', end='')
        sys.exit(0)
    parts = sys.argv[2].split('.')
    result = data
    for p in parts:
        if isinstance(result, dict):
            result = result.get(p, None)
            if result is None:
                print('unknown', end='')
                sys.exit(0)
        else:
            print('unknown', end='')
            sys.exit(0)
    print(result if isinstance(result, str) else json.dumps(result, ensure_ascii=False), end='')
except (json.JSONDecodeError, OSError, IOError):
    print('unknown', end='')
" "$file" "$key"
}

# safe_python_yaml <yaml_file> <key>
# Reads a key from a YAML file. Returns "unknown" on any failure.
safe_python_yaml() {
  local file="$1"
  local key="$2"
  python3 -c "
import sys
try:
    import yaml
    with open(sys.argv[1]) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        print('unknown', end='')
        sys.exit(0)
    result = data.get(sys.argv[2], None)
    if result is None:
        print('unknown', end='')
    else:
        print(result if isinstance(result, str) else str(result), end='')
except Exception:
    print('unknown', end='')
" "$file" "$key"
}

# read_suggestions [file]
# Reads proposal-suggestions.md (or specified file) as JSON array.
# Returns [] on missing / malformed / legacy format.
read_suggestions() {
  local file="${1:-proposal-suggestions.md}"
  python3 -c "
import json, sys, os
try:
    if not os.path.exists(sys.argv[1]):
        print('[]', end='')
        sys.exit(0)
    with open(sys.argv[1]) as f:
        content = f.read().strip()
    if not content:
        print('[]', end='')
        sys.exit(0)
    try:
        data = json.loads(content)
        if isinstance(data, list):
            print(json.dumps(data, ensure_ascii=False), end='')
        else:
            print('[]', end='')
    except json.JSONDecodeError:
        # Legacy YAML+Markdown format — warn and return []
        import sys as _sys
        print('[]', end='')
except Exception:
    print('[]', end='')
" "$file"
}

# write_suggestions <file> <json>
# Writes a JSON array to proposal-suggestions.md. If existing file is
# in legacy (non-JSON) format, creates .bak backup first. Refuses
# non-JSON input with non-zero exit.
write_suggestions() {
  local file="$1"
  local data="$2"
  python3 -c "
import json, sys, os, shutil
inp = sys.argv[1]
new_data = sys.argv[2]

# Validate JSON
try:
    parsed = json.loads(new_data)
    if not isinstance(parsed, list):
        print('Error: not a JSON array', file=sys.stderr)
        sys.exit(1)
except json.JSONDecodeError as e:
    print(f'Error: invalid JSON: {e}', file=sys.stderr)
    sys.exit(1)

# If existing file is not valid JSON, backup as .bak
if os.path.exists(inp):
    with open(inp) as f:
        existing = f.read().strip()
    if existing:
        try:
            json.loads(existing)
        except json.JSONDecodeError:
            shutil.copy2(inp, inp + '.bak')

with open(inp, 'w') as f:
    json.dump(parsed, f, ensure_ascii=False, indent=2)
    f.write('\n')
" "$file" "$data"
}