# rdd-workflow Architecture

> **For:** Project maintainers + contributors. If you are a **user** of rdd-workflow in another project, start at `../ONBOARDING.md` instead.

This directory is the **current-architecture snapshot** for rdd-workflow. Every doc here explains **why** a piece of the system exists (intent + trade-offs) and **the key structural seams** (modules, contracts, data flow). Implementation details (function signatures, line-by-line) live in code + docstrings.

For **decisions** behind the design, see [`../adr/README.md`](../adr/README.md). For **transient design artefacts** (specs, plans), see `../superpowers/specs/` and `../superpowers/plans/`.

## Doc Map

| Doc | Topic | Primary ADRs |
|-----|-------|--------------|
| [overview.md](overview.md) | System overview, module map, design principles | 0003, 0025 |
| [workflow-phases.md](workflow-phases.md) | Four-phase arch → design → plan → ship + handoffs | 0003, 0024, 0025 |
| [loop-engine.md](loop-engine.md) | 5 building blocks + loop/menu/hybrid modes | 0002, 0004 |
| [state-and-events.md](state-and-events.md) | 3-layer state model | 0006, 0016 |
| [gates-and-quality.md](gates-and-quality.md) | gate / tribunal / arch_quality_gate / change_alignment | 0007, 0008, 0018, 0019 |
| [skills-and-handoff.md](skills-and-handoff.md) | SKILL.md frontmatter, discovery, handoff contracts | 0016 |
| [multi-session.md](multi-session.md) | rddf-session lifecycle + conflict resolver | 0010, 0017 |
| [extension-points.md](extension-points.md) | How to add a skill / detector / action / CLI / ADR | 0021 |
| [historical-evolution.md](historical-evolution.md) | v1.0 → v2.0 → v2.1 timeline + per-refactor motivation | — |

## Update Convention

When you add a new skill, handoff file, or ADR, the corresponding `architecture/*.md` and `../adr/README.md` must be updated in the **same change**. This prevents documentation drift.

## When This Doc Set Was Last Refreshed

The doc set was last regenerated from live code as of v2.0.9+. See `historical-evolution.md` for the full version history.
