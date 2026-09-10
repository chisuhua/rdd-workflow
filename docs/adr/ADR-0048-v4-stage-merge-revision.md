# ADR-0048: v4 stage-merge 修订 — rdd-arch 完全脱离 roadmap + rdd-builder P0 触发 rdd-quick

> **状态**: 已采纳 (2026-09-09)
> **日期**: 2026-09-09
> **决策者**: sisyphus + user override + 2026-09-09 rdd-planner alignment audit
> **替代/修订**: ADR-0043 §1 (rdd-arch slim)、ADR-0047 D1 (rdd-quick 自 triage)、ADR-0038 §Decision 1 (planner horizontal orchestrator)
> **触发**: 2026-09-09 Oracle 架构审查 (`ses_f7a9e01dbffe2Lqu8jYjg4YvL2`) + user design intent (2026-09-09 对话)

## Context

v4 stage-merge (ADR-0043, 2026-09-04) 把 5 阶段架构合并为 4 阶段 (`rdd-arch → rdd-planner → rdd-builder → rdd-verifier`)。Wave 1+2+3 落地后 (per ADR-0044), 2026-09-09 rdd-planner alignment audit 揭示三类系统性问题需要修订:

### 问题 1: rdd-arch 与 roadmap 边界未真正分离

- ADR-0043 §1 line 30 明文 "rdd-arch 不再生成 roadmap-related 数据; 这些职责移交给 rdd-planner"
- 但 `skills/rdd-arch/SKILL.md` 实际仍保留 Phase 4 roadmap-define + role.boundaries.owns 仍包含 `roadmap.md` + `.rddf/roadmap/features/*.md` + `.rddf/roadmap/phases/*.md` (审计 finding C-1)
- arch-done Phase X Roadmap Sync (L721-746) 仍调用 `roadmap_incremental_update.sh`——证明 arch 端在做 roadmap 工作
- arch-done 双重门控 (ADR ≥ 1 + roadmap.md 存在) 隐含 arch 对 roadmap 有所有权

**架构后果**: 违反 ADR-0028 角色边界; 新加入者读 rdd-arch SKILL.md 会误以为 arch 管 roadmap

### 问题 2: rdd-planner 的 advisory 信号是死字段

- `_lib/schemas/planner_state_schema.json` 声明 `recommended_route` 字段 (enum `simple/complex/unknown`)
- 但 `_lib/planner_state.py::_default_state()` 不写入, `render_state()` 不产出, `rddf planner status` 不展示
- 唯一测试 `test_planner_handoff_schema_v1_rename.py` 仅验 schema 存在 (审计 finding Oracle delta D-5)
- `fix-v4-rdd-planner-scope-over-assignment` AC-13 把它列为 **optional**——从未被任何 runtime 消费

**架构后果**: schema-only 残骸; 任何依赖该字段的决策逻辑都找不到输入

### 问题 3: rdd-quick 决策点缺乏结构化信号

- ADR-0047 D1: "rdd-quick self-triages regardless"——quick 在没有完整 proposal.md 时自行判断复杂度
- quick P1 complexity triage 仅依赖 user 的 natural language + AI 综合判定 (per SKILL.md P1 complex/simple signals 清单)
- **错过结构化信号**: rdd-planner 已 attach 的 project/phase/theme + sprint 上下文 + 历史上同 project 的 simple/complex 比例
- **错过权威决策点**: rdd-quick 是实施通道, 不是入口推荐权威; 决策应在信息最完整的阶段做

**架构后果**: rdd-quick 沦为"任意用户都能强制进入的旁路"; 复杂度判定不准; rdd-quick 失败升级时回 planner 形成"planner → builder → quick → planner"潜在循环

## Decision

### 决策 1: rdd-arch 完全脱离 roadmap

**a. SKILL.md 删除 Phase 4 roadmap-define** (line 520-658, ~138 行):

```diff
- ## Phase 4: roadmap-define
- ... (整个 phase)
- ## Phase 5: arch validation
+ ## Phase 5: arch validation (门控检查)
```

**b. arch-done 门控从双重降为单重** (移除 `roadmap.md 存在` 检查):

```diff
 arch-done 必须满足双重门控才能通过:
- 1. ADR 数量 ≥ 1
- 2. roadmap.md 存在
+ 1. ADR 数量 ≥ 1 (单门控)
```

**c. role.boundaries.owns 移除 roadmap 相关**:

```diff
 owns:
   - "docs/adr/ADR-*.md"
-  - "roadmap.md"
-  - ".rddf/roadmap/phases/*.md"
-  - ".rddf/roadmap/features/*.md"
   - "docs/architecture/*-gap-analysis.md"
   - ".rddf/state/.arch-handoff.json"
   - ".rddf/state/.populate-state.json"  # 删除: 改由 planner 维护
```

**d. 删除 arch-done Phase X Roadmap Sync 调用** (L721-746):

```diff
- #### Step X: Roadmap Sync (internal)
- ... (整个 step)
```

**e. 反向引用修订**: Phase 6 arch-done 输出 "💡 Next: skill_use('rdd-planner')" 不变 (rdd-planner 现在接管 roadmap 初始化)

### 决策 2: rdd-planner 完全接管 roadmap + 新增 Phase 0

**a. SKILL.md 新增 Phase 0 roadmap-bootstrap** (在 setup 之前):

```
## Phase 0: roadmap-bootstrap (NEW per ADR-0048)

入口条件: 用户调用 skill_use("rdd-planner") 立即执行。

行为: 检测 .rddf/roadmap.md 是否存在。
  - 存在: 直接进入 Phase 1 setup
  - 不存在: 引导用户走 `rddf roadmap init` (skill_use("roadmap", "init"))
    提供 4 模板选择 (per roadmap skill):
    1. C++ 库项目 (基础 → 核心 → 高级)
    2. Web 应用 (MVP → 功能 → 优化)
    3. 空白模板 (自定义)
    4. 基于现有 ADR 生成
    用户确认后, .rddf/roadmap.md 创建成功 → Phase 1 setup
```

**b. Phase 5 planner validation 强化为双门控**:

```
门控 1: .rddf/roadmap.md 存在 (新增)
门控 2: .planner-state.json::state_revision 已 bump (新增 recommended_route 已写入)
```

**c. `recommended_route` 字段从 optional → required**:

- `_lib/schemas/planner_state_schema.json` properties 把 `recommended_route` enum 从 optional 提升为 required
- `_lib/planner_state.py::_default_state()` 默认值 `"unknown"`
- `_lib/planner_sync.py::apply_state` 按启发式计算:
  - `simple`: priority=P3 AND file_count ≤ 2 AND 无公共 API 改动关键词
  - `complex`: priority ∈ {P0, P1} OR 触碰 `_lib/core/` / `_lib/schemas/` OR breaking-change 关键词
  - `unknown`: 其他情况
- `rddf planner status` 输出加 `Recommended route: simple|complex|unknown`

**d. `.planner-handoff.json` 包含 `recommended_route`** (新增字段):

```json
{
  "schema": "planner-handoff-v1",
  ...
  "proposals_ready": [...],
  "awaiting_builder": [...],
  "recommended_route": "simple|complex|unknown"  // NEW
}
```

### 决策 3: rdd-builder P0 触发 rdd-quick (修订 ADR-0047 D1)

**a. P0 prompt 从 4-option 升为 5-option**:

```
══════════════════════════════════════════════
rdd-builder Phase 0: Approval Gate (HARD pause)
══════════════════════════════════════════════

检测到 proposal: <change-name>
Planner advisory: recommended_route = simple|complex|unknown

决策依据:
  - recommended_route = simple AND AC 数量 ≤ 2 AND files ≤ 2 AND 无 public interface 改动
    → 💡 推荐选项 5 (dispatch-to-quick)
  - 其他情况
    → 选项 1-4 (approve/reject/defer/revise)

请选择:
  1. ✅ approve       → 继续 Phase 1 plan gen
  2. ❌ reject        → rddf feedback add --kind rejected, exit 0 (no archive)
  3. ⏸ defer         → rddf feedback add --kind blocked, exit 0 (no archive)
  4. 🔄 revise        → rddf feedback add --kind needs-revision, exit 1
  5. ⚡ dispatch-quick → 转 rdd-quick (per ADR-0047 + ADR-0048)
                       → 仅当 recommended_route=simple 时启用
```

**b. 选项 5 触发逻辑**:

```bash
# phase0_approval.sh case 5:
5)
  # 写 .rddf/state/builder/<change>.json::approval_status="dispatched_to_quick"
  # 创建 .rddf/state/rdd-quick-context.json (传递 proposal.md 内容)
  # 关闭 stage_builder session
  # 委托 skill_use("rdd-quick") with --from-builder flag
  # rdd-quick 完成后: 直接 openspec archive (跳过 Phase 1-3)
  #                  或回 P0 重新决策 (用户选择)
```

**c. rdd-quick 升级契约修订** (SKILL.md L200):

```diff
- Recommendation: re-frame as an openspec change by running skill_use("rdd-planner").
+ Recommendation: re-frame by running skill_use("rdd-builder") — 回到 P0 重新决策
+                 (不再回到 rdd-planner,避免循环; rdd-builder P0 选项 1-5 重新选择)
```

**d. rdd-quick P1 complexity triage 简化** (因 planner 已提供 advisory):

- 读取 `.planner-handoff.json::recommended_route` 作为主信号
- 简单分支: `recommended_route=simple` → 仅向用户确认 (不再做完整 5 维度信号判定)
- 复杂分支: `recommended_route=complex` → 必须 spawn Metis + Oracle + 用户确认 (per ADR-0047)
- unknown 分支: 保留原 5 维度信号判定 (fallback)

**e. ADR-0047 D1 立场修订**:

```diff
- ### D1 — 归属: 独立 skill `rdd-quick`
- **新建独立 skill**, 不挂在 `rdd-planner` 之下. ... rdd-quick self-triages regardless.
+ ### D1 — 归属: 独立 skill `rdd-quick` (AMENDED per ADR-0048, 2026-09-09)
+ **rdd-quick 是独立 skill, 不挂在 `rdd-planner` 之下** (原有立场保留).
+ **rdd-quick 入口分两种** (NEW):
+   - **从 rdd-builder P0 触发** (主路径, 选项 5): planner-handoff::recommended_route 提供结构化 advisory
+   - **从 guide 推荐器直接调用** (旁路, 紧急): self-triage per 原 D1
+ **不再用 "self-triages regardless"**: P1 读取 planner-handoff 作为主信号, 仅在 unknown 时 fallback 到 self-triage
```

## Consequences

### 正面

- ✅ 修复审计 finding C-1 (rdd-arch/SKILL.md 错位): 一次性解决所有 roadmap 相关错位
- ✅ rdd-arch 简化: 高介入阶段只剩 ADR + 架构差距分析 (从 6 phase → 5 phase)
- ✅ rdd-planner 完全接管 roadmap: 角色边界清晰 (per ADR-0028)
- ✅ `recommended_route` 从死字段变 required: rdd-builder P0 是明确 consumer, 形成完整数据流
- ✅ rdd-quick 决策点升级: 从 self-triage (无结构化信号) 改为 builder P0 触发 (有结构化信号)
- ✅ 升级路径避免循环: quick 升级不再回 planner, 直接回 builder P0

### 负面 / 风险

- ⚠️ 反转 ADR-0047 D1 立场需 user override (per ADR-0044 模式): 已记录在 ADR-0048 + ADR-0047 amendment 块
- ⚠️ rdd-builder P0 5-option 增加决策复杂度: 推荐提示 (💡) 前置展示缓解
- ⚠️ rdd-planner `recommended_route` 启发式可能误判: 仅为 advisory, rdd-builder P0 保留用户最终决策权 (HARD pause)
- ⚠️ 旧调用方按 ADR-0047 找 `skill_use("rdd-planner")` 升级 quick 失效: SKILL.md + guide 推荐菜单同步更新
- ⚠️ 零污染契约 (4 个 sha256 hash) 需更新 `test_rdd_quick_isolation.bats`: 同步修改 4 个脚本

### 兼容性

- ✅ 旧 rdd-arch Phase 4 用户: 由 rdd-planner Phase 0 roadmap-bootstrap 接管, 引导迁移
- ✅ 旧 rdd-builder P0 4-option 用户: 5-option 是 superset, 1-4 行为完全不变
- ✅ 旧 rdd-quick 直接调用用户: 仍可从 guide 进入 (self-triage 降级路径)
- ⚠️ 升级契约变更 (quick → builder 而非 planner): 破坏脚本级依赖, 需脚本同步

## Implementation

### 文档改动 (~6 个文件)

1. `docs/adr/ADR-0048-v4-stage-merge-revision.md` (本文档, NEW)
2. `docs/adr/ADR-0047-rdd-quick-bypass-path.md` 加 AMENDMENT 块 (D1 修订)
3. `docs/adr/ADR-0038-rdd-planner-crosscutting.md` 加 AMENDMENT 块 (planner 完全独占 roadmap)
4. `docs/adr/ADR-0042-rdd-arch-rdd-planner-bidirectional-feedback.md` 加 note (planner advisory 升级)
5. `.rddf/improvements/fix-v4-rdd-planner-scope-over-assignment.md` AC-13 required (升级)
6. `docs/adr/README.md` 加 ADR-0048 行 + 演进图追加 v4.0.1

### SKILL.md 改动 (4 个 skill)

1. `skills/rdd-arch/SKILL.md`:
   - 删除 Phase 4 (L520-658, ~138 行)
   - Phase 5 改单门控 (移除 roadmap 检查)
   - role.boundaries.owns 删除 3 个 roadmap 项
   - 删除 Phase X Roadmap Sync (L721-746)
   - 修改 role.boundaries 描述
2. `skills/rdd-planner/SKILL.md`:
   - 新增 Phase 0: roadmap-bootstrap
   - Phase 5 planner validation 强化为双门控
   - entry/exit contract 更新 (写 recommended_route 到 handoff)
3. `skills/rdd-builder/SKILL.md`:
   - P0 prompt 改为 5-option + 推荐提示
   - 加 dispatch-quick 分支说明
   - 说明 rdd-quick-context.json 临时文件
4. `skills/rdd-quick/SKILL.md`:
   - L200 升级契约修订
   - P1 complexity triage 读 planner-handoff 作为主信号
   - 加 from-builder 入口说明

### 代码改动 (~10 个文件)

1. `_lib/schemas/planner_state_schema.json`: recommended_route required
2. `_lib/planner_state.py::_default_state()`: 默认 `recommended_route: "unknown"`
3. `_lib/planner_sync.py::apply_state`: 计算 recommended_route 启发式
4. `_lib/planner_sync.py::render_state`: 包含 recommended_route
5. `_lib/planner_handoff.py::write_planner_handoff`: 加 recommended_route 参数
6. `_lib/builder_deps.py::decide_execution_mode`: 读 planner-handoff::recommended_route
7. `_lib/cli/planner_cmd.py`: status 输出加 Recommended route 行
8. `_lib/cli/builder_cmd.py`: phase0 选项加 5 (dispatch-quick)
9. `_lib/builder_handoff.py`: approval_status 加 `dispatched_to_quick` 枚举值
10. `_lib/quick_history.py`: outcome 加 `dispatched_from_builder` 区分

### 脚本改动 (~5 个文件)

1. `skills/rdd-arch/scripts/arch_done_gate.sh`: 移除 roadmap 检查
2. `skills/rdd-builder/scripts/phase0_approval.sh`: 加 case 5 分支 + rdd-quick-context.json 写入
3. `skills/rdd-quick/scripts/scaffold_plan.sh`: 加 `--from-builder` flag
4. `skills/rdd-quick/scripts/append_history.py`: 加 outcome 枚举值
5. 删除: `skills/rdd-arch/scripts/roadmap_incremental_update.sh` (从 arch-done 调用方移除)

### 测试改动 (~7 个文件)

1. `tests/integration/test_rdd_arch_no_roadmap.bats` (NEW): arch 不引用 roadmap 锁定
3. `tests/integration/test_rdd_planner_roadmap_bootstrap.bats` (NEW): planner Phase 0 引导测试
4. `tests/integration/test_rdd_planner_recommended_route.bats` (NEW): planner advisory 输出测试
5. `tests/integration/test_rdd_builder_dispatch_quick.bats` (NEW): P0 5-option + dispatch-quick 测试
6. `tests/integration/test_rdd_quick.bats` (UPDATE): 升级契约变更 (planner → builder)
7. `tests/integration/test_rdd_quick_isolation.bats` (UPDATE): 4 个 sha256 hash 锁定更新
8. `tests/unit/test_recommended_route.py` (NEW): planner advisor 启发式单元测试

### 总工作量估算: 3-5 天 (1 工程师)

- 文档修订: 0.5 天
- SKILL.md 改动: 0.5 天
- 代码改动: 1-2 天
- 测试编写: 1 天
- 全量回归 + 修复: 0.5-1 天

## References

- **ADR-0037**: Feedback Contract for `.rddf/improvements/*.md`
- **ADR-0038**: rdd-planner Horizontal Orchestrator (Stage 2, AMENDED by ADR-0048)
- **ADR-0042**: rdd-arch ↔ rdd-planner 双向反馈闭环
- **ADR-0043**: rdd-workflow v4 stage-merge architecture (REVISED by ADR-0048)
- **ADR-0044**: v4 Stage Merge Wave 3 — Hard Removal of guide-* Skills
- **ADR-0047**: rdd-quick bypass path (AMENDED by ADR-0048 D1)
- **ADR-0045**: inline-ac-verifier-into-rdd-verifier
- **`.rddf/improvements/fix-v4-rdd-planner-scope-over-assignment.md`**: AC-13 required 升级
- **2026-09-09 rdd-planner alignment audit** (Oracle `ses_f7a9e01dbffe2Lqu8jYjg4YvL2`)
- **2026-09-09 user design intent** (3 项改动批准, 本 ADR 采纳)
- **实施 plan**: `.rddf/plans/adr-0048-v4-stage-merge-revision.md` (待写)

## 实施步骤建议

1. **P0**: 写 `.rddf/plans/adr-0048-v4-stage-merge-revision.md` (TDD 5 步 plan)
2. **P1**: 先改 ADR 文档 (本文 + ADR-0047 amendment + fix-v4-rdd-planner-scope-over-assignment AC-13)
3. **P2**: 改 SKILL.md (rdd-arch → rdd-planner → rdd-builder → rdd-quick)
4. **P3**: 改 _lib 代码 (按依赖顺序: schema → state → sync → handoff → builder_deps → cli)
5. **P4**: 改脚本 (rdd-arch → rdd-builder → rdd-quick)
6. **P5**: 写测试 + 跑全量回归
7. **P6**: archive via `rdd-builder` P3 + 跑 `./test.sh --full --regression`