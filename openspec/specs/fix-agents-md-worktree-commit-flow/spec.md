# fix-agents-md-worktree-commit-flow Specification

## Purpose
TBD - created by archiving change fix-agents-md-worktree-commit-flow. Update Purpose after archive.

## Requirements

### Requirement: acceptance-1

The system SHALL `bats tests/integration/test_worktree_archive_workflow_docs.bats` ⇒ 6/6 通过.

#### Scenario: `bats tests/integration/test_worktree_archive_workflow_docs.

- **WHEN** the change is applied
- **THEN** `bats tests/integration/test_worktree_archive_workflow_docs.bats` ⇒ 6/6 通过

### Requirement: acceptance-2

The system SHALL `grep -c "^### Worktree Commit Flow" AGENTS.md` ≥ 1.

#### Scenario: `grep -c "^### Worktree Commit Flow" AGENTS.md` ≥ 1

- **WHEN** the change is applied
- **THEN** `grep -c "^### Worktree Commit Flow" AGENTS.md` ≥ 1

### Requirement: acceptance-3

The system SHALL `grep -cE "^   - \`[a-z]+\(<scope>\):" AGENTS.md` ≥ 5.

#### Scenario: `grep -cE "^   - \`[a-z]+\(<scope>\):" AGENTS.md` ≥ 5

- **WHEN** the change is applied
- **THEN** `grep -cE "^   - \`[a-z]+\(<scope>\):" AGENTS.md` ≥ 5

### Requirement: acceptance-4

The system SHALL `grep -A 8 "^### 归档流程" AGENTS.md` 含 `check_worktree_commits`.

#### Scenario: `grep -A 8 "^### 归档流程" AGENTS.md` 含 `check_worktree_commits`

- **WHEN** the change is applied
- **THEN** `grep -A 8 "^### 归档流程" AGENTS.md` 含 `check_worktree_commits`

### Requirement: acceptance-5

The system SHALL `grep "execute 阶段不逐任务 commit" AGENTS.md` 的**匹配行本身**含 `worktree-internal commit` 或 `worktree 内做 1 个聚合 commit`.

#### Scenario: `grep "execute 阶段不逐任务 commit" AGENTS.md` 的**匹配行本身**含 `worktr

- **WHEN** the change is applied
- **THEN** `grep "execute 阶段不逐任务 commit" AGENTS.md` 的**匹配行本身**含 `worktree-internal commit` 或 `worktree 内做 1 个聚合 commit`

### Requirement: acceptance-6

The system SHALL `bash tests/scripts/report_regression.sh` ⇒ **新增失败 = 0**（**先于** refresh 执行，见 What Changes 4）.

#### Scenario: `bash tests/scripts/report_regression.sh` ⇒ **新增失败 = 0**（**先

- **WHEN** the change is applied
- **THEN** `bash tests/scripts/report_regression.sh` ⇒ **新增失败 = 0**（**先于** refresh 执行，见 What Changes 4）

### Requirement: acceptance-7

The system SHALL `bash tests/scripts/refresh_known_failures.sh --dry-run` 的 diff 期望 `removed=6, added=0`（summary `kept=4`）；核对通过后实跑 refresh.

#### Scenario: `bash tests/scripts/refresh_known_failures.sh --dry-run` 的 d

- **WHEN** the change is applied
- **THEN** `bash tests/scripts/refresh_known_failures.sh --dry-run` 的 diff 期望 `removed=6, added=0`（summary `kept=4`）；核对通过后实跑 refresh

### Requirement: acceptance-8

The system SHALL `git diff tests/KNOWN_FAILURES.txt` **仅**含 6 条 AGENTS.md 条目的移除与一条 summary 注释，**无非注释新增行**（防止 refresh 把别的新失败吸收进来）.

#### Scenario: `git diff tests/KNOWN_FAILURES.txt` **仅**含 6 条 AGENTS.md 条目的

- **WHEN** the change is applied
- **THEN** `git diff tests/KNOWN_FAILURES.txt` **仅**含 6 条 AGENTS.md 条目的移除与一条 summary 注释，**无非注释新增行**（防止 refresh 把别的新失败吸收进来）

### Requirement: acceptance-9

The system SHALL `tests/KNOWN_FAILURES.txt` 条目数 10 → 4，且剩余 4 条与本提案无关.

#### Scenario: `tests/KNOWN_FAILURES.txt` 条目数 10 → 4，且剩余 4 条与本提案无关

- **WHEN** the change is applied
- **THEN** `tests/KNOWN_FAILURES.txt` 条目数 10 → 4，且剩余 4 条与本提案无关

### Requirement: acceptance-10

The system SHALL `rddf doctor --category docs-consistency` 无新增 finding（新段内**不得**写「per ADR-00XX」这类未经核对的 ADR 引用 —— `docs_consistency` 会扫 AGENTS.md 的 ADR 编号引用并对磁盘缺失报 WARNING）.

#### Scenario: `rddf doctor --category docs-consistency` 无新增 finding（新段内**不

- **WHEN** the change is applied
- **THEN** `rddf doctor --category docs-consistency` 无新增 finding（新段内**不得**写「per ADR-00XX」这类未经核对的 ADR 引用 —— `docs_consistency` 会扫 AGENTS.md 的 ADR 编号引用并对磁盘缺失报 WARNING）
