# improve-openspec-test-change-support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** 支持 test-only / doc-only / refactor-only 类型的 change，自动同步 tasks.md 进度

**Architecture:** 在 roadmap-meta.yaml 中新增 `change_type` 字段区分 change 类型；execute 阶段自动标记 tasks.md；archive 阶段对非 feature 类型跳过 delta 校验

**Tech Stack:** Python 3.11+, bash, YAML (roadmap-meta.yaml), bash (tasks.md sync)

---

## File Structure

| File | Responsibility |
|---|---|
| `skills/propose/scripts/propose_change.py` | 新增 `change_type` 字段写入 roadmap-meta.yaml |
| `skills/execute/scripts/tasks_writeback.sh` | 已有，execute 自动回写 tasks.md（无需改） |
| `skills/execute/SKILL.md` | 确保 execute 阶段显式同步 tasks.md |
| `skills/_lib/archive.sh` | archive 时读取 change_type 跳过 delta 检查 |
| `skills/_lib/schemas/` | 更新 roadmap-meta schema（可选） |

---

### Task 1: 新增 change_type 字段到 roadmap-meta.yaml

**Files:**
- Modify: `skills/propose/scripts/propose_change.py`

- [ ] **Step 1: 验证当前 roadmap-meta.yaml 结构**

```bash
cd /workspace/project/rdd-workflow
# 检查一个已有的 roadmap-meta.yaml
cat openspec/changes/improve-openspec-test-change-support/roadmap-meta.yaml 2>/dev/null || echo "(文件不存在，需创建)"
```

- [ ] **Step 2: 修改 propose_change.py — 添加 change_type 参数和写入逻辑**

在 `update_roadmap_meta()` 函数中添加 `change_type` 参数（默认 `feature`），写入 roadmap-meta.yaml：

```python
def update_roadmap_meta(...):
    # 新增字段
    meta['change_type'] = os.environ.get('CHANGE_TYPE', 'feature')
    # ... existing code ...
```

验证：运行 `python3 -c "from skills.propose.scripts.propose_change import update_roadmap_meta; print('OK')"`

- [ ] **Step 3: 运行现有测试确认无回归**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/ -q --tb=short -k "propose" 2>&1 | tail -3
# 预期: ALL PASS
```

- [ ] **Step 4: Commit**

```bash
git add skills/propose/scripts/propose_change.py
git commit -m "feat: add change_type field to roadmap-meta.yaml (feature/test-only/doc-only/refactor-only)"
```

---

### Task 2: execute 阶段自动同步 tasks.md

**Files:**
- Modify: `skills/execute/scripts/tasks_writeback.sh`

- [ ] **Step 1: 验证 execute Step 5 已有 commit 后自动 mark**

```bash
cd /workspace/project/rdd-workflow
grep -n "tasks_writeback\|mark_task\|tasks.md" skills/execute/scripts/tasks_writeback.sh | head -5
# 预期: 已有 mark_task_done / mark_all_tasks_done 函数
```

- [ ] **Step 2: 增强 tasks_writeback.sh — 添加 post-commit hook**

在 `tasks_writeback.sh` 中添加 `auto_sync_on_commit()` 函数，在 execute Phase 末尾自动调用：

```bash
auto_sync_on_commit() {
    local change_name="$1"
    # Read tasks.md, mark all unchecked items as done
    if [ -f "openspec/changes/$change_name/tasks.md" ]; then
        sed -i 's/^- \[ \]/- [x]/' "openspec/changes/$change_name/tasks.md"
        echo "✅ tasks.md 自动同步完成: $change_name"
    fi
}
```

- [ ] **Step 3: Commit**

```bash
git add skills/execute/scripts/tasks_writeback.sh
git commit -m "feat: auto-sync tasks.md on execute completion"
```

---

### Task 3: archive 阶段跳过非 feature 类型的 delta 检查

**Files:**
- Modify: `skills/_lib/archive.sh`

- [ ] **Step 1: 在 archive.sh 中添加 change_type 检查**

在 `archive_change()` 函数中，merge 之前检查 roadmap-meta.yaml 的 `change_type`：

```bash
# Check change_type before archive
ROADMAP_META="openspec/changes/$CHANGE_NAME/roadmap-meta.yaml"
if [ -f "$ROADMAP_META" ]; then
    CHANGE_TYPE=$(python3 -c "import yaml; print(yaml.safe_load(open('$ROADMAP_META')).get('change_type', 'feature'))" 2>/dev/null || echo "feature")
    case "$CHANGE_TYPE" in
        test-only|doc-only|refactor-only)
            echo "ℹ️  跳过 delta 检查（change_type=$CHANGE_TYPE）"
            ;;
    esac
fi
```

- [ ] **Step 2: 验证 archive 流程无影响**

```bash
cd /workspace/project/rdd-workflow
# 手动测试：检查 archive.sh 语法
bash -n skills/_lib/archive.sh && echo "✅ 语法正确"
```

- [ ] **Step 3: Commit**

```bash
git add skills/_lib/archive.sh
git commit -m "feat: skip delta check for test-only/doc-only/refactor-only changes during archive"
```