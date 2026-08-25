## Implementation Tasks

> 实施顺序参考 `docs/superpowers/specs/2026-08-25-add-feature-fragment-command-design.md` §11。Task 1-7 顺序强依赖；Task 8-9 可并行。

### Phase A: Core Library (顺序)

- [x] **T1** Implement `add_feature(name, phase_refs, theme, status, force, project_root)` in `_lib/roadmap_state.py`
      - Read single source of truth: `list_active_fragments(kind="phase")` for phase_refs validation
      - Build frontmatter dict with `id: feat-<name>`, `kind: feature`, `status`, `phase_refs`, `主题`
      - Render 3-section body skeleton (概述 / 跨阶段拆分 / 验收标准)
      - Atomic write: tmp file + `os.replace`
      - Call `render_fragment_index` to refresh `.rddf/roadmap.md`
      - Compensating rollback: if render raises, delete just-written fragment
      - Return dict with `path`, `main_doc_refreshed` keys

- [x] **T2** Add `mkdir features/` step before fragment write (idempotent)
      - Use `os.makedirs(features_dir, exist_ok=True)`
      - Ensure `load_fragments` tolerates missing subdir (regression lock test #7)

- [x] **T3** Validate `phase_refs` via `validate_fragment_refs` (single source of truth: `list_active_fragments(kind="phase")`)
      - Empty list → reject exit 1
      - Each ID must exist → otherwise reject exit 1 with stderr listing invalid IDs

- [x] **T4** Implement duplicate detection (`feat-<name>.md` exists)
      - Without `--force` → reject exit 1, stderr "feat-<name>.md exists, use --force"
      - With `--force` → full regenerate (no merge)

- [x] **T5** Implement `--force` semantics
      - Overwrite both frontmatter and body skeleton
      - No merge of existing user-edited body
      - Document this behavior in `--help` text

### Phase B: Shell Wrapper + CLI Dispatch

- [x] **T6** Create `skills/roadmap/scripts/roadmap_add_feature.sh`
      - Parse CLI args: `--name`, `--phase-refs`, `--theme`, `--status`, `--force`
      - Export env vars to Python: `PROJECT_ROOT`, `CHANGE_NAME`, `PHASE_REFS`, `THEME`, `STATUS`, `FORCE`
      - Call `_lib/roadmap_state.py::add_feature` via Python
      - Follow Oracle C1: NO inline `python3 -c "...$VAR..."` interpolation
      - Exit codes: 0 success / 1 validation / 2 usage / 3 script-not-found (matches existing dispatch)

- [x] **T7** Extend `_lib/cli/roadmap_cmd.py::_SUBCOMMAND_MAP`
      - Add `add-feature` entry pointing to `roadmap_add_feature.sh`
      - Update `_help_text()` to document `add-feature` subcommand
      - Verify exit code propagation works end-to-end

### Phase C: SKILL.md Integration

- [x] **T8** Update `skills/guide-arch/SKILL.md`
      - Add "添加 feature fragment" option to Phase 4 menu (between option 4 and 5)
      - Document 4-step forced interaction: name → theme → phase_refs multi-select → preview+confirm
      - Add frontmatter `role.boundaries.owns: [.rddf/roadmap/phases/*.md, .rddf/roadmap/features/*.md]` (ADR-0028 patch)

- [x] **T9** Update `skills/roadmap/SKILL.md`
      - Add `add-feature` subcommand section
      - Document CLI usage + 3 examples (minimal / done status / force)
      - Reference `_lib/roadmap_state.py::add_feature` as the Python core contract

### Phase D: Tests

- [x] **T10** Add 7 unit tests in `tests/unit/test_roadmap_state.py`
      - `test_add_feature_creates_file_with_frontmatter` (frontmatter keys match schema)
      - `test_add_feature_validates_phase_refs` (unknown phase → exit 1, no file written)
      - `test_add_feature_rejects_duplicate_id` (no `--force` → exit 1, no overwrite)
      - `test_add_feature_force_regenerates` (with `--force`, old content replaced)
      - `test_add_feature_renders_auto_index` (main doc gains Features section)
      - `test_add_feature_mkdir_features_dir` (missing `features/` → auto-created)
      - `test_load_fragments_missing_subdir_tolerance` (regression lock for missing subdir)

- [x] **T11** Add 4 bats tests in `tests/integration/test_roadmap_add_feature.bats`
      - `test_cli_end_to_end_creates_fragment` (rddf roadmap add-feature happy path)
      - `test_menu_option_in_guide_arch_phase4` (SKILL.md contains "添加 feature")
      - `test_auto_index_idempotent` (call twice → main doc byte-equal)
      - `test_compensating_rollback_on_render_failure` (mock render raise → fragment removed)

### Phase E: Documentation

- [x] **T12** Update `CHANGELOG.md` v2.2+ entry noting new feature
- [x] **T13** Update `README.md` Roadmap section linking to `add-feature` subcommand
- [x] **T14** Update `skills/guide-design/scripts/approve_proposal.sh` (P1 bug fix)
      - Replace 4-line `.openspec.yaml` heredoc (name + created_by) with `schema: spec-driven` + `created: <date>` + `name: <name>` (matches openspec CLI v1.7+ format)
      - This prevents future approved proposals from being misread by `openspec instructions` (which expects schema field)

### Phase F: Validation

- [x] **T15** Run `./test.sh --python` and `./test.sh --bats tests/integration/test_roadmap_add_feature.bats`
      - All 11 new tests pass
      - No regression in existing 140 tests

- [x] **T16** Run `openspec validate add-feature-fragment-command --type change --strict`
      - No errors
      - Confirms specs/design/tasks all valid

- [x] **T17** Smoke test: `rddf roadmap add-feature smoke-test --phase-refs phase-1 --theme "smoke"`
      - Verify `.rddf/roadmap/features/feat-smoke-test.md` created
      - Verify `.rddf/roadmap.md` AUTO-INDEX updated
      - Verify idempotency: same args twice → no diff
      - Cleanup: `rm .rddf/roadmap/features/feat-smoke-test.md && rddf roadmap validate-fragments` (rebuild AUTO-INDEX)
