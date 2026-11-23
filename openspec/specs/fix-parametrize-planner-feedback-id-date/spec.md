# fix-parametrize-planner-feedback-id-date Specification

## Purpose
TBD - created by archiving change fix-parametrize-planner-feedback-id-date. Update Purpose after archive.
## Requirements
### Requirement: fix-parametrize-planner-feedback-id-date

The Wave 1 fix proposal `fix-parametrize-planner-feedback-id-date` MUST satisfy all Acceptance checkboxes listed in `openspec/changes/fix-parametrize-planner-feedback-id-date/proposal.md` ## Acceptance section. Each Scenario below mirrors one Acceptance checkbox and MUST be verifiable via `openspec change validate fix-parametrize-planner-feedback-id-date` and the corresponding pytest/grep test run.

#### Scenario: pytest-tests-unit-test-planner-feedback-id-uniqueness-py-5

GIVEN the Wave 1 fix proposal `fix-parametrize-planner-feedback-id-date` is being implemented
WHEN the developer executes ``pytest tests/unit/test_planner_feedback_id_uniqueness.py` 5 个失败测试全绿`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-parametrize-planner-feedback-id-date` and the corresponding pytest test run)

#### Scenario: utc-date-shell-3

GIVEN the Wave 1 fix proposal `fix-parametrize-planner-feedback-id-date` is being implemented
WHEN the developer executes `测试在任意 UTC 日期运行稳定(`date` shell 命令验证 3 个不同日期都绿)`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-parametrize-planner-feedback-id-date` and the corresponding pytest test run)

#### Scenario: faketime-monkeypatch-datetime-now

GIVEN the Wave 1 fix proposal `fix-parametrize-planner-feedback-id-date` is being implemented
WHEN the developer executes `测试不依赖系统时间(可通过 `faketime` 或 monkeypatch `datetime.now` 验证)`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-parametrize-planner-feedback-id-date` and the corresponding pytest test run)

#### Scenario: regression-test

GIVEN the Wave 1 fix proposal `fix-parametrize-planner-feedback-id-date` is being implemented
WHEN the developer executes `修改前先加 regression test 锁住"硬编码日期应被替换"`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-parametrize-planner-feedback-id-date` and the corresponding pytest test run)

#### Scenario: git-diff-stat-100

GIVEN the Wave 1 fix proposal `fix-parametrize-planner-feedback-id-date` is being implemented
WHEN the developer executes ``git diff --stat` 净增 ≤ 100 行`
THEN the acceptance criterion MUST be satisfied (verifiable via `openspec change validate fix-parametrize-planner-feedback-id-date` and the corresponding pytest test run)

