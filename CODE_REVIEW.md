# Code Quality Review: spec-workflow

## Critical Bugs (Will Cause Failures)

### 1. **CRITICAL: Python Syntax Error in propose.md** ⭐⭐⭐
**File:** `skills/propose.md` (Line 93)  
**Issue:** Invalid Python f-string with nested single quotes inside single-quoted f-string.

```python
# BROKEN:
print(f'  已从建议列表移除: {', '.join(removed)}')
#                     ^    ^
#                     |    |
#              closes f-string prematurely
```

**Fix:**
```python
print(f"  已从建议列表移除: {', '.join(removed)}")
```

**Impact:** The Python script will crash with `SyntaxError` when trying to remove suggestions from the list.

---

### 2. **CRITICAL: Broken Shell Variable Interpolation in Python f-string** ⭐⭐⭐
**File:** `skills/propose.md` (Line 81)  
**Issue:** Shell variable `$PROJECT_ROOT` inside Python f-string won't interpolate because Python f-strings don't understand shell variables.

```python
# BROKEN - Python sees literal '$PROJECT_ROOT':
if name and os.path.isdir(f'$PROJECT_ROOT/openspec/changes/{name}/'):
```

**Fix:** Use shell to inject the variable before Python runs:
```bash
# Option 1: Export as environment variable
export PROJECT_ROOT="$PROJECT_ROOT"
python3 -c "
import os
project_root = os.environ['PROJECT_ROOT']
# ... then use project_root in Python ...
if name and os.path.isdir(os.path.join(project_root, 'openspec', 'changes', name)):
"

# Option 2: Use string replacement in shell
python3 -c "
import os
project_root = '$PROJECT_ROOT'
# ...
"
```

**Impact:** The directory existence check always fails, causing all suggestions to be incorrectly retained.

---

### 3. **CRITICAL: `wc -l` on Empty String Returns 1, Not 0** ⭐⭐⭐
**Files:** Multiple files - `execute.md` (Line 102), `status.md` (Line 376), `guide.md` (Lines 268, 310, 850)  
**Issue:** When piped empty input, `wc -l` outputs `1` (counts the newline), not `0`.

```bash
# BROKEN - will show 1 even when no worktrees exist:
WORKTREE_COUNT=$(echo "$WT_INFO" | wc -l)
if [ "$WORKTREE_COUNT" -gt 0 ]; then  # Always true!
```

**Fix:**
```bash
# Option 1: Use grep -c (returns 0 when no matches)
WORKTREE_COUNT=$(git worktree list | grep -c "openspec/")

# Option 2: Check if variable is non-empty first
if [ -n "$WT_INFO" ]; then
    WORKTREE_COUNT=$(echo "$WT_INFO" | wc -l)
else
    WORKTREE_COUNT=0
fi

# Option 3: Use awk to avoid wc -l issue
WORKTREE_COUNT=$(git worktree list | awk '/openspec\// {count++} END {print count+0}')
```

**Impact:** All "check if any worktree exists" logic is broken - will always detect at least 1 worktree even when none exist.

---

### 4. **CRITICAL: Empty WORKTREE_PATH Could Delete Wrong Directory** ⭐⭐⭐
**File:** `skills/status.md` (Lines 345, 347)  
**Issue:** If `git worktree list` returns empty or malformed data, `WORKTREE_PATH` could be empty, and `git worktree remove ""` has undefined behavior.

```bash
# DANGEROUS - WORKTREE_PATH could be empty:
if [ "$IN_WORKTREE" = true ] && [ -n "$WORKTREE_PATH" ]; then
    git worktree remove "$WORKTREE_PATH"
```

**Fix:** Add explicit validation:
```bash
if [ "$IN_WORKTREE" = true ] && [ -n "$WORKTREE_PATH" ] && [ "$WORKTREE_PATH" != "/" ]; then
    git worktree remove "$WORKTREE_PATH"
```

**Impact:** Potential deletion of unintended directories if WORKTREE_PATH is empty or "/".

---

### 5. **CRITICAL: Unquoted Variable Expansions in Path Construction** ⭐⭐⭐
**Files:** Multiple - `execute.md` (Line 94), `guide.md` (Line 231, 310), `status.md` (Line 338)  
**Issue:** Directory paths with spaces will break shell commands.

```bash
# BROKEN - breaks if PROJECT_ROOT has spaces:
ls -d $PROJECT_ROOT/openspec/changes/*/ 2>/dev/null

# BROKEN - breaks on spaces:
for wt in $(git worktree list | grep "openspec/" | awk '{print $1}'); do
```

**Fix:**
```bash
# Use arrays for paths with potential spaces
mapfile -t wt_list < <(git worktree list | awk '/openspec\// {print $1}')
for wt in "${wt_list[@]}"; do
    # ...
done

# Or at minimum, quote variables:
ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null
```

**Impact:** Commands fail or produce incorrect results when paths contain spaces.

---

## High Severity Issues (Likely to Cause Problems)

### 6. **HIGH: Arithmetic Expansion with Empty/Non-Numeric Values** ⭐⭐
**File:** `skills/status.md` (Line 134)  
**Issue:** If `jq` returns empty string or "null", arithmetic expansion fails.

```bash
# BROKEN - if jq returns "null" or empty string:
REMAINING=$((TOTAL - COMPLETE))
# bash: null: syntax error: operand expected (error token is "null")
```

**Fix:**
```bash
# Validate numeric values before arithmetic
COMPLETE=$(echo "$APPLY" | jq -r '.progress.complete // 0')
TOTAL=$(echo "$APPLY" | jq -r '.progress.total // 0')

# Validate they are actually numbers
if ! [[ "$COMPLETE" =~ ^[0-9]+$ ]] || ! [[ "$TOTAL" =~ ^[0-9]+$ ]]; then
    echo "❌ 无法解析进度数据"
    exit 1
fi

REMAINING=$((TOTAL - COMPLETE))
```

**Impact:** Script crashes with syntax error when openspec returns unexpected JSON.

---

### 7. **HIGH: `grep -q "^$PROJECT_ROOT"` with Regex Metacharacters** ⭐⭐
**File:** `skills/guide.md` (Line 154)  
**Issue:** If `PROJECT_ROOT` contains regex special characters (e.g., `/workspace/project.CppHDL`), grep interprets them as regex.

```bash
# BROKEN - PROJECT_ROOT treated as regex:
if ! echo "$ABS_GIT_DIR" | grep -q "^$PROJECT_ROOT"; then
```

**Fix:**
```bash
# Use fixed-string matching (fgrep/grep -F)
if ! echo "$ABS_GIT_DIR" | grep -qF "$PROJECT_ROOT"; then
    # Or use parameter expansion to escape regex
    ESCAPED_ROOT=$(printf '%s\n' "$PROJECT_ROOT" | sed 's/[[\.*^$()+?{|]/\\&/g')
    if ! echo "$ABS_GIT_DIR" | grep -q "^$ESCAPED_ROOT"; then
```

**Impact:** False positives/negatives in git directory validation, potentially allowing operations in wrong repository.

---

### 8. **HIGH: `stat -c %Y` is GNU-specific (macOS/BSD incompatible)** ⭐⭐
**File:** `skills/plan.md` (Line 72)  
**Issue:** `stat -c` is GNU coreutils syntax. macOS/BSD use `stat -f %m`.

```bash
# BROKEN on macOS:
MTIME=$(stat -c %Y "$PROJECT_ROOT/openspec/changes/<name>/" 2>/dev/null || echo 0)
```

**Fix:**
```bash
# Portable stat alternative
get_mtime() {
    local path="$1"
    if command -v stat >/dev/null 2>&1; then
        # Try GNU stat first
        local mtime
        mtime=$(stat -c %Y "$path" 2>/dev/null) && { echo "$mtime"; return; }
        # Fallback to BSD stat
        mtime=$(stat -f %m "$path" 2>/dev/null) && { echo "$mtime"; return; }
    fi
    # Ultimate fallback: use find
    find "$path" -maxdepth 0 -printf '%T@\n' 2>/dev/null | cut -d. -f1
}

MTIME=$(get_mtime "$PROJECT_ROOT/openspec/changes/<name>/" || echo 0)
```

**Impact:** Script fails on macOS and BSD systems.

---

### 9. **HIGH: `readlink -f` is GNU-specific (macOS incompatible)** ⭐⭐
**File:** `skills/INSTALL.md` (Line 83)  
**Issue:** `readlink -f` doesn't exist on macOS.

```bash
# BROKEN on macOS:
PACKAGE_DIR=$(dirname "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$HOME/.agents/skills/spec-workflow")")")
```

**Fix:**
```bash
# Portable readlink -f equivalent
realpath() {
    local path="$1"
    if command -v realpath >/dev/null 2>&1; then
        realpath "$path"
    elif command -v readlink >/dev/null 2>&1 && readlink -f "$path" >/dev/null 2>&1; then
        readlink -f "$path"
    else
        # Fallback: cd to directory and use pwd
        (cd "$(dirname "$path")" && pwd -P)
    fi
}
```

**Impact:** INSTALL skill fails on macOS.

---

### 10. **HIGH: `nproc` Not Available on macOS** ⭐⭐
**Files:** `execute.md` (Lines 179, 213), `guide.md` (implied)  
**Issue:** `nproc` doesn't exist on macOS.

```bash
# BROKEN on macOS:
cmake --build build -j$(nproc)
```

**Fix:**
```bash
# Portable parallel job count
get_nproc() {
    if command -v nproc >/dev/null 2>&1; then
        nproc
    elif command -v sysctl >/dev/null 2>&1; then
        sysctl -n hw.ncpu
    elif [ -f /proc/cpuinfo ]; then
        grep -c ^processor /proc/cpuinfo
    else
        echo 4  # Safe default
    fi
}

cmake --build build -j"$(get_nproc)"
```

**Impact:** Build commands fail on macOS.

---

### 11. **HIGH: Git Worktree List Parsing Breaks on Paths with Spaces** ⭐⭐
**Files:** `execute.md` (Lines 70, 85, 105), `status.md` (Lines 137, 274), `guide.md` (Lines 692-693)  
**Issue:** Git worktree list output format is `PATH BRANCH COMMIT [ANNOTATED]`. If PATH contains spaces, awk '{print $1}' is wrong.

```bash
# BROKEN - if worktree path is "/path/with spaces/project":
wt_path=$(echo "$line" | awk '{print $1}')  # Gets "/path/with" only
```

**Fix:**
```bash
# Use git worktree list --porcelain (machine-readable format)
# Or parse more carefully knowing the last field is the branch
parse_worktree_list() {
    git worktree list | while IFS= read -r line; do
        # Skip header if any
        [[ "$line" =~ ^worktree ]] && continue
        # Extract branch (last field)
        branch="${line##* }"
        # Path is everything before the last field
        path="${line% $branch}"
        echo "$path|$branch"
    done
}
```

**Impact:** Worktree detection fails for projects in paths with spaces (common on macOS `/Users/First Last/`).

---

## Medium Severity Issues (Potential Problems)

### 12. **MEDIUM: `set -e` Missing `set -u` and `set -o pipefail`** ⭐
**File:** `install.sh` (Line 6)  
**Issue:** Only `set -e` is used, missing:
- `set -u` (treat unset variables as errors)
- `set -o pipefail` (catch errors in pipelines)

**Fix:**
```bash
#!/bin/bash
set -euo pipefail
```

**Impact:** Errors in pipelines and unset variables go undetected, leading to silent failures.

---

### 13. **MEDIUM: `command -v` with `&>` (Bash-specific)** ⭐
**Files:** `INSTALL.md` (Lines 17, 20), `propose.md` (implied)  
**Issue:** `&>` is bash-specific, not POSIX sh compatible.

```bash
# Non-portable:
command -v openspec &> /dev/null
```

**Fix:**
```bash
# POSIX compatible:
command -v openspec >/dev/null 2>&1
```

**Impact:** Scripts fail on systems with strict POSIX sh (rare but possible in containers).

---

### 14. **MEDIUM: `read -p` is Bash-specific** ⭐
**Files:** `INSTALL.md` (Line 38), `execute.md` (Line 122)  
**Issue:** `read -p` is a bash extension, not POSIX.

**Fix:**
```bash
# POSIX compatible:
printf "按回车键退出，或输入 'y' 继续安装（不推荐）: "
read -r confirm

# Or if bash is required, add shebang:
#!/bin/bash
```

**Impact:** Fails on systems with dash as /bin/sh.

---

### 15. **MEDIUM: `git branch --format` Requires Git 2.13+** ⭐
**File:** `skills/plan.md` (Line 46)  
**Issue:** `--format` flag added in git 2.13.0. The skill claims compatibility with git 2.25+ but this specific check could fail on older versions.

```bash
# Requires git 2.13+:
EXISTING_BRANCHES=$(git branch --list 'openspec/*' --format='%(refname:short)' | sed 's/^openspec\///')
```

**Fix:**
```bash
# More compatible:
EXISTING_BRANCHES=$(git branch --list 'openspec/*' | sed 's/^[* ]*openspec\///')
```

**Impact:** Incompatibility with older git versions (though 2.25+ requirement makes this minor).

---

### 16. **MEDIUM: `grep -oE` is GNU-specific** ⭐
**File:** `skills/deps.md` (Line 104)  
**Issue:** `-o` and `-E` together may behave differently on BSD grep.

```bash
# May fail on BSD grep:
ADR_REFS=$(grep -oE 'ADR-[0-9]+' "$file" 2>/dev/null | sort -u)
```

**Fix:**
```bash
# More portable:
ADR_REFS=$(grep -E 'ADR-[0-9]+' "$file" 2>/dev/null | grep -o 'ADR-[0-9]*' | sort -u)
```

---

### 17. **MEDIUM: Array Assignment with Command Substitution Breaks on Spaces** ⭐
**File:** `skills/deps.md` (Line 67)  
**Issue:** `CANDIDATES=($(python3 -c "..."))` splits on whitespace, breaking names with spaces.

```bash
# BROKEN for names with spaces:
CANDIDATES=($(python3 -c "print('name with spaces')"))
# Creates two elements: ["name", "with", "spaces"]
```

**Fix:**
```bash
# Use mapfile/readarray:
mapfile -t CANDIDATES < <(python3 -c "
import json, sys
with open('$DEPS_INPUT') as f:
    data = json.load(f)
for name in data.get('candidates', []):
    print(name)
")
```

---

### 18. **MEDIUM: Indirect Variable Expansion (`${!var}`) is Bash-specific** ⭐
**Files:** `skills/deps.md` (Lines 143, 167, 190)  
**Issue:** `${!files_var_a}` is bash-specific and won't work in POSIX sh.

```bash
# Bash-only:
files_var_a="FILES_$a"
COMMON=$(comm -12 <(echo "${!files_var_a}" | sort) <(echo "${!files_var_b}" | sort))
```

**Fix:**
```bash
# Use associative arrays (bash 4+) or eval (careful!)
declare -A FILES_MAP
FILES_MAP[$a]="file1 file2"
FILES_MAP[$b]="file2 file3"

# Or use a simpler approach with temp files
```

---

### 19. **MEDIUM: JSON Construction with Shell is Fragile** ⭐
**File:** `skills/plan.md` (Lines 166-177)  
**Issue:** Building JSON by echoing strings is error-prone with special characters.

```bash
# Fragile - breaks if PROJECT_ROOT contains quotes:
echo '  "project_root": "'"$PROJECT_ROOT"'",' >> "$DEPS_INPUT"
```

**Fix:**
```bash
# Use jq or Python for JSON construction:
python3 -c "
import json, sys
data = {
    'project_root': '$PROJECT_ROOT',
    'candidates': ['$(IFS=","; echo "${CANDIDATES[*]}")']
}
# Actually, better to use proper JSON serialization:
"

# Best: use jq
jq -n --arg root "$PROJECT_ROOT" \
   --argjson candidates "$(printf '%s\n' "${CANDIDATES[@]}" | jq -R . | jq -s .)" \
   '{project_root: $root, candidates: $candidates}' > "$DEPS_INPUT"
```

---

### 20. **MEDIUM: `sed` with Unescaped Variable in Pattern** ⭐
**File:** `skills/plan.md` (Line 37)  
**Issue:** `$PROJECT_ROOT` in sed replacement can contain special characters.

```bash
# Fragile:
ls -d $PROJECT_ROOT/openspec/changes/*/ 2>/dev/null | sed 's#$PROJECT_ROOT/openspec/changes/##; s#/##'
```

**Fix:**
```bash
# Use parameter expansion or awk:
ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | \
    sed "s|$(printf '%s' "$PROJECT_ROOT/openspec/changes/" | sed 's/[[\.*^$()+?{|/\\&/g')||g; s|/||g"

# Or simpler with awk:
ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | \
    awk -F/ -v root="$PROJECT_ROOT" '{sub(root "/openspec/changes/", ""); sub(/\/$/, ""); print}'
```

---

### 21. **MEDIUM: `git show HEAD:...` Fails in Empty Repository** ⭐
**Files:** `guide.md` (Lines 360, 552, 591)  
**Issue:** If repository has no commits yet, `HEAD` doesn't exist.

```bash
# Fails if no commits:
committed=$(git show HEAD:"$PROJECT_ROOT/openspec/changes/$name/.openspec.yaml" > /dev/null 2>&1 && echo "✅" || echo "⏳")
```

**Fix:**
```bash
# Check for HEAD first:
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    committed=$(git show HEAD:"openspec/changes/$name/.openspec.yaml" > /dev/null 2>&1 && echo "✅" || echo "⏳")
else
    committed="⏳"
fi
```

---

### 22. **MEDIUM: `cd` into Worktree Without Error Handling** ⭐
**Files:** `guide.md` (Lines 632, 754, 772), `execute.md` (Line 137)  
**Issue:** If `cd` fails (directory doesn't exist), subsequent commands run in wrong directory.

```bash
# Dangerous:
cd "$WORKTREE_PATH"
skill_use("spec-workflow-execute")
cd /workspace/project/CppHDL  # Never reached if cd fails or execute hangs
```

**Fix:**
```bash
# Always check cd success:
cd "$WORKTREE_PATH" || { echo "❌ 无法进入 worktree 目录"; exit 1; }
skill_use("spec-workflow-execute")
cd - >/dev/null || exit 1  # Return to previous directory
```

---

### 23. **MEDIUM: `grep -E` with Extended Regex in Single Quotes** ⭐
**File:** `skills/deps.md` (Line 489)  
**Issue:** Single quotes inside double-quoted regex cause syntax error.

```bash
# The single quote closes the shell string prematurely:
SCOPE_FILES=$(grep -E '^[ \t]*-[ \t]*('src/|file:)' "$file" 2>/dev/null)
#                                      ^
#                                      |
#                              closes outer quotes!
```

**Fix:**
```bash
# Use different quote escaping:
SCOPE_FILES=$(grep -E '^[ \t]*-[ \t]*(src/|file:)' "$file" 2>/dev/null)

# Or use a variable:
pattern='^[ \t]*-[ \t]*(src/|file:)'
SCOPE_FILES=$(grep -E "$pattern" "$file" 2>/dev/null)
```

---

### 24. **MEDIUM: `curl | bash` Security Risk** ⭐
**File:** `skills/INSTALL.md` (Line 174)  
**Issue:** Piping curl directly to bash is a well-known security anti-pattern.

```bash
# Security risk:
curl -sL <raw-url>/install-spec-workflow.sh | bash
```

**Fix:**
```bash
# Download, verify, then execute:
curl -sL -o /tmp/install-spec-workflow.sh <raw-url>/install-spec-workflow.sh
# Optionally verify checksum here
bash /tmp/install-spec-workflow.sh
rm -f /tmp/install-spec-workflow.sh
```

---

### 25. **MEDIUM: `mktemp` with Hardcoded `/tmp`** ⭐
**Files:** `status.md` (Line 205), `execute.md` (Line 312)  
**Issue:** Hardcoding `/tmp` is less secure and may fail if `/tmp` doesn't exist or is full.

```bash
# Less secure:
TMPFILE=$(mktemp /tmp/status_tasks_XXXXXX.md)
```

**Fix:**
```bash
# Better - uses system temp directory:
TMPFILE=$(mktemp -t status_tasks_XXXXXX.md)

# Or create in project directory (if cleanup is guaranteed):
TMPFILE=$(mktemp "${PROJECT_ROOT}/.zcf/.tmp_tasks_XXXXXX.md")
```

---

## Low Severity Issues (Style/Portability)

### 26. **LOW: Version String Format** ⭐
**File:** `package.json` (Line 3)  
**Issue:** Version is `"1.0"` instead of semantic versioning `"1.0.0"`.

**Fix:**
```json
{
  "version": "1.0.0"
}
```

---

### 27. **LOW: Non-NPM Dependencies in package.json** ⭐
**File:** `package.json` (Lines 15-17)  
**Issue:** `git` and `cmake` are system dependencies, not npm packages. Listing them in `dependencies` is incorrect for npm.

**Fix:**
```json
{
  "engines": {
    "opencode": ">=1.0.0",
    "git": ">=2.25.0",
    "cmake": ">=3.16.0"
  }
}
```

---

### 28. **LOW: Hardcoded Project Path** ⭐
**Files:** `status.md` (Line 302), `execute.md` (Line 258), `guide.md` (Lines 636, 757, 772, 842)  
**Issue:** Multiple hardcoded references to `/workspace/project/CppHDL`.

```bash
# Hardcoded path:
MAIN_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "/workspace/project/CppHDL")
cd /workspace/project/CppHDL
```

**Fix:**
```bash
# Always derive from git:
MAIN_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$MAIN_ROOT" ]; then
    echo "❌ 无法确定项目根目录"
    exit 1
fi
cd "$MAIN_ROOT" || exit 1
```

---

### 29. **LOW: `grep -rn` with Alternation Without `-E`** ⭐
**File:** `skills/propose.md` (Line 151)  
**Issue:** Using `\|` for alternation in basic regex mode is GNU-specific.

```bash
# GNU-specific:
grep -rn "TODO\|FIXME\|HACK\|WORKAROUND" include/ src/
```

**Fix:**
```bash
# Portable:
grep -rnE "TODO|FIXME|HACK|WORKAROUND" include/ src/
# Or use multiple -e flags:
grep -rn -e "TODO" -e "FIXME" -e "HACK" -e "WORKAROUND" include/ src/
```

---

### 30. **LOW: `for subdir in $(ls -d ...)` Anti-pattern** ⭐
**File:** `skills/propose.md` (Line 163)  
**Issue:** Parsing `ls` output is fragile. Should use globs.

```bash
# Fragile:
for subdir in $(ls -d include/*/ 2>/dev/null | xargs -n1 basename); do
```

**Fix:**
```bash
# Use glob:
for subdir in include/*/; do
    [ -d "$subdir" ] || continue
    subdir=$(basename "$subdir")
    # ...
done
```

---

## Logic Bugs and Edge Cases

### 31. **LOGIC: `git worktree list` Grepped by Path Instead of Branch**
**Files:** `guide.md` (Lines 602, 554), `status.md` (Line 109)  
**Issue:** Checking worktree existence by path rather than branch name can miss worktrees or detect false positives.

**Fix:** Use branch-based detection as the primary check:
```bash
# Better:
if git worktree list | awk -v branch="openspec/$CHANGE_NAME" '$3 == branch {found=1} END {exit !found}'; then
    echo "Worktree exists for branch openspec/$CHANGE_NAME"
fi
```

---

### 32. **LOGIC: `git merge --ff-only` Without Fallback Handling**
**File:** `guide.md` (Line 833), `status.md` (Line 318)  
**Issue:** `--ff-only` fails if main branch has moved forward, but the code does handle it with a fallback. However, the fallback in guide.md doesn't exist.

In `status.md` (Line 316-324):
```bash
# This logic is correct:
if [ "$MERGE_BASE" = "$MAIN_TIP" ]; then
    git merge --ff-only "openspec/<name>"
else
    git merge --no-ff "openspec/<name>" -m "merge: <name> change"
fi
```

But `guide.md` (Line 833) only has:
```bash
# Missing fallback:
git merge --ff-only "openspec/$CHANGE_NAME"
```

**Fix:** Apply the same fallback logic from status.md to guide.md.

---

### 33. **LOGIC: `awk` Exit Code Check After Redirection**
**Files:** `execute.md` (Lines 312-325), `status.md` (Lines 205-214)  
**Issue:** Checking `$?` after a pipeline only checks the last command (`mv`), not `awk`.

```bash
# Checks mv, not awk:
awk -v desc="..." -v repl="..." '...' "$file" > "$TMPFILE"
if [ $? -eq 0 ]; then  # This is mv's exit code, not awk's!
```

**Fix:**
```bash
# Use PIPESTATUS (bash) or set -o pipefail:
set -o pipefail
awk -v desc="..." -v repl="..." '...' "$file" > "$TMPFILE"
AWK_STATUS=$?
set +o pipefail

if [ "$AWK_STATUS" -eq 0 ]; then
    mv "$TMPFILE" "$file"
else
    rm -f "$TMPFILE"
fi
```

---

### 34. **LOGIC: `git branch -d` May Fail if Branch Has Unmerged Commits**
**Files:** `guide.md` (Line 840), `status.md` (Line 351)  
**Issue:** `git branch -d` (lowercase d) fails if branch has unmerged commits. Should use `-D` or check first.

```bash
# May fail:
git branch -d "openspec/$CHANGE_NAME"
```

**Fix:**
```bash
# Check if branch exists and handle unmerged:
if git branch --list "openspec/$CHANGE_NAME" | grep -q "openspec/$CHANGE_NAME"; then
    if git branch -d "openspec/$CHANGE_NAME" 2>/dev/null; then
        echo "✅ Branch 已删除"
    else
        echo "⚠️  Branch 有未合并的提交，强制删除"
        git branch -D "openspec/$CHANGE_NAME"
    fi
fi
```

---

### 35. **LOGIC: `git checkout` in Subshell Doesn't Affect Parent**
**Files:** `status.md` (Lines 287, 307)  
**Issue:** Changing directory in subshell doesn't affect parent shell.

```bash
# This cd only affects the subshell:
DIRTY=$(cd "$WORKTREE_PATH" && git status --porcelain | wc -l)
# Parent directory unchanged - that's correct

# But this is confusing:
cd "$MAIN_ROOT"  # In subshell due to pipeline context
```

**Fix:** The subshell behavior is actually correct here, but add comments to clarify:
```bash
# Explicit subshell for clarity:
DIRTY=$( (cd "$WORKTREE_PATH" && git status --porcelain | wc -l) )
```

---

### 36. **LOGIC: `grep "status: 待创建"` Assumes Exact Format**
**Files:** `guide.md` (Line 864), `status.md` (Line 386)  
**Issue:** Assumes `proposal-suggestions.md` has exact format `status: 待创建`.

```bash
# Fragile:
REMAINING=$(grep -c "status: 待创建" "proposal-suggestions.md" 2>/dev/null || echo "0")
```

**Fix:**
```bash
# More robust:
if [ -f "proposal-suggestions.md" ]; then
    REMAINING=$(grep -ciE "status\s*[:=]\s*待创建" "proposal-suggestions.md" 2>/dev/null || echo "0")
else
    REMAINING=0
fi
```

---

## Inconsistencies Between Files

### 37. **INCONSISTENCY: Skill Name Variations**
**Issue:** Different files reference the skill by different names:
- `spec-workflow-guide` (INSTALL.md, guide.md)
- `openspec-workflow-guide` (USAGE.md, guide.md)
- `spec-workflow-propose` (guide.md)
- `spec-workflow-plan` (guide.md, execute.md)
- `spec-workflow-execute` (execute.md, guide.md, USAGE.md)
- `spec-workflow-status` (status.md, execute.md)
- `openspec-workflow-execute` (USAGE.md)

**Fix:** Standardize all references to a single naming convention.

---

### 38. **INCONSISTENCY: `PROJECT_ROOT` Definition Varies**
**Files:** All skill files  
**Issue:** Different ways to detect project root:
- `PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)` (most common)
- `PROJECT_ROOT=$(pwd)` (guide.md line 128)
- `GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "unknown")` (execute.md, status.md)

**Fix:** Create a shared function/variable convention, e.g.:
```bash
# Standard project root detection
detect_project_root() {
    local root
    root=$(git rev-parse --show-toplevel 2>/dev/null)
    if [ -z "$root" ]; then
        echo "❌ 当前目录不是 git 仓库" >&2
        return 1
    fi
    echo "$root"
}

PROJECT_ROOT=$(detect_project_root) || exit 1
```

---

### 39. **INCONSISTENCY: `set -e` Usage Inconsistent**
**Files:** Various  
**Issue:** `install.sh` has `set -e` but skill markdown files don't consistently show error handling patterns.

**Fix:** Add error handling boilerplate to all executable code blocks.

---

### 40. **INCONSISTENCY: State File Format Mismatch**
**Files:** `guide.md` vs `USAGE.md`  
**Issue:** The `workflow-state.md` format in guide.md doesn't match the example in USAGE.md exactly.

**Fix:** Ensure documentation and implementation match.

---

## Summary by Severity

| Severity | Count | Key Issues |
|----------|-------|-----------|
| **Critical** | 5 | Python syntax error, broken variable interpolation, wc -l bug, empty path deletion risk, unquoted expansions |
| **High** | 10 | Arithmetic errors, regex metacharacters, GNU-specific commands (stat, readlink, nproc), git parsing |
| **Medium** | 12 | Missing shell options, bash-specific syntax, JSON construction, sed escaping, empty repo handling |
| **Low** | 5 | Version format, non-npm deps, hardcoded paths, grep syntax, ls parsing |
| **Logic** | 6 | Worktree detection, merge fallback, awk exit codes, branch deletion, format assumptions |
| **Inconsistency** | 4 | Naming conventions, project root, error handling, state format |

## Top Priority Fixes

1. **Fix Python syntax error in propose.md line 93**
2. **Fix shell variable interpolation in propose.md line 81**
3. **Replace all `wc -l` on potentially empty strings**
4. **Quote all variable expansions in path contexts**
5. **Add validation before `git worktree remove`**
6. **Replace GNU-specific commands with portable alternatives**
7. **Fix arithmetic expansion with jq output validation**
8. **Add `set -euo pipefail` to all shell scripts**
9. **Fix git worktree list parsing for paths with spaces**
10. **Standardize skill naming across all files**
