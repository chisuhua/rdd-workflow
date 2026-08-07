## Context

The rdd-workflow v2.1 working directory contains 5 categories of structured files that influence downstream behavior but have no unified validation floor:

1. `.rddf/state/*.json` (state_vector, sessions, iteration, deps-analysis) — gitignored, no validation
2. `.rddf/plans/*.md` (TDD 5-step contracts) — git-tracked, no schema check before `execute` reads
3. `openspec/changes/*/roadmap-meta.yaml` (manual_deps/manual_blocks per ADR-0022) — deps stage silently skips drift
4. `proposal-suggestions.md` / `proposal-approved.md` (Markdown table indices) — readers parse ad-hoc
5. `openspec/changes/*/tasks.md` (checkbox progress) — `execute` writes back without external audit

Existing infrastructure (`rdd-env-check`, ADR-0018 arch-quality gate, ADR-0019 change-arch-alignment) covers either environment (CLI/git/build) or single-phase gating (arch/change). None of these is a phase-independent, read-only, manual diagnostic.

The proposal `add-rdd-doctor-skill` introduces the missing layer.

## Goals / Non-Goals

**Goals:**

- Single bash entry point (`scripts/doctor.sh`) that fans out to 5 Python checkers
- Single Python aggregator (`scripts/doctor_render.py`) that produces the graded report and `--json` payload
- Path-resolver helper that always returns the real `_lib/` location, never the `skills/_lib/` shim
- Output contract matching `openspec validate` exit codes (0/1/2/3)
- Idempotent, read-only, and registered in `tests/smoke.bats`
- Documentation update to `AGENTS.md` and `tests/README.md`

**Non-Goals:**

- Auto-fix (deliberate YAGNI; v2 follow-up)
- Hard-block integration with phase gates (orthogonal to gate system)
- Cross-repo / global state scanning (`~/.rddf/`)
- Replacement or rewrite of `rdd-env-check`, ADR-0018, ADR-0019
- Modifying existing JSON schemas in `_lib/schemas/`
- Hooking into phase entry points (v1 is manual-only)

## Decisions

**Decision 1: Single Python process, not 5 subprocesses**

- Why: AC9 performance budget (< 3s for all 5 categories) cannot be hit if each checker pays Python startup cost. Importing all checkers into one `doctor_render.py` aggregator keeps the worst case under 1.5s and simplifies the severity aggregation.
- Alternatives considered: (a) per-checker subprocess — easier isolation but doubles wall time; (b) compiled checker binary — premature optimization, adds build complexity. Rejected.

**Decision 2: Path resolver helper resolves `_lib/` directly, not via shim**

- Why: Commit `c3a90fe` reduced `skills/_lib/` to a 6-line shim that sources `${HOME}/.agents/skills/_lib/`. Any checker that loads JSON schema via the shim risks silently inheriting stale global state. A direct resolver (`PROJECT_ROOT/_lib/schemas/`) is the only correct lookup.
- Alternatives considered: rely on `skills/_lib/state.sh` and trace the source. Rejected: that's how Bug A/B happened in design phase.

**Decision 3: Cat-5 is descoped — file existence + checkbox count, no openspec status cross-check**

- Why: `openspec status --change X --json` requires the `.openspec.yaml` to contain a `schema` field, which `approve_proposal.sh` currently does NOT write. Furthermore, `isComplete` is derived from artifact existence, NOT checkbox progress, making the cross-check vacuous even when CLI works. v1 ships without cross-check; v2 may revisit.
- Alternatives considered: detect CLI availability and degrade gracefully (option retained as SHOULD, see Decision 4).

**Decision 4: Degraded cat-5 emits INFO, never silent skip**

- Why: silent skips are how the existing design-phase bugs hid. When `openspec` is unreachable, cat-5 MUST emit an INFO finding (`openspec status unavailable, skipping cross-check`) so the operator sees the degraded path in the report.
- Alternatives considered: silent skip — rejected (loss of observability, exactly the failure mode doctor is meant to expose).

**Decision 5: Reuse `_lib/parse_approved.py` for proposal-table-check (cat-4)**

- Why: Oracle review flagged that writing a third parser invites the very drift it claims to detect. The existing `_lib/parse_approved.py` already parses proposal-approved rows; extending it (vs. forking) keeps a single source of truth.
- Alternatives considered: write a new lightweight parser — rejected (drift risk).

**Decision 6: One bash entry + one Python aggregator + N checker modules**

- Why: matches the project's established round-A/round-B extraction pattern; keeps `SKILL.md` short; allows future per-checker upgrades without touching dispatch.
- Alternatives considered: monolithic `doctor.py` — rejected (mixing concerns); full bash — rejected (no JSON serialization).

## Risks / Trade-offs

- [Cat-2 false positives on legitimate plan variation] → Mitigation: loose matching (presence of 5 step markers only), WARNING-only severity, no CRITICAL on missing-step alone. Run cat-2 against real corpus during execute phase and tune.
- [JSON string assertion brittleness in bats] → Mitigation: use `jq` for all JSON assertions, never bats string matching. Codify in test template.
- [Schema migration gap if `_lib/schemas/` ships a breaking change without version bump] → Mitigation: doctor surfaces "schema version mismatch" as a separate finding (separate from per-field validation). Defer to follow-up improvement.
- [Manual triggers only — discoverability] → Mitigation: prominent `AGENTS.md` section listing "when to run doctor" with 3 example scenarios.
- [5× checker Python startup during dev iteration] → Mitigation: single-process design (Decision 1).

## Migration Plan

- Add files; no existing files are renamed or moved
- Register in `tests/smoke.bats` with a smoke test
- Update `AGENTS.md` and `tests/README.md` (additive; one section + one line)
- No data migration required; no env-var migration; no skill-name deprecation
- Rollback: delete `skills/rdd-doctor/` + the smoke entry + the AGENTS/tests/README additions — reversible in a single commit

## Open Questions

- Should cat-2 (plan TDD structure) also verify that each step has at least one `bash` or `python` invocation, or is the loose "5 markers present" check sufficient? (Defer to execute phase tuning; default = loose.)
- Should the `--json` output include a top-level `next_step` field (e.g. `"rerun_guide_plan"`, `"manual_review"`, `"no_action"`)? Listed as SHOULD in improvements file; default = YES for forward compatibility with future hooks.
- Should doctor ship with a pre-baked fixture repo (`tests/fixtures/diseased-repo/`) to make regression trivial? Recommended YES for AC3 root-cause tests; default = YES.