# Tasks: add-issue-reporter

## 1. Reporter 核心（`_lib/issue_reporter.py`）

- [ ] 1.1 写 failing test: `detect_issue("manual", {"description": "foo"})` 返回 sanitize 后的 payload
- [ ] 1.2 写 failing test: `write_issue_file` 创建 `.rddf/issues/<cat>-<hash>.md` 含完整 frontmatter + body
- [ ] 1.3 写 failing test: `submit_issue_via_issue_file` 成功时返回 `submitted_url`，失败时返回 error
- [ ] 1.4 写 failing test: `is_ci_environment()` 在 `CI=true` 时返回 True
- [ ] 1.5 写 failing test: `is_ci_environment()` 在 `GITHUB_ACTIONS=true` 时返回 True
- [ ] 1.6 写 failing test: 错误路径（`write_issue_file` 在缺 .rddf/ 时抛 FileNotFoundError）
- [ ] 1.7 新建 `_lib/issue_reporter.py`，实现 5 个公共函数
- [ ] 1.8 跑 `pytest tests/unit/test_issue_reporter.py` 验证 6/6 pass

## 2. Close hook（`_lib/close_issues.py`）

- [ ] 2.1 写 failing test: `can_close_in_repo("chisuhua/rdd-workflow")` 在 mock gh 输出 `"true"` 时返回 True
- [ ] 2.2 写 failing test: `can_close_in_repo` 在 gh 缺失时返回 False
- [ ] 2.3 写 failing test: `close_issues_for_change` 解析 `roadmap-meta.yaml` 含 `issue_refs: [123]`
- [ ] 2.4 写 failing test: 已 CLOSED issue 被 skip（幂等）
- [ ] 2.5 写 failing test: 无 push 权限时输出 manual close 链接而非尝试关闭
- [ ] 2.6 写 failing test: `prune_old_issues(retention_days=30)` 删除 31 天前的 closed file
- [ ] 2.7 写 failing test: `prune_old_issues` 不删除 unsubmitted files
- [ ] 2.8 新建 `_lib/close_issues.py`，实现 `close_issues_for_change` + `can_close_in_repo` + `prune_old_issues`
- [ ] 2.9 跑 `pytest tests/unit/test_close_issues.py` 验证 7/7 pass

## 3. Bash 入口（`skills/_lib/close_issues.sh`）

- [ ] 3.1 写 failing test (bats): `source` shim 后能调用 `close_issues_for_change <name>`
- [ ] 3.2 写 failing test (bats): bash 入口在 python 不可用时输出明确错误
- [ ] 3.3 新建 `skills/_lib/close_issues.sh`，导出 bash 函数
- [ ] 3.4 跑 `bats tests/integration/test_close_issues_shell.bats` 验证 2/2 pass

## 4. 集成到 archive（worktree 模式）

- [ ] 4.1 写 failing test (bats): `_lib/archive.sh::archive_change` 在 mock roadmap 含 `issue_refs` 时调用 `close_issues_for_change`
- [ ] 4.2 写 failing test (bats): `close_issues_for_change` 失败时 archive 仍成功（`|| true`）
- [ ] 4.3 修改 `_lib/archive.sh::archive_change`，在 line 340 后、line 346 前插入：
  ```bash
  source "${HOME}/.agents/skills/_lib/close_issues.sh" 2>/dev/null || source "$(dirname "${BASH_SOURCE[0]}")/../skills/_lib/close_issues.sh"
  close_issues_for_change "$change_name" || log_warn "close_issues_for_change failed (non-blocking)"
  ```
- [ ] 4.4 跑 `bats tests/integration/test_archive_worktree_close_hook.bats` 验证 2/2 pass

## 5. 集成到 archive（lightweight 模式）

- [ ] 5.1 写 failing test (bats): `ship_archive.sh::archive_change_for_mode` 在 lightweight 分支调用 `close_issues_for_change`
- [ ] 5.2 修改 `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode`，在 lightweight 分支 line 231 后、line 237 前插入 hook
- [ ] 5.3 跑 `bats tests/integration/test_archive_lightweight_close_hook.bats` 验证 1/1 pass

## 6. CLI 路由（`_lib/cli/__init__.py`）

- [ ] 6.1 写 failing test: `rddf report-issue "foo"` 调用 `report_issue_cmd("foo")`
- [ ] 6.2 写 failing test: `rddf issue submit <file>` 调用 `issue_submit_cmd(file)`
- [ ] 6.3 写 failing test: `rddf issue list --state open` 返回本地 open issues
- [ ] 6.4 写 failing test: `rddf issue show <hash>` 返回本地 issue body
- [ ] 6.5 修改 `_lib/cli/__init__.py` 路由表 + `_lib/cli/issue_reporter_cmd.py` 新增实现
- [ ] 6.6 跑 `pytest tests/unit/test_cli_reporter.py` 验证 4/4 pass

## 7. `.gitignore` + env cache schema

- [ ] 7.1 在 `.gitignore` 追加 `.rddf/issues/`
- [ ] 7.2 在 `_lib/schemas/env_cache_schema.json` 新增 `gh_available: boolean` 字段
- [ ] 7.3 在 `rdd-env-check` 检测逻辑中加 `gh_available` 探测
- [ ] 7.4 跑 `pytest tests/unit/test_env_cache.py` 验证 schema 校验通过

## 8. 集成验证

- [ ] 8.1 跑 `pytest tests/unit/test_issue_reporter.py tests/unit/test_close_issues.py tests/unit/test_cli_reporter.py tests/unit/test_env_cache.py` 全部通过
- [ ] 8.2 跑 `bats tests/integration/test_archive_worktree_close_hook.bats tests/integration/test_archive_lightweight_close_hook.bats tests/integration/test_close_issues_shell.bats` 全部通过
- [ ] 8.3 跑 `./test.sh --quick` 验证 0 new failure（与 KNOWN_FAILURES.txt 对比）
- [ ] 8.4 跑 `openspec validate add-issue-reporter --type change --json` 0 errors
- [ ] 8.5 手动验证：模拟一个 issue 流程（write → submit → close）全链路

## 9. Commit

- [ ] 9.1 `git add _lib/issue_reporter.py _lib/close_issues.py skills/_lib/close_issues.sh _lib/archive.sh skills/guide-ship/scripts/ship_archive.sh _lib/cli/__init__.py .gitignore _lib/schemas/env_cache_schema.json tests/unit/test_issue_reporter.py tests/unit/test_close_issues.py tests/unit/test_cli_reporter.py tests/unit/test_env_cache.py tests/integration/test_archive_worktree_close_hook.bats tests/integration/test_archive_lightweight_close_hook.bats tests/integration/test_close_issues_shell.bats`
- [ ] 9.2 `git commit -m "feat(reporter): add issue reporter core + close hook

Implements ADR-0027 §1-3, §6:
- Reporter: 5 public functions (detect/write/submit/can_close/is_ci)
- Close hook: dual-mode integration in archive.sh (worktree) + ship_archive.sh (lightweight)
- CLI: rddf report-issue, rddf issue {submit,list,show}
- CI suppression + retention + .gitignore

TDD: ≥14 unit tests + ≥5 bats integration tests, 0 regression."`
- [ ] 9.3 （change-c 解锁后）`openspec archive add-issue-reporter --yes`
