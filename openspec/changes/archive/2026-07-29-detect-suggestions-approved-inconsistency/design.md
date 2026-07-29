# Detect suggestions-approved inconsistency — 技术设计

## 设计目标

在 `guide_entry` 的入口扫描阶段，检测 `proposal-suggestions.md` 中标记为 "completed" 的条目是否在 `proposal-approved.md` 中有对应的批准记录。若无，输出警告，提示审计追溯缺失。

## 实现方案

### 1. 检测函数 (`skills/_lib/state.sh`)

新增函数 `detect_approved_inconsistency()`：

```bash
# 检测 proposal-suggestions.md 中 "completed" 条目是否在 proposal-approved.md 中有对应记录
# 输出: 若不一致则显示警告信息，返回 0（仅警告，不阻塞）
detect_approved_inconsistency() {
    local project_root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
    local suggestions_file="$project_root/proposal-suggestions.md"
    local approved_file="$project_root/proposal-approved.md"
    
    [ ! -f "$suggestions_file" ] && return 0
    
    PY_SUGGESTIONS="$suggestions_file" PY_APPROVED="$approved_file" python3 -c '
import os, re, sys

suggestions_file = os.environ["PY_SUGGESTIONS"]
approved_file = os.environ["PY_APPROVED"]

try:
    # Read suggestions; check for "completed" in the 4th column (time/status)
    with open(suggestions_file) as f:
        suggestions = f.read()
    
    # Extract suggestion entries: | [name](path) | priority | source | status |
    # Status is in the 4th column — may be a date or "completed"
    sug_entries = set()
    for m in re.finditer(r"\|\s*\[([^\]]+)\]\(improvements/[^)]+\)\s*\|\s*\S+\s*\|\s*\S+\s*\|\s*(\S+)", suggestions):
        name = m.group(1).strip()
        status = m.group(2).strip()
        if status == "completed" or status == "已完成":
            sug_entries.add(name)
    
    if not sug_entries:
        sys.exit(0)
    
    # Read approved file if it exists
    approved_names = set()
    if os.path.isfile(approved_file):
        with open(approved_file) as f:
            content = f.read()
        approved_names = set(re.findall(r"\|\s*\[([^\]]+)\]\(improvements/", content))
    
    # Find inconsistencies: completed in suggestions but not in approved
    missing = sug_entries - approved_names
    if missing:
        names_str = ", ".join(sorted(missing))
        print(f"⚠️  {len(missing)} 个 suggestions 标记已完成但无 approved 记录: {names_str}")
        print("   建议审计: 检查这些 change 是否已归档，或通过 guide-arch 补充批准")
except Exception:
    pass
' 2>/dev/null
}
```

### 2. 集成到 `guide_entry.sh` 的扫描输出

在 `guide_entry.sh` 的 `guide_entry()` 函数中，在打印项目状态概览之后、`scan_session_binding` 之前，插入一致性检测调用：

```bash
# 在项目状态概览后检测 suggestions-approved 不一致
detect_approved_inconsistency "$PROJECT_ROOT"
```

### 3. 技术约束

- **轻量**: 仅解析 Markdown 表格，不涉及文件内容深度比较
- **非阻塞**: 仅显示警告，不阻止后续操作
- **自动执行**: 在 guide 入口扫描时自动执行，无需用户手动触发
- **静默退场**: 若 `proposal-suggestions.md` 不存在，直接返回 0 无输出

## 数据流

```
guide_entry.sh
  └─ scan_state()                    # 扫描项目状态，生成推荐
  └─ 打印项目状态概览 (roadmap/arch/plan handoff)
  └─ detect_approved_inconsistency() # 检测 suggestions≁approved 不一致
  └─ scan_session_binding()          # 扫描 session 绑定
```

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `skills/_lib/state.sh` | 修改 | 新增 `detect_approved_inconsistency()` 函数 |
| `skills/guide/scripts/guide_entry.sh` | 修改 | 在 `guide_entry()` 中调用一致性检测 |