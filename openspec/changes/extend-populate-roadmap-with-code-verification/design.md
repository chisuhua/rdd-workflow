## Context

`populate-roadmap-from-arch` v1.0 reads ADR README "已实施（v2.0.X+）" status sections to derive `implementation_version` and renders fragment body markers like `*（已实施 v2.0.0+）*`. This is a **self-reported** signal — the ADR author claims v2.0.0+ implementation, but no cross-check against the actual codebase verifies the claim.

Evidence from the v1.0 first execution (20260820T155324Z) shows 17 + 16 + 3 = 36 ADRs all claim "已实施" but their cited symbols (e.g., ADR-0004's 5 大构建块, ADR-0016 v2 schema support) have not been validated against code. Risks:

1. **误报已实施** — ADR self-reports but code was reverted or never merged
2. **遗漏增量** — implementation exists but ADR README not updated (small changes)
3. **架构漂移** — multi-maintainer drift between ADR intent and actual code

This change adds an **opt-in** Step 1.5 to `populate-roadmap-from-arch` that verifies each ADR's claim against the codebase via codebase-memory-mcp (preferred) or grep fallback, persisting results to a gitignored supplementary view file and rendering 4 verification-aware fragment body badges.

## Goals / Non-Goals

**Goals:**

- Add opt-in `--code-verify=off|on|strict` flag (default `off`, v1.0-compatible)
- Parse ADR "## 决策" / "Decision" section for code symbols (function/class/module names)
- Verify each ADR via codebase-memory-mcp (`search_graph` / `get_code_snippet`) → grep fallback
- Persist results to `.rddf/state/.populate-supplementary.json` (gitignored view, follows `populate_supplementary_schema.json` v1)
- Render 4 verification-aware badges in fragment body `## 已实施能力` section
- Exit code 2 in `strict` mode on discrepancy
- Preserve all v1.0 public APIs, CLI flags, and test outputs unchanged

**Non-Goals:**

- Modifying existing 6-section fragment structure (only badge marker changes in `## 已实施能力`)
- LLM semantic verification (semantic layer handled by `ac-verifier` skill)
- Cross-repo code verification (per ADR-0030, cross-repo handled by Hub)
- Historical fragment backfill (existing fragments not rewritten until next `populate` call)
- CI workflow integration (follow-up proposal; SKILL.md recommends but doesn't ship yml)
- Modifying `rdd-doctor` roadmap-refs category (rdd-doctor remains read-only single-source)

## Decisions

### 1. Additive extension over rewrite

**Decision**: Add `AdrCodeVerification` dataclass + 3 new functions to `populate_lib.py` (Step 1.5), rather than refactoring existing `_extract_adr_status_and_decision` / `generate_phase_body` / `_format_adr_block`.

**Rationale**:

- v1.0 has 12 pytest + 10 bats locking the contract, including consumers post-commit `2b0991a`
- Rewriting core functions carries high regression risk
- Additive approach keeps `--code-verify=off` (default) byte-identical to v1.0 output
- Future deprecation can be cleanly scoped to the Step 1.5 surface

**Alternatives considered:**

- Rewrite `populate_lib.py` v2.0: rejected — high regression risk, no functional gain for default path
- Move verification to separate skill (e.g., `verify-adr-by-code`): rejected — adds CLI friction; user wants `populate --code-verify` integrated UX

### 2. codebase-memory-mcp first, grep fallback

**Decision**: Try `codebase-memory-mcp` `search_graph` first (sub-millisecond, indexed call graph with structural context); fall back to `grep -rn "<symbol>" --include='*.py' --include='*.sh'` only on mcp unavailability.

**Rationale**:

- mcp gives structural context (function calls, imports, dead code) that pure text grep misses
- mcp indices the same workspace opencode sessions use — single source of truth
- grep fallback ensures verification works in CI / non-opencode environments
- Failure is graceful: warning logged, verification continues with degraded accuracy

**Alternatives considered:**

- `ast-grep` (AST-aware): rejected — adds heavy Python dep, overkill for symbol-presence check
- `tree-sitter`: rejected — same reason; codebase-memory-mcp already provides better context
- Grep only (no mcp): rejected — wastes the existing mcp investment, slower on hot path

### 3. 4-state verification_status enum

**Decision**: Encode verification result as one of 4 states:

| State | Self-claim | Code found | has_discrepancy |
|-------|------------|-----------|-----------------|
| `confirmed` | 已实施 | ≥80% of symbols | False |
| `self-claim-only` | 已实施 | <80% of symbols | **True** |
| `placeholder-as-claimed` | 占位 | 0 symbols | False |
| `placeholder-but-exists` | 占位 | ≥1 symbol | **True** |

**Rationale**:

- `confirmed` / `self-claim-only` distinguishes "ADR credible" vs "ADR overclaim"
- `placeholder-as-claimed` / `placeholder-but-exists` distinguishes "ADR honest" vs "ADR underclaim"
- `has_discrepancy` boolean is the single signal that drives strict-mode exit-2
- 80% threshold for `confirmed` accounts for: ADR text might mention deprecated symbols, mcp indexing lags recent changes (~1s)

**Alternatives considered:**

- Binary "verified / unverified": rejected — loses the underclaim signal
- Numeric score 0-1: rejected — overkill for downstream rendering; boolean per state is cleaner
- 100% strict match: rejected — false positive on benign symbol renames; 80% is empirically more stable

### 4. supplementary.json as gitignored view

**Decision**: Write `.rddf/state/.populate-supplementary.json` (already covered by `.rddf/state/` gitignore rule from ADR-0016), schema `populate_supplementary_schema.json` v1.

**Rationale**:

- Matches existing view-file pattern (`iteration.json`, `deps-analysis.json`)
- Multi-hook writable (Step 1.5 writes; Step 2 fragment rendering reads)
- Schema versioning (v1) follows `_lib/schemas/` constraint — bump version on field changes
- Gitignored so per-run timestamps don't dirty the working tree

**Alternatives considered:**

- Commit to repo under `openspec/specs/`: rejected — view file is regenerate-on-demand, not a source of truth
- Inline in fragment frontmatter: rejected — frontmatter should be stable across regenerations

### 5. Strict mode exit codes

**Decision**: Use exit codes aligned with `rdd-doctor`:

| Code | Meaning |
|------|---------|
| 0 | Success (off mode, or on mode with no discrepancy) |
| 1 | Preflight failure (mcp config broken, schema invalid) |
| 2 | Discrepancy detected in strict mode |

**Rationale**:

- Familiar to operators (matches `rdd-doctor` 0/1/2/3 convention)
- Distinguishes "user error" (1) from "data contradiction" (2) — different remediation

**Alternatives considered:**

- Single exit 1 for everything: rejected — loses signal granularity
- Exit 3 for strict mode: rejected — 3 is reserved for `rdd-doctor` warnings/info

### 6. Symbol parsing rules

**Decision**: Parse ADR text for symbols matching these patterns:

- `` `function_name()` `` — backtick-wrapped function call
- `` `ClassName` `` — backtick-wrapped PascalCase class
- `` `module_name.py` `` — backtick-wrapped module filename
- `def function_name` — explicit def declaration
- `class ClassName` — explicit class declaration
- `` `--flag-name` `` — backtick-wrapped CLI flag (matched against `populate.sh` source)

Filter out: code blocks (```...```), inline English prose, generic identifiers (`foo`, `bar`).

**Rationale**:

- ADR authors conventionally backtick code identifiers
- Filtering code blocks avoids matching documentation strings
- Explicit `def`/`class` covers the case where author wrote naturally

**Alternatives considered:**

- Full AST parse of ADR markdown: rejected — ADRs are prose, not code; regex is sufficient
- LLM-based symbol extraction: rejected — adds latency, depends on API key

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **mcp unavailable in CI** | grep fallback (works without any MCP server); log warning, continue |
| **mcp index lag (~1s)** | 80% threshold for `confirmed`; tolerate ≤20% miss |
| **Grep false positive (同名 symbol)** | Only match symbols explicitly mentioned in ADR text; bounded by ADR's own `## 决策` section |
| **Schema version drift** | `populate_supplementary_schema.json` v1; bump version on any field change; consumers reject version=0 |
| **Performance on large codebase** | Per-ADR < 1s mcp / < 5s grep; 33 ADRs < 30s mcp / < 3min grep fallback |
| **Breaking existing fragment consumers** | `--code-verify=off` default produces byte-identical output to v1.0; only adds badge markers in `on`/`strict` mode |
| **Strict mode false positives block CI** | SKILL.md "Recommended CI Integration" section will note: use `--code-verify=on` first to triage, then `--code-verify=strict` |
| **Backwards compat with consumers of `_format_adr_block`** | New function signature has `verification: Optional[AdrCodeVerification] = None`; default arg keeps existing callers working |

## Open Questions

None — all design decisions resolved during proposal approval (2026-08-21).