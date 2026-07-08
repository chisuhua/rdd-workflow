## 1. 触发器基础设施

- [ ] 1.1 新建 `skills/_lib/triggers.py`：定义 `Trigger` dataclass（id, type, config, rate_limit, enabled），`TriggerManager` 类（register, unregister, get_pending, deduplicate）
- [ ] 1.2 新建 `skills/_lib/trigger_registry.py`：`TriggerRegistry` 类，管理 triggers.json 的持久化读写，提供原子更新（通过 StateVector 锁机制）
- [ ] 1.3 新建 `skills/_lib/schemas/trigger_schema.json`：triggers.json 的 JSON Schema 定义
- [ ] 1.4 在 `requirements.txt` 中添加 `croniter>=2.0`

## 2. Cron 调度触发器

- [ ] 2.1 新建 `skills/_lib/schedulers/cron_scheduler.py`：`CronScheduler` 类，基于 croniter 计算下次触发时间，后台线程等待到触发时间后调用 `TriggerManager.fire()`
- [ ] 2.2 实现 cron 表达式验证：接受标准 5 字段格式（`min hour dom month dow`），无效表达式注册时拒绝
- [ ] 2.3 支持多 cron 触发器并发：每个触发器独立的调度线程，共享 TriggerManager

## 3. 事件驱动触发器

- [ ] 3.1 新建 `skills/_lib/schedulers/fs_watcher.py`：`FileSystemWatcher` 类，基于 `os.scandir` + mtime 比较的轮询模式（默认 30s），检测指定目录的文件变更
- [ ] 3.2 新建 `skills/_lib/schedulers/git_hook.py`：`GitHookListener` 类，通过 `git log --since` / `git branch --list` 检测 git 事件（新 commit、新 branch/tag）
- [ ] 3.3 新建 `skills/_lib/schedulers/webhook_receiver.py`：基于 `http.server.HTTPServer` 的最小 webhook 接收器，监听可配置端口（默认 9090），POST `/webhook/<trigger_id>` 路由
- [ ] 3.4 实现事件队列：`queue.Queue` 线程安全队列，webhook/fs/git 事件生产者写入，TriggerManager 在主线程 `scan_state` 中消费

## 4. 去重与速率限制

- [ ] 4.1 在 `TriggerManager` 中实现重叠检测：两个触发器匹配同一事件时，合并为一次触发，记录所有匹配的 trigger_id
- [ ] 4.2 新建 `skills/_lib/rate_limiter.py`：`TokenBucket` 类实现 token bucket 算法（capacity + refill_rate），状态持久化到 triggers.json
- [ ] 4.3 在 `TriggerManager.fire()` 中集成速率限制：超过限制时记录 warn 事件但不触发；bucket 状态每次 fire 后立即持久化

## 5. LoopEngine 集成

- [ ] 5.1 修改 `skills/loop_engine.py` 的 `scan_state` 阶段：在现有 8 个 detector 之后，调用 `TriggerManager.get_pending()` 获取待处理触发事件，作为额外的 `DetectionResult(type="triggers")` 注入
- [ ] 5.2 修改 `skills/_lib/detectors.py`：新增 `detect_trigger_events` 检测器函数（复用 TriggerManager），注册为第 9 个内置检测器
- [ ] 5.3 确保触发事件通过 `match_actions` 分发与现有检测结果一致
- [ ] 5.4 修改 `skills/loop_engine.py` 的 `run()` 方法：新增可选参数 `await_triggers: bool = False`，为 True 时在每次迭代的 scan_state 前检查 TriggerManager 的 pending 事件

## 6. 配置与安全护栏

- [ ] 6.1 在 `config.yaml` 默认配置中新增 `triggers` 配置段：`enabled`, `webhook_port`, `fs_watch_interval`, `default_rate_limit`
- [ ] 6.2 修改 `skills/_lib/config.py`：`ConfigParser.parse()` 支持解析 `triggers` 配置段
- [ ] 6.3 实现 `--trigger-off` 手动关闭：通过 `TriggerManager.disable_all()` 禁用所有触发器，状态持久化到 triggers.json
- [ ] 6.4 实现崩溃恢复：TriggerManager 启动时从 triggers.json 恢复 in-flight 触发器状态（last_fire_time, token_bucket 状态）

## 7. 测试

- [ ] 7.1 新建 `tests/unit/test_triggers.py`：Trigger dataclass 序列化、TriggerManager 注册/注销/去重、状态持久化
- [ ] 7.2 新建 `tests/unit/test_cron_scheduler.py`：cron 表达式解析、下次触发时间计算、边界情况（月末、闰年）
- [ ] 7.3 新建 `tests/unit/test_rate_limiter.py`：token bucket 消耗/补充、burst 限制、持久化恢复
- [ ] 7.4 新建 `tests/integration/test_trigger_loop_integration.py`：端到端触发 → detect → act 流程
- [ ] 7.5 更新 `tests/unit/test_detectors.py`：验证新增 detect_trigger_events 检测器