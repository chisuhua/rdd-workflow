# Round 2a Implementation Plan — 10 Mechanical Fixes

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax. Each task = one atomic commit.

**Goal:** Land 10 atomic commits fixing verified real bugs from `CODE_REVIEW.md` Medium/Low/Logic categories. Zero API change, zero new dependencies.

**Architecture:** Per-issue commit, mechanical text replacement. No refactor of healthy code. No new files.

**Tech Stack:** Markdown skill files + bash + Python (inline) + JSON. Existing tools only.

**Spec:** [`docs/superpowers/specs/2026-06-03-code-review-round-2a-design.md`](../specs/2026-06-03-code-review-round-2a-design.md) (commit `5143a07`)

**Predecessor:** Round 1 plan at `aef3279`, 9 fix commits pushed.

---

## Pre-Plan Verification (done)

Re-verified each deferred item against actual code on master (post-Round-1, 11 commits ahead). Result: **10 still real, 5 already fixed/skipped**:

| CODE_REVIEW # | Status | Evidence |
|---|---|---|
| #14 | Skipped | install.sh already has `set -euo pipefail`; INSTALL.md:127 `set -e` is inside heredoc generating child script (acceptable) |
| #16 | Real | deps.md:104 uses `grep -oE` |
| #17 | Skipped | no `array=()` pattern in current code |
| #18 | Real | deps.md:142,145,169,192,193 (5 sites) |
| #19 | Skipped | no JSON echo pattern in current code |
| #20 | Real | plan.md:46 sed with unescaped $PROJECT_ROOT |
| #21 | Real | guide.md:477,678,800 + plan.md:466 (4 sites of `git show HEAD:`) |
| #22 | Real | guide.md:1012 `cd "$WORKTREE_PATH"` no guard |
| #23 | Real | guide.md:612 grep with nested single-quote |
| #24 | Real | INSTALL.md:175 `curl ... | bash` |
| #26 | Skipped | package.json already has `"version": "1.0.0"` |
| #27 | Real | package.json:12-13 git/cmake in dependencies |
| #30 | Skipped | no `for x in $(ls -d ...)` in current code |
| #33 | Skipped | no `if [ $? -eq 0 ]` after awk in current code |
| #35 | Real | status.md:314 misleading "subshell" comment |
| #36 | Real | guide.md:1193, propose.md:657, status.md:397 (3 sites) |
| #37-40 | Round 2b | needs user design decisions (deferred) |

---

## Task A10: Move git/cmake to `engines` in `package.json` (Low #27)

**Files:** Modify `package.json:12-13`

- [ ] **Step 1: Read current `package.json`**

```bash
cat package.json
```

- [ ] **Step 2: Replace `dependencies` block (remove git/cmake) with `engines` block**

Old:
```json
  "dependencies": {
    "git": ">=2.25.0",
    "cmake": ">=3.16.0"
  }
```

New:
```json
  "engines": {
    "git": ">=2.25.0",
    "cmake": ">=3.16.0"
  }
```

- [ ] **Step 3: Validate JSON**

```bash
python3 -c "import json; json.load(open('package.json'))" && echo "JSON OK"
```

- [ ] **Step 4: Commit**

```bash
git add package.json
git commit -m "fix(package): move git/cmake from dependencies to engines (CODE_REVIEW #27)

git and cmake are system requirements, not npm packages. Listing
them in 'dependencies' is incorrect for npm and may confuse
package managers.

Moved to 'engines' field which is the correct location for system
runtime requirements.

Closes CODE_REVIEW.md issue #27."
```

---

## Task A9: Replace `curl | bash` with download-then-execute (Medium #24)

**Files:** Modify `skills/INSTALL.md:175`

- [ ] **Step 1: Read the line**

```bash
sed -n '173,180p' skills/INSTALL.md
```

- [ ] **Step 2: Replace line 175**

Old:
```bash
curl -sL <raw-url>/install-rdd-workflow.sh | bash
```

New (download to temp, optionally verify checksum, then execute):
```bash
curl -sL -o /tmp/install-rdd-workflow.sh <raw-url>/install-rdd-workflow.sh
# Optional: verify SHA256 checksum here (security)
bash /tmp/install-rdd-workflow.sh
rm -f /tmp/install-rdd-workflow.sh
```

- [ ] **Step 3: Commit**

```bash
git add skills/INSTALL.md
git commit -m "fix(install): download install script before executing (CODE_REVIEW #24)

Piping curl directly to bash is a well-known security anti-pattern:
the user has no opportunity to inspect the script before it runs.
If the remote is compromised or the connection is MITM'd, arbitrary
code runs with the user's privileges.

Replaced with download-to-temp-then-execute pattern. The user can
inspect /tmp/install-rdd-workflow.sh before running, and an
optional SHA256 verification line is included as a comment.

Closes CODE_REVIEW.md issue #24 in skills/INSTALL.md."
```

---

## Task A6: Fix unescaped `$PROJECT_ROOT` in sed (Medium #20)

**Files:** Modify `skills/plan.md:46`

- [ ] **Step 1: Read the line**

```bash
sed -n '44,50p' skills/plan.md
```

- [ ] **Step 2: Replace line 46**

Old:
```bash
ls -d $PROJECT_ROOT/openspec/changes/*/ 2>/dev/null | sed 's#$PROJECT_ROOT/openspec/changes/##; s#/##'
```

New (also quote `$PROJECT_ROOT` for paths with spaces, use awk to avoid sed escaping issues):
```bash
ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | awk -F/ -v root="$PROJECT_ROOT" '{sub(root "/openspec/changes/", ""); sub(/\/$/, ""); print}'
```

- [ ] **Step 3: Verify bash syntax of modified block**

```bash
awk '/^```bash$/,/^```$/' skills/plan.md > /tmp/check.sh
bash -n /tmp/check.sh && echo "SYNTAX OK"
```

- [ ] **Step 4: Commit**

```bash
git add skills/plan.md
git commit -m "fix(plan): use awk instead of sed with unescaped \$PROJECT_ROOT (CODE_REVIEW #20)

The original 'sed s#\$PROJECT_ROOT/openspec/changes/##' breaks if
\$PROJECT_ROOT contains '/' or '\&' (sed metacharacters).
Additionally, \$PROJECT_ROOT was unquoted, breaking on paths
with spaces.

Replaced with awk using -F/ and a -v root assignment. The root
path is passed as a literal variable to awk, avoiding any shell
or sed metacharacter interpretation.

Closes CODE_REVIEW.md issue #20 in skills/plan.md."
```

---

## Task A7: Guard `git show HEAD:` against empty repositories (Medium #21)

**Files:**
- Modify `skills/guide.md:477, 678, 800`
- Modify `skills/plan.md:466`

- [ ] **Step 1: Read each site for unique context**

```bash
echo "=== guide.md:477 ==="; sed -n '475,479p' skills/guide.md
echo "=== guide.md:678 ==="; sed -n '676,680p' skills/guide.md
echo "=== guide.md:800 ==="; sed -n '798,802p' skills/guide.md
echo "=== plan.md:466 ==="; sed -n '464,468p' skills/plan.md
```

- [ ] **Step 2: Replace `guide.md:477`**

Old:
```bash
        committed=$(git show HEAD:"$PROJECT_ROOT/openspec/changes/$name/.openspec.yaml" > /dev/null 2>&1 && echo "✅" || echo "⏳")
```

New:
```bash
        if git rev-parse --verify HEAD >/dev/null 2>&1; then
            committed=$(git show HEAD:"$PROJECT_ROOT/openspec/changes/$name/.openspec.yaml" > /dev/null 2>&1 && echo "✅" || echo "⏳")
        else
            committed="⏳"
        fi
```

- [ ] **Step 3: Replace `guide.md:678`**

Old:
```bash
    committed=$(git show HEAD:"$PROJECT_ROOT/openspec/changes/$name/.openspec.yaml" > /dev/null 2>&1 && echo "✅" || echo "⏳")
```

New:
```bash
    if git rev-parse --verify HEAD >/dev/null 2>&1; then
        committed=$(git show HEAD:"$PROJECT_ROOT/openspec/changes/$name/.openspec.yaml" > /dev/null 2>&1 && echo "✅" || echo "⏳")
    else
        committed="⏳"
    fi
```

- [ ] **Step 4: Replace `guide.md:800`**

Old:
```bash
if ! git show HEAD:"$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/.openspec.yaml" > /dev/null 2>&1; then
```

New:
```bash
if git rev-parse --verify HEAD >/dev/null 2>&1 && ! git show HEAD:"$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/.openspec.yaml" > /dev/null 2>&1; then
```

> Note: This site uses an `if !` inversion pattern. The fix combines the HEAD-exists check with the existing negation to preserve the original logic. Also add a fallback `else` branch:

Update the `if` block (the surrounding 5-7 lines) to also handle the no-HEAD case. Read context first:

```bash
sed -n '798,808p' skills/guide.md
```

Then replace the whole `if ! git show ...; then ... fi` block with:
```bash
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    if ! git show HEAD:"$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/.openspec.yaml" > /dev/null 2>&1; then
        echo "❌ Artifacts 尚未提交，无法创建 worktree"
        # ... rest of the original block ...
    fi
else
    echo "❌ 当前仓库没有任何提交（HEAD 不存在）"
    echo "请先 git commit 一些文件后再执行 plan"
    exit 1
fi
```

(Adjust the inner block to match the actual content read in Step 1.)

- [ ] **Step 5: Replace `plan.md:466`**

Old:
```bash
git show HEAD:$PROJECT_ROOT/openspec/changes/<name>/.openspec.yaml > /dev/null 2>&1
```

New:
```bash
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    git show HEAD:"$PROJECT_ROOT/openspec/changes/<name>/.openspec.yaml" > /dev/null 2>&1
fi
```

- [ ] **Step 6: Verify bash syntax of modified blocks**

```bash
for f in skills/guide.md skills/plan.md; do
    echo "=== $f ==="
    awk '/^```bash$/,/^```$/' "$f" > /tmp/check.sh
    bash -n /tmp/check.sh && echo "OK"
done
```

- [ ] **Step 7: Commit**

```bash
git add skills/guide.md skills/plan.md
git commit -m "fix(guide,plan): guard git show HEAD: against empty repositories (CODE_REVIEW #21)

'git show HEAD:<path>' fails with 'fatal: ambiguous argument HEAD'
in a fresh repository with no commits. Four sites in guide.md
(2 sites of inline committed-check, 1 site of worktree
gating) and one in plan.md (artifact commit-gate check)
were unguarded.

Wrapped each with a 'git rev-parse --verify HEAD' pre-check.
For the gating sites, an empty repo now produces a clear
error message and a non-zero exit instead of a cryptic
'fatal: ambiguous argument' failure.

Closes CODE_REVIEW.md issue #21 in skills/guide.md and skills/plan.md."
```

---

## Task A5: Split `grep -oE` for portability (Medium #16)

**Files:** Modify `skills/deps.md:104`

- [ ] **Step 1: Read the line**

```bash
sed -n '102,106p' skills/deps.md
```

- [ ] **Step 2: Replace line 104**

Old:
```bash
ADR_REFS=$(grep -oE 'ADR-[0-9]+' "$PROJECT_ROOT/openspec/changes/<name>/proposal.md" 2>/dev/null | sort -u)
```

New:
```bash
ADR_REFS=$(grep -E 'ADR-[0-9]+' "$PROJECT_ROOT/openspec/changes/<name>/proposal.md" 2>/dev/null | grep -o 'ADR-[0-9]*' | sort -u)
```

- [ ] **Step 3: Verify bash syntax**

```bash
awk '/^```bash$/,/^```$/' skills/deps.md > /tmp/check.sh
bash -n /tmp/check.sh && echo "SYNTAX OK"
```

- [ ] **Step 4: Commit**

```bash
git add skills/deps.md
git commit -m "fix(deps): split grep -oE for BSD/portable compatibility (CODE_REVIEW #16)

'grep -oE' may behave differently on BSD grep (macOS default).
Split into a two-step: 'grep -E' (extended regex matching) then
'grep -o' (extract matches). Both flags individually are
universally portable.

Closes CODE_REVIEW.md issue #16 in skills/deps.md."
```

---

## Task A8: Replace bash `${!var}` with portable `eval` (Medium #18)

**Files:** Modify `skills/deps.md:142, 145, 169, 192, 193`

> **Design decision:** The CODE_REVIEW suggested associative arrays (bash 4+) or `eval` (careful!). Associative arrays would also require changing the upstream writer (propose.md sets `FILES_$a` etc. externally), which is out of Round 2a scope. Going with `eval` — 1-file change, POSIX-compatible, works with existing variable naming convention.

- [ ] **Step 1: Read the three blocks for full context**

```bash
echo "=== block 1 (file conflict) ==="; sed -n '138,150p' skills/deps.md
echo "=== block 2 (ADR chain) ==="; sed -n '165,173p' skills/deps.md
echo "=== block 3 (interface) ==="; sed -n '186,200p' skills/deps.md
```

- [ ] **Step 2: Replace block 1 (file conflict detection)**

Old:
```bash
    # 取交集（使用 bash 间接变量展开 ${!var} 获取各 change 的文件列表）
    files_var_a="FILES_$a"
    files_var_b="FILES_$b"
    COMMON=$(comm -12 <(echo "${!files_var_a}" | sort) <(echo "${!files_var_b}" | sort))
```

New:
```bash
    # 取交集（用 eval 实现间接变量展开，兼容 bash 3.x / POSIX sh）
    files_var_a="FILES_$a"
    files_var_b="FILES_$b"
    COMMON=$(comm -12 <(eval "echo \"\${$files_var_a}\"" | sort) <(eval "echo \"\${$files_var_b}\"" | sort))
```

- [ ] **Step 3: Replace block 2 (ADR chain)**

Old:
```bash
for name in $CANDIDATES; do
  adr_var="ADR_REFS_$name"
  for adr in ${!adr_var}; do
    echo "$adr ← $name"
  done
done
```

New:
```bash
for name in $CANDIDATES; do
  adr_var="ADR_REFS_$name"
  for adr in $(eval "echo \${$adr_var}"); do
    echo "$adr ← $name"
  done
done
```

- [ ] **Step 4: Replace block 3 (interface dependency)**

Old:
```bash
    iface_var_a="IFACE_DEF_$a"
    iface_use_var_b="IFACE_USE_$b"
    for iface in ${!iface_var_a}; do
      if echo "${!iface_use_var_b}" | grep -q "$iface"; then
        echo "📦 $b 依赖 $a (接口: $iface)"
      fi
    done
```

New:
```bash
    iface_var_a="IFACE_DEF_$a"
    iface_use_var_b="IFACE_USE_$b"
    for iface in $(eval "echo \${$iface_var_a}"); do
      if eval "echo \${$iface_use_var_b}" | grep -q "$iface"; then
        echo "📦 $b 依赖 $a (接口: $iface)"
      fi
    done
```

- [ ] **Step 5: Verify bash syntax**

```bash
awk '/^```bash$/,/^```$/' skills/deps.md > /tmp/check.sh
bash -n /tmp/check.sh && echo "SYNTAX OK"
```

- [ ] **Step 6: Commit**

```bash
git add skills/deps.md
git commit -m "fix(deps): replace \${!var} bash indirect expansion with portable eval (CODE_REVIEW #18)

Bash 4+ indirect expansion '\${!var}' is not available in
older bash or POSIX sh. Five sites in deps.md used it to
read FILES_\$a, ADR_REFS_\$name, IFACE_DEF_\$a, IFACE_USE_\$b
(set externally by the propose step).

Replaced with 'eval' that achieves the same effect in any
POSIX-compatible shell. The 'eval' call uses \${} escaping
to defer expansion until eval runs.

Note: Associative arrays (bash 4+ declare -A) would be cleaner
but require also changing the upstream writer in propose.md.
That's a larger cross-file refactor deferred to a future round.

Closes CODE_REVIEW.md issue #18 in skills/deps.md."
```

---

## Task A3: Clarify `cd "$MAIN_ROOT"` comment (Logic #35)

**Files:** Modify `skills/status.md:313-315`

- [ ] **Step 1: Read the block**

```bash
sed -n '310,320p' skills/status.md
```

- [ ] **Step 2: Replace the block to match reality (cd is in main shell, not subshell)**

Old:
```bash
    # 使用 subshell 不改变当前目录
    cd "$MAIN_ROOT"
    
    # 动态检测默认分支（适用于 main/master/develop 等）
```

New:
```bash
    # cd 到主项目根目录（需要改变当前目录用于后续 git checkout/merge）
    cd "$MAIN_ROOT"
    
    # 动态检测默认分支（适用于 main/master/develop 等）
```

- [ ] **Step 3: Commit**

```bash
git add skills/status.md
git commit -m "fix(status): correct misleading subshell comment for cd (CODE_REVIEW #35)

status.md line 313 had '# 使用 subshell 不改变当前目录'
above a plain 'cd \"\$MAIN_ROOT\"'. A plain cd is NOT in a
subshell — it changes the current shell's directory. The
comment was either a copy-paste from a different block that
did use subshell, or described intended behaviour that wasn't
implemented.

Replaced with an accurate comment: the cd is intentional,
we need to change directory in this shell so subsequent
git checkout/merge commands operate on the main repo.

Closes CODE_REVIEW.md issue #35 in skills/status.md."
```

---

## Task A2: Fix `grep -E` quote nesting (Medium #23)

**Files:** Modify `skills/guide.md:612`

- [ ] **Step 1: Read the line**

```bash
sed -n '610,616p' skills/guide.md
```

- [ ] **Step 2: Replace line 612 (extract pattern to variable)**

Old:
```bash
SCOPE_FILES=$(grep -E '^[ \t]*-[ \t]*('src/|file:)' "$proposal_path" 2>/dev/null | ...)
```

New:
```bash
scope_pattern='^[ \t]*-[ \t]*(src/|file:)'
SCOPE_FILES=$(grep -E "$scope_pattern" "$proposal_path" 2>/dev/null | ...)
```

- [ ] **Step 3: Verify bash syntax**

```bash
awk '/^```bash$/,/^```$/' skills/guide.md > /tmp/check.sh
bash -n /tmp/check.sh && echo "SYNTAX OK"
```

- [ ] **Step 4: Commit**

```bash
git add skills/guide.md
git commit -m "fix(guide): extract grep -E pattern to variable to avoid quote nesting (CODE_REVIEW #23)

'grep -E \\'^[ \\t]*-[ \\t]*('src/|file:)\\'' has nested single
quotes that close the outer shell string prematurely, making
the regex effectively '^[ \\t]*-[ \\t]*(' which matches very
little useful content. The original code silently matches
nothing instead of erroring.

Extracting the pattern to a variable and using double quotes
around the grep argument avoids the nesting entirely. The
variable is bash-safe (no metacharacters in the value).

Closes CODE_REVIEW.md issue #23 in skills/guide.md."
```

---

## Task A1: Add `|| exit 1` guard to `cd "$WORKTREE_PATH"` (Medium #22)

**Files:** Modify `skills/guide.md:1012`

- [ ] **Step 1: Read the line**

```bash
sed -n '1010,1015p' skills/guide.md
```

- [ ] **Step 2: Replace line 1012**

Old:
```bash
cd "$WORKTREE_PATH"
```

New:
```bash
cd "$WORKTREE_PATH" || { echo "❌ 无法进入 worktree 目录: $WORKTREE_PATH"; exit 1; }
```

- [ ] **Step 3: Verify bash syntax**

```bash
awk '/^```bash$/,/^```$/' skills/guide.md > /tmp/check.sh
bash -n /tmp/check.sh && echo "SYNTAX OK"
```

- [ ] **Step 4: Commit**

```bash
git add skills/guide.md
git commit -m "fix(guide): guard cd to worktree against missing path (CODE_REVIEW #22)

A plain 'cd \$WORKTREE_PATH' silently continues execution in
the current directory if the worktree path is invalid. The
subsequent 'skill_use(\"rdd-workflow-execute\")' then runs
in the wrong place, producing confusing errors.

Added '|| { echo error; exit 1; }' guard so the script fails
loudly with a clear message instead.

Closes CODE_REVIEW.md issue #22 in skills/guide.md."
```

---

## Task A4: Robust `grep` for "status: 待创建" (Logic #36)

**Files:**
- Modify `skills/guide.md:1193`
- Modify `skills/propose.md:657`
- Modify `skills/status.md:397`

- [ ] **Step 1: Read all 3 sites**

```bash
echo "=== guide.md:1193 ==="; sed -n '1191,1195p' skills/guide.md
echo "=== propose.md:657 ==="; sed -n '655,659p' skills/propose.md
echo "=== status.md:397 ==="; sed -n '395,399p' skills/status.md
```

- [ ] **Step 2: Replace `guide.md:1193`**

Old:
```bash
        REMAINING_SUGGESTIONS=$(grep -c "status: 待创建" "proposal-suggestions.md" 2>/dev/null || echo "0")
```

New:
```bash
        REMAINING_SUGGESTIONS=$(grep -ciE "status\s*[:=]\s*待创建" "proposal-suggestions.md" 2>/dev/null || echo "0")
```

- [ ] **Step 3: Replace `propose.md:657`**

Old:
```bash
    REMAINING=$(grep -c "status: 待创建" "proposal-suggestions.md" 2>/dev/null || echo "0")
```

New:
```bash
    REMAINING=$(grep -ciE "status\s*[:=]\s*待创建" "proposal-suggestions.md" 2>/dev/null || echo "0")
```

- [ ] **Step 4: Replace `status.md:397`**

Old:
```bash
        REMAINING=$(grep -c "status: 待创建" "proposal-suggestions.md" 2>/dev/null || echo "0")
```

New:
```bash
        REMAINING=$(grep -ciE "status\s*[:=]\s*待创建" "proposal-suggestions.md" 2>/dev/null || echo "0")
```

- [ ] **Step 5: Verify bash syntax on all 3 files**

```bash
for f in skills/guide.md skills/propose.md skills/status.md; do
    echo "=== $f ==="
    awk '/^```bash$/,/^```$/' "$f" > /tmp/check.sh
    bash -n /tmp/check.sh && echo "OK"
done
```

- [ ] **Step 6: Commit**

```bash
git add skills/guide.md skills/propose.md skills/status.md
git commit -m "fix(guide,propose,status): robust grep for 'status: 待创建' marker (CODE_REVIEW #36)

The exact-match pattern 'grep -c \"status: 待创建\"' breaks if:
- the file has different whitespace (tab vs space)
- the separator is '=' instead of ':'
- the field name is in a different case

Replaced with 'grep -ciE \"status\\s*[:=]\\s*待创建\"' which
tolerates whitespace variations and either separator. The
'-i' flag is a bonus (case-insensitive, in case someone
capitalises 'Status' or writes it in English).

Files fixed: skills/guide.md:1193, skills/propose.md:657,
skills/status.md:397.

Closes CODE_REVIEW.md issue #36 in 3 files."
```

---

## Task A11: Final Validation

- [ ] **Step 1: Negative regression grep (after-state)**

```bash
echo "=== grep -oE (portability) ==="; git grep -nE 'grep -oE' skills/ install.sh
echo "=== bash indirect \${!var} ==="; git grep -nE '\$\{![a-z_]+\}' skills/ install.sh
echo "=== sed with \$PROJECT_ROOT ==="; git grep -nE "sed.*\\\$PROJECT_ROOT" skills/ install.sh
echo "=== git show HEAD: ==="; git grep -nE "git show HEAD:" skills/ install.sh
echo "=== cd \"\\\$WORKTREE_PATH\" without || ==="; git grep -nE 'cd "\$WORKTREE_PATH"$' skills/ install.sh
echo "=== grep -E with nested 'src/|file:' ==="; git grep -nE "grep -E '.*\\('src/" skills/ install.sh
echo "=== curl | bash ==="; git grep -nE 'curl.*\|.*bash' skills/ install.sh
echo "=== 'status: 待创建' exact match ==="; git grep -nE 'grep -c "status: 待创建"' skills/ install.sh
echo "=== package.json git/cmake in deps ==="; grep -A1 '"dependencies"' package.json
echo "=== subshell misleading comment ==="; grep -B1 'cd "$MAIN_ROOT"' skills/status.md
```

Expected: zero matches (or the only matches are the new portable/fixed patterns).

- [ ] **Step 2: Verify all modified files pass `bash -n`**

```bash
for f in skills/guide.md skills/execute.md skills/status.md skills/plan.md skills/propose.md skills/deps.md skills/INSTALL.md; do
    echo "=== $f ==="
    awk '/^```bash$/,/^```$/' "$f" > /tmp/check.sh
    bash -n /tmp/check.sh && echo "OK"
done
```

Expected: every file reports "OK".

- [ ] **Step 3: Validate package.json**

```bash
python3 -c "import json; json.load(open('package.json'))" && echo "JSON OK"
```

- [ ] **Step 4: Confirm 10 commits on top of Round 1 spec**

```bash
git log --oneline 5143a07..HEAD
```

Expected: 10 commits, each starting with `fix(`, referencing a CODE_REVIEW number.

- [ ] **Step 5: Confirm only intended files changed**

```bash
git diff --stat 5143a07..HEAD
```

Expected: 7 files (`skills/guide.md`, `skills/execute.md` (unchanged), `skills/status.md`, `skills/plan.md`, `skills/propose.md`, `skills/deps.md`, `skills/INSTALL.md`, `package.json`).

- [ ] **Step 6: Show the full commit log**

```bash
git log --oneline -15
```

Expected: Round 2a spec `5143a07` + 10 fix commits + Round 1 commits + prior history.

---

## Out-of-Scope (Round 2b — needs user decisions)

- Inconsistency #37: skill name standardization
- Inconsistency #38: `PROJECT_ROOT` definition unification
- Inconsistency #40: `workflow-state.md` format alignment between guide.md and USAGE.md
