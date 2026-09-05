# Wave 4 — Stale Detection + Loop Closure + Cleanup (v2 — Pending user approval)

> **Status**: Pending user approval (修订 v2, post Oracle+Metis review)
> **Date**: 2026-09-04
> **Author**: sisyphus
> **Depends on**: Stage 3 (`6d79a0d..92d9186`, 11 commits), ADR-0016/0028/0042, Oracle review (`bg_df537087`), Metis review (`bg_83f370c1`)

## 0. v1 → v2 修订摘要 (vs plan v1)

| 修订 ID | 来源 | v1 内容 | v2 修订 |
|---|---|---|---|
| **R1** 🔴 | Oracle + Metis | §6.1 一句话承认 `planner_state_revision` 可能缺失，MUST DO 第 8 步当它存在 | **Change 0 新增 Sub-task 0.0**: 创建 `state_revision` 全链路 (schema additive optional + `_default_state` 默认 0 + `write_state`/`update_state` 语义-diff 递增 + 新增 `_current_planner_state_revision()` reader) |
| **R2** 🔴 | Oracle + Metis | §2.3 伪代码 `with FileLock → write_planner_feedback` (后者内部自锁) | **Change 1.1 锁方案修订**: 临界区内**只用 `atomic_write_json`**；禁调 `write_planner_feedback` / `read_planner_feedback`（二者内部自带锁，fcntl.flock 不可重入，嵌套 LockTimeout 10s） |
| **R3** 🔴 | Metis | §2.4 代码 `e.id.startswith(...)` 是 Python bug | **Change 1.2 代码修正**: `e["feedback_id"]`；generator 内 `try/except (ValueError, IndexError, KeyError)` 跳过畸形 ID 并记录 `skipped_ids` |
| **R4** 🟡 | Metis | Change 2 hook 失败传播语义缺失 | **Change 2 MUST DO 加注**: `try/except + log warning + 不阻断 arch-done / sync 主流程`；新增 `test_hook_compute_failure_does_not_block_*` 单测 |
| **R5** 🟡 | Metis | Resolved revival 是 Stage 3 已实现行为 (L369)，Wave 4 上线首次 compute 全量复活 | **Change 3 ADR-0042 §X.X**: 明确"Wave 4 上线后 prior resolved 一次性 reopened_count=1"迁移预期 + `reopened_count >= 3` 触发 warning |
| **R6** 🟡 | Oracle + Metis | KNOWN_FAILURES shrink-only 用 bats 测试实现 | **Change 3 机制改为**: 复用 `report_regression.sh` L27-34 sed strip 规则 + `git show origin/master:tests/KNOWN_FAILURES.txt` 做 git-diff 集合比较 → CI 步骤；删原 bats 测试计划 |
| **R9** 🟡 | Oracle | Change 1 ID 修复只治一半（merge 用 `asdict(f)` 新 ID，fingerprint 命中也换号） | **Change 1.2 补充**: fingerprint 命中时 `as_dict["feedback_id"] = prior_match["feedback_id"]`；counter 只分配给真新 fingerprint |
| **R10** 🟡 | Oracle | §2.5 claim"Change 1 同一锁保护"不成立；compute 是 read-modify-write 但 read 在锁外 | **Change 2 新增 `recompute_planner_feedback(project_root)` 助手**: 单 FileLock 临界区内 read→compute→write；两 hook + `--recompute` CLI 三处共用 |
| **R11** 🟡 | Oracle | Hook 点描述错：`cmd_sync_apply` 不存在；`rdd_arch.py` 不存在 | **Change 2 hook 点修正**: planner 插 `_lib/cli/planner_cmd.py:118` `_apply_state_with_warn(...)` 之后；arch 插 `skills/rdd-arch/scripts/write_arch_handoff.sh` 成功后 |
| **R12** 🟡 | Metis | `_lib/arch_quality_gate.py:298` 有 `version != 1` warning 检查，与 Change 0 writer `version: 2` 输出冲突 | **Change 0 commit 1 后立即验证** `arch-quality-gate` pass；若失败，Change 0 子任务里同步修 gate (接受 `[1, 2]`) |
| **R13** | Metis | (并入 R4) | — |
| **R14** | Metis | (并入 R5) | — |
| **R15** | Metis | `last_seen_at` 每次 recompute 更新 → 文件 mtime 每次变 → 幂等性仅排除 timestamp | **Change 1 同步修订**: prior_match 时 `as_dict["last_seen_at"] = prior_match["last_seen_at"]`，仅新 entry 用 `now_iso` → 真幂等 |
| **scoping** | 用户决策 | — | **(b) + (B)**: state_revision = 内容哈希变化才 +1；Wave 4 保持 4-change 单波 |

---

## 1. 背景与动机

### 1.1 Stage 3 Oracle 审查发现

Stage 3 (11 commits) 实现 `rdd-arch` rename + 双向反馈闭环。Oracle (4m44s, `bg_df537087`) 揭示 3 P0 + 3 P1 缺陷：核心契约名实不符 (revision 字段无 writer)、lifecycle TOCTOU、feedback_id 同日撞号、闭环只闭一半、状态语义脏数据、文档漂移。

### 1.2 Wave 4 目标

修复 Stage 3 核心契约 bug，让"双向反馈闭环"从**文档承诺**变成**事实**：

1. **Stale 检测**: 真 2-revision（`arch_handoff_revision` + `state_revision`），`codebase_commit` 降级为 informational metadata
2. **生命周期原子化**: 4 个 op 全部 FileLock 临界区（critical section 仅 `atomic_write_json`）
3. **ID 稳定性**: 优先保留 prior `feedback_id`；counter 只分配给真新 fingerprint；防御畸形 ID
4. **闭环自动化**: `planner sync --apply` + arch-done 自动 recompute（`recompute_planner_feedback()` 助手统一 RMW 锁）
5. **清理**: 死代码、文档漂移、KNOWN_FAILURES shrink-only CI（复用 `report_regression.sh`）

### 1.3 不在 Wave 4 范围

- ❌ 不扩展反馈到 plan/ship/verify（Oracle 明示：等核心稳后再扩）
- ❌ 不实现其余 3 种 feedback kind emitter（`coverage_gap` / `adr_drift` / `roadmap_staleness`）
- ❌ 不移除 `guide-arch` shim（仅 1 wave 迁移时间）
- ❌ 不处理 `feat-fix-archive-gaps-v2` 第二轨道（ADR-0035 verifier-archive-gate 边界）
- ❌ 不修改 `.rddf/improvements/*.md` 现有 226 个文件
- ❌ 不修改其他阶段（design/plan/ship/verify）skill

---

## 2. 架构设计

### 2.1 Handoff Schema 修订 (v2.1 additive)

```jsonc
// .rddf/state/.arch-handoff.json — contract v2.1
{
  "version": 2,                              // 既有, 不变
  "arch_complete_revision": 7,               // NEW: 单调递增, 每次 write_arch_handoff +1
  "adr_dir": "docs/adr",
  "roadmap_path": "roadmap.md",
  "adr_pattern": "ADR-*.md",
  "discovered": { ... },
  // ...
}
```

**Schema 不 bump**: `_lib/schemas/arch_handoff_schema.json` 仅注释说明 `arch_complete_revision` 为 v2.1 可选 additive 字段。`version: 2` 不变。`additionalProperties: true` 已存在。

**兼容性**: 旧 consumer（无 `arch_complete_revision`）→ 视为 revision=0（向后兼容）。

### 2.2 planner_state Schema 修订 (Sub-task 0.0, additive)

```jsonc
// .rddf/state/.planner-state.json — contract v1.1 (additive, 不 bump const=1)
{
  "version": 1,                              // const=1 不变 (存量兼容)
  "state_revision": 5,                       // NEW: 语义哈希变化时 +1
  "current_sprint": "...",
  "last_sync_at": "...",
  // ...
}
```

**Schema 修订**（`planner_state_schema.json`）:
- 加 `properties.state_revision` (type: integer, optional, default: 0)
- **不** bump `"version": {"const": 1}` (否则 `read_state` 对存量文件抛 SchemaMismatchError)
- `additionalProperties: false` → 必须显式声明新字段

**`state_revision` 递增语义**（用户决策 **(b)**）:

```python
def _planner_state_semantic_hash(state: dict) -> str:
    """排除 timestamp / state_revision 本身的字段, 计算语义指纹."""
    semantic = {
        k: v for k, v in state.items()
        if k not in {"state_revision", "last_sync_at", "last_sync_status", "sprint_started_at"}
    }
    return hashlib.sha256(json.dumps(semantic, sort_keys=True).encode()).hexdigest()[:16]

def write_state(project_root: Path, state: dict) -> None:
    new_hash = _planner_state_semantic_hash(state)
    prior = read_state(project_root) or {}
    prior_hash = _planner_state_semantic_hash(prior)
    if new_hash != prior_hash:
        state["state_revision"] = prior.get("state_revision", 0) + 1
    # else: state_revision 不变
    # ... existing write logic
```

**Stale 触发矩阵**:

| arch_handoff_revision ↑ | state_revision ↑ | codebase_commit ↑ | stale? |
|---|---|---|---|
| ✓ | ✓ | ✓ | ✓ |
| ✓ | ✗ | ✓ | ✓ |
| ✗ | ✓ | ✓ | ✓ |
| ✗ | ✗ | ✓ | **✗** (修订前会 stale) |
| ✗ | ✗ | ✗ | ✗ |

### 2.3 Lifecycle Ops 修订 (atomic RMW, 无嵌套锁)

**修订后**:
```python
# _write_planner_feedback_unlocked (新增, 锁外可调)
def _write_planner_feedback_unlocked(data: dict) -> None:
    atomic_write_json(FEEDBACK_PATH, data)

# write_planner_feedback (保留, 薄包装)
def write_planner_feedback(data: dict) -> None:
    with FileLock(FEEDBACK_LOCK_PATH):
        _write_planner_feedback_unlocked(data)

# acknowledge_feedback (修订)
def acknowledge_feedback(feedback_id: str, by: str) -> FeedbackEntry:
    with FileLock(FEEDBACK_LOCK_PATH):                  # 外层锁
        state = read_planner_feedback_unlocked()         # 新增 unlocked reader
        entry = _find_entry(state, feedback_id)
        entry.acknowledge(by)
        _write_planner_feedback_unlocked(state)          # ✅ unlocked variant
    return entry
```

**关键约束** (MUST NOT DO):
- ❌ 在 `with FileLock(FEEDBACK_LOCK_PATH)` 临界区内**禁止**调 `write_planner_feedback` / `read_planner_feedback`（二者内部自带同锁，fcntl.flock per-fd 不可重入 → LockTimeout 10s）
- ❌ 在 `with FileLock(...)` 内**禁止**对同一路径二次 `with FileLock(...)`

### 2.4 feedback_id 稳定性 + 唯一性 (修订)

```python
def _next_feedback_id(date: str, prior_entries: list) -> str:
    """Counter 只分配给真新 fingerprint; 防御畸形 ID."""
    prefix = f"pf-{date}-"
    max_n = 0
    skipped = []
    for e in prior_entries:
        fid = e.get("feedback_id", "")
        if not isinstance(fid, str) or fid.count("-") != 2:
            skipped.append(fid or "<missing>")
            continue
        try:
            n = int(fid.rsplit("-", 1)[1])
            max_n = max(max_n, n)
        except (ValueError, IndexError):
            skipped.append(fid)
            continue
    if skipped:
        log.warning("Skipped %d malformed feedback_ids: %s", len(skipped), skipped[:5])
    return f"{prefix}{max_n + 1:03d}"
```

**merge 循环 (修订)**:
```python
for new_entry in new_feedbacks:
    prior_match = next(
        (e for e in prior_entries
         if e.get("fingerprint") == new_entry.fingerprint
         and e.get("status") not in ("resolved", "dismissed")),
        None,
    )
    if prior_match:
        # 保留 prior ID + last_seen_at (真幂等 + ID 稳定)
        as_dict = asdict(new_entry)
        as_dict["feedback_id"] = prior_match["feedback_id"]    # R9
        as_dict["last_seen_at"] = prior_match["last_seen_at"]  # R15
        as_dict["created_at"] = prior_match["created_at"]
    else:
        as_dict = asdict(new_entry)
        as_dict["feedback_id"] = _next_feedback_id(date, prior_entries)
    merged.append(as_dict)
```

### 2.5 闭环自动化 (Rev-Loop Hooks)

**触发点**（修订 R11）:
1. **planner sync --apply**: 在 `_lib/cli/planner_cmd.py:118` `_apply_state_with_warn(...)` 之后插 hook
2. **arch-done**: 在 `skills/rdd-arch/scripts/write_arch_handoff.sh`（bash wrapper）Python 调用成功后插 hook（bash 经 `_env.py` env-var 约定，不字符串插值）

**统一助手** (`_lib/planner_feedback.py`, 新增):
```python
def recompute_planner_feedback(project_root: Path) -> dict:
    """单 FileLock 临界区内 read → compute → write. 三处共用."""
    with FileLock(FEEDBACK_LOCK_PATH):
        prior = read_planner_feedback_unlocked()
        new_state = compute_planner_feedback(project_root, prior)
        _write_planner_feedback_unlocked(new_state)
    return new_state
```

**Hook 失败语义** (R4):
```python
# planner_cmd.py / write_arch_handoff.sh 中调用 recompute_planner_feedback 的包装:
def safe_recompute_planner_feedback(project_root: Path) -> None:
    """Hook 用: 失败 warn + 不抛异常."""
    try:
        recompute_planner_feedback(project_root)
    except Exception as e:
        print(f"WARNING: auto-feedback recompute failed: {e}", file=sys.stderr)
        log.exception("auto-feedback recompute failed")
        # 不 re-raise
```

**幂等保证** (修订后):
- `last_seen_at` 在 prior_match 时**保留 prior 值**（R15）→ 真幂等
- `created_at` 一直保留
- `feedback_id` 在 fingerprint 命中时保留 prior 值（R9）
- 文件 mtime 仅在语义变化时变化（R1 语义哈希 gate + R15 last_seen_at 保留）

### 2.6 Branch Helper 修订 (R3 修订)

```python
def _current_branch() -> str:
    """git rev-parse --abbrev-ref HEAD; 处理 detached HEAD + 非 git 环境."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=_project_root(),
            check=False,
        )
        if result.returncode != 0:
            return "unknown"
        branch = result.stdout.strip()
        if branch == "HEAD":                                    # detached HEAD
            return "detached"
        return branch or "unknown"
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return "unknown"
```

### 2.7 Resolved→Open Revival (文档化)

**当前行为** (Stage 3 L369 已实现, Wave 4 文档化): resolved + fingerprint 重现 → status=open, resolved_at/resolved_by **保留**.

**Wave 4 新增字段**: `reopened_count: int = 0` (default, 向后兼容旧文件).

**Wave 4 上线迁移预期** (R5):
- 首次 Change-0 writer 写入 arch_handoff_revision 0→N
- 下次 compute: 所有 prior-matched 条目 stale → resolved 条目**复活**为 open + reopened_count=1
- 历史 resolved 条目可能"一次性复活",需 ADR-0042 + release notes 公告
- `reopened_count >= 3` 触发 warning (反复复活 = 真实回归未修复)

### 2.8 KNOWN_FAILURES Shrink-Only CI (R6)

**复用现有机制** (`report_regression.sh` L27-34 sed strip 规则):
```bash
# .github/workflows/test.yml 新增步骤
- name: KNOWN_FAILURES shrink-only enforcement
  run: |
    set -e
    BASELINE=$(git show origin/master:tests/KNOWN_FAILURES.txt 2>/dev/null || git show HEAD~1:tests/KNOWN_FAILURES.txt)
    # 复用 report_regression.sh L27-34 sed strip 规则
    BASELINE_STRIPPED=$(echo "$BASELINE" | sed -E 's/#.*//' | sort -u)
    CURRENT_STRIPPED=$(sed -E 's/#.*//' tests/KNOWN_FAILURES.txt | sort -u)
    # diff: 允许修改注释行, 禁止新增失败行
    NEW_LINES=$(comm -13 <(echo "$BASELINE_STRIPPED") <(echo "$CURRENT_STRIPPED"))
    if [ -n "$NEW_LINES" ]; then
      echo "❌ KNOWN_FAILURES.txt grew (CI forbidden):"
      echo "$NEW_LINES"
      exit 1
    fi
```

---

## 3. Changes

### Change 0: arch_complete_revision + state_revision + 修订 Stale 检测

**Sub-task 0.0**: 创建 `state_revision` 全链路 (R1)

Files:
- `_lib/planner_state.py` (`_default_state` 加 `state_revision: int = 0`; `write_state` 加语义-diff 递增; 新增 `_planner_state_semantic_hash` helper)
- `_lib/schemas/planner_state_schema.json` (加 `state_revision` optional property; **不** bump const=1)
- `_lib/planner_feedback.py` (新增 `_current_planner_state_revision(project_root)` reader)
- `tests/unit/test_planner_state_revision_field.py` (新增)

**Sub-task 0.1**: arch_complete_revision writer (P0-1)

Files:
- `skills/rdd-arch/scripts/write_arch_handoff.py` (锁内读 prior + increment + 注入)
- `tests/unit/test_arch_handoff_revision.py` (新增)

**Sub-task 0.2**: Stale 检测改 2-revision (P0-1)

Files:
- `_lib/planner_feedback.py` (`compute_planner_feedback` stale 比较改用 `_current_arch_handoff_revision` + `_current_planner_state_revision`)
- `_lib/schemas/arch_handoff_schema.json` (注释说明 v2.1 additive)
- `docs/adr/ADR-0042-rdd-arch-rdd-planner-bidirectional-feedback.md` (修订 stale 章节)
- `docs/architecture/rdd-arch-rdd-planner-integration.md` (修订 stale 端到端示例)
- `tests/unit/test_planner_feedback_stale_revision_based.py` (新增)

**Sub-task 0.3**: arch-quality-gate 联动验证 (R12)

- Change 0 commit 1 后立即跑 `bash tests/scripts/check_arch_quality_gate.sh`(若存在) 或等价 pytest 测试, 验证 `_check_handoff_actionable` 对 `version: 2` + `arch_complete_revision: N` 输出无 warning
- 若失败: 在 Change 0 子任务里同步修 gate (L298 `version != 1` → `version not in [1, 2]`)

**MUST DO** (每 sub-task 独立 TDD 5 步):

**Sub-task 0.0 TDD**:
1. Write `tests/unit/test_planner_state_revision_field.py`:
   - `test_default_state_has_state_revision_zero`: 新建 state, `state_revision == 0`
   - `test_write_state_increments_on_semantic_change`: 改 unmapped_proposals 内容 → 写 → revision +1
   - `test_write_state_no_increment_on_timestamp_only`: 仅改 last_sync_at → 写 → revision 不变
   - `test_write_state_no_increment_on_identical_content`: 相同内容两次写 → revision 不变
   - `test_current_planner_state_revision_reader`: `_current_planner_state_revision(...)` 读出真实值
2. Run, expect 5 fail
3. Implement:
   - `_default_state()` 加 `"state_revision": 0`
   - `planner_state_schema.json` 加 `state_revision` (type: integer, optional)
   - `_planner_state_semantic_hash` helper
   - `write_state` / `update_state` 锁内: `if new_hash != prior_hash: state["state_revision"] = prior.get("state_revision", 0) + 1`
   - 新增 `_current_planner_state_revision(project_root)` reader
4. Verify pass
5. Commit: `feat(planner-state): add state_revision field with semantic-diff increment`

**Sub-task 0.1 TDD**:
1. Write `tests/unit/test_arch_handoff_revision.py`:
   - `test_write_increments_revision`: 写两次, revision 0→1→2
   - `test_first_write_revision_is_one`: 无 prior → revision=1
   - `test_revision_persists_in_handoff_dict`: 读回 handoff 包含字段
   - `test_revision_survives_concurrent_writes_via_lock`: 50 线程并发写, 最终 revision = 50
2. Run, expect 4 fail
3. Implement in `write_arch_handoff.py`:
   - 在 `FileLock` 临界区内: 读 prior handoff (JSON parse, 损坏则 log + 用 0 作 prior), `revision = prior.get("arch_complete_revision", 0) + 1`, 注入 `arch_complete_revision` 到 handoff dict
4. Verify pass
5. Commit: `feat(arch-handoff): write arch_complete_revision field per Wave 4`

**Sub-task 0.2 TDD**:
1. Write `tests/unit/test_planner_feedback_stale_revision_based.py`:
   - `test_stale_on_arch_handoff_revision_change`: 改 prior 的 computed_from.arch_handoff_revision → 旧条目 stale=True
   - `test_stale_on_state_revision_change`: 改 prior 的 computed_from.state_revision → 同上
   - `test_no_stale_when_both_revisions_unchanged`: 两 revision 不变 → 不 stale
   - `test_no_stale_on_doc_only_commit`: 仅 codebase_commit 变 → 不 stale
   - `test_stale_only_one_revision_change_sufficient`: 只需一个 revision 变化即可 stale
2. Run, expect 5 fail
3. Implement in `compute_planner_feedback`:
   - `prior_arch_rev = prior.get("computed_from", {}).get("arch_handoff_revision", 0)`
   - `current_arch_rev = _current_arch_handoff_revision()`
   - `prior_state_rev = prior.get("computed_from", {}).get("state_revision", 0)`
   - `current_state_rev = _current_planner_state_revision(project_root)`
   - `is_stale = (prior_arch_rev != current_arch_rev) or (prior_state_rev != current_state_rev)`
   - 保留 `codebase_commit` 在 `computed_from` (informational), **不**参与 stale 判断
4. Verify pass
5. Commit: `fix(planner-feedback): revise stale check from codebase_commit to 2-revision`

**Sub-task 0.3 (R12)**: Change 0 commit 1 后立即跑 arch-quality-gate, 若失败同步修 `_lib/arch_quality_gate.py:298`.

**MUST NOT DO**:
- ❌ 不 bump `arch_handoff.json::version: 2`
- ❌ 不 bump `planner_state_schema.json::version const=1`
- ❌ 不删除 `codebase_commit` 字段 (保留 informational)
- ❌ 不修改 `.arch-handoff.json` 其他字段
- ❌ 不破坏现有 consumer 读取路径

---

### Change 1: Lifecycle Atomic + ID Stability + Branch

**Sub-task 1.1**: Atomic lifecycle ops (P0-2 + R2 修订)

Files:
- `_lib/planner_feedback.py` (新增 `_write_planner_feedback_unlocked` + `read_planner_feedback_unlocked`; 4 个 op 全部用外层锁 + unlocked helper)
- `tests/unit/test_planner_feedback_lifecycle_atomic.py` (新增)

**Sub-task 1.2**: ID stability + uniqueness (P0-3 + R3 + R9 + R15)

Files:
- `_lib/planner_feedback.py::compute_planner_feedback` (merge 循环改: fingerprint 命中保留 prior ID + last_seen_at; 新增 `_next_feedback_id` defensive)
- `tests/unit/test_planner_feedback_id_uniqueness.py` (新增, 含畸形 ID 防御测试)

**Sub-task 1.3**: Branch helper (P1-2)

Files:
- `_lib/planner_feedback.py` (新增 `_current_branch()` helper; `_empty_schema` 和 `compute` 返回值改用 helper)
- `tests/unit/test_planner_feedback_branch.py` (新增, 含 detached HEAD + 非 git 环境)

**MUST DO**:

**Sub-task 1.1 TDD**:
1. Write `tests/unit/test_planner_feedback_lifecycle_atomic.py`:
   - `test_acknowledge_atomic_under_lock`: 50 线程并发 acknowledge 同一 ID → 最终 status=acknowledged
   - `test_resolve_atomic_under_lock`: 50 线程 resolve → status=resolved
   - `test_dismiss_atomic_under_lock`: 50 线程 dismiss → status=dismissed
   - `test_prune_resolved_atomic_under_lock`: 50 线程 prune → resolved/dismissed 全部清除
   - `test_concurrent_ack_and_resolve_no_lost_update`: 50 线程混合 ack/resolve → 最终状态 consistent
   - `test_no_nested_lock_deadlock`: 4 个 op 内调用链不超时 (< 1s)
2. Run, expect 6 fail
3. Implement:
   - 新增 `_write_planner_feedback_unlocked(data)` (内部调 `atomic_write_json`)
   - 新增 `read_planner_feedback_unlocked()` (内部调 `json.loads(FEEDBACK_PATH.read_text())`)
   - `write_planner_feedback(data)` 改为: `with FileLock(FEEDBACK_LOCK_PATH): _write_planner_feedback_unlocked(data)`
   - `read_planner_feedback()` 改为: `with FileLock(FEEDBACK_LOCK_PATH): return read_planner_feedback_unlocked()`
   - 4 个 op (acknowledge/resolve/dismiss/prune) 改为: `with FileLock(FEEDBACK_LOCK_PATH): state = read_planner_feedback_unlocked(); modify; _write_planner_feedback_unlocked(state)`
4. Verify pass (注意: 测试应 < 1s, 若 > 5s 说明嵌套锁死锁未解)
5. Commit: `fix(planner-feedback): make lifecycle ops atomic via FileLock + unlocked helpers`

**Sub-task 1.2 TDD**:
1. Write `tests/unit/test_planner_feedback_id_uniqueness.py`:
   - `test_same_day_recompute_no_collision`: prior 有 pf-YYYYMMDD-001 resolved, 当日 recompute → 新条目 pf-YYYYMMDD-002
   - `test_counter_starts_at_max_plus_one`: 3 个 prior pf-YYYYMMDD-005/003/007 → 新条目 pf-YYYYMMDD-008
   - `test_cross_day_independent_counter`: 跨日 prior -001/-002 + 当日新条目 -001 不撞号
   - `test_prior_id_preserved_on_fingerprint_match`: fingerprint 命中 → 新 entry feedback_id = prior_match["feedback_id"]
   - `test_malformed_id_skipped_in_counter`: 混入 pf-20260904-foo + pf-bad → counter 只算合法 pf-20260904-001
   - `test_missing_feedback_id_key_skipped`: entry 缺 feedback_id 字段 → 不崩, 跳过
2. Run, expect 6 fail
3. Implement in `compute_planner_feedback` (见 §2.4):
   - merge 循环: fingerprint 命中 → `as_dict["feedback_id"] = prior_match["feedback_id"]` + `as_dict["last_seen_at"] = prior_match["last_seen_at"]`
   - 新增 `_next_feedback_id(date, prior_entries)` (见 §2.4 防御实现)
4. Verify pass
5. Commit: `fix(planner-feedback): preserve prior feedback_id + last_seen_at on match, defensive counter`

**Sub-task 1.3 TDD**:
1. Write `tests/unit/test_planner_feedback_branch.py`:
   - `test_branch_uses_git_head`: 在 git repo 内 → branch = `git rev-parse --abbrev-ref HEAD` 输出
   - `test_branch_fallback_non_git`: mock subprocess 失败 → branch = "unknown"
   - `test_branch_detached_head_returns_detached`: git 返回 "HEAD" → branch = "detached"
   - `test_empty_schema_branch_uses_helper`: `_empty_schema()` 调用 helper 而非硬编码
2. Run, expect 4 fail
3. Implement `_current_branch()` (见 §2.6)
4. 替换 L229 (`_empty_schema`) 和 L390 (`compute` 返回) 硬编码 `"branch": "main"` 为 `_current_branch()`
5. Verify pass
6. Commit: `fix(planner-feedback): branch field uses git rev-parse, not hardcoded main`

**MUST NOT DO**:
- ❌ 修改 4 个 op 的公共 API (签名不变)
- ❌ 修改 fingerprint 算法
- ❌ 修改 feedback_id 字符串格式
- ❌ 在 `with FileLock(...)` 临界区内调 `write_planner_feedback` / `read_planner_feedback` (R2)

---

### Change 2: Sync + Arch-Done Hooks (闭环自动化)

**目标**: `planner sync --apply` 与 arch-done 自动 recompute feedback; `SKIP_AUTO_PLANNER_FEEDBACK=yes` opt-out; 失败不阻断主流程 (R4); 单锁 RMW (R10).

Files:
- `_lib/planner_feedback.py` (新增 `recompute_planner_feedback(project_root)` 助手 + `safe_recompute_planner_feedback(project_root)` 包装)
- `_lib/cli/planner_cmd.py` (在 L118 `_apply_state_with_warn(...)` 之后插 hook)
- `skills/rdd-arch/scripts/write_arch_handoff.sh` (Python 调用成功后插 hook)
- `skills/rdd-arch/scripts/_env.py` (env-var 传递: `SKIP_AUTO_PLANNER_FEEDBACK`, `PROJECT_ROOT`)
- `tests/integration/test_planner_sync_recomputes_feedback.bats` (新增)
- `tests/integration/test_arch_done_recomputes_feedback.bats` (新增)
- `tests/unit/test_planner_feedback_hook_failure_does_not_block.py` (新增, R4)

**MUST DO**:
1. Write `tests/integration/test_planner_sync_recomputes_feedback.bats`:
   - `@test "planner sync --apply triggers feedback recompute"`: 新建 .rddf/improvements/foo.md 无 theme_ref → sync 后 .planner-feedback.json 含 foo unmapped_proposal 反馈
   - `@test "SKIP_AUTO_PLANNER_FEEDBACK=yes opt-out"`: env var → 文件未更新
   - `@test "sync twice → feedback file content diff (除 last_seen_at) 为空"`: 真幂等 (R15)
2. Write `tests/integration/test_arch_done_recomputes_feedback.bats`:
   - `@test "rdd-arch arch-done triggers feedback recompute"`: mock write_arch_handoff → 验证 feedback 文件被刷新
   - `@test "arch-done SKIP_AUTO_PLANNER_FEEDBACK=yes opt-out"`: env var 跳过
   - `@test "arch-done twice → feedback identical (除 last_seen_at)"`: 真幂等
3. Write `tests/unit/test_planner_feedback_hook_failure_does_not_block.py`:
   - `test_recompute_planner_feedback_swallows_exceptions_via_safe_wrapper`: mock compute 抛异常 → `safe_recompute_planner_feedback` 不 re-raise
   - `test_sync_hook_does_not_propagate_exception`: mock 整个 recompute 抛异常 → cmd_sync 仍 exit 0
   - `test_arch_done_hook_does_not_propagate_exception`: mock bash wrapper exception → 主流程仍 success
4. Run, expect 9 fail (3+3+3)
5. Implement:
   - `_lib/planner_feedback.py::recompute_planner_feedback(project_root)` (见 §2.5)
   - `_lib/planner_feedback.py::safe_recompute_planner_feedback(project_root)` (见 §2.5)
   - `_lib/cli/planner_cmd.py:118` 之后插入:
     ```python
     if not os.environ.get("SKIP_AUTO_PLANNER_FEEDBACK"):
         safe_recompute_planner_feedback(project_root)
     ```
   - `skills/rdd-arch/scripts/write_arch_handoff.sh`: Python 调用成功后追加:
     ```bash
     if [ -z "$SKIP_AUTO_PLANNER_FEEDBACK" ]; then
       python3 -c "
     import os, sys
     from pathlib import Path
     sys.path.insert(0, os.environ['RDDF_PROJECT_ROOT'])
     from _lib.planner_feedback import safe_recompute_planner_feedback
     safe_recompute_planner_feedback(Path(os.environ['PROJECT_ROOT']))
     "
     fi
     ```
6. Verify pass
7. Commit: `feat(planner+arch): auto-recompute feedback on sync and arch-done (close loop)`

**MUST NOT DO**:
- ❌ 修改 `compute_planner_feedback` 公共 API
- ❌ 修改 feedback 文件 schema
- ❌ 不引入新 CLI 命令 (silent hook)
- ❌ 不改变 arch-done / sync 主流程返回值 (失败 warn + continue)
- ❌ 在 hook 处字符串插值调用 Python (Oracle C1 env-var 约定)
- ❌ 耦合到 design/plan/ship/verify 阶段

---

### Change 3: Cleanup (Dead Code, Doc Drift, KNOWN_FAILURES CI)

**目标**: 删 `stale_only` 死代码; 文档化 resolved-revival 语义 (R5); 修 write_arch_handoff docstring; KNOWN_FAILURES shrink-only CI (R6).

Files:
- `_lib/planner_feedback.py` (L384 删 `stale_only` 过滤; `FeedbackEntry` 加 `reopened_count: int = 0`; compute 中检测 resolved revival + increment reopened_count)
- `skills/rdd-arch/scripts/write_arch_handoff.py` L1 (docstring 改 canonical path)
- `docs/adr/ADR-0042-rdd-arch-rdd-planner-bidirectional-feedback.md` (新增 §X.X Resolved Revival 章节, 含 R5 迁移预期)
- `.github/workflows/test.yml` (新增 KNOWN_FAILURES shrink-only 步骤, R6)
- `tests/unit/test_planner_feedback_resolved_revival.py` (新增)
- `tests/integration/test_regression_baseline_shrink_only.bats` (新增)

**MUST DO**:
1. Write `tests/unit/test_planner_feedback_resolved_revival.py`:
   - `test_resolved_revival_flips_to_open_and_increments_count`: resolved + fingerprint 重现 → status=open + reopened_count=1 + resolved_at 保留
   - `test_dismissed_not_revival`: dismissed + fingerprint 重现 → 保持 dismissed (非对称)
   - `test_reopened_count_persists_across_computes`: 第二次 revive → reopened_count=2
   - `test_reopened_count_threshold_warning`: reopened_count >= 3 → entry 标 advisory_warning
2. Run, expect 4 fail
3. Implement:
   - `FeedbackEntry` 加 `reopened_count: int = 0` (default, 向后兼容)
   - compute L369 检测: resolved + fingerprint 命中 → `status = "open"`, `reopened_count = prior_match.get("reopened_count", 0) + 1`, `resolved_at`/`resolved_by` 保留
   - dismissed + fingerprint 命中 → 不复活 (clear doc)
   - 删 L384 `stale_only` 过滤
   - 新增 advisory: `reopened_count >= 3` → entry 加 `"advisory_warning": "high_reopen_count"`
4. Verify pass
5. Commit: `feat(planner-feedback): document resolved-revival semantics + add reopened_count`

6. Edit `write_arch_handoff.py` L1 docstring:
   - 改 `"""_lib/write_arch_handoff.py` 为 `"""skills/rdd-arch/scripts/write_arch_handoff.py`
7. Commit: `chore(arch-handoff): fix module docstring to canonical path`

8. Edit ADR-0042: 新增 §X.X "Resolved Revival Semantics" 章节, 明确:
   - 触发条件 + 状态转换 + resolved_at 保留语义
   - **Wave 4 上线迁移预期**: 首次 compute 后所有历史 resolved 条目一次性 reopened_count=1
   - reopened_count >= 3 advisory warning 触发条件
9. Commit: `docs(ADR-0042): add Resolved Revival Semantics section`

10. Edit `.github/workflows/test.yml` 加 KNOWN_FAILURES shrink-only 步骤 (见 §2.8)
11. Write `tests/integration/test_regression_baseline_shrink_only.bats`:
    - `@test "KNOWN_FAILURES.txt cannot grow vs origin/master"`: 临时修改文件加新行 → 跑 CI 步骤 → exit 1
    - `@test "KNOWN_FAILURES.txt can shrink (allowed)"`: 删行 → exit 0
    - `@test "KNOWN_FAILURES.txt comment-only changes allowed"`: 改注释 → exit 0
12. Verify pass
13. Commit: `chore(ci): add KNOWN_FAILURES.txt shrink-only enforcement via git-diff`

**MUST NOT DO**:
- ❌ 修改其他 stages 的 cleanup 债务 (Wave 4 仅限 planner_feedback + arch)
- ❌ 删除现有 dead code 测试 (Stage 3 引入)
- ❌ Wave 4 自身增长 `KNOWN_FAILURES.txt`
- ❌ 修改其他 docstring (仅修 `write_arch_handoff.py` L1)

---

## 4. 验证

### 4.1 单元测试 (`pytest tests/unit/`)

- 现有: 2625 passed, 4 skipped
- 预期新增: ~30 测试
  - `test_planner_state_revision_field.py`: 5
  - `test_arch_handoff_revision.py`: 4
  - `test_planner_feedback_stale_revision_based.py`: 5
  - `test_planner_feedback_lifecycle_atomic.py`: 6
  - `test_planner_feedback_id_uniqueness.py`: 6
  - `test_planner_feedback_branch.py`: 4
  - `test_planner_feedback_hook_failure_does_not_block.py`: 3
  - `test_planner_feedback_resolved_revival.py`: 4
- 预期总数: 2655+ passed

### 4.2 集成测试 (`pytest tests/integration/` + bats)

- 现有: 203 passed (.py) + 大量 bats
- 预期新增 bats:
  - `test_planner_sync_recomputes_feedback.bats`: 3
  - `test_arch_done_recomputes_feedback.bats`: 3
  - `test_regression_baseline_shrink_only.bats`: 3
- 预期 bats 增量: ~9

### 4.3 全量回归门

```bash
./test.sh --quick                                    # 必须 ALL PASSED (2655+ + 新测试)
./test.sh --full --regression                        # 必须 0 NEW failures
bash tests/scripts/report_regression.sh               # 必须 新增失败=0
bash tests/scripts/check_known_failures_shrink.sh     # 必须 KNOWN_FAILURES.txt 不增长
```

### 4.4 不变量

- `.rddf/improvements/` 226 个文件零触动
- AGENTS.md #25 identity 仍 True
- `_lib.write_arch_handoff` (canonical) / `skills.rdd-arch.scripts.write_arch_handoff` 引用一致 (docstring L1 修正后)
- `_lib.planner_feedback is skills._lib.planner_feedback` (identity merge shim 仍工作)

---

## 5. 风险

| 风险 | 缓解 |
|---|---|
| Schema 加字段 (`arch_complete_revision`, `state_revision`) 破坏旧 consumer | 字段为 additive optional, 旧 consumer 缺省 0; `additionalProperties: true/false` 已分别覆盖 |
| Stale 检测改语义 → 首次 Change-0 后所有 prior-matched 条目 stale | Sub-task 0.1 first-write revision=1 是设计选择; auto-hook (Change 2) 立即 recompute → stale 一次后清除 |
| Resolved revival 迁移潮: Wave 4 上线后所有 prior resolved 条目一次性 reopened_count=1 | ADR-0042 §X.X 文档化 + release notes 公告 + `reopened_count >= 3` warning |
| FileLock 嵌套死锁 (R2) | Change 1.1 MUST DO 显式禁止临界区内调 `write_planner_feedback`; 测试 `test_no_nested_lock_deadlock` 锁定 |
| Hook 增加 sync/arch-done 延迟 | `recompute_planner_feedback` 纯函数 + 文件读, < 200ms; 主流程延迟 < 300ms |
| FileLock 临界区测试 flakiness | `concurrent.futures.ThreadPoolExecutor` + 共享 `tmp_path` function-scoped fixture |
| KNOWN_FAILURES shrink-only CI 在 baseline 已有 pre-existing 时误报 | 只检测"当前 vs origin/master" diff; 允许 shrink + 注释修改, 禁止新增 |
| arch-quality-gate version check (R12) 与 Change 0 writer 冲突 | Sub-task 0.3 立即验证; 若失败同步修 gate L298 |

---

## 6. 实施时间线 (粗估)

| Change | 估计工时 | 关键 commit |
|---|---|---|
| Change 0 (Sub-task 0.0/0.1/0.2/0.3) | 3h | 3 commits |
| Change 1 (Sub-task 1.1/1.2/1.3) | 2.5h | 3 commits |
| Change 2 | 1.5h | 1 commit |
| Change 3 | 1.5h (含 CI 步骤 + ADR 修订) | 4 commits |
| 验证 | 0.5h | n/a |
| **总计** | **~9h** | **11 commits** |

---

## 7. 实施契约 (commit-by-commit)

按以下顺序合入 master, 每步 TDD 5 步独立可验证:

```
1.  feat(planner-state): add state_revision field with semantic-diff increment
2.  feat(arch-handoff): write arch_complete_revision field per Wave 4
3.  fix(planner-feedback): revise stale check from codebase_commit to 2-revision
4.  fix(planner-feedback): make lifecycle ops atomic via FileLock + unlocked helpers
5.  fix(planner-feedback): preserve prior feedback_id + last_seen_at on match, defensive counter
6.  fix(planner-feedback): branch field uses git rev-parse, not hardcoded main
7.  feat(planner+arch): auto-recompute feedback on sync and arch-done (close loop)
8.  feat(planner-feedback): document resolved-revival semantics + add reopened_count
9.  chore(arch-handoff): fix module docstring to canonical path
10. docs(ADR-0042): add Resolved Revival Semantics section
11. chore(ci): add KNOWN_FAILURES.txt shrink-only enforcement via git-diff
```

每个 commit 后跑 `./test.sh --quick` 确认不破坏既有测试.

---

## 8. 关闭 Wave 4 的判据

- [ ] 11 commits 已合入 master
- [ ] pytest unit 2655+ passed
- [ ] pytest integration 203+ passed + 9 新 bats passed
- [ ] `./test.sh --full --regression` 0 NEW failures
- [ ] KNOWN_FAILURES.txt 未增长
- [ ] `.rddf/improvements/` 226 文件零修改
- [ ] AGENTS.md #25 identity assertion True
- [ ] Oracle final review (post-Wave 4) 没有新增 P0 缺陷

---

> **Next**: 用户审批 → 执行 11 commits → 单波回归门 → 汇总。