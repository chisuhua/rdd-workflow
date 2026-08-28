# rdd-doctor-docs-consistency

## Why

`rdd-doctor` 当前只校验 5 类结构化文件（`.rddf/state/*.json` schema / `.rddf/plans/*.md` TDD 5 步 / `openspec/changes/*/roadmap-meta.yaml` / `proposal-*.md` 表格 / `openspec/changes/*/tasks.md` checkbox）。它是 read-only 的诊断工具，输出 CRITICAL/WARNING/INFO 三级报告。

2026-08-26 审计发现 6 类**文档一致性**问题，均为 rdd-doctor 当前不覆盖：

| 问题类型 | 出现位置 | rdd-doctor 当前覆盖？ |
|----------|----------|---------------------|
| 子技能数量不一致 | README (12) / INSTALL (20) / USAGE (13) / package.json (25) / 磁盘 (25) | ❌ |
| 阶段架构数字不一致 | README (4) / USAGE (3) / AGENTS (4+5 混合) | ❌ |
| npm test 行为反向提示 | README/AGENTS/CHANGELOG/USAGE (4 处声称"不跑 Python") vs package.json (跑) | ❌ |
| 版本号冲突 | README (v2.1+) / package.json (v3.0.0) / INSTALL (2.0.0-beta) | ❌ |
| 关键 ADR 列表过期 | AGENTS.md line 148 漏列 ADR-0025/0027/0029/0031/0034 | ❌ |
| 角色 frontmatter 不一致 | AGENTS.md 称"4 个阶段技能 role:"，但 `rdd-verifier` 也有 role: | ❌ |

每一类都是"软腐烂"——单独看每个文档都没大问题，但叠加起来造成用户**理解错位**（以为是 v2.0 但实际是 v3.0；以为没有 verify 但实际有）。

新增 `--category docs-consistency` 让 rdd-doctor 能定期巡检，CI 或开发者在 commit 前能自查。

## What Changes

**In Scope**:

- `_lib/cli/doctor_cmd.py` 新增 `--category docs-consistency` 路由
- `_lib/doctor.py` 或新建 `_lib/docs_consistency.py` 实现 6 类检查：
- `tests/integration/test_rdd_doctor.bats` 添加 6 个新 case
- `tests/unit/test_docs_consistency.py` 添加 6 个新 unit test
- 不破坏现有 5 类 category 的行为

**Out of Scope**:

- 自动修复文档（rdd-doctor 保持 read-only；自动修复属 P2 changelog-usage-sync 提案）
- 跨项目扫描（rdd-doctor 是项目本地工具；跨项目治理属 ADR-0027 L2 上报）
- ADR 自动生成（属 P2 adr-index-auto-sync 提案）

## Capabilities

- (no items specified)

## Impact

- (no items specified)

## Acceptance

- [ ] `_lib/docs_consistency.py` 6 个检查函数实现
- [ ] `_lib/cli/doctor_cmd.py` 新增 `--category docs-consistency` 路由
- [ ] `bash skills/rdd-doctor/scripts/doctor.sh --category docs-consistency` 在 master 分支运行 0 CRITICAL + 0 WARNING
- [ ] `bash skills/rdd-doctor/scripts/doctor.sh --category all` 包含 docs-consistency
- [ ] `tests/unit/test_docs_consistency.py` 6+ 个 unit test PASS
- [ ] `tests/integration/test_rdd_doctor.bats` 新增 6+ 个 integration test PASS
- [ ] 文档同步：CHANGELOG.md 添加本次 change 条目；README/AGENTS rdd-doctor 描述更新
- [ ] 新提案：把 docs-consistency 检查接入 pre-commit hook 作为 follow-up

