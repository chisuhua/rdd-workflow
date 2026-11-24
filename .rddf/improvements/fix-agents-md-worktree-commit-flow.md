---
优先级: P1
来源: 2026-11-05 归档收尾审查 — tests/KNOWN_FAILURES.txt 的 10 条基线失败中有 6 条同根因（AGENTS.md 缺 "Worktree Commit Flow" 段），且其中 4 条标注的跟踪项 feat-doc-drift-cleanup 在 .rddf/roadmap/features/ 下不存在，缺陷当前无任何活跃归属
阶段: v5.x
分类: docs
类型: documentation
状态: 已实施并验收（2026-11-24 立项 → 归档为 2026-11-24-fix-agents-md-worktree-commit-flow；10/10 AC pass；KNOWN_FAILURES 基线 10 → 4）
---

**优先级**: P1 | **来源**: 2026-11-05 归档收尾审查 — KNOWN_FAILURES 10 条基线失败中 6 条同根因（AGENTS.md 缺 "Worktree Commit Flow" 段），其中 4 条标注的跟踪项 `feat-doc-drift-cleanup` 不存在
**阶段**: v5.x | **分类**: docs | **类型**: documentation

> **范围定位**：本提案**只改文档 + 刷新基线**，不改任何代码路径。断言来源是既有的 `tests/integration/test_worktree_archive_workflow_docs.bats`（6 个用例，自 `worktree-archive-workflow` change 起就存在），本提案让实现追上早已写好的断言。

## Why

### 现象

`tests/KNOWN_FAILURES.txt` 现有 **10 条**基线失败，其中 **6 条**指向同一个缺口：

```
AGENTS.md: Worktree Commit Flow section exists
AGENTS.md: Worktree Commit Flow mentions execute and archive phases
AGENTS.md: Worktree Commit Flow lists 5 conventional commit types
AGENTS.md: trap #6 updated to mention worktree-internal commit
AGENTS.md: trap #6 cross-references Worktree Commit Flow
AGENTS.md: 归档流程 cross-references check_worktree_commits
```

这 6 条里**有 4 条**的 `# 备注` 写着 `tracked in feat-doc-drift-cleanup` / `fix in feat-doc-drift-cleanup` —— 但 `.rddf/roadmap/features/` 下**没有** `feat-doc-drift-cleanup` 这个 fragment（当前 9 个 fragment 已全部 `done`，无一对应）。即：**缺陷存在，归属丢失**。

> **「归属丢失」的准确表述**：该 fragment 名是 **2026-10-08 那次 selective refresh 登记基线时手写的占位**（`KNOWN_FAILURES.txt` L61 记 `kept=1, removed=9, added=20`），**从未被创建** —— 不是后来被删。因此读者去 `.rddf/roadmap/features/` 里找「被误删的 fragment」是找不到的。
>
> 同样的占位还出现在**另外 1 条** SKILL.md description 失败的备注里（同样指向 `feat-doc-drift-cleanup`）—— 即 10 条里有 **5 条**挂着这个虚构跟踪项（4 条属上列 AGENTS.md 族、1 条是 SKILL.md description），剩余 5 条中另有 2 条（`trap #6` 的两条）属 AGENTS.md 族但**没写**跟踪项，其余 3 条各自指向另一个 TBD 占位（`feat-rdd-env-bootstrap-help-audit` / `feat-rdd-builder-idempotency-audit` / `feat-rdd-builder-5-segment-rewrite`）。**基线登记环节允许虚构跟踪项**，这与文件尾注揭露的 skill-count drift 隐身是同一模式。

### 缺口是怎么形成的

> **架构依据**：`ADR-0061`（archive gate refuses unmerged branch）确立了「归档前 worktree 分支必须相对默认分支有新 commit」这条硬门禁（`_lib/archive.sh::check_worktree_commits`）。AGENTS.md 是这条门禁的**人类可读面** —— 本提案补的就是这半边（门禁在代码里，约定却不在文档里）。

`worktree-archive-workflow` change 落地时，约定被写进了**提案文档**（`.rddf/improvements/worktree-archive-workflow.md` §Worktree Commit Flow），内容是完整的：

- Phase 2 execute：改文件 + 跑测试 + 更新 plan checkbox，**不逐任务 commit**
- Phase 2 完成后：在 worktree 内用 conventional commit 提交 working tree
- Phase 3 archive：`archive_change_for_mode` 自动 merge → openspec archive → cleanup

但约定**没有同步进 AGENTS.md**。测试注释说得很直白（`test_worktree_archive_workflow_docs.bats` L6-11）：v4 把 `rdd-builder/SKILL.md` 的 "Phase 2.7" 瘦身后，那段内容「is now consolidated in AGENTS.md」—— 实际上并没有 consolidated 进去。

### 为什么现在值得修

1. **归属丢失**：4 条失败挂着不存在的 fragment，既不在 roadmap 视野里，也不在任何 improvement 的 Acceptance 里 —— 不会被任何人推进。
2. **文档说的是相反的话**：AGENTS.md 现有的 trap 规则写「execute 阶段不逐任务 commit」，而 `_lib/archive.sh::archive_change` 通过 `check_worktree_commits` 要求 worktree 分支**必须有 commit**。新用户/agent 读 AGENTS.md 会直接撞上「execute 不 commit 但 archive 需要 commits」的矛盾 —— 这正是原提案要消除的那个矛盾。
3. **杠杆最高**：10 条已知失败里 6 条归零，基线一次性瘦身过半。

### 不在本提案范围

另外 4 条已知失败（1 条 SKILL.md description 漂移、1 条 `rddf env-bootstrap --help` flags、1 条 `mark_approved_completed` 幂等、1 条 `phase0_approval.sh --auto-approve` 5 段）各有独立根因，且其中 3 条的跟踪项同样是 TBD 占位（`feat-rdd-env-bootstrap-help-audit` / `feat-rdd-builder-idempotency-audit` / `feat-rdd-builder-5-segment-rewrite`）。**本提案不碰它们** —— 一文档一决策，另案处理。

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

4. **刷新 `tests/KNOWN_FAILURES.txt`**：6 条转绿后移除对应基线条目，基线 10 → 4。

   > **执行顺序（不可颠倒）**：
   > 1. 先跑 `bash tests/scripts/report_regression.sh` 确认 **新增失败 = 0**；
   > 2. 再跑 `bash tests/scripts/refresh_known_failures.sh --dry-run`，核对 diff 期望 `removed=6, added=0`（summary 行 `kept=4`）；
   > 3. 核对通过后才实跑 refresh。
   >
   > **为什么顺序重要**：selective refresh 会把**实施窗口内的任何新失败**一并吸收进基线（它收集的是当前全部失败，减去仍在基线中的部分）。先 refresh 后跑回归，被吸收的新失败就从「新增失败」里消失了 —— 基线会把新回归洗白，**新增失败 = 0** 就失去意义。

**不改**：任何 `.sh` / `.py` / `.bats` 文件；`_lib/archive.sh`；`rdd-builder/SKILL.md`；其余 4 条已知失败条目。

**Out of Scope**:
- 任何 `.sh` / `.py` / `.bats` 文件 —— 本提案**只改 `AGENTS.md` + `tests/KNOWN_FAILURES.txt`**
- `_lib/archive.sh::check_worktree_commits`（**不**加 commit type 白名单校验 —— AGENTS.md 承诺 5 种 type 不构成实现约束）
- `rdd-builder/SKILL.md` / `skills/rdd-arch/SKILL.md` 等任何 SKILL.md
- 其余 4 条已知失败条目（1 条 SKILL.md description 漂移 / 1 条 `rddf env-bootstrap --help` flags / 1 条 `mark_approved_completed` 幂等 / 1 条 `phase0_approval.sh --auto-approve` 5 段）—— 各自独立根因，另案处理
- `.rddf/roadmap/features/` 的 fragment 补登 —— `feat-doc-drift-cleanup` 是**从未创建**的虚构跟踪项，本提案通过移除这 6 条基线条目**消除**该虚构引用，而不是补建一个 fragment

## Acceptance

- [x] `bats tests/integration/test_worktree_archive_workflow_docs.bats` ⇒ 6/6 通过
- [x] `grep -c "^### Worktree Commit Flow" AGENTS.md` ≥ 1
- [x] `grep -cE "^   - \`[a-z]+\(<scope>\):" AGENTS.md` ≥ 5
- [x] `grep -A 8 "^### 归档流程" AGENTS.md` 含 `check_worktree_commits`
- [x] `grep "execute 阶段不逐任务 commit" AGENTS.md` 的**匹配行本身**含 `worktree-internal commit` 或 `worktree 内做 1 个聚合 commit`
- [x] `bash tests/scripts/report_regression.sh` ⇒ **新增失败 = 0**（**先于** refresh 执行，见 What Changes 4）
- [x] `bash tests/scripts/refresh_known_failures.sh --dry-run` 的 diff 期望 `removed=6, added=0`（summary `kept=4`）；核对通过后实跑 refresh
- [x] `git diff tests/KNOWN_FAILURES.txt` **仅**含 6 条 AGENTS.md 条目的移除与一条 summary 注释，**无非注释新增行**（防止 refresh 把别的新失败吸收进来）
- [x] `tests/KNOWN_FAILURES.txt` 条目数 10 → 4，且剩余 4 条与本提案无关
- [x] `rddf doctor --category docs-consistency` 无新增 finding（新段内**不得**写「per ADR-00XX」这类未经核对的 ADR 引用 —— `docs_consistency` 会扫 AGENTS.md 的 ADR 编号引用并对磁盘缺失报 WARNING）

## Capabilities

**不新增 capability。** 本提案只让 AGENTS.md 与既有断言对齐，不改变任何对外契约。

## Impact

| 维度 | 影响 |
|---|---|
| 运行时 | 无（纯文档） |
| 对外契约 | 无 |
| 测试 | 不改测试；`test_worktree_archive_workflow_docs.bats` 由红转绿 |
| 基线 | `KNOWN_FAILURES.txt` 10 → 4（收紧基线是**收益**：后续新增失败更容易被看见） |
| 回滚 | 还原 AGENTS.md 两段 + 恢复 6 条基线条目，无副作用 |
| 后续 | 其余 4 条已知失败的归属丢失问题仍在（本提案明确不碰），需要时按同样方式逐条补 improvement |

## 实施记录

**2026-11-24 · 立项 → 实现 → 归档（全绿）**

| 项 | 内容 |
|---|---|
| change | `2026-11-24-fix-agents-md-worktree-commit-flow`（`openspec/changes/archive/`） |
| 实现分支 | `openspec/fix-agents-md-worktree-commit-flow` → commit `4e503ed5`（已合入 master，合并 commit `merge(change): ...`） |
| 改动文件 | `AGENTS.md`（+18 行：两段）、`tests/KNOWN_FAILURES.txt`（10 → 4 条）、`.rddf/plans/fix-agents-md-worktree-commit-flow.md`（TDD 计划） |
| 代码改动 | **零**（未改任何 `.sh` / `.py` / `.bats`） |
| 验收 | 10/10 AC pass（verdict cache 锚点 = 分支 tip `4e503ed5`） |
| 门禁 | 主仓 `./test.sh --full --regression` **ALL PASSED**（bats 新增失败 0 / 未评估 0 / pytest unit 3641 passed 0 failed / integration 192 passed / validate 160 passed 0 failed） |
| spec delta | `openspec/specs/fix-agents-md-worktree-commit-flow/spec.md`（+10 requirements） |

### 实施期发现的两件事

**① 本改动一度引入真回归（已修）**：AGENTS.md 初稿写「做 **1 个** 聚合 commit」，触发 `tests/unit/test_doc_contracts.py::test_docs_do_not_hardcode_directory_composition_counts` —— 该守卫禁止文档硬编码「N 个 / N 条」这类会随文件增删漂移的构成计数。改为「做**聚合** commit」后既满足 bats 断言 4（匹配行仍含 `worktree-internal commit`），也满足漂移计数守卫。

**② worktree 模式下的 6 个 pytest 失败 —— 先验问题，非本 change 引入（仅记录，不在本 change 修）**：
在 worktree 内跑 pytest unit 时，`tests/unit/test_resolve_project_root_contract_python.py`（5 个）与 `tests/unit/test_skills_lib_python_resolve_project_root.py`（1 个）失败：测试常量 `PROJECT_ROOT = Path(__file__).resolve().parents[2]` 期望 **git toplevel**（= worktree 根），而 `resolve_project_root` 按 `consolidate-resolve-project-root-helpers` 的 **canonical normalization** 返回**主仓根**（= `/workspace/main/rdd-workflow`）—— 两者口径不同。

**基线对照**（证明与本 change 无关）：
- 主仓跑同一批测试 → **24 passed**；
- master 的 detached worktree（`030c09e0`，不含本 change 任何改动）跑同一批 → **同样 6 个失败**，一模一样。

⇒ 归因：**仓库既有**的「canonical normalization vs 契约测试旧口径」冲突，与 AGENTS.md / KNOWN_FAILURES 改动无因果关系。
处置：**仅记录**（范围外不顺手改）。需要时另案 —— 口径二选一：改测试期望为 canonical root，或让 resolver 在 worktree 内返回 worktree root；后者会改动 ADR-0033 / canonical 语义，需走架构评审。
影响面：worktree 模式下的全量门不可能全绿；本 change 的归档门证据因此取 **主仓（CI 等价环境）** 的一次全绿运行。

