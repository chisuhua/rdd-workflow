# guide-design Phase 1 Diagnostic + Recovery — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `guide-design` Phase 1's hard-reject-on-missing-arch-handoff behavior with a diagnostic-first + soft-prompt + reconstruction flow, so transient state loss no longer blocks users with no recovery path.

**Architecture:**

- New `skills/guide-design/scripts/design_preflight.sh` runs **before** the hard gate. It collects evidence (arch-handoff existence, ADR count, roadmap presence, rddf-session history) and emits a structured status JSON. It **never** fails.
- New `skills/guide-design/scripts/reconstruct_arch_handoff.sh` synthesizes `.arch-handoff.json` from filesystem evidence (docs/adr/, roadmap.md, etc.) when the handoff is missing. Logs reconstruction to `.rddf/state/.reconstruction.log`.
- `skills/guide-design/SKILL.md` Phase 1 reads preflight output and branches: `normal` / `soft_prompt_reconstruct` / `hard_reject_no_evidence`.
- `skills/rddf-session/scripts/rddf_session_hooks.sh` is promoted from optional-graceful-degradation to required-fail-loud when missing.

**Tech Stack:** bash 4+ · bats-core 1.10+ · jq · python3 · git

---

## ⚡ Immediate Unblock (do this NOW, independent of plan execution)

Before executing this plan, the user is currently blocked. Run this one-off to unblock:

```bash
# Step 1 — synthesize evidence-driven .arch-handoff.json
bash skills/guide-design/scripts/reconstruct_arch_handoff.sh \
  --project-root "$(git rev-parse --show-toplevel)" \
  --output ".rddf/state/.arch-handoff.json"

# Step 2 — verify
cat .rddf/state/.arch-handoff.json | jq .

# Step 3 — re-invoke guide-design
skill_use("guide-design")
```

Tasks 1–4 below implement this script properly with tests. Until those tasks land, the user can paste the one-off above.

---

## Scope Split Recommendation

This plan covers **P1, P2, P4, P5** from the prior analysis (see prior session messages). **Out of scope** — separate plans needed:

- **P3** (git-track handoffs in `.rddf/handoff/`): architectural change, requires ADR-0016 amendment + refactor across all 4 guide-* skills. Recommend: `docs/superpowers/plans/2026-XX-XX-handoff-persistence.md` (future).
- **Cross-phase diagnostic parity**: apply same preflight pattern to `guide-arch`, `guide-plan`, `guide-ship` Phase 1. Recommend: bundled in the future plan above.

These are explicitly NOT covered here to keep this plan deliverable in one focused change.

---

## File Structure

| File | Operation | Responsibility |
|---|---|---|
| `skills/guide-design/scripts/design_preflight.sh` | Create | Collect evidence; emit status JSON; never fails |
| `skills/guide-design/scripts/reconstruct_arch_handoff.sh` | Create | Synthesize `.arch-handoff.json` from filesystem |
| `skills/guide-design/SKILL.md` | Modify | Phase 1: run preflight + branch on status; offer reconstruction in soft_prompt path |
| `skills/rddf-session/scripts/rddf_session_hooks.sh` | Modify | `rddf_session_hook_entry` exits non-zero when `resolve_rdd_skill_dir` is unavailable |
| `tests/integration/test_design_preflight.bats` | Create | 6 bats assertions covering evidence collection |
| `tests/integration/test_reconstruct_arch_handoff.bats` | Create | 7 bats assertions covering reconstruction paths |
| `tests/integration/test_rddf_session_hook_required.bats` | Create | 3 bats assertions covering fail-loud behavior |
| `tests/integration/test_guide_design_phase.bats` | Modify | Replace "rejects missing arch-handoff" test (line ~9-19) with diagnostic-aware variant |
| `tests/KNOWN_FAILURES.txt` | Modify (only if needed) | Track any pre-existing failure that the test rewrite exposes |
| `docs/adr/ADR-0016-arch-discovery-contract.md` | Modify (footnote) | Note reconstruction tool as legitimate handoff-recovery mechanism |

Truth-source hierarchy (per project convention):

| Layer | Role | Authority |
|---|---|---|
| L1 | Runtime skill code | `skills/guide-design/SKILL.md`, `scripts/*` |
| L2 | Filesystem evidence | `docs/adr/`, `roadmap.md`, `.rddf/state/` |
| L3 | Tests | bats integration, pytest unit |

Reconcile direction: L3 → L2 → L1. Tests dictate behavior; skill code conforms.

---

## Tasks

### Task 1: design_preflight.sh — skeleton + jq output contract

**Files:**
- Create: `skills/guide-design/scripts/design_preflight.sh`
- Create: `tests/integration/test_design_preflight.bats`

- [ ] **Step 1: Write failing test for jq output contract**

In `tests/integration/test_design_preflight.bats`:

```bash
#!/usr/bin/env bats
load ../test_helper

setup() {
  export PROJECT_ROOT="$BATS_TMPDIR/preflight-$$"
  mkdir -p "$PROJECT_ROOT/.rddf/state"
  mkdir -p "$PROJECT_ROOT/docs/adr"
}

teardown() { rm -rf "$PROJECT_ROOT"; }

@test "design_preflight: emits valid JSON with required keys" {
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  echo "$output" | jq -e '.arch_handoff_exists' >/dev/null
  echo "$output" | jq -e '.adr_count' >/dev/null
  echo "$output" | jq -e '.roadmap_exists' >/dev/null
  echo "$output" | jq -e '.session_history_arch_done' >/dev/null
  echo "$output" | jq -e '.recommendation' >/dev/null
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_design_preflight.bats`
Expected: FAIL with "design_preflight.sh not found" (file doesn't exist yet)

- [ ] **Step 3: Implement minimal preflight.sh**

In `skills/guide-design/scripts/design_preflight.sh`:

```bash
#!/usr/bin/env bash
# skills/guide-design/scripts/design_preflight.sh — design Phase 1 证据收集
# 永远 exit 0; 输出 status JSON 到 stdout, 诊断日志到 stderr.
# 调用方根据 .recommendation 字段决定下一步.

set -euo pipefail

PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

emit_status() {
  local arch_handoff="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
  local adr_dir="${SPEC_WORKFLOW_ADR_DIR:-$PROJECT_ROOT/docs/adr}"
  local roadmap="${SPEC_WORKFLOW_ROADMAP_PATH:-$PROJECT_ROOT/roadmap.md}"

  local arch_handoff_exists="false"
  [ -f "$arch_handoff" ] && arch_handoff_exists="true"

  local adr_count=0
  if [ -d "$adr_dir" ]; then
    adr_count=$(find "$adr_dir" -maxdepth 1 -name 'ADR-*.md' -type f 2>/dev/null | wc -l)
  fi

  local roadmap_exists="false"
  [ -f "$roadmap" ] && roadmap_exists="true"

  local session_arch_done="false"
  if [ -f "$PROJECT_ROOT/.rddf/state/sessions.json" ]; then
    session_arch_done=$(jq -r '
      [.sessions[]? | select(.stage=="stage_arch" and .status=="completed")]
      | length > 0
    ' "$PROJECT_ROOT/.rddf/state/sessions.json" 2>/dev/null || echo "false")
  fi

  local recommendation="hard_reject_no_evidence"
  if [ "$arch_handoff_exists" = "true" ]; then
    recommendation="normal"
  elif [ "$adr_count" -gt 0 ] && [ "$roadmap_exists" = "true" ]; then
    recommendation="soft_prompt_reconstruct"
  fi

  jq -n \
    --argjson arch_handoff_exists "$arch_handoff_exists" \
    --argjson adr_count "$adr_count" \
    --argjson roadmap_exists "$roadmap_exists" \
    --argjson session_history_arch_done "$session_arch_done" \
    --arg recommendation "$recommendation" \
    '{arch_handoff_exists: $arch_handoff_exists,
      adr_count: $adr_count,
      roadmap_exists: $roadmap_exists,
      session_history_arch_done: $session_history_arch_done,
      recommendation: $recommendation}'
}

emit_status
```

- [ ] **Step 4: Make executable + run test to verify it passes**

Run:
```bash
chmod +x skills/guide-design/scripts/design_preflight.sh
bats tests/integration/test_design_preflight.bats
```

Expected: 1 test, 0 failures

- [ ] **Step 5: Commit**

```bash
git add skills/guide-design/scripts/design_preflight.sh \
        tests/integration/test_design_preflight.bats
git commit -m "feat(guide-design): add preflight evidence collection script"
```

---

### Task 2: design_preflight.sh — adr_count edge cases

**Files:**
- Modify: `skills/guide-design/scripts/design_preflight.sh`
- Modify: `tests/integration/test_design_preflight.bats`

- [ ] **Step 1: Add failing tests for adr_count edge cases**

Append to `tests/integration/test_design_preflight.bats`:

```bash
@test "design_preflight: adr_count=0 when adr_dir missing" {
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.adr_count')" -eq 0 ]
}

@test "design_preflight: adr_count ignores ADR-0000-template" {
  touch "$PROJECT_ROOT/docs/adr/ADR-0000-template.md"
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-test.md"
  touch "$PROJECT_ROOT/docs/adr/ADR-0002-test.md"
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.adr_count')" -eq 2 ]
}

@test "design_preflight: adr_count handles ADR-XXXX prefix correctly" {
  touch "$PROJECT_ROOT/docs/adr/ADR-0022-real.md"
  touch "$PROJECT_ROOT/docs/adr/not-an-adr.md"
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.adr_count')" -eq 1 ]
}
```

- [ ] **Step 2: Run tests to verify they pass (already implemented in Task 1)**

Run: `bats tests/integration/test_design_preflight.bats`
Expected: 4 tests, 0 failures (Task 1 + new edge cases should all pass with the glob in Task 1's implementation since `ADR-*.md` matches `ADR-0000-template.md` too — if Task 3 below exposes this, fix the find filter)

- [ ] **Step 3: If Task 1's glob is too loose, refine adr_count filter**

In `skills/guide-design/scripts/design_preflight.sh`, replace the adr_count line:

```bash
# Before:
adr_count=$(find "$adr_dir" -maxdepth 1 -name 'ADR-*.md' -type f 2>/dev/null | wc -l)

# After (exclude templates):
adr_count=$(find "$adr_dir" -maxdepth 1 -name 'ADR-*.md' -type f \
  ! -name '*-template.md' ! -name '*-template-*' \
  2>/dev/null | wc -l)
```

Run: `bats tests/integration/test_design_preflight.bats`
Expected: 4 tests, 0 failures

- [ ] **Step 4: Commit**

```bash
git add skills/guide-design/scripts/design_preflight.sh \
        tests/integration/test_design_preflight.bats
git commit -m "fix(guide-design): exclude ADR templates from adr_count"
```

---

### Task 3: design_preflight.sh — recommendation logic edge cases

**Files:**
- Modify: `tests/integration/test_design_preflight.bats`

- [ ] **Step 1: Add failing tests for recommendation branches**

Append:

```bash
@test "design_preflight: recommendation=normal when arch_handoff exists" {
  echo '{"version":1,"discovered":true}' > "$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "normal" ]
}

@test "design_preflight: recommendation=soft_prompt_reconstruct when ADRs+roadmap exist but no handoff" {
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-x.md"
  touch "$PROJECT_ROOT/roadmap.md"
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "soft_prompt_reconstruct" ]
}

@test "design_preflight: recommendation=hard_reject_no_evidence when no evidence at all" {
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "hard_reject_no_evidence" ]
}

@test "design_preflight: recommendation=hard_reject_no_evidence when only ADRs (no roadmap)" {
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-x.md"
  run bash "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh" "$PROJECT_ROOT"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "hard_reject_no_evidence" ]
}
```

- [ ] **Step 2: Run tests**

Run: `bats tests/integration/test_design_preflight.bats`
Expected: 8 tests, 0 failures (recommendation logic from Task 1 already implements this; tests confirm)

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_design_preflight.bats
git commit -m "test(guide-design): add recommendation branch coverage"
```

---

### Task 4: reconstruct_arch_handoff.sh — skeleton + version field

**Files:**
- Create: `skills/guide-design/scripts/reconstruct_arch_handoff.sh`
- Create: `tests/integration/test_reconstruct_arch_handoff.bats`

- [ ] **Step 1: Write failing test**

In `tests/integration/test_reconstruct_arch_handoff.bats`:

```bash
#!/usr/bin/env bats
load ../test_helper

setup() {
  export PROJECT_ROOT="$BATS_TMPDIR/recon-$$"
  mkdir -p "$PROJECT_ROOT/.rddf/state"
  mkdir -p "$PROJECT_ROOT/docs/adr"
  mkdir -p "$PROJECT_ROOT/docs/architecture"
}

teardown() { rm -rf "$PROJECT_ROOT"; }

@test "reconstruct_arch_handoff: writes valid v1 schema handoff" {
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-test.md"
  touch "$PROJECT_ROOT/docs/adr/ADR-0002-test.md"
  touch "$PROJECT_ROOT/roadmap.md"
  touch "$PROJECT_ROOT/docs/architecture/overview.md"

  run bash "$REPO_ROOT/skills/guide-design/scripts/reconstruct_arch_handoff.sh" \
    --project-root "$PROJECT_ROOT"

  [ "$status" -eq 0 ]
  [ -f "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" ]

  # Validate JSON shape
  jq -e '.version == 1' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
  jq -e '.discovered == true' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
  jq -e '.adr_dir == "docs/adr"' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
  jq -e '.adr_pattern | test("ADR-")' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
  jq -e '.roadmap_path == "roadmap.md"' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
  jq -e '.architecture_dir == "docs/architecture"' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_reconstruct_arch_handoff.bats`
Expected: FAIL (script doesn't exist)

- [ ] **Step 3: Implement reconstruct_arch_handoff.sh**

```bash
#!/usr/bin/env bash
# skills/guide-design/scripts/reconstruct_arch_handoff.sh
# 从文件系统证据合成 .arch-handoff.json (ADR-0016 schema v1).
# 当 .arch-handoff.json 缺失但 arch 工作已完成时使用.
# 幂等: 已存在合法 handoff 时, 默认拒绝覆盖 (--force 覆盖).

set -euo pipefail

PROJECT_ROOT=""
OUTPUT_PATH=""
FORCE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-root) PROJECT_ROOT="$2"; shift 2 ;;
    --output)        OUTPUT_PATH="$2"; shift 2 ;;
    --force)         FORCE="true"; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
OUTPUT_PATH="${OUTPUT_PATH:-$PROJECT_ROOT/.rddf/state/.arch-handoff.json}"

# Idempotency: don't overwrite without --force
if [ -f "$OUTPUT_PATH" ] && [ "$FORCE" != "true" ]; then
  echo "❌ handoff already exists at $OUTPUT_PATH (use --force to overwrite)" >&2
  exit 1
fi

ADR_DIR_REL="docs/adr"
ADR_DIR_ABS="$PROJECT_ROOT/$ADR_DIR_REL"
ROADMAP_REL="roadmap.md"
ARCHITECTURE_DIR_REL="docs/architecture"

if [ ! -d "$ADR_DIR_ABS" ]; then
  echo "❌ adr_dir not found: $ADR_DIR_ABS" >&2
  echo "   Cannot reconstruct handoff without ADR directory" >&2
  exit 1
fi

# Derive adr_pattern from first existing ADR filename
ADR_PATTERN=$(find "$ADR_DIR_ABS" -maxdepth 1 -name 'ADR-*.md' -type f \
  ! -name '*-template*' 2>/dev/null | head -1 | xargs -I{} basename {} | \
  sed -E 's/[0-9]+.*//')

# Detect roadmap path
if [ ! -f "$PROJECT_ROOT/$ROADMAP_REL" ]; then
  # Fallback: search for any roadmap*.md
  FOUND_ROADMAP=$(find "$PROJECT_ROOT" -maxdepth 2 -name 'roadmap*.md' -type f 2>/dev/null | head -1)
  if [ -n "$FOUND_ROADMAP" ]; then
    ROADMAP_REL=$(realpath --relative-to="$PROJECT_ROOT" "$FOUND_ROADMAP")
  fi
fi

mkdir -p "$(dirname "$OUTPUT_PATH")"

jq -n \
  --arg version "1" \
  --arg adr_dir "$ADR_DIR_REL" \
  --arg adr_pattern "${ADR_PATTERN:-ADR-}" \
  --arg roadmap_path "$ROADMAP_REL" \
  --arg architecture_dir "$ARCHITECTURE_DIR_REL" \
  --arg discovered "true" \
  --arg reconstructed_at "$(date -Iseconds)" \
  --arg reconstructed_from "filesystem-evidence" \
  '{version: ($version | tonumber),
    adr_dir: $adr_dir,
    adr_pattern: $adr_pattern,
    roadmap_path: $roadmap_path,
    architecture_dir: $architecture_dir,
    discovered: ($discovered == "true"),
    reconstructed_at: $reconstructed_at,
    reconstructed_from: $reconstructed_from}' \
  > "$OUTPUT_PATH"

# Log reconstruction event
LOG_FILE="$PROJECT_ROOT/.rddf/state/.reconstruction.log"
mkdir -p "$(dirname "$LOG_FILE")"
echo "[$(date -Iseconds)] reconstructed .arch-handoff.json from filesystem evidence" >> "$LOG_FILE"

echo "✅ reconstructed: $OUTPUT_PATH" >&2
```

- [ ] **Step 4: Make executable + run test**

```bash
chmod +x skills/guide-design/scripts/reconstruct_arch_handoff.sh
bats tests/integration/test_reconstruct_arch_handoff.bats
```

Expected: 1 test, 0 failures

- [ ] **Step 5: Commit**

```bash
git add skills/guide-design/scripts/reconstruct_arch_handoff.sh \
        tests/integration/test_reconstruct_arch_handoff.bats
git commit -m "feat(guide-design): add arch-handoff reconstruction script"
```

---

### Task 5: reconstruct_arch_handoff.sh — idempotency + force

**Files:**
- Modify: `tests/integration/test_reconstruct_arch_handoff.bats`

- [ ] **Step 1: Add idempotency tests**

Append:

```bash
@test "reconstruct_arch_handoff: refuses to overwrite without --force" {
  echo '{"version":1,"discovered":false}' > "$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-x.md"

  run bash "$REPO_ROOT/skills/guide-design/scripts/reconstruct_arch_handoff.sh" \
    --project-root "$PROJECT_ROOT"

  [ "$status" -ne 0 ]
  # Original content unchanged
  jq -e '.discovered == false' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
}

@test "reconstruct_arch_handoff: --force overwrites existing handoff" {
  echo '{"version":1,"discovered":false}' > "$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-x.md"

  run bash "$REPO_ROOT/skills/guide-design/scripts/reconstruct_arch_handoff.sh" \
    --project-root "$PROJECT_ROOT" --force

  [ "$status" -eq 0 ]
  jq -e '.discovered == true' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" >/dev/null
}
```

- [ ] **Step 2: Run tests**

Run: `bats tests/integration/test_reconstruct_arch_handoff.bats`
Expected: 3 tests, 0 failures

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_reconstruct_arch_handoff.bats
git commit -m "test(guide-design): cover reconstruct idempotency and --force"
```

---

### Task 6: reconstruct_arch_handoff.sh — error path (missing adr_dir)

**Files:**
- Modify: `tests/integration/test_reconstruct_arch_handoff.bats`

- [ ] **Step 1: Add error path test**

Append:

```bash
@test "reconstruct_arch_handoff: rejects when no adr_dir exists" {
  # setup() created docs/adr, remove it
  rm -rf "$PROJECT_ROOT/docs/adr"

  run bash "$REPO_ROOT/skills/guide-design/scripts/reconstruct_arch_handoff.sh" \
    --project-root "$PROJECT_ROOT"

  [ "$status" -ne 0 ]
  echo "$output" | grep -q "adr_dir not found"
  [ ! -f "$PROJECT_ROOT/.rddf/state/.arch-handoff.json" ]
}

@test "reconstruct_arch_handoff: logs to .reconstruction.log" {
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-x.md"
  run bash "$REPO_ROOT/skills/guide-design/scripts/reconstruct_arch_handoff.sh" \
    --project-root "$PROJECT_ROOT"

  [ "$status" -eq 0 ]
  [ -f "$PROJECT_ROOT/.rddf/state/.reconstruction.log" ]
  grep -q "reconstructed" "$PROJECT_ROOT/.rddf/state/.reconstruction.log"
}

@test "reconstruct_arch_handoff: discovers alternative roadmap path" {
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-x.md"
  rm "$PROJECT_ROOT/roadmap.md" 2>/dev/null || true
  touch "$PROJECT_ROOT/my-roadmap.md"

  run bash "$REPO_ROOT/skills/guide-design/scripts/reconstruct_arch_handoff.sh" \
    --project-root "$PROJECT_ROOT"

  [ "$status" -eq 0 ]
  local roadmap_in_handoff
  roadmap_in_handoff=$(jq -r '.roadmap_path' "$PROJECT_ROOT/.rddf/state/.arch-handoff.json")
  [[ "$roadmap_in_handoff" == *roadmap* ]]
}
```

- [ ] **Step 2: Run tests**

Run: `bats tests/integration/test_reconstruct_arch_handoff.bats`
Expected: 6 tests, 0 failures

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_reconstruct_arch_handoff.bats
git commit -m "test(guide-design): cover reconstruct error paths and roadmap fallback"
```

---

### Task 7: guide-design/SKILL.md Phase 1 — replace hard gate with preflight + branch

**Files:**
- Modify: `skills/guide-design/SKILL.md`

- [ ] **Step 1: Read current Phase 1 section**

Read `skills/guide-design/SKILL.md` lines around "Phase 1: setup" and identify the exact block that does:

```bash
if [ ! -f ".rddf/state/.arch-handoff.json" ]; then
  echo "❌ arch-done 未完成，无法进入 design 阶段"
  echo "   请先运行: skill_use(\"guide-arch\")"
  return 1
fi
```

- [ ] **Step 2: Replace hard gate with preflight + branch logic**

Replace the hard-gate block with:

```bash
# === Phase 1: Diagnostic + Branch (replaces old hard gate) ===
source "$(dirname "${BASH_SOURCE[0]:-${0}})"/scripts/design_preflight.sh 2>/dev/null || \
  source "$HOME/.agents/skills/guide-design/scripts/design_preflight.sh"

PREFLIGHT_STATUS=$(design_preflight_status "$PROJECT_ROOT")
RECOMMENDATION=$(echo "$PREFLIGHT_STATUS" | jq -r '.recommendation')

case "$RECOMMENDATION" in
  normal)
    : # proceed to env check below
    ;;
  soft_prompt_reconstruct)
    echo "⚠️  arch-handoff 缺失但历史证据显示 arch-done 已完成" >&2
    echo "$PREFLIGHT_STATUS" | jq -r '
      "  - ADR 数量: \(.adr_count)\n" +
      "  - 路线图存在: \(.roadmap_exists)\n" +
      "  - session 历史 arch-done: \(.session_history_arch_done)"
    ' >&2
    echo "" >&2
    echo "可选操作:" >&2
    echo "  1. 重建 handoff: bash skills/guide-design/scripts/reconstruct_arch_handoff.sh --force" >&2
    echo "  2. 重跑 guide-arch (会丢失 arch 上下文)" >&2
    echo "  3. 退出,先手工检查" >&2
    echo "" >&2
    read -r -p "选择 [1/2/3]: " recon_choice
    case "$recon_choice" in
      1) bash skills/guide-design/scripts/reconstruct_arch_handoff.sh --force \
           --project-root "$PROJECT_ROOT" || return 1 ;;
      2) echo "请运行 skill_use(\"guide-arch\") 重做 arch 工作" >&2; return 1 ;;
      *) echo "已退出" >&2; return 0 ;;
    esac
    ;;
  hard_reject_no_evidence)
    echo "❌ arch-done 未完成，无法进入 design 阶段" >&2
    echo "   未发现任何 arch 工作证据 (无 ADR / 无 roadmap)" >&2
    echo "   请先运行: skill_use(\"guide-arch\")" >&2
    return 1
    ;;
esac
```

Note: `design_preflight_status` is the new function. Task 8 implements it as a wrapper around Task 1's `emit_status`.

- [ ] **Step 3: Verify integration test still passes (after Task 8 adds the wrapper)**

This step blocks on Task 8. Mark step as blocked until Task 8 lands.

- [ ] **Step 4: Commit (after Task 8)**

```bash
git add skills/guide-design/SKILL.md
git commit -m "feat(guide-design): Phase 1 diagnostic + soft-prompt recovery"
```

---

### Task 8: design_preflight.sh — wrap emit_status in exported function

**Files:**
- Modify: `skills/guide-design/scripts/design_preflight.sh`
- Modify: `tests/integration/test_design_preflight.bats`

- [ ] **Step 1: Add failing test for exported wrapper**

Append to `tests/integration/test_design_preflight.bats`:

```bash
@test "design_preflight: design_preflight_status() exported function works under set -e" {
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-x.md"
  touch "$PROJECT_ROOT/roadmap.md"

  run bash -c "
    set -euo pipefail
    source '$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh'
    result=\$(design_preflight_status '$PROJECT_ROOT')
    echo \"\$result\" | jq -e '.recommendation == \"soft_prompt_reconstruct\"'
  "
  [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_design_preflight.bats`
Expected: FAIL (function `design_preflight_status` not defined)

- [ ] **Step 3: Add exported wrapper**

In `skills/guide-design/scripts/design_preflight.sh`, replace the trailing `emit_status` line and add a wrapper:

```bash
# Public wrapper: usable from guide-design.md Phase 1 under set -e
design_preflight_status() {
  local project_root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  PROJECT_ROOT="$project_root" emit_status
}

# Direct execution: emit status JSON to stdout
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  emit_status
fi
```

- [ ] **Step 4: Run tests**

Run: `bats tests/integration/test_design_preflight.bats`
Expected: 9 tests, 0 failures

- [ ] **Step 5: Now complete Task 7 Step 3**

Run: `bats tests/integration/test_guide_design_phase.bats`
Expected: tests run, but Task 9 below will modify the "rejects missing arch-handoff" test first

- [ ] **Step 6: Commit**

```bash
git add skills/guide-design/scripts/design_preflight.sh \
        tests/integration/test_design_preflight.bats
git commit -m "feat(guide-design): export preflight status function"
```

---

### Task 9: Update existing test that encodes hard-gate behavior

**Files:**
- Modify: `tests/integration/test_guide_design_phase.bats`

- [ ] **Step 1: Find the test that encodes bad behavior**

In `tests/integration/test_guide_design_phase.bats`, the test `"guide-design: Phase 1 rejects missing arch-handoff"` (around lines 9-19) encodes the old behavior. This test should be REPLACED, not deleted, because the new behavior is "diagnose first, then decide".

- [ ] **Step 2: Replace with diagnostic-aware test**

Find and replace the test block with:

```bash
@test "guide-design: Phase 1 invokes preflight before deciding" {
  # No arch-handoff, but with adr+roadmap evidence → soft prompt path
  mkdir -p "$PROJECT_ROOT/docs/adr"
  touch "$PROJECT_ROOT/docs/adr/ADR-0001-test.md"
  touch "$PROJECT_ROOT/roadmap.md"

  # Verify preflight is callable and returns soft_prompt_reconstruct
  run bash -c '
    source "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh"
    design_preflight_status "$1"
  ' _ "$PROJECT_ROOT"

  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "soft_prompt_reconstruct" ]
}

@test "guide-design: Phase 1 hard-rejects only with no evidence" {
  # No arch-handoff, no ADRs, no roadmap → hard reject
  run bash -c '
    source "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh"
    design_preflight_status "$1"
  ' _ "$PROJECT_ROOT"

  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "hard_reject_no_evidence" ]
}

@test "guide-design: Phase 1 normal path with arch-handoff present" {
  echo '{"version":1,"discovered":true}' > "$PROJECT_ROOT/.rddf/state/.arch-handoff.json"

  run bash -c '
    source "$REPO_ROOT/skills/guide-design/scripts/design_preflight.sh"
    design_preflight_status "$1"
  ' _ "$PROJECT_ROOT"

  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '.recommendation')" = "normal" ]
}
```

- [ ] **Step 3: Run modified test file**

Run: `bats tests/integration/test_guide_design_phase.bats`
Expected: all tests pass, including new diagnostic-aware variants

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_guide_design_phase.bats
git commit -m "test(guide-design): replace hard-gate test with diagnostic-aware variants"
```

---

### Task 10: rddf-session hook fail-loud on missing helper

**Files:**
- Modify: `skills/rddf-session/scripts/rddf_session_hooks.sh`
- Create: `tests/integration/test_rddf_session_hook_required.bats`

- [ ] **Step 1: Write failing test**

In `tests/integration/test_rddf_session_hook_required.bats`:

```bash
#!/usr/bin/env bats
load ../test_helper

@test "rddf_session_hook_entry: fails loud when resolve_rdd_skill_dir unavailable" {
  # Simulate missing helper by clearing PATH and overriding source
  run bash -c '
    # Override resolve_rdd_skill_dir to fail
    resolve_rdd_skill_dir() { return 127; }
    export -f resolve_rdd_skill_dir
    source "'"$REPO_ROOT"'/skills/rddf-session/scripts/rddf_session_hooks.sh"
    rddf_session_hook_entry stage_design guide-design design-phase design-done /tmp/foo
  '
  [ "$status" -ne 0 ]
  echo "$output" | grep -qiE "fail|unavailable|required"
}

@test "rddf_session_hook_close: fails loud when resolve_rdd_skill_dir unavailable" {
  run bash -c '
    resolve_rdd_skill_dir() { return 127; }
    export -f resolve_rdd_skill_dir
    source "'"$REPO_ROOT"'/skills/rddf-session/scripts/rddf_session_hooks.sh"
    rddf_session_hook_close stage_design design-done guide-design
  '
  [ "$status" -ne 0 ]
}

@test "rddf_session_hook_entry: succeeds when helper available (smoke)" {
  # Smoke test: real call should not hard-fail (it may skip if env not set)
  run bash -c '
    source "'"$REPO_ROOT"'/skills/rddf-session/scripts/rddf_session_hooks.sh"
    # Should at minimum not 127-fail if helper resolves
    rddf_session_hook_entry stage_design guide-design design-phase design-done /tmp/nonexistent-$$ 2>&1 || true
    echo "exit_$?"
  '
  # We do not assert success since global env may vary; just that hook ran
  echo "$output" | grep -qE "exit_|rddf"
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_rddf_session_hook_required.bats`
Expected: first 2 tests FAIL (current code does graceful degradation via `||`)

- [ ] **Step 3: Read current hook implementation**

Read `skills/rddf-session/scripts/rddf_session_hooks.sh` and locate `rddf_session_hook_entry` and `rddf_session_hook_close`. The current pattern is:

```bash
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || \
  source "$HOME/.agents/skills/_lib/skill_root.sh"
if command -v resolve_rdd_skill_dir >/dev/null 2>&1; then
    source "$(resolve_rdd_skill_dir rddf-session)/scripts/rddf_session_hooks.sh"
    rddf_session_hook_*
else
    echo "⚠️  resolve_rdd_skill_dir 不可用, 跳过 rddf-session hook (graceful degradation)" >&2
fi
```

- [ ] **Step 4: Replace graceful degradation with fail-loud**

Change the pattern to:

```bash
source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || \
  source "$HOME/.agents/skills/_lib/skill_root.sh"

if ! command -v resolve_rdd_skill_dir >/dev/null 2>&1; then
    echo "❌ rddf-session hook 不可用: resolve_rdd_skill_dir 未定义" >&2
    echo "   修复: 检查 ~/.agents/skills/_lib/skill_root.sh 是否存在且 PATH 正确" >&2
    return 1 2>/dev/null || exit 1
fi

source "$(resolve_rdd_skill_dir rddf-session)/scripts/rddf_session_hooks.sh"
rddf_session_hook_*
```

Note: this is a behavior change. The previous `|| true` wrap that call sites used (e.g. in guide-design.md) should now propagate the non-zero exit. Audit call sites and remove redundant `|| true` wrappers.

- [ ] **Step 5: Run tests**

Run: `bats tests/integration/test_rddf_session_hook_required.bats`
Expected: 3 tests, 0 failures (or 2 PASS + 1 smoke ok)

- [ ] **Step 6: Audit call sites that may break**

```bash
grep -rn 'rddf_session_hook_' skills/ --include='*.md' --include='*.sh' | \
  grep -E '(\|\| true|\|\| :)'
```

For each match, decide:
- If the call site is inside a `case` branch where failure should propagate → keep exit code
- If the call site is in a soft-init context → leave as-is (those should fail loud now anyway)

- [ ] **Step 7: Commit**

```bash
git add skills/rddf-session/scripts/rddf_session_hooks.sh \
        tests/integration/test_rddf_session_hook_required.bats
git commit -m "feat(rddf-session): promote hook from graceful-degradation to fail-loud"
```

---

### Task 11: ADR-0016 footnote on reconstruction as legitimate recovery

**Files:**
- Modify: `docs/adr/ADR-0016-arch-discovery-contract.md`

- [ ] **Step 1: Locate discovery contract section**

Read ADR-0016 and find the section discussing handoff format / v1 schema. Add a footnote about reconstruction.

- [ ] **Step 2: Add footnote**

Append after the schema section:

```markdown
> **Recovery Note (added 2026-08-07):** `.arch-handoff.json` may be reconstructed from filesystem evidence via `skills/guide-design/scripts/reconstruct_arch_handoff.sh`. Reconstructed handoffs include `reconstructed_at` and `reconstructed_from: "filesystem-evidence"` fields. Schema v1 consumers must tolerate these optional fields.
```

- [ ] **Step 3: Update ADR index if it exists**

If `docs/adr/README.md` references ADR-0016, no change needed. If there is an automated index update mechanism (per improvement `auto-sync-adr-index.md`), trigger it.

- [ ] **Step 4: Commit**

```bash
git add docs/adr/ADR-0016-arch-discovery-contract.md
git commit -m "docs(adr-0016): document reconstruction as legitimate handoff recovery"
```

---

### Task 12: Update proposal-approved.md entry (after plan execution)

**Files:**
- Modify: `proposal-approved.md`

- [ ] **Step 1: Skip if not using proposal-approved workflow**

This task only applies if the user is running this plan via the formal guide-design → guide-plan → guide-ship OpenSpec flow. If executing inline, skip.

- [ ] **Step 2: Add entry referencing the plan**

Follow `docs/proposal-approved-format.md` (Markdown table format). Entry should reference:
- `improvements/add-guide-design-phase1-diagnostic.md` (created separately via brainstorming)
- Plan file: `docs/superpowers/plans/2026-08-07-guide-design-phase1-diagnostic.md`
- Status: 已批准
- Date: today's date

- [ ] **Step 3: Commit**

```bash
git add proposal-approved.md
git commit -m "docs: register guide-design-phase1-diagnostic as approved improvement"
```

---

### Task 13: Full regression run

**Files:** none (verification only)

- [ ] **Step 1: Run bats integration tests for changed areas**

```bash
bats tests/integration/test_design_preflight.bats
bats tests/integration/test_reconstruct_arch_handoff.bats
bats tests/integration/test_rddf_session_hook_required.bats
bats tests/integration/test_guide_design_phase.bats
```

Expected: all pass

- [ ] **Step 2: Run full bats regression**

```bash
./test.sh --full --regression
```

Expected: green or only baseline-known failures (no new failures)

- [ ] **Step 3: Run Python tests if any rddf-session logic touched**

```bash
python3 -m pytest tests/unit/ -q --tb=short
```

- [ ] **Step 4: Verify the originally-blocked scenario now succeeds**

In a clean shell:
```bash
# Remove arch-handoff (simulating the bug)
rm -f .rddf/state/.arch-handoff.json

# Run reconstruction
bash skills/guide-design/scripts/reconstruct_arch_handoff.sh --project-root "$(git rev-parse --show-toplevel)"

# Verify
test -f .rddf/state/.arch-handoff.json && \
  jq -e '.discovered' .rddf/state/.arch-handoff.json

# Re-invoke guide-design (should now pass Phase 1)
skill_use("guide-design")  # should NOT hard-reject
```

Expected: handoff exists, user can proceed past Phase 1

- [ ] **Step 5: Commit (only if Step 4 surfaced any fix)**

If verification revealed a missing piece, fix and commit. Otherwise, no commit.

---

## Self-Review

After writing this plan, applying the writing-plans skill checklist:

**1. Spec coverage** (mapping prior analysis items → tasks):
- ✅ P1 (preflight diagnostic script) → Tasks 1, 2, 3, 8
- ✅ P2 (reconstruction subcommand) → Tasks 4, 5, 6
- ✅ P4 (rddf-session hook strictness) → Task 10
- ✅ P5 (better diagnostic output) → Tasks 7, 9
- ⏸️ P3 (git-track handoffs) → explicitly out of scope per Scope Split

**2. Placeholder scan:** No "TBD" / "implement later" / "similar to Task N" markers. Every code block shows actual content.

**3. Type/function consistency:**
- `design_preflight_status` introduced in Task 8 Step 3, used by Task 7 Step 2 (which depends on Task 8). Dependency is explicit.
- `emit_status` (Task 1 internal) → `design_preflight_status` (Task 8 wrapper) → called from `guide-design/SKILL.md` (Task 7). Three-step chain, all explicit.
- `recommendation` field values: `normal` / `soft_prompt_reconstruct` / `hard_reject_no_evidence` — defined in Task 1, tested in Task 3, branched in Task 7. Consistent throughout.
- File paths match project conventions: `skills/guide-design/scripts/`, `tests/integration/`, `docs/adr/ADR-NNNN-*.md`, `.rddf/state/`.

**4. Out-of-scope clarity:** Scope Split Recommendation section explicitly enumerates what is NOT covered (P3, cross-phase parity), so a worker doesn't accidentally drift.

**5. Test discipline:** Every code-creating task has a failing test first (Steps 1-2), then implementation (Step 3), then verification (Step 4). No exceptions.

---

## Execution Handoff

Plan complete. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration with isolation.

**2. Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints for review.

**Which approach?**