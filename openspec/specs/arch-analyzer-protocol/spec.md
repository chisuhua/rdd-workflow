# arch-analyzer-protocol Specification

## Purpose
TBD - created by archiving change arch-analyzer-protocol. Update Purpose after archive.
## Requirements
### Requirement: arch-analyzer protocol data layer
A pure-Python data layer at `_lib/arch/protocol.py` MUST export three functions (`build_skeleton`, `validate_document`, `list_analyses`) and a `ValidationReport` dataclass.

#### Scenario: build_skeleton produces 5-section markdown
- **WHEN** `build_skeleton("test-slug", "2026-09-07")` is called
- **THEN** the output MUST contain a level-2 heading `## 1. 目标架构`
- **AND** `## 2. 当前架构`, `## 3. 差距清单`, `## 4. 补齐路径`, `## 5. 参考资料`
- **AND** the title line MUST be `# 架构差距分析: test-slug`
- **AND** the header MUST include `**生成日期**: 2026-09-07`

#### Scenario: validate_document detects 5-section structure
- **WHEN** `validate_document(path)` is called on a file containing all 5 sections
- **THEN** `structural_ok` MUST be `True`
- **AND** `issues` MUST be empty for structural problems

#### Scenario: validate_document flags broken structure
- **WHEN** `validate_document(path)` is called on a file where one section header is changed from `##` to `###`
- **THEN** `structural_ok` MUST be `False`
- **AND** `issues` MUST contain the missing section name

#### Scenario: validate_document classifies completeness
- **WHEN** `validate_document(path)` is called on a file with all `(待补充)` placeholders intact
- **THEN** `completeness` MUST be `"draft"`
- **WHEN** called on a file with no placeholders
- **THEN** `completeness` MUST be `"complete"`
- **WHEN** called on a file with some placeholders filled
- **THEN** `completeness` MUST be `"partial"`

#### Scenario: validate_document rejects non-kebab slug
- **WHEN** `build_skeleton("BadSlug", "")` is called
- **THEN** the function MUST raise `ValueError` with a message containing "kebab-case"

#### Scenario: list_analyses returns sorted paths
- **WHEN** `list_analyses(arch_dir)` is called on a directory containing `b-gap-analysis.md`, `a-gap-analysis.md`, `c-gap-analysis.md`
- **THEN** the returned list MUST be `[a-gap-analysis.md, b-gap-analysis.md, c-gap-analysis.md]`
- **AND** non-matching files (no `-gap-analysis.md` suffix) MUST NOT be returned

#### Scenario: list_analyses on empty directory
- **WHEN** `list_analyses(empty_dir)` is called
- **THEN** the returned list MUST be empty

### Requirement: arch_gap_analysis.sh wrapper contract preservation
The bash wrapper MUST preserve the exact observable contract of the pre-refactor implementation so all 8 existing bats tests pass unmodified.

#### Scenario: generate_gap_analysis creates the expected file
- **WHEN** `generate_gap_analysis "test-slug"` is called with `PROJECT_ROOT` unset and cwd set to a tmpdir containing `docs/architecture/`
- **THEN** the file `tmpdir/docs/architecture/test-slug-gap-analysis.md` MUST be created
- **AND** the file MUST contain `目标架构`, `当前架构`, `差距清单`, `补齐路径`, `参考资料` substrings

#### Scenario: generate_gap_analysis errors on empty slug
- **WHEN** `generate_gap_analysis ""` is called
- **THEN** stdout MUST contain `❌ 主题不能为空`
- **AND** the exit code MUST be non-zero

#### Scenario: generate_gap_analysis errors on existing file
- **WHEN** `generate_gap_analysis "existing"` is called when `existing-gap-analysis.md` already exists
- **THEN** stdout MUST contain `❌ 差距分析已存在`
- **AND** the exit code MUST be non-zero

#### Scenario: list_gap_analyses handles empty dir
- **WHEN** `list_gap_analyses` is called in an empty `docs/architecture/`
- **THEN** stdout MUST contain `⚠️  暂无差距分析`
- **AND** the exit code MUST be non-zero (test 7 uses `|| true`)

#### Scenario: list_gap_analyses finds existing
- **WHEN** `list_gap_analyses` is called when 2 gap analyses exist
- **THEN** stdout MUST contain both slugs
- **AND** the exit code MUST be zero

#### Scenario: DISCOVERED_ARCHITECTURE_DIR honored
- **WHEN** `generate_gap_analysis "test"` is called with `DISCOVERED_ARCHITECTURE_DIR=custom/architecture` env var
- **THEN** the file MUST be created at `<project_root>/custom/architecture/test-gap-analysis.md`

### Requirement: SKILL.md § Arch Gap Analysis Protocol block
`skills/rdd-arch/SKILL.md` MUST contain a `## Arch Gap Analysis Protocol` section that documents the gap analysis protocol and references `_lib/arch/protocol.py`.

#### Scenario: § Protocol section exists
- **WHEN** the SKILL.md is read
- **THEN** it MUST contain a `## Arch Gap Analysis Protocol` heading
- **AND** that section MUST reference `_lib/arch/protocol.py`
- **AND** that section MUST list the 5 markdown sections (目标架构 / 当前架构 / 差距清单 / 补齐路径 / 参考资料)

#### Scenario: frontmatter protocol_inline marker
- **WHEN** the SKILL.md frontmatter is read
- **THEN** `metadata.protocol_inline` MUST be `true`
- **AND** `metadata.protocol_data_layer` MUST be `"_lib/arch/protocol.py"`
- **AND** `metadata.protocol_context_file` MUST NOT be set (Analyzer Subset does not stage context)
- **AND** `metadata.protocol_cache_file` MUST NOT be set (Analyzer Subset has no SHA-bound cache)

### Requirement: cross-stage protocol template renamed
The cross-stage protocol template spec MUST be renamed from `verifier-protocol-template.md` to `cross-stage-protocol-template.md` and MUST document both the Verifier Subset (full 5 sections) and Analyzer Subset (sections 1/2/5-validated).

#### Scenario: filename renamed
- **WHEN** the spec directory is enumerated
- **THEN** `verifier-protocol-template.md` MUST NOT exist
- **AND** `cross-stage-protocol-template.md` MUST exist

#### Scenario: Analyzer Subset section exists
- **WHEN** `cross-stage-protocol-template.md` is read
- **THEN** it MUST contain a heading `### Analyzer Subset` (or equivalent)
- **AND** that section MUST declare `protocol_output_contract: true` as the analyzer-specific marker
- **AND** that section MUST enumerate which sections apply (1, 2, 5-validated) and which are skipped (3, 4) with one-sentence justifications

#### Scenario: Verifier Subset retained
- **WHEN** `cross-stage-protocol-template.md` is read
- **THEN** it MUST contain the full 5-section Verifier Subset description
- **AND** the Verifier Subset MUST NOT be removed

#### Scenario: Adoption Decision updated
- **WHEN** the `## Adoption Decision` section is read
- **THEN** it MUST reference `arch gap analysis` and `ADR-0046` as the first落地
- **AND** it MUST NOT say "tracked as future" for gap analysis

### Requirement: ADR-0046 documents the subset adoption
`docs/adr/ADR-0046-arch-analyzer-protocol-subset.md` MUST exist and document the gap analysis protocol subset adoption.

#### Scenario: ADR-0046 exists with status
- **WHEN** `docs/adr/ADR-0046-arch-analyzer-protocol-subset.md` is read
- **THEN** it MUST have a status line "Status: 已采纳 (2026-XX-XX)"
- **AND** it MUST reference ADR-0045 + the renamed template spec
- **AND** it MUST declare the Oracle session id `ses_f84cabe64ffeBiz3XzHmFSSznc`

#### Scenario: ADR-0046 enumerates per-section decisions
- **WHEN** the ADR is read
- **THEN** it MUST enumerate §1 ADOPT / §2 ADOPT / §3 SKIP / §4 SKIP / §5 REPURPOSE with one-sentence justification per item

#### Scenario: ADR-0046 declares arch-done wiring out-of-scope
- **WHEN** the ADR is read
- **THEN** it MUST contain an "Out of Scope" section that explicitly defers wiring `validate_document` into `rdd-arch/SKILL.md` Phase 5 arch-done gate to a future change

### Requirement: regression zero new failures
`./test.sh --full --regression` MUST report 0 new bats failures.

#### Scenario: existing 8 bats pass unmodified
- **WHEN** `tests/integration/test_arch_gap_analysis_extraction.bats` is run against the new wrapper
- **THEN** all 8 existing cases MUST pass (proves the wrapper contract is byte-identical)

#### Scenario: new bats + unit tests pass
- **WHEN** `tests/unit/test_arch_protocol.py` + `tests/integration/test_arch_gap_analysis_extraction.bats` are run together
- **THEN** all cases MUST pass (8 existing + 3 new unit + 3 new bats)

#### Scenario: regression baseline preserved
- **WHEN** `./test.sh --full --regression` is run
- **THEN** the report MUST show "新增失败: 0" or "✅ 0 新增失败"

