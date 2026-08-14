# preserve-orchestrator-command-stdout

## Why

- ADR-0027 §1.0.1：`rddf orchestrate subprocess` 包装任意子脚本进行 trace 捕获；2026-08-13 起默认 ON，任何 phase 入口的子命令都经过 orchestrator 包装。
- ADR-0027 §9：CI 环境抑制 `auto_submit`，但未约束 orchestrator 对子进程 stdout/stderr 的捕获行为。
- ADR-0026：内部元数据命名空间约定 — orchestrator trace 字段需遵循统一 blockquote 元数据规范。
- 仓库现状：`skills/_lib/orchestrator_entry.sh` 已实现默认 ON 包装，但 capture 机制未对用户透传做保护。
- Oracle 审查发现：dogfooding 阶段用户反馈"跑 phase 时看不到自己命令的实时输出"，与 trace 完整性需求冲突。

核心原则：trace 完整性 ≠ 用户命令输出可观测性。orchestrator 必须支持**并行双写**（stdout 透传 + 异步 tee 到文件），而非互斥 capture。

## What Changes

**In Scope**:

1. **stdout/stderr 透传**：`rddf orchestrate subprocess` 包装时，主进程的 stdout/stderr 默认透传到调用者终端，不被缓冲或丢弃。
2. **异步 tee 写 trace**：后台 reader 线程/进程异步复制 stdout/stderr 到 trace 文件，主流程不阻塞。
3. **PIPE 缓冲保护**：对长输出场景启用 O_NONBLOCK 或动态扩大 buffer，避免 reader 滞后导致子进程阻塞。
4. **失败降级**：reader 线程崩溃时主流程继续；trace 文件部分写入也允许（append-only，失败可截断）。
5. **CI 兼容**：CI runner 的非交互 stdout 行为不被破坏（透传仍生效）。
6. **可观测字段**：trace 文件新增 `stdout_capture_mode: tee | capture | passthrough` 字段，标记本次运行的输出策略。
7. **opt-out 逃生口**：`RDDF_ORCHESTRATOR_CAPTURE=passthrough|capture|tee` env var 允许用户临时关闭异步写或强制 capture，用于 trace 完整性严格场景。

**Out of Scope**:

- orchestrator 自身的 stdout（那是另一个问题）
- trace 文件格式 schema 升级（走 ADR-0027 既有 trace schema）
- 跨平台 tee 行为差异（优先 Linux/macOS，Windows 留 TODO）
- 实时输出着色/分页
- 改 `rddf orchestrate show` 的输出格式

## Capabilities

- 用户在终端跑 `rddf orchestrate subprocess <cmd>` 时能实时看到 `<cmd>` 的 stdout 输出
- 后台 reader 线程异步复制 stdout/stderr 到 `.rddf/state/trace/<phase>.json`
- 长输出（≥10MB）通过 O_NONBLOCK 或动态 buffer 扩容避免阻塞
- `RDDF_ORCHESTRATOR_CAPTURE` env var 支持 `tee` / `capture` / `passthrough` 三模式切换
- trace JSON 中记录 `stdout_capture_mode` 字段（事后可审计）
- reader 线程崩溃时主 phase 不受影响，trace 标记 `reader_died: true`

## Impact

- 不修改 ADR-0027 §1.0.1 既有的 subprocess 包装入口契约（向后兼容）
- 不让 orchestrator 自身的 stdout 干预子进程透传（避免递归 capture）
- trace 文件超阈值（默认 100MB）时 rotate 到 `.1`/`.2` 后缀，避免单文件过大
- `RDDF_ORCHESTRATOR_TRACE_MAX_BYTES` env var 控制 rotate 阈值

## Acceptance

- [ ] 新增 `tests/unit/test_orchestrator_tee.py` ≥10 cases，覆盖 `tee|capture|passthrough` 三模式切换、reader 线程崩溃降级、buffer 满不阻塞、env var 解析
- [ ] 新增 `tests/integration/test_orchestrator_stdout_passthrough.bats` ≥5 cases，覆盖真实长输出场景（1MB/100MB）、CI 环境模拟、reader OOM 模拟
- [ ] 手动验收：本地跑 `rddf orchestrate subprocess bash -c 'for i in $(seq 100000); do echo "line $i"; done'`，终端实时看到所有 line，`cat .rddf/state/trace/<phase>.json | jq .stdout_capture_mode` 输出 `tee`
- [ ] 手动验收：设置 `RDDF_ORCHESTRATOR_CAPTURE=passthrough` 后跑同一命令，无 trace 文件生成，终端输出正常
- [ ] `./test.sh --full --regression` 全绿，无新增失败（允许 `tests/KNOWN_FAILURES.txt` 中已记录的失败）
- [ ] 文档：`docs/architecture/extension-points.md` 新增"orchestrator 输出策略"小节；`CHANGELOG.md` Unreleased 段记录本提案
- [ ] CI：`CI=true rddf orchestrate subprocess bash -c 'echo "to CI log"'` 在 GitHub Actions runner 日志可见 `to CI log`
- [ ] 性能：reader 线程在 10MB 输出场景不增加 >5% 总耗时（手动 benchmark，对比 capture 模式 baseline；具体测量方式由 review 阶段确认 harness）