## Context

**失真链路**

`gh_hub_client.py` 三个方法 + `watch_hub.py` 一个方法在 gh v2.92.0 上 break, 而单元测试 mock 隔离了真 subprocess, 单元测试全绿. 实际 13 个 case e2e 测试首次运行即触发 4 个 RuntimeError.

**设计约束**

1. **不能破坏 unit test mock**: 现有 `tests/unit/test_gh_hub_client.py` 用 `unittest.mock.patch("subprocess.run")` mock stdout 为 `{"number": 42, "html_url": "..."}`. 修复后必须仍走 JSON parse 分支 (作为 fallback), 否则 unit test 失败.
2. **不引入新依赖**: gh CLI 是唯一外部依赖, 不能引入 `PyGithub` 等.
3. **batch 退化可接受**: O(N) REST 调用性能在当前规模 (<10 个 pending 条目) 可接受; 性能优化列为后续 change.

## Goals / Non-Goals

**Goals**:

- gh CLI 兼容层 4 处修复, 真实 GitHub 上行 + watch-hub 同步链可用
- 既有 unit test 不破坏 (JSON fallback 保留)
- 13 个 e2e 测试首次运行即过 (除环境依赖: gh auth + 网连通)
- 默认无 e2e 测试 (bats 加 filter 才跑, 避免 CI 网络依赖)

**Non-Goals**:

- 替换 `gh` CLI 为直接 HTTP API
- 优化 batch 性能
- 改 unit test 框架 (pytest mock 已够用)

## Technical Decisions

### TD-1: `create_issue` 双解析路径

**选项 A**: 仅解析 stdout URL (放弃 JSON fallback)
- 优点: 代码简单
- 缺点: 破坏 `tests/unit/test_gh_hub_client.py::test_create_issue_builds_correct_payload` (mock 返回 JSON)

**选项 B**: 保留 JSON fallback, stdout URL 为主路径 ✅
- 优点: 兼容 unit test + 兼容未来 gh CLI 加回 `--json` (gh ≥2.50 已有此 flag)
- 缺点: 双路径代码略多

**结论**: 选 B. 单元测试持续提供 mock 兼容性保险, 实际 gh v2.92.0 走 URL 路径.

### TD-2: `batch_get_issues_status` 改 REST 迭代

**选项 A**: GraphQL `nodes(ids: ...)` (需先 issue number → global ID, 2 次 API 调用)
- 优点: 1 次 API 调用获取 N 个 issue 状态

**选项 B**: 迭代 `get_issue_status` (N 次 API) ✅
- 优点: 简单, 无 ID 转换
- 缺点: N 次 REST 调用

**结论**: 选 B. 当前 pending 条目数 < 10, N 次调用 < 1s. 后续 change 可改 A.

### TD-3: `watch_hub` 去 subprocess

**选项 A**: 修复 subprocess 路径 (让 CWD 找到 `scripts/approve_proposal.sh`, 并预建 `hub-{N}.md` 提案)
- 优点: 保留原设计意图 (本地自动批准)
- 缺点: 提案 `hub-{N}` 与人类实际 proposal name 无关, 审计不真实

**选项 B**: watch-hub 只更新 pending 状态, 本地批准走 `approve_proposal.sh --manual --hub-issue` ✅
- 优点: 职责单一, watch-hub 是 polling 工具不需 approve 逻辑; 本地批准仍走设计完整的 `approve_proposal.sh`
- 缺点: 原"自动批准"语义丢失, 但原语义实际从未工作

**结论**: 选 B. 符合 ADR-0031"人类必须 approve"原则, watch-hub 不应代批.

## Implementation Notes

### 测试架构 (test_cross_repo_e2e_real.bats)

```
setup_file (一次性):
  1. gh repo view $HUB_REPO → 若不存在 gh repo create --public
  2. for label in rfc cross-repo approved e2e-test; do gh label create
  3. for s in spoke-a spoke-b spoke-c; do git clone --depth 1 → $TMPDIR/$s
  4. : > $TMPDIR.cleanup-issues

setup (每个 test):
  rm -f .rddf/state/{.cross-repo-pending.json,.cross-repo-audit.jsonl,.cross-repo-deps-cache.json}
  rm -f .rddf/improvements/*.md
  find openspec/changes -mindepth 1 -maxdepth 1 ! -name archive -exec rm -rf {} +

teardown_file:
  for num in cleanup-issues; do gh issue close --reason not planned; gh issue delete --yes
  for contract in $(gh api contents/contracts | grep e2e-); do gh api DELETE
  rm -rf $TMPDIR
```

13 个 case 编号 01-13, 见 proposal.md "Acceptance" 节.

### 安全默认值

- `RDDF_HUB_REPO` / `RDDF_REPORT_GH_REPO` 默认 `chisuhua/rdd-hub` (个人仓库), 生产应显式设置 org hub
- `RDDF_APPROVE_ACTOR=chisuhua-e2e-bot` 非交互默认, 生产应显式设置真实审批者
- 测试 Issue 标题前缀 `[RFC][e2e-test]`, label `e2e-test`, 便于人工筛选

## References

- ADR-0030 (待定): hub-and-spoke-federation
- ADR-0031 (已采纳): human-in-loop-cross-repo
- README §"跨项目协同 (ADR-0030)"
- `docs/proposal-suggestions-format.md`
- e2e 测试 session: `tests/integration/test_cross_repo_e2e_real.bats`
