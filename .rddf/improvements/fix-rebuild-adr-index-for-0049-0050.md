# fix-rebuild-adr-index-for-0049-0050

**优先级**: P2 | **来源**: 2026-09-10 KNOWN_FAILURES baseline (2 个 pytest unit 失败)
**阶段**: v4.x | **分类**: docs-fix | **类型**: bugfix
**主题**: 第二波归档治理改进（ADR 索引自动同步 / CHANGELOG-USAGE 同步 / verifier-archive-gate 边界明确化 / 第 3 波 doc drift 清理）

## Why

`tests/unit/test_adr_index_gate.py` 2 个测试因 `docs/adr/README.md` ADR 索引与磁盘不同步而失败:

- **磁盘**: 52 个 ADR(含 `ADR-0049` `ADR-0050`)
- **README 索引**: 48 行 `| [ADR-NNNN]... |`(缺 0049/0050)

根因: ADR-0049 (`feat(rdd-verifier): inline ac-verifier`) 和 ADR-0050 (`feat(rdd-builder): 全自动决策模式`) 在 commit 9c7b015 / 6721c0f 引入后,`docs/adr/README.md` 索引**从未重新生成**。AGENTS.md 顶部"v3.0+ ADR 实施状态"段说"上次同步: 2026-09-03",但 README 索引实际停在 2026-08-15 附近。drift 让 ADR 索引失去 trust — 用户找不到新 ADR,也无法判断哪些已采纳/待采纳。

## What Changes

- 重跑 ADR 索引生成器:`python3 -c "from _lib.adr_index_generator import render_table, scan_adrs; print(render_table(scan_adrs(Path('docs/adr'))))"` → 替换 README `<!-- ADR_INDEX_START -->...<!-- ADR_INDEX_END -->` 段
- 同步顶部"v3.0+ ADR 实施状态"日期注释(从 2026-09-03 → 2026-09-10)
- 同步"上次同步: ..."注释含 commit hash

## 架构依据

- ADR-0016 (`arch-handoff v1`) — 工件发现契约,README index 是发现契约的可读视图
- `_lib/adr_index_generator.py::render_table()` 是 generator of truth,README 是其 snapshot
- v2.0+ 多 commit 后 README 不再自动同步是已知技术债(类似本仓库 CHANGELOG.md drift)

## 范围

- **In Scope**:
  - 重生成 README `<!-- ADR_INDEX_START -->...<!-- ADR_INDEX_END -->` 段
  - 更新 README 顶部"v3.0+ ADR 实施状态"日期
  - 更新 README "上次同步: ..."注释
- **Out of Scope**:
  - 不改 ADR 自身内容
  - 不改 `_lib/adr_index_generator.py`(若需改属另一 improvement)
  - 不删旧 ADR

## Capabilities

- MUST 保持 `<!-- ADR_INDEX_START -->...<!-- ADR_INDEX_END -->` 标记完整(测试依赖)
- MUST 保持表格列结构(name 链接 | 标题 | 状态 | 日期)
- MUST 按 ADR 编号升序排列
- SHOULD 顶部注释日期精确到 commit hash(避免漂移)
- SHOULD commit message 用 `refactor(docs)` 而非 `feat`/`fix`
- SHOULD NOT 删除任何现有行(除旧同步注释)

## Impact

- 关联: KNOWN_FAILURES.txt 的 2 个 `test_adr_index_gate.py::*` 条目应在本提案完成后移除
- 关联: 与 `fix-parametrize-planner-feedback-id-date` / `fix-update-doctor-main-category-count` / `fix-remove-stale-filled-at-regression-test` 同期处理
- 不影响产品行为,纯文档同步

## Acceptance

见上「验收标准」段。

## 验收标准

- [ ] `pytest tests/unit/test_adr_index_gate.py::test_adr_numbering_is_unique` 通过
- [ ] `pytest tests/unit/test_adr_index_gate.py::test_readme_index_matches_generator_output` 通过
- [ ] README 顶部"上次同步"注释更新到当前 commit
- [ ] `grep "ADR-0049\|ADR-0050" docs/adr/README.md` 至少各匹配 1 行
- [ ] `git diff docs/adr/README.md` 仅显示新增行(无删除/修改现有行)
