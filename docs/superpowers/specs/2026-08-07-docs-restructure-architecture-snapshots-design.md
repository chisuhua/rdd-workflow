# Documentation Restructure — Architecture Snapshots + ADR Index Refresh

> **Date**: 2026-08-07
> **Status**: Draft
> **Author**: sisyphus
> **Goal**: Re-shape `docs/` so it reflects the live code (v2.0.9+, four-phase arch → design → plan → ship, 25 ADRs) instead of the stale v2.0 design-phase content

## Background

The current `docs/` directory holds 71 files accumulated over multiple refactors (v1.0 → v1.1 → v2.0 → v2.0.5 → v2.0.8 → v2.0.9). Three structural problems have emerged:

1. **`docs/v2-*.md`** (12 files, ~9 000 lines) describe a three-phase architecture (arch → plan → ship) that is **already obsolete**: v2.0.6+ added `guide-design` as a fourth phase (ADR-0025). The summary still references "ADR-0001 to ADR-0012" but the project now has 25 ADRs.
2. **`docs/adr/README.md`** is out of sync with `docs/adr/`: it lists only 24 ADRs (missing ADR-0025), tags implementation status as "v2.0" when actual code is v2.0.9+, and uses three-phase terminology in its dependency graph.
3. **There is no `docs/architecture/` directory.** The user wants a single, topic-split location for the current architecture — distinct from ADRs (decisions) and specs/plans (transient design artefacts).

This is a docs-only change. No `skills/`, `_lib/`, or `openspec/` files are modified.

## Goals

- A reader (maintainer + contributor) can open `docs/architecture/README.md` and navigate to any architecture topic in ≤2 clicks.
- Every architecture topic document explains **why** the design exists (intent + trade-offs) plus **the key structural seams** (modules, contracts, data flow). Implementation details (function signatures, line-by-line) stay in code + docstrings.
- The ADR index reflects all 25 ADRs and the four-phase architecture.
- Stale `docs/v2-*.md` content is **merged into `architecture/`**, not silently dropped — every meaningful piece of information from those files lands somewhere readable.

## Non-Goals (YAGNI)

- Do not rewrite ADR bodies — ADRs are immutable historical decisions.
- Do not create `docs/CONCEPTS.md`, `docs/CONTRIBUTING.md`, `docs/GLOSSARY.md`.
- Do not touch `docs/ONBOARDING.md`, `docs/change-quality-guide.md`, `docs/proposal-*.md`, `docs/loop-engineering-research.md`, `docs/audit/`, `docs/migration/`, `docs/legacy/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`.
- Do not modify any code under `skills/`, `_lib/`, or `openspec/`.
- Do not rename or renumber ADRs.

## Audience

**Project maintainer + contributor.** Medium-to-high technical depth. Assume the reader is comfortable reading Python and bash, knows `git worktree`, and is willing to read module docstrings. Do not over-explain OpenSpec basics.

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Single-target readers**: maintainer + contributor | User-confirmed. Drives language/depth/example choice throughout. |
| D2 | **Rewrite and merge all `v2-*.md` into `docs/architecture/`** | User-confirmed. Stale-but-once-valuable content is preserved in topic-split form rather than dropped. |
| D3 | **Only rewrite `docs/adr/README.md` index, not ADR bodies** | User-confirmed. ADR bodies are immutable historical records; updating them would lose git blame semantics. |
| D4 | **Topic-split `architecture/` into ~10 files** | User-confirmed. Better discoverability and per-topic evolution than one mega-doc. |
| D5 | **Depth = "why" + key structure** | User-confirmed. Avoids docs-vs-code drift; complements (not duplicates) docstrings. |
| D6 | **Scope limited to `architecture/` + ADR index** | User-confirmed. Avoids scope creep into onboarding, change-quality-guide, etc. |
| D7 | **Implementation approach = Plan A (10-file split mirroring v2-* topic map)** | Each file maps 1:1 to a source v2-* document; reviewer can audit "did we lose any v2-* content?" file-by-file. |

## Deliverables

### New files (11)

| Path | Source(s) | Approx LOC | Purpose |
|------|-----------|-----------|---------|
| `docs/architecture/README.md` | — | 80 | Entry point: doc map + reader declaration + update convention |
| `docs/architecture/overview.md` | v2-workflow-overview.md, v2-architecture-refactor-plan.md | 400 | System overview, module map, key design principles |
| `docs/architecture/workflow-phases.md` | v2-workflow-overview.md (phases section) | 500 | Four-phase arch → design → plan → ship + handoffs |
| `docs/architecture/loop-engine.md` | v2-loop-engine-guide.md, v2-loop-engine.md | 600 | 5 building blocks + interaction modes + when-loop-vs-menu |
| `docs/architecture/state-and-events.md` | v2-memory-system-guide.md | 400 | 3-layer state model + handoff contracts |
| `docs/architecture/gates-and-quality.md` | v2-gate-mechanism-guide.md, v2-tribunal-guide.md | 400 | gate / tribunal / arch_quality_gate / change_alignment |
| `docs/architecture/skills-and-handoff.md` | — (new, synthesised from SKILL.md files) | 350 | SKILL.md frontmatter, discovery, handoff schema versions |
| `docs/architecture/multi-session.md` | v2-multi-session-guide.md, ADR-0017 | 350 | rddf-session lifecycle + 4-option conflict resolver |
| `docs/architecture/extension-points.md` | — (new, from pattern audit) | 300 | How to add a skill / detector / action / CLI subcommand / ADR |
| `docs/architecture/historical-evolution.md` | v2-architecture-refactor-plan.md (history portion) | 250 | v1.0 → v2.0 → v2.1 timeline + per-refactor motivation |
| `docs/adr/README.md` (rewrite) | current docs/adr/README.md | 300 | Index updated to ADR-0025 + four-phase + new status |

### Deleted files (12)

- `docs/v2-adr-summary.md`
- `docs/v2-api-reference.md`
- `docs/v2-architecture-refactor-plan.md`
- `docs/v2-config-schema.md`
- `docs/v2-developer-guide.md`
- `docs/v2-gate-mechanism-guide.md`
- `docs/v2-implementation-plan.md`
- `docs/v2-loop-engine-guide.md`
- `docs/v2-loop-engine.md`
- `docs/v2-memory-system-guide.md`
- `docs/v2-multi-session-guide.md`
- `docs/v2-tribunal-guide.md`
- `docs/v2-workflow-overview.md`

(Total 13 v2-* deletions, not 12 — confirm in `ls docs/v2-*.md` during pre-flight.)

### Untouched (preserved)

`docs/ONBOARDING.md`, `docs/change-quality-guide.md`, `docs/proposal-approved-format.md`, `docs/proposal-suggestions-format.md`, `docs/loop-engineering-research.md`, `docs/audit/`, `docs/migration/`, `docs/legacy/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`, all `docs/adr/ADR-*.md`.

## Design — Each `architecture/` File

### `README.md` (entry)

- One-paragraph project description.
- "This doc is for maintainers + contributors" notice.
- Doc map table (file → topic → primary source ADR).
- Links to `../adr/README.md` and `../ONBOARDING.md`.
- Update convention: when a new skill / ADR is added, the corresponding `architecture/*.md` and `adr/README.md` must be updated in the same change.

### `overview.md`

- Value proposition (OpenSpec-compatible + AI workflow + cross-AI-tool portability).
- Top-level Mermaid: 4 phases + Loop engine + `_lib/` + skills + CLI.
- Module map: each skill / `_lib/` sub-module / `rddf` sub-command, 1-2 lines each.
- "Why four phases, not three" — links ADR-0003 → ADR-0025.
- "Why Loop engine" — links v1 menu-driven → v2 loop-driven rationale.
- 7 key design principles (Self-contained / Explicit contract / Idempotent / Single source of truth / No silent failure / TDD discipline / Skill frontmatter immutability).

### `workflow-phases.md`

- Mermaid: arch → design → plan → ship flow.
- One subsection per phase: responsibility, entry skill, key artefacts (`proposal.md`, `tasks.md`, `spec.md`), handoff contract (arch-handoff / plan-handoff / design-handoff).
- **Why design was split out from arch** (ADR-0025): review load, change-quality gate, two-tier content review.
- ADR references: 0003, 0024, 0025.

### `loop-engine.md`

- Goal → Plan → Execute → Verify → Adapt five building blocks (ADR-0004).
- Mapping: building block → module (`loop_state` / `agents` / `actions` / `detectors` / `tribunal` / `gate`).
- Flow diagram: loop / menu / hybrid mode selection (ADR-0002).
- Decision tree: when to use loop mode vs menu mode.
- Cross-references `state-and-events.md`, `gates-and-quality.md`.

### `state-and-events.md`

- 3-layer state model:
  1. State vector (`_lib/state_vector.py`) — instant read/write, schema-versioned.
  2. Event log (`_lib/event_log.py`) — append-only, replayable.
  3. Handoff files (`.rddf/state/.arch-handoff.json`, `.plan-handoff.json`, `.design-handoff.json`) — cross-skill contracts.
- Why 3 layers: vector = query, log = history, handoff = contract.
- ADR refs: 0006, 0016.

### `gates-and-quality.md`

- `gate.py` (ADR-0007): error/warning levels + plugin extension.
- `tribunal.py` (ADR-0008): multi-agent cross-validation + sanitization.
- `arch_quality_gate.py` (ADR-0018): 4 warning-level checks (alignment / debt / clarity / actionable).
- `change_alignment.py` (ADR-0019): 3 warning-level checks (refs_valid / no_contradiction / task_traceability).
- Invariant: warning = soft prompt, error = hard block.
- ADR refs: 0007, 0008, 0018, 0019.

### `skills-and-handoff.md`

- SKILL.md frontmatter spec (`name` / `description` / `license` / `compatibility` + `metadata.{author, version, evolved-from, user-invocable}`).
- Skill discovery paths: CLI / Skill tool / embedded call.
- Three invocation modes: `skill_use` / `rddf` / direct `.md` read.
- Handoff contract schema + version policy (ADR-0016).
- Refs: ADR-0016.

### `multi-session.md`

- `rddf-session` user-perspective lifecycle (ADR-0017).
- Project-level `sessions.json` persistence + 4-option conflict soft-prompt.
- v2.0 lightweight vs v2.1 full boundary (ADR-0010).
- Decision tree: when to start a new session vs resume.
- Refs: ADR-0010, ADR-0017.

### `extension-points.md`

- Adding a skill: frontmatter + per-skill `scripts/` + install hook (ADR-0021).
- Adding a detector / action (plugin loader).
- Adding a `rddf` CLI subcommand.
- Adding an ADR (naming + template + README sync).
- Refs: ADR-0021.

### `historical-evolution.md`

- Timeline: v1.0 (spec/ship, ADR-0001) → v2.0 (arch/plan/ship, ADR-0003) → v2.1 (arch/design/plan/ship, ADR-0025).
- v2.0.5+ per-skill scripts/ migration (ADR-0021).
- v2.0.6+ guide-design introduction (ADR-0025).
- v2.0.8+ global install support.
- v2.0.9+ deps-driven execution mode (ADR-0024).
- Each entry: pain point → solution mapping.

## ADR Index Rewrite (`docs/adr/README.md`)

Sections to refresh:

1. **Top status table** — extend to ADR-0025; change "v2.0 同步" → "v2.0.9+ 同步".
2. **ADR list** — add row for ADR-0025; update status column from stale "v2.0 / v3.0 候选" to current reality (e.g. ADR-0011/0012 marked "已采纳，未实施" or "v3.0 候选" depending on actual code state — verify during implementation).
3. **Architecture evolution diagram** — replace three-phase view with four-phase view.
4. **Decision dependency graph** — add edges for ADR-0016, 0021, 0024, 0025.
5. **Topic classification** — add new category "契约与协议" containing ADR-0016, 0017, 0022, 0024, 0025.

**Important**: The status field for each ADR is the **index author's** characterisation. Verify against `git log --oneline | grep -i <ADR-keyword>` for each one before writing; if uncertain, mark as "已采纳，状态待核实".

## Implementation Order

Five batches, each one independent commit for easy rollback:

1. **Batch 1 — Entry + Overview + Evolution**: `README.md`, `overview.md`, `historical-evolution.md`. Reader can land here and get a coherent system picture.
2. **Batch 2 — Core concepts**: `loop-engine.md`, `state-and-events.md`, `gates-and-quality.md`. Three docs cross-reference each other but each is independently readable.
3. **Batch 3 — Flow + protocol**: `workflow-phases.md`, `skills-and-handoff.md`, `multi-session.md`. Depend on Batch 2 concepts.
4. **Batch 4 — Extension + ADR index**: `extension-points.md`, `docs/adr/README.md` rewrite.
5. **Batch 5 — Cleanup**: delete 13 `docs/v2-*.md` files; run verification suite; commit.

After each batch: `./test.sh --quick` for sanity (docs shouldn't break tests, but proves the change is contained).

## Verification Strategy (5 checks)

| # | Check | Command |
|---|-------|---------|
| V1 | All relative `.md` links in new docs resolve | `grep -oE '\]\([^)]+\.md\)' docs/architecture/ -r \| xargs -I{} test -f {}` |
| V2 | No stale "三阶段" terminology | `grep -r '三阶段' docs/architecture/ docs/adr/README.md` must be empty |
| V3 | No stale "v2.0.0-beta" outside `historical-evolution.md` | `grep -r 'v2.0.0-beta' docs/architecture/ docs/adr/README.md` must be empty |
| V4 | ADR index lists 25 ADRs | `grep -c '^\| ADR-' docs/adr/README.md` == 25 (24 from old + ADR-0025) — verify exact count post-edit |
| V5 | Quick test suite still passes | `./test.sh --quick` returns 0 |

V1-V4 are mechanical and run inline after the change. V5 is sanity-only (docs change shouldn't affect tests).

## Risks & Mitigations

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R1 | External links to `v2-*.md` break | M | Pre-flight `grep -r 'v2-[a-z]' skills/ openspec/ _lib/ 2>/dev/null` — if any match, redirect in a 1-line edit before deletion. Expected: zero matches (those dirs use ADR refs, not doc refs). |
| R2 | New docs drift from live code | H | Implementation **must** cross-check claims against `_lib/*.py` docstrings + `skills/*/SKILL.md` frontmatter, not git history inference. |
| R3 | ADR index contradicts ADR body | M | Index only states "已采纳 / 已替代" etc. — does not paraphrase decisions. Where current code reality is unclear, mark "状态待核实" and resolve in follow-up. |
| R4 | Accidentally editing `skills/` or `_lib/` | L | Hard constraint: only files under `docs/architecture/` and `docs/adr/README.md` are writable in this change. Pre-commit check via `git status`. |
| R5 | Lost git annotation / blame history on `v2-*.md` | L | They are docs, not code. Blame loss is acceptable for documents that no longer reflect current state. |
| R6 | User discovers missing v2-* content after deletion | L | Per-file mapping table above lets reviewer audit. Add final check: "for each deleted v2-*.md, confirm each H2/H3 section's topic is present somewhere in `architecture/`". |

## Out-of-Scope Follow-ups (proposed, NOT in this change)

- Rewrite `docs/ONBOARDING.md` to point at `architecture/` instead of `v2-*`.
- Add a `docs/CONCEPTS.md` glossary once vocabulary stabilises.
- Convert `docs/superpowers/specs/` design specs into a structured index.
- Add CI step that fails if any new `skills/*/SKILL.md` lacks a corresponding entry in `docs/architecture/skills-and-handoff.md`.

These are intentionally deferred. They depend on this restructure landing first.

## Open Questions

None at design time. All material decisions captured above.