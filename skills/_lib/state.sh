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

# read_suggestions [file]
#   Reads proposal-suggestions.md as JSON. Always prints a JSON string.
#   Missing/legacy/malformed files all return "[]" with a stderr warning.
read_suggestions() {
  local file="${1:-proposal-suggestions.md}"
  if [[ ! -f "$file" ]]; then
    echo "[]"
    return 0
  fi
  python3 -c "
import json, sys

path = '$file'
try:
    with open(path) as f:
        raw = f.read()
except (FileNotFoundError, IOError) as e:
    print('[]')
    print(f'⚠️  read_suggestions: file not found: {e}', file=sys.stderr)
    sys.exit(0)

try:
    data = json.loads(raw)
    if not isinstance(data, list):
        print('[]')
        print('⚠️  read_suggestions: top-level value is not a JSON array', file=sys.stderr)
        sys.exit(0)
    print(json.dumps(data, ensure_ascii=False))
    sys.exit(0)
except json.JSONDecodeError:
    pass

if '## 架构依据' in raw or '- name:' in raw:
    print('⚠️  旧格式 proposal-suggestions.md 检测到', file=sys.stderr)
    print('   自动迁移需要手动确认', file=sys.stderr)
    print('   已备份到 ${file}.bak (后续写入时)', file=sys.stderr)
    print('[]')
    sys.exit(0)

print('[]')
print('⚠️  proposal-suggestions.md 不是合法 JSON', file=sys.stderr)
" 2>/dev/null || echo "[]"
}

# write_suggestions <file> <json_data>
#   Writes a JSON list of suggestions to <file>. Backs up to <file>.bak
#   if the existing file is detected as legacy format. Atomic via temp+mv.
write_suggestions() {
  local file="${1:-proposal-suggestions.md}"
  local data="${2:-[]}"

  if [[ -f "$file" ]] && grep -qE "^- name:|## 架构依据" "$file" 2>/dev/null; then
    echo "⚠️  旧格式 proposal-suggestions.md 检测到" >&2
    echo "   自动迁移需要手动确认" >&2
    if cp "$file" "${file}.bak" 2>/dev/null; then
      echo "   已备份到 ${file}.bak" >&2
    else
      echo "   ⚠️ 备份失败（权限？磁盘满？）— 直接覆盖" >&2
    fi
  fi

  if ! echo "$data" | python3 -c "import json, sys; json.load(sys.stdin)" 2>/dev/null; then
    echo "⚠️  write_suggestions: data is not valid JSON, refusing to write" >&2
    echo "    data was: $data" >&2
    return 1
  fi

  local tmp
  tmp=$(mktemp "${file}.XXXXXX") || { echo "⚠️  mktemp failed" >&2; return 1; }
  if ! echo "$data" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(json.dumps(data, ensure_ascii=False, indent=2))
" > "$tmp" 2>/dev/null; then
    echo "⚠️  write to temp file failed" >&2
    rm -f "$tmp"
    return 1
  fi
  if ! mv "$tmp" "$file" 2>/dev/null; then
    echo "⚠️  rename to $file failed" >&2
    rm -f "$tmp"
    return 1
  fi
  return 0
}
