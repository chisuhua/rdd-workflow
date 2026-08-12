## Context

`parent_feature` 是 rdd-workflow v2.0 feature 视图的分组键: 同一 feature 名下的 change 共享 `iteration.json` 的 `parent_feature` 字段, feature skill 的 `summary / graph / order` 视图据此聚合。 提案入口 (`propose_change.py::create_skeleton_change` 与 `guide-design/scripts/approve_proposal.sh`) 当前对 `parent_feature` 值不做校验, 任何字符串都直接写入 `iteration.json` 的 `parent_feature` 与 `roadmap-meta.yaml`。 这与本会话先前的 `fix-feature-decision-design-phase` (commit `3622c48`) 互补: 上次修了"head 字段被忽略"(feature 不生效), 这次补"head 字段生效但可能 typo"(feature 错生效)。

数据流:

```
用户 add-improve → improvements/<name>.md (**特性**: <feature-name>)
   ↓
guide-design approve_proposal.sh
   ↓ (parent_feature 解析自 head)
openspec/changes/<name>/roadmap-meta.yaml (parent_feature: <feature-name>)
.iterddf/state/iteration.json (changes[].parent_feature)
   ↓
feature skill: summary / graph / order 视图
```

单点校验 (propose 入口 + approve 入口) 覆盖所有下游 feature 视图。

## Goals / Non-Goals

**Goals:**
- 在两个 propose 入口对 `parent_feature` 做一致性校验, 与 ADR-0022 (manual_deps) 哲学对齐 (用户声明需先看到现存选项)
- 默认行为非阻断 — 仅 warning, 与现有 `STRICT_DESIGN_GATE` opt-in 哲学一致
- 提供单一 source of truth helper (避免 propose/approve 双 path 漂移)
- 新 feature 名仍然允许 (不必复用现有), 仅在 typo 场景下提示

**Non-Goals:**
- 不强制要求 "必须用现有 feature 名" — 新 feature 仍允许 (默认 warning 放行)
- 不修 head -8 启发式解析 (独立提案, 与本次提案正交)
- 不修 `parent_feature` 双写漂移 (propose 写入 + approve 写入 之间的不一致) (独立提案)
- 不做 feature dashboard / feature CLI / YAGNI 范围
- 不改 schema / 不写新 ADR / 不改 feature skill API
- 不引入新 pip/apt 依赖 — 用 stdlib `re/json/os`

## Decisions

### Decision 1: 单一 source of truth = iteration.json

**Choice**: `_collect_existing_features(project_root)` 仅从 `.rddf/state/iteration.json` 读取 `changes[].parent_feature`, 不读 `roadmap-meta.yaml`。

**Rationale**:
- iteration.json 是 view 文件, 由 `propose_create_change` / `iteration.add_or_update_change` 统一写入, schema 在 `_lib/schemas/iteration_schema.json` 管控
- roadmap-meta.yaml 是 per-change metadata, 可能存在与 iteration.json 漂移的双写场景 (本次提案范围内不修)
- 选 iteration.json 与 ADR-0019 (change-arch-alignment) 哲学一致: view 文件优先, per-change 文件次之

**Alternatives considered**:
- ❌ 同时读 iteration.json + roadmap-meta.yaml 取并集 → 漂移时误报
- ❌ 维护独立 `features.json` registry → 增加新 schema, YAGNI

### Decision 2: 默认 warning, STRICT opt-in error

**Choice**: 默认 `parent_feature` 不在现有集合时输出 WARNING 但仍落盘; 设置 `STRICT_FEATURE_VALIDATION=yes` 时退出码非 0 阻断。

**Rationale**:
- 与现有 `STRICT_DESIGN_GATE=yes` (propose_quality_check) / `STRICT_ARCH_GATE=yes` (guide-arch) 哲学一致: strict 是 opt-in, 不污染默认流
- 默认 warning 让用户看到 "可能 typo" 提示, 但不阻止新 feature 探索
- STRICT 模式给 CI / 严格项目保留硬阻断选项

**Alternatives considered**:
- ❌ 默认阻断 → 影响所有现有 workflow (回归风险高), 升级成本不匹配 ROI
- ❌ 仅 warning 无 STRICT → 用户没有升级到强约束的路径, 与现有 STRICT_* gate 哲学不一致

### Decision 3: 双 path 一致行为 (Python + bash)

**Choice**: Python (`propose_change.py::create_skeleton_change`) 和 bash (`guide-design/scripts/approve_proposal.sh`) 都执行校验, 行为一致 (warning vs STRICT 同语义)。

**Rationale**:
- propose 路径是常态入口, 必须校验
- approve 路径是 design 阶段的兜底入口 (D1 落盘路径), 跳过会留下 design-pre-created changes 绕过校验的洞
- 双 path 共享同一 source of truth helper (Python 版本), bash 端通过 `python3 -c "..."` 调用同一逻辑 (避免逻辑漂移)

**Alternatives considered**:
- ❌ 仅 Python 校验 → design 阶段 approve 路径绕过, 漏洞存在
- ❌ bash 独立实现 → 逻辑漂移风险, 违反 DRY

### Decision 4: `__ungrouped__` 排除

**Choice**: `_collect_existing_features()` 收集时排除 `__ungrouped__` synthetic key。

**Rationale**:
- `__ungrouped__` 是 feature skill 的 fallback bucket (iteration store 在无 parent_feature 时填入), 不是用户可选 feature 名
- 把 `__ungrouped__` 列在 "existing features" 列表里会误导用户去选它, 反而破坏分组语义
- 排除逻辑在 helper 内部, 调用方不需要关心

## Risks / Trade-offs

- [Risk] `parent_feature` 在 proposals 中可能拼写错误但用户故意 (e.g. 新 feature 名复用旧 typo) → **Mitigation**: warning 信息含现有 feature 列表, 用户看到后可决定是否确认; STRICT 模式强制纠正
- [Risk] `iteration.json` 不存在 / 无 changes (first-feature case) → **Mitigation**: helper 检测空 baseline 时返回空集合, 任何 `parent_feature` 放行 (与场景 GIVEN-3 一致)
- [Risk] 双 path 校验增加 propose/approve 启动开销 → **Mitigation**: helper 仅读取 + set 构造, < 10ms, 不影响 CI 时间预算
- [Risk] bash 端 `python3 -c "..."` 调用引入跨语言边界 → **Mitigation**: 调用极简 (仅 helper invocation), 错误通过 stderr 透传
- [Trade-off] warning 信息截断到 10 个现有 feature (超出 "and N more") → 用户在 > 10 个 feature 的项目里看不到完整列表; 接受这个 trade-off 因为 feature 名通常 < 10, 大型项目可设 STRICT 模式自行 grep

## Migration Plan

1. **Phase 1**: 实现 `_collect_existing_features()` helper + 单测 (3 case)
2. **Phase 2**: 在 `create_skeleton_change` 调用 helper, 加 warning 输出 (默认 non-blocking)
3. **Phase 3**: 在 `approve_proposal.sh` 调用同一 helper (via python3 inline), 加 warning 输出
4. **Phase 4**: 现有 43 个 `test_propose_change*.py` 全部仍绿; 现有 8 个 `test_approve_proposal_*.bats` 仍绿
5. **Rollback**: helper 是新文件, 移除 import + 调用即可回滚; iteration.json 写入逻辑不变

## Open Questions

- (已解) STRICT mode 是否需要额外配置入口 (e.g. roadmap-meta.yaml 字段) → **决策**: 不需要, 环境变量 `STRICT_FEATURE_VALIDATION=yes` 是单一开关
- (已解) 是否需要在 warning 中显示每个现有 feature 的 change 数量 → **决策**: 否, 列表已经足够; 用户可跑 `feature summary` 看详情
