# Spec: Verifier-Protocol Cross-Stage Template

> **Status**: spec only — **not yet implemented**. First application
> targeted for the next minor release cycle per verifier-v2-hardening
> Phase 7 / oracle Q3 recommendation.

## Why

`rdd-verifier` v2.0 (ADR-0045) established a 5-section pattern that decouples
the LLM verification logic from any external provider:

1. **SKILL.md § Protocol** — the agent-facing instruction block
3. **Staged context** — `.rddf/state/<rdd-phase>-context-<change>.json`
5. **Agent writeback** — agent reads context, executes, writes verdict cache
7. **SHA-bound cache** — `.rddf/state/.ac-verdict-<change>.json` (schema v2)
9. **Fail-closed gate** — missing/stale cache blocks, audited bypass permitted

Other phases (`rdd-arch`, `rdd-planner`, `rdd-builder`) may benefit from
the same pattern for LLM-adjacent automation. This spec freezes the
pattern as a shared template before any cross-stage adoption.

## Template (5 sections)

### Section 1: SKILL.md § Protocol

```yaml
# Frontmatter convention
metadata:
  protocol_inline: true   # marker for cross-stage scan
  protocol_data_layer: "_lib/<phase>/protocol.py"
  protocol_context_file: ".rddf/state/<rdd-phase>-context-<change>.json"
  protocol_cache_file: ".rddf/state/.<phase>-cache-<change>.json"
```

SKILL.md body MUST contain a `## <Phase> Protocol <` section with:
- AC / item extraction rules (regex + edge cases)
- Evidence collection protocol (tool priority chain)
- Output schema (strict, jsonschema-compatible)
- Persistence protocol (write cache + audit log)
- Exit code semantics

### Section 2: Data Layer (`_lib/<phase>/protocol.py`)

Pure functions:
- `parse_*` — extract items from proposal/spec/etc.
- `build_<phase>_context` — produce context dict for staged file
- `stage_<phase>_context` — atomic write (temp + rename)
- `validate_*_items` — strict jsonschema + semantic checks
- `validate_*_completeness` — length/count match guard

### Section 3: Staged Context File

Path: `.rddf/state/<rdd-phase>-context-<change>.json`
Schema:
```json
{
  "schema_version": 1,
  "phase": "<phase>",
  "change": "<change-name>",
  "item_count": N,
  "items": [...],
  "cache_path": "<absolute>",
  "audit_log_path": "<absolute>",
  "expected_output_schema": {...},
  "instruction": "<single-sentence summary>",
  "staged_at": "ISO-8601",
  "staged_by": "rdd-<phase>-vN"
}
```

### Section 4: SHA-Bound Cache (cross-stage consistent schema v2)

```json
{
  "schema_version": 2,
  "version": 2,
  "change": "<change-name>",
  "codebase_commit": "<git SHA>",
  "verdict": [...],
  "ran_at": "ISO-8601",
  "ran_by": "rdd-<phase>",
  "source": "rdd-<phase>",
  "verification_state": "passed|failed|errored|pending",
  "failed_acs": [],
  "implementation_ref": "<ref>"
}
```

Cache reads SHALL fail-closed on `schema_version != 2` (return None).

### Section 5: Fail-Closed Gate

- Cache missing OR stale → gate fails closed (return non-zero exit)
- Cache SHA != HEAD → gate fails closed
- Cache verdict incomplete (length != item_count, unknown IDs, duplicates)
  → gate fails closed
- Cache has failed items + `STRICT_*_GATE=yes` → gate fails closed
- Cache has failed items + non-strict → warning only
- Audited bypass: `<SKIP_...>=yes` + `<...>_BYPASS_REASON=<non-empty>`
  → gate succeeds with `verification.state = bypassed`

## Naming Conventions (cross-stage)

| Concept | Naming | Example |
| |
| staged context | `<rdd-phase>-context-<change>.json` | `rdd-arch-context-design.md.json` |
| verdict cache | `.<phase>-cache-<change>.json` (or `.ac-verdict-<change>.json` for verifier) | `.ac-verdict-foo.json` |
| audit log | `.rddf/state/.ac-verification.jsonl` (verifier) or per-phase equivalent | `.rddf/state/.arch-verification.jsonl` |

## Adoption Decision

**Per-phase**: explicit ADR + proposal before adoption. Avoid copy-paste
without per-phase justification.

**First application candidate**: `rdd-arch` gap analysis (per oracle Q3).
Not implemented in this change; tracked as future.

## Boundaries (Not Covered)

- **Human-dominated steps stay human-in-loop**. Planner's proposal
  content review (per `guide-design` Phase 3) is human-in-the-loop per
  ADR-0028 — only "reasoning-assistant" sub-steps may use this template.
- **No automatic cross-stage migration**: each adoption requires its own
  proposal, ADR, and review session.