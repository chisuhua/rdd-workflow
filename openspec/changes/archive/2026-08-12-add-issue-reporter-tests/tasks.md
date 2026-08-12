# Tasks: add-issue-reporter-tests

## 1. End-to-end integration tests（`test_issue_reporter_e2e.bats`）

- [ ] 1.1 写 failing test: 完整 5 环（detect → write → submit (mock) → archive → close）跑通
- [ ] 1.2 写 failing test: write_issue_file 创建的 frontmatter 完整（含 dedup_hash、rdd_workflow_version、submitted=false）
- [ ] 1.3 写 failing test: submit_issue_via_gh mock 成功后 submitted_url 字段更新
- [ ] 1.4 跑 `bats tests/integration/test_issue_reporter_e2e.bats` 验证 3/3 pass

## 2. 双模式 archive 集成测试（`test_archive_close_dual_mode.bats`）

- [ ] 2.1 写 failing test: worktree 模式 archive 触发 `_lib/archive.sh` line 340 后 hook
- [ ] 2.2 写 failing test: lightweight 模式 archive 触发 `ship_archive.sh` line 231 后 hook
- [ ] 2.3 写 failing test: hook 失败时 archive 仍返回 0（`|| true` 包裹）
- [ ] 2.4 跑 `bats tests/integration/test_archive_close_dual_mode.bats` 验证 3/3 pass

## 3. CI 抑制 + retention 测试（`test_ci_suppression_and_retention.bats`）

- [ ] 3.1 写 failing test: `CI=true` 时 `submit_issue_via_gh` 跳过，仅写本地
- [ ] 3.2 写 failing test: `GITHUB_ACTIONS=true` 时同样降级
- [ ] 3.3 写 failing test: 31 天前 closed file 被 prune，30 天前保留
- [ ] 3.4 写 failing test: unsubmitted file 即使超过 retention 也不被 prune
- [ ] 3.5 跑 `bats tests/integration/test_ci_suppression_and_retention.bats` 验证 4/4 pass

## 4. 第三方项目集成测试（`test_issue_reporter_external_project.bats`）

- [ ] 4.1 复用 `test_global_install_external_project.bats` 的 `$BATS_TMPDIR` 模式
- [ ] 4.2 写 failing test: 通过 `~/.agents/skills/_lib/` 路径调用 reporter 走 shim
- [ ] 4.3 写 failing test: shim 缺失时降级为 warning（不 crash）
- [ ] 4.4 跑 `bats tests/integration/test_issue_reporter_external_project.bats` 验证 2/2 pass

## 5. CLI + env cache 联合测试（`test_cli_env_cache_integration.py`）

- [ ] 5.1 写 failing test: `gh_available=true` 时 `rddf issue submit` 走 L2
- [ ] 5.2 写 failing test: `gh_available=false` 时 `rddf issue submit` 提示 "gh not available" 并降级 L1
- [ ] 5.3 写 failing test: 4 个 CLI 子命令都尊重 `gh_available` env cache
- [ ] 5.4 跑 `pytest tests/unit/test_cli_env_cache_integration.py` 验证 3/3 pass

## 6. Docs 更新

- [ ] 6.1 在 `docs/architecture/extension-points.md` 新增"添加上报触发点"小节
- [ ] 6.2 在 `docs/architecture/historical-evolution.md` v2.1.x 段记录 ADR-0027 实施时间线
- [ ] 6.3 在 `CHANGELOG.md` Unreleased 段记录 issue reporter 三个 change
- [ ] 6.4 在 `docs/adr/README.md` 把 ADR-0027 从"已采纳（v2.1.x+ 候选）"更新为"已实施（v2.1.x+）"

## 7. 集成验证

- [ ] 7.1 跑所有新 test file 全部通过（5 个文件，≥15 cases）
- [ ] 7.2 跑 `./test.sh --full --regression` 验证 0 new failure（与 KNOWN_FAILURES.txt 对比）
- [ ] 7.3 跑 `openspec validate add-issue-reporter-tests --type change --json` 0 errors
- [ ] 7.4 跑 `bash tests/scripts/doc_truth_sync.sh`（如存在）验证 docs 一致性

## 8. Commit

- [ ] 8.1 `git add tests/integration/test_issue_reporter_e2e.bats tests/integration/test_archive_close_dual_mode.bats tests/integration/test_ci_suppression_and_retention.bats tests/integration/test_issue_reporter_external_project.bats tests/unit/test_cli_env_cache_integration.py docs/architecture/extension-points.md docs/architecture/historical-evolution.md CHANGELOG.md docs/adr/README.md`
- [ ] 8.2 `git commit -m "test(reporter): add end-to-end + dual-mode + docs

Implements ADR-0027 In Scope '测试与文档':
- ≥10 e2e + bats tests (5 环全链路, 双模式 archive, CI 抑制, retention, 第三方)
- ≥3 unit tests (CLI + env cache 联合)
- 4 docs updates (extension-points, historical-evolution, CHANGELOG, ADR index)

Closes the 3-change series for ADR-0027 implementation.

TDD: all tests written first, 0 regression."`
- [ ] 8.3 `openspec archive add-issue-reporter-tests --yes`
