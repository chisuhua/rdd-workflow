## 1. 准备 + 验证

- [ ] 1.1 创建 worktree：`git worktree add .rddf/wt/migrate-improvements-to-rddf-namespace -b openspec/migrate-improvements-to-rddf-namespace master`
- [ ] 1.2 验证 worktree 工作区干净（`git status` 无未提交改动）
- [ ] 1.3 读 `.rddf/state/.plan-handoff.json` 确认 ship 阶段入口状态

## 2. git mv（原子移动）

- [ ] 2.1 `mkdir -p .rddf/improvements`
- [ ] 2.2 `git mv improvements/*.md .rddf/improvements/` （133 个文件）
- [ ] 2.3 `rmdir improvements` （验证目录为空）
- [ ] 2.4 验证：`git ls-files .rddf/improvements/ | wc -l` == 133 (AC-1a)
- [ ] 2.5 验证：`git log --follow .rddf/improvements/<sample>.md` 显示完整 history (AC-1c)

## 3. 批量链接更新

- [ ] 3.1 `sed -i 's|](improvements/|](.rddf/improvements/|g' proposal-approved.md`
- [ ] 3.2 验证：134 个链接全部更新（`grep -c '](.rddf/improvements/' proposal-approved.md` == 134）
- [ ] 3.3 验证：旧链接零残留（`grep -c '](improvements/' proposal-approved.md` == 0）

## 4. skills/_lib/ 路径常量

- [ ] 4.1 `grep -rln "improvements/" skills/ _lib/ > /tmp/affected-files.txt`
- [ ] 4.2 逐文件 review 替换（37 个文件，预计 1-3 处/文件）
  - [ ] 4.2.1 `skills/add-improve/SKILL.md` (3 处)
  - [ ] 4.2.2 `skills/guide-design/SKILL.md` (1 处)
  - [ ] 4.2.3 `skills/guide-design/scripts/*.sh` (3-4 处 glob 路径)
  - [ ] 4.2.4 `skills/guide-design/scripts/generate_full_proposal.py` (1 处)
  - [ ] 4.2.5 `skills/guide/scripts/scan-state.sh` (1-2 处 glob)
  - [ ] 4.2.6 `skills/guide*/SKILL.md` (3 处文档)
  - [ ] 4.2.7 `skills/propose/scripts/*.py` (3-4 处)
  - [ ] 4.2.8 `skills/rdd-doctor/scripts/checks/proposal_table_check.py` (1 处)
  - [ ] 4.2.9 其他 `_lib/` 文件 (~15 处)
- [ ] 4.3 验证：`grep -rn "improvements/" skills/ | grep -v ".rddf/improvements" | wc -l` == 0 (AC-2)

## 5. 文档同步

- [ ] 5.1 `docs/proposal-suggestions-format.md`: 路径示例改 `.rddf/improvements/`
- [ ] 5.2 `docs/proposal-approved-format.md`: 路径示例改 `.rddf/improvements/`
- [ ] 5.3 `INSTALL.md`: 路径提及（如有）
- [ ] 5.4 `USAGE.md`: 路径提及（如有）
- [ ] 5.5 `README.md`: 路径提及（如有）
- [ ] 5.6 `docs/adr/ADR-0024-deps-driven-execution-mode.md`: 文中 improvements 路径
- [ ] 5.7 `docs/adr/ADR-0025-design-proposal-creation.md`: 文中 improvements 路径
- [ ] 5.8 `docs/architecture/workflow-phases.md`: 文中 improvements 路径
- [ ] 5.9 验证：`grep -rn "improvements/" docs/ | grep -v ".rddf/improvements" | wc -l` == 0 (AC-2)

## 6. ADR-0026 创建

- [ ] 6.1 创建 `docs/adr/ADR-0026-internal-metadata-namespace-convention.md`
- [ ] 6.2 内容包含：dot-prefix 命名规则、已存在实例（plans/、improvements/）、未来添加新 metadata 类别的指引
- [ ] 6.3 验证：内容包含 `.rddf/<category>` 和 `opencode-skillfull` 关键字 (AC-7)

## 7. 测试 fixture + 集成测试

- [ ] 7.1 `tests/fixtures/diseased-repo/proposal-suggestions.md`: 路径改新
- [ ] 7.2 `tests/integration/fixtures/guide_entry_clean.json`: 路径改新
- [ ] 7.3 `tests/integration/scan_state.bats`: 路径改新
- [ ] 7.4 `tests/integration/test_approve_*.bats` (~5 个): 路径改新
- [ ] 7.5 `tests/integration/test_design_*.bats` (~3 个): 路径改新
- [ ] 7.6 `tests/integration/test_archive_*.bats` (~3 个): 路径改新
- [ ] 7.7 其他引用 `improvements/` 的 bats 文件
- [ ] 7.8 验证：`grep -rn "improvements/" tests/ | grep -v ".rddf/improvements" | wc -l` == 0 (AC-2)

## 8. 验证

- [ ] 8.1 AC-1: 文件迁移完整性（`git ls-files .rddf/improvements/ | wc -l` == 133, 旧目录为空, history 保留）
- [ ] 8.2 AC-2: 路径引用零残留（4 个目录 grep 全 0）
- [ ] 8.3 AC-3: 134 个 markdown 链接全部可解析
- [ ] 8.4 AC-4: skill 行为不变（`bash tests/smoke.bats` + `scan_state.bats` 全绿）
- [ ] 8.5 AC-5: 上下文节省（用户重启 opencode 验证 available_skills 不含 improvements/*）
- [ ] 8.6 AC-6: 全量回归测试（`./test.sh --full --regression` 通过）
- [ ] 8.7 AC-7: ADR-0026 文档化（文件存在 + 关键字命中）
- [ ] 8.8 AC-8: rdd-doctor 通过（0 CRITICAL + 0 路径相关 WARNING）

## 9. worktree 内部 commit + merge

- [ ] 9.1 1 个聚合 commit（不逐任务 commit）：`refactor(rdd-workflow): migrate improvements/ → .rddf/improvements/ for plugin filter (saves ~4,887 tokens)`
- [ ] 9.2 merge 到 default branch（`git checkout master && git merge --no-ff openspec/migrate-improvements-to-rddf-namespace`）
- [ ] 9.3 worktree + branch cleanup
- [ ] 9.4 跑 `./test.sh --full` 二次确认（合并后）
