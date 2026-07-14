## 1. find_current_binding + find_next_recommendation 方法

- [x] 1.1 在 `skills/_lib/rddf_session.py` 中新增 `find_current_binding(owner)` 方法（紧随 `create_session` 之后）
- [x] 1.2 在 `skills/_lib/rddf_session.py` 中新增 `find_next_recommendation(owner=None)` 方法（紧随 `find_current_binding` 之后）
- [x] 1.3 两个方法均使用 `_with_file_lock` 模式（与 `find_session`/`list_sessions` 一致）

## 2. unit tests

- [x] 2.1 创建 `tests/unit/test_rddf_binding.py`（10 个测试用例）
- [x] 2.2 active owner / terminal owner / different owner / multi-active / empty file — find_current_binding 5 个
- [x] 2.3 most-recent orphaned / no orphaned / mixed / empty / heartbeat-promotion — find_next_recommendation 5 个
- [x] 2.4 pytest 545 全绿（含 test_rddf_session.py 既有 24 个测试无回归）

## 3. rddf-session current 子命令

- [x] 3.1 在 `skills/rddf-session.md` subcommands 列表中插入 `current` 行（位于 `show` 与 `resume` 之间）
- [x] 3.2 在 bash case 列表中插入 `current)` 分支（Python heredoc 调用 `find_current_binding` + `find_next_recommendation`）
- [x] 3.3 更新 `*)` 用法行包含 `current`
- [x] 3.4 frontmatter `metadata.version` 从 1.0 → 1.1，添加 `evolved-from: "rddf-session.md v1.0"`

## 4. rddf-session current 集成测试

- [x] 4.1 创建 `tests/integration/test_rddf_session_current.bats`（8 个 bats 测试）
- [x] 4.2 bound / unbound / orphaned recommended / missing-file / corrupt-json / OPENCODE_SESSION_ID / hostname fallback / no-mutation
- [x] 4.3 bats 8/8 通过

## 5. scan_session_binding 函数

- [x] 5.1 在 `skills/_lib/scan-state.sh` 末尾新增 `scan_session_binding()` 函数 + `BINDING_LINES=()` 全局
- [x] 5.2 使用 process substitution `< <(...)`（非管道），保留调用方变量
- [x] 5.3 Python heredoc 使用 `<<'PYEOF'`（单引号，禁止 bash 变量展开）
- [x] 5.4 `PY_PROJECT_ROOT` env var 模式保证 cwd 安全
- [x] 5.5 sessions.json 缺失/损坏时静默返回（`BINDING_LINES=()` 空数组）

## 6. scan_session_binding 集成测试

- [x] 6.1 创建 `tests/integration/test_guide_binding_alert.bats`（5 个 scan_session_binding 测试）
- [x] 6.2 bound / unbound+orphaned / missing-file / RECOMMEND-preserved / no-mutation
- [x] 6.3 bats 5/5 通过

## 7. guide.md 集成

- [x] 7.1 修改 `skills/guide.md` bash 示例，在 `scan_state` 后追加 `scan_session_binding` + `BINDING_LINES` 打印
- [x] 7.2 添加 Output Format 章节中 v2.0.2+ 新输出行的文档
- [x] 7.3 调用顺序固定：`scan_state` → RECOMMEND/REASON echo → `scan_session_binding` → `printf '%s\n' "${BINDING_LINES[@]}"`
- [x] 7.4 frontmatter 不修改

## 8. guide.md 集成测试

- [x] 8.1 在 `tests/integration/test_guide_binding_alert.bats` 末尾追加 5 个 guide 集成测试
- [x] 8.2 bound / no-binding / RECOMMEND-stable / source-ordering / no-mutation
- [x] 8.3 bats 5/5 通过

## 9. 文档

- [x] 9.1 `AGENTS.md` 新增 `### Session Binding Policy (ADR-0017 + spec 2026-07-14)` subsection
- [x] 9.2 位于 Arch Discovery Contract 与 Skill 文件规范 之间
- [x] 9.3 `docs/adr/ADR-0017-rddf-session.md` 末尾新增 `## Cross-Reference` section
- [x] 9.4 引用 `docs/superpowers/specs/2026-07-14-rddf-session-binding-design.md`

## 10. 最终验证

- [x] 10.1 pytest tests/unit/ — 545 passed
- [x] 10.2 bats tests/integration/test_rddf_session_current.bats — 8 passed
- [x] 10.3 bats tests/integration/test_guide_binding_alert.bats — 10 passed
- [x] 10.4 bats tests/integration/test_guide_scan.bats — 4 passed（无回归）
- [x] 10.5 CI gate: `grep -rn "assert.*or True\|assert True" tests/` — empty
- [x] 10.6 sessions_schema.json: `git diff` 空（schema 未变）
- [x] 10.7 合并到 master（merge commit `f540f48`），worktree 已删除，分支已删除