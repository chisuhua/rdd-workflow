# add-feature-fragment-command — Design Spec

**Date:** 2026-08-25
**Status:** Proposed
**Scope:** Add `add-feature` operation primitive that creates `.rddf/roadmap/features/<name>.md` fragments and refreshes `.rddf/roadmap.md` AUTO-INDEX. Wire it into `guide-arch` Phase 4 menu and `rddf roadmap` CLI. Inherits architecture from `add-hierarchical-roadmap-structure` (already shipped, scenario 3).
**Supersedes:** None — strictly additive.
**Parent spec:** `docs/superpowers/specs/2026-08-07-docs-restructure-architecture-snapshots-design.md` (add-hierarchical-roadmap-structure implementation)
**Related ADRs:** ADR-0003 (three-phase architecture), ADR-0016 (arch artifact discovery), ADR-0028 (role model)

---

## 1. Background

The `add-hierarchical-roadmap-structure` change (shipped 2026-08-20) created the foundation for cross-phase feature tracking by introducing:

- `.rddf/roadmap/{phases,features,archive}/` three-layer directory (all tracked)
- `.rddf/roadmap.md` main document with `<!-- AUTO-INDEX -->` sentinel
- `Fragment` dataclass + 6 additive APIs in `_lib/roadmap_state.py`:
  - `load_fragments`, `get_fragment`, `list_active_fragments`
  - `render_fragment_index`, `validate_fragment_refs`, `aggregate_phase_progress`

The proposal explicitly described "scenario 3" (cross-stage feature manual creation) but **did not provide an operational entry point**. Users must today hand-craft YAML:

```bash
cat > .rddf/roadmap/features/auth-v2.md <<'EOF'
---
id: feat-auth-v2
kind: feature
status: active
phase_refs: [phase-2, phase-3, phase-4]
主题: RBAC 权限模型
---
EOF
# ... plus body content + manual render_fragment_index call
```

This friction prevents the hierarchical roadmap model from being used in practice. The `.rddf/roadmap/features/` directory is currently empty on this repository (confirmed via Oracle first-round review).

### 1.1 Why a CLI primitive + menu wrapper, not just a menu

Mirroring the architectural pattern of `add_phase` (which lives in `_lib/roadmap_state.py` and is dispatched via `rddf roadmap <sub>`) gives us:

- **Reusability** — non-arch contexts (e.g., `guide-design` mid-flight, retrospective roadmap editing) can call the same primitive without going through the arch state machine.
- **Testability** — the CLI is independently testable without spinning up the menu.
- **Discoverability** — `rddf roadmap --help` surfaces the operation; menu is one of many entry points.

### 1.2 What this spec does NOT do (Non-Goals)

- Does **not** bind feature fragments to openspec changes (`openspec/changes/<name>/`). That N:N binding is deferred to design/plan phase work and belongs to a separate proposal.
- Does **not** enhance the existing `feature.md` view-only skill (which derives from `iteration.json` + `deps-analysis.json`). Cross-source enrichment (read fragment for theme/phase_refs, fall back to iteration for status) is a follow-up.
- Does **not** implement archive / edit / delete CLI subcommands. Each is a future change.
- Does **not** refactor `add_phase` from its legacy flat model to the Fragment model (see §10 Known Debt).
- Does **not** add a new `rddf-session` hook. The menu item rides the existing arch session binding (ADR-0017).

---

## 2. Decision

Add an `add-feature` operation primitive as a `rddf roadmap` subcommand (mirroring the existing `migrate` and `validate-fragments` subcommands) and wire it as a Phase 4 menu option in `guide-arch`. The primitive uses the **Fragment model** (not the legacy flat model used by `add_phase`) and produces:

1. A new file `.rddf/roadmap/features/feat-<name>.md` with frontmatter + 3-section body skeleton
2. A refreshed `.rddf/roadmap.md` AUTO-INDEX block (via `render_fragment_index`)

The CLI body is shell-only (parameter parsing + env-var passing), following Oracle C1 env-var injection security pattern. The actual work lives in Python (`_lib/roadmap_state.py::add_feature`) so unit testing is straightforward.

---

## 3. Architecture (4 Layers)

```
┌─────────────────────────────────────────────────────────────────────┐
│ UI Layer                                                            │
│   skills/guide-arch/SKILL.md Phase 4 menu                           │
│     └─ option "添加 feature" → delegates to roadmap skill           │
│   skills/roadmap/SKILL.md → subcommand documentation                │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CLI Layer                                                           │
│   skills/roadmap/scripts/roadmap_add_feature.sh  (NEW, thin shell)  │
│     └─ parses args, exports env vars, calls Python                   │
│   _lib/cli/roadmap_cmd.py  (extend _SUBCOMMAND_MAP)                 │
│     └─ add-feature → roadmap_add_feature.sh                         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Library Layer (reused + new)                                        │
│   _lib/roadmap_state.py::add_feature  (NEW)                         │
│     ├─ mkdir features/ (idempotent)                                 │
│     ├─ validate_fragment_refs (R1)                                  │
│     ├─ atomic write features/feat-<name>.md                         │
│     ├─ render_fragment_index (refresh main doc)                     │
│     └─ compensating rollback if render fails                        │
│   + reuse list_active_fragments / load_fragments /                  │
│     validate_fragment_refs / render_fragment_index                  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Filesystem (all paths tracked, none gitignored)                     │
│   .rddf/roadmap/features/feat-<name>.md   (atomic write)            │
│   .rddf/roadmap.md                       (atomic write via sentinel)│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. CLI Interface

### 4.1 Subcommand registration

Extend `_lib/cli/roadmap_cmd.py::_SUBCOMMAND_MAP`:

```python
_SUBCOMMAND_MAP = {
    "migrate": project_root / "skills" / "roadmap" / "scripts" / "roadmap_migrate.sh",
    "validate-fragments": project_root / "skills" / "roadmap" / "scripts" / "roadmap_validate_fragments.sh",
    "add-feature": project_root / "skills" / "roadmap" / "scripts" / "roadmap_add_feature.sh",  # NEW
}
```

Update `_help_text()` to include the new subcommand.

### 4.2 Invocation

```bash
rddf roadmap add-feature <name> [options]

Arguments:
  <name>                      kebab-case feature id (CLI auto-prepends: feat-<name>)
                              Non-empty; kebab-case regex validated.

Options:
  --phase-refs <p1,p2,...>    Required. Comma-separated phase IDs.
                              Each ID validated against list_active_fragments(kind="phase").
                              Invalid → exit 1, stderr lists unknown IDs.
  --theme "<text>"            Required. Single-line 主题 (CJK ok).
  --status <a|d|x>            Optional. Default: a (active).
  --force                     Optional. Fully regenerates frontmatter + body skeleton
                              (destroys any user-edited body content).
                              Without --force, existing feat-<name>.md → exit 1.

Exit codes:
  0   success
  1   validation error (unknown phase_refs / duplicate without --force)
  2   usage error (missing required arg / malformed flag)
  3   script not found (matches existing dispatch convention)
```

### 4.3 Body content policy (MVP scope)

The MVP **generates a skeleton only**. The CLI does not accept body content as flags. Body content is filled by users/agents post-creation.

Skeleton structure (auto-generated from `--phase-refs`):

```markdown
## 概述
<TBD - 用户后续编辑>

## 跨阶段拆分

### phase-2
<TBD - 此阶段内的子任务清单>

### phase-3
<TBD - 此阶段内的子任务清单>

## 验收标准
<TBD - markdown checkbox 列表, design/plan 阶段消费>
```

Rationale: accepting body via flags would explode the CLI surface (overview, criteria list, per-phase sub-content). Users are expected to invoke this once per feature, then edit the markdown directly. Future "edit-feature" subcommand (out of scope) would address post-edit flows.

---

## 5. Frontmatter Schema

```yaml
---
id: feat-<name>             # auto-generated, kebab-case
kind: feature               # fixed literal
status: <active|done|archived>
phase_refs: [phase-2, phase-3]   # required, ≥ 1 element, all validated
主题: <single-line>                # required (CJK short phrase, spaces allowed)
---
```

### 5.1 Validation rules

- `id` — derived from `<name>` arg; CLI enforces `^[a-z][a-z0-9-]*$`.
- `kind` — always `feature`.
- `status` — default `active`; CLI accepts `a`/`d`/`x` short forms, expanded to `active`/`done`/`archived`.
- `phase_refs` — list of phase IDs; each must exist in `list_active_fragments(kind="phase")` (single read path; no direct directory scanning). Empty list rejected.
- `主题` — non-empty single line (no embedded newlines).

---

## 6. Atomicity & Error Handling

### 6.1 Write sequence

1. `mkdir -p .rddf/roadmap/features/` (idempotent; safe if exists)
2. `validate_fragment_refs` pre-check on proposed frontmatter → exit 1 on invalid
3. If `feat-<name>.md` exists and no `--force` → exit 1
4. Atomic write fragment: `tmp file + os.replace()` (existing pattern in `render_fragment_index`)
5. `render_fragment_index(.rddf/roadmap, .rddf/roadmap.md)` — re-reads fragment dir, idempotent
6. **Compensating rollback**: if step 5 raises, delete step 4 fragment file → exit 1

### 6.2 Failure semantics

| Failure point | State after | User-visible signal |
|---|---|---|
| mkdir fails (permissions) | no fragment written | stderr + exit 1 |
| phase_refs invalid | no fragment written | stderr lists invalid IDs + exit 1 |
| atomic write fails (disk full) | tmp cleaned via `trap` | stderr + exit 1 |
| render_fragment_index fails | fragment deleted | stderr + exit 1 ("compensation: fragment removed") |
| `--force` overwrite | old content destroyed, new written | stdout "✅ regenerated" |

### 6.3 Idempotency guarantee

`render_fragment_index` is already idempotent (verified by Oracle review: SENTINEL strip + rebuild). Calling `add-feature` twice with same args produces same `.rddf/roadmap.md` content; calling twice with `--force` is safe.

---

## 7. Testing (11 cases)

### 7.1 Python unit (7 tests, extend `tests/unit/test_roadmap_state.py`)

| # | Test | Assertion |
|---|---|---|
| 1 | `test_add_feature_creates_file_with_frontmatter` | frontmatter keys exactly match §5 schema |
| 2 | `test_add_feature_validates_phase_refs` | unknown phase id → no file written, exit 1 |
| 3 | `test_add_feature_rejects_duplicate_id` | existing fragment without `--force` → no overwrite, exit 1 |
| 4 | `test_add_feature_force_regenerates` | with `--force`, old content fully replaced |
| 5 | `test_add_feature_renders_auto_index` | main doc gains Features section after success |
| 6 | `test_add_feature_mkdir_features_dir` | missing `features/` → auto-created |
| 7 | `test_load_fragments_missing_subdir_tolerance` | `features/` missing → `load_fragments` returns empty list (regression lock) |

### 7.2 Bats integration (4 tests, new `tests/integration/test_roadmap_add_feature.bats`)

| # | Test | Assertion |
|---|---|---|
| 8 | `test_cli_end_to_end_creates_fragment` | `rddf roadmap add-feature auth-v2 --phase-refs phase-1 --theme "..."` creates file |
| 9 | `test_menu_option_in_guide_arch_phase4` | `guide-arch/SKILL.md` Phase 4 menu contains "添加 feature" string |
| 10 | `test_auto_index_idempotent` | call twice with same args → main doc identical (byte-equal) |
| 11 | `test_compensating_rollback_on_render_failure` | mock `render_fragment_index` to raise → fragment file removed |

### 7.3 Coverage target

Maintain project's existing floor: every Python helper ≥ 6 unit tests; every shell wrapper ≥ 4 bats tests. This spec stays at 7+4 = 11 (above floor).

---

## 8. ADR & Documentation

### 8.1 ADR

**No new ADR required.** This change is the operation primitive for `add-hierarchical-roadmap-structure` "scenario 3" (manual cross-stage feature creation), whose architecture decision was already adopted in that proposal.

### 8.2 ADR-0028 patch (1-line frontmatter update)

File: `skills/guide-arch/SKILL.md` frontmatter `role.boundaries.owns` list.

Add: `- ".rddf/roadmap/features/*.md"` (alongside existing `.rddf/roadmap/phases/*.md`).

This documents the ownership boundary explicitly. Already allowed by the role's intent (Phase 4 roadmap-define), but was missing from the frontmatter list.

### 8.3 Documentation updates

| File | Change |
|---|---|
| `skills/guide-arch/SKILL.md` | Phase 4 menu adds option "✨ 添加 feature fragment"; new sub-section documenting 4-step interaction |
| `skills/roadmap/SKILL.md` | New subcommand section "add-feature <name>" with CLI usage + 3 examples |
| `skills/roadmap/scripts/_help_text` (in `roadmap_cmd.py`) | Update help text to include `add-feature` |
| `CHANGELOG.md` | v2.2+ entry noting new feature |
| `README.md` | Roadmap section: link to add-feature subcommand |
| `docs/adr/README.md` (optional) | Brief note that hierarchical roadmap operation surface is now complete |

---

## 9. SKILL.md Interaction Contract

### 9.1 guide-arch Phase 4 menu (new option)

Insert after option 4 (强制推进到下一阶段), before option 5 (完成路线图定义 → 进入 arch validation):

```
5. ✨ 添加 feature fragment
```

### 9.2 Trigger sequence (4 mandatory steps)

When user selects option 5, the skill runs this sequence (one step fails → return to menu, no write):

1. **Input `name`** — `kebab-case` regex enforced; non-empty; auto-prefix `feat-` shown in preview.
2. **Input `theme`** — single-line CJK short phrase (≤ 50 chars); non-empty.
3. **Multi-select `phase_refs`** — render numbered list from `list_active_fragments(kind="phase")`; user enters comma-separated indices; resolve to phase IDs; validate each exists.
4. **Preview + confirm** — render full frontmatter + 3-section body to stderr; user types `y` to write, anything else returns to menu.

### 9.3 roadmap SKILL.md subcommand section

One-paragraph purpose + CLI usage block + 3 examples:

```bash
# Minimal: create an active feature spanning phase-2 and phase-3
rddf roadmap add-feature auth-v2 \
    --phase-refs phase-2,phase-3 \
    --theme "RBAC 权限模型"

# Mark as done at creation (rare)
rddf roadmap add-feature deprecate-legacy-auth \
    --phase-refs phase-3 \
    --theme "下线旧版认证" \
    --status d

# Overwrite an existing fragment (destroys body edits)
rddf roadmap add-feature auth-v2 \
    --phase-refs phase-2,phase-3 \
    --theme "RBAC 权限模型 (v2 重生)" \
    --force
```

---

## 10. Known Debt (NOT fixed in this change)

### 10.1 `add_phase` flat model dual track

`_lib/roadmap_state.py::add_phase` (L268) still uses the **legacy flat model**:

- Appends section to `roadmap.md` directly
- Updates `roadmap-state.json`

This is **incompatible** with the Fragment model used by `add-feature`. Two consequences:

1. Existing `roadmap edit` → "添加新阶段" workflow continues to bypass the Fragment system.
2. `validate_fragment_refs` will not catch phase IDs that exist only via the flat `roadmap.md` section.

**This change does NOT touch `add_phase`.** Reason: refactoring `add_phase` requires understanding its current call sites and the `roadmap-state.json` schema, which is a separate scoping exercise.

**Recommended follow-up**: file a separate `add-improve` proposal "重构 add_phase 为 Fragment 模型" with its own ADR candidate (potential ADR-0034).

**No code TODO added** — per Oracle review, comments decay; defer to the proposal system.

---

## 11. Implementation Effort Estimate

| Component | Effort | Lines (approx) |
|---|---|---|
| `roadmap_state.py::add_feature` (Python) | S | +90 |
| `roadmap_add_feature.sh` (shell wrapper) | S | +40 |
| `roadmap_cmd.py` dispatch + help | XS | +5 |
| `guide-arch/SKILL.md` Phase 4 menu | XS | +30 |
| `roadmap/SKILL.md` subcommand docs | XS | +25 |
| ADR-0028 patch | XS | +1 |
| Unit tests (7) | M | +200 |
| Bats tests (4) | M | +120 |
| **Total** | **Medium-low** | **~510 LOC** |

**Ordering** (no inter-component dependencies beyond what §6 specifies):
1. `_lib/roadmap_state.py::add_feature` (Python core)
2. `tests/unit/test_roadmap_state.py` extension (7 cases)
3. `skills/roadmap/scripts/roadmap_add_feature.sh` (thin shell)
4. `_lib/cli/roadmap_cmd.py` dispatch + help
5. `tests/integration/test_roadmap_add_feature.bats` (4 cases)
6. `skills/guide-arch/SKILL.md` Phase 4 menu option
7. `skills/roadmap/SKILL.md` subcommand docs
8. ADR-0028 patch
9. CHANGELOG / README updates

---

## 12. Acceptance Criteria

The change is complete when:

- [ ] `rddf roadmap add-feature <name> --phase-refs ... --theme ...` creates a fragment file with valid frontmatter
- [ ] `.rddf/roadmap.md` AUTO-INDEX block gains a Features entry after success
- [ ] Invalid `--phase-refs` exit 1 without writing any file
- [ ] Re-running with same args is byte-equal idempotent
- [ ] `--force` fully regenerates (no merge of existing body)
- [ ] Render failure triggers compensating deletion of fragment
- [ ] `guide-arch` Phase 4 menu shows "添加 feature" option with 4-step flow
- [ ] `rddf roadmap --help` lists `add-feature` subcommand
- [ ] All 11 tests pass (`./test.sh --python` + `bats tests/integration/test_roadmap_add_feature.bats`)
- [ ] ADR-0028 frontmatter includes `.rddf/roadmap/features/*.md`
- [ ] No regression in existing 140 arch/ADR tests

---

## 13. Out of Scope (Future Work)

- `rddf roadmap edit-feature` subcommand (post-creation editing)
- `rddf roadmap archive-feature` subcommand (lifecycle end)
- `rddf roadmap delete-feature` subcommand (destructive)
- `feature.md` skill view enhancement (read fragment for theme/phase_refs enrichment)
- `feature_ref` field in `roadmap-meta.yaml` (binds change to feature fragment)
- `add_phase` refactor to Fragment model (potential ADR-0034)
- Hierarchical feature nesting (`features/auth-v2/sso.md`)

---

## References

- `_lib/roadmap_state.py` — Fragment dataclass + 6 additive APIs
- `.rddf/improvements/add-hierarchical-roadmap-structure.md` — Parent proposal (shipped 2026-08-20)
- `_lib/cli/roadmap_cmd.py` — Existing dispatch map pattern
- `docs/adr/ADR-0003-three-phase-architecture.md` — Phase architecture
- `docs/adr/ADR-0016-arch-artifact-discovery-contract.md` — Discovery pattern
- `docs/adr/ADR-0028-role-model-per-phase.md` — Role boundaries
- `skills/roadmap/scripts/roadmap_migrate.sh` — Shell wrapper reference
- `skills/roadmap/scripts/roadmap_validate_fragments.sh` — Shell wrapper reference
- Oracle first-round review (bg_03696e35): position + content model decisions
- Oracle second-round review (bg_b16179e9): atomicity + SKILL.md contract + Known Debt
