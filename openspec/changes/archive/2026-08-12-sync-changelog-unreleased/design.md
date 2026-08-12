## Context

`CHANGELOG.md` `[Unreleased]` 段当前记录到 `afc369a` (test(reporter): add e2e integration + docs for ADR-0027 change-c)。在 `afc369a` 之后已经有 20+ commits 涉及 3 个主要 feature 工作：

1. **rddf orchestrate (Python orchestrator for phase subprocess detection)** — 11 commits
2. **env-check gh_available field (ADR-0027 reporter prereq)** — 1 commit
3. **archive close hook: lightweight mode** — 1 commit

当前 drift 状态：
- `CHANGELOG.md [Unreleased]` 段最后 commit = `afc369a`
- 后续 `git log --oneline --since="afc369a"` 返回 ≥ 20 commits
- 0 个 commits 在 CHANGELOG 中记录

这违反 `docs/change-quality-guide.md` 中"所有 unreleased 工作必须记录在 `[Unreleased]`" 原则。

## Goals / Non-Goals

**Goals:**
- 同步 `CHANGELOG.md [Unreleased]` 段，记录 20+ 提交的工作
- 按 3 个主题分组（orchestrator / env-check / archive），便于 release note 生成
- 同步 `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` 已记录的 `db355a0` cross-reference
- 添加 ADR-0027 dogfooding 关联说明

**Non-Goals:**
- 不重写 CHANGELOG 历史段（已正确）
- 不重构 CHANGELOG 结构（保持当前格式）
- 不追写 git-blame 早期 commits（仅 `[Unreleased]` 段）
- 不修改 `roadmap.md` / `docs/architecture/*` 历史记录（已正确）

## Decisions

**Decision 1: 按主题分组而非按 commit 顺序**
- 理由：release note 通常按主题分组（orchestrator / env-check / archive），便于用户阅读
- 替代方案：按 commit 顺序 — 决定为不采用，因为 commit 顺序会跨越多个主题，读者难以追踪

**Decision 2: 引用 commit hash 而非 description**
- 理由：可追溯到具体 commit，便于审阅
- 替代方案：仅描述 — 决定为不采用，因为失去 git blame 追溯能力

**Decision 3: ADR-0027 dogfooding 关联放在 CHANGELOG 注释而非 ADR**
- 理由：CHANGELOG 是 release note，是用户首先看的文档
- 替代方案：仅修改 ADR — 决定为不采用，因为 CHANGELOG 是 drift 的源头

## Risks / Trade-offs

- **Risk**: 误写 commit 描述 → **Mitigation**: 每个 commit 用 `git show <hash> --stat` 验证
- **Risk**: 漏写 commit → **Mitigation**: `git log --oneline afc369a..HEAD` 必须 0 行输出
- **Risk**: CHANGELOG 格式漂移 → **Mitigation**: 保持与 ADR-0027 段相同的 `### Feature Name` 标题格式
- **Trade-off**: 不写 commit granularity（如每个 feature 子节）会丢失细节 → **Mitigation**: 在每个主题子节内列出所有 commit hash
