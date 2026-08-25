## Context

`add-hierarchical-roadmap-structure` (shipped 2026-08-20) created the Fragment model infrastructure in `_lib/roadmap_state.py` (Fragment dataclass + 6 additive APIs: `load_fragments`, `get_fragment`, `list_active_fragments`, `render_fragment_index`, `validate_fragment_refs`, `aggregate_phase_progress`) plus `.rddf/roadmap/{phases,features,archive}/` directory structure. The proposal explicitly described "scenario 3" (cross-stage feature manual creation) but provided no operational entry point — users must today hand-craft YAML via `cat > .rddf/roadmap/features/<name>.md` followed by manual `render_fragment_index` invocation. The `.rddf/roadmap/features/` directory on this repo remains empty, blocking adoption of the hierarchical roadmap model.

This change adds the missing operation primitive: a `rddf roadmap add-feature` CLI that produces a complete fragment file + AUTO-INDEX refresh in a single invocation. It is reachable from two entry points: the `guide-arch` Phase 4 menu (interactive, 4-step confirmation flow) and direct CLI invocation (script-friendly). The Python implementation reuses the existing Fragment model APIs without mirroring the legacy `add_phase` flat-model debt.

## Goals / Non-Goals

**Goals:**
- Provide an atomic, validated, idempotent creation primitive for feature fragments
- Auto-refresh the main roadmap document's `<!-- AUTO-INDEX -->` block on each creation
- Reuse the existing Fragment model APIs (no new state, no new schema)
- Expose the primitive from both `guide-arch` Phase 4 menu and direct `rddf roadmap add-feature` CLI
- Validate `phase_refs` against `list_active_fragments(kind="phase")` (single read path, no direct directory scanning)

**Non-Goals:**
- Bind feature fragments to openspec changes (`feature_ref` in `roadmap-meta.yaml` — separate proposal)
- Enhance the view-only `feature.md` skill (which derives from `iteration.json`)
- Implement `edit-feature` / `archive-feature` / `delete-feature` subcommands (future change)
- Refactor legacy `add_phase` from flat model to Fragment model (potential ADR-0034, separate proposal)
- Implement hierarchical feature nesting (`features/auth-v2/sso.md`)
- Modify `iteration.json` / `deps-analysis.json` / `.arch-handoff.json` schema
- Modify any `openspec/specs/*.md` content

## Decisions

### 1. Four-layer architecture (UI → CLI → Library → Filesystem)

Mirror the existing `rddf roadmap migrate` and `validate-fragments` pattern:

```
UI:    guide-arch Phase 4 menu → delegates to roadmap skill
CLI:   skills/roadmap/scripts/roadmap_add_feature.sh  (NEW, thin shell)
       _lib/cli/roadmap_cmd.py  _SUBCOMMAND_MAP extension
Lib:   _lib/roadmap_state.py::add_feature  (NEW, Python core)
       + reuse list_active_fragments / load_fragments /
         validate_fragment_refs / render_fragment_index
FS:    .rddf/roadmap/features/feat-<name>.md   (atomic write)
       .rddf/roadmap.md                        (atomic write via AUTO-INDEX sentinel)
```

**Alternatives considered:**
- Inline bash in `guide-arch` SKILL.md: rejected — would skip the CLI primitive, blocking non-arch re-use
- Direct Python in `_lib/cli/roadmap_cmd.py` (no shell wrapper): rejected — breaks consistency with `migrate` and `validate-fragments` which both use `.sh` dispatch
- Mirror `add_phase` flat-model implementation: rejected — `add_phase` writes to `roadmap.md` + updates `roadmap-state.json`, which is a known dual-track debt; Fragment model is the future

### 2. Body content policy: skeleton only

The MVP CLI generates a 3-section body skeleton only (概述 / 跨阶段拆分 / 验收标准) with `<TBD>` placeholders. Body content is filled by users/agents post-creation via direct file editing.

**Alternatives considered:**
- Accept body via CLI flags (`--overview`, `--criteria`): rejected — would explode CLI surface for a one-shot operation
- Generate rich defaults from proposal.md context: rejected — adds mapping complexity for marginal value; users expect to customize

### 3. Validation source: `list_active_fragments(kind="phase")`

`phase_refs` validation uses `list_active_fragments(kind="phase")` as the single source of truth, not a direct directory scan. This keeps the read path consistent with downstream consumers (`feature.md` skill, render_fragment_index) and avoids drift between validation and render paths.

### 4. Atomicity: write-then-render with compensating rollback

Write order: validate → mkdir features/ → write fragment (atomic tmp+rename) → render_fragment_index. If render fails, the just-written fragment is deleted (compensating rollback) so AUTO-INDEX never lags behind disk state. Idempotency is guaranteed by `render_fragment_index`'s SENTINEL-strip-and-rebuild behavior.

**Alternatives considered:**
- Two-phase commit with rollback journal: rejected — overkill for a one-file write; OS-level `os.replace` already provides atomicity
- Best-effort render (log warning, continue): rejected — leaves orphan fragment that future `load_fragments` calls would surface without AUTO-INDEX entry; violates user mental model

### 5. `--force` semantics: full regenerate, no merge

`--force` regenerates both frontmatter and body skeleton from scratch, destroying any user-edited body content. This is documented behavior; merge semantics are deferred to a future `edit-feature` subcommand.

**Alternatives considered:**
- Merge existing body with new frontmatter: rejected — requires structured body parsing (YAML/JSON-aware) far beyond MVP scope
- Refuse `--force` if body hash differs: rejected — too clever; users want explicit overwrite semantics

### 6. SKILL.md interactive UX: 4-step forced sequence

`guide-arch` Phase 4 menu option triggers 4 mandatory steps: input name → input theme → multi-select phase_refs → preview+confirm. Each step's failure returns to the menu without writing.

**Alternatives considered:**
- Single combined form: rejected — error recovery is harder when fields are tangled
- Open-ended free-form conversation: rejected — too easy to fall back to "y" without review (Oracle review flagged this as known ADR risk for adr-create pattern)

### 7. Shell wrapper uses env-var passing (Oracle C1)

`roadmap_add_feature.sh` parses CLI args, then exports env vars and calls `_lib/roadmap_state.py::add_feature`. No `python3 -c "...$VAR..."` inline bash interpolation. This follows the security pattern established by `plan_deps_candidates.sh`, `update_roadmap_progress.sh`, `execute_step7.sh`, etc.

## Risks / Trade-offs

- **Body content not validated**: Users can write arbitrary content in `## 概述` / `## 跨阶段拆分` / `## 验收标准` sections. Trade-off accepted: these sections are content, not contract; downstream tooling does not consume them.
- **Dual-track debt (`add_phase` flat model)**: Not addressed. `add_phase` (L268 in `_lib/roadmap_state.py`) still uses the legacy flat model. Recommended follow-up: file a separate `add-improve` proposal to refactor `add_phase` to Fragment model (potential ADR-0034). This proposal does NOT touch `add_phase`.
- **No automatic binding to openspec changes**: Feature fragments and openspec changes remain disconnected. A change creator may create a fragment without ever opening an openspec change, or vice versa. Future `feature_ref` field in `roadmap-meta.yaml` will close this gap.
- **`.rddf/roadmap/features/` not yet populated**: This proposal only adds the creation primitive. Existing fragments will be empty unless users explicitly create them. Migration of historical "implicit" features (e.g., `auth-v2` discussed in design rationale) is out of scope.
- **Compensating rollback depends on render failure being detectable**: If `render_fragment_index` raises partway through and leaves a partial main_doc, our compensating deletion of the fragment is still correct (fragment + index inconsistent → user retries without fragment), but the main_doc may be in an inconsistent state until next `render_fragment_index` call. Low-probability risk; mitigated by `render_fragment_index`'s SENTINEL-strip behavior making partial writes impossible.
- **No `--dry-run` flag**: Users cannot preview the fragment file before writing. Trade-off: minimal CLI surface for MVP; future `edit-feature` could add dry-run.
