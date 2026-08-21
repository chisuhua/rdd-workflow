## ADDED Requirements

### Requirement: candidate-flag-semantics

系统 **MUST** 为每个候选计算 `flags` 字段(分类标签列表),使每个 flag 反映候选的语义状态。

#### Scenario: filesystem_present=False + iteration_status in (None, "planned", "proposed") → flags 含 "needs_planning"

- GIVEN 候选 `filesystem_present=False` 且 `iteration_status` 为 `None` / `"planned"` / `"proposed"` 之一
- AND 候选无 worktree 或 branch
- WHEN `_classify(cand)` 被调用
- THEN `cand.flags` 包含 `"missing_disk"` 和 `"needs_planning"`
- AND 不包含 `"executable"` / `"in_progress"` / `"ready_to_archive"`

#### Scenario: filesystem_present=False + iteration_status in ("approved", "archived") → flags 仅 "missing_disk"

- GIVEN 候选 `filesystem_present=False` 且 `iteration_status` 为 `"approved"` 或 `"archived"`
- AND 候选无 worktree 或 branch
- WHEN `_classify(cand)` 被调用
- THEN `cand.flags` 仅包含 `"missing_disk"`
- AND **不**包含 `"needs_planning"`

#### Scenario: filesystem_present=True + artifact_complete=True → flags 含 "executable"

- GIVEN 候选 `filesystem_present=True` 且 `artifact_complete=True`
- AND 候选无 worktree 或 branch
- WHEN `_classify(cand)` 被调用
- THEN `cand.flags` 包含 `"executable"`
- AND 不包含 `"missing_disk"` / `"needs_planning"` / `"in_progress"` / `"ready_to_archive"`

#### Scenario: filesystem_present=True + artifact_complete=False → flags 含 "needs_planning"

- GIVEN 候选 `filesystem_present=True` 且 `artifact_complete=False`(待补 artifacts)
- AND 候选无 worktree 或 branch
- WHEN `_classify(cand)` 被调用
- THEN `cand.flags` 包含 `"missing_disk"` 和 `"needs_planning"`

#### Scenario: worktree 或 branch 存在 → flags 含 "in_progress" 或 "ready_to_archive"

- GIVEN 候选 `worktree` 或 `branch` 非 None
- WHEN `_classify(cand)` 被调用
- THEN 若 `tasks_total - tasks_done > 0`,`cand.flags` 含 `"in_progress"`
- ELSE 若 `tasks_total - tasks_done == 0`,`cand.flags` 含 `"ready_to_archive"`
- AND 不包含 `"needs_planning"` / `"missing_disk"`

### Requirement: candidate-sort-priority

系统 **MUST** 按 priority 字典排序候选(数字越小越靠前),且 `_classify` 的 flag 选择 **MUST NOT** 影响排序逻辑。

#### Scenario: priority ordering is stable across fixes

- GIVEN 候选排序 priority dict:
  - `"in_progress"`: 0
  - `"executable"`: 1
  - `"ready_to_archive"`: 2
  - `"needs_planning"`: 3
  - `"needs_reconciliation"`: 4
  - `"artifacts_incomplete"`: 5
  - `"missing_disk"`: 6
- WHEN `discover()` 返回多个候选
- THEN 排序按"候选 flags 中优先级最小的键"升序
- AND 同优先级内按字母升序

### Requirement: discover-integration

`discover()` **MUST** 合并 4 个 source 的候选:

- `_disk_candidates`:`openspec/changes/*/` 目录
- `_handoff_candidates`:`.rddf/state/.plan-handoff.json` committed_changes + current_change
- `_iteration_candidates`:`.rddf/state/iteration.json`(过滤 status=="archived")
- `_git_candidates`:`git worktree list` + `git branch --list openspec/*`(过滤 archived_changes)

#### Scenario: archived entries are filtered out

- GIVEN `_iteration_candidates` 读取 `.rddf/state/iteration.json`
- WHEN `entry["status"] == "archived"`
- THEN 该 entry 不进入 candidate union
- AND 也不会出现在 `discover()` 的最终输出

#### Scenario: 4-source union deduplicates by name

- GIVEN 同一 change name 同时出现在 `_disk_candidates` 和 `_iteration_candidates`
- WHEN `discover()` merge 各 source
- THEN union dict 中仅 1 个 `Candidate` 实例(以 name 为 key)
- AND 字段值按 overlay 语义合并(non-default 字段以非空 source 为准)