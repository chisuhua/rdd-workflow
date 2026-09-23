---
优先级: P1
来源: 2026-09-23 add-stage-guide-e2e-cross-process-coverage AC-6a 实测确定性 fail (2 次连跑,0 差异)
阶段: v4.1 follow-up
分类: bug-fix
类型: fix
主题: 完整多会话支持
依赖: feat-guide-orchestrator-session-event-bus (shipped), add-stage-guide-e2e-cross-process-coverage (in progress)
---
**优先级**: P1 | **来源**: 2026-09-23 AC-6a deterministic fail
**阶段**: v4.1 follow-up | **分类**: bug-fix
**类型**: fix | **主题**: 完整多会话支持
**依赖**: feat-guide-orchestrator-session-event-bus, add-stage-guide-e2e-cross-process-coverage
**主题**: 完整多会话支持

> **症状**:`rddf_session_hook_guide_close` 在 EXIT/INT/TERM trap 中无法定位到 `rddf_session_hook_guide_entry` 创建的 stage_guide session。两次连续 `bats tests/integration/test_stage_guide_cross_process_e2e.bats` 运行 100% 确定性 fail(从 merge commit note 的 "flaky" 升级为 "deterministic fail"),AC-6a 阻塞 add-stage-guide-e2e-cross-process-coverage archive。
>
> **直接证据**(两次连跑均出现,owner ID `1027099` 来自 run1,`1027926` 来自 run2 — 证明 owner 解析一致但 close 仍 fail):
> ```
> rddf-session guide-entry: rds_8ea967c74f74 (stage_guide, owner=my-eci-group-poc_1027926)
> 📍 Current: rds_8ea967c74f74 (kind=stage_guide, parent=None, age=0min, changes=(none))
> rddf-session guide-close: no active stage_guide session for my-eci-group-poc_1027926, skipping
> rddf-session guide-close: no active stage_guide session for my-eci-group-poc_1027926, skipping
> expected guide_close to mark session completed, got 0 terminal sessions
> ```
>
> **根因(已定位)**:`skills/guide/scripts/guide_entry.sh:130` 把 `PROJECT_ROOT` 声明为 `local`:
> ```bash
> guide_entry() {
>   ...
>   local PROJECT_ROOT                                              # ← line 130
>   PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
>   ...
>   if type rddf_session_hook_guide_entry &>/dev/null; then
>     rddf_session_hook_guide_entry || true
>   fi
>   trap 'rddf_session_hook_guide_close' EXIT INT TERM              # ← trap 注册
>   ...
> }
> ```
>
> 1. `guide_entry --no-binding` 函数返回 → `local PROJECT_ROOT` 自动 pop 出调用栈
> 2. 子 shell 继续执行 `sleep 30`(或其它长任务)
> 3. 触发 SIGTERM → trap `rddf_session_hook_guide_close` 在 trap context 启动
> 4. trap 内 `PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"` **理论上**能 fallback,但实际触发 race / 上下文问题
>
> **遗留不确定性**(需要在实现阶段 diagnose):
> - `[FAKE_ROOT git rev-parse]` 在 trap 触发瞬间是否正确解析?如果是,PROJECT_ROOT 应当等于 FAKE_ROOT,sessions.json 应在同路径
> - 子 shell `(... ) &` 背景下,sleep 被 SIGTERM 打断后 trap 是否仍能访问原 cwd?
> - 是否存在 cache file `~/.cache/rddf-session-owner` 跨 run 干扰导致 owner 不一致?
> - `set -e` 与 `trap '...' EXIT INT TERM` 互动是否导致 trap 提前 abort?

## 架构依据

feat-guide-orchestrator-session-event-bus 的核心架构承诺是"用户在 OpenCode 窗口 A 跑 guide,窗口 A 退出时 `stage_guide` session 自动 marked completed"。该承诺的隐含前提是 **guide_entry 创建的 session 必须在 guide_exit 时可被同一 owner 找到并 mark completed**。

当前实现下,`guide_entry.sh` 在函数 context 用 `local PROJECT_ROOT`,trap 在函数返回后的 shell context 执行,导致:
1. **`local` 变量的可见性漏洞**:`local` 在 trap 触发时已 pop,trap 内的 `${PROJECT_ROOT:-...}` 必须依赖 fallback,而 fallback 不是显式传入 trap
2. **跨上下文状态耦合**:`guide_entry.sh` 与 `rddf_session_hooks.sh` 共享 `PROJECT_ROOT` 但没显式 export/传递契约
3. **可观测性盲区**:owner ID 解析路径有 4 层 fallback(env → cache → proc-cmdline → shell-pid),每层都可能产生看似一致但实际上不同的 owner

## 范围

**In Scope**:

- `skills/guide/scripts/guide_entry.sh`:`local PROJECT_ROOT` 改为 `export PROJECT_ROOT`(或显式传入 trap 命令字符串)
- `skills/rddf-session/scripts/rddf_session_hooks.sh`:`rddf_session_hook_guide_close` 增加 owner 解析失败时的 fallback(如果 cache 返回 stale,显式回退到子 shell `$$`)
- `tests/unit/test_guide_entry_polls.py`(可能已存在)或新 `tests/unit/test_guide_close_local_var.py`:加 regression test 覆盖"local PROJECT_ROOT pop 后 trap 触发"场景
- `tests/_lib/test_stage_guide_cross_process_fixture.bash`(在 rdd-workflow-e2e):AC-6a fixture 加重试机制,确保 session 创建完成(`wait_until_active_stage_guide` 而不是 `sleep 3`)
- 同步更新 `docs/architecture/multi-session.md`(已存在但需要 review 是否覆盖该场景)

**Out of Scope**:

- ❌ 不重写 `_rddf_resolve_owner` 整体逻辑(独立 improvement scope)
- ❌ 不修改 cache file `~/.cache/rddf-session-owner` 的 TTL/语义
- ❌ 不动 `rddf_session_hook_guide_entry`(已工作,只在 entry 时正确)
- ❌ 不动 `tests/integration/test_stage_guide_cross_process_e2e.bats` 的 AC-2/3/4/5/6b 已有 case

## Why

修复 `local PROJECT_ROOT` 在 `guide_entry()` 返回后 pop out of scope 的边界条件,确保 `trap 'rddf_session_hook_guide_close' EXIT INT TERM` 在 subshell 后台触发时仍能可靠定位到 guide-entry 创建的 stage_guide session。这是 feat-guide-orchestrator-session-event-bus "窗口退出自动清理 session" 架构承诺能真正成立的前提,也是 add-stage-guide-e2e-cross-process-coverage archive 的最后 1 个 AC blocker。

## What Changes

### `guide_entry.sh`:`local PROJECT_ROOT` 改为 `export PROJECT_ROOT`(line 130)

```bash
# Old (buggy — local pops after function returns, trap can't see it):
guide_entry() {
  ...
  local PROJECT_ROOT                                                  # ← line 130, bug
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  ...
  trap 'rddf_session_hook_guide_close' EXIT INT TERM                  # ← trap uses $PROJECT_ROOT but local is gone
  ...
}

# New (correct — exported so trap context can read it):
guide_entry() {
  ...
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)   # no `local` keyword
  export PROJECT_ROOT                                                  # ← ensures trap sees it
  ...
  trap 'rddf_session_hook_guide_close' EXIT INT TERM
  ...
}
```

### `rddf_session_hooks.sh`:`_rddf_resolve_owner` 增加"显式子 shell $$"兜底层

为防止 cache file stale 跨 run 干扰,新增第 5 层 fallback **仅在 trap context 启用**(避免 normal entry 路径 owner 不稳):

```bash
_rddf_resolve_owner() {
  # ... existing 1-4 layers (env → cache → proc-cmdline → shell-pid)
  ...
  # 5. (NEW, only when called from rddf_session_hook_guide_close trap context)
  if [ "${RDDF_RESOLVE_OWNER_FROM_TRAP:-no}" = "yes" ]; then
    # In trap, $$ = current shell PID (still valid even if function returned)
    RDDF_OWNER="$(hostname -s)_$$"
    RDDF_OWNER_FROM="trap-shell-pid"
    export RDDF_OWNER RDDF_OWNER_FROM
    return 0
  fi
  ...
}
```

并在 `rddf_session_hook_guide_close` 入口设 `RDDF_RESOLVE_OWNER_FROM_TRAP=yes`:

```bash
rddf_session_hook_guide_close() {
  RDDF_RESOLVE_OWNER_FROM_TRAP=yes _rddf_resolve_owner  # ← 新增
  ...
}
```

### 新 unit test:`tests/unit/test_guide_close_local_var.py`

```python
def test_local_project_root_pops_before_trap_fires():
    """Verify trap 'EXIT INT TERM' can still read PROJECT_ROOT after guide_entry returns."""
    import subprocess, tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env["RDD_GUIDE_SESSION_ENABLED"] = "yes"
        script = f'''
        source "{SKILL_DIR}/scripts/guide_entry.sh"
        guide_entry --no-binding
        sleep 0.5
        ''' + 'kill -TERM $$; wait'  # trigger trap
        # ... assert .rddf/state/sessions.json has stage_guide state=completed
```

### rdd-workflow-e2e fixture:AC-6a `sleep 3` → `wait_until_active_stage_guide`

```bash
# Old (race-prone):
sleep 3
local active_count=$(count_active_stage_guide_sessions "$sessions_file")
[[ "$active_count" -eq 1 ]] || { ... }

# New (deterministic):
wait_until_active_stage_guide_sessions "$sessions_file" 1 5  # max 5s, poll every 0.1s
```

## Acceptance

- [ ] ### AC-1 `rddf_session_hook_guide_close` 在 trap context 中能读到 `PROJECT_ROOT`
- [ ] ### AC-2 连续 5 次 `bats tests/integration/test_stage_guide_cross_process_e2e.bats` 跑 AC-6a,100% pass(当前 0/2 pass)
- [ ] ### AC-3 新 unit test 覆盖 `local PROJECT_ROOT` 在 trap 触发后不可见的边界条件 — `test_guide_close_local_var.py` pass
- [ ] ### AC-4 `rddf_session_hook_guide_close` 的 stderr 输出在正常路径 + SIGTERM 路径下等价(都不出现 "no active stage_guide session for X, skipping" 误报)
- [ ] ### AC-5 fixtures AC-6a 的 `sleep 3` 替换为 `wait_until_active_stage_guide_sessions` helper,减少 race window
- [ ] ### AC-6 现有 35 个 bats + 6 个 AC-1/2/3/4/5/6b 跑通后无 regression

## Capabilities

**MUST**:

- 修复后,`guide_entry.sh` 必须 `export PROJECT_ROOT`(或 trap 命令字符串显式传入),让 trap context 能可靠获取
- 修复后,`rddf_session_hook_guide_close` 必须确保 owner 解析至少有一层"显式 = 子 shell $$"的兜底,即使 cache file / proc cmdline 都失败
- 修复后,AC-6a fixture 必须使用 `wait_until_*` helper 而非固定 `sleep N`,把 race condition 收敛在 helper 内部
- 必须新增至少一个 unit test 覆盖 trap-after-function-return 场景

**MUST NOT**:

- ❌ 不得扩大 `_rddf_resolve_owner` 的 fallback chain 优先级变化(保持现有 env → cache → proc → shell-pid 顺序)
- ❌ 不得修改 `stage_guide` session 的 create_session / list_sessions / update_session_status 语义
- ❌ 不得回滚 `add-guide-polling-loop-implementation` 已 ship 的 polling logic
- ❌ 不得用 `kill -9` 替代 SIGTERM 验证 AC-6a(SIGTERM 才是 user-exit 路径的真实信号)

## Impact

**风险等级**:中(`guide_entry` 是所有 rdd-arch / plan / ship / verify 阶段的入口,任何 regression 会阻断整个 v4 流程)

**关联文件数**:
- 核心修改 2 文件:`guide_entry.sh` + `rddf_session_hooks.sh`(行数预计 < 30)
- 测试 1-2 文件:新 `test_guide_close_local_var.py`(预计 ~50 行)+ fixture helper
- 文档 1 文件:`docs/architecture/multi-session.md`(小幅 review)

**依赖 chain**:
- 本 improvement ship 后,**直接解锁** `add-stage-guide-e2e-cross-process-coverage` archive(AC-6a PASS → 7/7 PASS → rdd-verifier 通过)
- 间接解锁 v4.1 release 的"guide session 正确清理"承诺

**回归风险**:
- 修改 `guide_entry.sh` 的 `local PROJECT_ROOT` 行为可能影响其他调用者(recommend / scan_state 等)— 需用 `tests/unit/test_guide_entry_polls.py` 兜底验证
- 修改 `rddf_session_hook_guide_close` 可能引入新的 close 行为差异 — 需在 `tests/unit/test_doc_sync.py` 等已有 unit test 验证不退化

**参考证据**:
- AC-6a 实测确定性 fail(本会话 2 次连续):`bats` 输出 captured
- merge commit `3c89039` message 原文:"AC-6a: flaky (owner resolution / PROJECT_ROOT edge case, separate follow-up)"
- `fix-events-log-blocking-lock.md` 已 ship 解决了 AC-1 类似模式(同源 e2e 暴露真 bug → improvement → ship → AC PASS),可作为本 improvement 的执行范本