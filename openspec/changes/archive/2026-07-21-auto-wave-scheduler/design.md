# Design: auto-wave-scheduler

> **架构依据**: ADR-0010 (v2.1 DependencyScheduler 方向), ADR-0022 (manual_deps 字段), ADR-0020 (planned 状态与渐进填充)

## 概述

`auto-wave-scheduler` 是 v2.1 阶段的轻量自动化模块,消费 `iteration.json` + `deps-analysis.json` + `roadmap-meta.yaml` 中的依赖信息,**自动检测 wave 切换时机**并向用户输出建议。它**不**自动调用 guide-plan/guide-ship,仅打印推荐信息,保留人工 gate。

## 问题与动机

当前 wave 切换靠人工判断:

1. **归档后无感知**: 当 `change-a` 归档后,`change-b` (blocker=change-a) 的 blocker 已解除,但用户需手动 `skill_use("guide-plan")` 才知道哪些可填充。已有 `post_archive_fill.sh` 但仅扫描 planned 状态,**不覆盖 proposed 状态**(即不能 ship 的 proposed change 不被推荐)。
2. **入口状态丢失**: `guide-arch` / `guide-plan` / `guide-ship` 入口未自动同步 rddf-session 状态到 iteration.json(仅创建/关闭 rddf-session,不更新 iteration.json 中对应 change 的 status)。
3. **manual_deps 未被消费**: ADR-0022 引入的 `manual_deps` 字段已被 `deps` 合并进 `iteration.json`,但没有自动化消费方检测"当 manual_deps 中的 change 归档时,本 change 可执行"。

## 范围

### In Scope

1. **WaveScheduler 模块** (`skills/_lib/wave_scheduler.py`):
   - `detect_unblocked(iteration_data, deps_data=None) -> list[Recommendation]`: 扫描 planned/proposed changes,检测 blocker 是否已解除(综合 iteration.json 的 `blocker` 字段 + `manual_deps` 字段)
   - `format_recommendations(recs) -> str`: 格式化建议输出
   - `check_on_archive(project_root, archived_name) -> list[Recommendation]`: 归档钩子,检测由该 archived change 阻塞的所有变化
   - `check_on_entry(project_root, skill_name) -> list[Recommendation]`: 入口钩子,扫描当前可推进的变化

2. **bash wrapper** (`skills/_lib/wave_scheduler_hooks.sh`):
   - `wave_scheduler_post_archive <archived_name>`: 替代/扩展 `post_archive_fill.sh`,增加对 proposed 状态的检测
   - `wave_scheduler_entry_check <skill_name>`: 在 guide-arch/guide-plan/guide-ship 入口打印建议

3. **Hook 集成**:
   - `guide-ship` Phase 3 post-archive: 调用 `wave_scheduler_post_archive` (替换现有 `run_post_archive_fill_suggestion`)
   - `guide-plan` 入口: 调用 `wave_scheduler_entry_check guide-plan`
   - `guide-ship` 入口: 调用 `wave_scheduler_entry_check guide-ship`
   - **不**修改 `guide-arch` (arch 阶段不处理 changes,无意义)

4. **测试** (`tests/unit/test_wave_scheduler.py`):
   - 模拟 iteration.json 状态: planned/proposed + blocker 已归档
   - 模拟 manual_deps 场景
   - 模拟 deps-analysis.json 提供的 blocks 列表
   - 模拟多 change 并行可推进场景

### Out of Scope

- **不**自动调用 guide-plan/guide-ship (仅建议,用户确认)
- **不**修改 `DependencyScheduler` (ADR-0010 v2.1 完整版留待后续)
- **不**修改 iteration.json schema (复用 v4 的 manual_deps/manual_blocks 字段)
- **不**修改 deps-analysis.json schema
- **不**修改 `propose` / `execute` / `deps` 的 hook 行为

## 架构

### 数据流

```
iteration.json (v4)              deps-analysis.json (v1)
  │  changes[]:                     │  changes{}: per-change analysis
  │    - name, status               │    - name, status (ready/blocked_by/...)
  │    - blocker (str|null)         │    - blocker (str|null)
  │    - manual_deps (list|null)    │    - blocks (list[str])
  │    - manual_blocks (list|null)  │    - parallel_group (int)
  │    - parallel_group             │  execution_order: [name, ...]
  │                                 │
  └─────────┬───────────────────────┘
            │
            ▼
   ┌────────────────────────┐
   │  WaveScheduler         │
   │  - detect_unblocked()  │
   │  - format_recs()       │
   │  - check_on_archive()  │
   │  - check_on_entry()    │
   └─────────┬──────────────┘
            │
            ▼
   list[Recommendation]
     {name, current_status, blocked_by, blocker_status,
      wave: "fill"|"ship", reason: str}
```

### Recommendation 数据结构

```python
@dataclass
class Recommendation:
    name: str                      # 推荐的 change 名
    current_status: str            # planned / proposed
    blocked_by: str                # 之前的 blocker 名 (iteration.blocker 或 manual_deps[0])
    blocker_status: str            # archived / completed (解除原因)
    wave: str                      # "fill" (planned -> propose) | "ship" (proposed -> guide-ship)
    reason: str                    # 人类可读理由
    source: str                    # "iteration.blocker" | "manual_deps" | "deps.blocks"
```

### 决策逻辑

`detect_unblocked` 对每个 change 判断:

1. **status 过滤**: 仅处理 `planned` 和 `proposed` 状态
2. **blocker 来源** (按优先级):
   - `iteration.json.blocker` 字段 (deps 静态分析设置)
   - `iteration.json.manual_deps[0]` (人工声明,若 blocker 未设)
   - `deps-analysis.json.changes[name].blocker` (若 iteration 无)
3. **解除检测**: blocker 对应的 change 在 iteration.json 中 status 为 `archived` 或 `completed`
4. **wave 映射**:
   - `planned` -> `wave="fill"` (用户应调 guide-plan 填充)
   - `proposed` -> `wave="ship"` (用户应调 guide-ship 执行)
5. **manual_deps 多依赖**: 若 manual_deps 有多个,所有都需 archived/completed 才解锁;推荐时 `reason` 列出所有 manual_deps 状态

### 失败容错

- iteration.json 缺失或损坏: 返回空列表,不抛异常 (复用 `iteration.load()` 的容错)
- deps-analysis.json 缺失: 仅依赖 iteration.json 数据 (降级模式)
- 单个 change 字段缺失: 跳过该 change,继续处理

## 文件结构

| File | Responsibility |
|---|---|
| `skills/_lib/wave_scheduler.py` | WaveScheduler 类 + Recommendation dataclass,纯 Python 逻辑,无 IO |
| `skills/_lib/wave_scheduler_hooks.sh` | bash wrapper,封装 Python 调用,提供 `wave_scheduler_post_archive` / `wave_scheduler_entry_check` |
| `tests/unit/test_wave_scheduler.py` | 单元测试,模拟各种 iteration/deps 状态 |
| `tests/integration/test_wave_scheduler_hook.bats` | 集成测试,验证 bash wrapper 调用契约 |
| `skills/guide-ship/SKILL.md` (修改) | Phase 3 替换 `run_post_archive_fill_suggestion` -> `wave_scheduler_post_archive` |
| `skills/guide-plan/SKILL.md` (修改) | Phase 0 入口添加 `wave_scheduler_entry_check guide-plan` |
| `skills/guide-ship/SKILL.md` (修改) | Phase 1 入口添加 `wave_scheduler_entry_check guide-ship` |

## 与现有模块的关系

### 与 `iteration.get_unblocked_planned` 的关系

- 现有 `get_unblocked_planned(project_root)` 仅返回 planned 状态的 change
- WaveScheduler 扩展为: 同时返回 proposed 状态 (wave="ship") 并提供更丰富的 reason/source 信息
- **不**修改 `get_unblocked_planned` (向后兼容),WaveScheduler 内部调用它并扩展

### 与 `post_archive_fill.sh` 的关系

- `post_archive_fill.sh` 是 v2.0.7 提取的 helper,仅扫描 planned
- WaveScheduler 是其超集,增加 proposed 检测
- **迁移策略**: `post_archive_fill.sh` 改为薄 wrapper 调用 `wave_scheduler_post_archive`,保持向后兼容 (现有测试不应破坏)

### 与 `DependencyScheduler` 的关系

- `DependencyScheduler` 是拓扑排序工具 (Kahn 算法),无状态查询
- WaveScheduler **消费** 拓扑信息 (parallel_group, blocker) 但**不**重新计算
- ADR-0010 v2.1 完整版会整合两者,本变更不涉及

## 验收标准

1. **归档场景**: 归档 `change-a` 后,若 `change-b.blocker=change-a` 且 `change-b.status=planned`,输出:
   ```
   💡 Wave suggestion (post-archive):
      - change-b: blocker 'change-a' 已 archived,可填充 (wave=fill)
      运行 'skill_use("guide-plan")' -> 选择 '3. 填充骨架 change (fill)'
   ```
2. **ship 场景**: 若 `change-c.status=proposed` 且 `change-c.blocker=change-a` (已 archived),输出:
   ```
   💡 Wave suggestion (post-archive):
      - change-c: blocker 'change-a' 已 archived,可执行 (wave=ship)
      运行 'skill_use("guide-ship")' 处理 change-c
   ```
3. **manual_deps 场景**: 若 `change-d.manual_deps=[change-a, change-e]` 且两者都 archived,输出:
   ```
   💡 Wave suggestion (post-archive):
      - change-d: manual_deps [change-a, change-e] 均 archived,可填充 (wave=fill, source=manual_deps)
   ```
4. **入口场景**: guide-plan 入口若检测到 ready_for_fill changes,输出建议
5. **失败容错**: iteration.json 缺失时,WaveScheduler 返回空列表,不抛异常
6. **向后兼容**: 现有 `post_archive_fill.sh` 测试 (`test_post_archive_fill*` 若有) 不破坏

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| 推荐 stale change (blocker 已归档但 change 本身已 proposed) | status 过滤 + reason 字段说明 |
| manual_deps 环依赖 (A.dep=B, B.dep=A) | 跳过检测,reason="manual_deps cycle detected" (本变更不修复,仅标注) |
| deps-analysis.json 与 iteration.json 不一致 | 以 iteration.json 为准 (it is the authoritative source) |
| 入口 hook 阻塞用户 | WaveScheduler 调用设 1s 超时,失败仅 stderr 警告 |

## 测试覆盖矩阵

| 场景 | iteration.json 状态 | 预期 |
|---|---|---|
| planned + blocker archived | planned, blocker=X, X.status=archived | 1 个 fill 推荐 |
| planned + blocker completed | planned, blocker=X, X.status=completed | 1 个 fill 推荐 |
| planned + blocker in_worktree | planned, blocker=X, X.status=in_worktree | 0 推荐 (仍阻塞) |
| proposed + blocker archived | proposed, blocker=X, X.status=archived | 1 个 ship 推荐 |
| manual_deps 全 archived | planned, manual_deps=[A,B], A/B.status=archived | 1 个 fill 推荐,source=manual_deps |
| manual_deps 部分 archived | planned, manual_deps=[A,B], A.archived, B.in_worktree | 0 推荐 |
| 无 blocker 的 planned | planned, blocker=None | 0 推荐 (已被 list_ready_for_fill 覆盖) |
| iteration.json 缺失 | 文件不存在 | 返回空列表,不抛异常 |
| deps-analysis.json 缺失 | 文件不存在 | 降级为仅 iteration.json |
| check_on_archive 过滤 | 归档 change-a,但 change-b 的 blocker=change-c | 不推荐 change-b (与 change-a 无关) |
