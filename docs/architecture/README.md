# rdd-workflow Architecture

> **For:** Project maintainers + contributors. If you are a **user** of rdd-workflow in another project, start at `../ONBOARDING.md` instead.

This directory is the **current-architecture snapshot** for rdd-workflow. Every doc here explains **why** a piece of the system exists (intent + trade-offs) and **the key structural seams** (modules, contracts, data flow). Implementation details (function signatures, line-by-line) live in code + docstrings.

For **decisions** behind the design, see [`../adr/README.md`](../adr/README.md). For **transient design artefacts** (specs, plans), see `../superpowers/specs/` and `../superpowers/plans/`.

## Doc Map

| Doc | Topic | Primary ADRs |
|-----|-------|--------------|
| [overview.md](overview.md) | System overview, module map, design principles | 0003, 0025, 0034 |
| [workflow-phases.md](workflow-phases.md) | Four-stage arch → planner → builder → verifier + handoffs (v4.0.1 per ADR-0043 + ADR-0048; supersedes v3.0 five-phase) + `rdd-quick` bypass (per ADR-0047, AMENDED per ADR-0048) + **LLM-augmented P0** (per ADR-0049) | 0003, 0024, 0025, 0034, 0043, 0044, 0047, 0048, 0049 |
| [roadmap-organization.md](roadmap-organization.md) | **NEW** Roadmap 内容组织:三层文件结构 + 主文档三大 sentinel 区域 + 唯一写入方矩阵 + Sprint/Phase 正交关系 + 主题状态词汇(roadmap 概念入门,2026-09-21 沉淀) | 0038, 0041, 0048 |
| [v4-pipeline-data-flow.md](v4-pipeline-data-flow.md) | **NEW (v4.0.1)** Complete path topology + data flow timeline + `recommended_route` advisory signal pipeline (companion to workflow-phases.md) | 0048 |
| [loop-engine.md](loop-engine.md) | 5 building blocks + loop/menu/hybrid modes | 0002, 0004 |
| [state-and-events.md](state-and-events.md) | 3-layer state model | 0006, 0016 |
| [gates-and-quality.md](gates-and-quality.md) | gate / tribunal / arch_quality_gate / change_alignment | 0007, 0008, 0018, 0019 |
| [improvement-check-mechanisms.md](improvement-check-mechanisms.md) | Project-level (ADR-0014) vs workflow-level (ADR-0027) improvement checks, Oracle-reviewed gap analysis + 6-PR plan | 0014, 0027, 0029 |
| [skills-and-handoff.md](skills-and-handoff.md) | SKILL.md frontmatter, discovery, handoff contracts | 0016 |
| [multi-session.md](multi-session.md) | rddf-session lifecycle + conflict resolver | 0010, 0017 |
| [extension-points.md](extension-points.md) | How to add a skill / detector / action / CLI / ADR | 0021 |
| [historical-evolution.md](historical-evolution.md) | v1.0 → v2.0 → v2.1 timeline + per-refactor motivation | — |

## Update Convention

When you add a new skill, handoff file, or ADR, the corresponding `architecture/*.md` and `../adr/README.md` must be updated in the **same change**. This prevents documentation drift.

## When This Doc Set Was Last Refreshed

The doc set was last regenerated from live code as of v2.0.9+. See `historical-evolution.md` for the full version history.
