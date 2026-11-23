# fix-remove-stale-filled-at-regression-test Specification

## Purpose
TBD - created by archiving change fix-remove-stale-filled-at-regression-test. Update Purpose after archive.
## Requirements
### Requirement: fix-remove-stale-filled-at-regression-test

The Wave 1 fix proposal `fix-remove-stale-filled-at-regression-test` MUST satisfy all Acceptance checkboxes listed in `openspec/changes/fix-remove-stale-filled-at-regression-test/proposal.md` ## Acceptance section. Each Scenario below mirrors one Acceptance checkbox and MUST be verifiable via `openspec change validate fix-remove-stale-filled-at-regression-test` and the corresponding pytest/grep test run.

#### Scenario: pytest-tests-unit-test-cli-all-subcommands-py-testfilledatr

GIVEN the Wave 1 fix proposal `fix-remove-stale-filled-at-regression-test` is being implemented
WHEN the developer executes ``pytest tests/unit/test_cli_all_subcommands.py::TestFilledAtRegression::test_actual_repo_iteration_json_validates_after_fix` 通过`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-remove-stale-filled-at-regression-test` and the corresponding pytest test run)

#### Scenario: grep-rddf-state-iteration-json-0

GIVEN the Wave 1 fix proposal `fix-remove-stale-filled-at-regression-test` is being implemented
WHEN the developer executes `测试函数体内 grep `.rddf/state/iteration.json` 命中 0 行`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-remove-stale-filled-at-regression-test` and the corresponding pytest test run)

#### Scenario: tmp-path-fixture

GIVEN the Wave 1 fix proposal `fix-remove-stale-filled-at-regression-test` is being implemented
WHEN the developer executes `测试函数用 `tmp_path` 构造 fixture`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-remove-stale-filled-at-regression-test` and the corresponding pytest test run)

#### Scenario: docstring

GIVEN the Wave 1 fix proposal `fix-remove-stale-filled-at-regression-test` is being implemented
WHEN the developer executes `测试 docstring 反映新意图`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-remove-stale-filled-at-regression-test` and the corresponding pytest test run)

#### Scenario: pytest-tests-unit-test-cli-all-subcommands-py

GIVEN the Wave 1 fix proposal `fix-remove-stale-filled-at-regression-test` is being implemented
WHEN the developer executes ``pytest tests/unit/test_cli_all_subcommands.py` 全套不引入新失败`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-remove-stale-filled-at-regression-test` and the corresponding pytest test run)

