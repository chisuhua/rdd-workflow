# Archive cleanup plan files — 技术设计

## 设计目标

在 archive 完成后自动删除 `.rddf/plans/<change_name>.md`，并在 scan-state.sh 中增加孤立计划文件检测，防止孤立文件累积。

## 实现方案

### 变更 1: `ship_archive.sh` 新增 `cleanup_plan_file()` 函数

在 `skills/guide-ship/scripts/ship_archive.sh` 中新增函数，在 `archive_change_for_mode()` 末尾（`cleanup_plan_handoff` 之后）调用：

```bash
# cleanup_plan_file <project_root> <change_name>
#   归档完成后清理 .rddf/plans/<change_name>.md。
#   幂等：文件不存在时返回 0（无错误）。
#   严格作用域：仅操作 .rddf/plans/<change_name>.md 路径。
cleanup_plan_file() {
  local project_root="$1"
  local change_name="$2"
  local plan_file="$project_root/.rddf/plans/${change_name}.md"

  [ -f "$plan_file" ] || return 0  # 幂等：文件不存在则跳过

  rm -f "$plan_file"
  echo "✅ 已清理计划文件: .rddf/plans/${change_name}.md"
}
```

**集成位置**：在 `archive_change_for_mode()` 末尾，`cleanup_plan_handoff` 之后：

```bash
  # Cleanup plan handoff after archive
  cleanup_plan_handoff "$project_root" "$change_name" || true

  # Cleanup plan file after archive (新增)
  cleanup_plan_file "$project_root" "$change_name" || true
}
```

**设计理由**：
- 放在 `archive_change_for_mode()` 末尾（统一 funnel），worktree 和 lightweight 两种模式都受益
- 使用 `|| true` 包裹，与 `cleanup_plan_handoff` 保持一致的容错模式
- 先检查文件存在性再删除，幂等安全
- 只删除 `.<name>.md` 精确匹配，不 glob 遍历目录

### 变更 2: `scan-state.sh` 新增 `check_orphan_plan_files()` 函数

在 `skills/guide/scripts/scan-state.sh` 中新增函数，在 `scan_state()` 末尾（`check_arch_handoff_stale` 之后）调用：

```bash
# check_orphan_plan_files <project_root>
#   扫描 .rddf/plans/ 中的计划文件，检测孤立文件（其对应 change 已归档或不存在）。
#   输出 warning 级别信息（不阻塞流程），包含文件名列表和计数。
#   通过检查 openspec/changes/<name>/ 目录是否存在来判断。
#   只读：不修改任何文件。
check_orphan_plan_files() {
  local project_root="$1"
  local plans_dir="$project_root/.rddf/plans"

  [ -d "$plans_dir" ] || return 0

  local orphan_count=0
  local orphan_list=""

  for plan_file in "$plans_dir"/*.md; do
    [ -f "$plan_file" ] || continue
    local basename
    basename=$(basename "$plan_file" .md)
    local change_dir="$project_root/openspec/changes/$basename"

    # 检查 change 目录是否存在且非归档
    if [ ! -d "$change_dir" ]; then
      # 再检查是否在 archive 目录中
      if ! ls "$project_root/openspec/changes/archive/"*-"$basename" >/dev/null 2>&1; then
        orphan_count=$((orphan_count + 1))
        orphan_list="$orphan_list  - $basename"$'\n'
      fi
    fi
  done

  if [ "$orphan_count" -gt 0 ]; then
    echo "⚠️  发现 $orphan_count 个孤立计划文件 (.rddf/plans/):"
    echo "$orphan_list"
    echo "   (对应 change 已归档或不存在，可手动删除)"
  fi
}
```

**集成位置**：在 `scan_state()` 末尾，`check_arch_handoff_stale` 之后：

```bash
  check_stale_workflow_state "$PROJECT_ROOT"
  check_working_tree_cleanliness "$PROJECT_ROOT"
  check_arch_handoff_stale "$PROJECT_ROOT"
  check_orphan_plan_files "$PROJECT_ROOT"  # 新增
```

**设计理由**：
- 只读操作：不修改任何文件，仅输出 warning
- 使用 `ls openspec/changes/archive/` 检查归档状态，与现有归档目录结构一致
- 精确匹配 change 名称，不误判
- 输出文件名列表，便于用户手动清理

### 变更 3: 测试文件

新增 `tests/integration/test_archive_cleanup_plan_files.bats`：

```
@test "archive_cleanup_plan_files: archive 完成后自动删除计划文件"
@test "archive_cleanup_plan_files: scan-state 检测到孤立计划文件"
@test "archive_cleanup_plan_files: 无孤立文件时不输出 warning"
@test "archive_cleanup_plan_files: 删除操作幂等（文件不存在时跳过）"
```

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `skills/guide-ship/scripts/ship_archive.sh` | 修改 | 新增 `cleanup_plan_file()` 函数，在 `archive_change_for_mode()` 末尾调用 |
| `skills/guide/scripts/scan-state.sh` | 修改 | 新增 `check_orphan_plan_files()` 函数，在 `scan_state()` 末尾调用 |
| `tests/integration/test_archive_cleanup_plan_files.bats` | 新增 | 4 个 bats 测试覆盖 |

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 误删活跃 change 的计划文件 | 只在 archive 完成后执行删除（change 已无活跃状态）；文件名精确匹配，不 glob 遍历 |
| 孤立文件检测误判（将正常文件判为孤立） | 双重检查：先检查 `openspec/changes/<name>/` 目录，再检查 `archive/*-<name>` 目录 |
| scan-state.sh 性能影响 | 只扫描 `.rddf/plans/` 一个目录，通常 < 10 个文件，性能开销可忽略 |