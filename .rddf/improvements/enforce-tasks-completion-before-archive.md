# enforce-tasks-completion-before-archive

**优先级**: P2 | **来源**: 审计 9 个归档 change 时发现 tasks.md 完成度参差不齐
**阶段**: default | **分类**: quality
**类型**: debt

## 架构依据

- 当前 `_lib/archive.sh::check_worktree_commits` 要求 worktree 分支至少有 1 个 commit 才允许 archive，但 **未要求 tasks.md 完成度 = 100%**。
- 审计 9 个已归档 change 发现：
  - `migrate-improvements-to-rddf-namespace`: tasks.md **0/55**（！）但已 archive — 实际功能完整（155 proposal links 全可解析、smoke 测试通过），但 task 勾选完全空。
  - `complete-third-party-replay-and-upstream-reporting`: tasks.md 34/41（83%）— 7 个未勾选任务多为 meta（"Run test"、"Update proposal"）。
  - `fix-generator-scope-extraction`: tasks.md 8/10（80%）— 2 个 meta 任务。
  - 其他 6 个 100% 完成。
- `rdd-doctor --category tasks-checkbox` 当前未实现（仅检查 schema / plan-tdd / roadmap-meta / proposal-table 四类）。
- `harden-archive-iteration-sync`（commit `02fe62f`）已修复 iteration.json 同步，但未触及 tasks.md 完整性。

## 范围

- **In Scope**:
  - 在 `_lib/archive.sh::archive_change` 末尾添加 `check_tasks_completion` 步骤：当 tasks.md 存在但完成度 < 100% 时，输出 warning（不阻断默认流程）。
  - 新增环境变量 `STRICT_TASKS_GATE=yes`：开启后，未完成 tasks 直接阻断 archive（参照 `STRICT_CHANGE_GATE` 模式）。
  - 新增环境变量 `SKIP_TASKS_GATE=yes`：紧急情况绕过（同 `SKIP_*` 系列语义）。
  - 给 `rdd-doctor --category tasks-checkbox` 实现新检查：扫描 `openspec/changes/<name>/tasks.md` 和 `openspec/changes/archive/*/tasks.md`，报告完成度 < 100% 的 change 为 WARNING。
  - 新增 `tests/integration/test_archive_tasks_gate.bats` 验证 gate 行为（≥5 用例：默认 warning / STRICT 阻断 / SKIP 跳过 / 0 tasks edge case / completed-only 状态）。
- **Out Scope**:
  - 不修改已归档 change 的 tasks.md（保留历史状态）。
  - 不强制所有 change 必须勾选 tasks 才能 propose（仅在 archive 阶段校验）。
  - 不实现 tasks.md 自动勾选（AI 执行阶段已自动勾选，本提案只补校验）。
  - 不修改 `tasks_writeback.sh`（execute 阶段的回写逻辑已完整）。

## 关键场景

- GIVEN `migrate-improvements-to-rddf-namespace` 类型 change 实际功能完整但 tasks.md 0/55, WHEN 启用 `STRICT_TASKS_GATE=yes`, THEN archive 阶段阻断并提示"tasks 未完成: 0/55, 启用 SKIP_TASKS_GATE=yes 绕过"。
- GIVEN 默认环境（无 STRICT_*）+ tasks.md 8/10, WHEN archive 触发, THEN 输出 warning "tasks 80% 完成 (8/10), 建议 archive 后补勾" 但继续执行。
- GIVEN tasks.md 含 `- [~]` 或部分完成标记 (e.g. `- [WIP]`), WHEN check_tasks_completion 调用, THEN 仅统计 `- [x]` vs `- [ ]`，忽略其他标记（向后兼容）。
- GIVEN `rdd-doctor --category tasks-checkbox`, WHEN 扫描 active + archived changes, THEN 列出所有完成度 < 100% 的 change（含路径、完成度、未完成 task 数），输出 WARNING 级。

## 技术约束

- MUST 在 `archive.sh` 添加 `check_tasks_completion` 步骤，默认 warning 模式（不破坏现有 archive 流程）。
- MUST 遵循 ADR-0018 gate escalation 模式：`STRICT_TASKS_GATE=yes` 升级 error，`SKIP_TASKS_GATE=yes` 跳过。
- MUST NOT 强制勾选 tasks（只校验完成度，不修改 tasks.md 内容）。
- MUST NOT 阻塞 0 tasks edge case（如某些 change 无 tasks.md 也应正常 archive）。
- SHOULD 复用 `skills/_lib/gate.py` 现有 gate escalation 框架（warning/error 两级）。
- SHOULD 给 `rddf-doctor --category tasks-checkbox` 添加 1 个新检查类（参照 `plan-tdd` / `proposal-table` 等已有类）。

## 验收标准

- `_lib/archive.sh::archive_change` 新增 `check_tasks_completion` 步骤，输出格式：`"📋 tasks completion: <done>/<total> (<pct>%)"`。
- 默认环境下 tasks < 100% 时输出 warning 但 archive 成功；`STRICT_TASKS_GATE=yes` 时 tasks < 100% 阻断 archive 并返回非零退出码。
- `SKIP_TASKS_GATE=yes` 时跳过校验，与未启用 gate 时行为一致。
- `rdd-doctor --category tasks-checkbox` 新增检查类，列出所有不完整 tasks.md 的 change（active + archived），输出 WARNING 级报告（CRITICAL 仅在 `STRICT_TASKS_GATE` 模式下）。
- 新增 `tests/integration/test_archive_tasks_gate.bats` ≥5 用例：默认 warning / STRICT 阻断 / SKIP 跳过 / 0 tasks edge / 完成度统计准确性 全部 pass。
- 现有 archive 相关测试（`test_archive_iteration_sync_resilience.bats` 5 个、`test_archive_state_recovery.bats` 等）保持 pass（无 regression）。
- 手工验证：对 `migrate-improvements-to-rddf-namespace` 这种 0/55 tasks 的归档 change，doctor 现在会报告 WARNING；未来同类 change 在 archive 时医生级阻断。