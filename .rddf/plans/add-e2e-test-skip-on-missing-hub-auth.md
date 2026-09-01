# add-e2e-test-skip-on-missing-hub-auth Implementation Plan

> **For agentic workers:** skill_use("execute")

**Goal:** E2E 测试 (`test_cross_repo_e2e_real.bats` + `test_cross_repo_impact_detection.bats`) 在 gh 缺失/未认证/Hub 不可达时优雅 skip,而非 fail。

**Architecture:** 在 setup_file() 开头加 3 个前置检查(gh / gh auth / Hub 可达),失败则 `skip`。重试 1 次 git clone。

**Tech Stack:** bash, bats, gh CLI。

## Tasks

### Task 1: E2E test Skip-not-fail

- [ ] **Step 1**: 修改 `tests/integration/test_cross_repo_e2e_real.bats::setup_file()` 加 gh / auth / Hub 检查 + skip
- [ ] **Step 2**: 修改 `tests/integration/test_cross_repo_impact_detection.bats::setup_file()` 同样检查
- [ ] **Step 3**: 跑 bats 验证 skip 行为 (无 gh 环境): bats 仍然 PASS (skip 而非 fail)
- [ ] **Step 4**: 从 KNOWN_FAILURES.txt 移除 `setup_file failed` 条目
- [ ] **Step 5**: Defer commit

### Task 2: 文档 + commit + archive

- [ ] **Step 1**: `docs/change-quality-guide.md` 加"真实 E2E 测试 Skip-not-fail"段
- [ ] **Step 2**: `sed -i 's/- \\[ \\]/- [x]/' openspec/changes/add-e2e-test-skip-on-missing-hub-auth/tasks.md`
- [ ] **Step 3**: `git add -A && git commit -m "test(e2e): skip-not-fail on missing gh auth"`
- [ ] **Step 4**: `archive_change add-e2e-test-skip-on-missing-hub-auth`

## Self-Review
- ✅ 不破坏正常环境 E2E 测试
- ✅ skip 时 stdout 输出原因
