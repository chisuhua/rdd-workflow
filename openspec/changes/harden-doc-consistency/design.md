# Design: harden-doc-consistency

## Approach

按"代码优先，文档对齐代码"原则修复：

1. **代码修复**（run-time 行为变更）:
   - `skills/_lib/worktree.sh`: 修复 `find_default_branch` 在 worktree 内的 fallback
   - `skills/_lib/state.sh`: 删除 orphan helpers（或 refactor `propose.md`/`roadmap.md` 实际使用）
   - `skills/_lib/worktree.sh`: 删除 `is_change_committed`（或 wire-up 到 5 个使用点）
   - `skills/status.md` + `skills/execute.md`: 删除内联 `wt_path_for_branch_inline`，统一调用 `_lib/worktree.sh::wt_path_for_branch`

2. **文档修复**（对齐代码现状）:
   - `USAGE.md`: 重新对齐 phase 描述（5 阶段 + 1 退出）
   - `docs/adr/ADR-0001`: 重写 Decision section，对齐实际架构
   - `skills/INSTALL.md`: 同步版本号与 skill 列表
   - `docs/proposal-suggestions-format.md`: 添加 `deps.md` consumer
   - `skills/propose.md`: 修正 ADR 引用 regex（3 位 → 4 位）
   - `tests/README.md`: 同步实际文件布局

3. **跨文档同步**:
   - 所有 skill 中硬编码 `main` → `${DEFAULT_BRANCH:-master}` 或动态检测
   - `skills/status.md` 示例输出 `/path/to/CppHDL` → `/path/to/PROJECT_ROOT`

## Trade-offs

| 方案 | 优势 | 风险 |
|------|------|------|
| **A. 保留 `_lib/state.sh`，refactor `propose.md`/`roadmap.md` 使用** | 保留 helper；统一 JSON I/O 路径 | 改动面大；可能引入 bug |
| **B. 删除 `_lib/state.sh` 的 orphan helpers** | 简单；立即消除 dead code | 失去未来 refactor 的 hook |
| **A. 删除 `is_change_committed` 重复实现** | 简化 API | 无（无 caller） |
| **B. Wire-up `is_change_committed` 到 5 个使用点** | 统一 helper | 改动 5 个文件；风险更高 |

**决策**:
- `_lib/state.sh` → **B. 删除 orphan helpers**（更简单）
- `is_change_committed` → **A. 删除**（无 caller）
- `wt_path_for_branch_inline` → **A. 统一调用 `_lib/worktree.sh::wt_path_for_branch`**
- `find_default_branch` → **修复**（bug 修复必要）

## Test Strategy

1. **回归**: `bats tests/integration/test_doc_phase_consistency.bats` 应从 3/5 → 5/5
2. **完整性**: `bats tests/integration/test_skill_metadata_consistency.bats` 4/4 保持
3. **状态**: `bats tests/integration/test_status_skill.bats` 4/4 保持
4. **ADR**: `bats tests/integration/test_adr_directory.bats` 13/14 (test 13 在 commit 后通过)
5. **新单元测试**: 添加 `test_find_default_branch_in_worktree.bats` 验证 bug 修复
6. **新单元测试**: 添加 `test_wt_path_for_branch_helper.bats` 验证统一调用

## Migration

无需 migration（纯内部修复，无 schema 变更，无 API 变更）。

## Open Questions

无。
