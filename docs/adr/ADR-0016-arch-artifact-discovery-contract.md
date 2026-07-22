# ADR-0016: Arch 阶段工件发现契约 (Arch Artifact Discovery Contract)

> **v3.0.0 note**: Originally authored as "spec-workflow". Renamed to "rdd-workflow" in v3.0.0 (2026-07-22). See ADR-0023.


> **状态**: 已采纳
> **日期**: 2026-07-08
> **决策者**: sisyphus
> **依据**: ADR-0003 §2.1 (三阶段架构), ADR-0011 (阶段步骤化执行模型), ADR-0007 §3 (门控机制)

## Context

rdd-workflow v2.0 三阶段架构（ADR-0003）将工作流切分为 `arch → plan → ship`，由 handoff 文件 (`.rddf/state/.arch-handoff.json`、`.rddf/state/.plan-handoff.json`) 串联。经过对现有 8 个 `.md` skill 文件 + 2 个 `.py` 库的完整探索（2026-07-08 审计），发现三类**路径硬编码问题**：

### 问题 1: arch 阶段产物路径在多端重复硬编码

`docs/adr/`、`docs/architecture/`、`roadmap.md` 这三个 arch 阶段交付物的路径在以下位置**字面重复**出现：

| 文件 | 行号 | 硬编码内容 |
|------|------|-----------|
| `skills/guide-arch.md` | 145, 147, 210, 271, 290, 341, 414, 505, 671 | ADR 目录、architecture 目录、roadmap 文件路径 |
| `skills/guide-plan.md` | 119, 120 | handoff + roadmap 路径 |
| `skills/guide.md` (scan-state.sh) | 154 | roadmap 路径 |
| `skills/propose.md` | 188-210 | `ls docs/adr/ADR-*.md`、`ls docs/architecture/*-gap-analysis.md` |
| `skills/roadmap.md` | 197-202 | `ls docs/adr/ADR-*.md` |
| `skills/guide-ship.md` | 802 | drift analysis 写入路径 |
| `skills/_lib/gate.py` | 56-69 | `_check_adr_exists`、`_check_roadmap_defined`、`_check_arch_handoff_exists` |
| `skills/_lib/detectors.py` | 177-178 | ADR 计数 |
| `skills/_lib/actions.py` | 341-350 | `Path("docs/adr")` |

**共 14+ 处硬编码，分布在 10 个文件。**

### 问题 2: arch-handoff 已传递 `completed_adr_ids` 但下游仍硬编码扫描

`.rddf/state/.arch-handoff.json` 第 138 行已被 `guide-plan.md` 读取 `completed_adr_ids`，但 `propose.md` 第 188 行仍 `ls docs/adr/ADR-*.md` 重复扫描 — handoff 字段未被充分利用。

### 问题 3: 流程定义假设固定布局，破坏工作流

如果用户的实际项目结构是 `doc/architecture-decisions/`、`doc/roadmap.md`、`doc/arch/gaps/` 等变体：
- `guide-arch.md` 第 636 行 `ls -d "$PROJECT_ROOT/docs/adr/ADR-0"*.md` → 始终为 0
- `guide-arch.md` 第 648 行 `[ -f "$PROJECT_ROOT/roadmap.md" ]` → 始终为 no
- `arch-done` 双重门控（ADR-0007）**永远不通过** → arch → plan 切换硬阻断
- 即使用户有完整的 ADR 文档库和路线图，流程也会判定"未完成"

### 约束

- **保持向后兼容**：现有约定路径 (`docs/adr/`、`roadmap.md` 等) 必须**仍然工作**，不破坏已采纳项目
- **AGENTS.md 不能动**：人工维护、git tracked、已知有漂移（`project-organization.md` 第 53 行明确记录）。写入动态状态会与 worktree 模式 COMMIT GATE 冲突
- **handoff 模式是经过验证的契约**：ADR-0003 §2.1 显式定义了 `.arch-handoff.json`，应扩展而非替换
- **零外部 skill 依赖**：v2.0 重构已明确"零外部依赖"，不能用 oh-my-opencode 等外部工具

### 相关方

- **架构师**：希望用自己的目录结构组织 ADR（不希望被强制 `docs/adr/`）
- **集成方**：现有 OpenSpec 项目可能用 `doc/`、`documentation/` 等不同布局
- **Loop 引擎开发者**：希望在 detector 层获得结构化发现结果，而非现场 shell glob

## Decision

我们引入 **arch 工件发现契约 (Arch Artifact Discovery Contract)**，在 arch 阶段新增**轻量发现步骤**，将发现的工件路径持久化到现有 `.arch-handoff.json`，下游消费者（plan/ship/Library）优先读 handoff 路径，缺失时回退到硬编码默认。

### 三层设计

#### Layer 1: 发现步骤（arch 阶段新增）

在 `guide-arch.md` Phase 1 (setup) 中新增**步骤 5 — 工件发现**（前置步骤 1-4 保持不变）：

```
Phase 1: setup
  Step 1: 检测 openspec CLI
  Step 2: 检测 git 状态
  Step 3: 检测构建目录
  Step 4: 检测现有 ADR/roadmap/architecture 数量 (用于展示)
  Step 5 (新增): 发现 + 记录工件路径  ← 本 ADR 引入
```

发现函数 (`skills/_lib/discover_arch_artifacts.sh`)：

```bash
# 候选路径表(有序,首个命中即采用)
discover_adr_dir() {
  for candidate in docs/adr doc/adr documentation/adrs adrs docs/adr; do
    if [ -d "$PROJECT_ROOT/$candidate" ]; then
      echo "$candidate"; return 0
    fi
  done
  echo "docs/adr"  # 未发现时使用默认 + 标记 created=true
  return 1
}

discover_roadmap() {
  for candidate in roadmap.md docs/roadmap.md planning/roadmap.md ROADMAP.md; do
    if [ -f "$PROJECT_ROOT/$candidate" ]; then
      echo "$candidate"; return 0
    fi
  done
  echo "roadmap.md"
  return 1
}

discover_architecture_dir() {
  for candidate in docs/architecture docs/arch documentation/architecture; do
    if [ -d "$PROJECT_ROOT/$candidate" ]; then
      echo "$candidate"; return 0
    fi
  done
  echo "docs/architecture"
  return 1
}
```

#### Layer 2: handoff 字段扩展（核心契约）

扩展 `.rddf/state/.arch-handoff.json`，新增 5 个字段：

```json
{
  // ... 现有字段 ...
  "arch_complete_at": "...",
  "adr_count": 3,
  "completed_adr_ids": ["0001", "0002", "0003"],
  "current_phase": "phase-1",
  "plan_started_at": null,

  // ↓↓↓ 新增 ↓↓↓
  "adr_dir": "docs/adr",                       // 相对 PROJECT_ROOT 的 ADR 目录
  "roadmap_path": "roadmap.md",                // roadmap 文件相对路径
  "architecture_dir": "docs/architecture",     // 架构文档目录
  "adr_pattern": "ADR-*.md",                   // ADR 文件名 glob
  "discovered": {                              // 详细发现元数据
    "adr_dir": { "found": true, "created": false, "candidates_tried": 4 },
    "roadmap_path": { "found": true, "created": false, "candidates_tried": 4 },
    "architecture_dir": { "found": false, "created": false, "candidates_tried": 3 }
  },
  "version": 1                                 // 契约版本
}
```

**字段语义**：
- `adr_dir` / `roadmap_path` / `architecture_dir`: 相对 `PROJECT_ROOT` 的路径（保证 worktree 兼容）
- `adr_pattern`: glob 模式（支持 `ADR-*.md`、`DEC-*.md`、`RFD-*.md` 等命名变体）
- `discovered.*`: 发现过程的元数据，供诊断和回归测试
  - `found`: 路径是否实际存在于文件系统
  - `created`: discover 函数是否自动创建了路径 — **当前实现永远 `false`**（discover 是只读扫描器；文件创建留给人工程序 — adr-create / roadmap-define 阶段）
  - `candidates_tried`: 候选扫描次数（含环境变量覆盖 1 次或默认 N 次）
- `version`: 契约 schema 版本号，未来字段变更必须 bump

**fallback 策略**（三层防御）：
1. 环境变量覆盖（**真正的最高优先级**）— 即使路径不存在也走环境变量；missing 由 `discovered.found=false` + `created=false` 标记可观测：
   - `SPEC_WORKFLOW_ADR_DIR`
   - `SPEC_WORKFLOW_ROADMAP_PATH`
   - `SPEC_WORKFLOW_ARCHITECTURE_DIR`
   - `SPEC_WORKFLOW_ADR_PATTERN`
2. handoff 文件存在 → 读 handoff 字段
3. handoff 文件不存在 → 用硬编码默认值（`docs/adr/`、`roadmap.md`、`docs/architecture/`、`ADR-*.md`）

#### Layer 3: 下游消费改造（最小侵入）

改造现有 14+ 处硬编码点为 handoff 优先读取 + fallback 默认值。**不引入新文件、不替换任何模块**：

| 文件 | 改造模式 |
|------|---------|
| `skills/guide-plan.md` 第 119-149 行 | 读取 handoff 字段，fallback 到默认值 |
| `skills/guide.md` (scan-state.sh) 第 67 行 | 同上 |
| `skills/propose.md` 第 188-210 行 | ADR 扫描改用 `"$PROJECT_ROOT/$ADR_DIR/$ADR_PATTERN"` |
| `skills/roadmap.md` 第 197-202 行 | 同上 |
| `skills/guide-arch.md` Phase 1/3/4 | 自洽：自己读自己写的 handoff（如果存在） |
| `skills/_lib/gate.py` 第 56-69 行 | `_check_adr_exists` / `_check_roadmap_defined` 读 handoff |
| `skills/_lib/detectors.py` 第 177-178 行 | 读 handoff |
| `skills/_lib/actions.py` 第 341-350 行 | 读 handoff（仅 ADR 创建时需要） |

**保持现状**：
- `skills/guide-ship.md` 不读取 arch 端产物（仅写入 drift analysis），无需改造
- `skills/_lib/scan-state.sh` 已有 handoff 读取逻辑（第 67 行），仅需扩展读取的字段

### 影响范围

#### In Scope

- 新增 `skills/_lib/discover_arch_artifacts.sh` (~80 行)
- 新增 `skills/_lib/schemas/arch_handoff_schema.json` (~40 行, JSON Schema for version 1)
- 新增 `tests/unit/test_discover_arch_artifacts.sh` 或 `tests/unit/test_discover_arch_artifacts.py` (~120 行)
- 新增 `tests/integration/test_arch_discovery_handoff.bats` (~80 行)
- 修改 `skills/guide-arch.md` Phase 1 setup + Phase 5 arch-done (~50 行 diff)
- 修改 `skills/guide-plan.md` Phase 0 intake (~30 行 diff)
- 修改 `skills/propose.md` Phase 1a 扫描 (~20 行 diff)
- 修改 `skills/roadmap.md` Template 4 ADR 扫描 (~15 行 diff)
- 修改 `skills/guide.md` / `scan-state.sh` (~10 行 diff)
- 修改 `skills/_lib/gate.py` `_check_*` 函数 (~30 行 diff)
- 修改 `skills/_lib/detectors.py` ADR 检测 (~10 行 diff)
- 修改 `skills/_lib/actions.py` ADR 创建 (~10 行 diff)
- 更新 `AGENTS.md` 状态文件清单（新增 schema 描述）

#### Out Scope

- **不修改** `docs/adr/ADR-0000-template.md` 格式
- **不修改** openspec CLI 接口
- **不修改** `.openspec.yaml` / `roadmap-meta.yaml` 现有字段
- **不强制**用户迁移到新路径 — 默认约定仍为 `docs/adr/`、`roadmap.md`
- **不引入**新依赖（jq/python3 inline 已存在）
- **不修改** `iteration.json`、`deps-analysis.json` 等其他 view 文件

### 备选方案

| 备选 | 理由 |
|------|------|
| **A: 写入 AGENTS.md** | 拒绝：AGENTS.md 已 git tracked（违反 worktree COMMIT GATE），人工维护（project-organization.md 第 53 行记录了"AGENTS.md 漂移"问题），不是动态状态存储 |
| **B: 新建独立 `.rddf/state/arch-doc-paths.json`** | 拒绝：增加文件管理负担；`.arch-handoff.json` 已有 ADR 数据传递，新文件会创建第二个真相源；契约分裂 |
| **C: 完全无约定，让用户每次 prompt 传入路径** | 拒绝：破坏 arch-done 双重门控（ADR-0007）的自动化保证；每次手动输入易错 |
| **D: 用 openspec CLI 配置文件作为路径真相源** | 拒绝：openspec CLI 不管理 ADR 路径；引入跨工具耦合 |
| **E: 扩展 `.arch-handoff.json` + fallback 默认值（本 ADR）** | 接受：复用已验证契约、最小侵入、向后兼容、零新依赖 |

### 向后兼容保证

1. **默认路径不变**：handoff 缺失时所有 fallback 值为 `docs/adr/`、`roadmap.md`、`docs/architecture/`，与现有 v2.0 行为完全一致
2. **handoff 缺字段时**：消费者用 `// "default_value"` jq fallback，不报错
3. **handoff version=0**（旧格式，无 `discovered` 字段）：消费者按字段缺失处理
4. **新发现步骤**：若所有候选路径都不存在，使用默认 + 标记 `created=false`（不强制创建）
5. **CI gate**：`tests/integration/test_arch_discovery_handoff.bats` 覆盖 5 个向后兼容场景

## Consequences

### 正面

1. **支持自定义路径布局**：用户可在 `doc/`、`documentation/`、`content/` 等任意位置组织 ADR，流程仍能识别
2. **arch-done 门控可靠**：发现步骤消除路径假设，roadmap/ADR 探测准确率 100%（基于实际发现而非约定）
3. **下游契约统一**：14+ 处硬编码收敛到 1 个读取点 + fallback，降低维护成本
4. **worktree 兼容**：相对路径确保 worktree 内消费正常
5. **可观测性提升**：`discovered` 元数据支持诊断"为什么 arch-done 失败"
6. **零破坏性**：所有 fallback 值与现有约定一致，已采纳项目零迁移成本
7. **复用现有契约**：不引入新文件/新 schema 家族，符合"演进而非革命"原则

### 负面 / 风险

1. **handoff 字段膨胀**：从 6 字段增至 12 字段，复杂度上升
   - **缓解**：明确 `version` 字段，未来 schema 演进通过 version bump 隔离
2. **发现步骤依赖 glob 性能**：在 monorepo 中扫描多候选路径可能慢
   - **缓解**：候选列表 4 项硬编码，不递归扫描，单次成本 < 10ms
3. **fallback 链增加心智负担**：维护者需理解 handoff 优先 → 默认 fallback → 环境变量三层
   - **缓解**：明确写入 AGENTS.md 状态文件清单 + schema 文档
4. **arch-handoff 写入失败时下游行为**：当前 arch-handoff 失败会阻断 plan 端，发现步骤写入也是同样风险
   - **缓解**：复用现有 `mkdir -p` 容错模式；fallback 默认值保证可用性
5. **测试覆盖膨胀**：10 个文件改造需单元 + 集成测试
   - **缓解**：聚焦关键路径（handoff 读写 + fallback），不强求 100% 覆盖

### 后续待办

- [ ] 实现 `skills/_lib/discover_arch_artifacts.sh` (TDD)
- [ ] 实现 `skills/_lib/schemas/arch_handoff_schema.json` (JSON Schema for v1)
- [ ] 改造 `skills/guide-arch.md` Phase 1 setup (新增发现步骤)
- [ ] 改造 `skills/guide-arch.md` Phase 5 arch-done (写入新字段)
- [ ] 改造 `skills/guide-plan.md` Phase 0 intake (读 handoff + fallback)
- [ ] 改造 `skills/propose.md` Phase 1a 扫描 (用 handoff 路径替换硬编码)
- [ ] 改造 `skills/roadmap.md` Template 4 (用 handoff 路径替换硬编码)
- [ ] 改造 `skills/_lib/gate.py` `_check_*` 函数 (读 handoff)
- [ ] 改造 `skills/_lib/detectors.py` / `actions.py` (读 handoff)
- [ ] 编写 `tests/unit/test_discover_arch_artifacts.*` 单元测试
- [ ] 编写 `tests/integration/test_arch_discovery_handoff.bats` 集成测试
- [ ] 更新 `AGENTS.md` 状态文件清单 (新增 arch-handoff schema v1 描述)
- [ ] 同步 README.md ADR 索引表 (添加 ADR-0016)
- [ ] 验证 v1.x 兼容性 (旧 arch-handoff 无新字段时的行为)
- [ ] 撰写 CHANGELOG.md v2.1 条目

## References

- ADR-0003 §2.1 — 三阶段架构 (本 ADR 依赖的 handoff 契约定义)
- ADR-0003 §3 — 阶段间循环与切换 (`arch-done` 双重门控定义)
- ADR-0007 §3 — 门控机制 (本 ADR 扩展的 fallback 默认值对齐门控定义)
- ADR-0011 — 阶段步骤化执行模型 (本 ADR 的"步骤 5 工件发现"可作为 arch 模板的 `custom` 步骤)
- `skills/guide-arch.md` Phase 1-5 — 改造目标
- `skills/guide-plan.md` Phase 0 — 消费方改造目标
- `skills/propose.md` Phase 1a — 主要消费方
- `skills/_lib/gate.py` §`_check_adr_exists` — 门控检测改造目标
- `.rddf/state/.arch-handoff.json` — 扩展目标文件
- `docs/adr/ADR-0000-template.md` — 本 ADR 格式依据
- `docs/adr/README.md` §命名规范 / §状态生命周期 — 编号/状态合规依据