## Context

The repository now contains an initial `rdd-verifier` phase, but the implementation is not connected to the real lifecycle. Queue discovery uses `ship-done`, which is a phase-level event rather than a per-change iteration status. The CLI is a scaffold, production code does not write verdict caches, loop state is global instead of per change, and the archive gate has no coherent shared verification contract across lightweight and worktree modes.

The existing `guide-ship` archive flow already performs its archive gate before merge. It owns merge, `openspec archive`, archive commits, branch/worktree cleanup, and iteration synchronization. This change will preserve those responsibilities and introduce a precise verification handoff before archive finalization.

The dashboard currently collects lifecycle change data but has no verification data source or rendering dimension. The implementation must remain backward compatible with historical iteration entries and archived changes created before verifier metadata existed.

A pre-plan review identified five contracts that had to be closed before guide-plan: deterministic gate precedence, branch-identity fail-closed rule, ac-verifier fallback structured output, layered ownership of the four storage layers, and iteration schema versioning. The change now includes those contracts.

## Goals / Non-Goals

**Goals:**

- Make rdd-verifier discover the real set of implemented, task-complete, non-archived changes.
- Make `rddf rdd-verify` execute ac-verifier, persist verdicts, classify failures, update state, and return meaningful aggregate exit codes.
- Store verification state and loop state per change.
- Bind verdict caches to the `openspec/<change>` branch tip and fail closed if the branch is missing or the current branch does not match.
- Keep guide-ship responsible for merge, archive, branch deletion, worktree cleanup, and archive synchronization.
- Make archive readiness require a current passing verification result, with an explicit audited bypass.
- Compose `STRICT_AC_GATE`, `SKIP_RDD_VERIFIER`, `RDDF_VERIFIER_BYPASS_REASON`, `FORCE_ARCHIVE_INCOMPLETE`, and `FEATURE_ARCHIVE_GATE` so the verifier result dominates legacy ac-verifier fallback strictness.
- Persist the direct archive ac-verifier fallback result into the canonical cache using a structured output contract.
- Add dashboard collection and rendering for implementation, verification, and archive dimensions, with explicit schema v7 and icon map coverage.
- Add tests that use valid lifecycle states and exercise the full pre-archive handoff including bypass and gate precedence.

**Non-Goals:**

- Do not remove or change the semantics of `rddf ac-verify <change>` as a single change diagnostic command.
- Do not move merge, `openspec archive`, branch deletion, or worktree cleanup into rdd-verifier.
- Do not add a new top-level lifecycle status for every verification state; verification is a separate object.
- Do not retroactively fabricate passing verification results for historical archived changes.
- Do not introduce concurrent LLM execution in this change; batch verification remains serial with checkpoints.
- Do not redesign the dashboard UI framework or add external dependencies.

## Decisions

### 1. Preserve guide-ship ownership and insert a verification handoff

`guide-ship` remains the delivery owner. Its archive path is conceptually divided into:

```text
prepare/execute → verification pending → rdd-verifier → archive gate → merge/archive/cleanup
```

The existing `archive_gate_check` remains the final defensive enforcement point and runs before merge. rdd-verifier is the user-facing batch producer of verification results; guide-ship consumes those results.

The verifier phase must not invoke archive or cleanup operations. A failed verifier route returns the user to guide-ship or guide-plan; a passed verifier route returns `archive-ready` to guide-ship.

A negative-assertion test SHALL be added: after running `rddf rdd-verify`, no branch is deleted, no worktree is removed, and no `openspec/changes/<change>` directory is moved to `archive/`.

**Alternative rejected:** move archive and cleanup into rdd-verifier. This would mix high-human-involvement semantic review with mechanical delivery operations and contradict the existing `guide-ship` role model.

### 2. Use existing lifecycle statuses plus an independent verification object

Keep the existing iteration status enum (`planned`, `proposed`, `in_worktree`, `review`, `completed`, `archived`, `archived_partial`). Add an optional object to each change:

```json
{
  "verification": {
    "state": "pending|running|passed|failed|halted|bypassed|legacy|unknown",
    "verdict_sha": "<branch tip sha or null>",
    "checked_at": "<iso timestamp or null>",
    "route": "archive-ready|guide-ship|guide-plan|halted|null",
    "loop_count": 0,
    "failed_acs": ["AC-2"],
    "bypass_reason": null,
    "bypass_source": null,
    "archive_ready": false
  }
}
```

The object is optional for backward compatibility. A missing object on an active change is treated as `unknown`; on an archived change it is treated as `legacy`, never as `passed`.

A change is verifier-eligible when its lifecycle status is `in_worktree` or `completed`, its tasks are complete (`tasks_total > 0` and `tasks_done == tasks_total`), and it is not archived. The implementation must use the canonical iteration data rather than inventing `ship-done`.

### 3. Iterate the iteration schema to v7 with explicit verification fields

The current schema restricts `version` to `[3, 4, 5, 6]`. This change bumps it to allow `7` while keeping backward compatibility for v3–v6. The `verification` object is added under `changes.items.properties` and is optional. Required sub-fields are `state` and `archive_ready`; everything else is optional and nullable. Writers must include the new fields; readers must accept v3–v6 entries without `verification`.

### 4. Make the CLI the real orchestration boundary

`_lib/cli/rdd_verify_cmd.py` will own the non-interactive batch orchestration used by the skill and CI:

1. discover eligible changes;
2. initialize or load per-change verification state;
3. resolve the implementation commit as the `openspec/<change>` branch tip when present; otherwise fail closed;
4. read a matching cache or invoke ac-verifier;
5. persist the cache and verification state;
6. classify failed ACs using the existing pure classifier;
7. route failures and compute the aggregate exit code.

Aggregate exit code precedence is `halted (4) > error (3) > failed (1) > bypassed/passed (0)`. A non-empty batch with at least one halt masks failures and errors.

`SKIP_RDD_VERIFIER=yes` requires `RDDF_VERIFIER_BYPASS_REASON`. With both set, the command writes `verification.state=bypassed`, `bypass_source=SKIP_RDD_VERIFIER`, and `bypass_reason=<reason>` instead of producing a passed verdict. Without the reason, the command fails closed with exit code `3`. `SKIP_RDD_VERIFIER` SHALL NOT bypass `FEATURE_ARCHIVE_GATE=hard` or `FORCE_ARCHIVE_INCOMPLETE=yes`.

The interactive `skills/rdd-verifier/SKILL.md` remains responsible for user confirmation of classifications and route selection, while the CLI provides deterministic state and exit-code behavior.

### 5. Use per-change state and canonical main-repository cache location

Loop state files are stored per change:

```text
.rddf/state/verifier/<change-name>.json
```

Legacy single-file `.verifier-loop.json` migration: if the legacy file's `change` field equals the only eligible change, migrate it; otherwise leave the legacy file in place, log the situation, and initialize a new per-change state. Multi-change scenarios never copy legacy retry history into any change.

The cache lives in the canonical main repository state directory:

```text
.rddf/state/.ac-verdict-<change-name>.json
```

The cache payload adds `verification_state`, `failed_acs`, `source`/`ran_by`, and `schema_version`. `archive_gate_check` resolves the main repository root for cache lookup, resolves the implementation commit from `openspec/<change>` (worktree mode) or the current lightweight branch (when it matches), and falls closed otherwise.

All path-sensitive Python calls receive values via argv or environment variables; no shell path is interpolated into Python source.

### 6. Make archive readiness a strict verifier contract

The archive gate accepts a change only when:

```text
verification.state in (passed, bypassed) AND archive_ready == true
AND for passed: verdict_sha == current implementation branch tip
AND cache verdict contains no failed AC
```

A stale or missing cache is not a pass. The existing ac-verifier invocation remains a fallback for direct archive calls; it must produce a structured verdict and the gate must write that verdict to the canonical cache.

`STRICT_AC_GATE` controls the legacy direct ac-verifier fallback path only. It SHALL NOT make a cached failed verifier result pass. `SKIP_RDD_VERIFIER` produces bypassed verification but never makes a failed verdict pass. `FEATURE_ARCHIVE_GATE=hard` and `FORCE_ARCHIVE_INCOMPLETE=yes` retain their existing semantics, and verifier bypass does not weaken them.

### 7. Direct archive fallback SHALL write structured verdict to the canonical cache

When `archive_gate_check` invokes ac-verifier directly and ac-verifier produces a structured verdict (exit code `0` or `1`), the gate parses the verdict and writes it to the canonical cache with `ran_by=archive_gate_check`. The cache entry MUST include `verification_state`, `failed_acs`, and `implementation_ref`.

If ac-verifier returns an un parseable verdict JSON, the gate logs a warning, does NOT write the cache, and does NOT promote to passed. If the cache write fails after a passing verdict, the gate blocks archive. Exit code `2` from ac-verifier means "skipped, no AC section", and the gate does not write the cache; archive proceeds only when `SKIP_AC_VERIFICATION=yes` is set.

### 8. Lay out storage ownership across four layers

Iteration `verification` holds summary fields only:

- `state`, `archive_ready`, `failed_acs`, `verdict_sha`, `checked_at`, `route`, `bypass_reason`, `bypass_source`, `loop_count`.

Per-change loop state holds:

- retry history, classification history, halt reason, last user confirmation timestamp.

Cache holds:

- raw verdict, `codebase_commit`, `ran_by`, `schema_version`, optional `implementation_ref`.

Audit JSONL holds:

- append-only events (running, failed, halted, bypassed, archive-ready), each with timestamp and the relevant commit.

The summary fields are recomputable from the loop state + cache, so duplicates in iteration are forbidden. The writer writes the loop state first, then the cache, then the iteration summary, and finally the audit event. If any step fails, the change is left in a verifiable in-progress state and the operation exits non-zero without promoting the verdict to passed.

### 9. Sync archive metadata without erasing verification

`mark_iteration_archived` MUST preserve `verification` and only add `archived_at`. `clean-stale-plan-handoff-on-ship-done`, plan-file cleanup, and post-archive cleanup MUST NOT touch `.rddf/state/verifier/`, `.rddf/state/.ac-verdict-<change>.json`, or the audit log. Dashboard labels for archived changes use `verification.state` directly, treating legacy archived changes as `verification.state=legacy` regardless of `bypass_reason`.

### 10. Add dashboard verification dimension without breaking the 72-char width

`ChangeEntry` carries the structured `verification` object and a derived `archive_ready` boolean. Renderers add a short verification code column (`pending`, `running`, `passed`, `failed`, `halted`, `bypassed`, `legacy`, `unknown`) and a detail line for failed ACs and route. When row width exceeds 72 characters, the change name is truncated on the right and the verification code is preserved. The icon map covers every state in terminal and plain modes; unknown states fall back to a stable character without raising.

## Risks / Trade-offs

- Binding verdicts to branch HEAD means any implementation commit after verification invalidates the result. This is intentional and prevents stale verification from authorizing archive.
- Moving cache lookup to the main repository state directory reduces worktree isolation for verifier metadata, so filenames must remain change-scoped and writes must be atomic/locked.
- Existing historical iteration entries lack verification data, so dashboard must show legacy/unknown instead of inferring a pass.
- The heuristic classifier remains imperfect, especially for non-English reasoning. User confirmation remains mandatory for failure routing.
- Making archive verification strict may expose existing changes that previously relied on warning-only AC verification. The bypass path is explicit and auditable rather than silently preserving the old behavior.
- Bypass audit metadata may grow over time; per-change loop state and the audit log must be bounded by retention policy.
- The full repository test suite is slow; the change adds focused lifecycle/archive/dashboard tests and still runs the repository's full regression gate before archive.