# fix-lsp-dash-bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 pyright LSP 对 `skills.guide_arch`、`skills.guide_plan`、`skills.rddf_session` 等带连字符目录的 import 解析错误

**Architecture:** 3 个带连字符目录（guide-arch, guide-plan, rddf-session）已通过 conftest.py dash-bridge 在运行时正确映射，但 pyright LSP 不执行 conftest.py 所以报 "Import could not be resolved"。方案：在 pyrightconfig.json 中补全所有带连字符目录的 executionEnvironments 配置，使 pyright 将每个目录视为独立执行环境

**Tech Stack:** pyright (LSP), Python 3.11+, bash 验证脚本

---

## File Structure

| File | Responsibility |
|---|---|
| `pyrightconfig.json` | 添加缺失的 executionEnvironments 条目 + extraPaths |
| `skills/guide-arch/__init__.py` | 已有，无需修改 |
| `skills/guide-plan/__init__.py` | 已有，无需修改 |
| `skills/rddf-session/__init__.py` | 已有，无需修改 |
| `skills/rdd-workflow-writing-plans/__init__.py` | 已有，可能需要追加 |

---

### Task 1: 更新 pyrightconfig.json executionEnvironments

**Files:**
- Modify: `pyrightconfig.json`

- [ ] **Step 1: 验证当前 LSP 错误存在**

```bash
# 在 tests/ 中搜索包含 rddf_session 或 guide_arch 导入的文件
grep -rn "from skills\.\(rddf_session\|guide_arch\|guide_plan\)" tests/ --include="*.py" | wc -l
# 预期: 返回 > 0，确认需要修复的导入存在
```

- [ ] **Step 2: 运行现有测试确认代码正确**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_rddf_session.py tests/unit/test_guide_arch_metadata.py tests/unit/test_guide_plan_metadata.py -q --tb=short
# 预期: ALL PASS（运行时正常）
```

- [ ] **Step 3: 更新 pyrightconfig.json — 增加缺失 executionEnvironments**

```json
{
  "include": ["skills", "tests"],
  "exclude": ["**/node_modules", "**/__pycache__", "skills/**/archive"],
  "extraPaths": ["."],
  "executionEnvironments": [
    {"root": "skills/rddf-session"},
    {"root": "skills/guide-arch"},
    {"root": "skills/guide-plan"},
    {"root": "skills/guide-ship"},
    {"root": "skills/rdd-workflow-writing-plans"},
    {"root": "skills/feature"},
    {"root": "skills/propose"},
    {"root": "skills/deps"},
    {"root": "skills/execute"},
    {"root": "skills/status"},
    {"root": "skills/roadmap"},
    {"root": "skills/guide"}
  ]
}
```

新增: `rdd-workflow-writing-plans`、`feature`、`propose`、`deps`、`execute`、`status`、`roadmap`、`guide` — 覆盖所有 skills/ 子目录

- [ ] **Step 4: 验证 LSP 不再报告导入错误**

```bash
# 重启 LSP 后，检查关键文件
# 手动验证：打开 tests/unit/test_rddf_session.py 确认第9行不再有红色波浪线
echo "手动验证: 检查 tests/unit/test_rddf_session.py LSP 诊断"
```

- [ ] **Step 5: 运行完整测试确认无回归**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -3
# 预期: ALL PASS（57 个测试）
```

- [ ] **Step 6: Commit**

```bash
git add pyrightconfig.json
git commit -m "fix: add missing executionEnvironments to pyrightconfig.json for LSP dash-bridge

Add executionEnvironments for all skills/ subdirectories to fix pyright
'Import could not be resolved' errors when importing from directories
with hyphens (guide-arch, rddf-session, etc.)"
```

---

### Task 2: 添加 __init__.py 到缺失的 skills/ 子目录

**Files:**
- Create: `skills/guide/__init__.py`
- Create: `skills/feature/__init__.py`
- Create: `skills/propose/__init__.py`
- Create: `skills/deps/__init__.py`
- Create: `skills/execute/__init__.py`
- Create: `skills/status/__init__.py`
- Create: `skills/roadmap/__init__.py`

- [ ] **Step 1: 列出缺失 __init__.py 的目录**

```bash
cd /workspace/project/rdd-workflow
for d in skills/*/; do
    name=$(basename "$d")
    [ "$name" = "__pycache__" ] && continue
    [ -f "$d/__init__.py" ] && echo "✅ $name" || echo "❌ $name"
done
# 预期: guide, feature, propose, deps, execute, status, roadmap 标记为 ❌
```

- [ ] **Step 2: 创建 __init__.py 文件**

```bash
cd /workspace/project/rdd-workflow
for dir in skills/guide skills/feature skills/propose skills/deps skills/execute skills/status skills/roadmap; do
    echo "# Package marker for LSP import resolution" > "$dir/__init__.py"
    echo "✅ $dir/__init__.py"
done
```

- [ ] **Step 3: 验证创建成功**

```bash
cd /workspace/project/rdd-workflow
for d in skills/guide skills/feature skills/propose skills/deps skills/execute skills/status skills/roadmap; do
    [ -f "$d/__init__.py" ] && echo "✅ $d" || echo "❌ $d MISSING"
done
```

- [ ] **Step 4: 运行测试验证无回归**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -3
# 预期: ALL PASS
```

- [ ] **Step 5: Commit**

```bash
git add skills/guide/__init__.py skills/feature/__init__.py skills/propose/__init__.py \
        skills/deps/__init__.py skills/execute/__init__.py skills/status/__init__.py \
        skills/roadmap/__init__.py
git commit -m "fix: add __init__.py to all skills/ subdirectories for LSP resolution

All skills/ subdirectories that export Python modules now have __init__.py
markers, enabling pyright to properly resolve package imports."
```