# audit-attach-detach-calls - Tasks

**Priority**: P0
**Phase**: v2.1
**Type**: audit (read-only)

## Task 1: 静态扫描 attach_change/detach_change 调用点

- [x] 1.1 在 worktree 根运行 `grep -rn 'attach_change\|detach_change' skills/ tests/ docs/`
- [x] 1.2 分类每个匹配: production / test / definition / doc-reference
- [x] 1.3 记录每个调用点的 文件:行号 + 上下文 (1 行)

## Task 2: 追踪 3 个 hook 的 guide skill 调用矩阵

- [x] 2.1 grep `rddf_session_hook_entry|_close|_heartbeat` in skills/guide-arch/guide-plan/guide-ship SKILL.md
- [x] 2.2 对每个 hook 检查其 Python 实现内是否调用 attach/detach (hooks.sh:39-191)
- [x] 2.3 构建 3×3 调用矩阵表格

## Task 3: ADR-0017 契约期望对比

- [x] 3.1 读取 ADR-0017 + v2-multi-session-guide §"自动管理"
- [x] 3.2 列出期望的 attach 时机 (ship entry 时 attach 当前 change)
- [x] 3.3 列出期望的 detach 时机 (archive 时 detach 已归档 change)
- [x] 3.4 对比实际行为, 列出差异

## Task 4: 生成审计报告

- [x] 4.1 写 `.rddf/state/attach-detach-audit.md` 含 §1-§7 (见 design.md §6)
- [x] 4.2 报告中每个调用点必须有精确 文件:行号
- [x] 4.3 报告必须引用 ADR-0017 / v2-multi-session-guide 作为期望来源

## Task 5: 验证 + 提交

- [x] 5.1 确认无源文件被修改 (`git status` 仅本 change 的 artifacts + 报告)
- [x] 5.2 运行既有 `pytest tests/unit/test_rddf_session.py -q` 确认无 regression
- [x] 5.3 commit: `audit(attach-detach): produce audit report`
- [x] 5.4 archive change via openspec
