# Tasks: skills-reorg-phase4-thin

> **前置条件**: `skills-reorg-phase3-core` 完成,目录结构稳定

## Task 1: 提取 guide-ship.md 剩余内联代码

### 1.1: Phase 5 loop check → scripts/ship_done.sh

L650+ 的 `REMAINING`/`REMAINING_WT` 计算 + 双菜单提取到 `scripts/ship_done.sh::check_remaining_work`。

### 1.2: Phase 2 分离执行 echo → scripts/ship_execute_echo.sh

L192-215 和 L339-356 两处相似的分离执行指引提取为 `print_detached_execute_instructions <mode> <name>`。

### 1.3: Phase 4 清理 → scripts/ship_cleanup.sh

L610+ 的 worktree + branch 批量清理逻辑提取。

**验证**: `bats tests/integration/test_guide_ship_skill.bats tests/integration/test_ship_*.bats`

## Task 2: 提取其他 SKILL.md 剩余内联代码

| SKILL.md | 候选块 | 目标 helper |
|----------|--------|------------|
| guide-arch | roadmap init/status/gate-report 交互模板 | `scripts/arch_roadmap_menu.sh` |
| guide-plan | propose/create 菜单交互 | `scripts/plan_propose_menu.sh` |
| status | 归档交互 | `scripts/status_archive_menu.sh` |

每提取一个块 → 运行对应 bats 测试验证。

## Task 3: 创建 references/ LLM 参考文档

### 3.1: guide-arch/references/adr-format.md

从 `docs/adr/ADR-0000-template.md` 摘取 ADR frontmatter 模板 + 命名约定。

### 3.2: guide-ship/references/worktree-guide.md

从 `AGENTS.md` 的 "分支与 Worktree" 节 + `docs/adr/ADR-0010-*.md` 摘取 worktree 操作指引。

### 3.3: propose/references/proposal-format.md

从 `docs/proposal-suggestions-format.md` 摘取 JSON 字段说明。

### 3.4: deps/references/deps-analysis-guide.md

从 `docs/adr/ADR-0014-*.md` 摘取依赖分析规则。

### 3.5: execute/references/tdd-5-steps.md

从 `skills/spec-workflow-writing-plans/SKILL.md` 摘取 TDD 5 步结构。

## Task 4: 更新文档

### 4.1: 更新 CHANGELOG.md

新增 v2.0.8 section:
```markdown
## v2.0.8 — skills/ directory reorganization

### Phase 1: Per-skill subdirectory skeleton
### Phase 2: Single-skill helper migration (45 files)
### Phase 3: Core infrastructure consolidation
### Phase 4: SKILL.md thinning + references/
```

### 4.2: 更新 AGENTS.md

更新目录结构描述以反映新布局（`skills/<name>/SKILL.md` + `scripts/` + `references/`）。

### 4.3: 更新 tests/README.md

更新技能覆盖表引用路径。

## Task 5: 清理

### 5.1: 确认 state.sh STUB 状态

```bash
grep -rn "state\.sh" skills/ --include="*.sh" | grep -v "^Binary"
```
确认 `plan_queue_overview.sh:15` 是唯一引用点。如确实未调用,添加 TODO 注释标记为候选删除（`tech-debt-cleanup`）。

### 5.2: 扫描残留的 `_lib/` 旧路径引用

```bash
grep -r "_lib/" skills/*/SKILL.md | grep -v "scripts/" | grep -v "../_lib/"
```
确认无残留的旧路径。

## Task 6: 全量验证

```bash
bats tests/smoke.bats
bats tests/
python3 -m pytest tests/unit/ tests/integration/ -q --tb=short
```

**预期**: 0 failures, 全部现有测试通过。

## Task 7: commit

```bash
git add skills/*/scripts/ skills/*/references/ skills/*/SKILL.md CHANGELOG.md AGENTS.md tests/README.md
git commit -m "refactor(skills): Phase 4 — thin SKILL.md + add references/

- Extract remaining inline code blocks from guide-ship/guide-arch/guide-plan/status
- Add references/ LLM context docs for key skills (adr-format, worktree-guide, etc.)
- Update CHANGELOG.md (v2.0.8), AGENTS.md, tests/README.md with new layout
- All SKILL.md files now target ≤ 300 lines
- skills/ layout matches PKGM-Wiki pattern: SKILL.md + scripts/ + references/"
```