## Why

Oracle review concluded that proposal content quality is inconsistent across changes — scope clarity, ADR citation relevance, acceptance criteria testability, and scope boundary definitions are all subjective judgments that currently have no automated check. Adding a lightweight Oracle-based content review in the propose phase catches these issues early without introducing the heavy Tribunal machinery (per ADR-0015).

## What Changes

- New `propose_content_review.py` module: single Oracle invocation that checks 4 content quality dimensions on the newly created proposal
- Oracle prompt checks 4 items: scope clarity, ADR reference relevance, acceptance criteria testability, scope boundary reasonableness
- Output written to `.rddf/state/propose-review.json` as structured JSON (warning level, non-blocking)
- `propose.md` Phase 4 gains optional call to content review (skipped when `SKIP_CONTENT_REVIEW=yes`)
- Corresponding unit tests for the new module

## Capabilities

### New Capabilities
- `propose-content-review`: Oracle-based content review for proposal quality — 4-dimension check with structured JSON output and env-var skip support

### Modified Capabilities
<!-- No existing specs are changing — this is a new capability only. -->

## Impact

- `skills/propose/scripts/propose_content_review.py` — new module, single Oracle call
- `.rddf/state/propose-review.json` — new state artifact
- `propose.md` Phase 4 — optional integration point at end of create flow
- No changes to existing tests; all existing tests must pass
- No impact on Tribunal, plan phase, or archive phase (explicitly out of scope per ADR-0015 constraint)