# improve-change-splitting-strategy

**优先级**: P2 | **来源**: 2026-08-27 ship audit (sync-package-skills-to-disk + sync-agents-md-five-stage)
**阶段**: default | **分类**: governance
**类型**: process

**主题**: 2026-08-26 文档与代码一致性审计后续修复

## 架构依据

2026-08-27 同时 ship `sync-package-skills-to-disk`(改 AGENTS.md line 72/118) 和 `sync-agents-md-five-stage`(改 AGENTS.md line 84/148/159)。两个 change **共享同一个文件 AGENTS.md**,导致 ship 期间:

- 第 1 个 change commit 后,第 2 个 change 的 worktree 中的 AGENTS.md 已经包含了第 1 个 change 的修改(因为 worktree 从 master 创建)。
- 第 2 个 change 的 commit 时,如果不精确 patch,会把第 1 个 change 的内容也带进去(`git add -A` 污染案例)。
- 最终需要 `git reset --soft HEAD~1` + 手工精确 patch,浪费 3 次重做。

期望行为: 当多个 proposal 都修改同一文件时,应该:

1. **合并为单个 change**(在 design 阶段检测冲突)
2. **或**强制串行 ship 并要求精确 patch(在 ship 阶段)
3. **或**对共享文件改动做独立文件 patch(每个 change 只动自己那几行)

## 范围

**In Scope**:

- `guide-design` Phase 2 增加检测: 待审查 proposals 之间是否有共享文件修改(从 `.rddf/improvements/*.md` 的 ## 范围节 grep 文件路径)。
- 如果有冲突,提示用户:
  - 合并为单一 change,或
  - 强制串行 ship
- `guide-ship` 在 worktree 创建后,run `git diff main -- <file>` 显示冲突文件,要求 user 确认 patch 边界。

**Out of Scope**:

- 自动合并 proposals(高风险,需 user 决策)
- 修改 AGENTS.md 模板拆分

## 关键场景

- GIVEN `sync-package-skills-to-disk` 和 `sync-agents-md-five-stage` 都修改 AGENTS.md
  WHEN `guide-design` Phase 2 扫描 proposals
  THEN 提示 user "2 个 proposals 共享 AGENTS.md,建议合并或串行"

- GIVEN 第 2 个 change 的 worktree 创建后
  WHEN `git diff main -- AGENTS.md` 运行
  THEN 显示 2 处共享文件改动,要求 user 确认 patch 边界(只动 line 84/148/159,不要带 line 72/118)

## 技术约束

- MUST: 检测基于 `.rddf/improvements/*.md` 的 ## 范围节,不是 proposal.md(已 commit 时才可读)
- MUST: 检测结果作为 WARNING 输出,不阻断 ship
- MUST NOT: 自动合并或修改 proposals(必须 user 决策)
- SHOULD: 提供 `--strict-change-split` flag,启用时阻断冲突 ship

## 验收标准

- [ ] `guide-design` Phase 2 新增 shared-file 冲突检测
- [ ] 冲突时输出 WARNING: "N 个 proposals 共享文件 X,建议合并"
- [ ] `guide-ship` Phase 1 显示冲突文件 diff 提示
- [ ] 新增 unit test 覆盖 2 scenarios: 共享文件 / 无共享文件
- [ ] 文档更新 `guide-design/SKILL.md` 和 `guide-ship/SKILL.md`
