# skills/_lib/state.sh
# Safe JSON/YAML parsing helpers (P2-3 prerequisite).
# Wraps python3 invocations with try/except to avoid hard failures on malformed
# or missing files — callers always get a string back.
#
# Usage:
#   source skills/_lib/state.sh
#   val=$(safe_python_json "/path/to/state.json" ".current.change")
#   val=$(safe_python_yaml "/path/to/state.yaml")

# safe_python_json <file> <jq_expr>
#   Returns jq result, or "unknown" on error
#   Wraps json.load(open(file)) with try/except and dotted-path lookup.
#   Examples:
#     safe_python_json "/tmp/x.json"          # prints whole document (as repr-ish)
#     safe_python_json "/tmp/x.json" ".foo"   # prints data["foo"]
safe_python_json() {
  local file="${1:-}"
  local jq_expr="${2:-.}"
  [[ ! -f "$file" ]] && { echo "unknown"; return 0; }
  python3 -c "
import json, sys
try:
    with open('$file') as f:
        data = json.load(f)
    result = data
    for key in '$jq_expr'.lstrip('.').split('.'):
        if key and isinstance(result, dict):
            result = result.get(key, 'unknown')
    print(result)
except (FileNotFoundError, json.JSONDecodeError, AttributeError) as e:
    print('unknown')
" 2>/dev/null || echo "unknown"
}

# safe_python_yaml <file>
#   Returns parsed YAML, or empty on error
#   Gracefully degrades when PyYAML is missing (ImportError -> empty string).
safe_python_yaml() {
  local file="${1:-}"
  [[ ! -f "$file" ]] && { echo ""; return 0; }
  python3 -c "
import yaml, sys
try:
    with open('$file') as f:
        data = yaml.safe_load(f)
    print(data if data is not None else '')
except (FileNotFoundError, yaml.YAMLError, ImportError) as e:
    print('')
" 2>/dev/null || echo ""
}
