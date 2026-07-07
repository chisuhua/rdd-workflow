## Context

当前 LoopEngine (`skills/loop_engine.py`) 仅支持**手动触发**的执行模式：调用 `LoopEngine.run(goal_predicate)` 后同步运行 scan-detect-act 周期直到目标达成或安全限制触发。ADR-0009 预定了调度触发（cron）和事件驱动触发（文件变更、git 事件、webhook）的能力，但在 v2.0 发布时被推迟。

LoopEngine 的现有架构已经具备集成触发器的条件：
- `detectors.py` 的 8 个内置检测器通过统一的 `Detector.detect(state) → DetectionResult` 接口运行
- `actions.py` 的动作系统通过 `match_actions(detection_results)` 分发
- `StateVector` / `EventLog` 提供持久化状态和审计日志
- `ConfigParser` 从 `config.yaml` 加载运行时配置

本设计将触发器建模为 LoopEngine 的**外部唤醒源**：触发器不修改 LoopEngine 的核心循环逻辑，而是通过一个 `TriggerManager` 中间层在触发事件到达时调用 `LoopEngine.run()`。

## Goals / Non-Goals

**Goals:**
- Cron 表达式调度：支持标准 5 字段 cron 语法（`min hour dom month dow`），定期唤醒 LoopEngine
- 事件驱动触发：文件系统变更（inotify/polling）、git 事件（branch/tag）、webhook（HTTP POST）
- 触发器注册与去重：集中式注册表，支持重叠检测，同事件不重复触发
- LoopEngine 集成：触发器作为检测器输入源之一，复用 `match_actions` 分发
- 安全护栏：每触发器速率限制、手动关闭（`--trigger-off`）、崩溃恢复持久化

**Non-Goals:**
- 不支持分布式触发（单机范围）
- 不实现完整的 cron 守护进程（不替换系统 cron/systemd timer）
- 不实现 webhook 服务器的 TLS/认证（安全留给反向代理）
- 不修改 LoopEngine 核心循环逻辑（`run()` 签名和内部状态机不变）

## Decisions

### Decision 1: Trigger 作为独立模块，不侵入 LoopEngine 核心

**选择**: 新建 `skills/_lib/triggers.py` 模块，包含 `TriggerManager` 类。在 `loop_engine.py` 的 `scan_state` 阶段，`TriggerManager` 作为额外检测器源注入。

**备选**: 直接在 LoopEngine 中增加 `run_forever()` / `run_scheduled()` 方法

**理由**:
- LoopEngine.run() 保持同步语义，不引入事件循环
- 触发器逻辑独立可测试（不依赖 LoopEngine 完整状态）
- 未来可替换为外部调度器（systemd timer / k8s CronJob）而不影响 LoopEngine

### Decision 2: Cron 解析使用 `croniter` 库

**选择**: 引入 `croniter`（纯 Python，无 C 扩展依赖）作为 cron 表达式解析库

**备选**: 自行实现 cron 解析器

**理由**:
- cron 边界情况多（月末、闰年、时区），自研成本高
- `croniter` 是 Python cron 解析的事实标准（3000+ stars，活跃维护）
- 纯 Python 无系统依赖，与现有 `pip install` 流程兼容
- 添加到 `requirements.txt` 即可

### Decision 3: 触发注册表存储在 `.rddf/state/triggers.json`

**选择**: JSON 文件持久化，通过 `StateVector` 的原子写入机制管理

**备选**: SQLite 或独立配置文件

**理由**:
- 与现有状态管理一致（state-vector.json, iteration.json, roadmap-state.json）
- JSON 人类可读，方便调试
- 避免引入新依赖（SQLite driver）
- 触发器数量预计 < 20，JSON 性能足够

### Decision 4: 文件监听使用 polling 模式（非 inotify）

**选择**: 使用 `os.scandir` + 时间戳比较的轮询模式（默认 30s 间隔，可配置）

**备选**: `watchdog` 库（基于 inotify/FSEvents/ReadDirectoryChangesW）

**理由**:
- 避免 C 扩展依赖和跨平台兼容性问题
- 触发器场景下 30s 延迟可接受（非实时性要求）
- polling 实现简单（< 50 行），易于调试
- 可在后续 ADR 中升级为 `watchdog` 集成

### Decision 5: Webhook 使用内置 `http.server` + 最小 Flask-like 路由

**选择**: 基于 Python 标准库 `http.server.HTTPServer` 实现最小 webhook 接收器，监听可配置端口（默认 9090）

**备选**: 引入 Flask / FastAPI 作为依赖

**理由**:
- 零外部依赖（只用 stdlib）
- webhook 接收器功能简单：接收 POST → 验证 → 触发
- 认证/HTTPS 留给反向代理（nginx/caddy）
- 如果未来需求增长，可升级为 FastAPI 集成（非破坏性变更）

### Decision 6: 速率限制使用 token bucket 算法

**选择**: 每个触发器维护一个 token bucket（capacity=rate_limit, refill_rate=1/interval）。bucket 状态持久化到 triggers.json。

**备选**: 固定窗口计数器

**理由**:
- Token bucket 允许短时突发（burst），同时限制长期平均速率
- 比固定窗口更平滑（无边界效应）
- 持久化支持崩溃恢复

## Risks / Trade-offs

- **[Risk] 文件轮询可能遗漏快速连续变更** → Mitigation: 记录最后检测时间戳，每次扫描比较 mtime；可配置为更短间隔
- **[Risk] Webhook 接收器在后台线程运行，与 LoopEngine 的同步模型冲突** → Mitigation: webhook 接收器通过线程安全队列传递事件，TriggerManager 在主线程的 scan_state 中消费
- **[Risk] croniter 时区处理** → Mitigation: 所有 cron 表达式使用 UTC，文档注明
- **[Trade-off] Polling vs inotify** → Polling 简单但延迟高（30s）；inotify 实时但更复杂。选择 polling 作为 MVP，后续可配置切换