# Roadmap Content Organization (路线图内容组织)

> **目标读者**: rdd-workflow 贡献者 + 用户
> **状态**: 实际样例取自本项目 `.rddf/roadmap.md`(2026-09 快照)
> **关联 ADR**: [ADR-0038](../adr/ADR-0038-rdd-planner-crosscutting.md) sprint + AUTO-SPRINT 写入方约束 · [ADR-0041](../adr/ADR-0041-planner-sprint-lifecycle-and-history.md) sprint 生命周期 · [ADR-0048](../adr/ADR-0048-v4-stage-merge-revision.md) rdd-planner 完全独占 roadmap · [ADR-0025](../adr/ADR-0025-design-proposal-creation.md) improvement vs openspec proposal 区分

Roadmap 是 rdd-workflow 五大核心概念(roadmap / change / sprint / phase / handoff)之一。本文档**专门讲解"roadmap 内容如何组织"**,与其他 architecture 文档(`workflow-phases.md` 讲阶段治理、`state-and-events.md` 讲状态层)互为补充,不重复。

---

## TL;DR — 5 个互补维度

Roadmap 通过 **5 个正交维度** 组织复杂项目的实施路径:

| 维度 | 表达什么 | 落盘位置 | 数量级 |
|---|---|---|---|
| **Phase** | 长期能力里程碑 | 主文档 `## Phase Skeleton` + `phases/phase-N.md` | 4-10 个 |
| **Sub-phase** | 单 phase 内的子拆分 | `phases/phase-N.M.md` | 0-6 个/phase |
| **Feature** | 跨 phase 功能组合 | `features/feat-<name>.md` | 0-N 个 |
| **Theme** | phase 内的子主题 + proposal 覆盖度单位 | 主表 Theme 列(可空) | N×M 个 |
| **Sprint** | 当下执行窗口(默认按月) | `.planner-state.json::current_sprint` + AUTO-SPRINT 块 | 1 个 active |

**正交关系图**:

```
              ┌─────────── Phase (长期能力) ───────────┐
              │                                         │
              │  ┌─ Sub-phase ─┐  ┌─ Sub-phase ─┐       │
              │  │ phase-3.1   │  │ phase-3.2   │       │
              │  └─────────────┘  └─────────────┘       │
              │                                         │
   Feature ───┼──── 跨 phase 引用 (phase_refs) ────────┤
              │   feat-auth-v2 → [phase-2, phase-3]    │
              │                                         │
   Theme ─────┼──── 主表 Theme 列 + proposal 覆盖度 ───┤
              │                                         │
              └─────────────────────────────────────────┘

   Sprint (当下执行窗口,与 phase 正交):
              ┌──────── sprint-2026-09 ────────┐
              │  project-A → phase-3 (P1)     │
              │  project-B → phase-2 (P2)     │  ← 一个 sprint 可跨多个 phase
              │  project-C → phase-1 (P3)     │
              └───────────────────────────────┘
```

**核心区分**:

- **Phase** = "我们要构建什么能力"(产品演进轴)
- **Sprint** = "此刻我们在忙什么"(执行节拍,按月)
- **Sprint 不是 phase 的子集**,而是与 phase 正交的时间轴

---

## 1. 三层文件结构

```
.rddf/
├── roadmap.md                              # 主文档 (Phase Skeleton + AUTO-INDEX + AUTO-SPRINT)
├── roadmap/
│   ├── phases/phase-N.md                  # 单 phase 详情 fragment (per add-hierarchical-roadmap-structure)
│   └── features/feat-<name>.md            # 跨阶段 feature fragment
└── state/
    ├── .planner-state.json                # 当前 sprint 视图 (schema v1.1, 含 recommended_route)
    ├── .roadmap-state.json                # 阶段/分类计数(由 action_update_roadmap 自动维护)
    └── .planner-history.jsonl             # sprint 历史(append-only)
```

| 层 | 文件 | 维护方 | git tracked? |
|---|---|---|---|
| 主文档 | `.rddf/roadmap.md` | rdd-planner(**独占**,per ADR-0048) | ✅ |
| Phase fragment | `.rddf/roadmap/phases/phase-N.md` | rdd-planner(`rddf roadmap migrate` / 用户手动) | ✅ |
| Feature fragment | `.rddf/roadmap/features/feat-<name>.md` | rdd-planner(`rddf roadmap add-feature`) | ✅ |
| State | `.rddf/state/.planner-state.json` | rdd-planner(`sync --apply`) | ❌ gitignored |
| State | `.rddf/state/.roadmap-state.json` | loop action(自动) | ❌ gitignored |

---

## 2. 主文档三大 sentinel 区域

主文档 `.rddf/roadmap.md` 用 HTML 注释哨兵切成 3 段,语义上截然不同:

```
┌─────────────────────────────────────────────────────┐
│ ## Phase Skeleton                                   │  ← 用户手动编辑
│ (主题 + 状态 + 分类表,每行一个 phase-theme)          │
├─────────────────────────────────────────────────────┤
│ <!-- AUTO-INDEX -->                                  │  ← 自动生成
│ ## Fragment Index (auto-generated)                  │    (refresh_auto_index)
│ ### Phases / ### Features                            │
├─────────────────────────────────────────────────────┤
│ <!-- AUTO-SPRINT-START -->                           │  ← 自动生成
│ ## Current Sprint: sprint-YYYY-MM                    │    (update_roadmap 唯一写入方)
│ | Project | Phase | Priority | ... |                 │
│ ### Unmapped (N)                                    │
│ <!-- AUTO-SPRINT-END -->                             │
└─────────────────────────────────────────────────────┘
```

**实际样例**(本项目 `.rddf/roadmap.md`):

```markdown
## Phase Skeleton
| Phase   | Theme                              | Status |
|---------|------------------------------------|--------|
| phase-1 | 完整多会话支持                      | active |
| phase-2 | 编排能力完善                       | active |
| phase-3 | 流程定制层                          | active |
| phase-4 | 多方对称 + 回归                     | active |

<!-- AUTO-INDEX -->
## Fragment Index (auto-generated)
### Phases
- `phase-1` — 定时循环与事件触发
- ...
### Features
- `feat-fix-audit-findings` — 2026-08-26 文档与代码一致性审计后续修复

<!-- AUTO-SPRINT-START -->
## Current Sprint: sprint-2026-09
| Project      | Phase   | Priority | Proposal                    |
|--------------|---------|----------|-----------------------------|
| rdd-workflow | phase-3 | P1       | rdd-builder-auto-pick-mode   |

### Unmapped (239)
- ...
<!-- AUTO-SPRINT-END -->
```

**编辑约束**:

| 区域 | 谁可编辑 | 写入保护 |
|---|---|---|
| `## Phase Skeleton` | 用户手动 | 无锁 |
| `<!-- AUTO-INDEX -->` | `_lib/roadmap_state.py::refresh_auto_index` 自动 | atomic write |
| `<!-- AUTO-SPRINT -->` | `_lib/roadmap_sprint.py::update_roadmap` 自动 | FileLock + atomic write(.tmp + rename) |

---

## 3. 唯一写入方矩阵 (per ADR-0038 §7 + ADR-0042 §1)

防 multi-writer race(历史教训:`iteration.corrupt.*` 30+ 残留文件即此问题)。

| 文件 | 唯一写入方 | 锁机制 |
|---|---|---|
| `## Phase Skeleton` 表格 | 用户手动 | 无锁 |
| `<!-- AUTO-INDEX -->` 块 | `_lib/roadmap_state.py::refresh_auto_index` | atomic write |
| `<!-- AUTO-SPRINT -->` 块 | `_lib/roadmap_sprint.py::update_roadmap` (per ADR-0038 §7 **sole writer**) | FileLock + atomic write |
| `.rddf/state/.roadmap-state.json` | `_lib/loop/actions.py::action_update_roadmap` | 独立锁(不与上冲突) |
| `.rddf/roadmap/phases/phase-N.md` | `rddf roadmap migrate` / 用户手动 | git tracked,无并发 |
| `.rddf/roadmap/features/feat-*.md` | `rddf roadmap add-feature` | per-file FileLock |
| `.rddf/state/.planner-state.json` | `_lib/planner_sync.py::apply_state` | atomic_write + FileLock |
| `.rddf/state/.planner-history.jsonl` | `rddf planner advance-sprint` | append-only FileLock |

**关键约束**:`planner_sync.py` **不直接渲染 sprint block**,而是委托 `_lib/roadmap_sprint.update_roadmap(..., table="project")`。

---

## 4. Sprint 与 Phase 的正交关系

| 维度 | Phase | Sprint |
|---|---|---|
| 时间尺度 | 长期(数周到数月) | 短期(执行节拍,默认 1 个月) |
| 表达 | "我们要构建什么能力" | "此刻我们在忙什么" |
| 数量 | 4-10 个 | 1 个 active(`current_sprint`) |
| 跨关系 | 单 phase 或 phase-N.M 嵌套 | 一个 sprint 可跨多个 phase 的 active project |
| 推进机制 | `rddf roadmap advance`(gate 守护) | `rddf planner advance-sprint` |
| 谁在推进 | 用户手动 + 完成度门控 | rdd-planner 自动 + 时间触发 |
| 格式 ID | `phase-N` / `phase-N.M` | `sprint-YYYY-MM`(per ADR-0041) |

**关键洞察**:Sprint 是**当下窗口**,Phase 是**长期目标**。一个 sprint 可能并行做 phase-1、phase-2、phase-3 的不同项目(只要它们 active)。

---

## 5. 端到端数据流

```
用户调 add-improve → rdd-workflow-brainstorm (HARD-GATE)
  ↓
创建 .rddf/improvements/<name>.md (5 段)
  ↓
注册到 improvement-suggestions.md
  ↓
rddf planner attach <name> --project-id X --phase Y [--theme Z]
  ↓ (per-file FileLock + atomic_write)
更新 .rddf/improvements/<name>.md (添加 **主题**: **阶段**: 头部)
  ↓
rddf planner sync --apply
  ↓ (委托 update_roadmap table="project")
更新 .planner-state.json::active_projects
  ↓
更新 .rddf/roadmap.md AUTO-SPRINT 块 (含 Current Sprint 表 + Unmapped 列表)
  ↓
rddf planner advance-sprint  (写 history snapshot + 刷新 AUTO-SPRINT)
  ↓
.rddf/state/.planner-handoff.json (含 recommended_route advisory)
  ↓
rdd-builder P0 5-option gate
  ├─ recommended_route=simple → 💡 推荐选项 5 (dispatch-quick)
  └─ 其他 → 选项 1-4
```

---

## 6. 本项目当前状态(2026-09 快照)

| 指标 | 值 |
|---|---|
| Phase 数 | 4(phase-1 ~ phase-4) |
| Theme 数 | 11(跨 4 个 phase) |
| 当前 Sprint | `sprint-2026-09` |
| Active projects | 2(rdd-builder-auto-pick-mode, rdd-builder-phase0-llm-integration) |
| Unmapped proposals | 239 |
| Active features | 2(`feat-fix-audit-findings`, `feat-fix-archive-gaps-v2`) |

**含义**:本项目当前 attach 治理是 bottleneck — 239 个 improvement 等待 attach 到 phase/theme。建议:

```bash
# 查看 unmapped 列表
rddf planner sync --dry-run
# 或
rddf planner status
```

---

## 7. 常见误读与踩坑

| 误读 | 实际 |
|---|---|
| "sprint 是 phase 的子集" | ❌ sprint 与 phase 正交,一个 sprint 可跨多个 phase |
| "feature fragment 是 phase 的子级" | ❌ feature 跨**多个独立 phase**(`phase_refs: [...]`),不是 phase-N.M |
| "AUTO-SPRINT 块可手动编辑" | ❌ 由 `_lib/roadmap_sprint.update_roadmap` 唯一写入,手动编辑会被覆盖 |
| "Phase Skeleton 可自动维护" | ❌ 这是用户手动编辑区域,反映长期路线图骨架 |
| "sub-phase 命名可以 `phase-1-2`" | ❌ 必须严格 `phase-N.M`(单层数字后缀,per `validate-fragments` R4) |
| "sub-phase 可独立于伞表" | ❌ 父 phase 的伞表必须**先于**所有 `###` 子阶段 heading |
| "Roadmap 由 rdd-arch 维护" | ❌ 自 v4.0.1(ADR-0048),**rdd-planner 完全独占 roadmap**,rdd-arch 已完全脱离 |
| "roadmap.md 是用户根目录文件" | ❌ 主文档在 `.rddf/roadmap.md`,项目根的 `roadmap.md` 是 deprecated stub 指针 |
| "improvement 直接创建 openspec proposal" | ❌ improvement 是 5 段设计草稿(`.rddf/improvements/`),openspec proposal 由 rdd-builder P0 创建 |

---

## 8. 主题状态词汇(per `roadmap-proposal-guidance` v2.2+)

主文档 `## Phase Skeleton` 表格 Theme 列支持 3 种状态:

| 状态 | 含义 | 计入分母 |
|---|---|---|
| `未覆盖` | roadmap 定义但无 proposal 匹配 | 计入 |
| `已覆盖` | 至少一个 proposal 的 `**主题**:` 字段精确匹配 | 不计入 |
| `~skipped~` | 用户显式标记豁免(cell 末尾追加) | 不计入 |

`rdd-planner` Phase 1 preflight 计算 coverage 比率,`STRICT_PROPOSAL_COVERAGE=yes` 升级为严格阻断。

---

## 9. 嵌套阶段语法(per `phase-N.M`)

```markdown
### Phase 7: CPU+GPGPU Fused SoC (phase-3)
**完成条件**:
  - [ ] phase-3.1 ~ phase-3.6 全部完成

#### 任务分类 (伞表,必须先于子阶段)
| gpu-infra | 7.A GPU 基础设施 | (phase-3.1) | P0 | ... |

### 7.A GPU 基础设施 (phase-3.1)
#### 任务分类
| gpu-bundle | ... | ... | P0 | ... |
```

**约束**:

1. 父 phase 伞表必须**先于**所有 `###` 子阶段 heading
2. change meta `roadmap.phase` 可指向子阶段 ID(`phase-3.3`)
3. `advance_phase` 自动聚合子阶段完成度
4. 嵌套 ID 语法严格 `phase-N.M`(单层),禁止 `phase-1-2`
5. 平铺 `phase-N` 完全支持(向后兼容)

详见 `skills/roadmap/SKILL.md` §"嵌套阶段语法"。

---

## 10. 关键 CLI(快速速查)

```bash
# 初始化
rddf roadmap init                    # 4 模板选择 (C++ lib / Web app / blank / from-ADR)

# 查看状态
rddf roadmap status                  # 阶段 + 分类详情 + 门控
rddf planner status                  # sprint + active_projects + recommended_route

# 编辑
rddf roadmap edit                    # 交互式菜单(添加 phase / 修改分类 / ...)
rddf roadmap add-feature <name> \
    --phase-refs phase-2,phase-3 \
    --theme "RBAC 权限模型"          # 创建跨阶段 feature fragment

# 验证
rddf roadmap validate <change>       # 校验 change 的 phase/category 归属
rddf roadmap validate-fragments      # 8 条 R1-R8 校验规则

# 推进
rddf roadmap advance                 # phase 推进(完成度门控守护)
rddf planner advance-sprint          # sprint 推进(强制 new_sprint > old_sprint,per ADR-0041)

# 迁移(单文件 → fragment 树)
rddf roadmap migrate --dry-run       # 预览
rddf roadmap migrate --execute --yes # 执行(需 --yes 显式确认)
```

---

## 11. 关联文档

- **阶段治理视角**: [`workflow-phases.md`](workflow-phases.md) — Stage 2 段讲 rdd-planner 治理
- **状态与事件**: [`state-and-events.md`](state-and-events.md) — handoff 文件格式
- **rdd-arch ↔ rdd-planner 集成**: [`rdd-arch-rdd-planner-integration.md`](rdd-arch-rdd-planner-integration.md)
- **v4 数据流**: [`v4-pipeline-data-flow.md`](v4-pipeline-data-flow.md) — `recommended_route` 完整路径
- **roadmap 命令参考**: [`skills/roadmap/SKILL.md`](../../skills/roadmap/SKILL.md) — 5 个子命令详情
- **添加新 ADR/feature 的扩展点**: [`extension-points.md`](extension-points.md)
- **演进历史**: [`historical-evolution.md`](historical-evolution.md)

---

*文档版本: 2026-09-21(本项目 v4.0.1, ADR-0048 落地后)*
*生成背景: 见对话历史 — 用户首次接触 rdd-workflow 时发现"roadmap 内容组织"概念散落,无单一入口*
