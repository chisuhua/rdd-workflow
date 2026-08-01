## Context

`skills/_lib/state.sh` is a cross-cutting bash helper that defines `safe_python_json`, `count_pending_suggestions`, `check_dirty_key_files`, and other functions used by `guide`/`guide-arch`/`propose`/`roadmap`/`status`. In the rdd-workflow repository itself the file lives at `skills/_lib/state.sh`, but a downstream consumer project that installs rdd-workflow globally via `install.sh --global` does not have that local copy; the canonical helper is at `${HOME}/.agents/skills/_lib/state.sh`.

`skills/guide/scripts/scan-state.sh` and `skills/guide/scripts/guide_entry.sh` both source `state.sh` with a hard-coded `$PROJECT_ROOT/skills/_lib/state.sh` path. When the local file is missing, the source fails silently (stderr is not visible to the AI caller in the HydraForge case), and the scanner aborts before producing a recommendation menu.

Separately, `skills.rddf_session.scripts.rddf_session_pkg._types.py` defines `_TERMINAL_STATES = frozenset(("completed", "failed", "abandoned"))`. The `check_heartbeat_timeouts` command marks stale active sessions as `orphaned`, but `archive_history` filters on `_TERMINAL_STATES`, so orphaned sessions are never archived. This is the root cause of the HydraForge residual session issue.

## Goals / Non-Goals

**Goals:**
- Make `scan-state.sh` and `guide_entry.sh` load `state.sh` from the local copy first, then fall back to the global copy, then emit a clear stderr warning if both are missing.
- Keep the warning non-blocking: exit code 0, no error text in stdout, and the same menu output as today when a helper is found.
- Add `"orphaned"` to `_TERMINAL_STATES` so `archive_history` treats heartbeat-timeout sessions as terminal.
- Preserve the existing three terminal states and do not change any other schema fields.
- Add focused bats tests for the scanner fallback matrix and the terminal-state contract.
- Document the fallback contract in `AGENTS.md` and `CHANGELOG.md`.

**Non-Goals:**
- Rewrite scanner logic or the rddf-session coordinator beyond the one-line constant change.
- Introduce symlinks, runtime path resolution, or any other fallback mechanism.
- Modify `INSTALL.md` or the rdd-workflow installation layout.
- Fix the same issue in other shared helpers (`worktree.sh`, `archive.sh`) if they exist; those are out of scope.
- Change rddf-session heartbeat timeout, kind aliases, or schema version.

## Decisions

- **Local-first, global fallback**: The scanner tries `$PROJECT_ROOT/skills/_lib/state.sh` first. Only when that file is absent does it try `${HOME}/.agents/skills/_lib/state.sh`. This preserves zero behavior change for the rdd-workflow repository itself while fixing global-install consumer projects.
- **Compact `||` loop**: Both `scan-state.sh` and `guide_entry.sh` use a short `for` loop that tests `[-f]` and `source`s the first existing path. If the loop finishes without sourcing anything, a single stderr warning is printed. This keeps the code change to roughly +2~4 lines per file and avoids duplicating fallback logic.
- **Warning wording**: The warning includes the literal text `rdd-workflow not installed`, lists both tried paths, and points to `INSTALL.md` so users know how to recover. It is written to `>&2` to keep stdout clean for JSON consumers.
- **Additive terminal state**: `_TERMINAL_STATES` is changed from a three-element set to a four-element set by adding `"orphaned"`. The existing three states are kept verbatim to avoid breaking any consumer that depends on them.
- **Bats over pytest for the fallback matrix**: The fallback involves bash `source` paths and `$HOME`, so bats is the natural test framework. The existing test infrastructure already uses bats, so no new dependencies are introduced.

## Risks / Trade-offs

- [Risk] Warning could be missed if the AI caller ignores stderr → Mitigation: the warning text is explicit and includes `INSTALL.md`; stdout still produces an empty menu so callers can detect the degraded state.
- [Risk] Adding `orphaned` to `_TERMINAL_STATES` will make `update_session_status` refuse to transition out of `orphaned` → Mitigation: this is the intended contract; orphaned sessions are terminal and should be archived, not resumed.
- [Risk] The compact loop could warn if a real `state.sh` exists but `source` fails for syntax reasons → Mitigation: the repository's own `state.sh` is already tested; consumer installs are expected to be intact. The warning text is still actionable.
- [Risk] Line-count constraint (≤10 source lines) makes defensive error handling sparse → Mitigation: tests cover the four matrix cases and the terminal-state contract; the logic is intentionally minimal.

## Migration Plan

N/A — this is an additive bug fix. Consumer projects that already have a global install will begin working automatically. Projects that lack any install will see the new stderr warning with recovery instructions. No state migration is needed for rddf-session; existing `sessions.json` files continue to validate.

## Open Questions

None.
