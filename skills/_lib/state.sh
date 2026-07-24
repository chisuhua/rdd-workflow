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

# count_pending_suggestions [project_root]
# Counts proposals in improvements/ that are NOT in proposal-approved.md.
# Returns 0 if no pending proposals or files are missing.
count_pending_suggestions() {
  local project_root="${1:-.}"
  local imp_dir="$project_root/improvements"
  local approved_file="$project_root/proposal-approved.md"
  
  if [ ! -d "$imp_dir" ]; then
    echo 0
    return
  fi
  
  python3 -c "
import os, re
try:
    imp_dir = '$imp_dir'
    approved_file = '$approved_file'
    
    all_improvements = set()
    for f in os.listdir(imp_dir):
        if f.endswith('.md'):
            all_improvements.add(f[:-3])
    
    approved = set()
    if os.path.isfile(approved_file):
        with open(approved_file) as f:
            approved = set(re.findall(r'\|\s*\[([^\]]+)\]\(improvements/', f.read()))
    
    print(len(all_improvements - approved))
except Exception:
    print(0)
"
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
    lines = f.readlines()
name = sys.argv[2]
ts = sys.argv[3]

# Idempotency: check if already in completed section
in_completed = False
for line in lines:
    if f'[{name}]' in line:
        in_completed = True
        break

# Find entry in approved table
approved_idx = None
approved_line = None
for i, line in enumerate(lines):
    if f'[{name}]' in line and line.strip().startswith('|'):
        approved_idx = i
        approved_line = line
        break

# Already in completed table
if in_completed and approved_idx is None:
    sys.exit(0)

# Extract priority from approved row
priority = '?'
if approved_line:
    m = re.search(r'\|\s*\[[^\]]+\]\([^)]+\)\s*\|\s*(\S+)\s*\|', approved_line)
    if m:
        priority = m.group(1)

# Remove from approved table
if approved_idx is not None:
    del lines[approved_idx]

# Insert into completed table after header
completed_row = f'| [{name}](improvements/{name}.md) | {priority} | {ts} |\n'
inserted = False
for i, line in enumerate(lines):
    if line.startswith('## 已实施'):
        # Find the separator line after the header
        j = i + 1
        while j < len(lines):
            if lines[j].strip().startswith('|---'):
                # Insert after separator
                lines.insert(j + 1, completed_row)
                inserted = True
                break
            j += 1
        if inserted:
            break

if not inserted:
    lines.append(completed_row)

with open(sys.argv[1], 'w') as f:
    f.writelines(lines)
" "$approved_file" "$name" "$timestamp"
}