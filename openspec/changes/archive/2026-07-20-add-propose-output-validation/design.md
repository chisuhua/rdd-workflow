# Design: add-propose-output-validation

> Plan B from the improve-change-quality initiative. Adds post-propose
> quality validation that runs against `proposal.md` / `tasks.md` /
> `roadmap.md` and reports deficiencies as warnings (or errors when
> `STRICT_PROPOSE_GATE=yes`).

## Why

Plan B (propose-output-validation) complements Plan D (input-sources)
by ensuring that **already-created** changes meet a minimum quality
bar before they move into the plan / ship phases. Today, propose.md
Phase 4 writes skeleton artifacts and immediately finalizes them
without any structural validation. The result is that downstream
phases receive changes that may be missing an ADR reference, lack
scope sections, have a one-line proposal, or drift from the roadmap.
This module closes that gap with five focused checks.

## Architecture

`propose_quality_check.py` is a **standalone Python module** with a
`__main__` CLI entry point. It is *not* an inline bash block in
`propose.md`; this keeps the propose skill file lean and lets the
checker evolve independently. The propose skill (or any caller) can
invoke the checker as:

```bash
python3 -m skills.propose.scripts.propose_quality_check --change <name>
python3 -m skills.propose.scripts.propose_quality_check --change <name> --strict
```

### File location

```
skills/propose/scripts/
  __init__.py                  # existing
  propose_change.py            # existing (Phase 4 helpers)
  propose_quality_check.py     # NEW - this change
```

### Module shape

```python
# 5 check functions, each returns list[str] of warnings (empty = pass)
def check_proposal_length(proposal_path: str) -> list[str]
def check_adr_references(proposal_path: str) -> list[str]
def check_scope_sections(proposal_path: str) -> list[str]
def check_roadmap_alignment(name: str, project_root: str) -> list[str]
def check_tasks_completeness(tasks_path: str) -> list[str]

# Aggregator
def run_all_checks(name: str, project_root: str) -> list[str]

# CLI
def main()  # argparse: --change <name> --strict
```

The check functions are pure (no side effects, no I/O beyond reading
the file being validated) which makes them easy to unit-test with
`tmp_path` fixtures.

## The Five Checks

### 1. `check_proposal_length(proposal_path)` - min 500 chars

Proposal.md must have meaningful content. The skeleton template
written by `create_skeleton_change` (propose_change.py lines 82-87)
is ~130 chars; a properly filled-out proposal should be at least 500.

**Threshold rationale**: 500 chars aligns with Plan D's
input-sources length check and catches the most egregious
"forgot to fill it in" cases without rejecting concise-but-valid
proposals.

**Skeleton boilerplate stripping**: the check strips `<skeleton
motivation` and `<file path` markers so that an unfilled skeleton
is detected as short even if the raw byte count exceeds 500. (The
skeleton markers are the literal strings written by
`create_skeleton_change`.)

**Missing file**: returns a single warning `proposal.md not found
at <path>`.

### 2. `check_adr_references(proposal_path)` - must reference >=1 ADR

Proposals must cite at least one Architecture Decision Record. This
enforces ADR-0019 (change-arch-alignment) at propose time rather
than letting the gap surface during review.

**Detection**: regex `ADR-\d{4}` (4-digit zero-padded, matching the
ADR naming convention from ADR-0000 template). One match is enough.

**Missing file**: returns no warnings (the missing-file warning is
already emitted by check #1; we avoid double-reporting).

### 3. `check_scope_sections(proposal_path)` - In Scope / Out of Scope

Proposal.md must contain explicit scope sections. Ambiguous scope is
one of the top review-time surprises; making it a propose-time check
forces the author to draw the line early.

**Detection**: case-sensitive substring search for `In Scope` and
`Out of Scope` (or `Out Scope` as a common shorthand). We use
substring rather than header-regex because proposals may use either
`## In Scope` or `**In Scope:**` styling.

**Missing file**: returns no warnings (defer to check #1).

### 4. `check_roadmap_alignment(name, project_root)` - must be in roadmap.md

Every change name should appear in `roadmap.md`. This is a soft
alignment check: changes not in the roadmap may still be valid
(exploratory, hotfix) but should be flagged for review.

**Detection**: substring search for the change name in
`roadmap.md`. Substring (not word-boundary) is intentional - change
names commonly appear as `### change-name` or in tables.

**Missing roadmap.md**: returns a single warning `roadmap.md not
found, cannot verify alignment`. This is non-fatal because some
projects operate in compat mode without a roadmap.

### 5. `check_tasks_completeness(tasks_path)` - >=2 tasks

Tasks.md must contain at least 2 unchecked task items. A single-task
change almost always means the author hasn't decomposed the work
properly; 2 is the minimum useful granularity.

**Detection**: regex `^\s*-\s*\[ \]` (multiline) - matches standard
markdown task list syntax `- [ ]` with leading whitespace
tolerance. Checked items `- [x]` are not counted (they represent
already-done work, not future work).

**Missing file**: returns a single warning `tasks.md not found at
<path>`.

## STRICT_PROPOSE_GATE

| Mode | Env var | Behavior |
|------|---------|----------|
| Default | (unset) | Warnings printed, exit 0 |
| Strict | `STRICT_PROPOSE_GATE=yes` | Warnings printed, exit 1 |
| Strict (CLI) | `--strict` flag | Same as env var (CLI overrides) |

The strict flag is opt-in so that existing propose flows don't
suddenly start failing. Teams that want to enforce the gate in CI
can set `STRICT_PROPOSE_GATE=yes` globally.

The CLI flag `--strict` takes precedence over the env var: if both
are set, `--strict` wins. If neither is set, the env var default
(unset) means warnings-only.

## Threshold: 500 chars

Aligned with Plan D (input-sources) for consistency across the
two quality initiatives. Both plans now share the same minimum
content length, simplifying the mental model for authors.

## What This Change Does NOT Do

- Does **not** modify `propose.md` (the skill file). The checker is
  a standalone module; integration into the propose workflow is a
  follow-up decision (the propose skill can call the checker via
  subprocess, but that wiring is intentionally out of scope here).
- Does **not** modify the iteration.json schema (already at v4 from
  the earlier manual_deps work).
- Does **not** add bash wrapper scripts (`propose_quality_check.sh`).
  Python `__main__` entry is sufficient; a bash wrapper can be added
  later if the propose skill needs source-able helpers.
- Does **not** enforce the gate by default. STRICT_PROPOSE_GATE=yes
  is opt-in.

## Testing

Unit tests in `tests/unit/test_propose_quality_check.py` cover all
5 check functions with:

- **Pass case**: each check has a fixture that should produce zero
  warnings.
- **Fail case**: each check has a fixture that should produce the
  expected warning string.
- **Edge cases**: missing file, empty file, skeleton boilerplate
  stripping, strict-mode exit code.

Tests follow the pattern from `tests/unit/test_deps_output.py`:
- `tmp_path` fixture for isolated filesystem
- Direct function imports (`from skills.propose.scripts import
  propose_quality_check as pqc`)
- No mocking of filesystem (real writes to tmp_path)
- No `assert True or ...` tautologies (CI恒真断言门控)

## Open Questions (deferred)

1. **Should the propose skill auto-invoke the checker?** - Yes, but
   the wiring belongs in a separate change to keep this one focused
   on the checker module itself.
2. **Should strict mode also fail CI?** - CI integration is a
   separate concern; this change only provides the CLI exit code.
3. **Should the threshold be configurable per-project?** - Not yet;
   500 chars is the documented Plan B/D alignment. A
   `.rddf/config.yaml` override can be added if projects complain.
