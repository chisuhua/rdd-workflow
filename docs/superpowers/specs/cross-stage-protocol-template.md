# Spec: Cross-Stage Protocol Template

> **Status**: spec only — **partially implemented**. First Verifier Subset
> application landed in `inline-ac-verifier-into-rdd-verifier` (ADR-0045,
> archived 2026-09-07). First Analyzer Subset application landed in
> `arch-analyzer-protocol` (ADR-0046, in progress).

## Why

`rdd-verifier` v2.0 (ADR-0045) established a 5-section pattern that decouples
the LLM verification logic from any external provider:

1. **SKILL.md § Protocol** — the agent-facing instruction block
3. **Staged context** — `.rddf/state/<rdd-phase>-context-<change>.json`
5. **Agent writeback** — agent reads context, executes, writes verdict cache
7. **SHA-bound cache** — `.rddf/state/.ac-verdict-<change>.json` (schema v2)
9. **Fail-closed gate** — missing/stale cache blocks, audited bypass permitted

Other phases (`rdd-arch`, `rdd-planner`, `rdd-builder`) may benefit from
a **subset** of this pattern for LLM-adjacent automation. This spec
freezes both subsets as a shared template so cross-stage adopters don't
each invent semantics.

Two distinct subsets are documented:

- **Verifier Subset** (5 sections, full) — for LLM-as-judge verifier stages
  where the agent reads staged context and writes a verdict cache.
- **Analyzer Subset** (§1 + §2 + §5-repurposed) — for deterministic
  human-curated analyzers where no agent consumes context and no
  verdict is cached, but a structured-output contract is enforceable.

---

## Verifier Subset (LLM-as-Judge Verifier)

The full 5-section pattern. Use this when the stage has an agent
loop (staged context → LLM call → verdict cache → gate).

### Section 1: SKILL.md § Protocol

```yaml
# Frontmatter convention
metadata:
  protocol_inline: true          # marker for cross-stage scan
  protocol_data_layer: "_lib/<phase>/protocol.py"
  protocol_context_file: ".rddf/state/<rdd-phase>-context-<change>.json"
  protocol_cache_file: ".rddf/state/.<phase>-cache-<change>.json"
```

SKILL.md body MUST contain a `## <Phase> Protocol` section with:

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

---

## Analyzer Subset (Deterministic Human-Curated)

Use this when the stage is **deterministic** (no LLM call) and the
artifact is **human-curated** (no agent consumes staged context, no
LLM verdict to cache). The shared sections are §1 + §2 + §5-repurposed;
§3 (staged context) and §4 (SHA-bound cache) are explicitly SKIP.

**Frontmatter marker** distinguishes Analyzer Subset from Verifier Subset:

```yaml
metadata:
  protocol_inline: true          # required for cross-stage scan
  protocol_data_layer: "_lib/<phase>/protocol.py"
  protocol_output_contract: true # Analyzer Subset marker (NOT cache/context)
```

The `protocol_output_contract: true` marker tells cross-stage scanners
that this stage adopts Analyzer Subset (deterministic, no verdict cache)
rather than Verifier Subset (LLM-as-judge).

### Section 1: SKILL.md § Protocol

Same as Verifier Subset §1, minus the `protocol_context_file` /
`protocol_cache_file` markers (no staged context, no cache). The
SKILL.md body MUST contain a `## <Phase> Protocol` section that:

- Documents the deterministic output contract (e.g. 5-section markdown
  template, structured JSON shape, valid slug format).
- Lists the frontmatter markers actually in use.
- Cross-references the data layer file path.

### Section 2: Data Layer (`_lib/<phase>/protocol.py`)

Pure functions, **subset of Verifier Subset §2**:

- `parse_*` — validate input format (slug, identifier, etc.)
- `build_*_skeleton` — produce deterministic content
- `validate_document(path) -> ValidationReport` — Output Contract check
- `list_*` — enumerate artifacts

Functions `stage_*_context` and `validate_*_completeness` are **NOT
present** in Analyzer Subset (no staged context, no LLM verdict count
to validate against).

### Section 3: Staged Context File — **SKIP**

No agent consumes a staged context file. The generated artifact IS the
context — humans edit it directly. Adding a second source of truth
(staged JSON nobody reads) is form over substance.

### Section 4: SHA-Bound Cache — **SKIP**

No LLM verdict to bind to a SHA. The only meaningful "state" is the
git-tracked artifact itself. The analyzer's data layer reads from the
artifact on disk; no cache is necessary or desirable.

**Durability boundary**: analyzer artifacts are git-tracked, durable,
human-authored. Verifier §3/§4 files are gitignored, transient,
machine-generated. Any attempt to "cache" analyzer state would violate
this boundary.

### Section 5: Output Contract Validation (REPURPOSED from Fail-Closed Gate)

Analyzer Subset adopts §5 as a **two-tier validation** model, **not**
a fail-closed gate. This is the key semantic divergence from Verifier
Subset:

- **Structural validation (HARD, deterministic)** — the generated
  artifact MUST conform to the documented output contract (e.g. all 5
  markdown sections present, slug format valid, required fields
  non-empty). Implementation: `validate_document(path)` returns
  `ValidationReport(structural_ok: bool, ...)`. Failures indicate
  generator drift and SHOULD block further pipeline steps.
- **Completeness validation (ADVISORY, never blocks)** — how much of
  the artifact the human curator has filled in. Implementation:
  `ValidationReport.completeness: Literal["draft","partial","complete"]`.
  Used as an informational signal, never a hard gate. Humans curate
  asynchronously and arch-done-style gates MUST NOT block on
  advisory completeness.

The naming convention is deliberately **"validation"** not **"gate"**
in Analyzer Subset to prevent scope-creep into blocking semantics.

---

## Naming Conventions (cross-stage)

| Concept | Naming | Example |
|---------|--------|---------|
| Verifier staged context | `<rdd-phase>-context-<change>.json` | `rdd-arch-context-design.md.json` |
| Verifier verdict cache | `.<phase>-cache-<change>.json` (or `.ac-verdict-<change>.json` for verifier) | `.ac-verdict-foo.json` |
| Verifier audit log | `.rddf/state/.ac-verification.jsonl` (verifier) or per-phase equivalent | `.rddf/state/.arch-verification.jsonl` |
| Analyzer data layer | `_lib/<phase>/protocol.py` (canonical, per AGENTS.md rule 25) | `_lib/arch/protocol.py` |
| Analyzer artifact | `<artifact-name>.md` or `.json` (git-tracked, durable) | `docs/architecture/auth-gap-analysis.md` |

---

## Adoption Decision

**Per-phase**: explicit ADR + proposal before adoption. Avoid copy-paste
without per-phase justification.

**Adopted applications**:

- **Verifier Subset** — `rdd-verifier` v2.0 (ADR-0045, archived 2026-09-07).
- **Analyzer Subset** — `rdd-arch` gap analysis (ADR-0046, in progress).

**Future candidates** (each requires its own ADR):

- `rdd-planner` proposal-content review (Analyzer Subset; human-curated
  proposal markdown).
- `rdd-builder` plan-step review (Analyzer Subset; structured plan
  template).

## Boundaries (Not Covered)

- **Human-dominated steps stay human-in-loop**. Planner's proposal
  content review (per `guide-design` Phase 3) is human-in-the-loop per
  ADR-0028 — only "reasoning-assistant" sub-steps may use this template.
- **No automatic cross-stage migration**: each adoption requires its own
  proposal, ADR, and review session.
- **No shared state across subsets**: a phase must pick Verifier OR
  Analyzer, not both — the cache-vs-no-cache distinction is load-bearing
  for the durability boundary.