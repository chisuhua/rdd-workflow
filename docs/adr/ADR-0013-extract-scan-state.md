# ADR-0013: Extract scan-state logic from skills/guide.md into skills/_lib/scan-state.sh

> **v3.0.0 note**: Originally authored as "spec-workflow". Renamed to "rdd-workflow" in v3.0.0 (2026-07-22). See ADR-0023.


> **状态**: 已采纳
> **日期**: 2026-07-07
> **决策者**: rdd-workflow maintainers
> **替代**: (无)

## Context

`skills/guide.md` (无状态推荐器) carried a 70-line inline bash code block
implementing 11 priority-ordered state-detection branches. The block had
accumulated 4 latent bugs over v1.x → v2.0 evolution (awk `$3` vs `$2`,
missing bracket prefix in awk regex, `grep -q '待创建'` matching description
fields, cwd-relative Python `open`).

Inline code blocks in skill markdown have three problems:

1. They are re-interpreted by every AI agent on every invocation (token cost).
2. The gotchas are not enforced — each agent may re-derive them incorrectly.
3. They cannot be unit-tested in isolation; only static-grep tests exist.

## Decision

Extract the scan logic into a sourced library at `skills/_lib/scan-state.sh`,
mirroring the precedent set by `skills/_lib/worktree.sh` and
`skills/_lib/archive.sh` (extracted in ADR-0011/0012 chain). The library
exports a single `scan_state()` function that sets `$RECOMMEND` and `$REASON`
in the caller's namespace (backward-compatible with the previous inline
variable contract).

Fix the 4 latent bugs as part of the same change:

- Branch format: `$3 ~ /^\[openspec\//` instead of `$3 ~ /^openspec\//`
- No `grep -q "openspec/"` (false-positive on path substrings, P1-4)
- Python parser uses `json.load`, not `grep` (P1-7)
- Python `open()` uses `os.environ["PY_PROJECT_ROOT"]`, not cwd (archive.sh pattern)

## Consequences

Positive:

- `guide.md` context weight drops from ~70 lines of bash to a 6-line
  source-only call, saving ~1.5K tokens per agent invocation.
- 11 priority branches are now testable in isolation (Task 2 of plan
  adds 11 bats tests).
- Bracket bug fixed; future `git worktree list` output changes won't
  silently break the scanner.
- Sets precedent: any other skill carrying > 30 lines of inline bash
  is a candidate for similar extraction (deferred to future ADRs).

Negative:

- New file `skills/_lib/scan-state.sh` must be sourced by callers; if a
  future caller invokes `guide.md` logic without sourcing, `$RECOMMEND`
  will be empty. Mitigated by the explicit `source ... && scan_state`
  template in `guide.md`.
- Pre-existing INSTALL.md distribution gap (only `*.md` files copied)
  means the script may not be installed by `INSTALL.md`. Affects all
  `_lib/*.sh`; out of scope here.

## References

- Plan: .rddf/plans/scan-state-extraction.md
- Precedent: skills/_lib/worktree.sh (ADR-0011), skills/_lib/archive.sh (ADR-0012)
- Bug history: P0-2 (column $3), P1-3 (phase-gate report), P1-4 (bracket),
  P1-7 (json.load)