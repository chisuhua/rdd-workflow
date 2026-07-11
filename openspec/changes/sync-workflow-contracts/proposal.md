---
SCOPE: shared
STATUS: PROPOSED
---

## Why

最近一次 `USAGE.md` 大改后,仓库内的文档/契约在多个维度上彼此不一致,与生产代码也对不上。当前审计识别出至少 7 类漂移,继续放任会导致用户读到错误的 phase 数 / skill 数 / ADR 数 / 路径,后续 contributor 也会反复踩坑:

**漂移 1 — `.rddf/state/` 路径约定:点号 vs 无点号混用**

`USAGE.md` 已经升级到 `.rddf/state/.arch-handoff.json` / `.rddf/state/.plan-handoff.json`(点号前缀,gitignored),但 `openspec/specs/general/spec.md::Requirement general-docs-match-code::Scenario USAGE.md state-file table` 仍把 handoff 写作 `handoff.json`(无点号),并把 plan 路径写作 `.sisyphus/plans/<name>.md`(错的目录)。生产代码 `skills/_lib/iteration.py` / `skills/_lib/deps_output.py` 早就是点号前缀,docs/specs 必须跟上。

**漂移 2 — Ship 端 Phase 计数从「5 阶段 + 1 退出」升级到「7 编号子阶段」**

`USAGE.md` 现在描述 ship 端为 **Phase 1, 1.5, 2, 2.5, 3, 4, 5** 共 7 个编号子阶段(plan → verification → execute → review → archive → cleanup → ship-done)。但 `general/spec.md::Scenario USAGE.md ship-side phase count` 仍要求 "5 阶段 + 1 退出",这与生产 `guide-ship.md` 不符。

**漂移 3 — Phase 2.5 Review 在 spec 里被忽略**

USAGE.md 已经把 Phase 2.5 Review(execute 后债务扫描)列为 ship 端核心阶段,`skills/_lib/gate.py::review_debt_recorded` 也是 warning 级门控实现。但 general spec 没有覆盖 review phase 的契约,导致 `general-docs-match-code` 漏掉这个新阶段。

**漂移 4 — ⚡ 轻量模式 vs 🔀 Worktree 模式无 spec 覆盖**

`USAGE.md` 用两节篇幅描述轻量/worktree 自动检测(`git worktree list` 第三列匹配 + `find_default_branch` + 默认分支 merge),但 `general/spec.md::Requirement general-harden-doc-consistency::Scenario find_default_branch works in worktree context` 只覆盖了 default branch,不覆盖轻量模式下的退化路径(branch 直 merge,无 worktree remove)。结果:轻量模式在 spec 里完全没有契约,只有文档描述。

**漂移 5 — Skill 计数 / package manifest 不一致**

| 来源 | 数字 |
|------|------|
| `ls skills/*.md` | 13 |
| `skills/INSTALL.md` description | "13 个子技能" |
| `USAGE.md` skill 表 | 13 + "package.json 当前仅注册 11" |
| `package.json::skills[]` | 11(缺 `feature` + `rddf-session`) |
| `AGENTS.md::关键目录` | "12 个 .md" — **过时** |
| `README.md::目录结构` | 仍列 12 个 skill + 多个旧路径 |

`AGENTS.md` 是 contributor 第一入口,数字必须反映磁盘真相。`package.json` 是否补全 `feature` + `rddf-session` 是一次显式决策(发布节奏 vs API 稳定性),需要在 proposal 里做出选择。

**漂移 6 — ADR 索引与编号漂移**

`docs/adr/` 当前有 22 个 Markdown 文件:1 个 `README.md` + 1 个 `ADR-0000-template.md` + 20 个实体 ADR 文件。实体 ADR 覆盖 19 个唯一编号(0001-0019),其中 ADR-0013 有两个文件(`extract-scan-state` 与 `incremental-skeleton-planning`)。但:

- `AGENTS.md::ADR 规范` 仍写 "ADR-0001~0012(12 个)"
- `docs/adr/README.md` 顶部的 v2.0 ADR 状态表覆盖 0001-0012 + 0016(13 条),漏掉 ADR-0013(且 `ADR-0013-extract-scan-state.md` 与 `ADR-0013-incremental-skeleton-planning.md` **同编号重复**)、0014、0015、0017、0018、0019
- 下方 ADR 列表表(L26-43)又确实包含了 0016-0019 — 上下两个表自相矛盾
- 这意味着新 contributor 看顶部 status table 会以为 ADR-0017/0018/0019 不存在,跳过对齐检查

**漂移 7 — `npm test` vs `pytest` 陷阱缺乏 contract test**

`USAGE.md` 与 `AGENTS.md` 都明确警告 "`npm test` 只跑 bats,不跑 Python 测试",但没有任何测试**强制**这条约束。如果哪天有人改 `package.json::scripts.test` 加了 `pytest tests/`,约束失效但 CI 不会失败。需要一个 contract test 把这条 caveat 钉住。

**根因**:以上 7 类问题都是同一类根因 — 不同 surface(RESEARCH/USAGE/AGENTS/INSTALL/spec/code)各自演进,缺一个对账机制把它们锁在一起。

## What Changes

**本 change 不实现任何新的运行时工作流行为。** 它只做三件事:

1. **同步契约**:把 USAGE / AGENTS / INSTALL / README / package.json / ADR 索引 / openspec specs 之间的不一致字段对齐到生产 skill 代码的事实真相。
2. **更新 spec**:对 `openspec/specs/general/spec.md::Requirement general-docs-match-code` 和 `openspec/specs/doc-truth-sync/spec.md` 做 MODIFIED Requirements,把目标字段更新到 v2.0.1 实际状态。
3. **加 anti-drift 测试**:新增 1 个 Python unit + 2 个 bats integration,持续检查各 surface 的一致性,任何一项漂移就让 CI 失败。

### 关键决策点(在 tasks.md / acceptance criteria 里有更细颗粒)

| 决策点 | 选项 | 推荐 |
|--------|------|------|
| `package.json::skills[]` 是否补 `feature` + `rddf-session` | A: 现在补(对内可见) / B: 保持 src-only + 显式注释说明 | **B**(v2.0.1 暂保留 src-only,加注释) |
| ADR-0013 重复文件如何处理 | A: 重新编号其中一个 / B: 合并内容到单文件 / C: 在 README 显式 flag | **C**(先 flag,等 `init-deep` 决策后处理) |
| doc contract test 失败是否阻断 archive | A: warning(只警告) / B: error(阻断 archive) | **B**,对齐现有 `gate.py` 的 error/warning 分级 |

## Impact

- **影响文件**(全部为文档 / spec / 测试,无生产代码):
  - `USAGE.md` — phase 表 + state-file 表 + skill 表
  - `AGENTS.md` — skill 计数、ADR 计数、关键目录树、关键约定表的若干字段
  - `INSTALL.md` — skill description 加 "npm test vs pytest" 反 drift 注脚
  - `README.md` — 目录结构补 guide-arch.md / guide-plan.md / loop_engine.py / `_lib/`
  - `package.json` — skills[] 决策(见上表)
  - `docs/adr/README.md` — v2.0 status table 补到 0001-0019;duplicated ADR-0013 加 flag
  - `openspec/specs/general/spec.md` — `general-docs-match-code` Scenarios 整体刷新到 v2.0.1
  - `openspec/specs/doc-truth-sync/spec.md` — 新增 `doc-contract-tests-required` Requirement
  - `tests/integration/test_doc_contracts.bats` — 新增(~120 LOC)
  - `tests/integration/test_adr_index.bats` — 新增(~50 LOC)
  - `tests/unit/test_doc_contracts.py` — 新增(~80 LOC)
- **破坏性变更**:无。所有变更都是文档/spec/测试,运行时零变更。
- **API 变更**:无。
- **外部依赖**:无新增。
- **跨仓影响**:无。spec-workflow 是元仓,不影响 TaskRunner / UsrLinuxEmu。
- **运行时影响**:**零**。这是契约同步 change,不动 skill 状态机、不动 gate、不动 deps / iteration。

## Acceptance Criteria

- [ ] USAGE.md ship-side phase 表显式列出 7 个编号子阶段(Phase 1, 1.5, 2, 2.5, 3, 4, 5),与 `guide-ship.md` 一致
- [ ] USAGE.md state-file 表只列磁盘真实存在的文件,且 handoff/plan-handoff/arch-handoff 均为点号前缀路径
- [ ] USAGE.md skill 表保留 "13 个 .md / 11 个 in package.json" 的差异说明(显式决策 B)
- [ ] AGENTS.md skill 计数更新为 13,ADR 计数更新为 19 个唯一编号(0001-0019) / 20 个实体 ADR 文件(ADR-0013 重复)
- [ ] AGENTS.md 关键目录树的 `skills/` 与 `openspec/` 两段都与磁盘 `ls` 一致
- [ ] INSTALL.md description 保留 13 个子技能数,在末尾新增 "npm test vs pytest" 反 drift 提示块
- [ ] `package.json::skills[]` 决策落地(选 B:保留 11 个 + 加 `// src-only: feature, rddf-session` 注释,或选 A:补到 13 个)
- [ ] `docs/adr/README.md` 顶部 v2.0 status table 覆盖 0001-0019(19 个唯一编号 + ADR-0013 dup 标注,共 20 个实体 ADR 条目)
- [ ] `openspec/specs/general/spec.md::Requirement general-docs-match-code` 全部 Scenarios 更新到 v2.0.1:
  - ship-side phase 计数改为 7 编号子阶段
  - state-file 表移除 undotted 路径,加入 `.rddf/state/.plan-handoff.json` 与 `.rddf/state/.arch-handoff.json`
  - consumer 列表移除 `guide-spec`(v2.0 已删除),加入 `guide-arch` / `guide-plan`
- [ ] `openspec/specs/doc-truth-sync/spec.md` 新增 Requirement `doc-contract-tests-required`,Scenarios 锁定本 change 引入的 3 个测试
- [ ] `tests/integration/test_doc_contracts.bats` 新增且通过(断言:skill 数、ADR 数、phase 数、state-file 路径在 5 个 doc 文件之间一致)
- [ ] `tests/integration/test_adr_index.bats` 新增且通过(断言:`docs/adr/README.md` 引用的 ADR 文件全部存在,且不引用已删除文件)
- [ ] `tests/unit/test_doc_contracts.py` 新增且通过(断言:spec 文件之间不自相矛盾,且引用真实存在的 ADR 编号)
- [ ] `pytest tests/unit/` 全套通过(30 既有 + 1 新)
- [ ] `bats tests/smoke.bats` 通过(无回归)
- [ ] CI 断言质量门控(`grep -rn "assert.*or True\|assert True" tests/`)不破坏

## Risk

| # | Risk | Mitigation |
|---|------|------------|
| 1 | 误改 USAGE.md phase 表破坏既有读者心智模型 | proposal 显式标注 v2.0.1 → v2.0.2 升级,在 USAGE.md 顶部加 changelog note |
| 2 | ADR-0013 dup 文件处理选错路径 | tasks.md 显式选 C(只 flag,不重编号);后续 `init-deep` 决策后再处理 |
| 3 | doc contract test 误报(grep 误匹配) | 测试用稳定锚点(如固定行号 + 行首匹配),加 `--ignore-case` 控制 |
| 4 | CI 时间增加(<1s vs 当前) | 三个测试都用 grep/ls/pytest.collect,无外部依赖 |
| 5 | 修改 general spec 触发其他 change 失效 | 通知 add-spec-validation-gates 维护者,确保 validation 不对 MODIFIED Requirements 误报 |
| 6 | `package.json` 决策走 A(补 skill)会改变 INSTALL skill 的描述字符串 | INSTALL.md description 需同步更新,tasks.md 已包含 |
| 7 | `docs/adr/README.md` 状态表从 13 条扩展到 21 条可能视觉过长 | 改用折叠(`<details>` 块)或在表前加 "见下方完整列表" 引导 |

## Supersession / Dependencies

- **不 supersede** 任何现有 change
- **不 supersede** `doc-truth-sync`(它归档后被本 change 视为前序,scope 在本 change 内被扩展)
- **依赖**:
  - `gate-mechanism`(anti-drift test 复用其 error/warning 分级)
  - `arch-discovery-contract` ADR-0016(保证 ADR 索引与 handoff path 一致)
- **解锁**:
  - 未来 `init-deep` 决策可以处理 ADR-0013 dup 问题
  - 未来 `harden-doc-contracts` 可以把 anti-drift test 推到 CI lint 层

## 不做什么(显式边界)

- ❌ 不修改任何 production skill 代码(`skills/*.md` 中 frontmatter 之外的 prose)
- ❌ 不修改 `openspec/` 之外的 spec 文件
- ❌ 不修改 `tests/` 之外的测试基础设施
- ❌ 不修改 `.github/workflows/test.yml`(新测试由现有 bats + pytest 步骤自动覆盖)
- ❌ 不创建 worktree / branch / commit / push
- ❌ 不修改 `.openspec.yaml` 之外的任何元仓配置