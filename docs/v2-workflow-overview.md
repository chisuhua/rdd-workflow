# rdd-workflow v2.0 业务流程全景

> **版本**: 2.0.0
> **日期**: 2026-07-09
> **目标读者**: 使用 rdd-workflow 的产品经理、架构师、开发者

---

## 架构理念

rdd-workflow v2.0 按**三阶段架构**（ADR-0003）拆分，用户感知的是**三个业务层级**的循环：

```
 Roadmap ──────→ Feature ──────→ Change ──────→ Archive ──────→ Roadmap
   ^                                                                │
   └──────────────────────── 反馈闭环 ──────────────────────────────┘
```

| 层级 | 技能 | 用户操作 | 人工介入 |
|------|------|---------|---------|
| **Roadmap** | `guide-arch` + `roadmap.md` | 定义方向：ADR、差距分析、阶段划分 | **高** |
| **Feature** | `feature.md` | 分组管理：查看进度、依赖图、执行顺序 | **低**（只读） |
| **Change** | `guide-plan` + `guide-ship` | 具体执行：创建→执行→归档 | **中→低** |

---

> **💡 推荐入口**：首次使用请从 `skill_use("guide")` 开始。推荐器会根据当前项目状态（arch/plan/ship handoff、worktree、sprint 视图）自动建议下一步。

---

## 目录

- [第一层：Roadmap（方向定义）](#第一层roadmap方向定义)
- [第一层内部反馈闭环](#第一层内部反馈闭环)
- [第二层：Feature（分组管理）](#第二层feature分组管理)
- [第三层：Change（具体执行单元）](#第三层change具体执行单元)
  - [子层 A：创建 Change（guide-plan）](#子层-a创建-changeguide-plan)
  - [第三层反馈闭环 1：guide-plan 内部](#第三层反馈闭环-1guide-plan-内部)
  - [子层 B：执行 Change（guide-ship）](#子层-b执行-changeguide-ship)
  - [第三层反馈闭环 2：guide-ship 内部](#第三层反馈闭环-2guide-ship-内部)
- [跨层反馈闭环（完整 10 个）](#跨层反馈闭环完整-10-个)
- [全流程遍历](#全流程遍历)
- [关键设计原则](#关键设计原则)
- [产出物汇总](#产出物汇总)

---

## 第一层：Roadmap（方向定义）

**技能**：`guide-arch` + `roadmap.md`

**入口**：`skill_use("guide-arch")`

### 完整状态机（5 个阶段）

```
Phase 1: setup
   ├── 环境检测（openspec CLI / git / 构建目录）
   ├── 工件发现（ADR-0016 Layer 1：自动扫描 ADR 目录/roadmap/architecture 目录）
   └── 展示当前状态菜单
        ↓
Phase 2: adr-create
   ├── 查看现有 ADR 列表（状态/标题）
   ├── 创建新 ADR（从模板 ADR-0000-template.md 复制）
   ├── 查看指定 ADR 详情
   └── 编辑已有 ADR
        ↓
Phase 3: architecture
   ├── 生成架构差距分析文档（\*-gap-analysis.md）
   ├── 查看现有差距分析报告
   └── 编辑已有差距分析
        ↓
Phase 4: roadmap-define  ───委托──→ roadmap.md 的技能
   ├── init（4 类模板：C++ 库/Web 应用/空白/基于 ADR 生成）
   ├── status（查看阶段进度 + 分类统计）
   ├── edit（添加/修改阶段 + 任务分类 + 完成条件）
    ├── advance（门控检查 → 推进到下一阶段）
    ├── gate-report（生成阶段门控报告）
    └── validate（验证 change phase/category 分类）
        ↓
Phase 5: arch-done（出口）
   ├── 双重门控：ADR ≥ 1 + roadmap.md 存在
   └── 写入 .rddf/state/.arch-handoff.json（arch→plan 交接）
```

### 第一层内部反馈闭环

```
adr-create ──→ architecture ──→ roadmap-define ──→ adr-create（循环细化）
      ↑                                                      │
      └────────── 发现需要新 ADR，回到创建阶段 ────────────────┘
```

**第一层产出物**：

| 文件 | 说明 |
|------|------|
| `docs/adr/ADR-*.md` | 架构决策记录 |
| `roadmap.md` | 路线图定义 |
| `docs/architecture/*-gap-analysis.md` | 架构差距分析 |
| `.rddf/state/.arch-handoff.json` | arch→plan 交接信号 |

**用户操作频率**：低频，每个主要架构阶段执行一次。

---

## 第二层：Feature（分组管理）

**技能**：`feature.md`

**本质**：纯派生视图，**不修改任何 change artifacts**。从 `iteration.json` + `deps-analysis.json` 读取数据，写回 `feature_view` 节点。

### 4 个子命令

| 命令 | 功能 |
|------|------|
| `feature summary` | 汇总表：状态图标 + change 数量/已归档数 + 并行组/阻塞关系 |
| `feature graph` | Mermaid 流程图（feature 级拓扑 + 冲突边 + cycle 检测；注：依赖边受单 blocker 字段限制，多 change 的 feature 间通常无法形成完整依赖边） |
| `feature status <name>` | drill-down：单个 feature 的所有 change 状态表 |
| `feature order` | 按 wave 分组的推荐执行顺序 |

> **使用时机**：推荐在 `guide-plan` 的 deps 阶段之后、`guide-ship` 之前运行 `feature order` 决定处理顺序。Feature 是纯只读视图，可在任意阶段安全调用。

### Feature 派生逻辑

```
proposal.md 中 parent_feature 字段
   或 change name 以 feature-<name>-<part> 命名
                ↓
        iteration.json
                ↓
        feature_view.py
    ├── derive_feature_name()  — 推断归属
    ├── compute_feature_edges() — 构建拓扑
    ├── compute_status()       — 聚合状态
    └── compute_execution_order() — 推荐顺序
```

### 第二层反馈闭环

```
feature summary（用户看到进度）
        ↓
用户决定处理顺序（order）
        ↓
feature 内的 change 逐个执行/归档
        ↓
feature 的 archived_count 递增 → status 自动更新 → 反馈回 summary
```

**第二层产出物**：仅更新 `iteration.json` 的 `feature_view` 节点；不创建任何独立文件。

---

## 第三层：Change（具体执行单元）

### 子层 A：创建 Change（guide-plan）

**技能**：`guide-plan` + `propose.md` + `deps.md`

**入口**：`skill_use("guide-plan")`（前提：arch-done 已完成，`.arch-handoff.json` 存在）

```
Phase 1: scan
   ├── 环境检测 + arch handoff 验证（硬阻断）
   ├── 委托 propose.md 扫描 4 类差距源：
   │     ├── 1a: ADR 文件（"已采纳，暂不修复"项）
   │     ├── 1b: 架构差距分析（❌ / ⚠️ 项）
   │     ├── 1c: 代码 TODO/FIXME/HACK（前 30 条）
   │     └── 1d: 测试覆盖缺口（有头文件无测试）
   └── 去重合并 → 创建 improvements/*.md + 更新 proposal-suggestions.md 索引
        ↓
Phase 2: propose（用户交互核心）
   ├── 展示建议列表（按 P0/P1/P2 优先级分组）
   ├── 5 队列可视化（候选/骨架/阻塞/可ship/deps过期）
   ├── Feature 进度（每个 feature 的 done/total）
   ├── 用户选择创建 → 执行 openspec 命令序列：
   │     ├── openspec new change "<name>"
   │     ├── openspec status --change "<name>" --json
   │     ├── 循环 openspec instructions <artifact> --change "<name>" --json
   │     └── 按依赖顺序创建 artifacts（proposal.md → design.md → tasks.md）
   ├── skeleton 模式（debt-/fix-/prefix- 前缀自动降级）
   ├── 写入 roadmap-meta.yaml（phase + category）
   └── 更新 iteration.json（status=proposed）
        ↓（可循环回 Phase 3 继续创建更多）
Phase 2.5: fill（骨架→完整）
   ├── 从 iteration.json 读取 planned change
   ├── 按 deps 推荐顺序排列（blocker 清除者优先）
   ├── 填充 design.md + tasks.md
   └── iteration.json status: planned → proposed
        ↓
Phase 3: deps（自动执行，无用户交互）
   ├── Step 0: 读取 .deps-candidates.json
   ├── Step 1: 读取每 change 的 4 类信息：
   │     ├── 文件列表（proposal.md In Scope）
   │     ├── ADR 引用
   │     ├── 接口定义/使用（design.md）
   │     └── roadmap-meta.yaml（阶段/分类）
   ├── Step 2: 静态三轴分析：
   │     ├── 轴1: 文件冲突检测（scope 交集）
   │     ├── 轴2: ADR 依赖链（共享 ADR → 建议顺序）
   │     └── 轴3: 接口依赖（定义/使用链）
    ├── Step 3: AI 子代理语义分析（实验性⚠️，子代理不可用时自动降级为静态三轴分析；当前为接口契约占位，输出质量取决于运行时环境）：
    │     ├── 隐式依赖推断
    │     ├── 粒度评估（拆分/合并建议）
    │     └── 推荐执行顺序
   ├── Step 4: 融合判定（静态 + AI → 最终标记）
   ├── Step 5: 生成输出：
   │     ├── 5a: Mermaid 依赖图
   │     ├── 5b: Change 状态表（ready/prerequisite/blocked_by/conflict）
   │     ├── 5c: 推荐执行顺序
    │     ├── 5d: 冲突警告（当前为占位实现，未真正检测文件冲突）
   │     ├── 5e: AI 分析建议
   │     └── 阶段预检（change 是否在当前 roadmap 阶段内）
   └── Step 6: 同步 iteration.json（blocker/parallel_group/conflicts）
        ↓
Phase 4: plan-done（出口）
   ├── 门控 0: ready-for-ship ≥ 1（iteration.list_ready_for_ship）
   ├── 门控 1: active changes ≥ 1
   ├── 门控 2: 所有 artifacts 已提交（git show HEAD: 验证）
   └── 写入 .rddf/state/.plan-handoff.json（plan→ship 交接）
```

> ⚠️ **plan-done 后用户必须手动调用 `skill_use("guide-ship")` 进入执行阶段。** `guide-plan` 不会自动跳转。

### 第三层反馈闭环 1：guide-plan 内部

```
scan ──→ propose ──→ deps ──→ propose（继续添加 change）
                                    ↓
scan ──→ propose ──→ deps ──→ scan（重新扫描候选）
                                    ↓
Phase 5 自动检查：proposal-suggestions.md 还有剩余 → 问用户要不要继续
```

---

### 子层 B：执行 Change（guide-ship）

**技能**：`guide-ship` + `execute.md` + `status.md`

**入口**：`skill_use("guide-ship")`（前提：plan-done 已完成）

> **`status.md` 可独立使用**：`status` 技能有 5 个独立模式（A–E），可在任意阶段调用查看当前迭代状态，无需进入 guide-ship。例如 `skill_use("status", "--iteration")` 快速查看当前 sprint 视图。

```
Phase 1: plan（选择 + 准备）
   ├── 展示所有活跃 changes 状态表（Artifacts/Worktree/Plan）
   ├── 用户选择要处理的 change
   ├── COMMIT GATE（脏检测 + artifacts 提交验证）
   ├── 并行冲突检测：
   │     ├── 无其他 worktree + 仅此 1 个 change → ⚡ 轻量模式
   │     └── 有 active worktree 或 多个 change → 🔀 worktree 模式
   ├── 创建 branch（openspec/<name>）
   ├── [worktree 模式] git worktree add + WORKTREE VERIFICATION GATE
    ├── [轻量模式] git checkout openspec/<name>
    └── 生成实施计划（委托 rdd-workflow-writing-plans → TDD 5 步结构）

> ⚠️ **轻量模式 UX 说明**：轻量模式下 `guide-ship` 在主仓库直接切分支（`git checkout openspec/<name>`），你的工作目录会跟随分支变更。worktree 模式则在隔离目录 `.rddf/wt/<name>` 中工作，主分支不变。模式由系统自动选择，不可手动指定。

         ↓
Phase 1.5: 监控选择
   ├── 检测活跃 worktree/轻量分支数量
   └── 选择：进入 Execute / 回 Plan 处理其他 change
        ↓
Phase 2: execute（监控模式，读取 tasks.md 进度）
   ├── 实时读取所有 worktree 的 tasks.md 进度
   ├── 选项：本 session 执行 / 分离执行（新终端）
   └── 委托 execute.md 执行（包含 TDD 5 步纪律）：
         ├── Step 1: 确认在 worktree 内
         ├── Step 2: 验证构建环境（cmake -B build + 冷缓存检测）
         ├── Step 3: Review 计划（检查 spec 覆盖/占位符/类型一致性/文件路径）
         ├── Step 4: 每个 Work Unit 按 TDD 5 步执行：
         │     ├── Step 1: Write failing test
         │     ├── Step 2: Run test → verify fails
         │     ├── Step 3: Write minimal implementation
         │     ├── Step 4: Run test → verify passes
         │     └── Step 5: Commit + sed 更新 tasks.md [x]
          ├── Step 5: LSP diagnostics + cmake --build + ctest 验证（TDD 子步骤内完成）
         ├── Step 6: 输出报告 + 同步 iteration.json（tasks_done）
         └── Step 7: 检查其他 worktree → 引导切换
        ↓
Phase 2.5: review（债务扫描）
   ├── 扫描 3 类债务：
   │     ├── ① 新增 TODO/FIXME/HACK（git diff HEAD 抓新增标记）
   │     ├── ② 测试回归（ctest 对比）
   │     └── ③ 架构漂移（偏离 ADR 目标架构）
   ├── 用户选择处理方式：
   │     ├── 1. 范围內债务 → 追加到 tasks.md，回到 execute
   │     ├── 2. 旁效应债务 → 创建新 debt change → 自动增量 deps
   │     ├── 3. 架构漂移 → 生成差距分析文件 → 回注 guide-arch
   │     └── 4. 跳过
   └── FEATURE_ARCHIVE_GATE 检查（可选硬阻断）
        ↓
Phase 3: archive（归档）
   ├── 检测模式（worktree / 轻量）
   ├── [worktree] archive_change() →
   │     ├── MERGE VERIFICATION GATE（detached HEAD 阻断）
   │     ├── pre-merge dirty check
   │     ├── checkout default branch
   │     ├── merge（--ff-only 或 --no-ff fallback）
   │     ├── verify merge result
   │     ├── openspec archive <name> --yes
   │     └── cleanup: worktree remove + branch -D（需 FORCE_BRANCH_DELETE）
   ├── [轻量] merge branch → openspec archive → branch -d
   └── post-archive fill suggestion hook：
         ├── 扫描 iteration.json 中 status=planned 的 change
         └── 检查 blocker 状态 → 已归档 → 提示填充
        ↓
Phase 4: cleanup
   ├── 清理剩余 worktree（逐个或全部）
   └── 清理 openspec/* branches
        ↓
Phase 5: ship-done（出口）
   ├── 检查剩余 worktree/change 数量
   └── 4 个出口选项：
         ├── 1. 继续处理（guide-ship）
         ├── 2. 回 spec 端（guide-arch / guide-plan）创建更多 changes
         ├── 3. 本次 session 结束
         └── 4. 项目完成归档
```

### 第三层反馈闭环 2：guide-ship 内部

```
Phase 1 (选择 change)
    ↓
Phase 2 (execute) ←── Phase 2.5 review 选项 1（范围內债务追加）
    ↓
Phase 3 (archive)
    │
    ├── post-archive hook → 有解除 blocker 的 planned change → 提示回 guide-plan fill
    │
    └── 还有剩余 change/worktree → 继续 Phase 1 循环
    ↓
Phase 5 (ship-done) → 选项 2 → 回 guide-plan 创建更多 changes
                     → 选项 1 → 继续 guide-ship
```

---

## 跨层反馈闭环（完整 10 个）

### 闭环 1：Roadmap → Change（自上而下驱动）

```
roadmap.md 定义阶段 + 分类
    ↓
guide-plan scan → propose 读取 roadmap
    ↓
change 按阶段分配（phase）、按类型分配（category）
    ↓
roadmap-meta.yaml 记录归属
    ↓
deps 阶段预检：验证 change 是否在当前阶段内
```

### 闭环 2：Change → Roadmap（自下而上反馈）

```
execute 完成 → 更新 roadmap-state.json
    ↓
分类的 completed_changes 递增
    ↓
阶段内所有分类完成 → gate_status.all_changes_complete = true
    ↓
roadmap advance → 推进到下一阶段
```

### 闭环 3：Feature ↔ Change（分组管理）

```
iteration.json 的 feature 聚合
    ↓
feature summary 展示进度（archived_count / change_count）
    ↓
用户决策：先处理哪个 feature（按 wave/blocker）
    ↓
change 归档 → feature 进度更新 → 反馈回 summary
```

### 闭环 4：Archive → Plan（级联解阻塞）

```
change-A 归档
    ↓
post-archive hook 扫描 iteration.json
    ↓
发现 change-B（status=planned, blocked_by=change-A）的 blocker 已解除
    ↓
提示用户：运行 guide-plan → fill
    ↓
planned → proposed → 进入正常执行管道
```

### 闭环 5：Execute Review → Plan（债务回流）

```
execute 后 review 发现旁效应债务
    ↓
选项 2：创建新 debt change
    ├── 追加到 proposal-suggestions.md（type=debt）
    └── 自动增量 deps（文件冲突检测 → 追加到 .deps-candidates.json → 重跑 deps）
        ↓
回到 guide-plan 管道，就像普通 change 一样
```

### 闭环 6：Execute Review → Arch（架构漂移回注）

```
execute 后 review 发现架构漂移
    ↓
选项 3：生成差距分析文件 docs/architecture/<name>-drift-analysis.md
    ↓
提示运行 guide-arch
    ↓
架构师审查 → 决定是否修正 ADR → 回到流程起点
```

### 闭环 7：Guide 推荐器（无状态解耦）

```
guide 不写任何文件，只读状态：
  ├── 检查 .arch-handoff.json → 推荐 guide-plan
  ├── 检查 .plan-handoff.json → 推荐 guide-ship
  ├── 检查 worktree 状态 → 推荐监控/执行
  └── 检查 iteration.json → 推荐当前迭代视图
```

### 闭环 8：Plan → Arch（架构缺口回退）

```
propose/deps 发现架构定义不足
（如缺少对应 ADR、roadmap 阶段不存在、分类不匹配）
    ↓
用户手动退出 guide-plan → 运行 guide-arch
    ↓
补充 ADR / 调整 roadmap → 回到 guide-plan
```

### 闭环 9：Status → Action（状态驱动入口）

```
skill_use("status", "--iteration") 查看当前 sprint
    ↓
发现 ready-for-ship change → 直接进入 guide-ship
发现新增候选 → 进入 guide-plan propose
发现阻塞解除 → 进入 guide-plan fill
```

### 闭环 10：Iteration 统一状态汇聚

```
propose → iteration.json 创建/更新
deps    → iteration.json blocker/parallel_group/conflicts 更新
execute → iteration.json tasks_done 更新
archive → iteration.json change 标记为 archived + feature 计数更新
    ↓
feature summary、status --iteration、roadmap AUTO-SPRINT 都从 iteration.json 读取
    ↓
迭代状态一致性由单一状态源保证
```

### 闭环 11：rddf-session 跨 OpenCode session 恢复（ADR-0017）

```
OpenCode session A 中 guide-plan Phase 2 中断
    ↓
OpenCode session B 进入
    ↓
skill_use("rddf-session", "list") 显示 A 创建的 rds_xxx (state=active)
    ↓
skill_use("rddf-session", "resume", "rds_xxx") 转移所有权
    ↓
继续 Phase 2 → Phase 3 → plan-done
```

---

## 全流程遍历

```
Roadmap Layer:
  guide-arch setup → adr-create → architecture → roadmap-define → arch-done
        ↑                                                              ↓
        └──────────────────── 内部循环 ────────────────────────────────┘
                                                                        ↓
Feature Layer:
  feature summary → graph → order（只读，跨 change 聚合）
                                                                        ↓
Change Layer — Plan:
  guide-plan scan → propose(可循环) → fill → deps → plan-done
                                                                        ↓
Change Layer — Ship:
  guide-ship plan → execute(TDD 5步) → review(债务扫描) → archive → cleanup → ship-done
                    ↑_____________|          ↓
                    范围內债务追加  旁效应→proposal-suggestions.md(闭环5)
                                  架构漂移→guide-arch gap analysis(闭环6)
                                                                        ↓
Post-Archive Hook:
  级联解阻塞 planned change → 提示回 guide-plan fill(闭环4)
                                                                        ↓
Roadmap Update:
  archive 完成 → roadmap-state.json 更新(闭环2)
  阶段全完成 → advance 推进
```

---

## 产出物汇总

| 层级 | 阶段 | 产出文件 | 追踪 |
|------|------|---------|------|
| **Roadmap** | arch-done | `.rddf/state/.arch-handoff.json` | gitignored |
| | arch | `docs/adr/ADR-*.md` | 受版本控制 |
| | arch | `roadmap.md` | 受版本控制 |
| | arch | `docs/architecture/*-gap-analysis.md` | 受版本控制 |
| **Feature** | — | `iteration.json` (feature_view 节点) | gitignored |
| **Change** | scan | `improvements/*.md` + `proposal-suggestions.md` (Markdown 索引) | 受版本控制 |
| | propose | `openspec/changes/<name>/{proposal,design,tasks}.md` | 受版本控制 |
| | propose | `openspec/changes/<name>/roadmap-meta.yaml` | 受版本控制 |
| | plan-done | `.rddf/state/.plan-handoff.json` | gitignored |
| | deps | `.rddf/state/.deps-output.md` | gitignored |
| | deps | `.rddf/state/.deps-analysis.json` | gitignored |
| | archive | `openspec/changes/archive/<date>-<name>/` | 受版本控制 |

## 关键设计原则

| 原则 | 体现 |
|------|------|
| **单向流动** | Roadmap → Feature → Change，每一层都有反馈机制 |
| **Handoff 契约** | arch-done / plan-done 写 `.json`，下游读到手硬阻断或优雅降级 |
| **状态即真相** | 不从文件系统重算，从 `iteration.json` 统一读取 |
| **Write 只有一处** | `iteration.py::add_or_update_change()` 是唯一 mutation 入口 |
| **降级不崩溃** | AI 子代理不可用 → fallback；handoff 缺失 → 旧行为 |
| **门控不跳过** | arch-done 双重门控，plan-done 三重门控，merge verification gate |
| **债务不积累** | review Phase 2.5 强制要求显式决策：处理债务（范围内/旁效应）、回注架构漂移、或确认跳过；不允许无意识跳过 |
| **rddf-session 持久化**（ADR-0017） | 跨 OpenCode session 的 workflow 上下文通过 `.rddf/state/sessions.json` 持久化；冲突时 4 选项软提示（放弃/转移/强制/查看）；30 分钟无心跳 → orphaned |

---

## 相关文档

- `docs/adr/ADR-0003-three-phase-architecture.md` — 三阶段架构 ADR
- `docs/adr/ADR-0007-gate-mechanism.md` — 门控机制设计
- `docs/adr/ADR-0011-phase-step-execution-model.md` — 阶段步骤化执行模型
- `docs/adr/ADR-0016-arch-discovery-contract.md` — 架构工件发现契约
- `docs/v2-loop-engine-guide.md` — Loop 引擎技术细节
- `docs/v2-developer-guide.md` — 扩展开发指南
- `docs/v2-gate-mechanism-guide.md` — 门控机制指南
- `docs/proposal-suggestions-format.md` — proposal-suggestions.md 格式规范
