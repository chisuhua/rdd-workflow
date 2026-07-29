# Fix doc-truth-sync — normalize skill name between package.json and disk

**Priority**: P2
**Phase**: default
**Category**: infra-setup
**Type**: feature

## Problem

`doc_truth_sync` test #1 (`package.json::skills[] publishes all 13 disk skills`) fails because `package.json` declares 13 skills in `skills[]` but disk has 16 skills (`skills/*.md` + `skills/*/SKILL.md`). Three skills are missing from `package.json`:

- `add-improve`
- `openspec-gate`
- `rdd-workflow-brainstorm`

The root cause is that `package.json`'s `skills[]` array was not updated when these three skills were added to disk. This causes a CI test failure and means the skills are not published when the package is consumed as an npm dependency.

## Fix

Add the three missing skill names to `package.json`'s `skills[]` array, restoring parity between the declared and actual skill set.

## Out of Scope

- No functional changes to any skill
- No changes to AGENTS.md, README.md, or other documentation (those already reference the 3 skills)
- No changes to the `doc_truth_sync` test itself — the test is correct and should pass after the fix