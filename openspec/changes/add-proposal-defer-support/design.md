# Add proposal defer support — 技术设计

## 设计目标

在 `improvements/<name>.md` 元数据中持久化延迟状态，使 guide-arch Phase 5.5 默认跳过已推迟提案，并支持 `a`（show all）查看全部。

## 根因分析

当前 `arch_proposal_review.sh` 的延迟机制存在两个问题：

### 问题 1：延迟状态不持久

`arch_proposal_review.sh` L318-L325 的 `d` 选项仅写入 `proposal-suggestions.md`：
```bash
sed -i "s/\(\[$name\].[^|]*|[^|]*|[^|]*|\)[^|]*/\1 ⏳ 已延迟 ($timestamp)/" "$SUGGESTIONS_FILE"
```

但 Step 2 构建候选列表时（L88-L112），**只从 `improvements/` 目录扫描文件**，`proposal-suggestions.md` 仅在 Step 3 的状态过滤中检查（L130-L133）：
```bash
if echo "$status" | grep -qiE 'rejected|已拒绝|deferred|已延迟'; then
  continue
fi
```

这意味着：如果提案已在 `improvements/` 中存在但**未在 `proposal-suggestions.md` 注册**，延迟状态永远不会被读取。

### 问题 2：`list_improvements()` 不输出状态

`state.sh` L108-L123 的 `list_improvements()` 只输出 `name|priority|source`，调用方无法获取延迟状态。

## 修复策略

### 方案 A（推荐）：在 `improvements/<name>.md` 中持久化状态

在 improvement 文件的元数据中增加 `**状态**` 和 `**推迟原因**` 字段，`arch_proposal_review.sh` 直接从文件读取，文件系统是权威数据源。

**优点**：
- 状态随 improvement 文件一起版本控制
- 不依赖 `proposal-suggestions.md` 的格式
- 向后兼容：无 `**状态**` 字段视为 `待讨论`
- 用户可直接编辑文件修改状态

### 方案 B（备选）：仅依赖 `proposal-suggestions.md` 状态

强化对 `proposal-suggestions.md` 的读取，确保所有提案都在 suggestions 注册。

**缺点**：
- `proposal-suggestions.md` 是派生视图，不是权威数据源
- 格式复杂，用户不易直接编辑
- 需要修改 `add-improve` 确保所有提案注册到 suggestions

### 选择：方案 A

## 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `skills/_lib/state.sh` | `list_improvements()` 增加 `**状态**` 字段读取，输出 4 段格式 |
| `skills/guide-arch/scripts/arch_proposal_review.sh` | 读取 `**状态**`，默认跳过已推迟，新增 `a` 显示全部，`d` 决策写入文件 |

## 改进格式

### improvements/<name>.md 新元数据格式

```markdown
# add-proposal-defer-support

**优先级**: P1 | **来源**: ...
**阶段**: default | **分类**: general
**类型**: feature
**状态**: 待讨论          ← 新增（可选，缺省=待讨论）
**推迟原因**:            ← 新增（可选，仅在状态=已推迟时使用）
```

### 状态值

| 状态 | 含义 | Phase 5.5 行为 |
|------|------|----------------|
| 待讨论 | 默认，等待审查 | 正常展示 |
| 已推迟 | 已评估但决定推迟 | 默认隐藏，`a` 展示全部时显示 |
| 已完成 | 已实施完成 | 默认隐藏（与 `proposal-approved.md` → `已实施` 联动） |

## 详细修改

### 1. `list_improvements()` 在 state.sh

```bash
# 在现有 priority 和 source 提取后增加
local status=$(grep -m1 '^\*\*状态\*\*:' "$f" 2>/dev/null | sed 's/.*\*\*状态\*\*: *//' | cut -d'|' -f1 | xargs)
echo "${name}|${priority:-?}|${source:-?}|${status:-待讨论}"
```

### 2. `arch_proposal_review.sh` Step 3 分类逻辑

在 PENDING_PROPS 构建循环中，增加从 improvement 文件读取 `**状态**` 字段：

```bash
# 在 priority 和 source 提取后增加
local file_status=$(grep -m1 '^\*\*状态\*\*:' "$imp_file" 2>/dev/null | sed 's/.*\*\*状态\*\*: *//' | cut -d'|' -f1 | xargs)
file_status="${file_status:-待讨论}"

# 已推迟 → 跳过（除非 show_all 模式）
if [ "$file_status" = "已推迟" ] && [ "${SHOW_ALL:-false}" != "true" ]; then
  DEFERRED_COUNT=$((DEFERRED_COUNT + 1))
  continue
fi
```

### 3. `arch_proposal_review.sh` Step 4 展示

在 `📋 待审查: N 个` 行之后增加：

```bash
if [ "$DEFERRED_COUNT" -gt 0 ]; then
  echo "⏸️ 已推迟: $DEFERRED_COUNT 个（按 a 查看全部）"
fi
```

### 4. `arch_proposal_review.sh` Step 5 菜单

在选项列表中增加：

```bash
echo "  a             - 全部批准"
echo "  v             - 查看全部（含已推迟提案）"
echo "  s             - 跳过审批"
echo "  q             - 返回上级菜单"
```

### 5. `arch_proposal_review.sh` 处理 `v` 选项

```bash
v|V|view-all)
  SHOW_ALL=true
  # 重新执行审查（递归调用或循环）
  ;;
```

### 6. `arch_proposal_review.sh` `d` 决策写入文件

在 L318-L325 的 `d` 处理中，增加写入 improvement 文件：

```bash
d|D|defer)
  # 写入 improvement 文件
  if [ -f "$imp_file" ]; then
    # 在 **类型** 行后插入 **状态**: 已推迟
    sed -i '/^\*\*类型\*\*:/a\**状态**: 已推迟' "$imp_file"
  fi
  # 同时在 suggestions.md 标记（保持现有行为）
  if [ -f "$SUGGESTIONS_FILE" ]; then
    ...
  fi
  ;;
```

## 向后兼容

| 场景 | 行为 |
|------|------|
| 现有 improvement 无 `**状态**` 字段 | 视为 `待讨论`，正常展示 |
| 现有 improvement 有 `**状态**: 待讨论` | 正常展示 |
| 现有 improvement 有 `**状态**: 已推迟` | 默认隐藏 |
| `list_improvements()` 旧调用方只读前 3 个字段 | 不受影响，`| 待讨论` 追加在尾部 |

## 回归风险

### 风险 1：`list_improvements()` 调用方解析 4 段格式

`list_improvements()` 被 `guide-arch/SKILL.md` 和 `propose.md` 调用。当前调用方只读 `name|priority|source`，追加 `|status` 不会破坏——尾部字段被忽略。

**缓解**：验证所有调用方。检查 `grep` 模式。

### 风险 2：`sed -i` 插入顺序

`sed -i '/^\*\*类型\*\*:/a\**状态**: 已推迟'` 在 `**类型**` 行后追加。如果文件格式变化（如 `**类型**` 行被删除），插入失败。

**缓解**：使用更健壮的插入方式——在 `**类型**` 行后或文件头部区域查找特定位置。

### 风险 3：`v` 选项递归导致无限循环

`SHOW_ALL=true` 后重新执行审查，如果用户再次 `v`，不应重复展开。

**缓解**：`SHOW_ALL=true` 后不再显示 `v` 选项，或改为顶部状态切换。

## 验收标准

1. 含 `**状态**: 已推迟` 的提案在 Phase 5.5 默认不展示
2. 显示 `⏸️ N 个已推迟（按 v 查看全部）` 提示
3. 按 `v` 展示全部时推迟提案以 `⏸️` 前缀标识
4. 无 `**状态**` 字段的旧提案行为不变
5. `list_improvements()` 输出向后兼容