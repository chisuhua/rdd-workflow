# Attach/Detach Audit Report

**Change**: `audit-attach-detach-calls`  
**Mode**: read-only audit  
**Scope**: attach_change / detach_change call sites, guide hook chain, ADR-0017 contract comparison

## 1. Executive Summary

`detach_change()` is wired only once in production code, inside `rddf_session_hook_heartbeat()` for `guide-ship`; `attach_change()` has no production call site at all. The expected ship-entry attach lifecycle described by ADR-0017 and `docs/v2-multi-session-guide.md` is therefore incomplete: the attach hook is missing, and ship close does not verify that `attached_changes` is empty before completion.

## 2. Definitions

| Term | Meaning |
|------|---------|
| **Call site** | A concrete `.attach_change(` or `.detach_change(` invocation in code |
| **Production call site** | Code outside `tests/` and outside documentation examples |
| **Definition** | The `def attach_change` / `def detach_change` function body |
| **Hook** | `rddf_session_hook_entry`, `rddf_session_hook_close`, or `rddf_session_hook_heartbeat` |
| **Missing hook** | A lifecycle point required by the contract but not actually wired in code |

## 3. Call Site Inventory

### attach_change

| File | Line | Type | Context |
|------|------|------|---------|
| `skills/rddf-session/scripts/rddf_session.py` | 334-347 | definition | `def attach_change(self, session_id: str, change_name: str) -> None` |
| `tests/unit/test_rddf_session.py` | 109-124 | test | `coordinator.attach_change(...)` in attach and idempotency tests |
| `tests/unit/test_rddf_session.py` | 132-133 | test | attach before detach test setup |
| `openspec/changes/audit-attach-detach-calls/proposal.md` | 10-18, 24-28, 32-35 | doc-reference | states attach/detach are being audited and report target |
| `openspec/changes/audit-attach-detach-calls/design.md` | 10-20, 33-35, 51-55, 61-67, 72-80 | doc-reference | defines the contract and audit scope |
| `openspec/changes/archive/2026-07-09-add-rddf-session/tasks.md` | 11 | doc-reference | historical task to implement attach/detach lifecycle |
| `docs/adr/ADR-0017-rddf-session.md` | 24-30, 73-80, 94-110, 116-127 | doc-reference | expected lifecycle and implementation notes |
| `docs/v2-multi-session-guide.md` | 453-461 | doc-reference | expected automatic stage management |
| `proposal-suggestions.md` | 139, 169 | doc-reference | prior proposals mention attach/detach lifecycle |

### detach_change

| File | Line | Type | Context |
|------|------|------|---------|
| `skills/rddf-session/scripts/rddf_session.py` | 349-362 | definition | `def detach_change(self, session_id: str, change_name: str) -> None` |
| `skills/rddf-session/scripts/rddf_session_hooks.sh` | 184 | production | `coord.detach_change(sid, change_name)` inside `rddf_session_hook_heartbeat()` |
| `tests/unit/test_rddf_session.py` | 129-133 | test | `coordinator.detach_change(...)` in detach test |
| `openspec/changes/audit-attach-detach-calls/proposal.md` | 10-18, 24-28, 32-35 | doc-reference | states detach is in audit scope |
| `openspec/changes/audit-attach-detach-calls/design.md` | 10-20, 33-35, 51-55, 61-67, 72-80 | doc-reference | defines the contract and audit scope |
| `openspec/changes/archive/2026-07-09-add-rddf-session/tasks.md` | 11 | doc-reference | historical task to implement attach/detach lifecycle |
| `docs/adr/ADR-0017-rddf-session.md` | 24-30, 73-80, 94-110, 116-127 | doc-reference | expected lifecycle and implementation notes |
| `docs/v2-multi-session-guide.md` | 453-461 | doc-reference | expected automatic stage management |

## 4. Hook Call Chain

| Guide skill | Entry hook | Close hook | Heartbeat hook | attach_change called? | detach_change called? |
|------------|------------|------------|----------------|------------------------|-----------------------|
| `guide-arch` | `rddf_session_hook_entry` (line 85) | `rddf_session_hook_close` (line 533) | none | no | no |
| `guide-plan` | `rddf_session_hook_entry` (line 86) | `rddf_session_hook_close` (line 477) | none | no | no |
| `guide-ship` | `rddf_session_hook_entry` (line 42) | `rddf_session_hook_close` (line 591) | `rddf_session_hook_heartbeat` (line 506) | no | yes, via heartbeat |

### Hook internals

| Hook function | attach_change | detach_change | Notes |
|--------------|---------------|---------------|-------|
| `rddf_session_hook_entry()` | no | no | Creates/fetches session, resolves parent, prints session id |
| `rddf_session_hook_close()` | no | no | Creates/completes session, but does not inspect `attached_changes` |
| `rddf_session_hook_heartbeat()` | no | yes | Detaches `change_name` when provided, then refreshes heartbeat |

## 5. Expected vs Actual

### Expected behavior from contract

| Source | Expected behavior |
|--------|-------------------|
| `docs/adr/ADR-0017-rddf-session.md` | `guide-arch`/`guide-plan`/`guide-ship` create or find rddf-sessions at entry; `attached_changes` should be part of the session lifecycle |
| `docs/v2-multi-session-guide.md` §“自动管理” | `guide-ship` entry creates `kind=stage_ship`; once all `attached_changes` are archived, `stage_ship` becomes completed |

### Actual behavior in code

| Area | Actual behavior |
|------|-----------------|
| guide entry hooks | `guide-arch`, `guide-plan`, and `guide-ship` all call `rddf_session_hook_entry`, but none of them call `attach_change` |
| archive/heartbeat path | `guide-ship` heartbeat calls `detach_change(change_name)` after archive when a change name is provided |
| ship completion | `rddf_session_hook_close(stage_ship, ...)` completes the session without checking that `attached_changes` is empty |

## 6. Missing Hooks

1. **Missing ship-entry attach hook**  
   `guide-ship` entry should attach the active change to the current `stage_ship` rddf-session, but there is no `attach_change()` call in `rddf_session_hooks.sh` or in `guide-ship/SKILL.md`.

2. **Missing attach lifecycle symmetry for archive flow**  
   Heartbeat detaches an archived change, but there is no corresponding attach at ship start, so the `attached_changes` list never records the change before it is removed.

3. **Missing attached_changes completion gate**  
   `rddf_session_hook_close()` completes `stage_ship` without asserting that all attached changes were detached first. This allows completion to happen even if the lifecycle is incomplete.

## 7. Recommendations

- Add a dedicated ship-entry attach hook for the active change before execution begins.
- Ensure the ship close path validates that `attached_changes` is empty before marking `stage_ship` completed.
- Keep the detach call in heartbeat/archive flow only if the attach lifecycle is added symmetrically; otherwise the session data remains one-sided and harder to reason about.

## 8. Evidence Index

- `skills/rddf-session/scripts/rddf_session.py:334-362`
- `skills/rddf-session/scripts/rddf_session_hooks.sh:38-190`
- `skills/guide-arch/SKILL.md:85, 533`
- `skills/guide-plan/SKILL.md:86, 477`
- `skills/guide-ship/SKILL.md:42, 506, 591`
- `docs/adr/ADR-0017-rddf-session.md:24-30, 73-80, 94-110, 116-127`
- `docs/v2-multi-session-guide.md:453-461`
