# 提案池（待架构讨论）

> design 阶段输入。guide-design 逐个审查，批准后添加到 `improvement-approved.md`。
>
> **生命周期**: 提案从此文件创建 → design 审查 → 批准/拒绝/延迟 → 移至 `improvement-approved.md` 等待实施 → 实施后归档。
> **自动清理**: 提案被批准或实施后，`sync_suggestions()` 会自动从本表移除该行（不再停留）。
> **手动审计**: 发现过期条目时，运行 `skill_use("guide")` 的审计功能自动清理。
> **依赖记录**: `fix-orphan-hub-gates-wiring`（P1）阻塞于 `fix-adr-0031-safety-gate-substantiation`（P0）— audit log 须先非空，`check_cross_repo_approvals` 才能验证。

| 提案 | 优先级 | 来源 | 添加时间 | 状态 |
|------|--------|------|----------|------|
| [bypass-audit-mechanism](.rddf/improvements/bypass-audit-mechanism.md) | P2 | 2026-08-26 流程设计 review | 2026-08-26 | 延迟 (2026-08-28, 维持 v3.2 deferred 决策)  |
| [add-objective-evidence-v02-llm-synthesis](.rddf/improvements/add-objective-evidence-v02-llm-synthesis.md) | P2 | 2026-09-22 用户发起 — objective evidence v0.1 复盘 + 跨 repo 场景语义复杂度缺口补位 | 2026-09-22 | 待审查 |
| [add-stage-guide-e2e-cross-process-coverage](.rddf/improvements/add-stage-guide-e2e-cross-process-coverage.md) | P1 | 2026-09-23 review of feat-guide-orchestrator-session-event-bus — 核心架构承诺（跨 OpenCode 进程文件轮询）由 0 个 e2e test 验证；现有 test_guide_cross_container.bats 名为 cross 实为单进程模拟，存在 false confidence 风险 | 2026-09-23 | 待审查 |
| [fix-events-log-blocking-lock](.rddf/improvements/fix-events-log-blocking-lock.md) | P0 | 2026-09-23 add-stage-guide-e2e-cross-process-coverage AC-1 实测 — `events_log.py` 用 `fcntl.flock(LOCK_EX \| LOCK_NB)` 在并发写时抛 BlockingIOError 而非序列化，导致多进程并发 append_event 时第二个进程全部事件丢失。feat-guide-orchestrator-session-event-bus 跨进程架构实际不可用 | 2026-09-23 | 待审查 |
| [add-guide-polling-loop-implementation](.rddf/improvements/add-guide-polling-loop-implementation.md) | P0 | 2026-09-23 audit of feat-guide-orchestrator-session-event-bus — 8 个核心发现中 5 个 P0（guide_entry.sh 缺 polling 循环 + RddfSessionCoordinator 无 update_last_seen_offset API + rdd-planner/builder/verifier/quick SKILL.md 0 hook 调用）。架构承诺"窗口 A 跑 guide 能看到窗口 B 跑 rdd-builder 的进度"在生产代码层面完全未落地 | 2026-09-23 | 待审查 |
| [fix-guide-close-owner-resolution](.rddf/improvements/fix-guide-close-owner-resolution.md) | P1 | 2026-09-23 add-stage-guide-e2e-cross-process-coverage AC-6a 实测确定性 fail (2 次连跑 0/2) — `guide_entry.sh:130` 把 `PROJECT_ROOT` 声明为 `local`，函数返回后自动 pop out of scope，导致 trap `'EXIT INT TERM'` 在 subshell 后台触发时无法可靠定位 session。feat-guide-orchestrator-session-event-bus"窗口退出自动清理 stage_guide session"架构承诺部分不可用，add-stage-guide-e2e-cross-process-coverage archive 最后 1 个 AC blocker | 2026-09-23 | 待审查 |
| [complete-guide-orchestrator-flow](.rddf/improvements/complete-guide-orchestrator-flow.md) | P0 | 2026-09-24 用户对"guide 作为唯一入口"最小用法的复盘 — ADR-0055 (v4.1) 架构层已落地但流程层契约未形式化,**根因**: `_VALID_KINDS` 缺 `stage_builder/verify/quick` + hook 只 catch ConflictError → `RddfSessionError` 静默(SKILL.md 强制 hook 也无效),workflow_synthesizer 不消费 events.jsonl 导致 menu 只看 sessions.json 看不到过程,guide_entry 无 background polling 导致多窗口必须重新调 guide 才看到进度。**W2.0+W2.1+W2.2+W2.3+W2.5 已 ship + archive 2026-09-24** (70 新测试) | 2026-09-24 | **已 ship** |
| [fix-33-handlers-project-root-anti-pattern](.rddf/improvements/fix-33-handlers-project-root-anti-pattern.md) | P2 | 2026-09-25 fix-cmd-help-handling (P1, 已 ship commit 200efdd) 实施审计 — 32 个 `_lib/cli/*.py` handler 文件 (实际计数,提案中称"33"为估数) 重复使用 `os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()` 反模式 (~36 处 occurrences),而 `_lib/cli/__main__.py::resolve_project_root()` (per ADR-0033 submodule-aware git 探测) 已存在但**无 handler 使用**。fix-cmd-help-handling 是 symptom-level fix (dispatcher-level `--help` 拦截);此 improvement 是 root-cause 层 refactor | 2026-09-25 | 待审查 |

