# fix-update-doctor-main-category-count Specification

## Purpose
TBD - created by archiving change fix-update-doctor-main-category-count. Update Purpose after archive.
## Requirements
### Requirement: fix-update-doctor-main-category-count

The Wave 1 fix proposal `fix-update-doctor-main-category-count` MUST satisfy all Acceptance checkboxes listed in `openspec/changes/fix-update-doctor-main-category-count/proposal.md` ## Acceptance section. Each Scenario below mirrors one Acceptance checkbox and MUST be verifiable via `openspec change validate fix-update-doctor-main-category-count` and the corresponding pytest/grep test run.

#### Scenario: pytest-tests-unit-test-doctor-main-py-test-aggregate-runs-a

GIVEN the Wave 1 fix proposal `fix-update-doctor-main-category-count` is being implemented
WHEN the developer executes ``pytest tests/unit/test_doctor_main.py::test_aggregate_runs_all_10_categories` 通过`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-update-doctor-main-category-count` and the corresponding pytest test run)

#### Scenario: pytest-tests-unit-test-doctor-main-py-test-checkers-dict-ha

GIVEN the Wave 1 fix proposal `fix-update-doctor-main-category-count` is being implemented
WHEN the developer executes ``pytest tests/unit/test_doctor_main.py::test_checkers_dict_has_10_entries` 通过`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-update-doctor-main-category-count` and the corresponding pytest test run)

#### Scenario: category-names

GIVEN the Wave 1 fix proposal `fix-update-doctor-main-category-count` is being implemented
WHEN the developer executes ``_CATEGORY_NAMES` 常量定义并被两个测试使用`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-update-doctor-main-category-count` and the corresponding pytest test run)

#### Scenario: docstring-assertion

GIVEN the Wave 1 fix proposal `fix-update-doctor-main-category-count` is being implemented
WHEN the developer executes `docstring 数字与 assertion 一致`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-update-doctor-main-category-count` and the corresponding pytest test run)

#### Scenario: git-diff-tests-unit-test-doctor-main-py-10-11

GIVEN the Wave 1 fix proposal `fix-update-doctor-main-category-count` is being implemented
WHEN the developer executes ``git diff tests/unit/test_doctor_main.py` 仅显示 10 → 11 / 集合增项,无其他逻辑变更`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-update-doctor-main-category-count` and the corresponding pytest test run)

