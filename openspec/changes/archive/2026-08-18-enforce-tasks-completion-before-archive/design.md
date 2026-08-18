# enforce-tasks-completion-before-archive — Design

> Schema: spec-driven
> See: `proposal.md` for motivation, scope and acceptance criteria.

## Context

`_lib/archive.sh::archive_change` 中 `check_worktree_commits` (line 357) 强制 worktree 分支至少有 1 个 commit 才允许 archive,**未要求 tasks.md 完成度 = 100%**。审计 9 个已归档 change 发现:

- `migrate-improvements-to-rddf-namespace`: tasks.md **0/55**(!) 但已 archive — 实际功能完整(155 proposal links 全可解析、smoke 测试通过),但 task 勾选完全空。
- `complete-third-party-replay-and-upstream-reporting`: tasks.md 34/41(83%)— 7 个未勾选任务多为 meta("Run test"、"Update proposal")。
- `fix-generator-scope-extraction`: tasks.md 8/10(80%)— 2 个 meta 任务。
- 其他 6 个 100% 完成。

`rdd-doctor --category tasks-checkbox` 当前未实现(仅检查 `state` / `plan-tdd` / `roadmap-meta` / `proposal-table` 四类)。`harden-archive-iteration-sync`(commit `02fe62f`)已修复 iteration.json 同步,但未触及 tasks.md 完整性。本提案为 archive 主体流程补上 tasks.md 完成度校验 gate,遵循 ADR-0018 gate escalation 模式(默认 warning / `STRICT_*=yes` 升级 error / `SKIP_*=yes` 跳过)。

## Goals / Non-Goals

**Goals:**

- 在 `_lib/archive.sh::archive_change` 末尾(参考 step 8.5 tasks sidecar hook 位置,line 397)添加 `check_tasks_completion` 步骤
- 默认 warning 模式:输出 `"📋 tasks completion: <done>/<total> (<pct>%)"`,tasks < 100% 时打 warning 但 archive 继续
- `STRICT_TASKS_GATE=yes` 模式:tasks < 100% 直接阻断 archive,退出码 1(参照 `STRICT_CHANGE_GATE` escalation pattern)
- `SKIP_TASKS_GATE=yes` 模式:完全跳过校验(紧急 hotfix 路径,留 audit trail)
- 给 `rdd-doctor` 实现 `--category tasks-checkbox`:扫描 active + archived changes,列出完成度 < 100% 的 change 为 WARNING
- 新增 `tests/integration/test_archive_tasks_gate.bats` 验证 ≥5 关键场景

**Non-Goals:**

- 不修改已归档 change 的 tasks.md(保留历史状态)
- 不强制所有 change 必须勾选 tasks 才能 propose(仅在 archive 阶段校验)
- 不实现 tasks.md 自动勾选(AI 执行阶段已自动勾选,本提案只补校验)
- 不修改 `tasks_writeback.sh`(execute 阶段的回写逻辑已完整)
- 不实现"partial 完成"语义(`- [~]`、`- [WIP]` 等其他 checkbox 标记不被识别为完成,仅统计 `- [x]`)

## Decisions

### 1. tasks 完成度算法

`done = count("- [x]") + count("- [X]")`, `total = count of all "- [" lines`。`- [~]` / `- [WIP]` / `- [?]` 等其他标记归类为"未完成"(warning 时输出但不阻断 strict)。

**Alternatives considered:**

- 统计所有非 `- [ ]` 标记为完成:`- [~]` 也算完成 — 模糊"完成"语义,与 archived change 0/55 案例(都是 `- [ ]`)判断一致;但放弃区分 partial 状态,被否。
- 引入新的 checkbox 格式(`- [✓]`):破坏向后兼容,需改造所有 proposals 创建流程 — 被否。

### 2. hook 位置在 step 8 之后(step 8.5 之前)

放在 `mark_iteration_archived` (line 388) 之后、`tasks sidecar` (line 397) 之前。这样:

- iteration.json 已记录 archived 状态(便于 doctor 后续扫 archived)
- tasks sidecar 备份完整 tasks.md(本 gate 不会修改 tasks.md 内容)
- 失败容错:`|| true` 包裹,不影响 archive 主体

**Alternatives considered:**

- 放在 step 2(`check_worktree_commits`)之后:gate 失败时 iteration 未更新,doctor 难以追溯 — 被否。
- 放在 step 9(已删除的 cleanup 步骤)位置:archive 主体已完成,失败难以回滚 — 被否。

### 3. STRICT_TASKS_GATE 默认 OFF

`STRICT_TASKS_GATE=yes` 是 opt-in,与现有 `STRICT_CHANGE_GATE` 默认语义一致。存量 8 个 archive 0-83% 完成度的 changes 不受新 gate 影响(已归档历史),仅未来 change 受影响。

**Alternatives considered:**

- 默认 ON,blocking:存量变更通过 archive 后无法重新校验,产生"曾经 0/55 仍成功 archive"的不一致 — 被否。
- 仅在 CI 环境开启(env `CI=true`):增加环境依赖,本地 archive 行为不一致 — 被否。

### 4. rdd-doctor `tasks-checkbox` 检查跨 active + archived

扫描 `openspec/changes/*/tasks.md` 和 `openspec/changes/archive/*/tasks.md`(排除 `tasks.md` 不存在或 0 task 的 change,避免噪声)。

**Alternatives considered:**

- 仅 active changes:无法追溯历史问题(如 `migrate-improvements-to-rddf-namespace` 0/55 仍不会被报) — 被否。
- 仅 archived:丢失当前进度警告 — 被否。

### 5. test_archive_tasks_gate.bats 边界用例

至少 5 个 case 覆盖:

1. 默认 warning:tasks 8/10 → archive 继续 + stderr warning
2. STRICT 阻断:`STRICT_TASKS_GATE=yes` + tasks 8/10 → exit 1
3. SKIP 跳过:`SKIP_TASKS_GATE=yes` + tasks 0/55 → exit 0,无 warning
4. 0 tasks edge case:change 无 tasks.md → exit 0,不视为失败
5. 完成度统计准确性:mock 9 个不同 `[x]`/`[ ]` 分布,验证百分比计算正确

## Risks / Trade-offs

- **存量 8 个 archive 0-83% change 触发 doctor WARNING**:`rdd-doctor --category tasks-checkbox` 扫描历史时会列出 8 个不完整归档。这是设计预期(追溯历史问题),但 CI 启用后可能触发大量 WARNING 报告。**Mitigation**:doctor 默认输出按 change name 排序,可加 `--max-warnings N` 截断(后续提案)。
- **0 tasks edge case 误判**:某些 change(如纯文档)无 tasks.md。需在 `check_tasks_completion` 中先检测 tasks.md 存在性,缺失则跳过(`[INFO] no tasks.md, skipping completion check`)。
- **STRICT_TASKS_GATE 与 rdd-doctor 协调**:doctor 在 archive 阶段之前运行,而 `check_tasks_completion` 在 archive 主体中运行。两者可能产生重复 WARNING,但职责不同(doctor 是 read-only 诊断,gate 是 write-time 校验)。
- **失败容错破坏 strict 语义**:`check_tasks_completion` 失败时 `|| true` 包裹,但 STRICT 模式下应硬阻断。需在脚本内分支处理:`if [ "${STRICT_TASKS_GATE:-no}" = "yes" ]; then exit 1; else warn; fi`。