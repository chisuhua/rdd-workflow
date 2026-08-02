## Context

**背景**: 2026-08-02 ship 复盘发现 `add-rddf-session-auto-archive-on-entry` 根因 (详见 `improvements/add-rddf-session-auto-archive-on-entry.md` 架构依据)。

**当前状态**: rdd-workflow v2.1 design-done 后, 5 个 rddf-session 提案待实施. 本 change 是其中之一.

**约束**:
- MUST 与已实施 `proposal-approved.md` 中的设计保持一致
- MUST 走 `.rddf/plans/<name>.md` plan-driven 实施 (TDD 5 步)
- MUST 通过 `openspec validate <name>` 检查
- MUST 不破坏现有 rddf-session 行为 (向后兼容)

## Goals / Non-Goals

**Goals**:
- 实施 improvements/add-rddf-session-auto-archive-on-entry.md 范围 In Scope 列出的所有项
- 单元测试 + bats 集成测试覆盖关键场景
- 不破坏现有 schema v1 readers (load v2 时 missing field = null)

**Non-Goals**:
- 不在 OpenSpec spec/ 中创建 capability (此为 rdd-workflow 自指改进, 非产品 spec)
- 不修改 ADR (除非范围明确要求)
- 不实施 P0 + P1 + P2 之间的横向依赖 (按 plan 阶段 deps 推荐顺序)

## Decisions

### 决策 1: 复用现有模式

参考 archive 中已有 rddf-session 类 change 的实施模式 (例如 fix-rddf-session-lifecycle-binding, add-heartbeat-config, fix-rddf-session-owner-cross-call).

### 决策 2: 实施顺序

- P0 `fix-rddf-session-owner-stability` 先实施 (根因, 阻断其他 4 条的稳定运行)
- P1 并行: `add-rddf-session-sub-phase-heartbeat` + `add-rddf-session-auto-archive-on-entry`
- P2 并行: `add-rddf-session-status-cmd` + `add-rddf-session-workflow-group`
- 强约束: sub-phase-heartbeat + workflow-group 合并为单一 schema v1→v2 bump PR

### 决策 3: 测试策略

- 单元测试: Python `tests/unit/test_rddf_*.py` 覆盖 schema/validation
- 集成测试: bats `tests/integration/test_*.bats` 覆盖 hook 调用链

## Risks

- **schema 不兼容**: v1 readers 加载 v2 时缺字段 → 必须保证 Zod safeParse 把 missing 视为 null
- **hook 副作用**: 修改 `rddf_session_hooks.sh` 影响所有 stage_* session → 必须保留 backward compat
- **worktree 隔离**: 多 change 并行 ship 时 OPENCODE_SESSION_ID 一致性 → 依赖 P0 落地

## Open Questions

- sub_phase 节流 (≤ 1 次/分) 实现位置: hook 层 vs coordinator 层? 实施时决策
- RDDF_AUTO_ARCHIVE_THRESHOLD env var 是否与 keep=0 协调? 实施时验证
