# validate-feature-name

## Why

- 现状：`propose_change.py::create_skeleton_change` 与 `approve_proposal.sh` 接受任意字符串作为 `parent_feature`，写进 `iteration.json` 的 `parent_feature` 字段与 `roadmap-meta.yaml`。无任何校验。
- 风险：用户在 `**特性**:` 头部写错名（如 `wave-cores` 而非 `wave-core`），propose 不报错，iteration.json 多一个孤立 feature 节点，`feature` skill 的 `summary/graph/order` 视图随之漂移。**整组相关 change 在用户脑中属于一个 feature，但系统认为是两个**。
- 与 ADR-0022 (manual_deps) 的一致性 — ADR-0022 让用户在 roadmap-meta.yaml 显式声明依赖。同等级的需求是：让用户在 `**特性**:` 声明归属时知道**现存可选归属**，避免拼写错导致孤立。
- 与 ADR-0025 (design-proposal-creation) 的精神一致 — design 阶段的实质审查应该包括"这个 feature 名是否有效"。
- 与本次会话修复 `fix-feature-decision-design-phase` (commit `3622c48`) 衔接：上次修了"head 字段被忽略"（feature 不生效），这次补上"head 字段生效了但可能 typo"（feature 错生效）。
- 评估 ROI 高：单一校验点（propose 入口），覆盖所有下游 feature 视图，< 50 行代码 + 3 个测试 case。

## What Changes

**In Scope**:

- `skills/propose/scripts/propose_change.py::create_skeleton_change`：在写入 `parent_feature` 之前，从现有 `iteration.json` 收集所有有效 feature 名（`__ungrouped__` 排除），新值不在集合内则发 warning（默认）或 error（`STRICT_FEATURE_VALIDATION=yes` 时）
- `skills/guide-design/scripts/approve_proposal.sh` 在写 `roadmap-meta.yaml` 之前同样校验（保持双 path 一致行为）
- 单一新增 Python 函数 `_collect_existing_features(project_root)` 用于收集现有 feature 名（去重）
- 3 个新单元测试 case（typo 警告、匹配通过、空 iteration.json 放行）

### 关键场景

- GIVEN `iteration.json` 含 change A 的 `parent_feature="wave-core"`，WHEN propose 创建 change B 写 `**特性**: wave-cores`（typo），THEN propose 输出 WARNING `parent_feature='wave-cores' not in existing features [wave-core]` 并仍落盘（除非 `STRICT_FEATURE_VALIDATION=yes` 阻断）
- GIVEN `iteration.json` 含 `parent_feature="wave-core"`，WHEN propose 创建 change C 写 `**特性**: wave-core`（正确拼写），THEN propose 静默通过，无 warning
- GIVEN `iteration.json` 不存在（或无 changes），WHEN propose 创建 change D 任意 `**特性**` 值，THEN propose 静默通过（无 baseline 可对比）
- GIVEN `STRICT_FEATURE_VALIDATION=yes`，WHEN propose 创建 change E 写 `**特性**: brand-new`（不在现有），THEN propose 退出码非 0，输出 "existing features: ..." 列表
- GIVEN `iteration.json` 含 `__ungrouped__` synthetic feature，WHEN 收集现有 feature 名，THEN `__ungrouped__` 被排除（不应作为有效选项提示给用户）

**Out of Scope**:

- 不强制要求"必须用现有 feature 名" — 新 feature 仍然允许（只需 `STRICT_FEATURE_VALIDATION=no` 或未设置）
- 不修 head -8 启发式（独立提案）
- 不修 parent_feature 双写漂移（独立提案）
- 不做 feature dashboard / feature CLI（YAGNI）
- 不改 schema、不写 ADR、不改现有 feature skill API

## Capabilities

- MUST 单一 source of truth — feature 名收集只读 `iteration.json`，不读 `roadmap-meta.yaml`（避免双写漂移场景下的误报）
- MUST NOT 阻断 propose 默认行为 — 默认 warning（与现有 STRICT_DESIGN_GATE 哲学一致：strict 是 opt-in）
- MUST 兼容空 iteration.json / 不存在场景（first-feature case 不报错）
- MUST NOT 把 `__ungrouped__` 列为有效 feature（synthetic key）
- SHOULD 警告信息含现有 feature 列表（最多 10 个，超出截断 + 提示 "and N more"）
- SHOULD 不引入新依赖（用 stdlib re/json/os）

## Impact

- MUST 单一 source of truth — feature 名收集只读 `iteration.json`，不读 `roadmap-meta.yaml`（避免双写漂移场景下的误报）
- MUST NOT 阻断 propose 默认行为 — 默认 warning（与现有 STRICT_DESIGN_GATE 哲学一致：strict 是 opt-in）
- MUST 兼容空 iteration.json / 不存在场景（first-feature case 不报错）
- MUST NOT 把 `__ungrouped__` 列为有效 feature（synthetic key）
- SHOULD 警告信息含现有 feature 列表（最多 10 个，超出截断 + 提示 "and N more"）
- SHOULD 不引入新依赖（用 stdlib re/json/os）

## Acceptance

- [ ] `tests/unit/test_validate_feature_name.py` 新增 3 个 case（typo warning、match 静默、空 baseline 放行）全绿
- [ ] 现有 `tests/unit/test_propose_change*.py` (43 个) 全部仍绿
- [ ] `tests/integration/test_approve_proposal_*.bats` 9 个 case 中除 KNOWN_FAILURE 外的 8 个仍绿
- [ ] `STRICT_FEATURE_VALIDATION=yes` 下，typo 场景 propose 退出码非 0
- [ ] 警告信息含现有 feature 名列表（便于用户纠正）
- [ ] 不引入新 pip / apt 依赖

