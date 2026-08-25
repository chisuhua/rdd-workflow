# roadmap-feature-fragment Specification

## Purpose
TBD - created by archiving change add-feature-fragment-command. Update Purpose after archive.
## Requirements
### Requirement: roadmap add-feature CLI

The system SHALL provide a `rddf roadmap add-feature <name>` CLI subcommand that creates a new feature fragment in `.rddf/roadmap/features/feat-<name>.md` with valid frontmatter and refreshes the main roadmap document's AUTO-INDEX block.

#### Scenario: Successful creation
- **WHEN** the user invokes `rddf roadmap add-feature auth-v2 --phase-refs phase-2,phase-3 --theme "RBAC 权限模型"` with valid arguments
- **THEN** the system creates `.rddf/roadmap/features/feat-auth-v2.md` containing the frontmatter (id, kind=feature, status, phase_refs, 主题) and a 3-section body skeleton (概述 / 跨阶段拆分 / 验收标准)
- **AND** the system refreshes `.rddf/roadmap.md` so its `<!-- AUTO-INDEX -->` block now lists the new feature under the Features section
- **AND** the system exits with code 0

#### Scenario: Invalid phase_refs rejected
- **WHEN** the user invokes add-feature with a `--phase-refs` value containing a phase id that does not exist in `list_active_fragments(kind="phase")`
- **THEN** the system writes no files
- **AND** the system writes a stderr message listing the invalid phase ids
- **AND** the system exits with code 1

#### Scenario: Duplicate without --force rejected
- **WHEN** the user invokes add-feature for a name whose `feat-<name>.md` already exists
- **AND** the `--force` flag is NOT provided
- **THEN** the system writes no files
- **AND** the system writes a stderr message recommending `--force`
- **AND** the system exits with code 1

#### Scenario: --force fully regenerates
- **WHEN** the user invokes add-feature with `--force` for an existing `feat-<name>.md`
- **THEN** the system replaces the existing file with a fresh frontmatter + body skeleton (destroying any user-edited body content)
- **AND** the system refreshes AUTO-INDEX
- **AND** the system exits with code 0

#### Scenario: Missing features/ directory auto-created
- **WHEN** the user invokes add-feature and `.rddf/roadmap/features/` does not yet exist
- **THEN** the system creates the directory before writing the fragment
- **AND** the system creates the fragment and refreshes AUTO-INDEX as in the success scenario

#### Scenario: features/ subdirectory absence tolerated
- **WHEN** any code path calls `load_fragments(<fragments_dir>)` or `render_fragment_index(<fragments_dir>, <main_doc>)` while `.rddf/roadmap/features/` does not exist
- **THEN** the system returns an empty fragment list (or an unchanged main document) without raising
- **AND** no file system error is raised for the missing subdirectory

### Requirement: Fragment frontmatter validation

The system SHALL validate frontmatter fields before writing the fragment: `id` must be kebab-case (CLI auto-prepends `feat-`), `kind` is fixed as `feature`, `status` is one of `active`/`done`/`archived`, `phase_refs` is a non-empty list whose elements all exist as active phase fragments, and `主题` is a non-empty single-line string.

#### Scenario: Empty phase_refs rejected
- **WHEN** the user invokes add-feature with `--phase-refs ""` (empty list)
- **THEN** the system rejects the call with exit code 1
- **AND** the stderr message indicates phase_refs must be non-empty

#### Scenario: phase_refs validated against active phases
- **WHEN** the user invokes add-feature with `--phase-refs phase-2,phase-99`
- **THEN** the system resolves each id via `list_active_fragments(kind="phase")`
- **AND** the system rejects the call (exit 1) if any id is missing
- **AND** the system accepts the call (exit 0) only if all ids resolve

### Requirement: Atomic write with compensating rollback

The system SHALL perform fragment writes atomically (temp file + rename) and, if the subsequent `render_fragment_index` call fails, SHALL delete the just-written fragment to avoid orphan fragments that are not reflected in AUTO-INDEX.

#### Scenario: Successful atomic write
- **WHEN** add-feature validates inputs successfully and proceeds to write
- **THEN** the system writes to a temporary file in the same directory
- **AND** uses `os.replace` to atomically swap into the final filename
- **AND** trap-based cleanup removes the temp file if the swap fails

#### Scenario: Render failure triggers compensating deletion
- **WHEN** the fragment file was written successfully
- **AND** the `render_fragment_index` call subsequently raises (mocked or real failure)
- **THEN** the system deletes the just-written fragment file
- **AND** the system exits with code 1
- **AND** the stderr message states "compensation: fragment removed"

#### Scenario: Idempotent re-run produces byte-equal AUTO-INDEX
- **WHEN** the user runs add-feature twice with identical arguments
- **THEN** the second run produces the same `.rddf/roadmap.md` content as the first (byte-equal) because `render_fragment_index` strips any previous AUTO-INDEX block and rebuilds deterministically

### Requirement: guide-arch Phase 4 menu integration

The `guide-arch` skill's Phase 4 menu SHALL include an "添加 feature fragment" option that, when selected, runs a 4-step interaction (input name, input theme, multi-select phase_refs, preview+confirm) and delegates to `rddf roadmap add-feature`.

#### Scenario: Menu option present in Phase 4
- **WHEN** a user invokes `guide-arch` and reaches Phase 4 (roadmap-define)
- **THEN** the menu displays an "添加 feature fragment" option alongside the existing roadmap operations

#### Scenario: 4-step interaction enforces validation
- **WHEN** the user selects the "添加 feature fragment" option
- **THEN** the skill prompts sequentially for (1) feature name, (2) theme, (3) phase_refs selection from the existing phases, (4) preview+confirm
- **AND** each step's failure (empty input, invalid phase id, user rejects preview) returns to the menu without writing any file
- **AND** only step 4 confirmation writes the fragment via `rddf roadmap add-feature`

### Requirement: ADR-0028 role boundary extension

The `skills/guide-arch/SKILL.md` frontmatter `role.boundaries.owns` list SHALL explicitly include `.rddf/roadmap/features/*.md` alongside the existing `.rddf/roadmap/phases/*.md` entry, documenting that arch-phase guide-arch owns feature fragment files.

#### Scenario: Frontmatter contains features ownership
- **WHEN** the updated `skills/guide-arch/SKILL.md` is loaded
- **THEN** the `role.boundaries.owns` YAML list contains the string `.rddf/roadmap/features/*.md`

