# move-proposal-creation-to-design — Tasks

## 1. design-handoff schema v2

- [x] 1.1 写失败测试：`tests/unit/` 新增 design_handoff v2 schema 校验测试（changes_pre_created 必填性、version=2、additionalProperties 拒绝未知字段）
- [x] 1.2 更新 `skills/_lib/schemas/design_handoff_schema.json` → v2（新增 `changes_pre_created` 数组字段，version const 2）
- [x] 1.3 更新 `skills/guide-design/scripts/write_design_handoff.py` 写入 v2 + changes_pre_created
- [x] 1.4 更新 `skills/guide-plan/scripts/plan_intake.sh::check_design_handoff` 兼容 v1/v2（v1 时 changes_pre_created 视为空）+ bats 回归测试

## 2. approve 动作升级（生成→确认→落盘）

- [x] 2.1 写失败测试：approve 后 change 目录含完整 proposal.md / roadmap-meta.yaml（含 change_type）/ iteration.json(planned)
- [x] 2.2 `skills/guide-design/SKILL.md` Phase 3 编排：批准 → AI 按 D2 映射生成完整 proposal.md 草稿 → 用户确认 → 落盘
- [x] 2.3 `skills/guide-design/scripts/approve_proposal.sh` 串联 `openspec new change` + 状态写入（幂等：目录已存在跳过）
- [x] 2.4 phase/category 从 improvements 头部读取（禁止硬编码 default/general，fallback 时 warning）+ `parent_feature` 询问透传
- [x] 2.5 `skills/propose/scripts/propose_change.py` 骨架分支 roadmap-meta.yaml 补 `change_type` 字段

## 3. design 两层内容审查

- [x] 3.1 写失败测试：improvements 层检查（5 段完整性 / ADR 引用 ≥1 / 可量化验收 / 必填头部字段）
- [x] 3.2 新增 `skills/guide-design/scripts/design_content_review.{sh,py}`（env-var 传参，Oracle C1 合规）
- [x] 3.3 openspec proposal 层：调 `propose_quality_check` 的 proposal 3 项 + `openspec validate <name> --json`（ERROR 始终阻断）
- [x] 3.4 `STRICT_DESIGN_GATE=yes` 升级 warning 为阻断；`SKIP_CONTENT_REVIEW=yes` 跳过 Oracle 4 维叠加审查

## 4. guide-plan 适应性调整

- [x] 4.1 写失败测试：intake 识别 changes_pre_created 跳过已建 change
- [x] 4.2 `skills/guide-plan/SKILL.md` Phase 2 展示层标注"design 预建"，跳过 propose 创建
- [x] 4.3 Phase 2.5 fill 范围收缩为 specs/design/tasks（proposal=done 自然跳过）
- [x] 4.4 plan_done 既有 propose_quality_check 5 项回归测试确认无变化

## 5. ADR 与文档

- [x] 5.1 新增 `docs/adr/ADR-0025-design-proposal-creation.md`（职责再分配决策，状态：已采纳）
- [x] 5.2 AGENTS.md / README.md 同步 design 阶段新职责

## 6. 端到端验证

- [x] 6.1 bats 集成测试：approve → 完整 change 创建 → guide-plan 跳过创建 → fill 仅 specs/design/tasks → plan-done 通过
- [x] 6.2 `SKIP_DESIGN_HANDOFF=yes` 存量骨架路径 e2e 回归
- [x] 6.3 全量测试：pytest tests/unit + tests/integration + bats tests/ 全绿（含恒真断言门控）
