# improve-roadmap-feature-discovery

**优先级**: P2 | **来源**: 2026-08-27 Hybrid path reflection (创建 feat-fix-audit-findings 后, AGENTS.md 没有引用, 未来 agent 不知道此 feature 存在)
**阶段**: phase-1 | **分类**: governance
**类型**: improvement

**主题**: 2026-08-27 Hybrid path reflection (流程改进)

## 架构依据

2026-08-27 Hybrid path 中:
- 创建 `.rddf/roadmap/features/feat-fix-audit-findings.md` (kind: feature, phase_refs: phase-1..4)
- AUTO-INDEX 自动刷新到 `.rddf/roadmap.md` (含 1 个 features 列表条目)
- **AGENTS.md 没有引用此 feature**

后果:
- 未来 AI agent 启动 session 时,读 AGENTS.md 不知道 `feat-fix-audit-findings` 存在
- 不知道此 feature 含 9 个 improvement 提案待 design 审查
- 可能错误地创建重复的 audit 提案,失去 traceability
- 失去 feat-* → improvements/*.md 的追溯链

期望行为: AGENTS.md 自动或半自动反映当前所有活跃 feature fragments,新 agent session 能立即看到 roadmap 上下文。

## 范围

**In Scope**:

- `rddf roadmap list-features` CLI 命令实现,列出所有 `.rddf/roadmap/features/*.md` 的 summary (id, theme, phase_refs, status)
- AGENTS.md 增加自动生成段(由 roadmap tooling 维护):
  - `# Active Feature Fragments` 段,列出当前 active feature fragments
  - 每个 feature 含: 主题、phase_refs、关联 improvements 数量
- `rddf roadmap` 子命令增加 `--update-agent-md` 选项,扫描所有 feature fragments 并生成 AGENTS.md 的对应段
- 在 `guide-arch` Phase 1 加载 roadmap 时,输出 feature fragments 列表作为 context

**Out of Scope**:

- 修改 AGENTS.md 其他内容(只追加自动段)
- 反向: 从 AGENTS.md 解析 feature(单向写入)
- 强制阻断流程(只是 visibility 改进)

## 关键场景

- GIVEN `.rddf/roadmap/features/feat-fix-audit-findings.md` 存在
  WHEN `rddf roadmap list-features` 运行
  THEN 输出:
    ```
    feat-fix-audit-findings (active)
      主题: 2026-08-26 文档与代码一致性审计后续修复
      phase_refs: phase-1, phase-2, phase-3, phase-4
      improvements: 9 (.rddf/improvements/{fix-*, improve-*, reconcile-*})
    ```

- GIVEN `.rddf/roadmap/features/*.md` 包含 N 个 feature
  WHEN `rddf roadmap --update-agent-md` 运行
  THEN AGENTS.md 自动追加/更新 `# Active Feature Fragments` 段

- GIVEN AI agent 启动新 session,读 AGENTS.md
  WHEN 看到 `# Active Feature Fragments` 段
  THEN 立即知道当前活跃 feature 含 9 个 improvement 待 design 审查

## 技术约束

- MUST: AGENTS.md 自动段有明确标记(例如 `<!-- AUTO: feature fragments -->`),防止 manual edit 与 auto 冲突
- MUST: `list-features` 命令可被 rdd-doctor 巡检
- MUST NOT: 修改 AGENTS.md 中其他 manual 段(只追加自动段)
- SHOULD: `list-features` 支持 JSON / YAML 输出
- SHOULD: AGENTS.md 自动段在 roadmap 变更时自动刷新(install hook 或 pre-commit)

## 验收标准

- [ ] `rddf roadmap list-features` CLI 命令实现,支持 `--format {table,json,yaml}` 输出
- [ ] AGENTS.md 增加 `# Active Feature Fragments` 自动段(带 `<!-- AUTO -->` 标记)
- [ ] `rddf roadmap --update-agent-md` 实现,扫描所有 features 并更新 AGENTS.md
- [ ] `guide-arch` Phase 1 输出 feature fragments 列表作为 context
- [ ] `rdd-doctor --category roadmap-feature` 巡检(检查 feature fragment 格式 + AGENTS.md 一致性)
- [ ] 新增 unit test 覆盖 scenarios:
  - 列出 features
  - 更新 AGENTS.md
  - AGENTS.md 包含 AUTO 标记
  - 删除 feature 后 AGENTS.md 自动同步
- [ ] `list-features` 输出格式文档化
- [ ] `guide-arch/SKILL.md` Phase 1 步骤更新

## 相关

- 关联: `rddf roadmap add-feature` (创建 feature 的入口)
- 关联: AGENTS.md (项目本体文档)
- 关联: `feat-fix-audit-findings` (本提案触发的实例)
- 来源: 2026-08-27 Hybrid path reflection (本次会话)
- 文件: `rddf roadmap list-features` (新) + `.rddf/roadmap/features/` (扫描) + `AGENTS.md` (写入)