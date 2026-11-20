# retire-execute-skill 验收报告

- **change**: `openspec/changes/retire-execute-skill/`
- **日期**: 2026-11-20
- **验收方式**: **本地验收**（`rdd-verifier` skill 分流条件 2 不满足 —— `rddf rdd-verify --dry-run` ⇒ `No eligible changes to verify (empty queue)`；`.rddf/state/iteration.json` 中本 change 于验收前登记为 `in_worktree`，P3 archive gate 未触发）
- **已用轮次**: 1
- **本地验收额外门**: `.rddf/state/iteration.json` 中 `tasks_done == tasks_total > 0` ⇒ 92/92 ✓（口径：实施任务 T1–T16；T17 的验收/归档流程项本身不计入实施口径）
- **关联治理面**: opencode 仓 commit `c61124b`（`scripts/rdd-skills.sh` 的 `RDD_SKILLS_BUILTIN` 移除 `execute`；oracle `治理面判定: PASS-WITH-NOTES` → critic `APPROVE`）

## 判据来源

`openspec/changes/retire-execute-skill/proposal.md` 的 `## Acceptance` 段（AC-1 ~ AC-16）。

## 逐条判定

| AC | 判定 | 取证命令与结果 |
|---|---|---|
| AC-1 | **pass**（第 1 轮为判据缺陷，已闭合） | 实现：`test ! -d skills/execute` ✓；`test -f docs/legacy/skills/execute/SKILL.md` ✓；`find docs/legacy -name '__pycache__'` ⇒ 0 ✓；`docs/legacy/README.md:19` = `\| \`skills/execute/\` \| 2026-11-20 \| 退役 v2 遗留 plan 执行器子技能（…） \|` ✓。**第 1 轮**：proposal AC-1 与 tasks T12.3 的判据写作 `grep -Fq '\| skills/execute/ \| 2026-11-20 \|'`（漏反引号）⇒ 对实际行不命中 —— 判据缺陷，非实现缺陷（该行与 `:18` 的 guide 行格式一致，都带反引号）。**已路由回 builder 修判据（补反引号，不改 README）**；**复验**：`grep -Fq '\| \`skills/execute/\` \| 2026-11-20 \|' docs/legacy/README.md` ⇒ 命中 ✓ |
| AC-2 | **pass** | `python3 -c "…assert 'execute' not in d['skills'] and len(d['skills'])==27"` ✓；`python3 -m json.tool pyrightconfig.json` ✓；`! grep -q 'skills/execute' pyrightconfig.json` ✓ |
| AC-3 | **pass** | `bats tests/integration/test_skill_metadata_consistency.bats` ⇒ **2/2 ok**（package.json ↔ 磁盘 ↔ INSTALL.md 三向对齐） |
| AC-4 | **pass** | 13 个删除文件逐个 `test ! -e` ⇒ 全部不存在 ✓ |
| AC-5 | **pass** | `! grep -rq --exclude-dir=__pycache__ 'skills/execute\|skills\.execute' tests/` ⇒ **0 命中** ✓ |
| AC-6 | **pass** | `overview.md`：`\| \`execute\` \|` ⇒ 0；`\*\*27 skills\*\*.*22 sub-skills` ⇒ 1；`\| \`rdd-workflow-writing-plans\` \| … \| rdd-builder \|` ⇒ 1；`v4-pipeline-data-flow.md` 的 `execute/scripts` ⇒ 0；`workflow-phases.md` 的 `` `execute` (P2) `` ⇒ 0 ✓ |
| AC-7 | **pass** | `worktree-context-persistence/spec.md`：`RETIRED (2026-11-20, retire-execute-skill)` ⇒ **2**（Requirement 1 + 3；Requirement 2 保留）；`grep -cE 'skills/execute\|execute/SKILL\.md'` ⇒ **2**（每处 NOTE 内 1 次）✓；`add-rdd-quick-skill/spec.md` 的 `_lib/archive.sh` hash MUST 仍在 ⇒ 1 ✓；`fix-skill-layer-resolution-bash/spec.md` 的 `skills/execute/scripts/select_worktree.sh:16` ⇒ 0 ✓ |
| AC-8 | **pass** | `! grep -rqE 'execute/SKILL\.md\|execute/scripts\|skill_use\("execute"\)\|RDDF_EXECUTION_ROOT\|skills/execute\.md\|✅ \`execute\`\|\`execute\` \|' README.md AGENTS.md skills/INSTALL.md docs/ONBOARDING.md USAGE.md` ⇒ **0 命中** ✓（阶段动词 `P2 (execute)` / `plan → verification → execute → review` / ADR 文件名按设计保留） |
| AC-9 | **pass** | `! grep -q '编排 execute 子技能' skills/rdd-builder/SKILL.md` ✓；`! grep -rq 'skill_use("execute")' skills/rdd-workflow-writing-plans/SKILL.md skills/status/SKILL.md README.md USAGE.md` ✓；`! grep -q '与 execute.md 的契约' skills/rdd-workflow-writing-plans/SKILL.md` ✓ |
| AC-10 | **pass** | 整树 grep（`-I` + 4 个 `--exclude-dir`）过滤白名单后 ⇒ **为空** ✓ |
| AC-11 | **pass** | 本仓 root：`rdd-skills.sh --json` ⇒ `available[]` **27** 项，**不含 `execute`** ✓；治理仓 root：同 ✓ |
| AC-12 | **pass** | `test ! -e ~/.agents/skills/execute && test ! -L ~/.agents/skills/execute` ✓；`test ! -e ~/.agents/skills/guide && test ! -L ~/.agents/skills/guide` ✓（guide 是 ADR-0063 的遗留断链，本次顺手清） |
| AC-13 | **pass** | `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression` ⇒ **rc=0 / ALL PASSED**（`/tmp/opencode/exec-full2.log`）：未评估 0 / 已知失败 11 / **新增失败 0**；pytest unit **3439 passed** / 3 skipped；pytest integration **192 passed** ✓ |
| AC-14 | **pass** | 全部改动落在**单一提交** `c4dab232`；提交后 `git status --porcelain` ⇒ **0 行** ✓（`openspec/` 被 `.gitignore:45` 排除，其本地工件不在提交内 —— proposal 已注明不构成反证） |
| AC-15 | **pass** | `ls skills/*/SKILL.md \| wc -l` = **27**；`len(package.json::skills[])` = **27** ✓；文档提及：AGENTS.md 27 SKILL.md / 28 个子技能、README.md 28 个子技能、INSTALL.md 27 个子技能 ⇒ 全部 ∈ {27, 28} ✓（`skills/INSTALL.md:18` 的 v4.0.0 历史行按约定不计） |
| AC-16 | **pass** | **变异测试实跑**：向 README.md 注入一行 `skill_use("execute")` ⇒ `not ok 13 doc_drift_v4: README.md + USAGE.md have no live guide-*/execute skill invocations (AC-11)` + `# AC-11 violation: live skill_use("execute") in code block of README.md`；还原后 ⇒ `ok 13` ✓ |

## 失败项

**无（第 1 轮的 1 项已闭合）**

### 第 1 轮失败项与闭合记录

- **阻塞点**：`openspec/changes/retire-execute-skill/proposal.md` 的 AC-1 与 `tasks.md` 的 T12.3 使用 `grep -Fq '| skills/execute/ | 2026-11-20 |'`，但 `docs/legacy/README.md:19` 的实际行是 `| \`skills/execute/\` | 2026-11-20 | … |`（**带反引号**，与 `:18` 的 guide 行格式一致）⇒ 判据不命中。
- **需要什么决策**：把两处判据改为 `grep -Fq '| \`skills/execute/\` | 2026-11-20 |'`（补反引号），**不改** `docs/legacy/README.md`（该行格式与既有 guide 行一致，是正确的）。
- **已完成 / 未完成**：实施 100% 完成（T1–T16 全绿）；仅剩上述**计划工件的判据文字**待修。
- **建议下一步指令**：`sed` 修 proposal AC-1 与 tasks T12.3 两处判据（补反引号）→ verifier 复验 AC-1 → 勾 T17.1 → `openspec archive retire-execute-skill` → `rddf archive-sync`。
- **闭合证据**：builder 已按建议修两处判据（各 1 处命中，`git status` 仍为 1 行 = 本报告自身）；verifier 复验 ⇒ `grep -Fq '| \`skills/execute/\` | 2026-11-20 |' docs/legacy/README.md` **命中** ✓，其余四项判据仍全绿。

**分类**：`implementation_gap` 的**变体** —— 实现已满足，缺口在验收判据本身；修复面是 2 处判据文字（非实现代码），不触发回 builder 重做。

## 遗留清扫结果

| 项 | 结果 |
|---|---|
| TODO / FIXME / XXX / HACK | **本次 diff 未引入**（`git show HEAD \| grep '^+' \| grep -E '\b(TODO\|FIXME\|XXX\|HACK)\b'` ⇒ 0）。全仓命中 3 处均为**既有内容**：`USAGE.md:253/:258`（功能散文）、`docs/architecture/workflow-phases.md:136`（既有 KNOWN LIMITATION 注释）、`skills/rdd-workflow-writing-plans/SKILL.md:133`（占位符扫描清单） |
| 调试日志 / `breakpoint()` / `pdb` | **0**（本次 diff 无） |
| 注释掉的代码 | **0**（本次 diff 无 `+# if/for/while/def/return/print(` 形态） |
| 被 skip 的测试 | **无新增**（唯一 skip 命中是 `test_global_install_external_project.bats:13` 的既有 Skip-not-fail 策略注释） |
| 未替换的 mock / 临时 fallback | **0** |
| 恒假判据 | 本次新增的零残留守卫**已实跑变异测试验证会红**（AC-16），非恒绿 |
| 全局 symlink 残留 | **0**（`~/.agents/skills/` 由 43 → 41；execute 与 guide 两个断链均已清） |
| 跨仓 builtin 清单 | 27 项，精确等于上游 manifest；两 root 场景实测一致（AC-11） |

## 备注

1. **AC-7 的计数判据在实施中从 3 修正为 2**：proposal 初稿写「3 个 Requirement 各标 RETIRED」，实施时核实 `Requirement 2`（`archive.sh` 自动 cd 回主仓库）**不含任何 execute 引用**、应保留不动 ⇒ 实际退役 2 个。proposal / tasks / spec 三处已同步。
2. **`fix-skill-layer-resolution-bash/spec.md` 的额外处置**：除 T6.4 指定的先例改指外，该 spec 另有 2 处断言 `select_worktree.sh` 存在（`count SHALL be exactly 3`），归档后为假 ⇒ 已改为 2 并加注。
3. **AC-1 判据缺陷的来源**：判据在 proposal 起草时写成无反引号形态，而 README 表格行（沿用 guide 先例）带反引号 —— 属**判据未回读实际产物**，与本次 change 要消灭的「文档声称 ≠ 实现」是同一类错误模式。verifier 在取证阶段发现，未漏到归档。
4. **归档前置**：`openspec archive retire-execute-skill` 对本 change 无阻塞项；归档后由 `rddf archive-sync` 将 `iteration.json` 转为 `archived`（tasks 95/95）。
