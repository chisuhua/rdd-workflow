## Context

当前 `proposal-suggestions.md` 是单一 JSON 文件，内嵌所有提案的完整内容。需拆分为独立文件 + 双索引架构。

## Goals / Non-Goals

**Goals:**
- 每个提案独立为 `improvements/<name>.md`，自包含 5-section 内容
- `proposal-suggestions.md` 降级为 Markdown 表格索引（arch 阶段输入）
- `proposal-approved.md` 为 Markdown 表格索引（plan 阶段输入）
- guide-arch 新增审批能力
- guide-plan 切换数据源

**Non-Goals:**
- 不修改提案文件自身的格式（保留 5-section Markdown）
- 不引入 Tribunal 多 agent 审查（ADR-0015 约束）
- 不修改 ADR

## Decisions

### 决策 1：独立文件而非 JSON 内嵌

**选择**：每个提案独立为 `improvements/<name>.md`

**理由**：
- 原生 Markdown 可读性远优于 JSON 转义
- git diff 干净——每提案一个文件，commit 粒度匹配
- 审批后只需加一行链接，零内容复制
- 文件系统天然支持过滤（ls/glob）

**替代方案**：保持 JSON 但拆分为 suggestions.json + approved.json → 仍有 JSON 可读性问题

### 决策 2：状态由索引文件决定，不嵌入提案文件

**选择**：提案文件本身不含 `status` 字段，状态完全由所在索引文件决定

**理由**：
- 提案在 suggestions.md 中 = 待讨论
- 提案在 approved.md 中 = 已批准
- 消除 status 字段的状态机复杂度
- "在哪个文件就是什么状态"——直觉明确

### 决策 3：proposal-suggestions.md 充当完整的原提案索引

**选择**：即使提案已被批准，仍在 suggestions.md 中保留一行 (标记为"已审批 → approved.md")

**理由**：保持 suggestions.md 作为"提案全生命周期"的记录，方便追溯

## Data Flow

```
外部输入 (扫描/手写)
    │
    ▼
improvements/xxx.md  ← 提案文件（自包含，无状态字段）
    │
    ├──→ proposal-suggestions.md  ← 索引：链接 + 优先级 + 状态（待讨论/已审批/已拒绝）
    │
    └──→ proposal-approved.md     ← 索引：链接 + 优先级 + 批准时间/人
              │
              ▼
         guide-plan propose → 创建 openspec change
              │
              ▼
         archive.sh → 更新 approved.md 条目状态为"已完成"
```

## File Layout

```
improvements/                          ← 新目录 (git tracked)
├── proposal-approval-pipeline.md
├── fix-silent-exception.md
├── ...                               ← 共 27+ 个提议

proposal-suggestions.md               ← 降级为 Markdown 表（~50行）
proposal-approved.md                  ← 新 Markdown 表（~20行）

skills/
├── _lib/
│   ├── state.sh                     ← 新增 list_improvements() / list_approved()
│   ├── state_reader.py               ← 新增 read_improvement_entries()
│   ├── archive.sh                    ← L312 改 approved.md
│   ├── archive_helper.py             ← 〃
│   ├── gate.py                       ← 〃
│   ├── deashboard/                   ← 双索引展示
│   └── workflow_synthesizer.py       ← 双索引状态合成
├── propose/
│   ├── SKILL.md                       ← 〃 改 approved.md
│   └── scripts/propose_change.py      ← ├──改 approved.md
├── guide/
│   └── scripts/scan-state.sh        ← 双索引扫描
├── guide-arch/
│   └── SKILL.md                       ← 〃 新增 Phase 5.5
└── guide-plan/
    └── SKILL.md                       ← 〃 改 approved.md
```