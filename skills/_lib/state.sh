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

# count_pending_suggestions [project_root]
# Counts entries in proposal-suggestions.md where status == "待创建".
# Returns 0 on missing file, malformed JSON, empty list, or no matches.
# Defaults to ./proposal-suggestions.md when project_root not given.
#
# Extracted from inline Python heredocs in propose.md, status.md, and
# guide-plan.md (P3-3b). Algorithm equivalent to original inline versions:
# sum over list elements where element is a dict and status == "待创建".
count_pending_suggestions() {
  local project_root="${1:-.}"
  local ps_path="$project_root/proposal-suggestions.md"
  python3 -c "
import json, sys, os
p = sys.argv[1]
try:
    if not os.path.isfile(p):
        print(0)
        sys.exit(0)
    with open(p) as f:
        entries = json.load(f)
    if not isinstance(entries, list):
        print(0)
        sys.exit(0)
    count = sum(1 for e in entries if isinstance(e, dict) and e.get('status') == '待创建')
    print(count)
except (FileNotFoundError, json.JSONDecodeError):
    print(0)
" "$ps_path" 2>/dev/null || echo 0
}

# list_improvements <project_root>
# Lists improvement files in improvements/ directory.
# Returns newline-separated "name|priority|source" entries.
list_improvements() {
  local project_root="${1:-.}"
  local imp_dir="$project_root/improvements"
  if [ ! -d "$imp_dir" ]; then
    echo ""
    return
  fi
  for f in "$imp_dir"/*.md; do
    [ -f "$f" ] || continue
    local name=$(basename "$f" .md)
    # Extract priority and source from frontmatter-like headers
    local priority=$(grep -m1 '^\*\*优先级\*\*:' "$f" 2>/dev/null | sed 's/.*\*\*优先级\*\*: *//' | cut -d'|' -f1 | xargs)
    local source=$(grep -m1 '^\*\*优先级\*\*:' "$f" 2>/dev/null | sed 's/.*| \*\*来源\*\*: *//' | xargs)
    echo "${name}|${priority:-?}|${source:-?}"
  done
}

# list_approved <project_root>
# Parses proposal-approved.md Markdown table and returns approved entries.
# Returns newline-separated "name|priority|time|approver" entries.
list_approved() {
  local project_root="${1:-.}"
  local approved_file="$project_root/proposal-approved.md"
  if [ ! -f "$approved_file" ]; then
    echo ""
    return
  fi
  python3 -c "
import sys
with open(sys.argv[1]) as f:
    content = f.read()
# Find the approved table (## 已批准提案 section)
import re
# Match table rows after '## 已批准提案' header
section = re.split(r'## 已批准提案', content)
if len(section) > 1:
    # Find rows: | [name](path) | priority | time | approver |
    rows = re.findall(r'\|\s*\[([^\]]+)\]\([^)]+\)\s*\|\s*(\S+)\s*\|', section[1])
    for name, priority in rows:
        print(f'{name}|{priority}|-|-')
" "$approved_file" 2>/dev/null
}

# append_approved <project_root> <name> <priority>
# Appends a row to the approved proposals table in proposal-approved.md.
append_approved() {
  local project_root="$1"
  local name="$2"
  local priority="$3"
  local approved_file="$project_root/proposal-approved.md"
  local timestamp=$(date -u +%Y-%m-%d)
  
  if [ ! -f "$approved_file" ]; then
    echo "❌ proposal-approved.md not found" >&2
    return 1
  fi
  
  # Check if already exists
  if grep -q "\[$name\]" "$approved_file" 2>/dev/null; then
    echo "⚠️  $name already in approved list" >&2
    return 0
  fi
  
  # Insert before the ## 已实施 section
  local new_row="| [$name](improvements/$name.md) | $priority | $timestamp | guide-arch |"
  
  if grep -q '## 已实施' "$approved_file"; then
    # Insert before ## 已实施
    python3 -c "
import sys
with open(sys.argv[1]) as f:
    lines = f.readlines()
inserted = False
with open(sys.argv[1], 'w') as f:
    for line in lines:
        if not inserted and line.startswith('## 已实施'):
            f.write('$new_row\n\n')
            inserted = True
        f.write(line)
    if not inserted:
        f.write('$new_row\n')
" "$approved_file"
  else
    echo "$new_row" >> "$approved_file"
  fi
  echo "✅ $name added to approved list"
}

# mark_approved_completed <project_root> <name>
# Updates proposal-approved.md: moves entry from "已批准提案" to "已实施" table.
mark_approved_completed() {
  local project_root="$1"
  local name="$2"
  local approved_file="$project_root/proposal-approved.md"
  local timestamp=$(date -u +%Y-%m-%d)
  
  if [ ! -f "$approved_file" ]; then
    return 1
  fi
  
  python3 -c "
import sys, re
with open(sys.argv[1]) as f:
    content = f.read()
name = sys.argv[2]
ts = sys.argv[3]

# Find the row for this name
pattern = rf'\|\s*\[{re.escape(name)}\]\([^)]+\)\s*\|\s*(\S+)\s*\|[^|]*\|[^|]*\|'
match = re.search(pattern, content)
if not match:
    sys.exit(0)

# Remove from approved section, add to completed section
row = match.group(0)
# Extract priority
priority_match = re.search(r'\|\s*\[[^\]]+\]\([^)]+\)\s*\|\s*(\S+)\s*\|', row)
priority = priority_match.group(1) if priority_match else '?'

content = content.replace(row + '\n', '')
# Add to completed section
completed_row = f'| [{name}](improvements/{name}.md) | {priority} | {ts} |\n'
content = content.replace('## 已实施\n\n', f'## 已实施\n\n{completed_row}')

with open(sys.argv[1], 'w') as f:
    f.write(content)
" "$approved_file" "$name" "$timestamp"
}