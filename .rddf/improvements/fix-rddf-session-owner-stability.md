# fix-rddf-session-owner-stability

**优先级**: P0 | **来源**: 2026-08-02 ship 复盘
**阶段**: v2.1 | **分类**: core
**类型**: bugfix

## 架构依据

rddf-session owner identity 通过 `$(hostname -s)_$PPID` 推断 (SKILL.md L251 承诺 "stable across bash tool calls within one window"),但实际:

- bash 工具调用每次 spawn 新子 shell,子 shell `$PPID` 指向当前 shell 树的某一级,**不一定是 opencode server PID**
- 同一 OpenCode 窗口内,相邻两次 bash 调用会产生不同 owner ID (实证:`my-eci-group_2044384` → `my-eci-group_2506969`)
- 导致同窗口连续 `guide-ship` 调用创建多个"独立" rddf-sessions,产生:
  - 跨 owner 的虚假 parent 链 (`stage_ship` 的 parent 指向另一个 owner 的 `stage_plan`)
  - heartbeat 30 分钟超时检测不到(owner 漂移在秒级发生)
  - 用户难以分辨"我自己同一会话创建的多个 sessions"和"被遗忘的孤儿 sessions"
- 31 个 archived 历史 session 中,16 个 abandoned + 3 个 orphaned 主要是用户主动关闭未触发 archive-history,部分可能是此 bug 的表征

**Refine 而非新开 change**: 此 bug 与已实施的 `fix-rddf-session-owner-cross-call` (P1, 2026-07-29, 详见 `proposal-approved.md` 第 1 节) 是**同根因的回归**——后者把 fallback 从 `$$`(子 shell PID)改为 `$PPID`(父 shell PID),但原 PR 仅承诺"stable across bash tool calls",实际证明 `$PPID` 同样不可靠(实证见上)。本提案是 v2 升级版,设计阶段应创建 `refine-rddf-session-owner-detection` 增量 PR(而非开新 change),合并时引用本改进为根因证据链。

依据:ADR-0017 (rddf-session 设计 §2.1 owner identity)。

## 范围

- **In Scope**:
  - 修改 `skills/rddf-session/scripts/rddf_session_hooks.sh` 三处 fallback 逻辑 (`OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$PPID}"`)
  - fallback 链优先级:`$OPENCODE_SESSION_ID` env var → `/proc/<shell-ppid>/cmdline` 探测 opencode server → `$(hostname -s)_$$`(当前 shell PID 而非 `$PPID`)
  - **跨 bash 调用持久化机制**(关键缺口): bash 子进程不继承父 shell 探测结果,必须在某次探测成功后将结果写入 `~/.cache/rddf-session-owner` (per-host, 0600 权限),后续 fallback 在 env var 缺失时优先读此文件。具体契约:
    - 探测成功(proc-cmdline 命中)→ 写文件 `<ppid-or-host-pid>\t<source>\n`
    - 文件 TTL: 1 小时(防止 opencode server 重启后 stale ID)
    - env var 始终优先于文件(允许 OpenCode 平台运行时注入覆盖)
  - 增加 `OPENCODE_SESSION_ID_FROM` 调试字段 (env / proc-cmdline / shell-pid / cached-file),写入 sessions.json 时作为 session 的可选 `owner_meta` 子结构(不污染 schema v1 必填字段)
  - 单元测试:同窗口多次 bash 调用 fallback 一致性;cache file 写入/读取 round-trip
  - bats 集成测试:`rddf_session_hook_entry` 在无 env var 时按预期探测;删除 cache file 后下一次调用重建
- **Out Scope**:
  - 不修改 OpenCode 平台 (应由平台显式注入 `OPENCODE_SESSION_ID` uuid)
  - 不修改 schema (owner 字段类型不变,仅 fallback 来源变化)
  - 不修改 RDDF_ALLOW_CROSS_STAGE_PARALLEL 行为

## 关键场景

- GIVEN bash 工具调用无 `OPENCODE_SESSION_ID` env var,WHEN 调用 `rddf_session_hook_entry`,THEN 三次相邻 bash 调用产生**同一 owner ID**(通过 proc cmdline 探测 opencode server PID,稳定锚点)
- GIVEN bash 工具调用**有** `OPENCODE_SESSION_ID` env var (OpenCode 平台注入),WHEN 调用任何 hook,THEN env var 优先于 fallback
- GIVEN fallback 三种来源 (env / proc-cmdline / shell-pid),WHEN 调用 `rddf_session_hook_entry`,THEN session 的 `owner_kind` 字段标记 fallback 来源 (新字段,P3 提议)

## 技术约束

- 探测 `/proc/<shell-ppid>/cmdline` 必须限制搜索深度 (<=5 层),避免意外追溯到 init (PID 1) 或 launchd
- 仅当 cmdline 包含 "opencode" 子串时采纳为 opencode PID;否则 fallback 到 shell PID
- 改动必须向后兼容:`OPENCODE_SESSION_ID` 已显式设置时优先 (现有 contract 不变)

## 验收标准

- [ ] 同窗口相邻 3 次 bash 调用 `rddf_session_hook_entry` 产生同一 owner ID
- [ ] bash 调用前注入 `OPENCODE_SESSION_ID=<uuid>` 时,owner == 该 uuid (env 优先)
- [ ] 不含 "opencode" 的 cmdline 路径 fallback 到 shell PID,行为不退化
- [ ] 探测成功后写 `~/.cache/rddf-session-owner`;下次 env var 缺失时优先读文件 (TTL 1h)
- [ ] 跨 worktree 验证: 在主仓与 `.rddf/wt/<name>/` 下连续调用 `rddf_session_hook_entry`,owner ID 保持一致 (worktree 不影响 OPENCODE 进程级 owner 探测)
- [ ] 跨 plan-step 验证: 同一窗口内连续 6 个 ship 阶段子步骤 (plan/execute/review/archive/cleanup/ship-done) 调用 entry + close,owner ID 全程一致
- [ ] 旧 sessions.json 兼容: 加载含 `owner_opencode_session_id="my-eci-group_2044384"` (无 owner_meta) 的 v1 sessions 时不破坏,旧 session 保留原 owner (不强制回填 owner_meta)
- [ ] 单元测试覆盖三种 fallback 路径 + cache file 读写
- [ ] bats 集成测试通过