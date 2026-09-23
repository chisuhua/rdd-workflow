# add-stage-guide-e2e-cross-process-coverage
**优先级**: P1


## Why

### 架构承诺与测试覆盖 gap

feat-guide-orchestrator-session-event-bus（commit f5eb49c → 5ed6378 → 3519bd4）的核心创新是引入**文件级事件总线 + per-owner offset 轮询**作为多 OpenCode 窗口协同的载体：

| 架构组件 | 实现位置 | e2e 覆盖 | 内部覆盖 | 真跨进程？ |
|---------|----------|---------|---------|-----------|
| `stage_guide` rddf-session kind | `_commands.py:89`, `_types.py:45` | ❌ 0 | ✅ 单元 | ❌ |
| `.rddf/state/events.jsonl` 事件总线 | `events_log.py:1-254` | ❌ 0 | ✅ 单元 | ❌ |
| `last_seen_offset` per-owner 轮询 | `sessions_schema.json:68` | ❌ 0 | ⚠️ 单进程 | ❌ |
| `rddf_session_hook_guide_entry/close` | `rddf_session_hooks.sh:405, 453` | ❌ 0 | ✅ 集成 | ❌ |
| `fcntl.flock` 跨进程互斥 | `events_log.py:120-127` | ❌ 0 | ⚠️ 仅 EventsLog 单元 | ❌ |
| H7 全局 stage_guide 单例 | `_commands.py:81-94` | ❌ 0 | ⚠️ 同进程 | ❌ |
| AC-15 archive_events → last_seen_offset=0 | `events_log.py:255-294` | ❌ 0 | ✅ 单元 | ❌ |

**关键风险**：fcntl.flock 在 POSIX 文件锁语义下，**只有真多进程**才会触发 LOCK_EX 阻塞；单进程测试永远测不到锁竞争。`test_no_event_log_jsonl_alias` 等 anti-pattern guard 守卫文件存在，但守卫不了"两个进程真的同时写"。

### 设计目标

按 rdd-workflow-e2e 现有 fixture 模式（`setup_fake_project` + `invoke_*` helper）补一组**真跨进程** e2e case，覆盖 feat-guide-orchestrator-session-event-bus 核心架构承诺。每个 case 用 `subprocess.Popen` 或 `bash &` 派生独立进程，验证 fcntl.flock 互斥、offset 时序推进、singleton 拦截、crash 残留清理等真跨进程行为。

## What Changes

**In Scope**:

- 在 `rdd-workflow-e2e/tests/integration/` 新建 `test_stage_guide_cross_process_e2e.bats`
- 6 个真跨进程 case（详见 ## Acceptance）
- 共享 helper：`tests/_lib/test_stage_guide_cross_process_fixture.bash`（spawn 子进程 + 读 events.jsonl + 读 sessions.json）
- 同步更新 `rdd-workflow-e2e/README.md` 测试套件表 + 增加 KNOWN_FAILURES（如有环境限制 skip）
- ❌ 不修改 rdd-workflow 生产代码（仅添加测试，验证现有实现正确性）
- ❌ 不修改 rdd-workflow-e2e 现有 36 个 case
- ❌ 不引入新依赖（用 Python stdlib `subprocess` + `fcntl` + `os.fork`）
- ❌ 不实现真实 OpenCode 模拟（用 `$BASHPID` + `OWNER_<pid>` 区分 owner）
- ❌ 不动 rdd-workflow 内部 tests（test_guide_cross_container.bats 保持单进程视角，与 e2e 互补）

**Out of Scope**:

- (no items specified)

## Capabilities

- 每个 case 必须派生**真子进程**（`subprocess.Popen` 或 `bash &`），不接受同进程多 RddfSessionCoordinator 实例模拟
- 每个 case 必须清空 `$BATS_TEST_TMPDIR/.rddf/state/`（避免跨 case 污染）
- 每个 case 必须用 `wait` 收集子进程退出码，非 0 即 fail
- 跨进程 case 必须设 `RDDF_GUIDE_SESSION_ENABLED=yes`（覆盖默认禁用）以触发 hook entry/close
- 必须保留现有 KNOWN_FAILURES 不破坏（仅追加本提案新增 known failure，如真有）
- 不引入新 Python 依赖（用 stdlib subprocess / fcntl / os / signal）
- 不修改 rdd-workflow 仓的任何 tracked 文件（仅 e2e 仓 PR）
- 不为单个 case 修改 rdd-workflow 生产代码以"让测试通过"（如发现 bug，应走单独 improvement 提案修代码，本提案先记录"待修"）
- 不使用 Docker / Podman / chroot 等容器隔离（用 PID + 文件锁就够，引入容器是过度工程）
- 不模拟 OpenCode 真实行为（用 `$BASHPID` + `OWNER_$pid` 作为 owner 标识足够）

## Impact

- ### 风险

- **CI 耗时增加**：6 个 case 每个 spawn 2-3 个子进程，每个 case 估计 5-15s，套件总耗时 +30-90s（rdd-workflow-e2e 当前 ~20s，扩展后 ~50-110s）
- **平台差异**：macOS flock 行为可能与 Linux 不同（已知 macOS 10.13+ flock fcntl 兼容但行为细节差异），需在 KNOWN_FAILURES 标注或用 `os.open(... O_EXLOCK)`（BSD 风格）做 fallback
- **flaky 风险**：进程调度 + fcntl 时序在 CI 容器内可能 flaky。AC-1/AC-2 这种并发 case 需要多次重试 + 宽容阈值

### 收益

- 验证 feat-guide-orchestrator-session-event-bus 核心架构承诺，**消除 silent skip 风险**
- 为未来 rdd-workflow 跨窗口 feature 提供 fixture 模板
- 提升用户跨 OpenCode 窗口协同的稳定性（真跨进程 race condition 才能暴露的问题）

### 依赖

- 上游：`feat-guide-orchestrator-session-event-bus` 已 ship（本仓 branch `feat/guide-orchestrator-session-event-bus` 含 6 commits）
- 同仓：`tests/integration/test_guide_cross_container.bats` 已存在（单进程视角），本提案与之互补
- 工具：`subprocess` (Python stdlib), `fcntl` (Python stdlib), `bash &` + `wait` (bash builtin)

## Acceptance

- [ ] **AC-1 fcntl 并发写**：2 个 Python 子进程同时 `append_event` 同一 events.jsonl（每进程写 50 行），合并后 events.jsonl 共 100 行且无重复 event_id
- [ ] **AC-2 offset 轮询时序**：进程 A 持续 append_event（每 100ms 写 1 行，运行 2s 共 20 行）；进程 B 用 `read_since(offset=0)` 在 2s 内轮询 5 次，每次 offset 单调推进，最终 offset 推进 ≥ 10（具体阈值由 rdd-builder 设计）
- [ ] **AC-3 crash 残留恢复**：进程 A 创建 stage_guide session + 写 5 个事件 → `kill -9` A → 进程 B 启动后读 sessions.json 看到 A 的 active stage_guide + 读 events.jsonl 从 offset=0 看到全部 5 个事件
- [ ] **AC-4 H7 全局单例**：2 个 owner（OWNER_A / OWNER_B）同时尝试 `create_session(kind="stage_guide")`，第二个返回 ConflictError，sessions.json 中只有 1 个 active stage_guide
- [ ] **AC-5 自动归档重置**：进程写满 events.jsonl 到 50MB+（或临时调低 `RDDF_EVENTS_LOG_MAX_SIZE_MB=1` 触发归档）→ 所有 active stage_guide 的 `goal.last_seen_offset == 0`
- [ ] **AC-6 guide_entry 持久化**：bash subshell `bash guide_entry.sh &` 后 `kill -1` 父 subshell（触发 EXIT trap 调 guide_close）→ sessions.json 中 stage_guide 标记 `state="completed"`；若 subshell 异常退出（`kill -9` 父）→ stage_guide 仍为 active（hook entry/close 不破坏长生命周期）
- [ ] **AC-7 文档同步**：`rdd-workflow-e2e/README.md` 测试套件表更新（36 → 42 cases）+ 新 case 描述准确
- [ ] **AC-8 回归门**：`bash tests/scripts/report_regression.sh` 在 rdd-workflow-e2e 跑通（0 新增失败）
- [ ] **AC-9 主仓回归**：本仓 `./test.sh --quick` 通过（确认本提案不破坏 rdd-workflow 测试）

