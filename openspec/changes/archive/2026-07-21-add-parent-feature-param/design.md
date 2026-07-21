# Design: add-parent-feature-param

## 上下文与现状

`iteration_schema.json` L99-102 已定义 `parent_feature` 字段（string|null），但写入端从未传递过该字段。消费端已就绪：

- `skills/_lib/iteration/store.py::derive_feature_name()` L444-450 已优先读取 `parent_feature` 字段
- `skills/feature/scripts/feature_view.py::group_changes_by_feature()` L47-58 已使用 `parent_feature`
- `skills/guide-ship/scripts/ship_archive.sh::check_feature_integrity()` L80 已读取 `parent_feature`
- `skills/deps/scripts/deps_output.py` 已在 AI 建议中支持 `parent_feature`

所有 7 个 active changes 都因无 `parent_feature` 也无 `feature-` 前缀而落入 `__ungrouped__`。本变更激活该字段，让 change 可显式归入 feature 组，无需 `feature-` 命名约定。

## 架构依据

- **ADR-0016 "extend not replace"**: schema 字段已存在，只需修复写入端，无需新增结构。
- **ADR-0022 manual_deps 兄弟模式**: 同样的 "roadmap-meta.yaml 字段 → iteration.json 同步" 模式，作为参考实现。
- **前向声明语义**: `parent_feature` 指向不存在的 feature 视为定义新 feature（与 name-prefix 派生行为一致）。

## 设计决策

### D1: parent_feature 存储 location

**决策**: `parent_feature` 同时写入两处：
1. `openspec/changes/<name>/roadmap-meta.yaml` 的新字段 `parent_feature`（人类可读、随 git 版本控制）
2. `.rddf/state/iteration.json` 的 `changes[].parent_feature` 字段（机器可读、view 文件）

**理由**: 与 ADR-0022 manual_deps 完全对称 - roadmap-meta.yaml 是 source of truth, iteration.json 是镜像。这样：
- 手动编辑 roadmap-meta.yaml 后下次 propose/finalize 可重新同步
- iteration.json 消费者（feature_view, ship_archive, derive_feature_name）无需读 yaml

### D2: 保留字拒绝

**决策**: `parent_feature="__ungrouped__"` 被拒绝，抛 `ValueError`。

**理由**: `__ungrouped__` 是 `feature_view.py::UNGROUPED` 合成键，表示"无 feature 归属"。若允许用户显式设置，会导致 `group_changes_by_feature` 逻辑混乱（显式设置但实际是"无归属"语义）。

**实现位置**: 在 `propose_change.py::create_skeleton_change` 和 `update_iteration_proposed` 入口校验。**不**在 `iteration.add_or_update_change` 校验，因为 store 层应保持中性（schema 已允许任意 string）。

### D3: 显式 parent_feature 优先级

**决策**: 显式 `parent_feature` 优先于 `feature-` 命名约定。

**理由**: 这已是 `derive_feature_name` 既有行为（L444-450 先检查 parent_feature 字段，再 fallback 到 name-prefix）。本变更不改变此优先级，仅激活写入端。

### D4: 向后兼容

**决策**: `parent_feature` 参数为可选 (`Optional[str] = None`)。不传时行为完全不变（字段不写入 iteration.json，不写入 roadmap-meta.yaml）。

**理由**: 现有 21 个 Python unit + 9 bats integration 测试不应被破坏。

### D5: bash wrapper 参数解析

**决策**: `propose_change.sh` 的 `propose_create_change` 和 `propose_finalize_change` 通过环境变量 `PARENT_FEATURE` 传递（不用位置参数），与现有 Oracle C1 安全模式（env-var passing）一致。

**理由**: 避免扩展位置参数列表（破坏现有调用方），且 env-var 模式消除 bash 字符串注入风险。

### D6: schema 不变

**决策**: `iteration_schema.json` **零变更**。`parent_feature` 字段已存在 (L99-102)。

**理由**: 字段已定义，只是写入端缺失。proposal.md "Schema 零变更" 约束满足。

## 实现范围

### 写入端修改

| 文件 | 修改 |
|------|------|
| `skills/propose/scripts/propose_change.py::create_skeleton_change` | 加 `parent_feature: Optional[str] = None` 参数；拒绝 `__ungrouped__`；写入 roadmap-meta.yaml + iteration.json |
| `skills/propose/scripts/propose_change.py::update_iteration_proposed` | 加 `parent_feature: Optional[str] = None` 参数；拒绝 `__ungrouped__`；写入 iteration.json |
| `skills/propose/scripts/propose_change.py::update_roadmap_meta` | 加 `parent_feature: Optional[str] = None` 参数；写入 roadmap-meta.yaml（保持 source of truth 一致） |
| `skills/propose/scripts/propose_change.sh::propose_create_change` | 读取 `PARENT_FEATURE` env var，传给 Python |
| `skills/propose/scripts/propose_change.sh::propose_finalize_change` | 读取 `PARENT_FEATURE` env var，传给 Python |
| `skills/propose/SKILL.md` Phase 4 | 在 `propose_create_change` / `propose_finalize_change` 调用前加可选 `PARENT_FEATURE` 交互/解析 |

### 不修改

- `skills/_lib/iteration/store.py::add_or_update_change` - 已通过 `**fields` 接受 parent_feature
- `skills/_lib/iteration/store.py::derive_feature_name` - 已正确读取 parent_feature
- `skills/_lib/schemas/iteration_schema.json` - 字段已存在
- `skills/feature/scripts/feature_view.py` - 已支持
- `skills/guide-ship/scripts/ship_archive.sh` - 已支持

## 验证策略

### 单元测试（4 个，对应 proposal "4 个 unit test"）

1. **test_create_skeleton_change_with_parent_feature**: 传 `parent_feature="feature-rddf"`，验证 iteration.json + roadmap-meta.yaml 都含该字段
2. **test_create_skeleton_change_rejects_ungrouped**: 传 `parent_feature="__ungrouped__"`，验证 `ValueError` 抛出，且无文件写入
3. **test_update_iteration_proposed_with_parent_feature**: 传 `parent_feature="feature-rddf"`，验证 iteration.json 含该字段
4. **test_parent_feature_groups_into_feature**: 端到端 - 两个 change 同 `parent_feature`，通过 `list_feature_groups` 验证归入同一组

### 集成测试（2 个 bats，对应 proposal "2 个 integration test"）

5. **test_propose_create_change_with_parent_feature_env**: 通过 `PARENT_FEATURE=feature-x propose_create_change ...` 验证 bash wrapper 传递正确
6. **test_propose_finalize_change_with_parent_feature_env**: 同上，对 finalize 路径

### 回归

- 全部 21 个现有 `test_propose_change.py` 测试通过
- 全部 `test_iteration.py` 测试通过
- 全部 `test_feature_view.py` 测试通过

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 现有调用方不传 parent_feature 导致回归 | 参数默认 None，行为不变 |
| `__ungrouped__` 保留字绕过校验 | 在三个入口（skeleton, finalize, update_iteration）都校验 |
| roadmap-meta.yaml 旧文件无 parent_feature 字段 | 视为 None（无 feature 归属），与现有行为一致 |
| bash wrapper env-var 未设置 | Python 端 `os.environ.get("PARENT_FEATURE") or None`，None 时不传 |
