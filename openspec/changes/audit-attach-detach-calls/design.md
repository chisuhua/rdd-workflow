# audit-attach-detach-calls — Design

**Priority**: P0
**Phase**: v2.1
**Status**: filled
**Type**: audit (read-only, no code modifications)

## 1. Goal

确定 `RddfSessionCoordinator.attach_change()` 与 `detach_change()` 是否被 guide 技能
（`guide-arch` / `guide-plan` / `guide-ship`）实际调用,找出缺失的 hook,
为后续修复提供证据基础。

## 2. Background

`RddfSessionCoordinator` (定义于 `skills/rddf-session/scripts/rddf_session.py`)
提供两个 idempotent 方法维护 session.attached_changes 列表:

- `attach_change(session_id, change_name)` — 添加 change_name (line 334-347)
- `detach_change(session_id, change_name)` — 移除 change_name (line 349-362)

`docs/v2-multi-session-guide.md` §"自动管理" 规定:
> `guide-ship` 入口 -> 创建 `kind=stage_ship`, parent=最新 stage_plan
> 所有 attached_changes archived -> `stage_ship` -> completed

即 attached_changes 应在 ship entry 时填充,每次 archive 时清空。
本审计验证该契约是否被实际执行。

## 3. Audit Methodology

### 3.1 静态扫描

使用 `grep -rn 'attach_change\|detach_change'` 在 `skills/`, `tests/`, `docs/`
目录全量搜索调用点 (含 `coord.attach_change(` 与 `coord.detach_change(`)。

### 3.2 Hook 调用链追踪

追踪 `rddf_session_hook_entry` / `rddf_session_hook_close` /
`rddf_session_hook_heartbeat` 三个 hook 在 guide-arch/plan/ship SKILL.md
中的调用,确认 hook 内部是否触发 attach/detach。

### 3.3 期望 vs 实际对比

依据 ADR-0017 + v2-multi-session-guide 列出期望的 attach/detach 时机,
与代码实际行为对比,列出缺失 hook。

## 4. Definitions

| Term | Meaning |
|------|---------|
| **Call site** | 代码中实际写有 `.attach_change(` 或 `.detach_change(` 的位置 |
| **Production call site** | 排除 `tests/` 与文档示例的生产代码调用点 |
| **Hook** | `rddf_session_hook_entry` / `_close` / `_heartbeat` 之一 |
| **Expected attach point** | 按 ADR-0017 契约应该调用 attach_change 的时机 |
| **Missing hook** | 期望调用但实际未调用的 attach/detach 时机 |

## 5. Audit Scope (In/Out)

**In Scope**:
- 扫描 `skills/` + `tests/` + `docs/` 全部文本
- 列出 attach_change/detach_change 的所有调用点
- 追踪 3 个 hook 在 3 个 guide skill 的调用情况
- 依据 ADR-0017 契约列出缺失的 attach/detach hook

**Out of Scope**:
- 修改任何代码 / 文档 / 测试
- 修复发现的缺失 hook (留待后续 change)
- 性能 / 并发分析

## 6. Deliverable

单一审计报告: `.rddf/state/attach-detach-audit.md`, 含以下章节:

1. **Executive Summary** — 一句话结论
2. **Definitions** — 术语表 (同 §4)
3. **Call Site Inventory** — 所有调用点的表格 (文件:行号, 类型, 上下文)
4. **Hook Call Chain** — 3 个 hook × 3 个 guide skill 的调用矩阵
5. **Expected vs Actual** — ADR-0017 契约期望 vs 实际行为
6. **Missing Hooks** — 缺失的 attach/detach 时机列表 + 影响评估
7. **Recommendations** — 后续修复建议 (非强制)

## 7. Verification

- 报告必须列出每个调用点的精确文件路径 + 行号
- 报告必须引用 ADR-0017 / v2-multi-session-guide 作为期望来源
- 报告必须明确区分 "production call" vs "test call" vs "definition"
- 不修改任何 `.py` / `.sh` / `.md` 源文件 (除本 change 的 artifacts)

## 8. Risk

**Low**: 纯只读审计,无运行时副作用,不修改代码。

## 9. References

- ADR-0017: `docs/adr/ADR-0017-rddf-session.md`
- v2-multi-session-guide: `docs/v2-multi-session-guide.md` §"自动管理"
- 实现: `skills/rddf-session/scripts/rddf_session.py:334-362`
- Hook: `skills/rddf-session/scripts/rddf_session_hooks.sh:1-191`
- 测试: `tests/unit/test_rddf_session.py:109-135`
