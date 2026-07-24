# add-session-progress-view Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task.

**Goal:** 添加 rddf-session progress 子命令，展示 Wave 执行和归档进度

**Architecture:** 新增 `progress` 子命令到 rddf-session，读取 iteration.json + sessions.json 生成格式化进度视图

**Tech Stack:** Python 3.11+, bash (rddf-session entry), iteration.json, sessions.json

---

### Task 1: 添加 progress 子命令到 rddf-session

**Files:**
- Modify: `skills/rddf-session/scripts/rddf_session_pkg/_commands.py`
- Modify: `skills/rddf-session/SKILL.md`

- [ ] **Step 1: 验证当前 rddf-session 子命令**

```bash
cd /workspace/project/rdd-workflow
# 检查已有的子命令
grep -n "subcommand\|case.*in" skills/rddf-session/SKILL.md | head -10
```

- [ ] **Step 2: 在 _commands.py 中添加 progress 命令**

```python
def cmd_progress(sessions_file: str, project_root: str) -> str:
    """Display wave execution progress and archive status."""
    from ._types import RddfSessionCoordinator
    import os, json
    
    coord = RddfSessionCoordinator(sessions_file=sessions_file)
    sessions = coord.list_sessions()
    
    # Read iteration.json
    iter_path = os.path.join(project_root, ".rddf", "state", "iteration.json")
    try:
        with open(iter_path) as f:
            iteration = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        iteration = {"changes": []}
    
    lines = []
    lines.append("📊 Session Progress View")
    lines.append(f"{'session_id':<20} {'state':<12} {'changes':<10} {'wave':<8}")
    lines.append("-" * 60)
    for s in sessions:
        lines.append(f"{s.session_id:<20} {s.state:<12} {len(s.attached_changes):<10}")
    return "\n".join(lines)
```

- [ ] **Step 3: 在 SKILL.md 中注册 progress 子命令**

在 rddf-session/SKILL.md 的 Subcommands 列表中添加 `progress`

- [ ] **Step 4: 运行测试验证**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_rddf_session.py -q --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add skills/rddf-session/
git commit -m "feat(rddf-session): add progress subcommand for wave/archive status"
```