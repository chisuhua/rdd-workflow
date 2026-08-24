## ADDED Requirements

### Requirement: fix-review-debt-recorded-gate
The system SHALL implement fix-review-debt-recorded-gate functionality per proposal.md scope.

#### Scenario: scenario-1
- **GIVEN** **WHEN** Phase 2.5 commit 前 ship_review.sh 调 helper
- **WHEN** **THEN**
- **THEN** - helper 扫 `.go` 文件(18 种语言 glob 含 `.go`)
- 探测 `.rddf/improvements/cleanup-<change>-debt.md` 是否存在且 mtime > execute_finished_at
- 若不存在 → 提示用户选项 1-3(范围內 / side-effect / arch drift)
- 若存在 → silent pass

#### Scenario: scenario-2
- **GIVEN** **WHEN** helper 执行
- **WHEN** **THEN**
- **THEN** - 必填参数 `project_root` 来自 `ctx`,绝对路径
- `Path(project_root) / ".rddf/improvements"` 解析正确
- 无 silent failure

#### Scenario: scenario-3
- **GIVEN** **WHEN** helper 执行
- **WHEN** **THEN**
- **THEN** - `except PermissionError as e:` → 记录具体 stderr 提示 `cannot read .rddf/improvements: <reason>`
- 返回 `(False, "warning")`(与 disk-error 相符的警告)
- 不静默 pass

