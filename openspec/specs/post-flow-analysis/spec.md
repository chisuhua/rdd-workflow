# post-flow-analysis Specification

## Purpose
TBD - created by archiving change fix-adr-0027-cli-optin-gate. Update Purpose after archive.
## Requirements
### Requirement: fix-adr-0027-cli-optin-gate
The system SHALL implement fix-adr-0027-cli-optin-gate functionality per proposal.md scope.

#### Scenario: scenario-1
- **GIVEN** **WHEN** SKILL.md Phase Exit 段指示 agent 调 `rddf report-issue --exit-code 137 --no-submit --category phase-crash --phase guide-ship "execute crashed"`
- **WHEN** **THEN**
- **THEN** 1. argparse 接收全部已知 flag → exit 0
2. `--no-submit` 默认 true → `submit_issue_via_gh` **不调用**
3. 写本地 `.rddf/issues/phase-crash-<hash>.md`,含 `--exit-code 137` 在 metadata
4. stdout 输出 `✅ wrote <path>`(L3 提示

#### Scenario: scenario-2
- **GIVEN** **WHEN** `RDDF_REPORT_ENABLED=yes RDDF_REPORT_AUTO_SUBMIT=yes rddf issue submit .rddf/issues/phase-crash-<hash>.md`
- **WHEN** **THEN**
- **THEN** 1. `issue_cmd::cmd_issue` 校验 `RDDF_REPORT_ENABLED=yes` → 通过
2. 校验 `RDDF_REPORT_AUTO_SUBMIT=yes` → 通过
3. 校验文件 frontmatter 的 `category` 在 `submit_categories` 列表 → 通过
4. 校验 `CI != true` → 通过(本地)
5. `subm

#### Scenario: scenario-3
- **GIVEN** **WHEN** `rddf issue submit <file>`
- **WHEN** **THEN**
- **THEN** 1. `submit_issue_via_gh` 直接拒绝并打印提示:L2 opt-out by default,exit 2,非 0
2. 本地 issue 文件**不变**(L1 已写,保留供用户后续手动操作)
3. stderr 提示:`Set RDDF_REPORT_AUTO_SUBMIT=yes AND ensure file category is in RDDF_REPORT_SUB

### Requirement: fix-post-flow-classifier-ordering
The system SHALL implement fix-post-flow-classifier-ordering functionality per proposal.md scope.

#### Scenario: scenario-1
- **GIVEN** **WHEN** classifier 执行
- **WHEN** **THEN**
- **THEN** - F1 正则匹配(`Traceback` + 栈帧路径含 `skills/_lib/` 或 `_lib/`)
- 分类为 `phase-crash`
- `dedup_hash` 基于前 3 个 stack frame 归一化

#### Scenario: scenario-2
- **GIVEN** **WHEN** classifier 执行
- **WHEN** **THEN**
- **THEN** - F4 正则匹配(优先于 F3)
- 分类为 `gate-failure`
- Reporter 段记 `skill_invoked: gate-system`

#### Scenario: scenario-3
- **GIVEN** **WHEN** classifier 执行
- **WHEN** **THEN**
- **THEN** - F2 正则匹配(优先于 F3)
- 分类为 `gate-failure`
- **不再是 F3-mislabeled as flow-bug**

