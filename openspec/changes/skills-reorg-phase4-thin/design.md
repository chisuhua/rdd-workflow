# Design: skills-reorg-phase4-thin

## Decision 1: 提取优先级

遵循 Round A/B/C 的成熟模式：
1. `> 20 行` 且 `> 80% 代码` 的内联块 → 必提取
2. `> 10 行` 且 `> 50% 代码` 的内联块 → 建议提取
3. 纯 markdown 指令/表格 → 保留在 SKILL.md 中

## Decision 2: references/ 内容来源

从 `docs/` 中摘取与具体 skill 强相关的文档片段，而非复制整个文件。例如：
- `skills/guide-arch/references/adr-format.md` ← `docs/adr/ADR-0000-template.md` 的结构说明部分
- `skills/guide-ship/references/worktree-guide.md` ← `AGENTS.md` 的 worktree 相关约定

## Decision 3: state.sh STUB 处理

AGENTS.md 称 `state.sh` 为 STUB（"无 production 调用方"），但实际代码显示 `plan_queue_overview.sh:15` source 了它。Phase 4 中需要确认该函数是否实际被调用；若确实未调用，可考虑删除（但不在本 change 范围 — 属于 `tech-debt-cleanup`）。

## Decision 4: 文档更新

- `CHANGELOG.md`: 新增 v2.0.8 section 记录四阶段重构
- `AGENTS.md`: 更新目录结构描述以反映新布局
- `tests/README.md`: 更新技能覆盖表引用路径

## 回滚方案

per-file `git checkout`。
