# add-rddf-session-sub-phase-heartbeat

## Why

rddf-session 当前 `kind` 字段只有 4 个 stage-level 值 (`stage_arch/design/plan/ship`)。`guide-ship` 内部实际包含 6 个子阶段 (plan / execute / review / archive / cleanup / ship-done),但 hooks 只在子阶段切换时短暂活动 (尤其 execute 阶段 AI 实际执行任务,可能耗时数分钟到数十分钟),期间没有心跳。

后果:
- execute 子阶段 AI 卡住时,30 分钟超时才能察觉;用户感知不到具体卡点
- 调试时无法区分"已完成 archive" vs "正在 archive" vs "卡在 archive"
- 多 change 并行 archive 时,无法知道进度 (`rds_xxx` 是处理 change A 还是 change B)

依据:ADR-0017 §3 heartbeat 设计。

## What Changes

**In Scope**:

- **In Scope**:
- `skills/_lib/schemas/sessions_schema.json` v1 → v2: 新增 `sub_phase: str | null` 字段 (默认 null 兼容 v1)
- `RddfSessionCoordinator.update_session_status()` 新增 `sub_phase` 参数 (向后兼容)
- `rddf_session_hook_entry` 入口: `sub_phase="phase_<N>_<name>"` (e.g., `phase_3_archive`)
- `rddf_session_hook_heartbeat` 心跳: `sub_phase="phase_<N>_<name>_<context>"` (e.g., `phase_3_archive_move-proposal-creation-to-design`)
- 文档: `rddf-session list` 输出新增 `sub_phase` 列
- **复用已落地的 `RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS`** (默认 5 min) 作为 sub_phase 切换检测阈值 — 由 `add-heartbeat-config` P1 提案 (2026-07-28 实施) 落地于 `skills/rddf-session/scripts/rddf_session_pkg/_types.py` L20-21、L98-132。**不新增** `RDDF_SUB_PHASE_TIMEOUT_SECONDS`,避免 env var 膨胀
- 整体 session 长超时 (30 min, 同样由 `RDDF_HEARTBEAT_TIMEOUT_SECONDS` 控制) 保留,sub_phase 切换检测仅在 `last_heartbeat` 超过 refresh threshold 时输出 "stuck on $sub_phase" warning (不标 orphaned, 长超时阈值才标)
- **强依赖: 本提案与 `add-rddf-session-workflow-group` 合并为单一 schema v1→v2 bump PR (`bump-sessions-schema-v2`)**, 一次同时支持 `sub_phase: str | null` + `workflow_group: str | null` 两个 optional 字段。**禁止拆为两次独立 bump**, 否则会引入 v1.5 中间态无谓复杂化。Plan 阶段必须先实施 P0 (`fix-rddf-session-owner-stability`) 再启动本 PR。
- **Out Scope**:
- 不修改 schema 现有必填字段 (向后兼容)
- 不修改 entry hook 的 kind 语义
- 不引入新的 lock 机制 (sub_phase 切换不阻塞其他 hooks)

### 关键场景

- GIVEN `guide-ship` 处于 Phase 3 archive 阶段且正在处理 change="demo",WHEN 调用 `rddf_session_hook_heartbeat`,THEN `sub_phase="phase_3_archive_demo"`,`list` 命令可看到具体进度
- GIVEN `sub_phase` 已设置,WHEN 5 分钟内无心跳,THEN 输出 "stuck on $sub_phase" warning (但不标 orphaned,30 分钟阈值才标)
- GIVEN v1 sessions.json (无 sub_phase 字段),WHEN 加载,THEN schema 兼容,`sub_phase=None`

**Out of Scope**:

- design 阶段不生成 tasks.md / design.md / specs (留在 plan fill)
- 不修改 ADR-0003 (另起 ADR 记录本次职责再分配)


## Capabilities

- `design-proposal-creation`: design 审批批准即创建完整 openspec change
- `design-content-review`: 两层内容审查 (improvements 5 段 + openspec validate), warning / strict 双模式


## Impact

- **受影响文件**: `skills/guide-design/SKILL.md` + 4 个 scripts, `skills/guide-plan/scripts/plan_intake.sh`, `docs/adr/ADR-0025-*.md` (新增)
- **兼容性**: `SKIP_DESIGN_HANDOFF=yes` 存量路径行为不变
- **硬约束**: 批准动作幂等; env-var 传参 (Oracle C1)


## Acceptance

- [ ] schema v2 支持 `sub_phase: str | null`,v1 payloads 兼容加载
- [ ] `rddf-session list` 输出新增 `sub_phase` 列
- [ ] `rddf_session_hook_heartbeat stage_ship foo` 输出 `sub_phase="phase_3_archive_foo"`
- [ ] 5 分钟无 sub_phase 心跳输出 warning,但不改变 state
- [ ] 单元测试 + bats 集成测试通过

