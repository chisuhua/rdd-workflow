---
优先级: P1
来源: 2026-11-05 归档收尾审查 — tests/KNOWN_FAILURES.txt 的 11 条基线失败中有 6 条同根因（AGENTS.md 缺 "Worktree Commit Flow" 段），且这 6 条标注的跟踪项 feat-doc-drift-cleanup 在 .rddf/roadmap/features/ 下不存在，缺陷当前无任何活跃归属
阶段: v5.x
分类: docs
类型: documentation
---

**优先级**: P1 | **来源**: 2026-11-05 归档收尾审查 — KNOWN_FAILURES 11 条基线失败中 6 条同根因（AGENTS.md 缺 "Worktree Commit Flow" 段），标注的跟踪项 `feat-doc-drift-cleanup` 不存在
**阶段**: v5.x | **分类**: docs | **类型**: documentation

> **范围定位**：本提案**只改文档 + 刷新基线**，不改任何代码路径。断言来源是既有的 `tests/integration/test_worktree_archive_workflow_docs.bats`（6 个用例，自 `worktree-archive-workflow` change 起就存在），本提案让实现追上早已写好的断言。

## Why

### 现象

`tests/KNOWN_FAILURES.txt` 现有 **11 条**基线失败，其中 **6 条**指向同一个缺口：

```
AGENTS.md: Worktree Commit Flow section exists
AGENTS.md: Worktree Commit Flow mentions execute and archive phases
AGENTS.md: Worktree Commit Flow lists 5 conventional commit types
AGENTS.md: trap #6 updated to mention worktree-internal commit
AGENTS.md: trap #6 cross-references Worktree Commit Flow
AGENTS.md: 归档流程 cross-references check_worktree_commits
```

这 6 条的 `# 备注` 都写着 `tracked in feat-doc-drift-cleanup` / `fix in feat-doc-drift-cleanup` —— 但 `.rddf/roadmap/features/` 下**没有** `feat-doc-drift-cleanup` 这个 fragment（当前 8 个 fragment 已全部 `done`，无一对应）。即：**缺陷存在，归属丢失**。

> **「归属丢失」的准确表述**：该 fragment 名是 **2026-10-08 那次 selective refresh 登记基线时手写的占位**（`KNOWN_FAILURES.txt` L60 记 `kept=1, removed=9, added=20`），**从未被创建** —— 不是后来被删。因此读者去 `.rddf/roadmap/features/` 里找「被误删的 fragment」是找不到的。
>
> 同样的占位出现在**另外 2 条** SKILL.md description 失败的备注里（同样指向 `feat-doc-drift-cleanup`）—— 即 11 条里有 **8 条**挂着这个虚构跟踪项，剩余 3 条各自指向另一个 TBD 占位（`feat-rdd-env-bootstrap-help-audit` / `feat-rdd-builder-idempotency-audit` / `feat-rdd-builder-5-segment-rewrite`）。**基线登记环节允许虚构跟踪项**，这与文件尾注揭露的 skill-count drift 隐身是同一模式。

### 缺口是怎么形成的

`worktree-archive-workflow` change 落地时，约定被写进了**提案文档**（`.rddf/improvements/worktree-archive-workflow.md` §Worktree Commit Flow），内容是完整的：

- Phase 2 execute：改文件 + 跑测试 + 更新 plan checkbox，**不逐任务 commit**
- Phase 2 完成后：在 worktree 内用 conventional commit 提交 working tree
- Phase 3 archive：`archive_change_for_mode` 自动 merge → openspec archive → cleanup

但约定**没有同步进 AGENTS.md**。测试注释说得很直白（`test_worktree_archive_workflow_docs.bats` L6-11）：v4 把 `rdd-builder/SKILL.md` 的 "Phase 2.7" 瘦身后，那段内容「is now consolidated in AGENTS.md」—— 实际上并没有 consolidated 进去。

### 为什么现在值得修

1. **归属丢失**：6 条失败挂着不存在的 fragment，既不在 roadmap 视野里，也不在任何 improvement 的 Acceptance 里 —— 不会被任何人推进。
2. **文档说的是相反的话**：AGENTS.md 现有的 trap 规则写「execute 阶段不逐任务 commit」，而 `_lib/archive.sh::archive_change` 通过 `check_worktree_commits` 要求 worktree 分支**必须有 commit**。新用户/agent 读 AGENTS.md 会直接撞上「execute 不 commit 但 archive 需要 commits」的矛盾 —— 这正是原提案要消除的那个矛盾。
3. **杠杆最高**：11 条已知失败里 6 条归零，基线一次性瘦身过半。

### 不在本提案范围

另外 5 条已知失败（2 条 SKILL.md description 漂移、1 条 `rddf env-bootstrap --help` flags、1 条 `mark_approved_completed` 幂等、1 条 `phase0_approval.sh --auto-approve` 5 段）各有独立根因，且其中 3 条的跟踪项同样是 TBD 占位（`feat-rdd-env-bootstrap-help-audit` / `feat-rdd-builder-idempotency-audit` / `feat-rdd-builder-5-segment-rewrite`）。**本提案不碰它们** —— 一文档一决策，另案处理。

## What Changes

1. **AGENTS.md 新增 `### Worktree Commit Flow` 段**，内容取自 `.rddf/improvements/worktree-archive-workflow.md`（不重新发明），并满足既有断言：

   | 断言 | 段内须含（**按测试的真实语义写**） |
   |---|---|
   | `section exists` | **H3** 标题行 `### Worktree Commit Flow` —— 注意原提案用的是 `##`（H2），照抄原提案格式会挂测试 1（测试锚 `^###`） |
   | `mentions execute and archive phases` | 字面量 `Phase 2 execute` 与 `Phase 3 archive` |
   | `lists 5 conventional commit types` | ≥ 5 行匹配 `   - \`<type>(<scope>):` —— **3 空格缩进（非 4）+ 反引号包裹 + 全局匹配**（不限本段内） |
   | `trap #6 updated to mention worktree-internal commit` | 「execute 阶段不逐任务 commit」**所在行本身**须含 `worktree-internal commit` 或 `worktree 内做 1 个聚合 commit` —— 测试是**无 `-A`** 的 `grep`，锚匹配行而非其后 2 行 |
   | `trap #6 cross-references Worktree Commit Flow` | 同上匹配行后 2 行内含 `Worktree Commit Flow`（测试用 `grep -A 2`） |

   > **`trap #6` 是历史命名**：它来自旧版 AGENTS.md 的编号陷阱列表，当前仓库**没有**那个列表（全仓 grep 无「trap #6」列表）。测试只锚「execute 阶段不逐任务 commit」这一行字面文本，与编号无关。实施者**不要**去恢复一个编号陷阱列表。

   可直接通过测试 4 / 5 的示例行：

   ```
   - execute 阶段不逐任务 commit；Phase 2 全部 task 通过后，在 worktree 内做 1 个聚合 commit（worktree-internal commit），详见 Worktree Commit Flow
   ```

   完整示例段（2026-11-05 已实测：6/6 断言通过）：

   ```markdown
   ### Worktree Commit Flow

   每个 change 在 worktree 内执行时：

   1. **Phase 2 execute**：修改文件 + 运行测试 + 更新 plan checkboxes（`-[ ]` → `-[x]`）。
      - execute 阶段不逐任务 commit；Phase 2 全部 task 通过后，在 worktree 内做 1 个聚合 commit（worktree-internal commit），详见 Worktree Commit Flow
      - `feat(<scope>): <description>` for new features
      - `fix(<scope>): <description>` for bug fixes
      - `test(<scope>): <description>` for test changes
      - `chore(<scope>): <description>` for tooling changes
      - `docs(<scope>): <description>` for documentation changes

   2. **Phase 3 archive**：由 `ship_archive.sh::archive_change_for_mode` 自动 merge → openspec archive → cleanup worktree/branch。

   ### 归档流程

   归档前由 `check_worktree_commits` 强制 worktree 分支相对默认分支有新 commit，否则拒绝归档。
   ```

2. **5 种 commit type**：`feat` / `fix` / `test` / `chore` 取自原提案；第 5 种补 `docs`（文档变更）—— 原提案只列了 4 种，断言要求 ≥ 5 种。实现侧无冲突：`_lib/archive.sh::check_worktree_commits` **不校验** commit type 白名单，因此 AGENTS.md 承诺 5 种不构成实现约束（也不要顺手在 archive.sh 加 type 校验 —— 超出本提案「不改代码」范围）。

3. **AGENTS.md 新增 `### 归档流程` 段**，段内 8 行内出现 `check_worktree_commits`（与「Worktree Commit Flow」交叉引用）。

   > **位置约束**：两个新段加在 AGENTS.md **正文区**，**不得**插入 `<!-- AUTO: feature fragments start -->` 或 `<!-- AUTO: objectives start -->` 哨兵段内部 —— 哨兵段由 `rddf roadmap --update-agent-md` 重写，插入其中会被下次更新静默抹掉。建议 `### 归档流程` 紧邻现有的 `### Archive 前全量回归门（MANDATORY）` 段。

4. **刷新 `tests/KNOWN_FAILURES.txt`**：6 条转绿后移除对应基线条目，基线 11 → 5。

   > **执行顺序（不可颠倒）**：
   > 1. 先跑 `bash tests/scripts/report_regression.sh` 确认 **新增失败 = 0**；
   > 2. 再跑 `bash tests/scripts/refresh_known_failures.sh --dry-run`，核对 diff 期望 `removed=6, added=0`（summary 行 `kept=5`）；
   > 3. 核对通过后才实跑 refresh。
   >
   > **为什么顺序重要**：selective refresh 会把**实施窗口内的任何新失败**一并吸收进基线（它收集的是当前全部失败，减去仍在基线中的部分）。先 refresh 后跑回归，被吸收的新失败就从「新增失败」里消失了 —— 基线会把新回归洗白，**新增失败 = 0** 就失去意义。

**不改**：任何 `.sh` / `.py` / `.bats` 文件；`_lib/archive.sh`；`rdd-builder/SKILL.md`；其余 5 条已知失败条目。

## Acceptance

- [ ] `bats tests/integration/test_worktree_archive_workflow_docs.bats` ⇒ 6/6 通过
- [ ] `grep -c "^### Worktree Commit Flow" AGENTS.md` ≥ 1
- [ ] `grep -cE "^   - \`[a-z]+\(<scope>\):" AGENTS.md` ≥ 5
- [ ] `grep -A 8 "^### 归档流程" AGENTS.md` 含 `check_worktree_commits`
- [ ] `grep "execute 阶段不逐任务 commit" AGENTS.md` 的**匹配行本身**含 `worktree-internal commit` 或 `worktree 内做 1 个聚合 commit`
- [ ] `bash tests/scripts/report_regression.sh` ⇒ **新增失败 = 0**（**先于** refresh 执行，见 What Changes 4）
- [ ] `bash tests/scripts/refresh_known_failures.sh --dry-run` 的 diff 期望 `removed=6, added=0`（summary `kept=5`）；核对通过后实跑 refresh
- [ ] `git diff tests/KNOWN_FAILURES.txt` **仅**含 6 条 AGENTS.md 条目的移除与一条 summary 注释，**无非注释新增行**（防止 refresh 把别的新失败吸收进来）
- [ ] `tests/KNOWN_FAILURES.txt` 条目数 11 → 5，且剩余 5 条与本提案无关
- [ ] `rddf doctor --category docs-consistency` 无新增 finding（新段内**不得**写「per ADR-00XX」这类未经核对的 ADR 引用 —— `docs_consistency` 会扫 AGENTS.md 的 ADR 编号引用并对磁盘缺失报 WARNING）

## Capabilities

**不新增 capability。** 本提案只让 AGENTS.md 与既有断言对齐，不改变任何对外契约。

## Impact

| 维度 | 影响 |
|---|---|
| 运行时 | 无（纯文档） |
| 对外契约 | 无 |
| 测试 | 不改测试；`test_worktree_archive_workflow_docs.bats` 由红转绿 |
| 基线 | `KNOWN_FAILURES.txt` 11 → 5（收紧基线是**收益**：后续新增失败更容易被看见） |
| 回滚 | 还原 AGENTS.md 两段 + 恢复 6 条基线条目，无副作用 |
| 后续 | 其余 5 条已知失败的归属丢失问题仍在（本提案明确不碰），需要时按同样方式逐条补 improvement |
