# fix-plan-intake-stale-pre-created-changes — Tasks

## Task 1: 修正 `PENDING_PROPOSALS` 计数逻辑

- [x] **1.1** 在 `plan_intake.sh` 新增 Python 一次性函数（fallback 到 plain bash if python3 缺失）：
  - 输入：`$PROJECT_ROOT`
  - 读取 `proposal-approved.md`
  - 取 `## 已实施` 之前章节
  - 对每行抽取 change name
  - 排除 `openspec/changes/<name>` 已存在的
  - 排除 `openspec/changes/archive/*-<name>` 已存在的
  - 返回 `(pending_count, pending_names)`
- [x] **1.2** 把现有 `grep -c '| \['` 替换为新函数调用
- [x] **1.3** 输出新格式：
  - 之前：`⚠️  proposal-approved.md 中有 225 个已批准提案但无活跃 change`
  - 之后：`📋 待创建 proposal: 0 (已排除 223 个已归档 + 2 个已批准)` 或仅 `📋 待创建 proposal: N`
- [x] **1.4** 添加 bash fallback（无 python3 时退化到 `grep` 旧行为 + warning）

## Task 2: `check_design_handoff` 分类展示

- [x] **2.1** 在 `check_design_handoff` 读入 `CHANGES_PRE_CREATED` 后调用新分类函数
- [x] **2.2** 分类函数输出 `(pending, active, archived)` 三个计数
- [x] **2.3** 输出新格式：
  - 全部归档：`✅ design-done handoff 已验证 (v2 schema, 19 个预建 changes: 0 待处理, 19 已归档)`
  - 部分待处理：`✅ design-done handoff 已验证 (v2 schema, 3 个预建 changes: 2 待处理, 1 已创建)`
- [x] **2.4** 导出 env vars：`CHANGES_PENDING_COUNT`, `CHANGES_ACTIVE_COUNT`, `CHANGES_ARCHIVED_COUNT`
- [x] **2.5** 保留 `CHANGES_PRE_CREATED` 内部数组完整（不删名字）

## Task 3: 新增 `is_design_pre_created_pending` helper

- [x] **3.1** 在 `plan_intake.sh` 现有 `is_design_pre_created` 旁边新增 helper
- [x] **3.2** 实现：
  - 名字不在数组 → 返回 1
  - 名字在数组 + `openspec/changes/<name>` 存在 → 返回 1
  - 名字在数组 + `archive/*-<name>` 存在 → 返回 1
  - 名字在数组 + 都不存在 → 返回 0
- [x] **3.3** `is_design_pre_created` 既有 helper 不动（向后兼容）

## Task 4: 集成测试 (bats)

- [x] **4.1** 新建 `tests/integration/test_plan_intake_archived_filtering.bats`
- [x] **4.2** 测试 `全部预建已归档 → 不输出 pending 警告`
- [x] **4.3** 测试 `部分预建待处理 → 正确分类展示`
- [x] **4.4** 测试 `PENDING_PROPOSALS 排除已实施区`
- [x] **4.5** 测试 `SKIP_DESIGN_HANDOFF=yes 跳过新逻辑`
- [x] **4.6** 扩展 `tests/integration/test_plan_intake_design_pre_created.bats`：
  - [x] `is_design_pre_created_pending: 名字在数组 + 已归档 → 返回 1`
  - [x] `is_design_pre_created_pending: 名字在数组 + 未归档 → 返回 0`

## Task 5: 文档化

- [ ] **5.1** `skills/guide-plan/SKILL.md` Phase 1 段补充归档过滤说明（SKIPPED: SKILL.md 现有"已批准提案列表"展示层是按目录/全局读取，已正确处理归档场景，无需改动）
- [x] **5.2** 新建 `docs/adr/ADR-0036-design-handoff-runtime-filter.md`
  - 背景：design handoff 永不过期是设计选择（持久化 = 审计）
  - 决策：运行时过滤而非落盘时清理
  - 备选：archive 时清理 design handoff（被否决，破坏设计/执行阶段边界）
  - 影响：guide-plan intake 增加 ~10ms Python 计算

## Task 6: 端到端验证

- [x] **6.1** `./test.sh --quick` 通过（包含新测试）
- [x] **6.2** `./test.sh --unit` Python 单测全绿（6 个失败均为 pre-existing baseline bug，非本次引入）
- [x] **6.3** 在本仓库实际跑 `run_plan_intake` 验证：
  - [x] 不再输出 "X 个已批准提案但无活跃 change" 误导
  - [x] 输出 "0 个待创建" + "19 个预建 changes: 0 待处理, 19 已归档"
- [x] **6.4** `lsp_diagnostics` 检查 `plan_intake.sh` 无新增 warning/error

## Task 7: 提交与归档

- [x] **7.1** worktree 内聚合 commit（按 v2.0.5+ 约定）
- [ ] **7.2** `./test.sh --full --regression` 全量回归门
- [ ] **7.3** guide-ship archive change
