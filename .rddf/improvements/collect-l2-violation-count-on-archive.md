# collect-l2-violation-count-on-archive

**优先级**: P2 | **来源**: Session 复盘 2026-08-05 UsrLinuxEmu — 5 个 `stage4-l2-foundation-removal-*` change 的 feat commit 各自声明 L2 违规减少量（`#3/8 → #2/8` / `#4→#3, #3→#2` 等），但项目级"全局绝对计数"从未记录；ADR-072 §D4 revised 的"B-class 12 violations → 0"目标无法在 git history 中验证
**阶段**: v2.1 | **分类**: infra-setup
**类型**: feature

## 架构依据

- **现状**: L2 violation count 是项目级指标（"drv/ 还有几处 `#include "sim/"`"），但 archive 时只记录每个 change 的相对减少量
- **ADR-0017**: iteration.json 是核心状态文件 — 它已经记录了 change 粒度的 `archived_at` 等元数据，新增 L2 count 字段是 schema 的自然扩展
- **`rddf-iteration-strict-schema.md`** (本 session, P1) 已提到 schema 严格化但未扩展 schema 本身；本提案是它的**前置依赖**（要先扩 schema，再让 strict schema 校验支持新字段）
- **本提案范围**：archive 时自动收集项目级 L2 violation count 写入 iteration.json 的 `l2_violation_count_after` 字段；rddf status / iteration view 渲染该字段

### 本仓库实际复现 (2026-08-05 UsrLinuxEmu session 已验证)

5 个 removal change 的 feat commit message 给出的 L2 减少量：

```
f1070ec feat(gpu): remove gpu_queue_emu direct include from drv (L2 #3/8 -> #2/8)
22c41af feat(gpu): remove graph direct include from drv (L2 #4->#3, #3->#2)
5929f50 feat(gpu): remove hardware_puller_emu direct include from drv (L2 #2/8 -> #1/8)
dfe97e7 feat(gpu): remove mem_pool direct include from drv (L2 #3->#2, #2->#1)
0ab7133 feat(gpu): remove stream_capture direct include from drv (L2 #2->#1, #1->#0)
```

实测 5 个全部 ship 后：

```
$ grep -rn '#include.*"sim/' plugins/gpu_driver/drv/ | wc -l
1
$ grep -rn '#include.*"sim/' plugins/gpu_driver/drv/
plugins/gpu_driver/drv/gpgpu_device.cpp:15:#include "sim/fence_id.h"
```

**问题**：
- 全局计数从 8 降到 1（不是 commit message 给的"#n/8"）
- "1" 来自 `sim/fence_id.h`，在所有 removal change 的 Out of Scope 中提到（属于 kfd_events.c）
- 项目无法回答"ADR-072 的 B-class 12 violations → 0 目标进展如何" — 因为没有任何文件记录每个里程碑的绝对计数

## 范围

- **In Scope**:
  - iteration.json schema 增加 optional 字段：`l2_violation_count_after` (int, 0..N) 和 `l2_violation_kind` (enum: `sim_include_drv`, `sim_class_type`, ... — 默认 `sim_include_drv`)
  - `archive.sh::archive_change()` 末尾调用 `collect_l2_count()` 函数，写入新字段
  - `collect_l2_count()` 默认实现：`grep -rn '#include.*"sim/' plugins/gpu_driver/drv/ | wc -l`（参考 UsrLinuxEmu 的 L2 基线命令）；可通过 `rddf config set l2_count_cmd '<cmd>'` 自定义
  - `rddf status --iteration` 渲染 archived change 时显示 `L2: <n>` 字段
  - `rddf l2-trend` 子命令：列出所有 archived change 的 L2 count 序列，便于画 trend chart
  - 单元测试：collect_l2_count mock stdout；schema bump 后仍兼容旧 iteration.json（schema migration）
- **Out Scope**:
  - 不实现 L2 trend chart 的画图（命令只输出数据，画图由 caller 决定）
  - 不修改 L2 count 命令的具体 grep 模式（保留默认 + 允许自定义）
  - 不实现其他 violation kind 的检测（只支持 `sim_include_drv` 作为默认 kind）

## 关键场景

- GIVEN `archive_change(name)` 完成，WHEN 进入末尾，THEN 调 `collect_l2_count()` → 默认命令运行 → 解析输出为整数 → 写入 iteration.json 中该 change 的 `l2_violation_count_after` 字段
- GIVEN iteration.json schema 已 bump，WHEN 加载旧（无 `l2_violation_count_after` 字段）iteration.json，THEN schema 校验通过（旧字段 optional）；`rddf status --iteration` 对这些 change 显示 `L2: (not recorded)`
- GIVEN `rddf config set l2_count_cmd 'grep -rn "sim_" plugins/gpu_driver/drv/ | wc -l'`，WHEN 下次 archive，THEN 使用自定义命令而非默认
- GIVEN `rddf l2-trend` 运行，WHEN 输出，THEN 按 archived_at 时间排序列出 `change_name | l2_violation_count_after | archived_at`，便于观察 trend

## 技术约束

- MUST 走标准的 schema migration 流程（schema_version bump + 迁移脚本兼容旧 iteration.json），不允许直接改 schema 不带迁移
- MUST 把 `collect_l2_count()` 放到独立模块（`skills/_lib/iteration/l2.py`），便于自定义命令的实现
- MUST NOT 在 archive 主流程中阻塞：collect_l2_count 失败应只写 warning，不 raise（参考 `fix-archive-iteration-sync.md` 的 helper 设计）
- SHOULD 缓存上一次 L2 count（在同一 archive 批次内复用）

## 验收标准

- iteration.json schema 增加 2 个 optional 字段（per-change item）
- `skills/_lib/iteration/l2.py::collect_l2_count()` 约 30 行
- `rddf l2-trend` 子命令可用
- 2 个回归测试：默认命令 / 自定义命令 / archive 失败不阻塞
- 所有现有 bats / pytest 测试通过
