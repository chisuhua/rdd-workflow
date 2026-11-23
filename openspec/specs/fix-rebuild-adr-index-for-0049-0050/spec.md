# fix-rebuild-adr-index-for-0049-0050 Specification

## Purpose
TBD - created by archiving change fix-rebuild-adr-index-for-0049-0050. Update Purpose after archive.
## Requirements
### Requirement: fix-rebuild-adr-index-for-0049-0050

The Wave 1 fix proposal `fix-rebuild-adr-index-for-0049-0050` MUST satisfy all Acceptance checkboxes listed in `openspec/changes/fix-rebuild-adr-index-for-0049-0050/proposal.md` ## Acceptance section. Each Scenario below mirrors one Acceptance checkbox and MUST be verifiable via `openspec change validate fix-rebuild-adr-index-for-0049-0050` and the corresponding pytest/grep test run.

#### Scenario: pytest-tests-unit-test-adr-index-gate-py-test-adr-numbering

GIVEN the Wave 1 fix proposal `fix-rebuild-adr-index-for-0049-0050` is being implemented
WHEN the developer executes ``pytest tests/unit/test_adr_index_gate.py::test_adr_numbering_is_unique` 通过`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-rebuild-adr-index-for-0049-0050` and the corresponding pytest test run)

#### Scenario: pytest-tests-unit-test-adr-index-gate-py-test-readme-index

GIVEN the Wave 1 fix proposal `fix-rebuild-adr-index-for-0049-0050` is being implemented
WHEN the developer executes ``pytest tests/unit/test_adr_index_gate.py::test_readme_index_matches_generator_output` 通过`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-rebuild-adr-index-for-0049-0050` and the corresponding pytest test run)

#### Scenario: readme-commit

GIVEN the Wave 1 fix proposal `fix-rebuild-adr-index-for-0049-0050` is being implemented
WHEN the developer executes `README 顶部"上次同步"注释更新到当前 commit`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-rebuild-adr-index-for-0049-0050` and the corresponding pytest test run)

#### Scenario: grep-adr-0049-adr-0050-docs-adr-readme-md-1

GIVEN the Wave 1 fix proposal `fix-rebuild-adr-index-for-0049-0050` is being implemented
WHEN the developer executes ``grep "ADR-0049\|ADR-0050" docs/adr/README.md` 至少各匹配 1 行`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-rebuild-adr-index-for-0049-0050` and the corresponding pytest test run)

#### Scenario: git-diff-docs-adr-readme-md

GIVEN the Wave 1 fix proposal `fix-rebuild-adr-index-for-0049-0050` is being implemented
WHEN the developer executes ``git diff docs/adr/README.md` 仅显示新增行(无删除/修改现有行)`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-rebuild-adr-index-for-0049-0050` and the corresponding pytest test run)

