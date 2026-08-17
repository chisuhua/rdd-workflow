# AC Verifier Skill — Design

**Date**: 2026-08-17
**Status**: Draft (awaiting user review)
**Author**: brainstorming session output
**Related**: audit of 9 archived changes (2026-08-17) revealed 3 changes claimed ACs not actually implemented

## 1. Problem & Motivation

### Observed failure mode

In the 2026-08-17 audit of 9 archived changes:

| Change | Unimplemented ACs |
|--------|-------------------|
| `add-contract-lint-ci-gate` | `rddf contract-check` CLI registration; `STRICT_CONTRACT_GATE` env var wiring; README CI integration example (3 ACs) |
| `add-cross-repo-deps-orchestration` | `STRICT_DEPS_GATE` env var wiring; README cross-repo example (2 ACs) |
| `add-cross-repo-state-schemas` | `"version": {"const": "v1"}` field on 17 schemas (1 AC across 17 files) |

All three were archived with `tasks.md` 100% completed and all tests passing, yet **proposal ACs were not actually satisfied**. Current `archive_gate_check` only counts `- [x]` checkboxes in `tasks.md`, not proposal ACs.

### Root cause

Two structural gaps:

1. **No link between proposal AC and archived change**: proposals carry `## 验收标准` but archive flow never reads them.
2. **No semantic verification**: tasks.md checkbox checking is procedural, not semantic — "I checked the box" ≠ "the requirement is met".

### Goal

Add a verification skill that runs before archive, semantically checking whether each `## 验收标准` bullet is genuinely satisfied in the committed code. Catches the failure mode above.

## 2. Design Decisions (from brainstorming)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Verification mechanism | AI semantic (LLM with tools) | Prose ACs cannot be reduced to deterministic checks; LLM with grep/codegraph/codebase-memory-mcp can investigate claims |
| Default trigger | Always run | Audit found 100% gap rate; opt-in would miss most cases |
| Context for LLM | AC text + new commits + tools (grep, codegraph, codebase-memory-mcp, git log) | Tool-augmented investigation beats text-only; matches user's mental model of "AI first understands AC, then investigates claims" |
| Output format | Per-AC structured JSON verdict | Machine-actionable for gate logic; preserves per-AC granularity |
| Failure handling | Default warning; `STRICT_AC_GATE=yes` blocks archive | Consistent with existing `STRICT_*_GATE` pattern (CHANGE_GATE, DESIGN_GATE, DEPS_GATE); gradual adoption |
| AC extraction | Only bullets in `## 验收标准` section | 100% of existing proposals comply; strict = low false-positive |
| Architecture | Hybrid (new skill + archive integration) | Mirrors `contract-check` + `rdd-doctor` pattern; supports both manual and automatic invocation |

## 3. Architecture

### Component diagram

```
   proposal.md (## 验收标准 section)
         │
         ▼
   ac_verifier.py: parse_acs()           # extract bullets
         │
         ▼
   ac_verifier.py: ai_verify_acs()       # single LLM call with tools
         │     ├─ codegraph_explore()
         │     ├─ grep_app_searchGitHub()
         │     ├─ codebase-memory-mcp queries
         │     └─ git log / diff (subprocess)
         │
         ▼
   Per-AC verdict JSON
   [{ac_id, status, confidence, evidence, reasoning}, ...]
         │
         ├──▶ .rddf/state/.ac-verification.jsonl   (audit log, append-only)
         ├──▶ stdout summary                       (human-readable)
         └──▶ exit code → gate decision
                  │
                  ▼
             archive_gate_check return code
```

### Key design constraints

1. **Single LLM call** for all ACs in one batch — avoids N×token cost; one prompt with multiple verifications.
2. **Tools exposed via MCP** (codegraph, codebase-memory-mcp, context7) and via Python subprocess (grep, git). All tools declared in system prompt; LLM chooses.
3. **Fail-closed on parse failure**: if LLM output is not valid JSON, retry once with schema reminder, then mark all ACs as `fail`. Never silently pass.
4. **Append-only audit log**: `.rddf/state/.ac-verification.jsonl` accumulates all verification attempts (success, failure, skip). Enables historical forensics.

## 4. Component Interfaces

### Skills layout

```
skills/ac-verifier/
  SKILL.md                        # frontmatter + user-facing docs (≥40 lines)
  scripts/
    ac_verifier.sh                # bash wrapper (env, args, exit codes)
    ac_verifier.py                # Python agent driver (≤250 LOC)
    ac_verifier_prompt.py         # prompt templates + tool manifest (≤100 LOC)
    ac_verifier_mocks.py          # mock LLM for tests (≤50 LOC)
```

### `ac_verifier.sh` interface

```bash
ac_verifier.sh <change-name> [--dry-run] [--strict] [--skip]

Arguments:
  <change-name>       Required. OpenSpec change name (matches directory under openspec/changes/)

Flags:
  --dry-run           Run AI verification but do NOT write audit log or affect gate
  --strict            Equivalent to STRICT_AC_GATE=yes (block archive on any fail)
  --skip              Equivalent to SKIP_AC_VERIFICATION=yes (no-op, exit 2)

Exit codes:
  0  All ACs pass (or no AC section found)
  1  At least one AC fail (warning by default; error under STRICT_AC_GATE)
  2  Skipped (SKIP_AC_VERIFICATION=yes, or no proposal.md found, or no AC section)
  3  Error (LLM call failed after retries, missing API key, etc.)

Environment variables:
  STRICT_AC_GATE=yes          Promote AC fail → archive blocker (matches STRICT_*_GATE pattern)
  SKIP_AC_VERIFICATION=yes    Skip verification entirely (matches SKIP_* pattern)
  AC_LLM_MOCK=yes             Use mock LLM (testing only)
  AC_LLM_PROVIDER             "openai" | "anthropic" | "local-ollama" (default: auto-detect from env)
  AC_LLM_MODEL                Model name (default: provider default)
  AC_LLM_TIMEOUT              Seconds per LLM call (default: 60)
```

### Python module API

```python
# skills/ac-verifier/scripts/ac_verifier.py

def parse_acs(proposal_path: Path) -> list[dict]:
    """Extract AC bullets from `## 验收标准` section.
    Returns list of {ac_id: "AC-N", description: str, has_checkbox: bool}.
    Empty list if section missing.
    """

def build_agent_prompt(acs: list[dict], change_name: str) -> tuple[str, str]:
    """Build (system_prompt, user_prompt) pair for LLM.
    System prompt declares tools + JSON schema; user prompt lists ACs.
    """

def invoke_ai_agent(system: str, user: str, mock: bool = False) -> str:
    """Call LLM with tools. Returns raw text. Handles mock mode.
    On non-OK response: raise AcVerifierError after retries.
    """

def parse_verdict(raw: str, expected_count: int) -> list[dict]:
    """Parse LLM JSON output. Validate against schema. Auto-fill missing ACs with fail.
    Raises AcVerifierError on unparseable JSON after retry.
    """

def apply_gate_rules(verdict: list[dict], strict: bool) -> int:
    """Return exit code based on verdict + env vars.
    0 if all pass; 1 if any fail (or 1 always if strict); 2 if no ACs.
    """

def append_audit_log(verdict: list[dict], change_name: str, exit_code: int) -> None:
    """Append JSONL entry to .rddf/state/.ac-verification.jsonl.
    Entry: {ts, change_name, verdict, exit_code, llm_model, llm_provider}.
    """
```

### Audit log schema

```json
// .rddf/state/.ac-verification.jsonl (one JSON per line)
{
  "ts": "2026-08-17T07:35:00.000Z",
  "change_name": "add-contract-lint-ci-gate",
  "exit_code": 1,
  "llm_provider": "anthropic",
  "llm_model": "claude-opus-4",
  "duration_ms": 8234,
  "verdict": [
    {"ac_id": "AC-1", "status": "pass", "confidence": 0.95, "reasoning": "..."},
    {"ac_id": "AC-2", "status": "fail", "confidence": 0.88, "reasoning": "..."}
  ]
}
```

## 5. AI Agent Prompt Contract

### System prompt (template)

```
You are an AC verification agent for rdd-workflow. Given an OpenSpec change's
acceptance criteria (ACs) and access to code investigation tools, you must
determine whether each AC is genuinely satisfied in the committed code.

Available tools:
- codegraph_explore(query): structural code search via knowledge graph
- grep_app_searchGitHub(query, path?, language?): pattern matching
- codebase-memory-mcp: function/class/import lookup (via MCP)
- git log / git diff (subprocess via your driver): commit history

For each AC, you MUST:
1. Make at least one tool call to gather evidence
2. Cross-reference AC text against actual implementation
3. Issue verdict: "pass" (genuinely satisfied) | "fail" (not satisfied) |
   "partial" (partially satisfied with caveats)
4. Provide 0.0-1.0 confidence score
5. Cite evidence in 1-2 sentences

Output format (strict JSON array, no other text):
[
  {
    "ac_id": "AC-1",
    "description": "<verbatim AC text>",
    "status": "pass" | "fail" | "partial",
    "confidence": 0.0-1.0,
    "evidence": [
      {"tool": "codegraph", "query": "...", "result_summary": "..."}
    ],
    "reasoning": "1-2 sentences justifying verdict"
  }
]

Array length MUST equal AC count. Omitting any AC invalidates response.
```

### Retry protocol

1. **First attempt**: standard prompt
2. **On JSON parse failure**: retry once with appended reminder "Your previous output was not valid JSON. Re-emit the JSON array ONLY."
3. **On second failure**: fail-closed. Mark all ACs as `{"status": "fail", "reasoning": "AI output unparseable after retry"}`. Exit 3.

## 6. Error Handling & Boundary Cases

| Scenario | Behavior |
|----------|----------|
| LLM returns non-JSON | Retry once; still fail → all ACs marked `fail` (fail-closed) |
| LLM omits an AC from verdict | Auto-fill with `{"status": "fail", "reasoning": "AI omitted this AC"}` |
| Tool call times out (>30s) | That AC marked `partial` with reasoning "tool inconclusive" |
| API key missing | `ac_verifier.py` raises at init; bash wrapper emits warning + exit 2 |
| `SKIP_AC_VERIFICATION=yes` | Skip AI entirely; exit 2; stderr "AC verification skipped via SKIP_AC_VERIFICATION" |
| No `## 验收标准` section | Treat as "no ACs to verify"; exit 0; stderr "no AC section found" |
| `--dry-run` flag | Run AI but skip audit log write; gate decision not propagated |
| Already-archived change | Verdict still written to audit log; no effect on any flow |
| `STRICT_AC_GATE=yes` + any fail | Exit 1 (blocking); `archive_gate_check` propagates this exit |
| Concurrent archive runs | Append-only log handles concurrent writes (last-write-wins per line is acceptable) |

## 7. Integration with Archive Flow

### `_lib/archive.sh::archive_gate_check` modification

Insert new step before final return:

```bash
# After existing tasks.md completion check, before return 0:
if [ "${SKIP_AC_VERIFICATION:-no}" = "yes" ]; then
  echo "⏭️  AC verification skipped via SKIP_AC_VERIFICATION"
elif [ -f "$tasks_root/openspec/changes/$change_name/proposal.md" ]; then
  local ac_result
  ac_result=$(bash "$AC_VERIFIER_SH" "$change_name" 2>&1)
  local ac_exit=$?
  if [ $ac_exit -eq 1 ]; then
    if [ "${STRICT_AC_GATE:-no}" = "yes" ]; then
      echo "❌ archive_gate_check: AC verification failed under STRICT_AC_GATE"
      echo "$ac_result" | tail -30
      return 1
    else
      echo "⚠️  archive_gate_check: AC verification warning (STRICT_AC_GATE=yes to block)"
      echo "$ac_result" | tail -30
    fi
  elif [ $ac_exit -eq 3 ]; then
    echo "⚠️  AC verification errored; treating as warning (set SKIP_AC_VERIFICATION=yes to suppress)"
  fi
fi
```

### `ship_archive.sh` integration

Already calls `archive_gate_check` at line 150. No additional change needed — the new AC step is encapsulated within `archive_gate_check`. Lightweight mode also benefits since it uses the same archive flow.

### Failure isolation

If AC verification fails with exit 3 (LLM error, not verdict fail), archive flow continues with warning. This prevents LLM infrastructure issues from blocking legitimate archives. Operators can set `SKIP_AC_VERIFICATION=yes` for hotfix situations.

## 8. CLI & Skill Surface

### CLI subcommand

```bash
# Manual invocation (outside archive flow)
rddf ac-verify <change-name> [--dry-run] [--strict]

# Skill invocation (user-facing)
skill_use("ac-verifier", "<change-name>")

# Future: integrate into rddf status / rdd-doctor
rddf doctor --category ac              # show recent AC verification history
```

### SKILL.md frontmatter (user-invocable: true)

```yaml
---
name: ac-verifier
description: Verify OpenSpec change acceptance criteria against committed code via AI semantic check + tools. Used standalone (`rddf ac-verify <name>`) or automatically invoked before archive.
license: MIT
compatibility: requires openspec CLI v1.3.1+, Python 3.11+, ANTHROPIC_API_KEY or OPENAI_API_KEY
metadata:
  author: rdd-workflow
  version: 1.0
  evolved-from: ""
  user-invocable: true
---
```

## 9. Testing Strategy

| Layer | File | Cases |
|-------|------|-------|
| Unit | `tests/unit/test_ac_verifier.py` | parse_acs (5: empty / single / multi / mixed checkbox / missing section); build_prompt (3); apply_gate_rules (5: all pass / 1 fail / STRICT / SKIP / no ACs); parse_verdict (3: valid / missing AC / invalid JSON); audit log append (2) |
| Integration | `tests/integration/test_ac_verifier_skill.bats` | skill registration (3); rddf ac-verify CLI (3: help / pass / fail); archive_gate_check integration (5: pass-through / warning / strict-block / skip / no-proposal) |
| E2E | `tests/integration/test_ac_verifier_e2e.bats` | mock LLM end-to-end (≥4: pass-through / fail-with-warning / fail-strict-block / LLM-error-soft-fail) |
| Visual | Manual: `rddf ac-verify <existing-change>` output readability | N/A — human review |

### Mock LLM strategy

`AC_LLM_MOCK=yes` env var triggers `_ac_verifier_mocks.py` to return canned verdicts keyed by AC hash. Covers 5 mock scenarios:

- `mock_pass_all` — all ACs pass
- `mock_fail_one` — second AC fails with specific evidence
- `mock_partial` — one AC marked partial
- `mock_invalid_json` — first call returns prose, second call returns valid JSON
- `mock_omitted_ac` — verdict array shorter than AC count

## 10. Rollout & Migration

### Phase 1: Standalone (week 1)

- Deploy skill + scripts
- Users opt in via `rddf ac-verify <name>` manually
- No archive integration yet
- Collect feedback on prompt quality and tool effectiveness

### Phase 2: Archive integration (week 2, default warning)

- Add AC step to `archive_gate_check` (warning only)
- Existing archives run with new warning; expect ~10-30% changes to surface warnings (matches audit findings)
- Users fix or set `STRICT_AC_GATE=no` (default) to allow warning archive

### Phase 3: STRICT by default for new changes (week 3, opt-in)

- Add `strict-default: true` flag in proposal frontmatter (optional)
- Changes opting in to strict-mode are blocked on AC fail
- Collect metrics on false-positive rate

### Phase 4: STRICT by default for all changes (week 4+, post-validation)

- Flip `STRICT_AC_GATE` default to `yes` for new changes (with `SKIP_AC_VERIFICATION=yes` escape hatch)
- Deprecate warning-only mode after 30-day overlap window

### Backward compatibility

- Existing `archive_gate_check` behavior preserved when `SKIP_AC_VERIFICATION=yes`
- All existing tests must continue to pass (regression safety)
- New env vars all have safe defaults (`SKIP_AC_VERIFICATION=no`, `STRICT_AC_GATE=no`)

## 11. Open Questions & Risks

| Question | Mitigation |
|----------|-----------|
| LLM API cost at scale (1 verify per archive × 100s of changes/month) | Cache verdict for same commit SHA + proposal hash; reuse for unchanged inputs |
| False positives on legitimate code (e.g., docs-only changes may not "implement" AC in narrow sense) | `--skip` flag + `STRICT_AC_GATE=no` default allow escape; prompt engineering to accept "documentation evidence" |
| LLM latency (~5-15s per archive) acceptable? | Warning mode runs in parallel with archive step; total archive time +5-15s. Acceptable per audit. |
| Vendor lock-in (one LLM provider) | `AC_LLM_PROVIDER` env var + pluggable interface; can swap providers without code changes |
| Schema drift in `.ac-verification.jsonl` | Versioned schema field in first line; migrations add fields with defaults |
| Concurrent archive race in audit log | Append-only JSONL handles this; eventual consistency acceptable |

## 12. Acceptance Criteria

- `skills/ac-verifier/SKILL.md` with user-invocable: true frontmatter
- `ac_verifier.sh` exits 0/1/2/3 per spec; manpage-style help via `--help`
- `ac_verifier.py` exposes parse_acs / build_agent_prompt / invoke_ai_agent / parse_verdict / apply_gate_rules / append_audit_log
- `_lib/archive.sh::archive_gate_check` includes new AC verification step
- `tests/unit/test_ac_verifier.py` ≥18 cases pass
- `tests/integration/test_ac_verifier_skill.bats` ≥11 cases pass
- `tests/integration/test_ac_verifier_e2e.bats` ≥4 mock-LLM cases pass
- Manual verification: `rddf ac-verify <existing-change>` returns readable verdict for the 3 audit-failed changes; verdict correctly identifies missing ACs (add-contract-lint-ci-gate should surface 3 fails)
- No regression: existing archive tests (`test_archive_iteration_sync_resilience.bats` 5 cases + `test_archive_state_recovery.bats` etc.) all continue to pass
- `.rddf/state/.ac-verification.jsonl` populated on each non-dry-run invocation
- `STRICT_AC_GATE=yes` causes archive to exit non-zero when verdict has any fail
- `SKIP_AC_VERIFICATION=yes` bypasses entirely (verifies existing escape-hatch semantics)

## 13. Out of Scope

- Cross-repo AC verification (only single-repo changes for v1)
- Multi-LLM consensus (verifier ensemble) — future iteration
- AC auto-fix suggestions (just verdict + evidence; no patches)
- UI dashboard for AC verification history — covered by `rddf status` evolution
- Enforcement on plan-done (only archive-done, per brainstorming Q2)