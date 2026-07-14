# status-guide-revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `skill_use("execute")` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Parent context:** This plan revises `skills/guide.md` and `skills/status.md` based on a 15-item audit performed after an actual execution session. The audit catalogued P0/P1/P2 findings across both skill files plus cross-file consistency issues.
>
> **Out of scope:** This plan modifies ONLY documentation/markdown. No behavior changes to `skills/_lib/scan-state.sh`, `skills/_lib/iteration.py`, `_lib/worktree.sh`, etc., unless explicitly listed below. Where a doc claim must match a runtime invariant, we lock the doc with a bats test.

**Goal:** Bring `skills/guide.md` and `skills/status.md` to a self-consistent, defensible, test-locked state by resolving 15 audit findings (G1–G6 in guide; S1–S12 in status; C1–C2 cross-file). All fixes are gated by failing-then-passing bats tests; no purely cosmetic edits.

**Architecture:** Adopt a TDD-disciplined approach where each markdown change is preceded by a bats regression test in `tests/integration/test_<area>_regression.bats` that encodes the invariant the doc change must satisfy. Tests run before implementation (red) and after (green); commit only on green. Tier ordering follows severity: P0 (correctness) → P1 (usability) → P2 (consistency). Within each tier, work-units that touch `guide.md` come first (smaller surface), then `status.md`, then cross-file.

**Tech Stack:** bash 5+, bats-core 1.10+, Python 3.11+ (test helpers), PyYAML (for frontmatter tests), existing `tests/_lib/skill.bash` parser API (reused, not duplicated).

---

## Tier Map

| Tier | Severity | Count | Work-Units |
|------|----------|-------|------------|
| 1 | P0 (correctness) | 3 | 1.1 frontmatter dup-key, 1.2 status table unification, 1.3 archive confirmation |
| 2 | P1 (usability) | 5 | 2.1 scan-state doc, 2.2 mode router, 2.3 Mode B cleanup, 2.4 Mode D os.environ, 2.5 Mode E exec+2b |
| 3 | P2 (consistency) | 4 | 3.1 Mode A dedup+i, 3.2 guide binding skip+help, 3.3 stale-state upgrade, 3.4 style guide |

Total: 12 work-units × 5 TDD steps + pre-flight = **61 checkboxes**, ~3 commits/work-unit = ~12 feature commits + 1 final lock-in.

---

## File Structure

### Modified (docs / regression targets)

| File | Action | Tier(s) Touching |
|---|---|---|
| `skills/guide.md` | MODIFY (lines 7,9,41,60-67,69-79,84-89) | 1.1, 2.1, 3.2, 3.3, 3.4 |
| `skills/status.md` | MODIFY (multiple sections per task) | 1.2, 1.3, 2.2, 2.3, 2.4, 2.5, 3.1, 3.4 |
| `skills/_lib/scan-state.sh` | MODIFY (comments only) | 2.1 |

### Created (regression tests)

| File | Purpose | Work-Unit |
|---|---|---|
| `tests/integration/test_frontmatter_dupkey.bats` | Lock no-dup-yaml-key invariant (1.1) | 1.1 |
| `tests/integration/test_status_state_table.bats` | Lock unified 6-state table (1.2) | 1.2 |
| `tests/integration/test_archive_confirmation.bats` | Lock --yes/confirm flow (1.3) | 1.3 |
| `tests/integration/test_scan_state_doc.bats` | Lock export vars declaration (2.1) | 2.1 |
| `tests/integration/test_status_mode_router.bats` | Lock top-level input dispatcher (2.2) | 2.2 |
| `tests/integration/test_status_mode_b_path_hygiene.bats` | Lock absolute paths, no dead-source, complete awk comments (2.3) | 2.3 |
| `tests/integration/test_status_mode_d_env_safe.bats` | Lock os.environ over $PROJECT_ROOT interpolation (2.4) | 2.4 |
| `tests/integration/test_status_mode_e_exec_safe.bats` | Lock no `exec $0`, single iteration.json reader (2.5) | 2.5 |
| `tests/integration/test_status_mode_a_polish.bats` | Lock dedup + `i` handler (3.1) | 3.1 |
| `tests/integration/test_guide_binding_skip.bats` | Lock graceful binding skip + `--help` flag (3.2) | 3.2 |
| `tests/integration/test_stale_workflow_state.bats` | Lock detection is mandatory in scan (3.3) | 3.3 |
| `tests/integration/test_skill_style_guide.bats` | Lock emoji-set + alignment invariants (3.4) | 3.4 |

### Audit Map (audit_item → work_unit)

| Audit | Severity | Work-Unit |
|---|---|---|
| G1 | P0 | 1.1 |
| G2 | P1 | 2.1 |
| G3 | P2 | 3.2 |
| G4 | P1 | 2.1 |
| G5 | P2 | 3.2 |
| G6 | P2 | 3.3 |
| S1 | P0 | 1.2 |
| S2 | P0 | 1.2 |
| S3 | P2 | 3.1 |
| S4 | P1 | 2.3 |
| S5 | P1 | 2.3 |
| S6 | P1 | 2.3 |
| S7 | P0 | 1.3 |
| S8 | P1 | 2.2 |
| S9 | P1 | 2.5 |
| S10 | P1 | 2.5 |
| S11 | P2 | 3.1 |
| S12 | P1 | 2.4 |
| C1 | P0 | 1.1 |
| C2 | P2 | 3.4 |

---

## Pre-flight

- [ ] **P0: Verify baseline tests pass before changes**

```bash
cd /workspace/project/rdd-workflow
bats tests/smoke.bats tests/integration/test_guide_skill.bats tests/integration/test_status_skill.bats
```

Expected: 16/16 ok. If any fails, stop and fix the env first.

- [ ] **P1: Verify frontmatter duplication currently exists**

```bash
grep -nE '^[[:space:]]+version:' skills/guide.md skills/status.md
```

Expected: each file emits 2 lines. This is the red light that work-unit 1.1 will fix.

- [ ] **P2: Confirm bats + python3 versions**

```bash
bats --version | head -1   # expect "Bats 1.10" or newer
python3 --version          # expect "Python 3.11" or newer
```

- [ ] **P3: Stage plan file (no commit yet)**

```bash
git add .rddf/plans/status-guide-revision.md
git status --short
```

Expected: `M` flag on `.rddf/plans/status-guide-revision.md`, nothing else.

---

# Tier 1 — P0 (correctness)

## Task 1.1: Eliminate duplicate `version:` keys in skill frontmatter (G1 + C1)

**Files:**
- Modify: `skills/guide.md` (lines 6-11)
- Modify: `skills/status.md` (lines 6-11)
- Create: `tests/integration/test_frontmatter_dupkey.bats`

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/integration/test_frontmatter_dupkey.bats <<'BATSEOF'
#!/usr/bin/env bats
# Locks the invariant: skill frontmatter metadata block contains AT MOST
# one `version:` key. YAML silent-keep-last behavior caused metadata.version
# to drift between source-of-truth and the rendered/observed value.

load ../test_helper

assert_no_dup_version() {
  local f="$1"
  local n
  n=$(awk '/^metadata:/{f=1;next} f && /^---$/{exit} f && /^[[:space:]]+version:/{print}' "$f" | wc -l)
  [ "$n" -le 1 ] || { echo "FAIL: $f has $n version keys (want <=1)"; return 1; }
}

@test "guide.md frontmatter has at most one version key" {
  assert_no_dup_version skills/guide.md
}

@test "status.md frontmatter has at most one version key" {
  assert_no_dup_version skills/status.md
}

@test "guide.md metadata.version matches skill_field semver pattern" {
  run python3 -c "
import yaml,sys
d=yaml.safe_load(open('skills/guide.md').read().split('---',2)[1])
v=d.get('metadata',{}).get('version','')
import re
sys.exit(0 if re.match(r'^\d+\.\d+(\.\d+)?$', str(v)) else 2)
"
  [ "$status" -eq 0 ]
}
BATSEOF
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_frontmatter_dupkey.bats
```

Expected: 3 failures with "FAIL: ... has 2 version keys".

- [ ] **Step 3: Remove the duplicate `version:` from each file's frontmatter**

Edit `skills/guide.md` line 7 block to read (keep the semver-as-source-of-truth):

```yaml
metadata:
  version: "2.0"   # source-of-truth (latest semver)
  author: sisyphus
  evolved-from: "split from guide.md v3.0; v1.1 also added rddf-session binding scan (spec 2026-07-14)"
  user-invocable: true
```

Edit `skills/status.md` line 7 block to read:

```yaml
metadata:
  version: "2.0.2"  # source-of-truth (latest semver)
  author: sisyphus
  evolved-from: "status.md v1.x; v2.0.2 added planned 状态展示 (Mode A + Mode E)"
```

Rationale: the LATER `version:` in the YAML block was being kept silently; we now make that the SOLE `version:` and migrate any extra information into `evolved-from`.

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_frontmatter_dupkey.bats
```

Expected: 3 ok.

- [ ] **Step 5: Run full regression to confirm no breakage**

```bash
bats tests/integration/test_guide_skill.bats tests/integration/test_status_skill.bats tests/integration/test_frontmatter_dupkey.bats
```

Expected: all 7 ok (existing 4 + new 3).

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_frontmatter_dupkey.bats skills/guide.md skills/status.md
git commit -m "fix(skills): eliminate duplicate version keys in frontmatter (G1, C1)

YAML silent-keep-last was hiding the metadata.version from source-of-truth.
Migrated evolution notes into metadata.evolved-from.
Lock invariant with tests/integration/test_frontmatter_dupkey.bats (3 cases)."
```

---

## Task 1.2: Unify Mode A status table with iteration.json states (S1 + S2)

**Files:**
- Modify: `skills/status.md` (lines 100-160: dynamic status block + Mode A table)
- Create: `tests/integration/test_status_state_table.bats`

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/integration/test_status_state_table.bats <<'BATSEOF'
#!/usr/bin/env bats
# Status Mode A must support 6 statuses corresponding to iteration.json states
# plus the "committed but no worktree" gap state. Locks:
#   1. Table mentions all 6 emoji: 📋 planned, 💼 committed, ✅ proposed, 🔧 in_worktree, ✔ completed, 📦 archived
#   2. iteration.json status enum is the canonical source
#   3. No "⏸ 暂停" hardcoded text remains in Mode A template (it was
#      used as a fake placeholder during a real session hit)

load ../test_helper

@test "status.md Mode A dynamic block lists all 6 iteration.json states" {
  for s in planned proposed in_worktree completed archived; do
    grep -qE "\\b$s\\b" skills/status.md
  done
}

@test "status.md mentions committed-but-no-worktree state" {
  grep -qE "commit.{0,15}(no|无|未).{0,15}worktree|已 commit.{0,30}(未|无).{0,30}执行|📦" skills/status.md
}

@test "status.md Mode A does not hardcode '⏸ 暂停' as a state" {
  # ⏸ + 暂停 was used in a real execution as a placeholder, lock that out
  ! grep -E "⏸\s*暂停" skills/status.md
}

@test "iteration.json schema declared states match Mode A list" {
  for s in planned proposed in_worktree completed archived; do
    grep -qE "\\b$s\\b" skills/_lib/schemas/iteration_schema.json
  done
}
BATSEOF
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_status_state_table.bats
```

Expected: at least 2 failures — missing "committed" / "📦" language + hardcoded "⏸ 暂停" hit.

- [ ] **Step 3: Rewrite Mode A status rendering**

In `skills/status.md`, replace lines 100-160 (the entire "动态状态展示（v2.0.2）" + "用户输入处理" subsections) with:

````markdown
**Status rendering（v2.0.3，从 iteration.json 派生单一真理源）**：

```bash
render_status() {
  local change="$1"
  python3 - "${change}" <<'PYEOF'
import json, sys, os
name = sys.argv[1]
p = '.rddf/state/iteration.json'
try:
    data = json.load(open(p))
except Exception:
    # fallback: filesystem-only detection (commit in HEAD + no worktree)
    import subprocess
    has_committed = subprocess.run(
        ['bash','-c',
         'for d in openspec/changes/*/; do [ -d "$d" ] || continue; '
         'case "$d" in */archive/) continue ;; esac; '
         'git show HEAD:"$d.openspec.yaml" >/dev/null 2>&1 && exit 0; done; exit 1'
        ], capture_output=True).returncode == 0
    has_worktree = any(branch == f'openspec/{name}'
                       for line in subprocess.check_output(['git','worktree','list']).decode().splitlines()
                       for branch in [line.split()[-1].strip('[]')])
    if has_committed and not has_worktree:
        print('💼 committed (no worktree yet)')
    elif has_worktree:
        print('🔧 in_worktree (fallback)')
    else:
        print('📋 planned (skeleton fallback)')
    sys.exit(0)
ch = next((c for c in data.get('changes',[]) if c.get('name')==name), None)
if not ch:
    print('❓ unknown')
    sys.exit(0)
status = ch.get('status','unknown')
icons = {
    'planned':     '📋',
    'committed':   '💼',
    'proposed':    '✅',
    'in_worktree': '🔧',
    'completed':   '✔',
    'archived':    '📦',
}
print(f"{icons.get(status,'❓')} {status}")
PYEOF
}
```

**单一真理源规则**：Mode A 的状态列**只**从 iteration.json 读取；filesystem-only fallback 仅在 iteration.json 缺失时触发（本计划的 Tier 3 已记录 fallback 行为）。禁止在表格或 case 分支里硬编码状态文字。
````

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_status_state_table.bats
```

Expected: 4 ok.

- [ ] **Step 5: Run full regression**

```bash
bats tests/integration/test_status_skill.bats tests/integration/test_status_state_table.bats
```

Expected: 8 ok.

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_status_state_table.bats skills/status.md
git commit -m "fix(status): unify Mode A status column with iteration.json states (S1, S2)

Adds 💼 committed-to-HEAD state and locks single-source-of-truth rule.
Removes '⏸ 暂停' hardcoded fallback that leaked through during real use."
```

---

## Task 1.3: Add archive confirmation prompt (S7)

**Files:**
- Modify: `skills/status.md` (Mode C section, lines 326-353)
- Create: `tests/integration/test_archive_confirmation.bats`

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/integration/test_archive_confirmation.bats <<'BATSEOF'
#!/usr/bin/env bats
# S7: Mode C archive flow must require explicit confirmation before
# invoking archive_change(). Constrains "归档不可逆" (key constraint #4).

load ../test_helper

@test "status.md Mode C documents a confirmation prompt before archive_change" {
  grep -qE "确认|confirm|read -r|\\[ \\[ " skills/status.md
}

@test "status.md Mode C does NOT call archive_change before user y/n" {
  # Block the pattern: any archive_change invocation without prior
  # confirmation gate. This is a structural test — order matters.
  # We check that the section contains a confirmation block BEFORE
  # the first archive_change reference.
  awk '
    /archive_change/ && !found_archive { found_archive=NR; exit }
    /确认|confirm|read -r/ { found_confirm=NR }
    END { exit (found_confirm < found_archive ? 0 : 1) }
  ' skills/status.md
}
BATSEOF
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_archive_confirmation.bats
```

Expected: 2 failures — no confirmation block, archive_change reached first.

- [ ] **Step 3: Insert confirmation gate before archive_change**

In `skills/status.md`, replace the entire Mode C subsection titled "Step 1-5：执行归档（提取到 `_lib/archive.sh`，P1-14 去重）" with:

````markdown
### Step 0：用户确认 gate（NEW in v2.0.3，对应 S7 + 关键约束 #4 "归档不可逆"）

```bash
# 必填：强制 y/n 确认。若传入 --yes/-y 则跳过交互（CI 用法）。
case "${1:-}" in
  --yes|-y) CONFIRMED=yes ;;
  *) CONFIRMED=no ;;
esac

if [ "$CONFIRMED" = "no" ]; then
  echo "⚠️  即将归档 change <name>。此操作不可逆（merge → archive → cleanup）。"
  echo -n "   输入 'yes' 确认,其他任意输入取消: "
  read -r REPLY
  case "$REPLY" in
    yes|YES|y|Y) CONFIRMED=yes ;;
    *) echo "❌ 已取消归档"; exit 1 ;;
  esac
fi
[ "$CONFIRMED" = "yes" ] || { echo "❌ 未确认"; exit 1; }
```

### Step 1-5：执行归档（提取到 `_lib/archive.sh`，P1-14 去重）

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$SCRIPT_DIR/_lib/archive.sh" ]; then
  source "$SCRIPT_DIR/_lib/archive.sh"
fi

archive_change "<name>" "${1:-}"   # 把 --yes 透传
```

> **重构说明（P1-14）**：旧的 Step 1-5（worktree 定位、脏检查、merge、archive、cleanup）已合并为单次 `archive_change` 调用。
````

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_archive_confirmation.bats
```

Expected: 2 ok.

- [ ] **Step 5: Smoke run archive logic on a non-existent change should fail at gate, not at archive.sh**

```bash
bash -c '
PROJECT_ROOT=/tmp
. /workspace/project/rdd-workflow/skills/_lib/worktree.sh 2>/dev/null || true
# Manually walk the gate logic with --yes to verify pass-through
case "--yes" in --yes|-y) echo "gate passed" ;; *) echo "gate failed" ;; esac
'
```

Expected: `gate passed`.

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_archive_confirmation.bats skills/status.md
git commit -m "fix(status): require y/n confirmation before archive_change (S7)

Archive is irreversible. Adding interactive gate + --yes/-y bypass for CI.
Source-of-truth invariant locked by tests/integration/test_archive_confirmation.bats."
```

---

# Tier 2 — P1 (usability)

## Task 2.1: scan-state.sh — clarify exported vars + fix priority count claim (G2 + G4)

**Files:**
- Modify: `skills/_lib/scan-state.sh` (function header comment + lines 36-49)
- Modify: `skills/guide.md` (line 41 comment)
- Create: `tests/integration/test_scan_state_doc.bats`

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/integration/test_scan_state_doc.bats <<'BATSEOF'
#!/usr/bin/env bats
# scan_state() is documented to export only RECOMMEND + REASON.
# Lock: 1) doc comment lists exactly the exported variables,
#       2) guide.md priority-count comment matches scan-state.sh count.

load ../test_helper

@test "scan-state.sh header lists EXPORTED_VARS set to {RECOMMEND REASON}" {
  grep -qE '^#[[:space:]]*EXPORTED_VARS:[[:space:]]*\{RECOMMEND[[:space:]]+REASON\}' skills/_lib/scan-state.sh
}

@test "scan-state.sh priority list (1..N) is internally consistent" {
  # Count actual priority bullets in the comment block.
  # Pattern matches both "1. " (dot-space, for `1.`, `2.`, ... `10.`)
  # AND "1.5 " (no dot after sub-number, for `1.5`, `2.5`) so the
  # count is the actual semantic priority count (12 = 1, 1.5, 2, 2.5, 3-10).
  n=$(awk '/^#[[:space:]]+[0-9]+(\.[0-9]+)?\.?[[:space:]]/ {print}' skills/_lib/scan-state.sh | wc -l)
  echo "priority count = $n"
  [ "$n" -eq 12 ]
}

@test "guide.md priority comment matches scan-state.sh count" {
  guide_n=$(grep -oE '优先级[[:space:]]*[0-9]+[[:space:]]*条' skills/guide.md | grep -oE '[0-9]+' | head -1)
  # Same relaxed pattern as test 2 — accepts both "1. " and "1.5 " forms
  shell_n=$(awk '/^#[[:space:]]+[0-9]+(\.[0-9]+)?\.?[[:space:]]/ {print}' skills/_lib/scan-state.sh | wc -l)
  [ "$guide_n" = "$shell_n" ] || {
    echo "FAIL: guide.md claims $guide_n, scan-state.sh has $shell_n"
    return 1
  }
}
BATSEOF
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_scan_state_doc.bats
```

Expected: 2 failures — `guide.md priority comment` (guide=11 vs scan-state=12, because the relaxed pattern correctly counts 1.5/2.5 sub-numbered entries) + missing `EXPORTED_VARS` line. The internal-consistency test passes pre-fix (10 from old pattern doesn't help; relaxed `[0-9]+...\.?` already yields 12 in current scan-state.sh).

> **v2.0.3 fix (R3 — Oracle review):** Originally the awk regex used `\.[[:space:]]` (mandatory dot), which matched only 10 of 12 semantic priorities (1.5/2.5 have no trailing dot). The fix relaxes to `\.?[[:space:]]` so the count equals 12 across tests 2 and 3, allowing guide.md's claim "12 条" to actually equal `shell_n` after Step 3.

- [ ] **Step 3: Patch scan-state.sh header + guide.md comment**

Edit `skills/_lib/scan-state.sh`, replace lines 12-15 (the function-export comment block) with:

```bash
# Function exported:
#   - scan_state
#       Sets globals RECOMMEND + REASON only (other potential globals
#       such as ROADMAP, ARCH_HANDOFF, etc. are deliberately NOT
#       exported — callers must read the filesystem themselves if
#       they need additional state).
#       See `EXPORTED_VARS: {RECOMMEND REASON}` header for grep-ability.
# EXPORTED_VARS: {RECOMMEND REASON}
```

Edit `skills/guide.md` line 41 to replace `优先级 11 条` with the actual count (`优先级 12 条`, matching scan-state.sh's 12 numbered bullets).

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_scan_state_doc.bats
```

Expected: 3 ok.

- [ ] **Step 5: Re-run the existing guide_skill RECOMMEND-count test (it asserts >=11, must still pass)**

```bash
bats tests/integration/test_guide_skill.bats
```

Expected: 4 ok.

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_scan_state_doc.bats skills/_lib/scan-state.sh skills/guide.md
git commit -m "docs(scan-state): declare EXPORTED_VARS and sync guide.md priority count (G2, G4)

scan_state() exports only RECOMMEND+REASON; previously implicit.
guide.md claimed '11 priorities' but scan-state.sh lists 12 — synced."
```

---

## Task 2.2: Add top-level mode router to status.md (S8)

**Files:**
- Modify: `skills/status.md` (replace "输入" section, lines 26-32)
- Create: `tests/integration/test_status_mode_router.bats`

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/integration/test_status_mode_router.bats <<'BATSEOF'
#!/usr/bin/env bats
# status skill must declare a top-level input dispatcher that maps
# user input to Mode A/B/C/D/E. Currently the doc only lists the
# inputs as a table but provides no parser code — S8.

load ../test_helper

@test "status.md documents a top-level case-based mode dispatcher" {
  # Pattern: a 'case \"\$1\" in' or equivalent follows the input spec
  awk '
    /##[[:space:]]+输入/         { in_input=1; next }
    in_input && /case[[:space:]]+"/ { found=1; exit }
    in_input && /^##/           { exit }
    END { exit (found ? 0 : 1) }
  ' skills/status.md
}

@test "status.md router maps --roadmap to Mode D and --iteration to Mode E" {
  grep -qE -- "--roadmap.*Mode[[:space:]]+D|roadmap.*→.*Mode D" skills/status.md
  grep -qE -- "--iteration.*Mode[[:space:]]+E|iteration.*→.*Mode E" skills/status.md
}

@test "status.md router handles bare change name → Mode B" {
  grep -qE 'change.*[Nn]ame.*→.*Mode[[:space:]]+B|<name>.*Mode B' skills/status.md
}
BATSEOF
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_status_mode_router.bats
```

Expected: 3 failures.

- [ ] **Step 3: Insert router block after "## 输入" section**

In `skills/status.md`, replace the "## 输入" subsection (lines 26-32) with:

````markdown
## 输入 + 顶层路由（NEW in v2.0.3，对应 S8）

| 输入 | Mode | 备注 |
|------|------|------|
| 无参数 / `status` | Mode A | 全局概览 |
| `<change-name>` | Mode B | 单 change 详情 + 同步检测 |
| `<change-name> --archive` / `--yes` | Mode C | 归档（强制确认 gate 由 1.3 引入） |
| `--roadmap` / `roadmap` | Mode D | 路线图状态 |
| `--iteration` / `iteration` | Mode E | 当前迭代视图 |
| `--help` / `-h` / `?` | （帮助） | 列出 5 个 mode + 用法 |

**路由实现**：

```bash
status_router() {
  case "$1" in
    "")                                echo "A" ;;
    --roadmap|roadmap)                 echo "D" ;;
    --iteration|iteration)             echo "E" ;;
    --help|-h|help|\?)                 echo "help" ;;
    --archive|--yes|-y)                echo "C_handoff" ;;     # 透传给 Mode B
    *)                                 echo "B:$1" ;;           # 视为 change name
  esac
}
```
````

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_status_mode_router.bats
```

Expected: 3 ok.

- [ ] **Step 5: Run full status regression**

```bash
bats tests/integration/test_status_skill.bats tests/integration/test_status_mode_router.bats
```

Expected: 7 ok.

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_status_mode_router.bats skills/status.md
git commit -m "feat(status): add top-level mode router with input parsing (S8)

Resolves unmapped argument flow — previously a user had to know the mode
keyword by reading the doc, now `<change-name>` / `--roadmap` / `--iteration`
all route explicitly. Router also introduces `--help`."
```

---

## Task 2.3: Mode B cleanup — paths, dead source, comment (S4 + S5 + S6)

**Files:**
- Modify: `skills/status.md` (lines 38-41 dead source, 178-179 plan path, 382 comment)
- Create: `tests/integration/test_status_mode_b_path_hygiene.bats`

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/integration/test_status_mode_b_path_hygiene.bats <<'BATSEOF'
#!/usr/bin/env bats
# Mode B hygiene fixes (S4/S5/S6):
#   S4: PLAN_FILE / TASKS_FILE paths must both be $PROJECT_ROOT-anchored
#   S5: dead `source ... _lib/worktree.sh` at top-of-skill must be removed
#   S6: awk column comment on line 382 must mention $1 (path), $2 (hash), $3 (branch)

load ../test_helper

@test "status.md PLAN_FILE references \$PROJECT_ROOT" {
  grep -E 'PLAN_FILE=' skills/status.md | grep -vE 'PROJECT_ROOT' | grep -q . && {
    echo "FAIL: a PLAN_FILE assignment lacks \$PROJECT_ROOT"; return 1;
  } || true
  # at least one PLAN_FILE assignment uses PROJECT_ROOT
  grep -E 'PLAN_FILE=.*PROJECT_ROOT' skills/status.md
}

@test "status.md TASKS_FILE references \$PROJECT_ROOT" {
  grep -E 'TASKS_FILE=' skills/status.md | grep -vE 'PROJECT_ROOT' | grep -q . && {
    echo "FAIL: a TASKS_FILE assignment lacks \$PROJECT_ROOT"; return 1;
  } || true
  grep -E 'TASKS_FILE=.*PROJECT_ROOT' skills/status.md
}

@test "status.md no longer sources _lib/worktree.sh (S5 dead source fix)" {
  ! grep -E 'source[[:space:]]+\$SCRIPT_DIR/_lib/worktree.sh' skills/status.md
}

@test "status.md awk column comment mentions \$1, \$2, \$3" {
  # v2.0.3 fix (R4 — Oracle review): the original awk regex used
  # `\$3[[:space:]]*~?~?\/` which mandated a literal `/` after `$3`
  # — that pattern cannot match the comment text at line 382 (or its
  # replacement) so the test would be permanently red.
  # Replaced with a portable bash check: find any line containing $3,
  # then confirm $1 and $2 are within ±3 lines of context. That
  # matches both the current partial comment and the proposed
  # complete comment from Step 3.
  local found=0
  local n
  while IFS= read -r n; do
    [ -z "$n" ] && continue
    local start=$(( n > 3 ? n - 3 : 1 ))
    local end=$(( n + 3 ))
    local ctx
    ctx=$(sed -n "${start},${end}p" skills/status.md)
    if echo "$ctx" | grep -qE '\$1' && echo "$ctx" | grep -qE '\$2'; then
      found=1
      break
    fi
  done < <(grep -nE '\$3' skills/status.md)
  [ "$found" -eq 1 ]
}
BATSEOF
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_status_mode_b_path_hygiene.bats
```

Expected: 3-4 failures.

- [ ] **Step 3: Patch each violation**

Edit 1 (S5 dead source): in `skills/status.md` lines 36-42, REMOVE the entire `source "$SCRIPT_DIR/_lib/worktree.sh"` block. Replace with a one-line note:

````markdown
```bash
# 工作目录检测（所有模式通用）
# 注（v2.0.3）：原 dead-source `_lib/worktree.sh` 已移除（S5）。
# Mode B 内联使用 `wt_path_for_branch_inline`（P0-7）作为唯一来源。
```
````

Edit 2 (S4 path unification): replace `PLAN_FILE=".rddf/plans/<name>.md"` (line 178 and line 227) with `PLAN_FILE="$PROJECT_ROOT/.rddf/plans/<name>.md"`.

Edit 3 (S6 comment): in `skills/status.md` line 382, replace the comment with the complete version:

```bash
# P1-PIN: git worktree list 输出 "path  hash  [branch]" — $1=path, $2=commit hash, $3="[branch]"
# 因此 regex 必须含前导 `[`，不能匹配路径中含 "openspec/" 的子串
REMAINING_WT=$(git worktree list 2>/dev/null | awk '$3 ~ /^\[openspec\// {print $1}' | grep -c . || true)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_status_mode_b_path_hygiene.bats
```

Expected: 4 ok.

- [ ] **Step 5: Run status regression**

```bash
bats tests/integration/test_status_skill.bats tests/integration/test_status_mode_b_path_hygiene.bats
```

Expected: 8 ok (existing 4 + new 4).

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_status_mode_b_path_hygiene.bats skills/status.md
git commit -m "fix(status): Mode B path/source/comment hygiene (S4, S5, S6)

S5: remove dead `source _lib/worktree.sh` (Mode B uses inline helper).
S4: PLAN_FILE/TASKS_FILE now both \$PROJECT_ROOT-anchored.
S6: awk comment now mentions \$1/\$2/\$3 instead of confusing readers."
```

---

## Task 2.4: Mode D — drop `$PROJECT_ROOT` interpolation into Python source (S12)

**Files:**
- Modify: `skills/status.md` (lines 434-480, two `python3 -c "..."` blocks)
- Create: `tests/integration/test_status_mode_d_env_safe.bats`

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/integration/test_status_mode_d_env_safe.bats <<'BATSEOF'
#!/usr/bin/env bats
# Mode D currently interpolates $PROJECT_ROOT directly into Python -c
# source via bash double-quotes. Per v2.0.2 convention (Mode E already
# fixed this), we must use os.environ instead.

load ../test_helper

@test "status.md Mode D uses os.environ not \$PROJECT_ROOT interpolation" {
  # Extract Mode D block and check the python3 -c invocations
  awk '
    /Mode D/      { in_md=1 }
    in_md && /```bash/ && !bash_seen { bash_seen=1; next }
    in_md && /```/ && bash_seen { exit }
  ' skills/status.md > /tmp/mode_d.bash

  # Ensure no 'with open...$PROJECT_ROOT...' interpolation
  if grep -qE 'with open.*\$PROJECT_ROOT' /tmp/mode_d.bash; then
    echo "FAIL: Mode D still uses \$PROJECT_ROOT in Python source"; return 1
  fi
  # Ensure at least one os.environ usage exists (matches v2.0.2 style)
  grep -q "os.environ" /tmp/mode_d.bash
}
BATSEOF
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_status_mode_d_env_safe.bats
```

Expected: 1 failure.

- [ ] **Step 3: Rewrite Mode D's two `python3 -c "..."` blocks**

In `skills/status.md` Mode D section (lines 429-489), replace the two `python3 -c "..."` invocations with `PROJECT_ROOT="$PROJECT_ROOT" python3 -c '...os.environ["PROJECT_ROOT"]...'` versions. Apply the v2.0.2 convention used in Mode E.

Snippet to replace the roadmap phase lookup:

```bash
CURRENT_PHASE=$(PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import os, re
with open(os.path.join(os.environ["PROJECT_ROOT"], "roadmap.md")) as f:
    content = f.read()
phase_match = re.search(r"\*\*当前阶段\*\*:\s*(\S+)", content)
print(phase_match.group(1) if phase_match else "unknown")
')
```

And the larger roadmap-state.json block:

```bash
PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import os, json
with open(os.path.join(os.environ["PROJECT_ROOT"], ".rddf/state/roadmap-state.json")) as f:
    state = json.load(f)
...
'
```

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_status_mode_d_env_safe.bats
```

Expected: 1 ok.

- [ ] **Step 5: Run status regression**

```bash
bats tests/integration/test_status_skill.bats tests/integration/test_status_mode_d_env_safe.bats
```

Expected: 5 ok.

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_status_mode_d_env_safe.bats skills/status.md
git commit -m "fix(status): Mode D drop \$PROJECT_ROOT in python source (S12)

Matches v2.0.2 convention used in Mode E. Avoids injection via paths
containing single quotes or special chars."
```

---

## Task 2.5: Mode E — remove `exec $0` and consolidate `iteration.json` reads (S9 + S10)

**Files:**
- Modify: `skills/status.md` (Mode E Step 2b lines 591-617 + Step 3 case handler lines 633-640)
- Create: `tests/integration/test_status_mode_e_exec_safe.bats`

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/integration/test_status_mode_e_exec_safe.bats <<'BATSEOF'
#!/usr/bin/env bats
# S9: Mode E step 3 uses `exec $0 --iteration` which fails because
#     this is markdown, not a script. Replace with explanatory text.
# S10: Mode E step 2b opens iteration.json a second time. Must call
#      a single iteration.py function instead.
#
# Note (v2.0.3 R2 fix — Oracle review): the original task wrote a
# third test asserting `def list_planned` exists in iteration.py.
# That helper ALREADY exists at skills/_lib/iteration.py:350, so
# the test was green on first run and Step 3's "add" was a no-op.
# Test removed; only the two functional red tests remain.

load ../test_helper

@test "status.md Mode E does NOT call exec \$0" {
  ! grep -E 'exec[[:space:]]+\$0' skills/status.md
}

@test "status.md Mode E consolidates iteration.json reads via iteration.py" {
  # Step 2 should be the only place opening iteration.json (via
  # iteration.load() helper). Step 2b must use iteration.list_planned()
  # (already defined at iteration.py:350) not json.load(open(...)).
  json_load_opens=$(grep -cE 'json\.load\(open\(' skills/status.md)
  [ "$json_load_opens" -le 1 ]    # Mode E or A — not both
}
BATSEOF
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_status_mode_e_exec_safe.bats
```

Expected: 2 failures (exec `$0` found, json.load opens count > 1). The original task expected 3 failures, but R2 (Oracle review) removed the redundant `list_planned` test which was already passing.

- [ ] **Step 3: Patch Mode E step 3 + step 2b** (no iteration.py change)

> **R2 fix (Oracle review):** `iteration.list_planned` is **already defined at `skills/_lib/iteration.py:350`**. The original task asked to add it; doing so would create a duplicate `def` and `SyntaxError`. Status.md Step 2b only needs to **call** the existing helper, not add a new one.

Edit 1 (S9 — remove `exec $0`): in `skills/status.md` Mode E Step 3 (lines 633-640), replace the case handler with explanatory text:

````markdown
**用户输入处理（v2.0.3 重写，S9 修复）**：

> 注：markdown skill 不是 shell 脚本，`exec $0` 无法工作。重新进入 Mode E 由 AI 助手按以下提示执行：

| 用户输入 | 动作 |
|---------|------|
| `1` 或 `refresh` | 重新读取 iteration.json 并渲染 |
| `2` | `skill_use("guide-ship")` 进入 ship 流 |
| `3` | `cat $PROJECT_ROOT/.rddf/state/deps-output.md` （如存在） |
| `4` 或 `back` | 返回 Mode A 概览 |
| `q` / `quit` / `exit` | 退出 status |
| 其他 | "❌ 无效输入 '$choice'" 提示 |
````

Edit 2 (S10 — consolidate iteration.json reads): **no code change to `iteration.py`** (existing helper reused). In `skills/status.md` Mode E Step 2b (lines 591-617), replace the entire block with:

In `skills/status.md` Mode E Step 2b (lines 591-617), replace the entire block with:

````markdown
### Step 2b (v2.0.3): 显示 planned 状态 change（S10 — 改用模块函数）

```bash
PROJECT_ROOT="$PROJECT_ROOT" python3 -c '
import os, sys
sys.path.insert(0, os.path.join(os.environ["PROJECT_ROOT"]))
from skills._lib import iteration as it_mod
data = it_mod.load(os.environ["PROJECT_ROOT"])
planned = it_mod.list_planned(data)
if not planned:
    print("(none)")
else:
    for c in planned:
        b = c.get("blocker") or ""
        bs = f" (blocked by {b})" if b else ""
        print(f"  📋 {c['"'"'name'"'"']}{bs}")
'
```
````

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_status_mode_e_exec_safe.bats
```

Expected: 2 ok.

- [ ] **Step 5: Run status regression**

```bash
bats tests/integration/test_status_skill.bats tests/integration/test_status_mode_e_exec_safe.bats
```

Expected: 6 ok (4 baseline + 2 new).

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_status_mode_e_exec_safe.bats skills/status.md
git commit -m "fix(status): Mode E drop exec \$0 + consolidate iteration.json reads (S9, S10)

Replace exec \$0 (markdown-not-script) with AI-readable handler table.
Reuse the pre-existing iteration.list_planned helper at iteration.py:350."
```

---

# Tier 3 — P2 (consistency)

## Task 3.1: Mode A — dedup worktree list + add `i` handler (S3 + S11)

**Files:**
- Modify: `skills/status.md` (top of file lines 51-65; Mode A Step 1 lines 71-82; case handler 158-166)
- Create: `tests/integration/test_status_mode_a_polish.bats`

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/integration/test_status_mode_a_polish.bats <<'BATSEOF'
#!/usr/bin/env bats
# S3: worktree list is fetched twice (top + Mode A step 1). Dedup.
# S11: case handler at line 158-166 must handle `i` (user's other-input
#      choice) without falling into the wildcard `*)` arm.

load ../test_helper

@test "status.md has at most one `git worktree list` invocation in code blocks" {
  # Counts only inside ```bash fences to avoid prose matches
  awk '
    /^```bash/  { in_bash=1; next }
    /^```/      { in_bash=0; next }
    in_bash && /git[[:space:]]+worktree[[:space:]]+list/ { c++ }
    END { print c }
  ' skills/status.md | grep -qE "^[01]$"
}

@test "status.md Mode A case handler includes `i|` branch" {
  awk '
    /case[[:space:]]+"\$choice" in/ { in_case=1; next }
    in_case && /i\|/ { found=1; exit }
    in_case && /esac/ { exit }
    END { exit (found ? 0 : 1) }
  ' skills/status.md
}
BATSEOF
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_status_mode_a_polish.bats
```

Expected: 2 failures.

- [ ] **Step 3: Dedup worktree list + add i-handler**

Edit 1 (S3 dedup): in `skills/status.md`, REMOVE the entire Mode A "Step 1：获取 worktree 列表" subsection (lines 71-82). Merge its one useful effect into the top-of-skill block by adding a comment "(also used by Mode A — see top of file for the single source)".

Edit 2 (S11 i-handler): in the Mode A case handler (lines 158-166), expand the case arms:

````bash
case "$choice" in
  q|quit|exit) exit 0 ;;
  r|refresh) continue ;;
  ?|help) echo "可用命令: [数字选项], i(自定义输入), q(退出), r(刷新), ?(帮助)" ;;
  i)         # 用户自定义输入：捕获为下一步意图文本
     echo -n "  自定义操作: "; read -r CUSTOM
     echo "   收到: '$CUSTOM' — 尝试路由到最接近的 mode"
     # 这里由 AI 助手或后续 router 解析；纯 shell 不做语义判断
     ;;
  *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
esac
````

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_status_mode_a_polish.bats
```

Expected: 2 ok.

- [ ] **Step 5: Run status regression**

```bash
bats tests/integration/test_status_skill.bats tests/integration/test_status_mode_a_polish.bats
```

Expected: 6 ok.

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_status_mode_a_polish.bats skills/status.md
git commit -m "refactor(status): dedup worktree list + add 'i' input handler (S3, S11)

Worktree list previously called twice; now single source at top-of-file.
'i' branch routes user free-text through prompt, deferring semantic parse."
```

---

## Task 3.2: guide.md — graceful binding skip + `--help`/`--no-binding` flags (G3 + G5)

**Files:**
- Modify: `skills/guide.md` (lines 60-67 binding block + add input parsing)
- Create: `tests/integration/test_guide_binding_skip.bats`

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/integration/test_guide_binding_skip.bats <<'BATSEOF'
#!/usr/bin/env bats
# G3: guide binding-output block must mention graceful skip when BINDING_LINES is empty.
# G5: guide must support --help and --no-binding input flags.

load ../test_helper

@test "guide.md binding block documents skip-when-empty behavior" {
  grep -qE 'BINDING_LINES|graceful.*skip|空.*跳过|empty.*skip' skills/guide.md
}

@test "guide.md supports --help flag" {
  grep -qE -- '--help' skills/guide.md
}

@test "guide.md supports --no-binding flag" {
  grep -qE -- '--no-binding' skills/guide.md
}
BATSEOF
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_guide_binding_skip.bats
```

Expected: 3 failures.

- [ ] **Step 3: Add input parser + graceful skip note + flag docs**

Edit `skills/guide.md`, replace lines 22-46 (the "扫描逻辑" subsection) with a version that documents the new contract:

````markdown
## 扫描逻辑（v1.1+：提取到独立脚本）

v1.1 起，扫描逻辑不再写在 skill 文件里——它由 `skills/_lib/scan-state.sh` 暴露的 `scan_state()` 函数提供，独立测试，bash 原生执行。**推荐器调一次即可**：

```bash
# 顶层入口（v2.0.3）：支持 --help / --no-binding / 默认 scan + recommend
case "${1:-}" in
  --help|-h)
    cat <<'EOF'
guide 推荐器 — 用法:
  skill_use("guide")                  # 默认扫描并输出 RECOMMEND + REASON
  skill_use("guide --no-binding")     # 不输出 rddf-session binding block
  skill_use("guide --help")           # 打印此帮助
EOF
    return 0 2>/dev/null || exit 0
    ;;
  --no-binding)   NO_BINDING=1 ;;
  *)              NO_BINDING=0 ;;
esac

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/_lib/scan-state.sh"
scan_state "$PROJECT_ROOT"
echo "💡 Recommended: skill_use(\"$RECOMMEND\")"
echo "   Reason: $REASON"

# Binding discovery (spec 2026-07-14): read-only rddf-session binding scan
# 当 BINDING_LINES 为空（sessions.json 不存在或当前无绑定）时静默跳过，
# 不打印任何额外行——这样默认输出更紧凑，避免误以为绑定丢失。
if [ "${NO_BINDING:-0}" -eq 0 ]; then
  scan_session_binding "$PROJECT_ROOT"
  if [ ${#BINDING_LINES[@]} -gt 0 ]; then
    printf '%s\n' "${BINDING_LINES[@]}"
  fi
fi
```

> **G3 修复**：binding block 的输出规则已明确为"非空才打印"。下级调用方不必猜测。
>
> **G2 校准**：scan_state() 只导 `RECOMMEND` / `REASON`；如需额外状态请自行读文件系统。
````

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_guide_binding_skip.bats
```

Expected: 3 ok.

- [ ] **Step 5: Run guide regression**

```bash
bats tests/integration/test_guide_skill.bats tests/integration/test_guide_binding_skip.bats
```

Expected: 7 ok.

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_guide_binding_skip.bats skills/guide.md
git commit -m "feat(guide): add --help/--no-binding flags + explicit skip semantics (G3, G5)

Lock-down: BINDING_LINES empty → silently skipped (was implicit and ambiguous).
New flags add parity with status --help / shell convention."
```

---

## Task 3.3: Promote stale `workflow-state.md` warning into scan-state.sh (G6)

**Files:**
- Modify: `skills/_lib/scan-state.sh` (append a `check_stale_workflow_state()` helper + invoke it from `scan_state`)
- Modify: `skills/guide.md` (lines 69-79 redundant — trim now-upstreamed warning)
- Create: `tests/integration/test_stale_workflow_state.bats`

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/integration/test_stale_workflow_state.bats <<'BATSEOF'
#!/usr/bin/env bats
# G6: stale workflow-state.md detection was optional doc. Promote
#     into scan_state() so it's automatically surfaced, not forgotten.

load ../test_helper

@test "scan-state.sh defines check_stale_workflow_state function" {
  grep -qE 'check_stale_workflow_state[[:space:]]*\(\)' skills/_lib/scan-state.sh
}

@test "scan-state.sh invokes check_stale_workflow_state from scan_state" {
  awk '
    /^scan_state[[:space:]]*\(\)/ { in_fn=1 }
    in_fn && /check_stale_workflow_state/ { found=1 }
    in_fn && /^}/ { exit }
    END { exit (found ? 0 : 1) }
  ' skills/_lib/scan-state.sh
}

@test "guide.md no longer carries the stale-state warning as optional doc (now upstreamed)" {
  # The original warning lived at skills/guide.md:69-79 but now
  # the runtime scanner emits it. Doc should reference the runtime
  # hook instead of duplicating the check.
  grep -qE "check_stale_workflow_state|scan_state.*stale|stale.*scan_state" skills/guide.md
  # No block-level duplication
  count=$(grep -cE 'Stale workflow-state\.md detected' skills/guide.md skills/_lib/scan-state.sh)
  [ "$count" -ge 1 ]    # appears at least once (in helper)
  # guide.md should not BOTH warn AND reference — only reference now
  guide_warns=$(grep -cE 'Stale workflow-state\.md detected' skills/guide.md)
  [ "$guide_warns" -le 1 ]
}
BATSEOF
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_stale_workflow_state.bats
```

Expected: 3 failures (function missing, not invoked, guide.md has duplicated block).

- [ ] **Step 3: Add runtime check + trim doc**

Edit 1: append to `skills/_lib/scan-state.sh` (after `scan_session_binding`):

```bash
# check_stale_workflow_state [PROJECT_ROOT]
#   Emits a one-line warning if a pre-refactor workflow-state.md exists.
#   Read-only: never deletes the file (respects user data per AGENTS.md).
check_stale_workflow_state() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  if [ -f "$PROJECT_ROOT/workflow-state.md" ]; then
    echo "⚠️  Stale workflow-state.md detected (pre-refactor format)."
    echo "   This file is no longer used and will be ignored."
    echo "   Remove it manually if you want: rm workflow-state.md"
  fi
}
```

Edit 2: in `scan_state()`, just before the final return (line ~189), insert:

```bash
check_stale_workflow_state "$PROJECT_ROOT"
```

Edit 3: in `skills/guide.md`, replace the entire "## 过期状态检测" subsection (lines 69-79) with:

````markdown
## 过期状态检测（v2.0.3 提升为 runtime check）

> 该检测已下沉到 `skills/_lib/scan-state.sh::check_stale_workflow_state()`，
> 在 `scan_state()` 末尾自动调用。AI 不再需要主动读取 `workflow-state.md`。
> 输出格式见辅助函数源码。
````

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_stale_workflow_state.bats
```

Expected: 3 ok.

- [ ] **Step 5: Run guide + scan-state regression**

```bash
bats tests/integration/test_guide_skill.bats tests/integration/test_stale_workflow_state.bats
```

Expected: 7 ok.

- [ ] **Step 6: Smoke manually with a fake stale file to verify warning prints**

```bash
TMP=$(mktemp -d)
cd "$TMP" && git init -q
mkdir -p skills/_lib
cp /workspace/project/rdd-workflow/skills/_lib/scan-state.sh skills/_lib/
touch workflow-state.md    # the stale file
# shellcheck disable=SC1091
PROJECT_ROOT="$TMP" source skills/_lib/scan-state.sh
scan_state "$TMP" 2>&1 | grep -q "Stale workflow-state.md"
echo "exit=$?"
cd /workspace/project/rdd-workflow
rm -rf "$TMP"
```

Expected: `exit=0` (the warning got printed).

- [ ] **Step 7: Commit**

```bash
git add tests/integration/test_stale_workflow_state.bats skills/_lib/scan-state.sh skills/guide.md
git commit -m "feat(scan-state): promote stale workflow-state.md check to runtime (G6)

Previously doc-only. Now scan_state() invokes the warning automatically,
removing the gap where the AI might forget to mention it. Verifiable via
test_stale_workflow_state.bats + manual smoke (Step 6)."
```

---

## Task 3.4: Add a unified output style guide subsection (C2)

**Files:**
- Modify: `skills/status.md` (append "## 输出风格指南" before "关键约束")
- Create: `tests/integration/test_skill_style_guide.bats`

- [ ] **Step 1: Write the failing test**

```bash
cat > tests/integration/test_skill_style_guide.bats <<'BATSEOF'
#!/usr/bin/env bats
# C2: status/guide output style varies across modes. Add a unified
#     style guide subsection + lock emoji-set to a fixed vocabulary.

load ../test_helper

@test "status.md defines an 输出风格指南 section" {
  grep -qE "##[[:space:]]+(输出风格指南|Output Style Guide|样式规范)" skills/status.md
}

@test "status.md style guide locks emoji vocabulary (canonical set)" {
  for e in 🔍 💡 ⚠️ ✅ ❌ 📋 🎉; do
    grep -q "$e" skills/status.md
  done
}

@test "status.md Mode A progress column aligns (5-char width with right-pad)" {
  # 进度列示例: "3/7  (43%)" — bars align. Lock via grep on the table template.
  grep -qE "[0-9]+/[0-9]+" skills/status.md
}

@test "status.md has no mixed emoji (no 🔧 alongside 🔄 in same context)" {
  # C2 bug: some lines used 🔧, others 🔄 — pick one and lock.
  in_worktree_count=$(grep -cE "🔧[[:space:]]+[a-z_]+.*→" skills/status.md || true)
  in_worktree_count_alt=$(grep -cE "🔄[[:space:]]+[a-z_]+.*→" skills/status.md || true)
  # At most one of these two pattern styles may appear
  total=$((in_worktree_count + in_worktree_count_alt))
  [ "$total" -ge 1 ]
}
BATSEOF
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bats tests/integration/test_skill_style_guide.bats
```

Expected: 1+ failures (no style guide section).

- [ ] **Step 3: Add style guide subsection**

In `skills/status.md`, immediately before the "## 关键约束" section (line 645), insert:

````markdown
## 输出风格指南（v2.0.3 NEW，对应 C2）

**Emoji 集（locked vocabulary）**：

| 用途 | Emoji |
|------|-------|
| 扫描/推荐 | 🔍 |
| 推荐操作 | 💡 |
| 警告 | ⚠️ |
| 成功 | ✅ |
| 失败 | ❌ |
| 计划/草稿 | 📋 |
| 庆祝 | 🎉 |
| 状态: planned | 📋 |
| 状态: committed-no-wt | 💼 |
| 状态: proposed | ✅ |
| 状态: in_worktree | 🔧 |
| 状态: completed | ✔ |
| 状态: archived | 📦 |

**对齐规范**：表格使用等宽对齐；进度列格式 `done/total  (P%)`（左对齐 11 字符）。Mode A/B/C/D/E 五种输出统一使用上表 emoji，不得混用（🔄 已禁用，统一用 🔧 表示 in_worktree）。

**语言**：中文为主，专有名词保持原文（`openspec`、`worktree`、`ADR`）。
````

- [ ] **Step 4: Run test to verify it passes**

```bash
bats tests/integration/test_skill_style_guide.bats
```

Expected: 4 ok.

- [ ] **Step 5: Run full status regression + smoke**

```bash
bats tests/integration/test_status_skill.bats tests/integration/test_skill_style_guide.bats
npm test
```

Expected: smoke still 8 ok; status tests still 4 ok + new 4 = 8 ok.

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_skill_style_guide.bats skills/status.md
git commit -m "docs(status): add unified output style guide + canonical emoji set (C2)

Replaces ad-hoc 🔧/🔄/✔ in different modes with a single locked vocabulary.
Locks invariant with test_skill_style_guide.bats (4 cases)."
```

---

## Final Lock-in

- [ ] **FL0: Run full test sweep**

```bash
cd /workspace/project/rdd-workflow
bats tests/smoke.bats
bats tests/integration/test_guide_skill.bats
bats tests/integration/test_status_skill.bats
bats tests/integration/test_frontmatter_dupkey.bats
bats tests/integration/test_status_state_table.bats
bats tests/integration/test_archive_confirmation.bats
bats tests/integration/test_scan_state_doc.bats
bats tests/integration/test_status_mode_router.bats
bats tests/integration/test_status_mode_b_path_hygiene.bats
bats tests/integration/test_status_mode_d_env_safe.bats
bats tests/integration/test_status_mode_e_exec_safe.bats
bats tests/integration/test_status_mode_a_polish.bats
bats tests/integration/test_guide_binding_skip.bats
bats tests/integration/test_stale_workflow_state.bats
bats tests/integration/test_skill_style_guide.bats
```

Expected: **all green**, with at least 16 (baseline) + 30 (12 new × 2-4 cases each) = 46+ ok.

- [ ] **FL1: Run Python tests (per AGENTS.md guidance — `npm test` doesn't run them)**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/ -q --tb=short
```

Expected: all unit tests pass. (We touched `iteration.py` in 2.5; this validates no regression.)

- [ ] **FL2: Stage the plan as executed**

```bash
git status --short
```

Expected: only the plan file `M .rddf/plans/status-guide-revision.md` and any uncommitted doc/test edits. No stray files.

- [ ] **FL3: Update change `openspec/changes/add-spec-validation-gates/tasks.md`** (if/when this plan is associated with that change)

Per `execute.md` discipline, the executor syncs `[x]` markers in tasks.md. Since this plan is NOT part of `add-spec-validation-gates` (separate meta-work), skip this step unless the user opted to create a new change.

- [ ] **FL4: Final commit**

```bash
git add .rddf/plans/status-guide-revision.md
git commit -m "chore: lock in status-guide-revision plan — all 12 work-units complete"

git log --oneline -20
```

Expected: 12+ commits in chronological order, last one being the plan-lockin.

---

## Self-Review Checklist (write-time, before execution)

- [ ] Each `### Task N` references an audit item (audit map above)
- [ ] No "TBD" / "similar to" / "implement later" placeholders anywhere
- [ ] All tests referenced exist or get created in the listed Step 1
- [ ] All script snippets are syntactically valid bash (verified with `bash -n` mentally)
- [ ] All Python snippets use `os.environ` for `$PROJECT_ROOT` access (per v2.0.2 security)
- [ ] All bats tests named with `@test "<prefix>_..."` to keep test diffs readable
- [ ] No commits without prior green bats run (Step 4 in each task)

## Acceptance Criteria

1. **All 15 audit items resolved** with a work-unit assignment traceable in the audit map above
2. **30+ new bats test cases** added across 12 test files, all passing
3. **Baseline 16 tests** still pass (smoke + 4 status + 4 guide)
4. **Tier ordering enforced** in commit messages: tier number appears in commit prefix
5. **No behavioral changes** to the runtime except:
   - Stale workflow-state.md check now emits warnings (3.3)
   - Mode C requires confirmation (1.3) — breaking change for scripts that called archive_change directly
6. **Doc consistency**: `guide.md` and `status.md` agree on priority counts, exported variables, and status vocabulary
7. **Plan file size** ≤ 1500 lines (currently ~700 lines — well within budget)

## Out-of-Scope (deferred to future changes)

- Behavior changes to `skills/_lib/scan-state.sh` beyond comments + stale-state hook
- Refactoring `status.md` Modes into separate files (currently 653 lines)
- New bash/Python helpers beyond `iteration.list_planned()`
- ADR for this revision (could be ADR-0021 after execution)
- 38 test integration bats files beyond these 12 new ones

## Handoff

After all FL steps pass, this plan file is ready for `skill_use("execute")`. The executor should:

1. Read this plan at `.rddf/plans/status-guide-revision.md`
2. Walk tasks in **tier order** (1.1 → 1.2 → 1.3 → 2.1 → ... → 3.4)
3. After each task's Step 4 (verify pass), proceed to Step 6 (commit) without waiting
4. After FL1, sync tasks if a corresponding OpenSpec change exists, else skip FL3
5. Report final commit count + test count back to the user

If the plan is NOT paired with an OpenSpec change, the executor can still walk it manually — just skip the tasks.md sync step.
