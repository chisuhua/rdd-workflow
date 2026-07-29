# Pre-checkout Warning — 技术设计

## 设计目标

在 guide 入口扫描阶段，检测关键文件（proposal-suggestions.md、proposal-approved.md）是否有未提交的更改，若有则显示警告，防止用户执行 `git checkout -- .` 等破坏性操作时丢失数据。

## 实现方案

### 1. 脏检查函数 (`skills/_lib/state.sh`)

新增函数 `check_dirty_key_files()`：

```bash
# 检查 proposal-suggestions.md 和 proposal-approved.md 是否有未提交更改
# 输出: 若脏则显示警告信息，返回 0（仅警告，不阻塞）
check_dirty_key_files() {
    local project_root="${1:-$(git rev-parse --show-toplevel)}"
    local dirty_files=""
    
    for f in "proposal-suggestions.md" "proposal-approved.md"; do
        if git -C "$project_root" diff --name-only -- "$f" | grep -q "$f"; then
            dirty_files="$dirty_files $f"
        fi
    done
    
    if [ -n "$dirty_files" ]; then
        echo "⚠️  关键文件有未提交更改:$dirty_files"
        echo "   建议: git add$dirty_files && git commit -m \"save\""
        echo "    避免 git checkout -- . 回滚丢失数据"
    fi
}
```

### 2. 集成到 `guide/scan-state.sh`

在 scan-state.sh 的路径 4/5（展示 guide-ship/guide-plan 选项之前）插入脏检查调用：

```bash
# 在列出可选项之前，检查关键文件完整性
check_dirty_key_files "$PROJECT_ROOT"
```

### 3. 技术约束

- **轻量**: 仅使用 `git diff --name-only`，不涉及文件内容比较
- **非阻塞**: 仅显示警告，不阻止后续操作
- **自动执行**: 在 guide 入口扫描时自动执行，无需用户手动触发

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `skills/_lib/state.sh` | 修改 | 新增 `check_dirty_key_files()` 函数 |
| `skills/guide/scan-state.sh` | 修改 | 在路径 4/5 调用脏检查 |