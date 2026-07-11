---
SCOPE: shared
STATUS: PROPOSED
---

# Tasks: sync-workflow-contracts

> **Goal**: 把 USAGE / AGENTS / INSTALL / README / package.json / ADR 索引 / openspec specs 之间的 7 类不一致(proposal §Why)锁到一起,并加 3 个 anti-drift 测试持续防漂移。
> **Risk**: low(纯文档 + spec + 测试,零生产代码变更)。
> **不做什么**:不修改 `skills/*.md` prose(除 INSTALL.md description)、不修改 `skills/_lib/*.py`、不修改 `.github/workflows/test.yml`、不处理 ADR-0013 dup 重编号、不创建 worktree/branch/commit/push。
> **Estimated effort**: 1-1.5 d。

---

## 1. 基线验证(Pre-flight)

> 跑在动手改任何文件之前,确认当前 drift 状态可复现。

- [ ] **Task 1.1**: 记录磁盘真相

```bash
cd /workspace/project/spec-workflow
echo "=== skills on disk ===" && ls skills/*.md | wc -l
echo "=== package.json skills count ===" && python3 -c "import json; print(len(json.load(open('package.json'))['skills']))"
echo "=== ADR files ===" && ls docs/adr/ADR-*.md | wc -l
echo "=== ADR numbers ===" && ls docs/adr/ADR-*.md | sed -E 's/.*ADR-([0-9]+).*/\1/' | sort -u
echo "=== openspec specs ===" && ls openspec/specs/ | wc -l
```

Expected: 13 / 11 / 21 / {0001..0012,0013,0013,0014..0019} / 25

- [ ] **Task 1.2**: 记录当前 drift 字段

```bash
cd /workspace/project/spec-workflow
echo "=== USAGE.md ship-side phase count ===" && grep -E "Phase [0-9]" USAGE.md | head -10
echo "=== general/spec.md ship-side phase count ===" && grep -E "5 阶段|ship-side" openspec/specs/general/spec.md
echo "=== general/spec.md handoff paths ===" && grep -E "handoff\\.json|plan-handoff" openspec/specs/general/spec.md
echo "=== general/spec.md consumer list ===" && grep -E "guide-spec|consumer" openspec/specs/general/spec.md
echo "=== AGENTS.md skill count ===" && grep -E "12 个|13 个|skill.*\\.md" AGENTS.md
echo "=== AGENTS.md ADR count ===" && grep -E "ADR-0001~0012|ADR-00[0-9]+" AGENTS.md | head -5
echo "=== docs/adr/README.md status table ===" && grep -cE "^> \\| ADR-" docs/adr/README.md
```

Expected: 确认 7 类 drift 全部可观察(为后续 spec delta 提供 baseline)。

- [ ] **Task 1.3**: 跑 baseline 测试,确保改动前全部通过

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
bats tests/smoke.bats 2>&1 | tail -5
```

Expected: 28+ unit 文件 + 7 smoke cases 全部通过。

---

## 2. README / AGENTS / INSTALL / package.json 决策

> 这一组决定 narrative docs 与分发契约的对齐。先讨论决策,再动手改。

- [ ] **Task 2.1**: 决策 `package.json::skills[]` 是否补 `feature` + `rddf-session`

**Decision task**(在 PR review 讨论):

- 选项 A:补到 13 个(同步改 INSTALL.md description)
- **选项 B(推荐)**:保留 11 个,在 `package.json` 顶部加 `// src-only skills (not published via npm): feature, rddf-session — see skills/` 注释

输出:**Maintainer 在 PR review 时选定 A 或 B**,对应下方 2.2 或 2.3 任务执行。

- [ ] **Task 2.2 (若选 A)**: 把 `feature` 与 `rddf-session` 加入 `package.json::skills[]`

```bash
cd /workspace/project/spec-workflow
# 编辑 package.json,skills[] 末尾加入 "feature", "rddf-session"
# 同时改 description 字段,体现 13 个 skill
# 同时改 INSTALL.md description "全部 13 个子技能" → "全部 13 个子技能(均通过 npm 发布)"
```

- [ ] **Task 2.3 (若选 B)**: 保留 11 个,在 `package.json` 顶部加注释

```bash
cd /workspace/project/spec-workflow
# 在 package.json 顶部(license 字段后)插入注释行:
# 注意:JSON 标准不支持注释,需用 "_comment": "src-only skills (not in 'skills' array): feature, rddf-session"
# 同步在 USAGE.md skill 表下方加 "(feature + rddf-session 暂仅在仓库内可用,不在 npm 发布清单)"
```

- [ ] **Task 2.4**: 改 `USAGE.md`

具体修改:

1. 顶部 changelog note 加 `> **v2.0.2 (sync-workflow-contracts)**: ship-side phase count 由 5+1 升级为 7 编号子阶段`
2. Arch / Plan / Ship 三阶段表 L19 ship 端描述改为 `plan → verification → execute → review → archive → cleanup → ship-done(7 子阶段,编号 1, 1.5, 2, 2.5, 3, 4, 5)`
3. state-file 表 L57-58:`proposal-suggestions.md` 仍保留无点号;`.rddf/state/.arch-handoff.json` / `.rddf/state/.plan-handoff.json` / `.rddf/state/.deps-candidates.json` / `.rddf/state/.deps-output.md` 保留点号;`.rddf/state/deps-analysis.json` / `iteration.json` / `sessions.json` / `index.md` 保持生产无点路径;`roadmap-state.json` 点/无点混用需显式标注 canonical 决策;移除任何 undotted handoff.json 引用
4. skill 表(L95-111)保持 13 vs 11 的差异说明(显式标注 `feature` + `rddf-session` 状态)

- [ ] **Task 2.5**: 改 `AGENTS.md`

具体修改:

1. 关键目录树 `skills/` 段 L44-61:skill 计数 "12 个 .md" → "13 个 .md";在 INSTALL.md 后插入 `feature.md` 与 `rddf-session.md`(它们在仓库中可用,package.json 暂未注册)
2. `docs/adr/` 段 L70:`ADR-0001~0012 (12 个)` → `ADR-0001~0019 (19 个,加 ADR-0013 重复:extract-scan-state + incremental-skeleton-planning)`
3. 关键目录树 `openspec/` 段 L72:`已采纳的 capability specs (22 个)` → `已采纳的 capability specs (25 个)`
4. 常见陷阱 #11 保持 "`npm test` 不跑 Python" 不变(已有正确描述)

- [ ] **Task 2.6**: 改 `INSTALL.md`

具体修改:

1. description L3 保留 "13 个子技能" 数字
2. 末尾「元信息」表后追加 `## npm test vs pytest` 提示块:

```
## npm test vs pytest

> spec-workflow 的 CI 陷阱:`npm test` 只跑 bats,**不**跑 pytest。
> 任何 Python 代码改动后必须显式执行 `pytest tests/`。
> 反漂移测试 `tests/integration/test_doc_contracts.bats` 会断言本约束不被违反。
```

- [ ] **Task 2.7**: 改 `README.md`

具体修改:

1. 目录结构(L42-65):补全 `guide-arch.md` / `guide-plan.md` / `loop_engine.py` / `_lib/` 子目录
2. 「v2.0 新特性」段保留「三阶段架构」表格,但行内描述对齐到 7 编号子阶段

---

## 3. ADR 索引 / 编号审计

- [ ] **Task 3.1**: 改 `docs/adr/README.md` 顶部 status table

现状(L7-21)覆盖 0001-0012 + 0016(13 条)。扩展到:

- 0001-0019 全 19 条
- ADR-0013 后标 `⚠️ 同编号重复:extract-scan-state + incremental-skeleton-planning(后续 `init-deep` 决策)`
- ADR-0017 / 0018 / 0019 行补全(当前完全缺失)

- [ ] **Task 3.2**: 验证 ADR 列表表(L26-43)与顶部 status table 编号一致

如有缺漏,补全;如有重复,移除。

- [ ] **Task 3.3**: ADR-0013 dup 加显式 follow-up 任务

在 `docs/adr/README.md` 顶部 status table 上方加:

```
> ⚠️ **ADR-0013 dup**: 同编号重复(extract-scan-state + incremental-skeleton-planning)。
> 处理方案由后续 `init-deep` 决策决定;当前保留两个文件。
```

---

## 4. OpenSpec Spec 同步

- [ ] **Task 4.1**: 改 `openspec/specs/general/spec.md` 的 `general-docs-match-code` Requirement

具体 Scenarios 修改:

- **Scenario "USAGE.md ship-side phase count"**:5 阶段 + 1 退出 → 7 编号子阶段(plan → verification → execute → review → archive → cleanup → ship-done)
- **Scenario "USAGE.md state-file table"**:移除 `.sisyphus/plans/<name>.md` 与 `handoff.json`;加入 `.rddf/state/.arch-handoff.json` / `.rddf/state/.plan-handoff.json` / `.rddf/state/.deps-candidates.json` / `.rddf/state/.deps-output.md` / `.rddf/state/deps-analysis.json`;`roadmap-state.json` 需记录点/无点 canonical 决策而非假定统一点号
- 新增 Scenario "ship-side supports lightweight + worktree modes":断言 USAGE.md 描述 ⚡ 轻量与 🔀 worktree 两种模式,且 `find_default_branch` 在 worktree context 仍返回 default branch
- 新增 Scenario "package.json skills[] aligns with INSTALL.md description":断言 11 (npm) vs 13 (仓库) 的差异说明在两个文件都存在
- 修 **Scenario "proposal-suggestions-format lists all 5 consumers"**:移除 `guide-spec`(v2.0 已删除),加入 `guide-arch` + `guide-plan`

- [ ] **Task 4.2**: 改 `openspec/specs/doc-truth-sync/spec.md`

具体修改(在末尾新增 Section `## MODIFIED Requirements`):

```markdown
### Requirement: doc-contract-tests-required
The system SHALL provide anti-drift contract tests that catch silent rot between
documentation surfaces (USAGE.md, AGENTS.md, INSTALL.md, README.md, package.json,
docs/adr/README.md) and OpenSpec specs. The tests MUST fail CI (error severity)
when any of the following drift:
- skill count in package.json vs on-disk `skills/*.md`
- ADR count or numbering between docs/adr/README.md and actual `docs/adr/ADR-*.md` files
- ship-side phase count between USAGE.md and general/spec.md
- state-file path conventions (dotted vs undotted) across USAGE.md and general/spec.md
- `npm test` script no longer triggers only `bats tests/` (the npm-vs-pytest caveat)

#### Scenario: skill count drift is caught
- **WHEN** a contributor adds a new `skills/foo.md` without updating package.json
- **AND** CI runs `bats tests/integration/test_doc_contracts.bats`
- **THEN** the test exits 1
- **AND** stderr identifies which doc reports the stale count

#### Scenario: ADR index references nonexistent file
- **WHEN** `docs/adr/README.md` lists an ADR number with no corresponding `ADR-NNNN-*.md` file
- **AND** CI runs `bats tests/integration/test_adr_index.bats`
- **THEN** the test exits 1
- **AND** stderr identifies the missing ADR file

#### Scenario: package.json skills drift from on-disk truth
- **WHEN** `package.json::skills[]` lists 12 skills but `ls skills/*.md` returns 13
- **AND** CI runs `pytest tests/unit/test_doc_contracts.py`
- **THEN** the test exits 1
- **AND** stderr reports the discrepancy

#### Scenario: state-file path dotted/undotted inconsistency
- **WHEN** general/spec.md references `handoff.json` (undotted) but USAGE.md uses `.rddf/state/.arch-handoff.json` (dotted)
- **AND** CI runs `bats tests/integration/test_doc_contracts.bats`
- **THEN** the test exits 1
- **AND** stderr identifies the inconsistent path

#### Scenario: npm test trap regression
- **WHEN** a contributor modifies `package.json::scripts.test` to include pytest
- **AND** CI runs `bats tests/integration/test_doc_contracts.bats`
- **THEN** the npm-test-vs-pytest test exits 1
- **AND** stderr reminds: "npm test MUST only run bats; pytest is a separate command"
```

---

## 5. Anti-drift 测试(新增)

> 三个测试是本 change 的核心 enforcement layer。每条都遵循 TDD:写失败测试 → 看红 → 改 doc 让测试通过 → 看绿。

- [ ] **Task 5.1**: 新增 `tests/integration/test_doc_contracts.bats`

TDD Step 1 — 写失败测试。`@test` 用例至少包含:

- `doc_truth_sync: USAGE.md and general/spec.md agree on ship-side phase count`
- `doc_truth_sync: state-file paths use dotted prefix convention (.rddf/state/.X)`
- `doc_truth_sync: AGENTS.md skill count matches `ls skills/*.md | wc -l` (13)`
- `doc_truth_sync: package.json::skills[] count aligns with INSTALL.md description delta note`
- `doc_truth_sync: `npm test` script contains only bats invocation (pytest caveat)`

每个 `@test` 用稳定锚点(`grep -F` 完整字符串 + 显式 ignore 注释行),不要脆弱正则。

- [ ] **Task 5.2**: 新增 `tests/integration/test_adr_index.bats`

TDD Step 1 — 写失败测试:

- `adr_index: docs/adr/README.md status table covers all real ADRs (0001-0019)`
- `adr_index: docs/adr/README.md does not reference deleted ADR numbers`
- `adr_index: duplicated ADR-0013 is explicitly flagged in README.md`

实现用 `find docs/adr -name 'ADR-NNNN-*.md' | sort` 列真实文件,正则提取 README 引用的编号,断言子集关系。

- [ ] **Task 5.3**: 新增 `tests/unit/test_doc_contracts.py`

TDD Step 1 — 写失败测试。Python pytest 用例:

- `test_general_spec_no_guide_spec_reference`:断言 `openspec/specs/general/spec.md` 不包含字面 `guide-spec`(v2.0 已删除)
- `test_general_spec_phase_count_matches_usaged`:读取 USAGE.md 的 Phase 数,断言 general/spec.md Scenario 与之一致
- `test_install_description_skill_count_matches_disk`:读取 INSTALL.md description 抽取数字,断言等于 `len(ls skills/*.md)`
- `test_package_json_skills_count_within_delta`:断言 `package.json::skills[]` 长度 ≤ 磁盘 skill 数 + 2(允许 src-only 显式标注)
- `test_state_file_paths_dotted`:grep `general/spec.md` 出现的 handoff/plan-handoff/deps-candidates/deps-output/deps-analysis/roadmap-state/iteration/sessions/index,断言全部以 `.` 前缀出现

---

## 6. 验证(Verification)

> 全部 anti-drift 测试通过 + 既有测试无回归 + CI 门控不破坏。

- [ ] **Task 6.1**: 跑新增 anti-drift 测试

```bash
cd /workspace/project/spec-workflow
bats tests/integration/test_doc_contracts.bats
bats tests/integration/test_adr_index.bats
pytest tests/unit/test_doc_contracts.py -v
```

Expected: 三个测试全绿。

- [ ] **Task 6.2**: 跑既有测试,确认零回归

```bash
cd /workspace/project/spec-workflow
python3 -m pytest tests/unit/ -q --tb=short
python3 -m pytest tests/integration/ -q --tb=short
bats tests/smoke.bats
```

Expected: 所有既有测试继续通过(28+ unit / 51 integration / 7 smoke)。

- [ ] **Task 6.3**: 跑 openspec validate 确认 change artifacts 合法

```bash
cd /workspace/project/spec-workflow
openspec validate sync-workflow-contracts
```

Expected: PASS(若 validator 报 MODIFIED target 不存在,说明 spec.md target 写错,需检查 spec delta 路径)。

- [ ] **Task 6.4**: 跑 CI 质量门控

```bash
cd /workspace/project/spec-workflow
# 恒真断言门控
grep -rn "assert.*or True\|assert True" tests/ | head -5
echo "exit=$?"

# openspec CLI 校验
openspec list --specs
```

Expected: 恒真断言 grep 无命中(空输出,exit 1 from grep means no match);`openspec list --specs` 列出 25 个 spec。

- [ ] **Task 6.5**: 端到端反漂移验证

```bash
# 故意制造一个 drift,确认 anti-drift test 能抓住
cd /workspace/project/spec-workflow
# (临时)把 USAGE.md 中 "Phase 1.5" 改成 "Phase 1.6"
sed -i.bak 's/Phase 1\.5/Phase 1.6/' USAGE.md
bats tests/integration/test_doc_contracts.bats 2>&1 | tail -10
# 应该 exit 1,且 stderr 提到 phase 数不一致
# 然后恢复
mv USAGE.md.bak USAGE.md
bats tests/integration/test_doc_contracts.bats 2>&1 | tail -3
# 应该重新 exit 0
```

Expected: 第一轮 exit 1 且 stderr 指明漂移;恢复后 exit 0。

---

## 7. 提交与归档(Commit + Archive)

> 本 change 的 deliverable 已完成,按 spec-workflow 标准流程 commit + archive。

- [ ] **Task 7.1**: 提交 artifacts 到 git(在 worktree 内)

```bash
cd "$WT_PATH"
git add openspec/changes/sync-workflow-contracts/{.openspec.yaml,proposal.md,design.md,tasks.md,specs/doc-truth-sync/spec.md,specs/general/spec.md}
git add tests/integration/test_doc_contracts.bats tests/integration/test_adr_index.bats tests/unit/test_doc_contracts.py
git add USAGE.md AGENTS.md INSTALL.md README.md package.json docs/adr/README.md
git add openspec/specs/general/spec.md openspec/specs/doc-truth-sync/spec.md
git commit -m "feat(contracts): sync-workflow-contracts + anti-drift tests

- Synchronize USAGE/AGENTS/INSTALL/README/package.json/ADR/spec docs
- Update general-docs-match-code Scenarios to v2.0.1 (7 subphases + dotted paths + drop guide-spec)
- Add doc-contract-tests-required Requirement to doc-truth-sync spec
- Add 3 anti-drift tests (2 bats + 1 pytest) to lock cross-doc consistency
- ADR-0013 dup explicitly flagged (deferred to init-deep decision)"
```

- [ ] **Task 7.2**: 走 `guide-ship` 流程归档

按 `USAGE.md` Phase 1 → Phase 5 标准流程:

1. Phase 1(Plan):进入 worktree / 轻量分支,生成 `.rddf/plans/sync-workflow-contracts.md`
2. Phase 2(Execute):阻塞执行本 tasks.md 全部任务
3. Phase 3(Archive):`openspec archive sync-workflow-contracts --yes`
4. Phase 4(Cleanup):清理 worktree / branch
5. Phase 5(Ship-done):rddf-session 关闭

- [ ] **Task 7.3**: 归档后验证

```bash
cd /workspace/project/spec-workflow
ls openspec/changes/archive/ | grep sync-workflow-contracts
# 应该看到 2026-07-11-sync-workflow-contracts/ 目录
```

Expected: 归档目录出现。

---

## 8. Acceptance Criteria(本 tasks.md 完成判定)

> 与 proposal §Acceptance Criteria 一致。

- [ ] USAGE.md ship-side phase 表显式列出 7 编号子阶段
- [ ] USAGE.md state-file 表全部点号前缀(.rddf/state/.X)
- [ ] USAGE.md skill 表保留 13 vs 11 差异说明
- [ ] AGENTS.md skill 数 13 / ADR 数 21 实 + 1 重
- [ ] INSTALL.md description 保留 13,新增 npm-vs-pytest 块
- [ ] `package.json` 决策落地(A 或 B 之一)
- [ ] `docs/adr/README.md` 顶部 status table 覆盖 0001-0019,ADR-0013 dup flag
- [ ] `general/spec.md::Requirement general-docs-match-code` 全部 Scenarios 更新到 v2.0.1
- [ ] `doc-truth-sync/spec.md` 新增 `doc-contract-tests-required` Requirement
- [ ] 3 个 anti-drift 测试全绿
- [ ] 既有 pytest + bats 测试零回归
- [ ] `openspec validate sync-workflow-contracts` PASS
- [ ] CI 恒真断言门控不破坏

## 9. Follow-ups(显式推迟)

> 本 change scope 外但已识别的问题,留给后续 change。

- [ ] **Follow-up F1**: ADR-0013 dup 处理(`init-deep` 决策)
- [ ] **Follow-up F2**: `package.json::skills[]` 决策何时从 B 升到 A(`feature` 与 `rddf-session` API 稳定后)
- [ ] **Follow-up F3**: `docs/v2-adr-summary.md` 是否存在并需更新(本 change 未审计该文件)
- [ ] **Follow-up F4**: `roadmap-state.json` 点/无点混用收敛为单独 change;本 change 只暴露 drift 并要求维护者选择 canonical path,不执行 rename