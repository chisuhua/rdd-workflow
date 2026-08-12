# Historical Evolution

This document records the **architectural** milestones — the points at which the system's structure changed, not every release. For release-by-release notes, see [`../../CHANGELOG.md`](../../CHANGELOG.md).

## Timeline

```
v1.0 (2026-06-03)           v1.1 (2026-06-05)           v2.0 (2026-06-22)
─────────────────           ─────────────────           ─────────────────
Single guide.md (10         Two phases:                  Three phases:
phases, menu-driven)        spec / ship                  arch / plan / ship
                            (ADR-0001)                   (ADR-0003)
                                                        + Loop engine (ADR-0004)
                                                        + Interaction modes (ADR-0002)
                                                        + Human-in-Loop nodes (ADR-0005)
                                                        + State vector + event log (ADR-0006)
                                                        + Gate mechanism (ADR-0007)
                                                        + Tribunal committee (ADR-0008)

v2.0.1 (2026-07-09)         v2.0.5 (2026-07-16)         v2.0.6 (2026-07-21)
─────────────────           ─────────────────           ─────────────────
rddf-session user           Per-skill scripts/           guide-design introduced
lifecycle                   migration begins             (ADR-0025) — proposal review
(ADR-0017)                  (ADR-0021)                   moves out of arch

v2.0.8 (2026-07-28)         v2.0.9 (2026-08-04)         v2.1.0 (2026-08-12)
─────────────────           ─────────────────           ─────────────────
Global install support      Deps-driven execution mode   Continuous evolution
                            (ADR-0024)                  feedback loop
                                                        (ADR-0027)
```

## Pain Point → Solution Mappings

| When | Pain | Solution | ADR |
|------|------|----------|-----|
| v1.0 | Every workflow step required user menu selection; no autonomy. | Introduce a goal-driven loop orchestrator. | 0002, 0004 |
| v1.1 | spec/phase and ship/phase both lived in one file; couldn't evolve independently. | Split into `guide-spec` + `guide-ship`. | 0001 (later superseded by 0003) |
| v2.0 | v1.x couldn't represent "I want to define architecture separately from changes." | Three-phase architecture: arch / plan / ship. | 0003 |
| v2.0 | State scattered across 13 files; impossible to query consistently. | Centralise to a schema-versioned state vector + append-only event log. | 0006 |
| v2.0 | Each phase-end check was bespoke and untyped. | Generic gate mechanism: error/warning + plugin extensions. | 0007 |
| v2.0 | Single-agent review caught only what the reviewer saw. | Multi-agent tribunal with weighted scoring + data sanitization. | 0008 |
| v2.0.1 | Cross-session continuity was lost when the user closed opencode. | rddf-session: project-level sessions.json + 4-option conflict resolver. | 0017 |
| v2.0.5 | Skills accumulated inline bash blocks (some 100+ lines), making them hard to diff. | Phase 2 migration: per-skill `scripts/` directories. | 0021 |
| v2.0.6 | Arch phase had grown proposal-creation + proposal-review on top of ADR/roadmap work; review load was heavy. | Split `guide-design`: arch keeps architecture definition; design owns proposal lifecycle + two-tier content review. | 0025 |
| v2.0.8 | Per-project install was painful; users wanted one install for all projects. | Global install via `~/.agents/skills/`. | (no ADR — install-script only) |
| v2.0.9 | Execution mode (worktree vs lightweight) was decided in guide-ship by inspecting disk; couldn't see plan-time intent. | Deps analysis writes execution mode into `.plan-handoff.json`; guide-ship reads it. | 0024 |
| v2.1.0 | No structured feedback loop from third-party rdd-workflow users back to maintainers; evolution was driven by intuition, not evidence. | Continuous evolution feedback loop: detect → buffer → report → triage → close, with triple opt-in, dedup_hash for cross-machine stability, dual-mode archive close hook. | 0027 |
| v2.1.x | Bash `trap ERR` could not capture failures from sub-scripts that didn't source `post_flow_wrap.sh`; agents didn't always comply with SKILL.md Phase Exit prose; SIGKILL/OOM left no signal at all. | New `rddf orchestrate` subcommand: Python supervisor that captures every phase subprocess with tempfile streams + sanitize, appends to JSONL trace, runs stale-trace sweep on entry to detect killed phases (B4 fix), single-writer rule to coexist with existing trap path. 4 SKILL.md files updated with 3-rule Phase Exit checklists. | spec 2026-08-12 |

## Architectural Constants

These have held since v2.0 and are unlikely to change without a major version bump:

- **`openspec/` is the source of truth** for change artefacts (`proposal.md`, `specs/*.md`, `tasks.md`).
- **Skills are discovered by name**; `SKILL.md` frontmatter is the contract.
- **`_lib/` is shared but not user-invocable** — end users never call `_lib.*` directly.
- **Bash + Python coexistence** — bash for orchestration, Python for stateful logic.
- **Hard isolation in worktrees** — every shipped change lives in a worktree until archived.

## What's Still Open

Tracked under `../proposal-suggestions.md` and `../proposal-approved.md`:
- v3.0+ candidate: declarative flow DSL (ADR-0011, 0012 — adopted but not implemented).
- v3.0+ candidate: scheduled triggers (ADR-0009 — placeholder).
- v2.1.x follow-up: ADR-0017 conflict-resolver 5th option "report upstream" (requires separate ADR to modify rddf-session).
