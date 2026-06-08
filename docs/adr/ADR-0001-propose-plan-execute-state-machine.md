# ADR-0001: spec-workflow 状态机分相（propose → plan → execute → status → archive）

> **状态**: 已采纳
> **日期**: 2026-06-08
> **决策者**: sisyphus

## Context

spec-workflow 是一个面向 OpenSpec 变更管理的工作流技能包。在 spec-workflow v1.0 之前，整个工作流被压在一个庞大的 `guide.md` 状态机中，单一文件承担了：

- 推荐入口（用户首次进入时决定调 `guide-spec` 还是 `guide-ship`）
- spec 端状态机（setup → roadmap → propose → deps）
- ship 端状态机（plan → execute → status → archive）
- 7 个子技能（propose / execute / status / roadmap / deps / INSTALL / prometheus-start-work）

随着状态分支与子技能数量的增长，单文件状态机出现了三类问题：

1. **状态爆炸**：`guide.md` v3.0 同时承担 5 个 phase（spec+ship），phase 计数器相互干扰（例如 spec-done 与 ship-done 共用退出逻辑）
2. **测试覆盖断层**：v1.0 仅有 `tests/smoke.bats`（7 个基础设施断言），9 个 skill 完全没有单元测试
3. **责任混合**：推荐器应当只读不写（无状态），而状态机需要写 git/磁盘——两者关注点不同

`docs/audit/2026-06-05-workflow-audit.md` 记录了 6 处 P0/P1 缺陷（P0-6 `prometheus-start-work` 黑盒依赖、P0-7 `$2`/`$3` 列号错位、P0-8 PROJECT_ROOT 解析、P0-9 `read -p` 阻塞等），全部源于单文件状态机的复杂度。

**约束**:
- 保持向后兼容：现有 `npx skills add chisuhua/spec-workflow` 用户的工作流不中断
- 推荐入口必须仍然是无状态的（写一次代码 → 不需要任何 state 文件）
- 9 个 skill 的内容不重新设计，只做"工作流层"拆分

## Decision

我们将 spec-workflow 工作流拆分为 **5 阶段 + 1 推荐器 + 9 子技能** 的三层层级结构：

```
推荐器层 (1):     guide
                        ↓
状态机层 (2):     guide-spec (spec 端)
                  guide-ship (ship 端)
                        ↓
子技能层 (9):     INSTALL, propose, roadmap, deps (spec 端)
                  execute, status, prometheus-planning (ship 端)
```

**5 阶段**:
1. `propose` — 生成 OpenSpec change artifacts（proposal.md / design.md / tasks.md）
2. `plan` — Prometheus 生成 `.sisyphus/plans/<name>.md`（含三级回退链）
3. `execute` — 在 worktree 内执行计划，原子更新 tasks.md
4. `status` — 跨 worktree 状态概览 + 归档判定
5. `archive` — 合并到 default branch + `openspec archive` + worktree/branch 清理

**职责分层原则**:
- **推荐器 (guide)**: 无状态、只读、返回单行建议 `skill_use("guide-spec")` 或 `skill_use("guide-ship")`
- **状态机 (guide-spec / guide-ship)**: 拥有 `.zcf/.handoff.json`、调用子技能、phase 计数
- **子技能**: 单一职责（只做一件事），可独立测试

## Consequences

### 正面

- **可测试性**: 每个 skill 独立 bats 测试（`test_*_skill.bats`），覆盖率从 0% 提升到 ≥ 3 cases/skill
- **状态隔离**: spec 端与 ship 端的 phase 计数互不干扰
- **推荐器可缓存**: `guide` 是纯函数，可未来加入 `caching` 优化而不破坏状态机
- **可观测性**: 每个 phase 的输入/输出可被 `.sisyphus/plans/` 与 tasks.md 独立追踪
- **审计友好**: 6 处 P0/P1 缺陷可独立 fix（如 P0-7 只影响 ship 端）

### 负面 / 风险

- **入口分裂**: 用户从 1 个 `guide.md` 变成先看到 `guide`，再选 spec/ship。增加一次跳转（但提升 90% 用例的清晰度）
- **跨 phase 数据传递**: 需要 `.zcf/.handoff.json`（spec-done 写入 → ship-started 读取）—— 引入了一个新的 state 文件
- **文档同步**: README.md / USAGE.md 需要重写工作流图（已在 v1.1 完成）

### 后续待办

- [ ] `暂不修复` v1.2 之前不增加 `guide` 的状态缓存（保持纯函数语义）
- [ ] `未来参考` 评估将 `prometheus-planning` 进一步下沉为 `skills/_lib/prometheus.sh`（与 `archive.sh` / `worktree.sh` 对齐）
- [ ] `待修复` `skills/execute.md` 仍依赖 `EXECUTE_CHOICE` 环境变量绕过 `read -p` 阻塞（P0-9 部分缓解）

## References

- `README.md` §工作流程 — 5 阶段可视化
- `USAGE.md` §3 — 详细工作流示例
- `docs/audit/2026-06-05-workflow-audit.md` — 6 处 P0/P1 缺陷原始记录
- `skills/guide.md` — 推荐器（无状态）
- `skills/guide-spec.md` §1-4 — spec 端状态机
- `skills/guide-ship.md` §1-4 — ship 端状态机
- `skills/prometheus-planning.md` — plan 阶段子技能（v1.1+ 替代 prometheus-start-work）
- `tests/integration/test_guide_skill.bats` — 推荐器单元测试
- `tests/integration/test_guide_spec_skill.bats` — spec 状态机单元测试
- `tests/integration/test_guide_ship_skill.bats` — ship 状态机单元测试
