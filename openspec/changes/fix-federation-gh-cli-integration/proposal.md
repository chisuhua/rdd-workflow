# fix-federation-gh-cli-integration

## Why

**背景**

实现 `rddf report-issue --category=rfc` 上行通道与 `rddf watch-hub --once` 下行状态同步的 `skills/_lib/gh_hub_client.py` / `skills/watch-hub/scripts/watch_hub.py`, 在 unit test 覆盖下被 mock 隔离, 实际从未在真实 GitHub 上验证. 

**e2e 测试发现 (2026-08-19)**

新增 `tests/integration/test_cross_repo_e2e_real.bats` 对真实 GitHub 仓库 `chisuhua/rdd-hub` 跑完 13 个测试时, 发现 4 个生产 bug:

1. **`gh_hub_client.create_issue`**: `gh issue create --json` flag 不被 gh v2.92.0 支持 (仅 `gh issue view` 支持 `--json`). 真实调用直接 `RuntimeError: gh command failed: unknown flag: --json`, RFC 上行完全不能工作.

2. **`gh_hub_client.get_issue_status`**: 字段名错. 使用 `--json state,state_reason`, 但 gh JSON 输出字段名是 `stateReason` (camelCase). `watch_hub` 因此永远拿不到 `stateReason`, 状态同步失效.

3. **`gh_hub_client.batch_get_issues_status`**: GraphQL `IssueFilters { numbers: [...] }` 不被 GitHub API 接受 (`InputObject 'IssueFilters' doesn't accept argument 'numbers'`). 批量查询必失败.

4. **`watch_hub.watch_hub`**: 检测到 `CLOSED + COMPLETED` 时调用 `bash scripts/approve_proposal.sh hub-{N}`, 但 (a) `scripts/approve_proposal.sh` 是 CWD 相对路径, 在 spoke 工作目录不存在; (b) 提案名 `hub-{N}` 无对应 improvement 文件. 子进程必失败, watch-hub 整体卡死.

**失真链路**

- README 承诺: "`rddf report-issue --category=rfc` 在 Hub 创建 Issue + 写 `.cross-repo-pending.json`"
- 真相: gh CLI 兼容层 4 处 break, 上行与 watch-hub 同步链完全不能工作

**已有机制（接线+修复而非新增）**

- `gh_hub_client.create_issue` / `get_issue_status` / `batch_get_issues_status` 单元测试已 mock subprocess, 不暴露真 bug
- `report_issue_rfc.py` / `watch_hub.py` 走 `_run()` 间接调用 gh, 错误未透传
- 无任何 e2e 测试覆盖真实 GitHub

## What Changes

**In Scope**:

- **修复 #1** `skills/_lib/gh_hub_client.py::create_issue`: 去除 `--json` flag, 改为解析 stdout URL (`https://github.com/<owner>/<repo>/issues/<N>`), 保留 JSON fallback 兼容 unit test mock
- **修复 #2** `skills/_lib/gh_hub_client.py::get_issue_status`: `--json state,state_reason` → `state,stateReason`
- **修复 #3** `skills/_lib/gh_hub_client.py::batch_get_issues_status`: 删除 GraphQL `IssueFilters{numbers}`, 改为迭代 `get_issue_status` (O(N) 但可靠; 后续可优化为 `nodes(ids:)`)
- **修复 #4** `skills/watch-hub/scripts/watch_hub.py`: 去除 broken subprocess 调用, watch-hub 只更新 `.cross-repo-pending.json` 状态 (本地 `--manual` 批准走 `approve_proposal.sh` 路径, 与 watch-hub 解耦)
- **新增 e2e 测试** `tests/integration/test_cross_repo_e2e_real.bats`: 13 个 case 覆盖 Hub bootstrap → RFC 上行 → design gate 阻断 → 人类审批模拟 → 本地 `--manual` 批准 → 契约下行 → contract-check pass/breaking → 跨仓库 deps → watch-hub 同步, setup_file 自动建 `chisuhua/rdd-hub` + 预置 label, teardown_file 自动清理 Issue + contract + 临时 spoke 副本

**Out of Scope**:

- 优化 `batch_get_issues_status` 为 `nodes(ids:)` (后续 change 优化性能, 当前 O(N) REST 可用)
- 完善 Hub Projects V2 字段自动创建 (已用 mock, 不是本 change 阻塞)
- `gh_hub_client.py` LSP 报 `state_dir: str vs Path` 兼容问题 (与本 change 无关)

## Capabilities

新增 capability (待 openspec/specs/ 采纳):

- `cross-repo-federation-v1` (扩 ADR-0030/0031): 修复 gh CLI 兼容性, e2e 验证通道完整

## Impact

- **能力**: Hub-and-Spoke 联邦协同从"README 描述但不能工作"变为"真实 GitHub 可用"
- **兼容**: 不破坏既有 unit test (mock 路径仍走 JSON 分支)
- **风险**: 低. 修复点在 gh CLI 兼容层, 改动 isolated; 既有 7 个相关 bats test + 133 个 unit test 全绿

## Acceptance

- [ ] **AC-1**: `rddf report-issue --category=rfc` 在真实 GitHub 创建 Issue + 写 `.cross-repo-pending.json`
- [ ] **AC-2**: `rddf watch-hub --once` 正确检测 `state=CLOSED + stateReason=COMPLETED` 并更新 pending
- [ ] **AC-3**: `tests/integration/test_cross_repo_e2e_real.bats` 13/13 全过, 单次运行 < 90s
- [ ] **AC-4**: 既有 `tests/unit/test_gh_hub_client.py` 3 个 case + `tests/integration/test_design_done_gate_hub.bats` 等 7 个相关 test 全绿
- [ ] **AC-5**: `./test.sh --python --unit` 133 个 unit test 全过
- [ ] **AC-6**: 审计 trail — `git log --grep='fix-federation-gh-cli-integration'` 含清晰 conventional commit
