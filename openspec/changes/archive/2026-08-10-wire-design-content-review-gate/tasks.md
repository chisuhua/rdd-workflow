# Tasks: wire-design-content-review-gate

## 1. Wiring Investigation

- [x] 1.1 Read `skills/guide-design/scripts/design_content_review.sh` to confirm its entry-point signature and exit-code convention
- [x] 1.2 Read `skills/guide-design/scripts/approve_proposal.sh` to identify the existing approve-side-effect ordering (status write, proposal landing, iteration.json mutation)
- [x] 1.3 Read `skills/guide-design/scripts/design_proposal_review.sh` to identify the batch approve orchestration

## 2. Add review invocation helper (single shared path)

- [x] 2.1 Create a single helper that invokes `design_content_review.sh` with `IMPROVEMENTS_PATH` and `PROJECT_ROOT` from env (Oracle C1-safe)
- [x] 2.2 The helper runs the review, captures its exit status, and emits a structured `{name, severity, reason}` record
- [x] 2.3 Honor `STRICT_DESIGN_GATE=yes` and `SKIP_CONTENT_REVIEW=yes` by reading env vars (no new flags)

## 3. Wire single-item approve to the helper

- [x] 3.1 Insert the helper call at the beginning of the single-item approve path, before any approve-side-effect
- [x] 3.2 Confirm that in default mode, review warnings continue to allow approve to complete
- [x] 3.3 Confirm that `STRICT_DESIGN_GATE=yes` upgrades review blocking to gate failure and blocks approve-side-effect

## 4. Wire batch approve to the helper (per-item, isolated)

- [x] 4.1 Confirm batch approve invokes the helper for each item, not once at the batch level
- [x] 4.2 Confirm that one item's blocking failure does NOT silently bypass review for siblings
- [x] 4.3 Confirm that batch terminate behavior remains consistent with single-item behavior

## 5. Preserve SKIP_CONTENT_REVIEW escape hatch

- [x] 5.1 When `SKIP_CONTENT_REVIEW=yes`, the helper short-circuits and approve proceeds without invoking `design_content_review.sh`
- [x] 5.2 Confirm no other approve-side-effects are bypassed (only the content review)
- [x] 5.3 Confirm the user-visible output distinguishes "review skipped via SKIP_CONTENT_REVIEW" from "review ran and passed"

## 6. Regression Coverage

- [x] 6.1 Add a bats test asserting single-item approve invokes `design_content_review.sh` when `SKIP_CONTENT_REVIEW` is unset
- [x] 6.2 Add a bats test asserting default-mode review warning allows approve to complete
- [x] 6.3 Add a bats test asserting `STRICT_DESIGN_GATE=yes` blocks approve-side-effect on review blocking
- [x] 6.4 Add a bats test asserting `SKIP_CONTENT_REVIEW=yes` skips review without affecting other approve semantics
- [x] 6.5 Add a bats test asserting batch approve invokes review per-item and surfaces each result independently
- [x] 6.6 Run `./test.sh --full --regression` and confirm no new failures vs. `KNOWN_FAILURES.txt`

## 7. Verification

- [x] 7.1 Run `openspec validate wire-design-content-review-gate --type change --json` and confirm no errors
- [x] 7.2 Confirm `proposal-suggestions.md`, all existing proposals, ADR files, and git history outside this change are unmodified