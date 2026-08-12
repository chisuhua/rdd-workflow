# add-issue-reporter

> **优先级**: P0 (主体功能)
> **来源**: ADR-0027 实施拆分
> **前置依赖**: `add-issue-reporter-prereqs`（必须先合并）
> **关联**: `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` §6, §1-3

## Why

ADR-0027 §1-3 与 §6 定义了完整 5 环反馈环（Detect → Buffer → Report → Triage → Close），但 change-a 仅完成 3 个**前置依赖**。`change-b` 实现 5 环中的核心 3 环：

1. **Detect 环**（§1）：5 类触发点 — rdd-doctor CRITICAL / gate failure / phase crash / 手动 `rddf report-issue` /（ADR-0017 第 5 选项 — 暂留独立 ADR）。
2. **Buffer 环**（§2）：本地 `.rddf/issues/<cat>-<8char-hash>.md` 文件 + `.rddf/state/.issue-reporter.json` 元数据。
3. **Report 环**（§3）：三层提交 — L1 永远（本地）、L2 opt-in + gh CLI + 非 CI、L3 仅本地 + 用户提示。

`change-b` 还实现 **Close 环**（§6）的核心机制：`close_issues_for_change()` 函数在归档成功时自动关闭关联 issue（含权限探测、双模式覆盖、幂等、失败容忍）。

**为什么 TDD 5 步**: 每个核心函数（`write_issue_file`, `submit_issue_via_gh`, `close_issues_for_change`, `can_close_in_repo`, `is_ci_environment`）都需先写 failing test、看到失败、实现、看到通过、commit。

## What Changes

**In Scope**:

- **新增 `_lib/issue_reporter.py`**：导出 5 个公共函数 — `detect_issue(category, payload)` / `write_issue_file(category, payload)` / `submit_issue_via_gh(file_path, category)` / `can_close_in_repo(gh_repo)` / `is_ci_environment()`。
- **新增 `_lib/close_issues.py`**：导出 `close_issues_for_change(change_name, project_root, new_version)` — 解析 `roadmap-meta.yaml` 的 `issue_refs` + 权限探测 + 幂等关闭 + 失败容忍 + 按 `dedup_hash` 精确更新本地 issue 文件。
- **新增 `skills/_lib/close_issues.sh`**：bash 入口（`source` shim → 调用 `_lib/close_issues.py`），提供 `close_issues_for_change <change_name>` 函数。
- **改造 `_lib/archive.sh::archive_change`**：在 `openspec archive`（line 340）之后、`cleanup_worktree_and_branch`（line 346）之前，插入 `close_issues_for_change "$change_name" || true` 调用。
- **改造 `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode`**：在 lightweight 分支 `openspec archive`（line 231）之后、`commit_archive_moves`（line 237）之前，插入 `close_issues_for_change` 调用。
- **改造 `_lib/cli/__init__.py`**：路由表新增 `report-issue` / `issue`（含 `submit` / `list` / `show` 子命令）。
- **新增 `skills/rddf-reporter/scripts/`**：可选 — 简化 CLI 入口（实际由 `_lib/cli/` 路由表统一管理，本 change 不新增 17th skill）。
- **新增 `.gitignore` 条目**：`.rddf/issues/`。
- **新增 retention 机制**：`close_issues_for_change` 内置 `prune_old_issues(retention_days=30)` 调用（删除已 closed 且超过 retention 天数的本地 issue 文件，未提交的不删）。
- **新增 env 探测**：`is_ci_environment()` 检查 `CI` / `GITHUB_ACTIONS` / `JENKINS_URL` / `BUILDKITE` / `CIRCLECI` / `GITLAB_CI` 6 个标识。
- **新增 `rdd-env-check` 检测**：`.rddf/state/.env-cache.json` 新增 `gh_available` 字段（best-effort，不阻塞 phase 入口）。

**Out of Scope**:

- 不实现 detect 触发点的实际埋点（仅提供 `detect_issue()` 公共 API；实际 wire-up 在 change-c）
- 不实现 integration tests（`change-c`）
- 不写 docs（`change-c`）
- 不实现 `rddf-reporter` 新 skill（用现有 `_lib/cli/` 路由表，避免 17th skill 引发注册成本）
- 不实现 ADR-0017 冲突解决器第 5 选项（已标记需独立 ADR）
- 不实现 fork 仓库的 `gh_repo` 自动发现（用户手动配置）
- 不做 rate-limiting（GitHub 默认 5000 req/h 足够）

### 关键场景

- GIVEN `rddf report-issue "doc typo on line 42"`, WHEN 调用, THEN 在 `.rddf/issues/manual-<hash>.md` 写本地文件
- GIVEN 已写本地 issue 且 `RDDF_REPORT_AUTO_SUBMIT=yes` + gh 可用 + 非 CI, WHEN L2 触发, THEN `gh issue create` 成功 + `submitted_url` 字段更新
- GIVEN gh 缺失, WHEN L2 触发, THEN 降级为 L3（输出"运行 `rddf issue submit <file>`"）
- GIVEN `gh api` 返回 `permissions.push == false`（用户无写权限）, WHEN `close_issues_for_change` 调用, THEN 输出"issue #N fixed; please close manually: <URL>"
- GIVEN change 已 archive 且 `roadmap-meta.yaml` 含 `issue_refs: [123]`, WHEN `close_issues_for_change` 调用, THEN 幂等检查 state + 关闭 + 本地文件更新
- GIVEN `CI=true`, WHEN reporter 触发, THEN L2 强制降级为 L1（仅本地）
- GIVEN worktree 模式 archive, WHEN hook 调用, THEN issue 自动关闭
- GIVEN lightweight 模式 archive, WHEN hook 调用, THEN issue 自动关闭（双模式覆盖）
- GIVEN `.rddf/issues/` 含 50 个文件，30 个已 closed 超过 30 天, WHEN `prune_old_issues` 调用, THEN 20 个保留（30 个清理）

## Capabilities

### 1. Reporter 核心（`_lib/issue_reporter.py`）

- MUST 5 个公共函数全部有 docstring + type hints
- MUST `detect_issue(category, payload)` 调用 `_lib/loop/sanitizer.py::sanitize()` 对 payload 脱敏
- MUST `write_issue_file` 用 `compute_dedup_hash`（change-a 提供的）生成文件名
- MUST `submit_issue_via_gh` 调用前先 `gh issue list --search "<hash>" --state all` 查重
- MUST 全部错误用 `try/except` 包裹 + 返回 `Result(success: bool, error: str | None)`
- MUST 提供 ≥6 unit test 覆盖 5 个函数 + 错误路径

### 2. Close hook（`_lib/close_issues.py` + `skills/_lib/close_issues.sh`）

- MUST bash 入口通过 shim 正确加载 `_lib/close_issues.py`
- MUST `close_issues_for_change` 解析 `roadmap-meta.yaml`（用 PyYAML）
- MUST `can_close_in_repo` 用 `gh api repos/{owner}/{repo} --jq .permissions.push` 探测
- MUST 关闭时 comment 包含 change 名 + commit SHA + rdd-workflow 新版本号
- MUST 幂等：`gh issue view` 检查 state == CLOSED 则 skip
- MUST 失败容忍：整个 hook 在 `archive_change` 中以 `|| true` 调用
- MUST 按 `dedup_hash` 精确更新本地 issue 文件（不全局 sed）
- MUST 调用 `prune_old_issues(retention_days)` 清理
- MUST 提供 ≥5 unit test + ≥2 bats integration test（worktree + lightweight 双模式）

### 3. 集成到 archive 双模式

- MUST `_lib/archive.sh::archive_change` 在 line 340 后、line 346 前插入 hook
- MUST `skills/guide-ship/scripts/ship_archive.sh::archive_change_for_mode` 的 lightweight 分支同步插入
- MUST hook 失败不阻断 archive（与 `_lib/post_archive_cleanup.sh` 模式一致）
- MUST 提供 ≥2 bats integration test 验证双模式 hook 都触发

### 4. CLI 路由

- MUST `_lib/cli/__init__.py::route` 注册 `report-issue` / `issue` 子命令
- MUST `rddf report-issue "<desc>"` 接受描述作为 argv
- MUST `rddf issue submit <file>` 提交指定 issue 文件
- MUST `rddf issue list [--state open|closed|all]` 列出本地 issues
- MUST `rddf issue show <hash>` 显示本地 issue 内容
- MUST 提供 ≥3 unit test 覆盖 4 个子命令

### 5. CI 抑制 + retention

- MUST `is_ci_environment()` 检测 6 个 CI 标识
- MUST L2 提交前检查 `is_ci_environment()`，true 则降级 L1
- MUST `prune_old_issues` 只删除 `submitted == True` 且 `closed_at` 超过 retention 的文件
- MUST `.rddf/issues/` 加入 `.gitignore`
- MUST `.rddf/state/.env-cache.json` schema 新增 `gh_available` 字段

## Impact

- 影响文件：
  - 新增: `_lib/issue_reporter.py`（~200 行）
  - 新增: `_lib/close_issues.py`（~150 行）
  - 新增: `skills/_lib/close_issues.sh`（~50 行 bash 入口）
  - 修改: `_lib/archive.sh`（+5 行 hook 插入）
  - 修改: `skills/guide-ship/scripts/ship_archive.sh`（+5 行 hook 插入）
  - 修改: `_lib/cli/__init__.py`（+30 行路由表）
  - 修改: `.gitignore`（+1 行）
  - 修改: `_lib/schemas/env_cache_schema.json`（+1 字段）
- 兼容性：所有现有 archive 流程保持原行为（hook 用 `|| true` 包裹）
- 风险：中 — hook 失败容忍已设计，但需充分测试双模式覆盖

## Acceptance

- `tests/unit/test_issue_reporter.py` 全部通过（≥6 cases）
- `tests/unit/test_close_issues.py` 全部通过（≥5 cases）
- `tests/unit/test_cli_reporter.py` 全部通过（≥3 cases）
- `tests/integration/test_archive_close_hook.bats` 全部通过（≥2 cases，覆盖双模式）
- 现有 archive 相关 test 全部不 regression
- `openspec validate add-issue-reporter --type change --json` 0 errors
- 双模式 archive 各跑一次，新 issue 都被正确关闭
- `./test.sh --quick` 0 new failure
- commit message: `feat(reporter): add issue reporter core + close hook`
