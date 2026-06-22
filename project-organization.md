# HydraForge 项目整理多阶段执行计划

> **计划类型**: 文档 + 架构双轨整理（多阶段、依赖驱动）
> **执行模式**: OpenSpec 混合模式（Hybrid B+A）— Stages 1+2 共用一个 change，Stages 3/4/5 各自独立 change；所有 change 都 amend 现有 `tech-debt-cleanup` capability
> **总工期估计**: 5-9 周
> **最后验证**: 2026-06-12

---

## TL;DR

> **核心目标**: 把 HydraForge 的"文档/ADR/spec/代码"四方漂移（drift）收敛到单一真相源；把 `engine.h` 的 6 路跨模块耦合通过接口反转解开；为后续规模化重构铺好 Build/CI 基础设施。
>
> **关键交付物**:
> - 5 个 OpenSpec change 全部归档
> - 6 类状态标签统一（ADR 文本、README 表格、relationships.md、SPECS-ALIGNMENT.md、AGENTS.md、agenticdsl/ 反向引用）
> - 13 个已废弃 ADR 物理归档到 `docs/archive/adr/`
> - 三套 stdlib spec 合并为 1 套；两套 memory spec 合并为 1 套
> - `agenticdsl/` 子树提升为 `docs/proposals/`
> - `LayeredContext` 真正实现（替代 flat `unordered_map`）
> - `engine.h` 零跨模块 include（接口反转原则）
> - `compile_commands.json` + `CMakePresets.json` + GitHub Actions CI
>
> **关键路径**: Stage 1 → Stage 2 → Stage 3 → Stage 4（Stage 5 与 3/4 并行）
> **关键风险**: Stage 4（engine.h 解耦）涉及 10+ 模块，必须最后独立执行

---

## Context

### 原始需求

用户要求基于"对 `docs/adr` 和 `docs/specs` 的梳理"和"项目架构建议"两个前置输出，给出一个**完整的、包含优先级和依赖关系的多阶段执行计划**。

### 关键发现（已审计，2026-06-12）

**已完成的清理工作**（2026-06-08 至 2026-06-10，最近 3 个 OpenSpec change 已归档）：
- `docs-code-alignment-fixes`：13 个 ADR 标为"已废弃"，死链修复，状态字段同步
- `tech-debt-and-doc-cleanup`：log.h 门面、5 个孤儿 lib 子图删除、`src/modules/prompts.yaml` 删除、LLMCallNode 死代码移除、IExecutionPolicy 3 模式实现、CostCollector 集成
- C1 migration：IInteractionBus 上线，公共头文件迁至 `include/agenticdsl/`

**仍然存在的核心问题**（按依赖顺序）：

1. **元数据漂移**（最低成本修复）— 2 个 466 字节占位 ADR（0029/0035）、5 个编号空洞（0024-0028）、3 套状态词汇并存、ADR-0008 自我矛盾（文件"已批准" vs README"❌未实施"）
2. **归档未完成**— 13 个标记为"已废弃"的 ADR 仍在活动树
3. **规范碎片化**— stdlib spec 有 3 份（dsl-lib.md / phase2-standard-library.md / stdlib.md），memory spec 有 3 份（memory.md / phase2 §memory / dsl §10.3），命名空间互不一致
4. **agenticdsl/ 语义混淆**— 32 篇语言演进提案与 28 个已批准 ADR 混在同一根目录
5. **Context 模型三方冲突**— `src/core/types/context.h` 是 flat `unordered_map`；`dsl.md` §4.1 规定 `LayeredContext`；ADR-0008 标"❌未实施"
6. **engine.h 耦合黑洞**— `src/core/engine.h` 直接 include 6 个模块头文件（scheduler/parser/budget/llm/mock/tools），是 ADR-0019 §1.4 列为"待解决"但未修复的问题
7. **NodeExecutor 紧耦合**— 把 `MarkdownParser` 作为成员对象持有（应改为 `IParser*` 抽象）
8. **examples 实际已断**— LSP 诊断显示 `examples/agent_simple/simple.cpp` 和 `examples/agent_loop/agent_loop.cpp` 找不到 `agenticdsl/core/engine.h`（C1 迁移后未同步更新 examples）
9. **基础设施缺失**— 无 `compile_commands.json`、无 `CMakePresets.json`、无 CI，每次重构靠手工 `cmake && ctest`
10. **AGENTS.md 漂移**— 引用已删除的 `src/modules/prompts.yaml`，与当前代码状态不一致

### Metis 审查反馈（已采纳）

- **重置每阶段开头的状态校验**：每次重新进入计划必须跑 `git log --oneline -20` 防止新工作被遗漏（最近一次审计中 4/5"未解决问题"已被归档）
- **使用 OpenSpec 混合模式**：1 个 umbrella change 覆盖 Stages 1+2（都是元数据/文档），3 个独立 change 覆盖 Stages 3/4/5（都是代码或基础设施）
- **Amend 现有 `tech-debt-cleanup` capability**：不创建新的 base spec，避免能力碎片化
- **MVP 范围 = Stage 1**：3-5 天可独立交付，验证后不打断后续阶段
- **不混阶段**：文档阶段与代码阶段不能合并到同一 OpenSpec change

### 用户决策（已确认）

| 决策点 | 选择 | 理由 |
|---|---|---|
| 执行模式 | Hybrid B+A（Oracle 不可用，按 Metis 建议自决） | 平衡审计统一性与阶段独立性 |
| Context 模型 | **实现 LayeredContext** | code → spec 对齐，符合 dsl.md §4.1 + ADR-0008 |
| engine.h 时机 | **最后阶段独立执行** | 涉及 10+ 模块，先决于 Context 决策 |
| agenticdsl/ 位置 | **提升为 `docs/proposals/`** | 区分"已批准决策"（ADR-NNNN）与"未决提案" |

---

## Work Objectives

### Core Objective

将 HydraForge 的"文档/规范/代码/构建"四方漂移收敛为可维护、可验证、可扩展的一致体系；用 5 个有内部依赖关系的阶段完成 13 类已识别问题的修复。

### Definition of Done（项目级，描述性，非任务项）

> 下列条目是项目级 Definition of Done 的描述，**不是可勾选任务**。
> 实际验证在 Final Verification Wave (F1-F4) 与每个 Stage 的退出条件中执行。

- 所有 ADR 状态、编号、引用在 `docs/README.md`、`relationships.md`、文件文本三处一致
- 13 个已废弃 ADR 物理归档到 `docs/archive/adr/`，README 不再列出
- stdlib spec 仅 1 份；memory spec 仅 1 份；CONTEXT 模型仅 1 份
- `engine.h` 直接 include 模块数 = 0
- `LayeredContext` 在 `include/agenticdsl/types/context.h` 中实现，所有调用方迁移完毕
- `cmake --build build && ctest --output-on-failure` 100% 通过
- 6 个 examples 全部能 build
- CI 绿灯，自动验证新增回归

### Must Have

- 所有阶段的 OpenSpec change 走完 proposal → design → tasks → specs → archive 完整闭环
- 每个阶段结束都有可执行的退出命令（`cmake --build` + `ctest` + 针对性 `grep` 校验）
- 所有向后兼容的 break（API 改名、include 路径变更）在 OpenSpec proposal 中显式声明

### Must NOT Have（防漂移护栏）

- 不创建新的 `openspec/specs/<新能力>/spec.md`，统一 amend `tech-debt-cleanup/spec.md`
- 不在 Stage 1 之前开始任何 spec 合并（状态词汇未统一会传播漂移）
- 不在 Stage 3 之前开始任何 Context 相关代码改动
- 不在 Stage 4 中触碰 `engine.h` 之外的 include 链
- 不删除任何 ADR 内容（已废弃的也要保留在 `docs/archive/adr/` 可追溯）
- 不混"文档清理"与"代码重构"到同一 OpenSpec change
- 不修改 `src/common/policy/` 三个 mode 策略的接口（已实现完整，不动）

### Spec Framework Integration

- **Detected Framework**: OpenSpec (Fission-AI)
- **Config File**: `openspec/config.yaml`（schema: spec-driven）
- **Active Specs**: `openspec/specs/tech-debt-cleanup/spec.md`、`openspec/specs/docs-code-alignment/spec.md`
- **Active Changes**: 无（最近的 2 个已归档）
- **Available Commands**: `/opsx:propose`、`/opsx:apply`、`/opsx:archive`
- **Spec-to-Task Mapping**: 每个新阶段 → 1 个 OpenSpec change → tasks.md 包含该阶段所有 task → 通过 `archive` 完成后能力自动合并到 base spec

---

## Verification Strategy

### Test Decision

- **Infrastructure exists**: YES（24 个 Catch2 测试文件）
- **Automated tests**: 现有 + 阶段增量；TDD 模式由具体阶段决定
- **Framework**: Catch2 v3
- **Per-stage 规则**:
  - 文档阶段：grep 验证 + ctest 全绿（不破坏现有测试）
  - 代码阶段：TDD 写新测试 + 迁移现有测试 + ctest 全绿
  - 构建阶段：CI 自身就是验证

### QA Policy（每个 stage 末尾的强制退出校验）

```
阶段 1 退出:
  cmake --build build && ctest --output-on-failure  # 24/24 PASS
  grep -rn "已批准\|未实施\|部分实施\|提议中\|已替代" docs/adr/  # 0 命中
  ls docs/adr/adr-0029.md docs/adr/adr-0035.md 2>&1 | grep -c "No such"  # = 2
  ls examples/agent_simple/simple.cpp examples/agent_loop/agent_loop.cpp && cmake --build build  # 全部通过

阶段 2 退出:
  find docs/specs -name "*stdlib*" -o -name "*memory*"  # 数量从 6 个收敛到 2 个
  find docs/archive/adr -name "adr-*.md" | wc -l  # = 13
  ls docs/proposals/  # 旧 agenticdsl/ 已迁移

阶段 3 退出:
  ctest --output-on-failure  # 25+/25+ PASS
  grep -rn "unordered_map<std::string, Value>" src/  # 0 命中
  grep -rn "LayeredContext" src/ include/  # ≥ 5 处使用

阶段 4 退出:
  grep -c '#include "modules/\|#include "common/' src/core/engine.h  # = 0
  for d in agent_basic agent_loop agent_simple skill_porting slice_01_tool_call; do cmake --build build/$d || echo "FAIL: $d"; done
  ctest --output-on-failure  # 全绿

阶段 5 退出:
  ls compile_commands.json  # 存在
  ls CMakePresets.json  # 存在
  python3 tools/adr_lint.py docs/adr/  # 0 错误
  python3 tools/adr_relationships.py --check  # relationships.md 与 frontmatter 一致
```

---

## Execution Strategy

### 阶段依赖图

```
Stage 1 (Cleanup Foundation, 3-5d)
   ↓
Stage 2 (Spec Consolidation, 1-2w) ───┐
   ↓                                  │
Stage 3 (LayeredContext, 1-2w)        │ 可并行
   ↓                                  ↓
Stage 4 (engine.h Decoupling, 2-3w)  Stage 5 (Build/CI, 1w)
                                      ↓
                              (Stage 5 跑在 3/4 期间任意时刻)
```

**关键路径**: 1 → 2 → 3 → 4 = 约 6-11 周（如果串行）
**最大并行加速**: Stage 5 与 Stage 3 或 4 并行 → 约 5-9 周
**建议**: Stage 5 启动在 Stage 1 完成后立即开始，作为"基础设施地基"与 Stages 2-4 并行

### 阶段状态机

| 阶段 | OpenSpec Change | 启动条件 | 完成条件 | 预计工期 |
|------|-----------------|----------|----------|----------|
| 1 | `docs-and-arch-cleanup-foundation` | 无（可立即开始） | 6 个状态标签统一 + 占位文件清理 | 3-5d |
| 2 | 同 1 | Stage 1 完成 + 6 标签已固化 | 13 ADR 归档 + agenticdsl 提升 + spec 合并 | 1-2w |
| 3 | `layered-context-implementation` | Stage 1 完成（Stage 2 不是硬前置） | LayeredContext 实现 + 全部测试通过 | 1-2w |
| 4 | `core-interface-inversion` | Stage 3 完成 | engine.h 0 跨模块 include + 6 examples 全 build | 2-3w |
| 5 | `build-system-bootstrap` | Stage 1 完成（独立） | CI 跑通 + compile_commands + presets | 1w |

**关键约束**:
- Stage 1 必须**先**于其他所有阶段（最高优先级）
- Stage 2 和 Stage 3 互不依赖，但都依赖 Stage 1
- Stage 4 必须**后**于 Stage 3（Context 模型决定影响 engine.h 边界）
- Stage 5 任何时候都可以并行启动（建议从 Stage 1 完成后立即开始）

### OpenSpec 实际目录结构

```
openspec/changes/
├── 2026-06-XX-docs-and-arch-cleanup-foundation/    # Stages 1+2
│   ├── proposal.md
│   ├── design.md
│   ├── tasks.md            # 13+ tasks across Stages 1+2
│   └── specs/
│       └── tech-debt-cleanup/
│           └── spec.md     # AMEND 现有
├── 2026-06-XX-layered-context-implementation/      # Stage 3
├── 2026-06-XX-core-interface-inversion/            # Stage 4
└── 2026-06-XX-build-system-bootstrap/              # Stage 5
```

---

## TODOs

> 任务标签使用裸数字（1, 2, 3...），子步骤以 Stage 标题为前缀。
> OpenSpec change ID 在每个 Stage 头部标注。

### Stage 1 — Cleanup Foundation [OpenSpec: docs-and-arch-cleanup-foundation]

> **amends**: `openspec/specs/tech-debt-cleanup/spec.md`
> **工期**: 3-5 天 | **风险**: 低 | **依赖**: 无（可立即开始）
> **MVP**: 是，本阶段可独立交付

- [ ] 1. [S1] 删除占位 ADR 文件并修复 phantom 引用
  - 删除 `docs/adr/adr-0029.md` 和 `docs/adr/adr-0035.md`（两个 466 字节占位）
  - 修复 `docs/adr/adr-0030-async-runtime-dual-layer.md:16` 对 ADR-0025 的 phantom 引用 → 改为"未来 ADR-0024+（预留）"
  - 修复 `docs/adr/adr-0031-execution-policy.md:423` 对 ADR-0027 的 phantom 引用 → 改为"ADR-0031 自身 §2（Plan/Agent/YOLO 三模式定义）"
  - 在 `docs/README.md` 的 adr 表格中移除 0029/0035 行
  - **不修改**已废弃 ADR（13 个 `❌未实施` 标记的）的内容
  - **Recommended Agent Profile**: `quick` — 单文件删除 + 文本修复
  - **QA**:
    ```
    ls docs/adr/adr-0029.md docs/adr/adr-0035.md 2>&1 | grep -c "No such"  # = 2
    grep -c "ADR-0025" docs/adr/adr-0030-async-runtime-dual-layer.md  # = 0
    grep -c "ADR-0027" docs/adr/adr-0031-execution-policy.md  # = 0
    grep -c "adr-0029\|adr-0035" docs/README.md  # = 0
    ```

- [ ] 2. **[S1] 收敛状态词汇到 6 个标准标签**
  - 在 `docs/adr/STATUS-GLOSSARY.md`（新建）固化 6 标签：✅ Approved / 🟡 Partial / ❌ Not Implemented / ⛔ Superseded / 🔍 Proposed / 📋 Reserved
  - 扫所有 ADR 文件头，替换"已批准/未实施/部分实施/提议中/已替代"为对应 emoji
  - 更新 `docs/README.md` 表格：`docs/adr/relationships.md`、`docs/SPECS-ALIGNMENT.md` 同步
  - **不改变** 0029/0035 的状态（已删）；**不修改** ADR 的实质内容（仅状态字段）
  - **Recommended Agent Profile**: `quick` — 大批量 sed-style 替换
  - **Blocked By**: 任务 1（占位文件先删）
  - **QA**:
    ```
    cat docs/adr/STATUS-GLOSSARY.md | wc -l  # ≥ 30
    grep -rn "已批准\|未实施\|部分实施\|提议中\|已替代" docs/ | grep -v STATUS-GLOSSARY  # = 0 命中
    cmake --build build && ctest  # 仍 100% 通过
    ```

- [ ] 3. **[S1] 修复 ADR-0008 自我矛盾 + 同步 AGENTS.md**
  - 在 `docs/adr/adr-0008-structured-context.md` 顶部加注脚："LayeredContext C++ 实现见 Stage 3（layered-context-implementation），本 ADR 在 2026-06-08 之前仅完成规范层面"
  - 在 `docs/README.md` 标 ADR-0008 状态为 🟡 Partial
  - 重新生成 `AGENTS.md`：删除 `src/modules/prompts.yaml` 引用；删除过时工具链描述；更新 L0 engine.h 耦合描述
  - **不修改** ADR-0008 的规范内容（那是 Stage 2/3 的工作）
  - **Recommended Agent Profile**: `quick` — 文本编辑
  - **QA**:
    ```
    grep "adr-0008" docs/README.md  # 显示 🟡
    grep -c "prompts.yaml" AGENTS.md  # = 0
    cmake --build build && ctest  # 仍通过
    ```

- [ ] 4. **[S1] 修复 examples 头文件引用（C1 迁移后续修复）**
  - 修改 `examples/agent_simple/simple.cpp:1`：将 `#include "agenticdsl/core/engine.h"` 改为 `#include "agenticdsl/agenticdsl.h"`
  - 修改 `examples/agent_loop/agent_loop.cpp:1`：同上
  - 检查其他 4 个 examples（agent_basic, skill_porting, slice_01_tool_call, superpowers）统一迁移
  - 在 `AGENTS.md` 添加"公共头文件路径"小节
  - **不修改** examples 业务逻辑
  - **Recommended Agent Profile**: `quick` — 6 个文件 sed 替换
  - **QA**:
    ```
    grep -rn "agenticdsl/core/engine.h" examples/  # = 0
    for d in agent_basic agent_loop agent_simple skill_porting slice_01_tool_call; do
      cmake --build build/$d || echo "FAIL: $d"
    done  # 全部通过
    ```

- [ ] 5. **[S1] Stage 1 退出验证 + 提交**
  - 跑完整 build + test 套件
  - 跑状态词汇检查、占位文件检查、examples build 检查
  - 在 `openspec/changes/2026-06-XX-docs-and-arch-cleanup-foundation/tasks.md` 标记任务 1-4 为 [x]
  - 提交 commit 并 push
  - **Recommended Agent Profile**: `quick` — 验证步骤
  - **Blocked By**: 任务 1, 2, 3, 4

---

### Stage 2 — Spec Consolidation [OpenSpec: docs-and-arch-cleanup-foundation 续]

> **amends**: `openspec/specs/tech-debt-cleanup/spec.md`
> **工期**: 1-2 周 | **风险**: 中 | **依赖**: Stage 1（状态词汇必须先统一）

- [ ] 6. **[S2] 提升 agenticdsl/ 为 docs/proposals/**
  - 移动整个 `docs/adr/agenticdsl/` 目录到 `docs/proposals/`
  - 更新 `docs/README.md`：删除 `adr/agenticdsl/` 行，新增 `proposals/` 行（带 14 子目录索引）
  - 更新所有 32 个 proposals 文档的内部链接：从 `[adr-0001](adr/adr-0001-...)` 改为 `[adr-0001](../adr/adr-0001-...)`
  - 添加 18 个 ADR → 5 个最相关 proposals 的反向引用（按 `ALIGNMENT-REVIEW.md` 建议）
  - **不重写** proposals 内容，只调整链接
  - **Recommended Agent Profile**: `unspecified-high` — 大批量链接修复
  - **Blocked By**: 任务 2（状态词汇统一）
  - **QA**:
    ```
    ls docs/proposals/  # 14 子目录
    ls docs/adr/agenticdsl/ 2>&1 | grep -c "No such"  # = 1
    grep -rn "docs/adr/agenticdsl" docs/  # = 0
    grep -rE "\.\./adr/adr-" docs/proposals/ | wc -l  # ≥ 30
    ```

- [ ] 7. **[S2] 物理归档 13 个已废弃 ADR**
  - 创建 `docs/archive/adr/` 目录
  - 移动 13 个 ADR 文件到此目录：
    - `phase-2-memory/adr-0010`, `0011`, `0012`, `0013`, `0014`（5 个）
    - `phase-3-reasoning/adr-0015`, `0016`, `0017`, `0018`（4 个）
    - `phase-5-async/adr-0030`、`phase-5-policy/adr-0032`、`phase-7-router/adr-0034`、`phase-8-kernel/adr-0036`（4 个）
  - 更新 `docs/README.md`：删除这 13 行；新增 `docs/archive/adr/` 索引行
  - 在 `docs/adr/relationships.md` 添加"归档 ADR 列表"小节
  - **不删除** ADR 内容；保留完整可追溯
  - **Recommended Agent Profile**: `quick` — 13 个 `git mv`
  - **Blocked By**: 任务 2
  - **QA**:
    ```
    find docs/archive/adr -name "adr-*.md" | wc -l  # = 13
    grep -E "adr-0010|adr-0011|adr-0012|adr-0013|adr-0014|adr-0015|adr-0016|adr-0017|adr-0018|adr-0030|adr-0032|adr-0034|adr-0036" docs/README.md  # = 0
    cmake --build build && ctest  # 仍通过（docs 改动不影响）
    ```

- [ ] 8. **[S2] 合并 3 套 stdlib spec → 1 套**
  - 读 `docs/specs/dsl-lib.md` (v3.10) — 11 个子图
  - 读 `docs/specs/phase2-standard-library.md` (v1.0) — 31+ 子图（覆盖 ADR-0010~0018）
  - 读 `docs/specs/stdlib.md` (v1.0) — 8 个子图
  - 创建 `docs/specs/stdlib-v3.10.md`：合并 3 份 spec 的子图（去重 + 命名空间对齐）
  - 命名空间统一为 `dsl.md` §2.1 的 3 层架构：`/lib/dslgraph/`、`/lib/memory/`、`/lib/reasoning/`、`/lib/conversation/`、`/lib/workflow/`
  - 删除 3 个原文件
  - 更新 `docs/README.md` 中 3 行 → 1 行
  - 更新 `docs/specs/dsl.md` 的 `§10.3` 引用指向新文件
  - **不修改** 子图语义，只统一命名空间
  - **Recommended Agent Profile**: `unspecified-high` — 需要 spec 阅读理解
  - **Blocked By**: 任务 2, 7（README 表格更新）
  - **QA**:
    ```
    find docs/specs -name "*stdlib*"  # 恰好 1 个
    grep -rE "phase2-standard-library|stdlib\.md|dsl-lib" docs/specs/  # = 0 (除归档元数据)
    grep -E "/lib/(human|error|auth|data|utils)/" docs/specs/  # = 0（已统一）
    ```

- [ ] 9. **[S2] 合并 3 套 memory spec → 1 套**
  - 读 `docs/specs/memory.md` (v3.2 草案) — 6 个核心子图
  - 读 `docs/specs/dsl.md` §10.3 — 8 个子图（命名空间格式 `@v1`）
  - 此前 `phase2-standard-library.md` 已在任务 8 中归档
  - 创建 `docs/specs/memory-v3.10.md`：合并 memory.md 与 dsl.md §10.3 的子图
  - 子图命名对齐 dsl.md `@v3.10` 后缀规范（如 `kg_write_fact` → `kg.write_fact@v3.10`）
  - 删除 `docs/specs/memory.md`
  - 更新 `docs/specs/dsl.md` 的 `§10.3` 引用指向新文件
  - **Recommended Agent Profile**: `unspecified-high`
  - **Blocked By**: 任务 2, 8
  - **QA**:
    ```
    find docs/specs -name "*memory*"  # 恰好 1 个
    grep -E "kg_write_fact|kg_write_subgraph" docs/specs/  # = 0（已统一为 kg.write_fact）
    grep -E "@v1" docs/specs/memory-v3.10.md  # = 0（已升级为 @v3.10）
    ```

- [ ] 10. **[S2] 重新审计 SPECS-ALIGNMENT.md 状态徽章**
  - 读 `docs/SPECS-ALIGNMENT.md` §变更追踪（line 86-99）
  - 重置所有 ✅ 徽章为待审状态
  - 重新逐文件验证：每个声称都对应到具体代码或 ADR 引用
  - 修正 `specs/architecture.md` 实际路径（line 99 已知错误）
  - **Recommended Agent Profile**: `quick` — 文本编辑
  - **Blocked By**: 任务 8, 9（spec 合并后审计才有意义）
  - **QA**:
    ```
    grep -E "✅ 已更新" docs/SPECS-ALIGNMENT.md  # 全部带 [需重新审计] 标注
    grep -E "agenticdsl/architecture" docs/SPECS-ALIGNMENT.md  # = 0
    ```

- [ ] 11. **[S2] Stage 2 退出验证 + 提交 + 归档 OpenSpec change**
  - 跑完整 build + test 套件
  - 跑 `docs/specs/` 文件清单检查
  - 在 tasks.md 标记任务 6-10 为 [x]
  - 跑 `git commit -m "chore(stage2): spec consolidation"`
  - **不** 立即归档 OpenSpec change（要等 Stage 4 完成后整体归档，但 tasks.md 完成度可先标）
  - **Recommended Agent Profile**: `quick` — 验证步骤
  - **Blocked By**: 任务 6, 7, 8, 9, 10

---

### Stage 3 — LayeredContext Implementation [OpenSpec: layered-context-implementation]

> **amends**: `openspec/specs/tech-debt-cleanup/spec.md`
> **工期**: 1-2 周 | **风险**: 高（核心数据结构变更）| **依赖**: Stage 1（词汇统一）

- [ ] 12. **[S3] 设计 `LayeredContext` C++ 类型并写测试**
  - 在 `include/agenticdsl/types/layered_context.h` 定义：
    ```cpp
    namespace agenticdsl::types {
      // L1: system (只读, 来自 env)
      // L2: recent (短期 session 状态, 可写)
      // L3: working (当前任务数据, 可写)
      // L4: archive (历史, 压缩存储, 追加写)
      // L5: meta (元数据, 类型/权限)
      struct LayeredContext {
        nlohmann::json system;
        nlohmann::json recent;
        nlohmann::json working;
        nlohmann::json archive;
        nlohmann::json meta;

        // path-based access: "working.data.user_input"
        nlohmann::json& at(const std::string& path);
        const nlohmann::json& at(const std::string& path) const;

        // layer-aware: 检查 path 是否在允许 layer
        bool can_read(const std::string& path, Permission p) const;
        bool can_write(const std::string& path, Permission p) const;
      };
    }
    ```
  - 写 `tests/test_layered_context.cpp`：≥ 8 test cases（每层 ≥ 1 个，路径访问 ≥ 2 个，权限 ≥ 2 个）
  - **TDD**: 先写失败测试，再写实现
  - **Recommended Agent Profile**: `cpp` — 核心数据结构
  - **Skills**: `test-driven-development`, `cpp-modernize`
  - **QA**:
    ```
    cmake -B build -DAGENTICDSL_BUILD_TESTS=ON && cmake --build build && ctest --output-on-failure  # 25+/25+
    cat tests/test_layered_context.cpp | grep -c "TEST_CASE"  # ≥ 8
    ```

- [ ] 13. **[S3] 迁移所有调用方从 flat Context → LayeredContext**
  - 调用点扫描：`grep -rn "Context\b" src/modules/ src/core/ | grep -v "LayeredContext\|test_\|CMakeLists"`
  - 主要调用方：
    - `src/modules/scheduler/topo_scheduler.cpp:147` — `execute(Context)`
    - `src/modules/executor/node_executor.h:50` — `execute_dsl_node(..., Context&)`
    - `src/modules/cognitive/simple_orchestrator.cpp` — `process(..., Context)`
    - `src/common/tools/registry.h` — 工具签名如有 Context
  - 策略：保持 `Context` 作为 `using Context = LayeredContext;` 的 typedef（向后兼容）
  - 添加 deprecation warning：`[[deprecated("use LayeredContext explicitly")]]` 仅在 flat 操作时触发
  - **不修改** 任何 `Context::operator[]` 调用（语义已变）；改为 `ctx.working["key"]`
  - **Recommended Agent Profile**: `cpp` — 大批量迁移
  - **Skills**: `cpp-modernize`, `cpp-architecture`
  - **Blocked By**: 任务 12
  - **QA**:
    ```
    ctest --output-on-failure  # 全部通过
    grep -rn "unordered_map<std::string, Value>" src/  # = 0
    grep -rn "LayeredContext" src/ include/ | wc -l  # ≥ 5
    grep -rn "Context& ctx\|Context ctx" src/  # 仍存在（typedef 兼容）
    ```

- [ ] 14. **[S3] 更新 ADR-0008 + docs/specs/dsl.md 状态**
  - 读 `docs/adr/adr-0008-structured-context.md` — 更新状态字段：🟡 Partial → ✅ Approved
  - 读 `docs/specs/dsl.md` §4.1 — 确认 LayeredContext 字段已与 C++ 实现一致；如不一致，更新 spec
  - 更新 `docs/README.md` ADR-0008 状态行
  - **不修改** spec 的语义（只是把代码追上 spec）
  - **Recommended Agent Profile**: `quick` — 状态字段同步
  - **Blocked By**: 任务 13
  - **QA**:
    ```
    grep "状态" docs/adr/adr-0008-structured-context.md | head -1  # 包含 ✅
    grep "adr-0008" docs/README.md  # 显示 ✅
    ```

- [ ] 15. **[S3] Stage 3 退出验证 + 提交**
  - 跑 `cmake --build build && ctest --output-on-failure`
  - 跑 6 个 examples 的 build 验证
  - 在 `openspec/changes/2026-06-XX-layered-context-implementation/tasks.md` 标 [x]
  - 提交 commit 并 push
  - **Recommended Agent Profile**: `quick` — 验证步骤
  - **Blocked By**: 任务 12, 13, 14

---

### Stage 4 — engine.h Decoupling [OpenSpec: core-interface-inversion]

> **amends**: `openspec/specs/tech-debt-cleanup/spec.md`
> **工期**: 2-3 周 | **风险**: 高（10+ 模块受影响）| **依赖**: Stage 3（Context 模型决定）

- [ ] 16. **[S4] 定义 `i*` 接口（IScheduler, IParser）**
  - 在 `include/agenticdsl/contract/ischeduler.h` 定义：
    ```cpp
    namespace agenticdsl::contract {
      class IScheduler {
       public:
        virtual ~IScheduler() = default;
        virtual void register_node(const std::string& id, NodeFactory f) = 0;
        virtual void append_dynamic_graphs(const std::string& base_id, const ParsedGraph& g) = 0;
        virtual ExecutionResult execute(const LayeredContext& ctx) = 0;
      };
    }
    ```
  - 在 `include/agenticdsl/contract/iparser.h` 定义：
    ```cpp
    class IParser {
     public:
      virtual ~IParser() = default;
      virtual ParsedGraph parse(const std::string& markdown) = 0;
      virtual ParsedGraph parse_file(const std::filesystem::path& p) = 0;
    };
    ```
  - 已有：`IInteractionBus`、`IExecutionPolicy`、`ICognitiveOrchestrator`
  - **不修改** 现有实现
  - **Recommended Agent Profile**: `cpp`
  - **Skills**: `cpp-architecture`
  - **QA**:
    ```
    ls include/agenticdsl/contract/  # 5 个 .h（iinteraction_bus, inmemory_bus, iexecution_policy, ischeduler, iparser）
    cmake --build build  # 仍通过
    ```

- [ ] 17. **[S4] 改 TopoScheduler / MarkdownParser 继承 i* 接口**
  - `src/modules/scheduler/topo_scheduler.h`：class TopoScheduler : public IScheduler
  - `src/modules/parser/markdown_parser.h`：class MarkdownParser : public IParser
  - 添加 `override` 关键字
  - **不修改** 方法签名（保持向后兼容）
  - **Recommended Agent Profile**: `cpp`
  - **Blocked By**: 任务 16
  - **QA**:
    ```
    grep "public IScheduler" src/modules/scheduler/topo_scheduler.h
    grep "public IParser" src/modules/parser/markdown_parser.h
    cmake --build build && ctest  # 仍通过
    ```

- [ ] 18. **[S4] 添加 CMake INTERFACE include set**
  - 修改根 `CMakeLists.txt`：创建 `agenticdsl::core_headers` INTERFACE 库
  - 链接 `include/` 到 INTERFACE_INCLUDE_DIRECTORIES
  - 让 `agenticdsl/agenticdsl.h` 可被外部项目 include
  - **不修改** 现有 module 库的 target
  - **Recommended Agent Profile**: `cmake`
  - **Skills**: `cmake`
  - **Blocked By**: 任务 16
  - **QA**:
    ```
    grep "INTERFACE_INCLUDE_DIRECTORIES.*include" CMakeLists.txt
    cmake -B build && cmake --build build  # 仍通过
    ```

- [ ] 19. **[S4] 重构 engine.h 移除跨模块 include**
  - 当前 `src/core/engine.h:11-16` 包含：
    ```cpp
    #include "modules/scheduler/topo_scheduler.h"  // ← 移除
    #include "modules/parser/markdown_parser.h"    // ← 移除
    #include "modules/budget/budget_controller.h"  // ← 移除
    #include "common/llm/llm_types.h"              // ← 保留（types/）
    #include "common/llm/mock_provider.h"          // ← 移除
    #include "common/tools/registry.h"             // ← 移除
    ```
  - 改为：只 include `core/agenticdsl.h` + `contract/i*` 头文件
  - `engine.h` 持有 `std::unique_ptr<IScheduler>`、`std::unique_ptr<IParser>` 等
  - **不修改** `DSLEngine` 的公开 API
  - **Recommended Agent Profile**: `cpp`
  - **Skills**: `cpp-architecture`
  - **Blocked By**: 任务 17, 18
  - **QA**:
    ```
    grep -c '#include "modules/\|#include "common/' src/core/engine.h  # = 0
    grep -c '#include "agenticdsl/contract/' src/core/engine.h  # ≥ 3
    cmake --build build && ctest  # 仍通过
    ```

- [ ] 20. **[S4] 改 NodeExecutor 持有 IParser* 而非嵌入 MarkdownParser**
  - 当前 `src/modules/executor/node_executor.h:40` 持有 `MarkdownParser markdown_parser_`
  - 改为：`std::unique_ptr<IParser> parser_`
  - DSLEngine 注入 parser
  - **不修改** 任何 `markdown_parser_` 调用点（语义不变）
  - **Recommended Agent Profile**: `cpp`
  - **Skills**: `cpp-architecture`
  - **Blocked By**: 任务 17
  - **QA**:
    ```
    grep "MarkdownParser markdown_parser_" src/modules/executor/node_executor.h  # = 0
    grep "IParser" src/modules/executor/node_executor.h  # ≥ 1
    ctest  # 仍通过
    ```

- [ ] 21. **[S4] 验证 6 个 examples 全 build + 更新 ADR-0019**
  - 跑 6 个 examples 完整 build
  - 修复 examples 头文件路径（如有遗漏）
  - 更新 `docs/adr/adr-0019-iinteraction-bus-mvp.md` §1.4："跨模块耦合问题已修复（2026-06-XX）"
  - **Recommended Agent Profile**: `quick` — 验证 + 文档
  - **Blocked By**: 任务 19, 20
  - **QA**:
    ```
    for d in agent_basic agent_loop agent_simple skill_porting slice_01_tool_call; do
      cmake --build build/$d 2>&1 | tail -3
    done  # 全部 0 error
    grep "已修复\|已解决" docs/adr/adr-0019-iinteraction-bus-mvp.md  # ≥ 1
    ```

- [ ] 22. **[S4] Stage 4 退出验证 + 提交 + 归档 OpenSpec change**
  - 跑全部 build + test + examples
  - 跑退出条件 grep 检查
  - 在 tasks.md 标 [x]
  - 提交并 push
  - 归档 OpenSpec change
  - **Recommended Agent Profile**: `quick` — 验证步骤
  - **Blocked By**: 任务 16-21

---

### Stage 5 — Build System & CI [OpenSpec: build-system-bootstrap]

> **amends**: `openspec/specs/tech-debt-cleanup/spec.md`
> **工期**: 1 周 | **风险**: 中 | **依赖**: Stage 1（独立任务，可从 Stage 1 完成后立即开始）

- [ ] 23. **[S5] 添加 compile_commands.json 生成**
  - 修改根 `CMakeLists.txt`：
    ```cmake
    set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
    ```
  - 创建 `compile_commands.json` 的 symlink 到 build 目录
  - 添加 `compile_commands.json` 到 `.gitignore`（不提交）
  - **不修改** 现有 target 配置
  - **Recommended Agent Profile**: `cmake`
  - **Skills**: `cmake`
  - **QA**:
    ```
    cmake -B build && ls build/compile_commands.json  # 存在
    grep "compile_commands.json" .gitignore  # = 1
    ```

- [ ] 24. **[S5] 添加 CMakePresets.json**
  - 在根目录创建 `CMakePresets.json`：
    ```json
    {
      "version": 3,
      "configurePresets": [
        { "name": "debug",   "binaryDir": "build/debug",   "cacheVariables": { "CMAKE_BUILD_TYPE": "Debug" } },
        { "name": "release", "binaryDir": "build/release", "cacheVariables": { "CMAKE_BUILD_TYPE": "Release" } },
        { "name": "asan",    "binaryDir": "build/asan",    "cacheVariables": { "CMAKE_BUILD_TYPE": "Debug", "CMAKE_CXX_FLAGS": "-fsanitize=address" } }
      ]
    }
    ```
  - **不修改** 现有 `cmake -B build` 工作流
  - **Recommended Agent Profile**: `cmake`
  - **Blocked By**: 任务 23
  - **QA**:
    ```
    ls CMakePresets.json  # 存在
    cmake --preset debug && cmake --build build/debug  # 成功
    ```

- [ ] 25. **[S5] 添加 GitHub Actions CI**
  - 创建 `.github/workflows/ci.yml`：
    - jobs: configure (cmake), build (make -j), test (ctest), lint (clang-tidy)
    - 在 ubuntu-latest + GCC 11/12 + Clang 14/15 上跑
  - 添加 CI badge 到 `README.md`
  - **不修改** 现有 build 命令
  - **Recommended Agent Profile**: `unspecified-high`
  - **Blocked By**: 任务 23, 24
  - **QA**:
    ```
    ls .github/workflows/ci.yml
    gh workflow view ci.yml  # 解析成功
    # 推送后 GitHub Actions 跑通（需要 push 权限）
    ```

- [ ] 26. **[S5] 写 tools/adr_lint.py**
  - 在 `tools/adr_lint.py` 写：
    - 解析所有 `docs/adr/adr-*.md` 文件头
    - 验证必填字段：`adr:`, `title:`, `status:`, `date:`
    - 验证 `status:` 值在 6 个标准标签内
    - 验证 `depends-on:` 引用的 ADR 必须存在
    - 验证 `supersedes:` 不能引用比自己更新的 ADR
  - 添加到 `.github/workflows/ci.yml` 作为 lint job
  - **不修改** ADR 内容（只校验）
  - **Recommended Agent Profile**: `quick` — Python 脚本
  - **QA**:
    ```
    python3 tools/adr_lint.py docs/adr/  # exit 0
    python3 tools/adr_lint.py docs/adr/ 2>&1 | grep -c "ERROR"  # = 0
    ```

- [ ] 27. **[S5] 写 tools/adr_relationships.py 自动生成 relationships.md**
  - 解析 ADR frontmatter
  - 生成依赖图（Mermaid 格式 + 表格）
  - 输出到 `docs/adr/relationships.md`
  - 在 CI 中跑：`python3 tools/adr_relationships.py --check` 验证与文件一致
  - **替换** 手写的 `relationships.md`
  - **Recommended Agent Profile**: `quick` — Python 脚本
  - **Blocked By**: 任务 26
  - **QA**:
    ```
    python3 tools/adr_relationships.py --check  # exit 0
    python3 tools/adr_relationships.py --write  # 生成 relationships.md
    git diff docs/adr/relationships.md  # 仅变化部分
    ```

- [ ] 28. **[S5] Stage 5 退出验证 + 提交 + 归档 OpenSpec change**
  - 跑 CI 完整流程
  - 跑 adr_lint + adr_relationships
  - 提交并 push 触发 CI
  - 归档 OpenSpec change
  - **Recommended Agent Profile**: `quick` — 验证步骤
  - **Blocked By**: 任务 23-27

---

### Final Verification Wave

> 4 个 review agent 并行运行，全部 APPROVE 后由用户确认。

- [ ] F1. 计划合规性审计
  - 端到端读所有 4 个 OpenSpec change 的 proposal/design/tasks
  - 验证 5 个 Stage 退出条件全部满足
  - 验证所有 `Must Have` 已交付，所有 `Must NOT Have` 未违反
  - 输出：`Compliance [N/N] | VERDICT: APPROVE/REJECT`
  - Agent: oracle

- [ ] F2. 代码质量审查
  - 跑 `cmake --build build && ctest` 全绿
  - 跑 `clang-tidy` 在所有改动的 .h/.cpp 上
  - 检查 LayeredContext、i* 接口的 API 一致性
  - 输出：`Build [PASS/FAIL] | Tests [N pass/N fail] | Lint [N clean/N issues] | VERDICT`
  - Agent: unspecified-high

- [ ] F3. 真实人工 QA（agent 代理）
  - 跑 6 个 examples 完整 build + 执行
  - 跑全部 28 个 ADR 的退出验证
  - 跑 Stage 1-5 的所有退出 grep 检查
  - 跑 ADR-0019 §1.4 验证（engine.h 0 跨模块 include）
  - 跑 AGENTS.md 准确性核验（无 stale 引用）
  - 输出：`Scenarios [N/N pass] | Integration [N/N] | VERDICT`
  - Agent: unspecified-high

- [ ] F4. 范围保真度检查
  - 读 5 个 OpenSpec change 的 tasks.md 完成度
  - 验证每个 Stage 任务的 acceptance criteria 全部勾选
  - 验证 13 个已废弃 ADR 物理归档
  - 验证 6 个状态标签在 docs/README.md 中唯一使用
  - 验证 stdlib/memory/context 三类 spec 各自仅 1 份
  - 输出：`Tasks [N/N compliant] | Contamination [CLEAN] | VERDICT`
  - Agent: deep

---

## Commit Strategy

| Stage | Commit 消息 | 涉及文件 |
|-------|------------|----------|
| 1 | `chore(stage1): cleanup foundation (placeholders + status vocab + examples)` | docs/adr/, AGENTS.md, examples/ |
| 2 | `chore(stage2): spec consolidation (proposals + archive + stdlib/memory merge)` | docs/adr/, docs/proposals/, docs/specs/ |
| 3 | `feat(context): implement LayeredContext (L1-L5 structured)` | include/agenticdsl/types/layered_context.h, src/, tests/ |
| 4 | `refactor(core): interface inversion (engine.h decoupled, i* contracts)` | include/agenticdsl/contract/, src/core/, src/modules/ |
| 5 | `ci: build system bootstrap (presets + workflows + adr lint)` | CMakeLists.txt, CMakePresets.json, .github/workflows/, tools/ |

每个 commit 独立推送，每个 Stage 结束后归档对应的 OpenSpec change。

---

## Success Criteria

### 阶段级验证命令

```bash
# Stage 1
cmake --build build && ctest --output-on-failure  # 24/24
grep -rn "已批准\|未实施\|部分实施" docs/ | grep -v STATUS-GLOSSARY  # 空
ls docs/adr/adr-0029.md 2>&1 | grep "No such"  # 文件已删

# Stage 2
find docs/specs -name "*stdlib*" -o -name "*memory*" | wc -l  # = 2
find docs/archive/adr -name "adr-*.md" | wc -l  # = 13
ls docs/proposals/ | wc -l  # = 14

# Stage 3
grep -rn "unordered_map<std::string, Value>" src/  # 空
ctest --output-on-failure  # 25+/25+

# Stage 4
grep -c '#include "modules/' src/core/engine.h  # = 0
for d in agent_basic agent_loop agent_simple skill_porting slice_01_tool_call; do
  cmake --build build/$d
done  # 全部成功

# Stage 5
ls compile_commands.json CMakePresets.json .github/workflows/ci.yml  # 3 个文件
python3 tools/adr_lint.py docs/adr/ && python3 tools/adr_relationships.py --check  # 0 错误
```

### 最终检查清单（描述性，非任务项）

> 下列条目是项目级最终检查清单，**不是可勾选任务**。验证在 Final Verification Wave (F1-F4) 中执行。

- 5 个 OpenSpec change 全部归档到 `openspec/changes/archive/`
- 6 个状态标签在所有文档中唯一使用
- 13 个已废弃 ADR 物理归档
- stdlib/memory spec 各自 1 份
- agenticdsl/ → proposals/ 完成
- LayeredContext 在 include/ 中实现并被使用
- engine.h 0 跨模块 include
- 6 个 examples 全 build
- CI 绿灯
- tools/adr_lint.py + tools/adr_relationships.py 工作

---

## 附录 A: OpenSpec Change 模板

每个新 change 目录结构（参考 `openspec/changes/archive/2026-06-10-tech-debt-and-doc-cleanup/` 模板）：

```
openspec/changes/2026-06-XX-<change-name>/
├── proposal.md      # 为什么做（背景、目标、影响）
├── design.md        # 怎么做（架构、接口、迁移路径）
├── tasks.md         # 做什么（按编号列出所有 task + acceptance）
└── specs/
    └── tech-debt-cleanup/  # AMEND 现有
        └── spec.md  # 增量的需求 + scenario（不重写 base spec）
```

## 附录 B: ADR Frontmatter Schema（Stage 1 + Stage 5 配合引入）

```markdown
---
adr: NNNN
title: <标题>
status: approved | partial | not-implemented | superseded | proposed | reserved
deciders: [<团队>]
date: YYYY-MM-DD
supersedes: []          # 替代的旧 ADR 编号
depends-on: [adr-NNNN]  # 依赖的 ADR 编号
last-verified-against-code: YYYY-MM-DD
---

# ADR-NNNN: <标题>
```

## 附录 C: 风险登记表

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| Stage 4 engine.h 解耦引入 ABI 破坏 | 高 | 通过 `IScheduler*` / `IParser*` 抽象层；保留旧 `TopoScheduler` 名称为 typedef |
| Stage 3 Context 重构影响 10+ 调用方 | 高 | `using Context = LayeredContext` 兼容层 + 全测试覆盖 |
| Stage 2 spec 合并丢失细节 | 中 | 由 spec 作者人工 review 合并后的内容；不退化为自动合并 |
| Stage 5 CI 引入外部依赖（GitHub Actions） | 中 | 本地先验证 `ctest` 通过；CI 仅作冗余验证 |
| 元数据状态词汇变化被遗漏 | 低 | Stage 1 末尾 grep 强制 0 命中 |

