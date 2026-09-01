# fix-report-regression-sed-double-hash-strip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: skill_use("execute")

**Goal:** 修复 `tests/scripts/report_regression.sh` 的 sed strip 正则误截断 bats description 中含 `##` 的 description,消除回归门"新增失败"误报。

**Architecture:** `report_regression.sh` 当前用 `sed -E 's/[[:space:]]+#.*$//'` strip `#` 注释,会误截 `## 决策` 这种合法 description 内容。改用 `sed -E 's/[[:space:]]+#[a-z][a-z].*$//'` (仅 strip ` #` 后接字母的注释如 `# pre-existing:`),保留 description 内的 `##`。

**Tech Stack:** bash 4.x, sed, bats。

---

## File Structure

| File | Change |
|---|---|
| `tests/scripts/report_regression.sh` | 修 sed strip 正则(L28 附近,~5 行) |
| `tests/unit/test_report_regression_strip.py` | 新文件,~5 个单元测试 |
| `tests/integration/test_report_regression_descriptions.bats` | 新文件,~3 个端到端 bats |
| `docs/change-quality-guide.md` | 加"回归门 description 解析"段 |

---

## Tasks

### Task 1: 修复 sed 正则 + 加回归保护

**Files:** Modify `tests/scripts/report_regression.sh:27-32`

- [ ] **Step 1: 写 failing 单元测试** 在 `tests/unit/test_report_regression_strip.py` 写 5 个测试覆盖:`# pre-existing` 注释被 strip / `## 决策` 描述保留 / `# ADR-NNNN:` 保留 / 无 `#` 保留 / 末尾 `# no comment` 保留
- [ ] **Step 2: 跑测试确认 fail** `pytest tests/unit/test_report_regression_strip.py -v` → FAIL (file missing or assertion fail)
- [ ] **Step 3: 修 sed regex** 把 L28 的 `sed -E 's/[[:space:]]+#.*$//'` 改为 `sed -E 's/[[:space:]]+#[A-Za-z].*$//'` (注意避免误 strip `# ADR-NNNN:`,后续测试会验证)
- [ ] **Step 4: 跑测试确认 pass** `pytest tests/unit/test_report_regression_strip.py -v` → PASS
- [ ] **Step 5: Defer commit**

### Task 2: 端到端 bats 验证 + 文档

- [ ] **Step 1**: 写 `tests/integration/test_report_regression_descriptions.bats` 3 个测试:`## 决策` description 匹配 baseline / `# ADR-NNNN` 保留 / `# pre-existing:` 注释 strip
- [ ] **Step 2**: `bats tests/integration/test_report_regression_descriptions.bats` → 3 pass
- [ ] **Step 3**: 跑 `bash tests/scripts/report_regression.sh` → 输出 `✅ 0 新增失败`
- [ ] **Step 4**: 更新 `docs/change-quality-guide.md` 加"回归门 description 解析"段(说明 `##` 陷阱 + 正确格式)
- [ ] **Step 5**: Defer commit

### Task 3: tasks.md 全 14 tasks 标记 + worktree commit

- [ ] **Step 1**: `sed -i 's/- \[ \]/- [x]/' openspec/changes/fix-report-regression-sed-double-hash-strip/tasks.md`
- [ ] **Step 2**: `git add -A && git commit -m "fix(regression-gate): correct sed double-hash strip"`
- [ ] **Step 3**: 验证 `git log -1 --oneline` 显示 commit

## Self-Review
- ✅ Spec 覆盖:3 个 task 对应 proposal 14 个原 task (实现+测试+文档)
- ✅ 无 TBD 占位
- ✅ 不破坏 baseline (132+ 条 KNOWN_FAILURES 仍正确匹配)
