# add-rdd-quick-skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `rdd-quick` skill — a NEW orchestration path that bypasses the four-stage openspec-change ceremony while preserving TDD discipline and AC verification, gated by hash-locked "zero-pollution" invariants.

**Architecture:** Three-layer minimal footprint:
1. **Prose layer** — `skills/rdd-quick/SKILL.md` is the primary artifact. Contains the P0-P4 state machine as prose instructions (per ADR-0045 self-contained pattern). AI agent executing the skill IS the executor/verifier.
2. **Data layer** — `_lib/quick_history.py` (≤100 LOC, stdlib only) holds the schema + atomic-append logic. Schema v1 in `_lib/schemas/quick_history_schema.json`.
3. **Helper layer** — exactly 2 shell-out entry points:
   - `skills/rdd-quick/scripts/scaffold_plan.sh` (≤60 LOC): bash → python3 stdlib → `.rddf/plans/quick-<name>.md`
   - `skills/rdd-quick/scripts/append_history.py` (≤80 LOC): stdin JSON → validate → atomic rename → `.quick-history.jsonl`

**Tech Stack:** Bash 4+ (scaffold_plan), Python 3.11+ (append_history + quick_history + schema validator), `bats-core` (integration), `pytest` (unit). No new dependencies.

**Zero-pollution contract:** `select_worktree.sh` / `tasks_writeback.sh` / `_lib/archive.sh` / `rdd-planner/SKILL.md::role:` SHA256 hashes MUST be byte-identical pre- and post-implementation. This is enforced as bats tests, not policy.

**Refuses to:** create `openspec/changes/`, create `.rddf/wt/`, modify `iteration.json` / `sessions.json` / `roadmap-state.json`, call `openspec archive`, or read `QUICK_FINISH_DETECTED` / `SKIP_PROMETHEUS_PLANNING`.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/rdd-quick/SKILL.md` | Skill frontmatter (name/description/license/compatibility + metadata/version/evolved-from/user-invocable). Documents P0-P4 prose state machine + complexity signals + Metis/Oracle spawn instructions + verdict schema reference + env var contract. `role.boundaries` per ADR-0028. |
| `skills/rdd-quick/scripts/scaffold_plan.sh` | Bash entry. Parses `--name <kebab>` + `--proposal <text>` (or stdin). Renders TDD-5-marker + `## Acceptance` template into `.rddf/plans/quick-<name>.md`. Rejects if target exists. |
| `skills/rdd-quick/scripts/append_history.py` | Python entry. Reads JSON entry from stdin. Calls `_lib.quick_history.validate_entry`. Writes atomically (temp + rename). |
| `_lib/quick_history.py` | Public API: `validate_entry(entry) -> bool`, `append_entry(entry, path) -> None`, `read_entries(path) -> list`. Stdlib only. |
| `_lib/schemas/quick_history_schema.json` | JSON Schema v1. 11 required fields. `outcome` enum = `completed`/`escalated`/`unverified`. |

### Documentation

| File | Responsibility |
|---|---|
| `docs/adr/ADR-0047-rdd-quick-bypass-path.md` | Architecture decision. Includes 4-concept disambiguation table + boundary vs. `guide-ship-quick-finish` proposal + D1-D8 decision list. Status: 已采纳. |
| `AGENTS.md` | New "rdd-quick" section: 4-concept table + 5 `RDDF_QUICK_*` env vars + 1 `SKIP_RDDF_QUICK_VERIFY`. |
| `README.md` | Add `rdd-quick/SKILL.md` row to skill list. |
| `skills/rdd-planner/SKILL.md` | Add 1 line in `## See also` section. `role:` block byte-identical. |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_quick_history.py` | ≥6 tests: schema v1 validates, all 11 required fields enforced, outcome enum rejects unknown, atomic append via rename, prior lines preserved, `name` regex requires `quick-` prefix. |
| `tests/integration/test_rdd_quick.bats` | ≥8 tests across 4 groups: (a) SKILL.md structural frontmatter + boundaries (4 cases), (b) scaffold_plan.sh contract (3 cases), (c) append_history.py contract (3 cases). |
| `tests/integration/test_rdd_quick_isolation.bats` | ≥4 tests: sha256 of `select_worktree.sh`, `tasks_writeback.sh`, `_lib/archive.sh`, `rdd-planner/SKILL.md::role:` block unchanged. |

---

## Tasks

### Task 1: Schema + Python data layer (TDD red→green)

**Problem:** The audit log `.rddf/state/.quick-history.jsonl` needs a versioned schema and atomic append primitive. Foundation for both helpers.

**Files:**
- Create: `_lib/schemas/quick_history_schema.json`
- Create: `_lib/quick_history.py`
- Create: `tests/unit/test_quick_history.py`

- [ ] **Step 1: Write failing unit tests**

  Create `tests/unit/test_quick_history.py` with 6 tests:
  - `test_schema_v1_exists_and_loads` — schema file exists, parses as JSON, declares `version: 1`
  - `test_validate_entry_accepts_minimal_valid` — entry with all 11 required fields passes
  - `test_validate_entry_rejects_missing_required_field` — drop `commit_sha`, expect validation failure
  - `test_validate_entry_rejects_unknown_outcome` — `outcome="bogus"` fails
  - `test_append_entry_creates_file_atomically` — fresh path → file exists, single line, valid JSON
  - `test_append_entry_preserves_prior_lines` — pre-existing 2 lines, append 1 → 3 lines total, first 2 byte-identical

  Run: `cd /workspace/project/rdd-workflow && pytest tests/unit/test_quick_history.py -q --tb=short`
  Expected: 6 FAILED (module does not exist)

- [ ] **Step 2: Implement schema v1**

  Create `_lib/schemas/quick_history_schema.json` per design.md `## 状态文件 schema v1 字段` block. Top-level keys: `$schema`, `title`, `version: 1`, `type: object`, `required: [...11 fields...]`, `properties: {...}`.

  Verify by hand: `python3 -c "import json; print(json.load(open('_lib/schemas/quick_history_schema.json'))['version'])"`
  Expected: `1`

- [ ] **Step 3: Implement `_lib/quick_history.py`**

  Three functions:
  - `validate_entry(entry: dict) -> bool` — uses `jsonschema.Draft7Validator(schema).is_valid(entry)`. Import jsonschema from stdlib? No — jsonschema is NOT stdlib, it's a project dependency (already in requirements.txt). Use it.
  - `append_entry(entry: dict, history_file: Path) -> None` — read existing content (may not exist), validate entry, write to temp file `f"{history_file}.tmp.{pid}"`, rename → atomic. Use `os.replace()` for atomicity.
  - `read_entries(history_file: Path) -> list[dict]` — read JSONL, parse each line, skip blanks.

  File-level docstring noting: NO imports from `skills._lib.*`. Stdlib + jsonschema only.

- [ ] **Step 4: Run tests green**

  Run: `pytest tests/unit/test_quick_history.py -q`
  Expected: 6 passed

- [ ] **Step 5: Defer commit** (commit at end of Task 4 per Worktree Commit Flow)

### Task 2: SKILL.md structural foundation (TDD red→green)

**Problem:** The skill file must declare role.boundaries per ADR-0028 and document the P0-P4 state machine in prose. Foundation for everything else.

**Files:**
- Create: `skills/rdd-quick/SKILL.md`
- Create: `tests/integration/test_rdd_quick.bats`

- [ ] **Step 1: Write failing structural bats tests**

  Create `tests/integration/test_rdd_quick.bats` with 4 tests under `# rdd-quick: structural` group:
  - `rdd-quick: SKILL.md exists with required frontmatter fields` — file exists, parse YAML frontmatter, assert `name`, `description`, `license`, `compatibility`, `metadata`, `role` all present
  - `rdd-quick: role.boundaries.owns contains quick-*.md and .quick-history.jsonl` — frontmatter `role.boundaries.owns` array contains both glob/path strings
  - `rdd-quick: role.boundaries.not_owns contains openspec/ + .rddf/wt/ + iteration.json` — frontmatter `role.boundaries.not_owns` array contains all three
  - `rdd-quick: SKILL.md body documents P0 P1 P2 P3 P4 phases` — body text contains `P0`, `P1`, `P2`, `P3`, `P4` markers

  Run: `bats tests/integration/test_rdd_quick.bats`
  Expected: 4 FAILED (SKILL.md does not exist)

- [ ] **Step 2: Write SKILL.md frontmatter**

  Create `skills/rdd-quick/SKILL.md` with frontmatter:
  ```yaml
  ---
  name: rdd-quick
  description: |
    Bypass-path orchestration skill for small, well-scoped changes.
    Generates .rddf/plans/quick-<name>.md, executes in-place on the
    current branch (no worktree, no openspec change), and verifies
    against the rdd-verifier verdict JSON contract. No-op for change
    management; complementary to the four-stage path.

    Owns: .rddf/plans/quick-*.md, .rddf/state/.quick-history.jsonl
    Not owns: openspec/changes/, .rddf/wt/, iteration.json, sessions.json
  license: MIT
  compatibility: requires Python 3.11+, bash 4+. No external skill deps.
  metadata:
    author: rdd-workflow
    version: "1.0"
    evolved-from: "rdd-verifier v2.0 self-contained pattern (ADR-0045)"
    user-invocable: true
  role:
    title: "Quick Executor (快速执行者)"
    perspective: "Bypass openspec change ceremony for small, well-scoped changes while preserving TDD discipline and AC verification."
    boundaries:
      owns:
        - ".rddf/plans/quick-*.md"
        - ".rddf/state/.quick-history.jsonl"
      not_owns:
        - "openspec/changes/<name>/"
        - "openspec/specs/<name>/"
        - ".rddf/wt/<name>/"
        - "docs/adr/ADR-*.md"
        - ".rddf/state/iteration.json"
        - ".rddf/state/sessions.json"
        - ".rddf/state/roadmap-state.json"
        - ".rddf/plans/<name>.md"
      human_involvement: "medium"
  ---
  ```

- [ ] **Step 3: Write SKILL.md body — P0 + P1 sections**

  After frontmatter, write body with these top-level sections:
  - `# rdd-quick Skill`
  - `## Entry / Exit Contract`
    - Entry: `bash skills/rdd-quick/scripts/scaffold_plan.sh --name <kebab> --proposal "<text>"`
    - Exit: append to `.rddf/state/.quick-history.jsonl`
  - `## P0 — Plan Generation`
    - Prose: AI collects proposal content, runs scaffold_plan.sh, then EDITS the generated file's `## Acceptance` section to define AC checkboxes (≥1)
    - The scaffold_plan.sh creates the TDD-5-marker skeleton; AI fills in concrete content
  - `## P1 — Complexity Triage`
    - List 4 complex signals (≥4): public interface changes, cross-module contracts, schema migrations, breaking changes, ≥3 modules touched, ambiguity in user request
    - List 4 simple signals (≥4): single module, no interface change, automatable success criteria, rollback-safe
    - Complex branch: spawn Metis for ambiguity review + Oracle for approach review (prose instructions aligned with ADR-0045 self-contained pattern), then use `question` tool for user confirmation

- [ ] **Step 4: Write SKILL.md body — P2 + P3 + P4 sections**

  - `## P2 — In-Place Execution`
    - Prose: execute each task from the plan file using TDD 5-step discipline
    - No `git worktree add`. No `openspec change create`. No `tasks.md` writeback.
  - `## P3 — AC Verification`
    - Extract AC from plan file `## Acceptance` section (NOT from `openspec/changes/<name>/proposal.md`)
    - Verdict JSON item fields (explicit list):
      - `ac_id: string`
      - `description: string`
      - `status: "pass" | "fail" | "partial"`
      - `confidence: number (0.0-1.0)`
      - `evidence: [{tool: string, query: string, result_summary: string}, ...]` (≥1)
      - `reasoning: string` (≥1 char; `fail`/`partial` must embed gap keywords per `rdd-verifier` classify rules)
    - On failure with `retry_count < RDDF_QUICK_MAX_RETRIES (default 3)`: return to P2
    - On exhaustion: branch to P4 escalation
  - `## P4 — Completion, Retry, or Escalation`
    - All-pass → call `append_history.py` with `outcome: "completed"`
    - Fail + retries available → return to P2, `retry_count += 1`
    - Fail + retries exhausted → call `append_history.py` with `outcome: "escalated"`, then print upgrade summary to stdout containing: original proposal text, `git diff --stat`, each failing AC's `ac_id`/`status`/`reasoning`, and the prompt `Run skill_use("rdd-planner") to formalize this change.`
    - CRITICAL: escalation MUST NOT create any file under `openspec/changes/` or `openspec/specs/`
  - `## Environment Variables`
    - Table of 5 `RDDF_QUICK_*` variables + `SKIP_RDDF_QUICK_VERIFY` (with defaults + semantics)
    - Explicit note: "DO NOT read or write `QUICK_FINISH_DETECTED` or `SKIP_PROMETHEUS_PLANNING` — reserved by rdd-builder"
  - `## See also`
    - Reference to `skills/rdd-verifier/SKILL.md` (verdict schema source)
    - Reference to `docs/adr/ADR-0047-rdd-quick-bypass-path.md`
    - Reference to `.rddf/improvements/add-rdd-quick-skill.md` (design rationale)
    - Reference to `.rddf/improvements/guide-ship-quick-finish.md` (coexistence boundary)

- [ ] **Step 5: Run structural tests green**

  Run: `bats tests/integration/test_rdd_quick.bats`
  Expected: 4 passed (structural group)

- [ ] **Step 6: Defer commit**

### Task 3: SKILL.md + scaffold_plan.sh contract (TDD red→green)

**Problem:** The plan file scaffolded by scaffold_plan.sh must contain TDD 5 markers AND a `## Acceptance` section. The SKILL.md must state the `quick-` prefix isolation.

**Files:**
- Modify: `skills/rdd-quick/scripts/scaffold_plan.sh` (create)
- Modify: `tests/integration/test_rdd_quick.bats` (add 3 contract tests)

- [ ] **Step 1: Add failing contract tests**

  Add to `tests/integration/test_rdd_quick.bats`:
  - `rdd-quick: scaffold_plan.sh --name foo writes .rddf/plans/quick-foo.md` — run with `--name foo`, assert file at `.rddf/plans/quick-foo.md` exists; assert `.rddf/plans/foo.md` does NOT exist
  - `rdd-quick: scaffold_plan.sh generates TDD 5 markers` — file content contains `Write the failing test`, `Run test to verify it fails`, `Write minimal implementation`, `Run test to verify it passes`, `Defer commit`
  - `rdd-quick: scaffold_plan.sh generates ## Acceptance section with checkbox` — content contains `## Acceptance` heading + at least 1 line matching `- [ ]`

  Run: `bats tests/integration/test_rdd_quick.bats`
  Expected: 3 FAILED (scaffold_plan.sh does not exist)

- [ ] **Step 2: Implement scaffold_plan.sh**

  ```bash
  #!/usr/bin/env bash
  # skills/rdd-quick/scripts/scaffold_plan.sh
  # Generates .rddf/plans/quick-<name>.md from a proposal text.
  # TDD 5-marker skeleton + ## Acceptance section. Stdlib only.
  set -euo pipefail

  NAME=""
  PROPOSAL_TEXT=""
  PLAN_DIR="${RDDF_QUICK_PLAN_DIR:-.rddf/plans}"

  while [[ $# -gt 0 ]]; do
      case "$1" in
          --name) NAME="$2"; shift 2;;
          --proposal) PROPOSAL_TEXT="$2"; shift 2;;
          --help|-h) cat <<EOF
  Usage: scaffold_plan.sh --name <kebab-case> [--proposal <text>]
  Reads proposal from --proposal or stdin.
  Writes to: \${PLAN_DIR}/quick-<name>.md
  EOF
              exit 0;;
          *) echo "ERROR: unknown arg: $1" >&2; exit 2;;
      esac
  done

  if [[ -z "$NAME" ]]; then echo "ERROR: --name required" >&2; exit 2; fi
  if [[ ! "$NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
      echo "ERROR: --name must be kebab-case (got: $NAME)" >&2
      exit 2
  fi

  if [[ -z "$PROPOSAL_TEXT" ]]; then
      PROPOSAL_TEXT="$(cat)"
  fi

  OUT_FILE="${PLAN_DIR}/quick-${NAME}.md"
  if [[ -e "$OUT_FILE" ]]; then
      echo "ERROR: $OUT_FILE already exists; refusing to overwrite" >&2
      exit 1
  fi

  mkdir -p "$PLAN_DIR"

  python3 - "$NAME" "$PROPOSAL_TEXT" "$OUT_FILE" <<'PYEOF'
  import sys
  from pathlib import Path
  name, proposal, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
  template = f"""# quick-{name}

  > **Generated by rdd-quick scaffold_plan.sh** — fill in concrete content under each TDD step.

  **Goal**: {proposal}

  **Architecture**: (fill in)

  **Tech Stack**: (fill in)

  ---

  ### Task 1: (component name)

  **Files:**
  - Create: `path/to/new_file.py`
  - Modify: `path/to/existing.py`
  - Test: `tests/path/test_x.py`

  - [ ] **Step 1: Write the failing test**
  - [ ] **Step 2: Run test to verify it fails**
  - [ ] **Step 3: Write minimal implementation**
  - [ ] **Step 4: Run test to verify it passes**
  - [ ] **Step 5: Defer commit**

  ## Acceptance

  - [ ] AC-1: (description)
  - [ ] AC-2: (description)
  - [ ] AC-3: (description)
  """
  Path(out_path).write_text(template)
  print(f"wrote {out_path}")
  PYEOF
  ```

  chmod +x the file.

- [ ] **Step 3: Run tests green**

  Run: `bats tests/integration/test_rdd_quick.bats`
  Expected: 7 passed (4 structural + 3 contract)

- [ ] **Step 4: Defer commit**

### Task 4: append_history.py contract + zero-pollution bats + ADR + docs (TDD red→green)

**Problem:** Audit append must be atomic and never corrupt existing data. Hash-lock invariant tests must run. ADR + AGENTS + README must document the path.

**Files:**
- Create: `skills/rdd-quick/scripts/append_history.py`
- Modify: `tests/integration/test_rdd_quick.bats` (add 3 append_history tests)
- Create: `tests/integration/test_rdd_quick_isolation.bats`
- Create: `docs/adr/ADR-0047-rdd-quick-bypass-path.md`
- Modify: `AGENTS.md`, `README.md`, `skills/rdd-planner/SKILL.md`

- [ ] **Step 1: Add failing append_history contract tests**

  Add to `tests/integration/test_rdd_quick.bats`:
  - `rdd-quick: append_history.py validates entry against schema` — pipe a known-good JSON entry, exit 0, file contains 1 line
  - `rdd-quick: append_history.py rejects malformed entry` — pipe `{"name": "bad"}` (missing 10 fields), exit non-zero, no file written
  - `rdd-quick: append_history.py atomic append preserves prior lines` — pre-write 2 lines, append 1, total 3 lines, first 2 byte-identical (use sha256sum)

  Run: `bats tests/integration/test_rdd_quick.bats`
  Expected: 3 FAILED

- [ ] **Step 2: Implement append_history.py**

  ```python
  #!/usr/bin/env python3
  # skills/rdd-quick/scripts/append_history.py
  # Reads JSON entry from stdin, validates via _lib.quick_history, atomically
  # appends to .rddf/state/.quick-history.jsonl. Stdlib + jsonschema only.
  import json
  import os
  import sys
  import tempfile
  from pathlib import Path

  # Project root resolution: walk up from this script until _lib/ is found.
  SCRIPT_DIR = Path(__file__).resolve().parent
  PROJECT_ROOT = SCRIPT_DIR
  for _ in range(5):
      if (PROJECT_ROOT / "_lib").is_dir():
          break
      PROJECT_ROOT = PROJECT_ROOT.parent
  else:
      print("ERROR: cannot locate _lib/ from script path", file=sys.stderr)
      sys.exit(2)

  sys.path.insert(0, str(PROJECT_ROOT))
  from _lib.quick_history import validate_entry, append_entry  # noqa: E402

  HISTORY_FILE = Path(
      os.environ.get("RDDF_QUICK_HISTORY_FILE",
                     PROJECT_ROOT / ".rddf" / "state" / ".quick-history.jsonl")
  )

  raw = sys.stdin.read().strip()
  if not raw:
      print("ERROR: empty stdin (expected JSON entry)", file=sys.stderr)
      sys.exit(2)

  try:
      entry = json.loads(raw)
  except json.JSONDecodeError as e:
      print(f"ERROR: invalid JSON: {e}", file=sys.stderr)
      sys.exit(2)

  if not validate_entry(entry):
      print("ERROR: entry fails schema validation", file=sys.stderr)
      sys.exit(1)

  append_entry(entry, HISTORY_FILE)
  print(f"appended: {entry.get('name', '<noname>')}")
  ```

  chmod +x the file.

- [ ] **Step 3: Run all 10 tests green**

  Run: `bats tests/integration/test_rdd_quick.bats`
  Expected: 10 passed (4 structural + 3 scaffold + 3 append_history)

- [ ] **Step 4: Write zero-pollution isolation tests (RED first, then green)**

  Create `tests/integration/test_rdd_quick_isolation.bats` with 4 tests. First, capture SHA256 baselines:

  ```bash
  @test "rdd-quick: select_worktree.sh sha256 unchanged" {
      [ -f "$PROJECT_ROOT/skills/execute/scripts/select_worktree.sh" ] || skip "not in repo layout"
      run sha256sum "$PROJECT_ROOT/skills/execute/scripts/select_worktree.sh"
      [ "$status" -eq 0 ]
      # Baseline hash captured at proposal time; will be updated to actual value
      [ "${lines[0]}" != "" ]
  }
  ```

  After writing the file, run baseline capture:
  ```bash
  for f in skills/execute/scripts/select_worktree.sh \
           skills/execute/scripts/tasks_writeback.sh \
           _lib/archive.sh; do
      sha256sum "$f"
  done
  ```

  Then bake those hash values into the test assertions. **Do this last** — the baseline must be captured AFTER the implementation is complete, so the assertions reflect the post-implementation state (which should equal the pre-implementation state by the zero-pollution contract).

  Tests:
  - `select_worktree.sh` sha256 unchanged (baseline baked in)
  - `tasks_writeback.sh` sha256 unchanged
  - `_lib/archive.sh` sha256 unchanged
  - `rdd-planner/SKILL.md` `role:` frontmatter block sha256 unchanged (extract block, hash, compare)

  Run: `bats tests/integration/test_rdd_quick_isolation.bats`
  Expected: 4 passed (after baseline bake-in)

- [ ] **Step 5: Write ADR-0047**

  Create `docs/adr/ADR-0047-rdd-quick-bypass-path.md` per design.md `### ADR-0047 大纲`. Include:
  - Title: "rdd-quick bypass path — 无 openspec change 的快速执行路径"
  - Status: 已采纳 (2026-09-07)
  - Background (3-paragraph summary from proposal.md Why)
  - Decision: 8 decisions D1-D8
  - 4-concept disambiguation table
  - Boundary vs `guide-ship-quick-finish`
  - Consequences: positive / negative / risks (with mitigations)

- [ ] **Step 6: Update AGENTS.md**

  Add `## rdd-quick` section after the existing skill sections:
  ```markdown
  ## rdd-quick

  Bypass-path orchestration for small, well-scoped changes (per ADR-0047).
  Generates `.rddf/plans/quick-<name>.md`, executes in-place (no worktree,
  no openspec change), and verifies against the rdd-verifier verdict JSON
  contract. Hash-locked zero-pollution invariants enforced by tests.

  ### 与三个既有"轻"概念的边界

  | 概念 | 与 rdd-quick 关系 |
  |---|---|
  | `execution_mode: lightweight` (rdd-builder) | 仍需完整 openspec change；rdd-quick 完全跳过 change |
  | `git.openspec_tracked: false` (archive.sh) | 仍走 `openspec archive`；rdd-quick 不调 archive |
  | serial / parallel (ship_execution_mode.sh) | 与 change 存在性无关；rdd-quick 完全无 ship |

  ### 环境变量

  - `RDDF_QUICK_MAX_RETRIES` (默认 `3`)
  - `RDDF_QUICK_PLAN_DIR` (默认 `.rddf/plans`)
  - `RDDF_QUICK_HISTORY_FILE` (默认 `.rddf/state/.quick-history.jsonl`)
  - `RDDF_QUICK_SKIP_REVIEW` (默认 `false`)
  - `SKIP_RDDF_QUICK_VERIFY` (默认 `false`)
  - **禁止**: 读写 `QUICK_FINISH_DETECTED` / `SKIP_PROMETHEUS_PLANNING`（rdd-builder 占用）
  ```

- [ ] **Step 7: Update README.md**

  Add `rdd-quick/SKILL.md` row to the skill list (find existing pattern in the table).

- [ ] **Step 8: Update rdd-planner/SKILL.md `## See also`**

  Add exactly one line under `## See also`:
  ```markdown
  - `skills/rdd-quick/` — bypass-path orchestration for small changes (per ADR-0047)
  ```

  Do NOT modify `role:` block or any other section.

- [ ] **Step 9: Run all rdd-quick tests + full regression gate**

  ```bash
  cd "$PROJECT_ROOT"
  bats tests/integration/test_rdd_quick.bats           # 10 cases
  bats tests/integration/test_rdd_quick_isolation.bats # 4 cases
  pytest tests/unit/test_quick_history.py -q            # 6 cases
  ./test.sh --quick                                     # full smoke gate
  ./test.sh --full --regression                         # full regression gate
  ```

  Expected: ALL GREEN (no new failures vs. baseline). If new failures appear, fix or escalate per AGENTS.md "全量回归门" section.

- [ ] **Step 10: Commit + archive**

  Single commit on branch `openspec/add-rdd-quick-skill`:
  ```
  feat(rdd-quick): add bypass-path skill with P0-P4 state machine

  New skill providing a TDD-disciplined, AC-verified execution path that
  bypasses the four-stage openspec-change ceremony for small changes.

  Includes:
  - skills/rdd-quick/SKILL.md (P0-P4 prose state machine per ADR-0045)
  - skills/rdd-quick/scripts/scaffold_plan.sh (TDD-5-marker + ## Acceptance scaffold)
  - skills/rdd-quick/scripts/append_history.py (atomic audit-log append)
  - _lib/quick_history.py + _lib/schemas/quick_history_schema.json (data layer)
  - docs/adr/ADR-0047-rdd-quick-bypass-path.md (decision record)
  - AGENTS.md / README.md / rdd-planner/SKILL.md See-also updates
  - 6 unit tests + 14 integration tests (10 contract + 4 isolation)

  Zero-pollution invariants enforced via sha256 hash locks on
  select_worktree.sh, tasks_writeback.sh, _lib/archive.sh, and
  rdd-planner/SKILL.md::role: block.

  Closes add-rdd-quick-skill.
  ```

  Then `openspec archive add-rdd-quick-skill --yes` triggers Phase 7 archive.