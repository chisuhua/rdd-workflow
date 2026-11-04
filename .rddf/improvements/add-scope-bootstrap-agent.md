---
优先级: P2
来源: ChipForge 2026-10-18/19 governance window 实战 + 用户观察 4 个 scope 切换场景 (governance → ip/cache → tests/soc → tests/cpu) agent 缺乏显式 work-focus 状态, 跨 session drift 风险 + 用户 2026-10-19 显式请求"其他项目如何更新 AGENTS.md 配置 scope 内容, 是否提供一个命令, 用 LLM 分析项目同时和用户讨论如何划分 scope"
阶段: v2.3
分类: arch-design
类型: feature
特性: __ungrouped__
---
**优先级**: P2 | **来源**: ChipForge 2026-10-18/19 governance window 实战 + 用户观察 4 个 scope 切换场景 (governance → ip/cache → tests/soc → tests/cpu) agent 缺乏显式 work-focus 状态, 跨 session drift 风险 + 用户 2026-10-19 显式请求"其他项目如何更新 AGENTS.md 配置 scope 内容, 是否提供一个命令, 用 LLM 分析项目同时和用户讨论如何划分 scope"
**阶段**: v2.3 | **分类**: arch-design
**类型**: feature
**特性**: __ungrouped__

> **范围定位**: 本提案是 rdd-workflow **首个 scope-bootstrap 能力提案**, 跟现有 `~/.config/opencode/AGENTS.md` §Build Agent 角色矩阵 (per-user 全局) 正交独立, 是 **per-project 局部**的 work-focus 矩阵 bootstrap 机制.
>
> 本提案**不**实现 skill (如 `skill_use("rdd-scope-bootstrap")`), 仅落 5 段 improvement 提案. skill 实施由 rdd-planner / rdd-builder 流程后续 follow-up.

## Why

> 原标题"架构依据"按 rdd-workflow add-archive-post-commit 模式; 与 ChipForge 5 段格式 "Why" 兼容 (rdd-workflow add-auto-rfc 也用 "Why"). 本提案同时为 rdd-workflow 用户和 ChipForge 用户友好.

### 症状 1 (ChipForge 2026-10-18, 4 个 scope 切换无显式状态)

- 1 session 内 4 个 scope 切换: governance (起始) → ip/cache (cache-tlm 改名) → tests/soc (拆 SoC 子目录) → tests/cpu (改 cpu/configs → schema) → governance (scope-matrix 起草)
- 每次切换无显式 prompt context 信号, agent 仅靠 LLM 自觉继续"上次状态"
- 长 session 容易 cognitive drift (用户观察到的痛点)
- ChipForge 解决方案: scope-matrix-proposal (2026-10-19) + scope-state-show-and-read-hint (2026-10-19) 两个 change 已落 AGENTS.md §Build Agent Work Scope Matrix (POC) + `.rddf/state/scope.json` schema v1

### 症状 2 (新项目没有 scope matrix 模板, 用户必须 1-from-scratch)

- 用户 2026-10-19 直接问: "如果其他项目如何更新 AGENTS.md 配置 scope 内容? 是不是提供一个命令, 用 LLM 分析项目同时和用户讨论如何划分 scope?"
- 答案现状 (无 scope-bootstrap): 用户在新项目 root, 不知道 AGENTS.md 要不要 §Build Agent Work Scope Matrix, 不知道 5 categories 怎么定义, 不知道物理目录 → scope 映射怎么填, 不知道 `.rddf/state/scope.json` schema v1 是什么
- 即使知道, 也无法靠 LLM 一次性自助生成, 因为 LLM 没有"扫项目 → 提议 scope 列表 → 与用户对话"的可复制流程

### ChipForge 已落地的"scope matrix exemplar" (parent reference)

| 资源 | 位置 | 内容 |
|------|------|------|
| AGENTS.md §Build Agent Work Scope Matrix (POC) | ChipForge AGENTS.md L394-707 | 156 行, 13 sections (§0.5 + §1-9 + §10-13), 含 5 categories × 15 targets + 物理目录映射表 + Mermaid + scope.json schema + slash command docs |
| `.rddf/state/scope.json` schema v1 | ChipForge .rddf/state/scope.json | `schema_version=scope-v1`, `current_scope={category, target, sub_target}`, `history[]` array |
| openspec spec | openspec/specs/scope-matrix-proposal/spec.md | 11 Requirement, D3 spec-delta |
| improvement draft | .rddf/improvements/scope-matrix-proposal.md | 5-段 (Why / What / Acceptance / Capabilities / Impact) |

### 与现有 rdd-workflow capability 对齐

| 维度 | 现有 rdd-workflow | ChipForge 落地 | 本提案 |
|------|------|------|------|
| 工作流模板 | rdd-arch / rdd-planner / rdd-builder / rdd-verifier / rdd-quick | 已沿用 (本次 4 governance change 全走 rdd-builder P0-P3) | scope-bootstrap 提议走同一 rdd-workflow path (rdd-planner 起草 → rdd-builder 实施 → rdd-verifier 验收) |
| Improvement 5 段 | 现有 (per 多个 example 提案) | 已沿用 (scope-matrix-proposal + scope-state-show-and-read-hint 走同 5 段) | scope-bootstrap 走同 5 段, 跟 rdd-workflow 兼容 |
| State 文件 | `.rddf/state/{role,session,events,iteration}.json` | `.rddf/state/scope.json` (force-add 突破 `.gitignore:57 state/`) | scope-bootstrap 引导新建 `scope.json`, 沿用 force-add pattern |
| Slash command | `/role-show` (user→LLM 口语, opencode runtime 不解析) | `/scope-show` `/scope-history` `/scope-reset` (同 user→LLM 口语) | scope-bootstrap 提议增 `/scope-bootstrap` (同 user→LLM 口语) |
| Gitignore 处理 | `.rddf/state/` gitignored by default | force-add 突破 | scope-bootstrap 引导用户也 force-add scope.json |
| 跨 session 行为 | session-bootstrap 默认 `general` + `governance/governance` | 同 | scope-bootstrap 引导用户默认填 `governance/governance` |
| review / approval | 5-option approval gate (per ADR-0048) | 已沿用 (case 1 approve) | scope-bootstrap 走 rdd-planner + rdd-builder 完整 review chain |

### 方案评估 (3 候选 + 推荐)

| 方案 | 实现成本 | 落地速度 | 通用性 | 推荐度 |
|------|---------|---------|--------|--------|
| **A. rdd-workflow skill 实施** (skill `scope-bootstrap-agent`) | 中 (1-2 周) | 慢 | 高 (任何 LLM 可用, 复用 rdd-workflow 流程) | ⭐⭐⭐ **终局正解** |
| B. 单文件 `tools/scope-bootstrap.sh` shell 工具 | 中低 (2-3 天) | 中 | 中 (依赖 LLM API key) | ⭐⭐ 短期备选 |
| C. opencode framework extension (新 agent) | 高 (数周) | 极慢 | 最高 (LLM 无关) | ⭐ 远期 + 需 opencode PR |
| **D. 纯 docs 提案 (本提案)** | **极低 (1-2 小时)** | **快 (今天)** | 高 (任何 LLM 可用) | ⭐⭐⭐ **本提案落 D, 后续可升 A** |

> **本提案的边界**: 仅落方案 D (1 份 improvement 提案文件), **不**实施 skill. 后续如果有需求, 可起 rdd-planner 阶段做方案 A (skill 实施).

### 3 候选命令的 LLM 入口设计 (本提案 §3 落地)

| 入口 | user 触发 | LLM 动作 | 输出 |
|------|----|------|------|
| 1. Slash command (user 优先) | `/scope-bootstrap <path> "project-desc"` | LLM 读 prompt template → 扫项目 → 输出 5 categories × N targets 草稿 | 多轮对话, 每段 y/n |
| 2. Improvement proposal 入口 (medium-term) | 用户提 openspec change "scope-bootstrap" + 提供项目 root + 描述 | 走 rdd-builder P0-P3, 落 AGENTS.md + .rddf/state/scope.json | 同 ChipForge 4 governance change 模式 |
| 3. 复用现有 rdd-workflow improvement proposal format (本提案) | 用户 (或 LLM agent) 在新项目 root 写 `.rddf/improvements/scope-bootstrap-initial.md` 5 段 | LLM 按 rdd-workflow 5 段指南生成该 proposal | proposal + AGENTS.md + scope.json 三件套 |

> 本提案**主要推荐入口 3** (proposal 模式, 跟 rdd-workflow 兼容), **可选 入口 1** (slash command, 短期加速).

## What Changes

> 原标题"范围"按 rdd-workflow add-archive-post-commit 模式; 与 ChipForge 5 段 "What Changes" 兼容. 本提案同时为 rdd-workflow 用户和 ChipForge 用户友好.

### In Scope

**A. improvement 提案文件 (本提案本体)**:
- 新建 `.rddf/improvements/add-scope-bootstrap-agent.md` (per rdd-workflow 5 段格式, 含 YAML frontmatter + 6 sections)
- 包含 prompt template (user→LLM 复制用)
- 包含 fallback reference (ChipForge §Build Agent Work Scope Matrix as exemplar)
- 包含 mock example (假设新项目 X, 输出长这样)

**B. 落 improvement-suggestions.md 索引行**:
- append 一行: `| [add-scope-bootstrap-agent](.rddf/improvements/add-scope-bootstrap-agent.md) | P2 | 2026-10-19 ChipForge 治理实战 | 2026-10-19 | 待审查 |`

**C. 文档化在 `USAGE.md` / `HANDOFF.md`** (轻量):
- `USAGE.md` 新增 1 段 "Scope Bootstrap for New Projects" 引用本 proposal
- `HANDOFF.md` 新增 1 行 "scope bootstrap: 见 add-scope-bootstrap-agent proposal (P2, 2026-10-19)"

**D. 跨项目使用案例 (docs/example/)** (轻量):
- 新建 `docs/example/scope-bootstrap-mock-output.md`: 模拟新项目 (e.g. "riscv-simulator") 跑 scope-bootstrap 后的预期 AGENTS.md §scope matrix 段落 (mock 而非真实 output, 100-200 行)

### Out of Scope

- **不实施 skill `rdd-scope-bootstrap-agent`** (留 future work, 走 rdd-planner 流程)
- **不动 `~/.config/opencode/AGENTS.md`** (用户全局, parallel 独立)
- **不动现有 rdd-workflow skills 目录** (rdd-arch / rdd-planner / rdd-builder / rdd-verifier / rdd-quick)
- **不动 ChipForge 仓库** (本提案落在 rdd-workflow 项目内, 跨项目独立)
- **不动 `~/.rddf/state/scope.json`** (用户全局, 不属于 rdd-workflow 项目级)
- **不动 `.rddf/state/{role,builder-handoff}.json`** (rdd-workflow 已有 state, 不混入新概念)

## Acceptance

### 必达 (Hard)

- [ ] `.rddf/improvements/add-scope-bootstrap-agent.md` 文件已存在
- [ ] YAML frontmatter 含 优先级/来源/阶段/分类/类型/特性 6 字段
- [ ] 6 sections (Why / What / Acceptance / Capabilities / Impact) 全写
- [ ] prompt template 段 (含 8 步 user→LLM 复制脚本) 完整
- [ ] mock example 段 (假设新项目 X, 含 5 categories 草稿 + AGENTS.md 段落预览) 完整
- [ ] `improvement-suggestions.md` 含 1 行新条目, 链接 proposal + 来源 + 时间

### 应达 (Soft)

- [ ] `USAGE.md` 新增 1 段 "Scope Bootstrap for New Projects" 引用本 proposal
- [ ] `HANDOFF.md` 新增 1 行 "scope bootstrap: ..." 引用
- [ ] `docs/example/scope-bootstrap-mock-output.md` mock output 完整 (含 5 categories × 8-10 targets + 物理目录映射 + Mermaid + scope.json state)
- [ ] proposal 段含与 `add-archive-post-commit-hook-and-force-flag.md` 同等质量的对照表 + 范围定位

### 治理 (Meta)

- [ ] proposal 通过 `rddf validate` 0 fail
- [ ] proposal 通过 `rddf status` 检查 status 状态 OK
- [ ] proposal 状态从 `draft` 转 `proposed` (待 rdd-arch / rdd-planner 审查)

## Capabilities

新增能力 (cross-cutting):

### MUST

- 新项目 (e.g. "riscv-simulator", "neural-net-compiler") root 路径下, 用户可手起 1 份 `.rddf/improvements/scope-bootstrap-initial.md` 5 段 proposal
- LLM 收到 proposal 后, 引导 user 走 8 步 (per §3 入口 3) 生成 AGENTS.md §scope matrix 段落 + .rddf/state/scope.json
- 输出与 ChipForge 已落地 scope matrix 兼容 (5 categories × N targets, 物理目录映射表, Mermaid, scope.json schema v1)
- 新项目 scope matrix 一旦生成, 后续 rdd-builder P0-P3 流程可正常消费 (与 ChipForge 流程兼容)

### MUST NOT

- 不动 rdd-workflow 现有 skills 目录
- 不实施 scope-bootstrap skill (仅落 proposal, 实施 future work)
- 不与现有 `~/.config/opencode/AGENTS.md` Role Matrix 冲突 (本提案正交独立)
- 不限制新项目用不同 categories / targets (灵活, 5 categories 是 ChipForge pattern, 不是硬约束)

详见本提案 §E (Capabilities 展开).

## Impact

### 受影响文件

| 文件 | 动作 | 大小 |
|------|------|------|
| `.rddf/improvements/add-scope-bootstrap-agent.md` | 新建 | ~6000 字 (含 prompt template + mock example) |
| `improvement-suggestions.md` | append 1 行 | 1 行 |
| `USAGE.md` | append 1 段 | ~300 字 |
| `HANDOFF.md` | append 1 行 | 1 行 |
| `docs/example/scope-bootstrap-mock-output.md` | 新建 (optional) | ~2000 字 |

总计: 0 业务代码改动, docs-only change (~8000 字 if 全 optional 落地).

### 风险

- **R-COMPLEXITY-1** (跨项目 5 categories 命名不一致) → 缓解: 提案强调"5 categories 是 ChipForge pattern, 不是硬约束", 新项目可自定义 categories (e.g. "core/runtime" "core/lib" "test" "ci" "docs")
- **R-LLM-QUALITY-1** (LLM 扫描项目质量因模型而异) → 缓解: 提案 prompt template 含"8 步强制顺序" + "每段 y/n 接受" checkpoint, 避免 LLM 一次塞 200 行用户拒收
- **R-DOC-ROT-1** (ChipForge 同步漂移) → 缓解: proposal 引用 ChipForge 路径用相对引用, 不绑死行号
- **R-AGENT-SCOPE-1** (新项目用 non-build agent 误用) → 缓解: 提案明确"本提案仅 build agent / planner / arch 触发, 其他 agent 不必支持"
- **R-OPENCODE-1** (opencode runtime 不解析真 slash command) → 缓解: 同 scope-state-show-and-read-hint, 注明 "user→LLM 口语口令"
- **回退**: git revert 单 commit 即可 (proposal 文件 + 1-2 行 doc update)

### 下游依赖

- **上游**: rdd-workflow 现有 5 段 improvement proposal format (已存在)
- **下游**:
  - 未来 rdd-planner 阶段可基于本 proposal 设计 `skill_use("rdd-scope-bootstrap")` skill (方案 A 升级)
  - 未来 rdd-builder 阶段可基于本 proposal 设计 `rddf scope-bootstrap <path>` CLI 命令 (B 方案升级)
  - ChipForge 后续 governance 改动可继续沿用本 proposal 描述的 scope matrix 模式

### 不解决

- 实施 scope-bootstrap skill (留 future work)
- 实施 scope-bootstrap shell CLI 工具 (留 future work)
- 给 opencode framework 提新 agent PR (留 future work, 跨项目)
- 跟 `~/.config/opencode/AGENTS.md` Role Matrix 做形式化集成 (留 future work)
