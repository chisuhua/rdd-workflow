# sync-agents-md-five-stage

**优先级**: P1 | **来源**: 2026-08-26 文档与代码一致性审计
**阶段**: default | **分类**: docs
**类型**: improvement

## 架构依据

AGENTS.md 是 rdd-workflow 项目的"项目本体 AGENTS 文档"（区别于全局 ~/.config/opencode/AGENTS.md）。它对架构的描述应当是 **single source of truth** —— README / USAGE / CHANGELOG 在用户视角解释，但 AGENTS.md 描述项目结构本身。

2026-08-26 审计发现 AGENTS.md 内部有 4 处与 v3.0 现状不一致：

| 行号 | 当前声明 | 实际 | 修复 |
|------|---------|------|------|
| line 84 | "**四阶段架构** (v2.1): `arch → design → plan → ship`" | 五阶段（含 verify） | 改为 "**五阶段架构** (v3.0+): `arch → design → plan → ship → verify`" |
| line 148 | "关键 ADR: ADR-0003 / ADR-0010 / ADR-0016 / ... / ADR-0028 / ADR-0030 / **ADR-0033**" | 漏列 ADR-0025（design 阶段）、ADR-0027（continuous evolution）、ADR-0029（issue-driven）、ADR-0031（cross-repo human-in-loop）、ADR-0032（hub deepening）、ADR-0034（rdd-verifier） | 补全到 ADR-0034 |
| line 159 | "**4 个阶段技能** (`guide-arch`, `guide-design`, `guide-plan`, `guide-ship`) 的 frontmatter 包含 `role:` 字段" | 漏 `rdd-verifier` (5 个阶段技能都有 role: 字段) | 改为 5 个 |
| line 118 | "Markdown skills (14 SKILL.md + INSTALL.md)" | 实际 25 个 SKILL.md + INSTALL.md | 改为 25 SKILL.md + INSTALL.md |

同时 USAGE.md 的 P0 修订已部分补齐，但 AGENTS.md 是给 AI agent 的"项目地图"，优先级高于 USAGE.md。

## 范围

**In Scope**:
- AGENTS.md line 84-94 阶段架构表统一为 5 阶段
- AGENTS.md line 148 关键 ADR 列表补全（从 ADR-0033 补到 ADR-0034）
- AGENTS.md line 159 "4 个阶段技能" → "5 个阶段技能"
- AGENTS.md line 118 "14 SKILL.md" → 实际数量
- 验证 `tests/integration/test_adr_index.bats` 与 `tests/unit/test_doc_contracts.py` 不回归

**Out of Scope**:
- USAGE.md 的深度重写（USAGE.md v3.1 重写为另一提案 rdd-doctor-docs-consistency 关联）
- docs/adr/README.md 的 ADR 列表自动生成（为 P2 提案 adr-index-auto-sync 范围）

## 设计

### line 84 修订

```diff
- **四阶段架构** (v2.1): `arch → design → plan → ship`
+ **五阶段架构** (v3.0+): `arch → design → plan → ship → verify`
```

### line 148 关键 ADR 列表补全

```diff
- 关键 ADR: ADR-0003 三阶段架构 / ADR-0010 多会话管理 / ADR-0016 arch 发现契约 / ADR-0017 rddf-session / ADR-0018 arch 质量门 / ADR-0019 change-arch-alignment / ADR-0022 manual_deps 字段 / ADR-0024 deps-driven execution mode / ADR-0028 role-model / ADR-0030 hub-spoke / ADR-0033 submodule-aware
+ 关键 ADR: ADR-0003 三阶段架构 / ADR-0010 多会话管理 / ADR-0016 arch 发现契约 / ADR-0017 rddf-session / ADR-0018 arch 质量门 / ADR-0019 change-arch-alignment / ADR-0022 manual_deps 字段 / ADR-0024 deps-driven execution mode / ADR-0025 design 阶段独立化 / ADR-0027 continuous evolution / ADR-0028 role-model / ADR-0029 issue-driven / ADR-0030 hub-spoke / ADR-0031 cross-repo human-in-loop / ADR-0033 submodule-aware / ADR-0034 rdd-verifier
```

### line 159 修订

```diff
- 4 个阶段技能 (`guide-arch`, `guide-design`, `guide-plan`, `guide-ship`) 的 frontmatter 包含 `role:` 字段
+ 5 个阶段技能 (`guide-arch`, `guide-design`, `guide-plan`, `guide-ship`, `rdd-verifier`) 的 frontmatter 包含 `role:` 字段（per ADR-0028 + ADR-0034 §10）
```

### line 118 修订

```diff
- skills/                        # Markdown skills (14 SKILL.md + INSTALL.md) + per-skill scripts/
+ skills/                        # Markdown skills (25 SKILL.md + INSTALL.md) + per-skill scripts/
```

## 影响

- **正向**：AGENTS.md 作为项目地图恢复与 v3.0 现状一致
- **正向**：AI agent 读 AGENTS.md 后能正确识别 5 阶段架构与所有有效 ADR
- **风险**：line 148 ADR 列表可能很快又过期（v3.1+ 新增 ADR 时）—— 但这属于 P2 提案 adr-index-auto-sync 范围
- **兼容性**：纯文档，无破坏

## 验收

- [ ] AGENTS.md line 84 含 "五阶段架构 (v3.0+)"
- [ ] AGENTS.md line 88-94 表格列出 5 行（arch/design/plan/ship/verify）已是 SSOT，无变化
- [ ] AGENTS.md line 148 包含 ADR-0025 / ADR-0027 / ADR-0029 / ADR-0031 / ADR-0034
- [ ] AGENTS.md line 159 "5 个阶段技能" 含 rdd-verifier
- [ ] AGENTS.md line 118 "25 SKILL.md + INSTALL.md"
- [ ] `tests/unit/test_doc_contracts.py` 全部 PASS
- [ ] `tests/integration/test_adr_index.bats` 不回归
- [ ] 任何后续 ADR-0035+ 仍能补到 line 148 列表（不必现在生成）