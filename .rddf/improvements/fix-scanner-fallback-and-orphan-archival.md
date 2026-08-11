# fix-scanner-fallback-and-orphan-archival

**优先级**: P1 | **来源**: HydraForge 案例 2026-07-31 — 消费方项目调用 `skill_use("guide")` 时 scanner 静默失败, 用户被迫手工绕过; rddf-session archive-history 不能清理孤儿 session
**阶段**: default | **分类**: infra-setup
**类型**: debt

## 架构依据

- **ADR-0013**（已采纳）: scan-state 提取到 `skills/_lib/scan-state.sh`, 确立"helper 集中在 `_lib/`"的先例
- **ADR-0021**（已采纳）: Phase 2 per-skill helper 迁移 — 单 skill helper 移走, **跨 skill 共享 helper 留在 `_lib/`** (state.sh / worktree.sh / archive.sh)
- **ADR-0017** §3: rddf-session 跨 OpenCode session 持久化, `_TERMINAL_STATES` 是 schema 一部分
- **触发事件**: HydraForge 项目（rdd-workflow 使用方）于 2026-07-31 调用 `skill_use("guide")`, scanner 在 `PROJECT_ROOT/skills/_lib/state.sh: No such file or directory` 处静默失败, 无菜单输出; 用户被迫手工扫描状态
- **根因 1**: `scan-state.sh:67` + `guide_entry.sh:185` 硬编码 `source "$PROJECT_ROOT/skills/_lib/state.sh"`, 无全局 `~/.agents/skills/_lib/state.sh` fallback
- **根因 2**: rddf-session `_TERMINAL_STATES = {"completed", "failed", "abandoned"}` 不含 `"orphaned"`, 导致 `archive_history(keep=0)` 跳过 heartbeat-timeout session（在 HydraForge 案例中: 11 个 session 仅归档 4 个, 7 个孤儿残留）
- **临时绕过（不可持续）**: 用户手工把 7 个 `orphaned` 改为 `abandoned`, 触发 archive-history round 2 — 这违反 schema 语义, 长期不可维护

## 范围

**In Scope**:
1. `skills/guide/scripts/scan-state.sh` 第 67 行: 硬编码 `source` 改为多路径 fallback（`PROJECT_ROOT/skills/_lib/state.sh` → `${HOME}/.agents/skills/_lib/state.sh`）
2. `skills/guide/scripts/guide_entry.sh` 第 185 行: 同上
3. fallback 全失败时打印 warning 到 stderr（不静默退出）
4. `skills/rddf-session/scripts/rddf_session_pkg/_types.py` 第 42 行: `_TERMINAL_STATES` 添加 `"orphaned"`
5. 新增测试: `tests/integration/test_scanner_fallback.bats`（4 矩阵）+ `tests/unit/test_terminal_states_orphan.bats`（4 state 各 1 case）

**Out Scope**:
- 重写 scanner 逻辑（仅 2 行 source 改动 + 错误处理）
- 修改 rdd-workflow 安装路径或 INSTALL.md
- 引入 symlink / runtime path resolution 等其他 fallback 机制
- 修复其他共享 helper（`worktree.sh` / `archive.sh`）的同类问题（如有则单列改进）
- rddf-session 其他 schema 调整（保留现状, 只补 `orphaned`）

## 关键场景

**场景 1（scanner fallback 成功）**:
- GIVEN PROJECT_ROOT 是消费方项目（无本地 `skills/_lib/state.sh`）, 全局 `~/.agents/skills/_lib/state.sh` 存在
- WHEN 调用 `skill_use("guide")` 触发 `scan-state.sh::scan_state()`
- THEN scanner 自动从 `~/.agents/skills/_lib/state.sh` 加载 helper, 正常输出菜单

**场景 2（fallback 全失败）**:
- GIVEN PROJECT_ROOT 无本地 `skills/_lib/state.sh`, 全局也不存在
- WHEN scanner 启动
- THEN 打印明确 warning 到 stderr (`"⚠️ rdd-workflow not installed: tried PROJECT_ROOT/skills/_lib/state.sh and ~/.agents/skills/_lib/state.sh, both missing. Run INSTALL.md"`), stdout 输出空菜单（保持当前行为, 不污染 JSON）

**场景 3（孤儿 session 归档）**:
- GIVEN sessions.json 包含 1 个 active + 2 个 orphaned（heartbeat-timeout）
- WHEN 调用 `archive_history(keep=0)`
- THEN 3 个 session 全部进入 `.archive.json`（当前只归档 1 个 active-derived, 2 个孤儿残留）

**场景 4（向后兼容 — rdd-workflow 自身项目）**:
- GIVEN PROJECT_ROOT 是 rdd-workflow 自身（有本地 `skills/_lib/state.sh`）
- WHEN scanner 启动
- THEN 优先使用本地副本, 全局 fallback 不被触发, 行为零变化（diff 0 字节）

**场景 5（混合 session 状态）**:
- GIVEN sessions.json 含 completed (1) + failed (1) + abandoned (1) + orphaned (1) + active (1)
- WHEN `archive_history(keep=10)`
- THEN 5 个 terminal (completed/failed/abandoned/orphaned) 全部归档; active 保留

## 技术约束

**MUST**:
- scanner source 顺序: 先 `$PROJECT_ROOT/skills/_lib/state.sh`, 再 `${HOME}/.agents/skills/_lib/state.sh`, 再 fallback warning
- 两处 scanner (`scan-state.sh:67` + `guide_entry.sh:185`) 行为必须一致
- `_TERMINAL_STATES` 添加 `"orphaned"` 后保持原 3 个 state 不变（adopt, 不要 replace）
- 新增 bats 测试用项目现有 bats 版本（不引入新依赖）
- fallback warning 用 stderr 输出（不污染 stdout menu JSON）
- warning 文本必须含 `"rdd-workflow not installed"` 关键字 + `INSTALL.md` 路径提示
- 用 `${HOME}` 而非 `~`（shell 兼容）

**MUST NOT**:
- 不得引入 symlink / runtime path resolution 等其他 fallback 机制
- 不得修改 rdd-workflow 自身的 `skills/_lib/state.sh`（helper 内容不变, 仅 scanner 加载路径）
- 不得删除 `_TERMINAL_STATES` 现有 3 个 state
- 不得对 `archive_history()` 函数签名做破坏性变更
- 不得在 scanner 中硬编码 `~`
- 不得 fallback 警告时 exit 非零（warning 必须非阻塞, scanner 仍输出空菜单）

**SHOULD**:
- fallback 路径搜索应在 1ms 内完成（不引入网络调用、磁盘扫描）
- 加载失败 warning 文本应明确指向 `INSTALL.md`（让用户知道如何修复）
- 测试覆盖 PROJECT_ROOT 有/无 state.sh × HOME 有/无 state.sh 共 4 种矩阵
- 新增测试应使用与现有 bats 测试一致的 `setup` / `teardown` 模式

## 验收标准

1. **scanner fallback 行为**: 4 矩阵测试全 PASS（PROJECT_ROOT × HOME 各有/无 state.sh）
2. **warning 文本**: 当两路径都缺失, stderr 输出含 `"rdd-workflow not installed"` + `INSTALL.md` 提示, exit code 0
3. **菜单输出一致**: scanner 成功加载 fallback 时, stdout 输出与原 PROJECT_ROOT 加载路径完全一致（diff 0 字节）
4. **rddf-session schema**: `_TERMINAL_STATES == {"completed", "failed", "abandoned", "orphaned"}` 且 4 个 unit test 通过
5. **archive-history 行为**: HydraForge 复现脚本（11 sessions 全归档）100% 一次成功, 不再需要 schema workaround
6. **回归测试**: 现有 `tests/integration/test_scan-state.bats` 全 PASS 零修改
7. **CI 检查**: `openspec validate` + `bats tests/integration/` 全部 exit 0
8. **行数约束**: `scan-state.sh` + `guide_entry.sh` 各 +2~4 行; `_types.py` 1 行修改; 总计 ≤10 行代码变更
9. **文档同步**: AGENTS.md（rdd-workflow 项目自身）+ CHANGELOG.md 同步记录 fallback 行为变化