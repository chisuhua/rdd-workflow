# ADR-0003: 三阶段架构重构 (arch → plan → ship)

> **v3.0.0 note**: Originally authored as "spec-workflow". Renamed to "rdd-workflow" in v3.0.0 (2026-07-22). See ADR-0023.


> **状态**: 已采纳
> **日期**: 2026-06-22
> **决策者**: sisyphus
> **替代**: ADR-0001 §2 (双阶段架构 spec/ship)

## Context

rdd-workflow v1.x 采用**双阶段架构**（spec 端 + ship 端），以 `git commit artifacts` 为切分点：

```
v1.x 架构:
guide → guide-spec (setup → roadmap → propose → deps → spec-done)
             ↓
      guide-ship (plan → execute → archive → cleanup → ship-done)
```

在 v1.1 审计和用户反馈中，发现三类架构问题：

1. **架构定义与变更生成混合**: `guide-spec` 同时承担架构定义（roadmap、ADR 扫描）和变更生成（propose、deps），但这两类工作的**人工介入程度**截然不同：
   - 架构定义（ADR、roadmap）需要大量人工思考和审查
   - 变更生成（propose、deps）可以高度自动化

2. **Plan 阶段职责不清**: 当前 `plan` 阶段（guide-ship Phase 1）混合了两种职责：
   - 创建 worktree（基础设施操作）
   - 生成 Prometheus 计划（AI 辅助的实现规划）
   但实际上，**plan 应该专注于生成 openspec change artifacts**（proposal.md、design.md、tasks.md），而不是 worktree 管理

3. **缺少架构治理阶段**: 在项目初期或重大重构时，需要先定义 ADR、架构文档、roadmap，然后才能进入 change 生成。现有架构假设 roadmap 已存在或可自动生成，但实际场景中**架构定义是独立且高人工介入的工作**。

**约束**:
- 保持向后兼容：现有 `guide-spec` 和 `guide-ship` 接口在 v2.x 期间继续有效
- 不改变子技能职责：propose/execute/status/roadmap 保持独立
- 阶段间循环：阶段内可形成循环，阶段间可通过判断节点切换

**相关方**:
- 架构师：需要独立的架构定义阶段（ADR、roadmap）
- 开发者：需要自动化的 change 生成和执行
- 技术负责人：需要在架构决策点保留人工审查

## Decision

我们将双阶段架构重构为**三阶段架构**（arch → plan → ship），按**人工介入程度**和**职责类型**切分：

```
v2.x 架构:
guide → guide-arch (架构定义阶段)
             ↓
      guide-plan (变更生成阶段)
             ↓
      guide-ship (变更执行阶段)
```

### 三阶段职责定义

#### Phase 1: arch (架构定义阶段)

**目标**: 定义项目架构决策、路线图、架构文档，为后续 change 生成提供依据。

**特征**:
- **高人工介入**: 需要架构师思考和审查
- **低频执行**: 项目初期或重大重构时执行
- **输出稳定**: ADR、roadmap、架构文档一旦定义，较少变更

**职责**:
| # | 子阶段 | 职责 | 输出 |
|---|--------|------|------|
| 1 | setup | 环境检测（openspec CLI、git、现有 ADR/roadmap） | 环境报告 |
| 2 | adr-create | 创建/更新 ADR 文档 | `docs/adr/ADR-*.md` |
| 3 | architecture | 生成架构差距分析文档 | `docs/architecture/*-gap-analysis.md` |
| 4 | roadmap-define | 定义/更新路线图 | `roadmap.md` + `roadmap-meta.yaml` |
| 5 | arch-done | 验证架构文档完整性，交接 plan 阶段 | `.rddf/state/arch-handoff.json` |

**菜单示例**:
```
=== Arch 阶段 - 架构定义 ===

当前项目状态:
  ADR 文档: 3 个 (最新: ADR-0003)
  Roadmap: 已定义 (当前阶段: core, 完成度: 45%)
  架构差距: 2 个待处理

请选择操作:
  1. 创建新 ADR
  2. 更新 Roadmap
  3. 生成架构差距分析
  4. 查看架构文档状态
  5. 完成架构定义 → 进入 Plan 阶段
  6. 退出

输入编号 (1-6):
```

#### Phase 2: plan (变更生成阶段)

**目标**: 基于架构定义（ADR、roadmap），生成 OpenSpec change artifacts（proposal、design、tasks）。

**特征**:
- **中等人工介入**: 需要审查 change 内容，但可自动化生成
- **中频执行**: 每次新功能/修复时执行
- **输出频繁**: 每个 change 对应一组 artifacts

**职责**:
| # | 子阶段 | 职责 | 输出 |
|---|--------|------|------|
| 1 | scan | 扫描 ADR 未实现、TODO/FIXME、测试缺口 | 候选 change 列表 |
| 2 | propose | 创建 OpenSpec change artifacts | `openspec/changes/<name>/{proposal,design,tasks}.md` |
| 3 | deps | 依赖分析（冲突、ADR 引用、接口依赖） | `.rddf/state/deps-output.md` |
| 4 | plan-done | 验证 artifacts 完整性，交接 ship 阶段 | `.rddf/state/plan-handoff.json` |

**菜单示例**:
```
=== Plan 阶段 - 变更生成 ===

当前项目状态:
  Active Changes: 2 个 (add-auth, refactor-db)
  Roadmap 阶段: core (完成度: 45%)
  待处理 ADR: ADR-0004 (认证架构)

请选择操作:
  1. 扫描新 change 候选
  2. 创建 change (从 ADR/TODO/测试缺口)
  3. 运行依赖分析
  4. 查看 changes 状态
  5. 完成变更生成 → 进入 Ship 阶段
  6. 返回 Arch 阶段
  7. 退出

输入编号 (1-7):
```

#### Phase 3: ship (变更执行阶段)

**目标**: 为已提交的 changes 创建 worktree、生成实施计划、执行、归档。

**特征**:
- **低人工介入** (在 hybrid/loop 模式下): 可自动执行
- **高频执行**: 每次 change 实施时执行
- **输出频繁**: 代码变更、测试、merge

**职责**:
| # | 子阶段 | 职责 | 输出 |
|---|--------|------|------|
| 1 | plan | 选择 change → 创建 worktree → 生成 Prometheus 计划 | `.rddf/plans/<name>.md` |
| 2 | execute | 监控/执行 work units | 代码变更、测试通过 |
| 3 | archive | merge → openspec archive → cleanup | archived change |
| 4 | cleanup | 清理残留 worktrees/branches | 清理报告 |
| 5 | ship-done | 验证全空，可选回到 plan 或 arch 阶段 | 完成报告 |

**菜单示例**:
```
=== Ship 阶段 - 变更执行 ===

当前项目状态:
  Worktrees: 1 个活跃 (add-auth, 进度: 70%)
  Pending Archive: 0 个
  已完成 Changes: 5 个

请选择操作:
  1. 创建 worktree (为新 change)
  2. 监控执行 (查看 worktree 进度)
  3. 归档完成的 change
  4. 清理残留 worktrees
  5. 查看执行状态
  6. 返回 Plan 阶段
  7. 完成本次 Ship 流程
  8. 退出

输入编号 (1-8):
```

### 阶段间循环与切换

```
阶段内循环:
  arch:  adr-create → roadmap-define → adr-create (循环细化)
  plan:  scan → propose → deps → scan (循环生成多个 changes)
  ship:  plan → execute → archive → plan (循环处理多个 changes)

阶段间切换:
  arch → plan:  arch-done 验证通过 (ADR + roadmap 完整)
  plan → ship:  plan-done 验证通过 (artifacts 已 commit)
  ship → plan:  ship-done 选择"继续处理新 changes"
  plan → arch:  plan 阶段选择"返回 Arch 阶段" (需要更新架构)
  ship → arch:  ship-done 选择"回到 Arch 阶段" (需要重大架构调整)
```

**切换条件**:
| 切换 | 触发条件 | 验证 |
|------|---------|------|
| arch → plan | `arch-done` 验证通过 | ADR 数量 ≥ 1, roadmap.md 存在 |
| plan → ship | `plan-done` 验证通过 | active changes 数量 ≥ 1, artifacts 已 commit |
| ship → plan | `ship-done` 选择"继续" | 无活跃 worktrees |
| plan → arch | 用户主动选择 | 无未提交的 changes |
| ship → arch | 用户主动选择 | 无活跃 worktrees, 无 pending archive |

### 影响范围

- **In Scope**:
  - 新增 `skills/guide-arch.md` (架构定义阶段状态机)
  - 拆分 `skills/guide-spec.md` → `guide-plan.md` (只保留 propose + deps)
  - 保留 `skills/guide-ship.md` (职责不变)
  - 更新 `skills/guide.md` (推荐器扫描 3 个阶段)
  - 新增阶段间交接文件 (`.rddf/state/arch-handoff.json`, `.rddf/state/plan-handoff.json`)
  
- **Out Scope**:
  - 不改变子技能接口 (propose/execute/status/roadmap/deps 保持独立)
  - 不改变 openspec CLI 接口
  - 不改变状态文件格式 (`.rddf/state/` 目录结构保持)

### 备选方案

| 备选 | 理由 |
|------|------|
| **保持双阶段 (spec/ship)** | 拒绝：架构定义与变更生成混合，人工介入程度不匹配 |
| **四阶段 (arch → propose → plan → ship)** | 拒绝：propose 和 plan 职责重叠，增加复杂度无收益 |
| **单阶段 (统一 guide)** | 拒绝：v1.0 已证明单文件状态机不可维护 |
| **三阶段 (arch → plan → ship)** | 接受：按人工介入程度和职责类型清晰切分 |

## Consequences

### 正面

- **职责清晰**: arch 专注架构治理，plan 专注 change 生成，ship 专注执行
- **人工介入匹配**: 高介入 (arch) → 中介入 (plan) → 低介入 (ship)，符合实际工作流
- **架构治理强化**: ADR 和 roadmap 定义成为独立阶段，避免"跳过架构直接编码"
- **阶段间灵活切换**: 支持 forward (arch→plan→ship) 和 backward (ship→plan→arch) 切换
- **Loop 引擎友好**: 三阶段提供清晰的 detector/action 边界，便于 Loop 编排

### 负面 / 风险

- **迁移成本**: 现有用户需要从 `guide-spec` 迁移到 `guide-arch` + `guide-plan`
  - **缓解**: v2.x 期间保留 `guide-spec` 作为别名（内部调用 arch → plan）
- **阶段切换复杂度**: 用户需要理解何时切换阶段
  - **缓解**: `guide` 推荐器自动检测并推荐下一阶段
- **文档更新**: README/USAGE 需要重写工作流图
  - **缓解**: 提供迁移指南 (`docs/migration/v1-to-v2.md`)

### 后续待办

- [ ] 实现 `skills/guide-arch.md` (架构定义阶段)
- [ ] 重命名 `skills/guide-spec.md` → `skills/guide-plan.md` (移除 roadmap 相关逻辑)
- [ ] 更新 `skills/guide.md` 推荐器支持三阶段扫描
- [ ] 实现阶段间交接文件 (`.arch-handoff.json`, `.plan-handoff.json`)
- [ ] 添加阶段切换验证逻辑
- [ ] 更新 README.md 和 USAGE.md 工作流图
- [ ] 创建迁移指南 (`docs/migration/v1-to-v2.md`)
- [ ] 添加集成测试 (阶段间切换场景)

## References

- ADR-0001 — 原始双阶段架构 (spec/ship)
- `skills/guide-spec.md` — 当前 spec 端状态机（将拆分为 arch + plan）
- `skills/guide-ship.md` — 当前 ship 端状态机（保持不变）
- `skills/guide.md` — 推荐器（将扩展为三阶段扫描）
- `docs/adr/ADR-*.md` — ADR 文档目录（arch 阶段输出）
- `roadmap.md` — 路线图（arch 阶段输出）
- `docs/architecture/*-gap-analysis.md` — 架构差距分析（arch 阶段输出）
- `openspec/changes/<name>/{proposal,design,tasks}.md` — change artifacts（plan 阶段输出）

