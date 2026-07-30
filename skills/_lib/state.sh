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
# Returns newline-separated "name|priority|source|status" entries.
# The status field defaults to "待讨论" if the improvement file has no
# **状态** metadata line (backward compatible with old files).
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
    local status=$(grep -m1 '^\*\*状态\*\*:' "$f" 2>/dev/null | sed 's/.*\*\*状态\*\*: *//' | cut -d'|' -f1 | xargs)
    echo "${name}|${priority:-?}|${source:-?}|${status:-待讨论}"
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
  
  sync_suggestions "$project_root" "$name" "approved"
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

  sync_suggestions "$project_root" "$name" "completed"
}

# sync_suggestions <project_root> <name> <status>
#   Syncs a change's status between proposal-suggestions.md and proposal-approved.md.
#   - "approved" / "completed": removes the row from suggestions entirely (prevents
#     ghost entries that show as "pending review" when they are already done).
#   - "deferred" / "rejected": updates the status column in place (keeps row visible).
#   - Also accepts optional timestamp: sync_suggestions <root> <name> <status> "<timestamp>"
#   Idempotent: safe to call multiple times.
sync_suggestions() {
  local project_root="$1"
  local name="$2"
  local status="${3:-approved}"
  local timestamp="${4:-$(date -u +%Y-%m-%d)}"
  
  local suggestions_file="$project_root/proposal-suggestions.md"
  [ ! -f "$suggestions_file" ] && return 0
  
  REMOVE_ROW=false
  [ "$status" = "approved" ] || [ "$status" = "completed" ] && REMOVE_ROW=true
  
  SUGGESTIONS_FILE="$suggestions_file" CHANGE_NAME="$name" NEW_STATUS="$status" \
  REMOVE_ROW="$REMOVE_ROW" NEW_TIMESTAMP="$timestamp" \
  python3 -c '
import os, re
suggestions_file = os.environ["SUGGESTIONS_FILE"]
name = os.environ["CHANGE_NAME"]
status = os.environ["NEW_STATUS"]
remove_row = os.environ.get("REMOVE_ROW", "false") == "true"
ts = os.environ.get("NEW_TIMESTAMP", "")

with open(suggestions_file) as f:
    lines = f.readlines()

new_lines = []
removed = False
for line in lines:
    if re.search(r"\[" + re.escape(name) + r"\]\(improvements/", line):
        if remove_row:
            removed = True
            continue  # skip this line entirely
        else:
            parts = line.rstrip("\n").split("|")
            # Format: | [name](path) | priority | source | added_time | status |
            # After split: ["", " [name]...", " priority ", " source ", " date ", " status ", ""]
            if len(parts) >= 6:
                # Timestamped status for deferred/rejected
                status_display = status
                if status in ("deferred", "已延迟"):
                    status_display = f"⏳ 已延迟 ({ts})"
                elif status in ("rejected", "已拒绝"):
                    status_display = f"❌ 已拒绝 ({ts})"
                parts[-2] = f" {status_display} "
                line = "|".join(parts) + "\n"
            removed = True
    new_lines.append(line)

if removed:
    with open(suggestions_file, "w") as f:
        f.writelines(new_lines)
'
}

# sweep_implemented_proposals <project_root>
# Scans proposal-approved.md pending table against openspec/changes/archive/.
# For each pending entry with a matching archive dir (suffix match),
# calls mark_approved_completed to move it to the "已实施" section.
# Idempotent: safe to run repeatedly.
sweep_implemented_proposals() {
  local project_root="$1"
  local approved_file="$project_root/proposal-approved.md"

  if [ ! -f "$approved_file" ]; then
    return 0
  fi

  local archive_dir="$project_root/openspec/changes/archive"
  if [ ! -d "$archive_dir" ]; then
    return 0
  fi

  echo "🔍 扫描已实现提案 (sweep_implemented_proposals)..."
  local moved=0

  # Parse pending proposals from proposal-approved.md (before ## 已实施)
  # Extract [name](improvements/name.md) entries, check archive dir
  while IFS='|' read -r name rest; do
    [ -z "$name" ] && continue
    # Trim whitespace
    name=$(echo "$name" | xargs)
    # Check for matching archive dir: archive/*-<name>
    if ls -d "$archive_dir/"*-"$name" 2>/dev/null | grep -q .; then
      mark_approved_completed "$project_root" "$name"
      echo "  ✅ $name — 已归档，标记为已实施"
      moved=$((moved + 1))
    fi
  done < <(python3 -c "
import sys, re
with open(sys.argv[1]) as f:
    content = f.read()
# Only scan entries before ## 已实施
section = re.split(r'## 已实施', content)[0]
for m in re.finditer(r'\|\s*\[([^\]]+)\]\(improvements/([^)]+)\)\s*\|', section):
    print(f\"{m.group(1)}|{m.group(2)}\")
" "$approved_file" 2>/dev/null)

  if [ "$moved" -gt 0 ]; then
    echo "  🎯 共标记 $moved 个提案为已实施"
  else
    echo "  无已归档但未标记的提案"
  fi
}

# sweep_stale_suggestions <project_root>
#   Scans proposal-suggestions.md for entries that are already listed in
#   proposal-approved.md (either approved or completed sections) and removes
#   them. Prevents ghost entries where a proposal is already done but the
#   suggestions table still shows "pending review". Idempotent.
sweep_stale_suggestions() {
  local project_root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local suggestions_file="$project_root/proposal-suggestions.md"
  local approved_file="$project_root/proposal-approved.md"

  [ ! -f "$suggestions_file" ] && return 0
  [ ! -f "$approved_file" ] && return 0

  PY_SUGGESTIONS="$suggestions_file" PY_APPROVED="$approved_file" python3 -c '
import os, re, sys

suggestions_file = os.environ["PY_SUGGESTIONS"]
approved_file = os.environ["PY_APPROVED"]

with open(approved_file) as f:
    approved_content = f.read()

# Collect all names in proposal-approved.md (both approved and completed sections)
approved_names = set()
for m in re.finditer(r"\[([^\]]+)\]\(improvements/([^)]+)\)", approved_content):
    approved_names.add(m.group(1))

if not approved_names:
    sys.exit(0)

with open(suggestions_file) as f:
    lines = f.readlines()

new_lines = []
removed = 0
for line in lines:
    # Check if this line contains a suggestion that is now in approved
    m = re.search(r"\[([^\]]+)\]\(improvements/", line)
    if m and m.group(1) in approved_names:
        removed += 1
        continue
    new_lines.append(line)

if removed > 0:
    # Preserve empty table structure: if only header+separator remain, keep them
    with open(suggestions_file, "w") as f:
        f.writelines(new_lines)
    print(f"🧹 sweep_stale_suggestions: removed {removed} stale entries from suggestions table")
' 2>/dev/null || true
}

# check_dirty_key_files [project_root]
#   Detects uncommitted (unstaged) changes to proposal-suggestions.md and
#   proposal-approved.md via `git diff --name-only`. Emits a warning block
#   listing the dirty files and a recovery hint when any are dirty.
#   Non-blocking: always returns 0.
#   Used by guide/scan-state.sh before destructive git operations.
check_dirty_key_files() {
  local project_root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local dirty_files=""

  for f in "proposal-suggestions.md" "proposal-approved.md"; do
    if [ -f "$project_root/$f" ] && \
       git -C "$project_root" diff --name-only -- "$f" 2>/dev/null | grep -q "^$f$"; then
      dirty_files="$dirty_files $f"
    fi
  done

  if [ -n "$dirty_files" ]; then
    echo "⚠️  关键文件有未提交更改:$dirty_files"
    echo "   建议: git add$dirty_files && git commit -m 'save key workflow files'"
    echo "   避免 git checkout -- . 回滚丢失数据"
  fi
  return 0
}

# detect_approved_inconsistency <project_root>
# Detect suggestions marked "completed" in proposal-suggestions.md that have
# no corresponding entry in proposal-approved.md. Outputs a warning if
# inconsistent. Non-blocking: always returns 0.
# Uses env-var passing (PY_SUGGESTIONS / PY_APPROVED) per Oracle C1 fix to
# avoid bash string-interpolation injection.
detect_approved_inconsistency() {
    local project_root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
    local suggestions_file="$project_root/proposal-suggestions.md"
    local approved_file="$project_root/proposal-approved.md"

    [ ! -f "$suggestions_file" ] && return 0

    PY_SUGGESTIONS="$suggestions_file" PY_APPROVED="$approved_file" python3 -c '
import os, re, sys

suggestions_file = os.environ["PY_SUGGESTIONS"]
approved_file = os.environ["PY_APPROVED"]

try:
    with open(suggestions_file) as f:
        suggestions = f.read()

    sug_entries = set()
    for m in re.finditer(r"\|\s*\[([^\]]+)\]\(improvements/[^)]+\)\s*\|\s*\S+\s*\|\s*\S+\s*\|\s*(\S+)", suggestions):
        name = m.group(1).strip()
        status = m.group(2).strip()
        if status in ("completed", "已完成"):
            sug_entries.add(name)

    if not sug_entries:
        sys.exit(0)

    approved_names = set()
    if os.path.isfile(approved_file):
        with open(approved_file) as f:
            content = f.read()
        approved_names = set(re.findall(r"\|\s*\[([^\]]+)\]\(improvements/", content))

    missing = sug_entries - approved_names
    if missing:
        names_str = ", ".join(sorted(missing))
        print(f"⚠️  {len(missing)} 个 suggestions 标记已完成但无 approved 记录: {names_str}")
        print("   建议审计: 检查这些 change 是否已归档，或通过 guide-arch 补充批准")
except Exception:
    pass
' 2>/dev/null
}