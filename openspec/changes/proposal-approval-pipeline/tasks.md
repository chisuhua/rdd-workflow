## 1. improvements/ 目录 + 迁移脚本

- [ ] 1.1 创建 `skills/_lib/migrate_proposals.py` — 将 legacy JSON `proposal-suggestions.md` 转换为 `improvements/*.md` 独立文件
- [ ] 1.2 创建 `docs/proposal-approved-format.md` — proposal-approved.md 格式规范文档
- [ ] 1.3 执行迁移脚本，生成全部 27 个 `improvements/*.md`
- [ ] 1.4 更新 `proposal-suggestions.md` — 确保索引表包含所有迁移后的提案 + 正确的状态标记

## 2. state.sh — 新增双索引读写函数

- [ ] 2.1 `skills/_lib/state.sh` 新增 `list_improvements(project_root)` — 扫描 improvements/ 目录返回 Markdown 行列表
- [ ] 2.2 `skills/_lib/state.sh` 新增 `list_approved(project_root)` — 解析 proposal-approved.md 表格返回条目
- [ ] 2.3 `skills/_lib/state.sh` 新增 `append_approved(project_root, name, priority)` — 追加一行到 proposal-approved.md
- [ ] 2.4 `skills/_lib/state.sh` 新增 `mark_approved_completed(project_root, name)` — 标记 approved.md 条目为已完成

## 3. propose skill — 从 approved.md 读取

- [ ] 3.1 `skills/propose/SKILL.md` — Phase 0 改为读取 `proposal-approved.md`（筛选 status=approved 或未标记为已完成的条目）
- [ ] 3.2 `skills/propose/scripts/propose_change.py` — `set_suggestion_status()` 改为更新 `proposal-approved.md`
- [ ] 3.3 `skills/propose/scripts/update_proposal_status.py` — 目标文件改为 `proposal-approved.md`

## 4. scan-state.sh + dashboard + gate — 双索引适配

- [ ] 4.1 `skills/guide/scripts/scan-state.sh` — 双索引扫描：suggestions 有待讨论 → 推荐 arch；approved 有 → 推荐 plan
- [ ] 4.2 `skills/_lib/dashboard/__init__.py` + `renderer.py` — 双索引展示（suggestions panel + approved panel）
- [ ] 4.3 `skills/_lib/workflow_synthesizer.py` — 双索引状态合成
- [ ] 4.4 `skills/_lib/gate.py` — proposal 相关检查适配双索引
- [ ] 4.5 `skills/_lib/state_reader.py` — 新增 `read_improvement_entries()` 扫描 improvements/ 目录读取 frontmatter

## 5. archive.sh — 归档时更新 approved.md

- [ ] 5.1 `skills/_lib/archive.sh` L312 — `python3 update_proposal_status.py` 调用改为更新 `proposal-approved.md`
- [ ] 5.2 `skills/_lib/archive_helper.py` — 适配双索引

## 6. guide-arch — 新增 Phase 5.5 审批流程

- [ ] 6.1 `skills/guide-arch/SKILL.md` — 新增 Phase 5.5，展示 improvements/ 目录下待讨论提案，支持批准/拒绝/延迟
- [ ] 6.2 `skills/guide-arch/scripts/` — 新增 `approve_proposal.sh` 辅助脚本（追加到 approved.md）

## 7. 测试适配

- [ ] 7.1 `tests/integration/test_suggestions_format.bats` — 适配双索引格式
- [ ] 7.2 `tests/integration/test_archive_proposal_status.bats` — 适配 approved.md
- [ ] 7.3 `tests/unit/test_propose_change.py` — `TestSetSuggestionStatus` 适配新目标文件
- [ ] 7.4 `tests/integration/test_count_pending_suggestions.bats` — 改为 count pending improvements

## 8. 验证

- [ ] 8.1 `npm test` 全部测试通过
- [ ] 8.2 `lsp_diagnostics` 所有修改文件 clean
- [ ] 8.3 验证 guide-arch → guide-plan 全流程