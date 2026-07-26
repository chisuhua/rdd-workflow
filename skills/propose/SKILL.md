---
name: propose
description: 分析项目文档与代码的差距，生成 propose 建议列表，用户选择后执行 openspec-propose 命令序列创建 artifacts。被 guide-plan 调用（不在 archive/ 阶段直接调用）。
license: MIT
compatibility: Requires openspec CLI v1.3.1+. Reads docs/adr/, docs/architecture/, docs/developer_guide/, roadmap.md.
metadata:
  version: "2.0"  # P0: Roadmap 驱动，支持分阶段 change 生成
  author: sisyphus
  evolved-from: "iterate of v1.0"
  replaces-step: "step1-manual"  # 替代原工作流 Step 1 的手动 openspec new/propose 操作
---

# OpenSpec 工作流 — Propose

分析项目文档与代码之间的对齐情况，生成 propose 建议，用户选择后执行 openspec-propose 命令序列创建 artifacts。

**openspec-propose 命令序列**（等同于 Phase 4 的全部步骤）：
1. `openspec new change "<name>"` — 创建 change 目录
2. `openspec status --change "<name>" --json` — 获取所有 artifact 及其依赖关系
3. 循环 `openspec instructions "<artifact>" --change "<name>" --json` — 获取每个 artifact 的模板、上下文、输出路径
4. 按依赖顺序创建 artifact 文件（proposal.md → design.md → tasks.md 等）

`proposal-suggestions.md` 是提案索引文件（Markdown 表格格式，随 git 版本控制），索引到 `improvements/` 目录下的完整提案内容。每次扫描发现新建议时，创建 `improvements/<name>.md` 文件并更新索引。审查通过后添加到 `proposal-approved.md`。

## 工作流位置

```
本技能：扫描文档/代码 → 读取 roadmap → 合并现有建议 → 分类验证 → 用户选择 → 串行创建 propose → 更新 proposal-suggestions.md
                                                                                                                  ↓
guide-ship.worktree: COMMIT GATE → 创建 worktree → 生成 Prometheus 计划
```

**Roadmap 驱动特性**：
- 读取 `roadmap.md` 获取当前阶段和任务分类
- 生成的 change 自动分配阶段和分类
- 验证 change 是否匹配当前阶段分类
- 不匹配时提示重新定义分类或移到未来阶段

---

## 流程

### Phase -1：Roadmap 检测（前置）

检查项目是否存在 `roadmap.md`，确定工作模式：

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ROADMAP_FILE="$PROJECT_ROOT/roadmap.md"
STATE_FILE="$PROJECT_ROOT/.rddf/state/roadmap-state.json"

# 加载 state.sh 辅助函数（safe_python_json, safe_python_yaml）
# P2-3: state.json 读取改为防御式 (read+write 路径使用 safe_python_json 预检)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$SCRIPT_DIR/../_lib/state.sh" ]; then
  source "$SCRIPT_DIR/../_lib/state.sh"
fi

ROADMAP_MODE=false
CURRENT_PHASE="default"
VALID_CATEGORIES=""

if [ -f "$ROADMAP_FILE" ]; then
    echo "📂 检测到路线图: $ROADMAP_FILE"
    ROADMAP_MODE=true
    
    # 读取当前阶段
    CURRENT_PHASE=$(python3 -c "
import re
with open('$ROADMAP_FILE') as f:
    content = f.read()
phase_match = re.search(r'\*\*当前阶段\*\*:\s*(\S+)', content)
print(phase_match.group(1) if phase_match else 'unknown')
")
    
    # 读取当前阶段的任务分类
    VALID_CATEGORIES=$(python3 -c "
import re
with open('$ROADMAP_FILE') as f:
    content = f.read()

# 找到当前阶段部分
phase_sections = re.findall(r'### Phase \d+:.*?\n#### 任务分类\n\n\| 分类ID \| 名称 \|.*?\n((?:\|.*?\|\n)+)', content, re.DOTALL)
if phase_sections:
    # 提取第一个匹配的分类表格（当前阶段）
    table = phase_sections[0]
    cats = re.findall(r'\|\s*(\S+)\s*\|\s*([^|]+)\|', table)
    for cat_id, cat_name in cats:
        print(f'{cat_id}:{cat_name.strip()}')
")
    
    echo "   当前阶段: $CURRENT_PHASE"
    echo "   有效分类:"
    echo "$VALID_CATEGORIES" | while IFS=: read -r id name; do
        echo "     - $id: $name"
    done
else
    echo "⚠️  未检测到 roadmap.md，使用兼容模式"
    echo "   所有 change 将归为 'default' 阶段和 'general' 分类"
    echo "   建议初始化路线图: skill_use(\"roadmap\", \"init\")"
    # P1-6: 检测兼容模式 + 残留状态文件
    # 当 roadmap.md 不存在但 .rddf/state/roadmap-state.json 仍存在,说明:
    #   - 之前启用过 roadmap,后来切换到兼容模式
    #   - 或 roadmap.md 被误删/未提交
    # 此时不自动恢复,只提示用户,避免误覆盖用户数据
    if [ -f "$STATE_FILE" ]; then
        echo ""
        echo "⚠️  roadmap.md 已不存在，但 .rddf/state/roadmap-state.json 存在"
        echo "   推测：roadmap 模式已切换为兼容模式"
        echo "   已有的 roadmap-meta.yaml 不会自动更新 .roadmap-state.json"
        echo "   如需重新启用 roadmap，请运行：skill_use(\"roadmap\", \"init\")"
    fi
fi
```

---

### Phase 0：检查已创建的 changes

读取 `improvements/` 目录和 `openspec/changes/` 目录，移除已创建的 change 对应的 improvement 条目：

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# 检查 improvements/ 和 openspec/changes/ 的交集
if [ -d "$PROJECT_ROOT/improvements" ]; then
  for imp_file in "$PROJECT_ROOT/improvements"/*.md; do
    [ -f "$imp_file" ] || continue
    name=$(basename "$imp_file" .md)
    
    # 如果已存在对应的 change 目录，从 proposal-suggestions.md 移除索引
    if [ -d "$PROJECT_ROOT/openspec/changes/$name" ]; then
      # 从索引中移除（如果存在）
      if [ -f "$PROJECT_ROOT/proposal-suggestions.md" ]; then
        sed -i "/\[$name\](improvements\/$name.md)/d" "$PROJECT_ROOT/proposal-suggestions.md"
        echo "  已从索引移除: $name (change 已存在)"
      fi
    fi
  done
fi
```

> **首次执行**（无 improvements/ 目录时）：跳转到 Phase 1。

---

### Phase 1：扫描项目文档与代码

扫描以下资料，收集新的差距信息。新发现的建议会与 Phase 0 加载的现有建议合并（按 name 去重）。

**1a. 扫描 ADR 文件**

```bash
# ADR-0016 Layer 3: read paths from handoff. Fallback to v2.0 conventions
# when handoff missing. ⚠️ partial-quote for glob expansion (Momus CRITICAL#4):
# prefix is quoted (variable), suffix is unquoted (wildcard expansion).
ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
if [ -f "$ARCH_HANDOFF" ]; then
    ADR_DIR=$(jq -r '.adr_dir // "docs/adr"' "$ARCH_HANDOFF")
    ADR_PATTERN=$(jq -r '.adr_pattern // "ADR-*.md"' "$ARCH_HANDOFF")
    ARCHITECTURE_DIR=$(jq -r '.architecture_dir // "docs/architecture"' "$ARCH_HANDOFF")
else
    ADR_DIR="docs/adr"
    ADR_PATTERN="ADR-*.md"
    ARCHITECTURE_DIR="docs/architecture"
fi

ls "$PROJECT_ROOT/$ADR_DIR"/$ADR_PATTERN 2>/dev/null
```

逐个读取，对每个 ADR 提取：

| 信息 | 来源 |
|------|------|
| ADR 编号和标题 | 文件头 `# ADR-NNNN:` |
| 状态 | `**状态**:` 行（已采纳/已拒绝/待定） |
| 决策日期 | `**日期**:` 行 |
| 未实现项 | 文档正文中的`待修复`、`暂不修复`、`未来参考`等标记 |
| 具体待办 | 文件中的任务列表、TODO 标记 |

**1b. 扫描架构文档**

```bash
ls "$PROJECT_ROOT/$ARCHITECTURE_DIR/"*-gap-analysis.md 2>/dev/null
ls "$PROJECT_ROOT/$ARCHITECTURE_DIR/"*-architecture.md 2>/dev/null
ls "$PROJECT_ROOT/$ARCHITECTURE_DIR/"PHASE*-ARCHITECTURE.md 2>/dev/null

# 开发指南中的技术报告和模式文档
ls docs/developer_guide/tech-reports/ 2>/dev/null
ls docs/developer_guide/patterns/ 2>/dev/null
```

提取：

- 差距分析表中的 ❌ 缺失项和 ⚠️ 部分完成项
- 计划但未实现的功能
- 设计评审中提出的待办项
- 明确标注了工作量的改进项

**1c. 扫描代码标记**

```bash
# 搜索关键目录的 TODO/FIXME/HACK 标记
# 限制文件类型，先收集再 head，避免跳过 archive/ 后不足 30 条
grep -rnE "TODO|FIXME|HACK|WORKAROUND" include/ src/ \
  --include="*.h" --include="*.hpp" --include="*.cpp" --include="*.cu" \
  | grep -v "archive/" > /tmp/todo_raw.txt
head -30 /tmp/todo_raw.txt
```

记录每个标记的文件位置、上下文、紧急程度（从注释推断）。只取前 30 条最关键的。

**1d. 扫描测试覆盖缺口**

```bash
# 自动发现 include/ 下所有子目录（无需硬编码列表）
for subdir in include/*/; do
    [ -d "$subdir" ] || continue
    subdir_name=$(basename "$subdir")
    ls "$subdir" 2>/dev/null | sed 's/\..*$//' | sort > "/tmp/headers_$subdir_name.txt"
done
cat /tmp/headers_*.txt | sort -u > /tmp/all_headers.txt

ls tests/ | sed 's/\..*$//' | sort > /tmp/all_tests.txt

# 有头文件但无对应测试的组件
comm -23 /tmp/all_headers.txt /tmp/all_tests.txt
```

---

### Phase 2：合并、分类并写入建议列表

将 Phase 1 新发现的建议与 Phase 0 加载的现有建议合并，并分配阶段和分类：

```
合并规则：
- 按 name（kebab-case）去重，重复时保留旧的（用户可能已经评估过）
- 新增的建议追加到末尾
```

**分类分配逻辑**：

```bash
# 为每个新发现的建议自动分配阶段和分类
assign_phase_category() {
    local name=$1
    local source=$2
    local description=$3
    
    if [ "$ROADMAP_MODE" = false ]; then
        # 兼容模式
        echo "phase: \"default\""
        echo "category: \"general\""
        return
    fi
    
    # Roadmap 模式：基于内容推断分类
    python3 -c "
import re

name = '$name'
source = '$source'
desc = '''$description'''

# 分类推断规则
category = 'general'

# 基于关键词推断
if any(k in desc.lower() for k in ['接口', '架构', '设计', 'api', 'interface']):
    category = 'arch-design'
elif any(k in desc.lower() for k in ['构建', 'ci', 'cd', '工具链', 'cmake', 'infra']):
    category = 'infra-setup'
elif any(k in desc.lower() for k in ['测试', 'test', '验证', 'coverage']):
    category = 'core-test'
elif any(k in desc.lower() for k in ['实现', 'impl', '功能', 'feature']):
    category = 'core-impl'

print(f'phase: \"$CURRENT_PHASE\"')
print(f'category: \"{category}\"')
"
}

# 推断 change 工作类型：functional / debt / refactor
infer_type() {
    local source=$1
    local description=$2
    local priority=$3
    
    python3 -c "
source = '$source'
desc = '''$description'''
priority = '$priority'

# 基于来源和描述推断类型
combined = (source + desc).lower()
if any(k in combined for k in ['debt', '债务', '清理遗留', 'cleanup-legacy', 'tech-debt']):
    print('debt')
elif any(k in desc.lower() for k in ['重构', 'refactor', '重写', 'rewrite']):
    print('refactor')
else:
    print('functional')
"
}
```

**建议条目格式**（含结构化需求描述 + 路线图元数据）：

每条建议包含以下字段。其中 `description` 字段使用 `/opsx:propose` 格式，这是后续传递给 openspec-propose 的完整需求描述：

**P1-7 容器格式**：建议以 JSON 数组形式写入 `proposal-suggestions.md`（替换旧的 YAML+Markdown 混合格式）。完整 schema 见 `docs/proposal-suggestions-format.md`。

```json
{
  "name": "add-stream-pipe-ops",            // kebab-case 名称
  "priority": "P0",                          // P0/P1/P2
  "source": "ADR-022 §已采纳 §未实现",        // 来源文档
  "status": "待创建",                         // 状态：待创建 / 进行中 / 已完成
  "phase": "phase-1",                        // 所属阶段（roadmap 驱动）
  "category": "core-impl",                   // 任务分类（roadmap 驱动）
  "description": "## 架构依据\n- ADR-022 §3.2: Stream 管道操作符设计决策（已采纳，代码未实现）\n- ADR-019 §4.1: Verilog 代码生成完整性要求（影响 codegen 适配）\n\n## 范围\n- **In Scope**:\n  - 实现 Stream 管道操作符 m2sPipe/s2mPipe/halfPipe\n  - 修改文件：include/chlib/stream_operators.h\n  - 配套单元测试\n- **Out Scope**:\n  - 不修改现有 FIFO/Arbiter/Fork 实现\n  - 不涉及跨时钟域适配\n\n## 关键场景\n- GIVEN 一个 ch_stream<T> 实例, WHEN 调用 .m2sPipe(), THEN 返回带一级流水寄存器的新 Stream\n- GIVEN 两个 Stream 通过 s2mPipe 连接, WHEN 反压, THEN 寄存器缓存一拍数据\n\n## 技术约束\n- MUST 保持与 SpinalHDL m2sPipe/s2mPipe/halfPipe 语义一致\n- MUST NOT 引入新的模板特化\n- SHOULD 覆盖 pipeline 延迟场景测试\n\n## 验收标准\n- 3 个操作符编译通过\n- 4 个 Catch2 测试覆盖正常/反压/复位场景\n- 现有 stream 测试全部通过",
  "effort": "2-3天"
}
```

> 上面的 `description` 是一个 JSON 字符串字段（用 `\n` 表示换行）。`propose.md` 和 4 个其他 consumer（`guide-spec.md`、`guide.md`、`status.md`、`deps.md`）都通过 `skills/_lib/state.sh::read_suggestions` / `write_suggestions` 读写。

**优先级归类**：

| 类别 | 来源 | 默认优先级 |
|------|------|-----------|
| 🔴 ADR 未实现 | ADR 中 "已采纳，暂不修复" 且有明确待办 | P0 |
| 🟡 架构差距 | 差距分析表中的 ❌/⚠️ 项 | P1 |
| 🔵 计划功能 | PHASE 文档中的未实现计划 | P1-P2 |
| 🟢 代码标记 | TODO/FIXME 注释 | P2 |
| ⚪ 测试缺口 | 有头文件无测试 | P2 |

**写入文件**：

```bash
# 写入 proposal-suggestions.md（覆盖写入）
# 格式为 JSON 数组（P1-7 规范）
# 此文件将随 git 版本控制
# 实际写入委托给 skills/_lib/state.sh::write_suggestions
```

---

### Phase 3：与用户交互确认

展示建议列表，让用户选择。使用 Question 工具提供选项。

**展示格式**：

```
## 📋 建议变更清单

已扫描 <N> 个 ADR，<M> 个架构文档，发现 <X> 个可 propose 的变更：

### 🔴 P0（ADR 未实现）
1. fix-ns-pollution — 修复 8 文件命名空间污染（ADR-033，高风险）
2. add-stream-pipe-ops — 实现 Stream 管道操作符（ADR-022，2-3天）

### 🟡 P1（架构差距）
3. add-cdc-support — 跨时钟域支持（架构差距分析，3-5天）

### 🟢 P2（代码标记/测试缺口）
4. refactor-sim-eval — 重构仿真评估顺序（context.cpp:152 TODO）

---

选择要创建的 propose（可多选）：
```

构建 Question 工具的选项列表：

```javascript
// 对每个建议创建一个选项
{
    header: "选择 propose",
    question: "请选择要创建的 propose（可多选；若列表为空可选择跳过）",
    multiple: true,
    options: [
        { label: "fix-ns-pollution",     description: "P0: 修复命名空间污染 (ADR-033)" },
        { label: "add-stream-pipe-ops",  description: "P0: 实现Stream管道操作符 (ADR-022, 2-3天)" },
        { label: "add-cdc-support",      description: "P1: 跨时钟域支持 (架构差距, 3-5天)" },
        { label: "...",                  description: "..." },
        // 如果用户想创建建议列表之外的新 propose
        { label: "其他 (自定义)",           description: "描述新的 propose 需求" }
    ]
}
```

用户选择处理：

| 选择 | 行为 |
|------|------|
| 一个或多个建议 | 记录选中的 name + description，进入 Phase 4 |
| "其他 (自定义)" | 用户描述需求，AI 按相同格式生成新条目，进入 Phase 4 |
| 跳过（未选择） | 直接进入 Phase 5，跳过创建 |
| Phase 4 完成后回到 Phase 3 继续选择 | 支持多次选择，直到用户完成 |

**Phase 3.5：归属 feature 提示（可选）**

用户选择 propose 后、进入 Phase 4 之前，可选询问是否归属到 feature 组：

```
将此 change 归属到哪个 feature 组？
（可选，直接回车跳过 - 保持向后兼容）
> 
```

处理逻辑：

| 用户输入 | 行为 |
|---------|------|
| 输入 feature 名称 | 设置 `PARENT_FEATURE=<value>`，传给 Phase 4 |
| 直接回车（空） | `PARENT_FEATURE` 保持未设置（向后兼容） |
| 输入 `__ungrouped__` | 拒绝："保留字，请输入其他名称或留空"，重新提示 |

```bash
# Optional: set PARENT_FEATURE to register this change under a feature group.
# Rejected values: "__ungrouped__" (reserved synthetic key per feature_view.py::UNGROUPED).
# When user presses Enter (empty), PARENT_FEATURE stays unset (backward compatible).
# When user provides a value, set PARENT_FEATURE env var for Phase 4 consumption.
# Phase 4 functions (propose_create_change / propose_finalize_change) also accept
# --parent-feature CLI arg which takes precedence over the env var.
```

---

### Phase 4：串行创建每个 propose

对每个选中的 propose，按以下步骤串行创建（每次成功后继续下一个）：

```bash
# P0-1: Phase 4 extracted to _lib/propose_change.sh + _lib/propose_change.py
# 5 Python helpers preserve original behavior:
# - create_skeleton_change (skeleton branch, was lines 486-551)
# - update_roadmap_meta (was lines 617-686)
# - update_roadmap_state (was lines 688-711)
# - update_iteration_proposed (was lines 713-760)
# - set_suggestion_status (was lines 531-548)
#
# The artifact creation loop at lines 580-608 is HALF-IMPLEMENTED
# (pseudo-code, see audit 2026-07-16) and is preserved as-is below.
source "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/propose_change.sh"

THIS_SESSION_CREATED=()

for arg in "$@"; do
  case "$arg" in
    --skeleton|--skeleton-only) SKELETON_MODE=true ;;
  esac
done
SKELETON_MODE="${SKELETON_MODE:-false}"

# Step 4a: Guardrail — check if change already exists
if [ -d "$PROJECT_ROOT/openspec/changes/<name>/" ]; then
    echo "⚠️ Change <name> 已存在，跳过"
    continue
fi

# Step 4a-skel: Skeleton mode branch (creates minimal artifacts only)
if [ "$SKELETON_MODE" = "true" ]; then
    # Optional: set PARENT_FEATURE to register this change under a feature group.
    # This activates the parent_feature field in iteration.json + roadmap-meta.yaml.
    # Rejected values: "__ungrouped__" (reserved synthetic key).
    # When unset, behavior is unchanged (backward compatible).
    # Example: PARENT_FEATURE="feature-rddf" propose_create_change ...
    propose_create_change <name> --skeleton "$CURRENT_PHASE" "$CHANGE_CATEGORY" "$PRIORITY"
    # Update proposal-suggestions.md: status "待创建" → "skeleton"
    if [ -f "$PROJECT_ROOT/proposal-suggestions.md" ]; then
        PROJECT_ROOT="$PROJECT_ROOT" NAME="<name>" NEW_STATUS="skeleton" python3 <<PYEOF
import os, json
p = os.path.join(os.environ.get("PROJECT_ROOT", "."), "proposal-suggestions.md")
target = os.environ.get("NAME", "")
new_status = os.environ.get("NEW_STATUS", "skeleton")
try:
    with open(p) as f:
        entries = json.load(f)
    if isinstance(entries, list):
        for e in entries:
            if isinstance(e, dict) and e.get("name") == target:
                e["status"] = new_status
        with open(p, "w") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
            f.write("\n")
except (FileNotFoundError, json.JSONDecodeError):
    pass
PYEOF
    fi

    # Step 4e: Quality check (propose-quality-autohook)
    if [ -f "$SCRIPT_DIR/scripts/propose_quality_hook.sh" ]; then
        source "$SCRIPT_DIR/scripts/propose_quality_hook.sh"
        invoke_propose_quality_hook "<name>"
    fi
    continue
fi

# Step 4b: openspec new change
openspec new change "<name>"
if [ $? -ne 0 ]; then
    echo "❌ 创建 change <name> 失败，跳过"
    continue
fi

# Spec-validation gate (add-spec-validation-gates)
if [ -f "$PROJECT_ROOT/openspec/changes/<name>/.openspec.yaml" ]; then
    if ! python3 "$(dirname "${BASH_SOURCE[0]:-$0}")/scripts/validate_baseline.py" "<name>" >/dev/null 2>&1; then
        echo "❌ Baseline validation failed for <name>"
        continue
    fi
fi

THIS_SESSION_CREATED+=("<name>")

# Step 4c: artifact creation loop (TODO — requires openspec CLI artifact support)
# 
# Current status: The artifact creation loop was identified as HALF-IMPLEMENTED in audit
# 2026-07-16. The pseudo-code below outlines the intended behavior, but full implementation
# requires:
#   1. openspec CLI 'instructions' command to support artifact generation
#   2. Proper dependency resolution between artifacts
#   3. Output path validation and content generation
#
# For now, `openspec new change` creates the minimal artifacts (proposal.md, roadmap-meta.yaml).
# Additional artifacts (design.md, tasks.md, specs/*.md) are created manually or via
# guide-ship's plan generation phase.
#
# TODO(v3.1): Implement full artifact creation loop when openspec CLI adds artifact support.
#
# [PRESERVED PSEUDO-CODE FOR REFERENCE - NOT bash-executable]
# for each artifact_id in artifact_order:
#     INSTR=$(openspec instructions "$artifact_id" --change "<name>" --json)
#     OUTPUT_PATH=$(echo "$INSTR" | jq -r '.outputPath')
#     DEPS=$(echo "$INSTR" | jq -r '.dependencies[]')
#     for each dep in DEPS:
#         读取 dep 文件内容
#     # 写入 OUTPUT_PATH
#     test -f "$OUTPUT_PATH" || { echo "❌ artifact $artifact_id 创建失败"; break; }
#     echo "  已创建: $artifact_id → $OUTPUT_PATH"

echo "⚠️  Artifact creation loop not yet implemented (requires openspec CLI support)"

# Step 4d: roadmap + iteration sync (extracted to helper)
if [ "${ROADMAP_MODE:-false}" = "true" ]; then
    # Optional: set PARENT_FEATURE to register this change under a feature group.
    # This activates the parent_feature field in iteration.json + roadmap-meta.yaml.
    # Rejected values: "__ungrouped__" (reserved synthetic key).
    # When unset, behavior is unchanged (backward compatible).
    # Example: PARENT_FEATURE="feature-rddf" propose_finalize_change ...
    VALID_CAT="${VALID_CATEGORIES:-}"
    propose_finalize_change <name> "$CURRENT_PHASE" "$CHANGE_CATEGORY" "$PRIORITY" "$VALID_CAT"
fi

# Step 4e: Quality check (propose-quality-autohook)
if [ -f "$SCRIPT_DIR/scripts/propose_quality_hook.sh" ]; then
    source "$SCRIPT_DIR/scripts/propose_quality_hook.sh"
    invoke_propose_quality_hook "<name>"
fi
```

---

### Phase 5：更新 proposal-suggestions.md + 汇总输出

**5a. 从建议列表中移除已创建的 propose**

从 proposal-suggestions.md 中删除已成功创建的条目（按 name 匹配）。保留未选中和跳过的条目供下次使用。

**5b. 汇总输出 + 自动提交**

Propose 创建完成后，自动检测未提交的 artifacts 并执行提交：

```
✅ Propose 阶段完成

本次创建的 propose：
  1. fix-ns-pollution → openspec/changes/fix-ns-pollution/ (已完成)
  2. add-stream-pipe-ops → openspec/changes/add-stream-pipe-ops/ (已完成)

建议列表剩余 2 个 propose（未创建）：
  - add-cdc-support (P1)
  - refactor-sim-eval (P2)

【自动提交】检测到未提交的 artifacts，正在提交...
```

**自动提交脚本**（Phase 5 后执行）：

```bash
# P0-3: 仅精确添加本次会话实际创建的 change（不再使用 `git add openspec/changes/*/` 通配符）
#       - 危险点：`*/` 会把 archive/、其它未相关 change 一并加入暂存区
#       - 新方案：依赖 Phase 4 中 THIS_SESSION_CREATED 数组（按 name 逐个 git add）
if [ ${#THIS_SESSION_CREATED[@]} -gt 0 ]; then
    echo "📦 提交本次创建的 ${#THIS_SESSION_CREATED[@]} 个 changes..."

    # 逐个精确 git add（避免把 archive/ 或其它无关 change 误加进来）
    for name in "${THIS_SESSION_CREATED[@]}"; do
        # Only commit artifacts that exist (skeleton changes have fewer files)
        if [ -f "$PROJECT_ROOT/openspec/changes/$name/proposal.md" ]; then
            git add "openspec/changes/$name/proposal.md"
        fi
        if [ -f "$PROJECT_ROOT/openspec/changes/$name/roadmap-meta.yaml" ]; then
            git add "openspec/changes/$name/roadmap-meta.yaml"
        fi
        if [ -f "$PROJECT_ROOT/openspec/changes/$name/.openspec.yaml" ]; then
            git add "openspec/changes/$name/.openspec.yaml"
        fi
        if [ -f "$PROJECT_ROOT/openspec/changes/$name/design.md" ]; then
            git add "openspec/changes/$name/design.md"
        fi
        if [ -f "$PROJECT_ROOT/openspec/changes/$name/tasks.md" ]; then
            git add "openspec/changes/$name/tasks.md"
        fi
    done
    git add proposal-suggestions.md

    # 提交信息使用数组中实际创建的名称
    git commit -m "feat: propose ${THIS_SESSION_CREATED[*]}"

    echo "✅ 已提交: ${THIS_SESSION_CREATED[*]}"
else
    echo "✅ 本次未创建任何 change，无需提交"
fi
```

**【重要】自动提交触发条件**：
- 检测到 `openspec/changes/<name>/` 目录有新建或修改的文件
- 检测到 `proposal-suggestions.md` 有更新
- 只在用户选择「完成 Propose 阶段」时触发，不是每次创建 change 都触发

---

**5c. 用户未选择任何 propose 时的输出**

```
✅ 扫描完成，未创建新的 propose。

建议列表已更新（含 X 个待办建议）：
  - fix-ns-pollution (P0)
  - add-stream-pipe-ops (P0)
  - ...

下次执行本技能时会从现有建议列表继续。
```

**5d. Phase 5 后自动检查剩余建议（循环机制）**

```bash
# 检查是否还有剩余建议
if [ -f "proposal-suggestions.md" ]; then
    # P1-7: 文件格式已规范化为 JSON 列表
    #       用 json.load 解析后筛选 status == "待创建" 的条目
    #       旧实现的 grep 在 JSON 字符串中会误匹配 description 字段里的"待创建"字面量
    source "$(dirname "${BASH_SOURCE[0]:-$0}")/../_lib/state.sh"
    REMAINING=$(count_pending_suggestions "$PROJECT_ROOT")
    REMAINING=${REMAINING:-0}
    if [ "$REMAINING" -gt 0 ]; then
        echo ""
        echo "📋 proposal-suggestions.md 中还有 $REMAINING 个未创建的 change"
        echo ""
        echo "请选择:"
        echo "1. 继续创建其他 change（返回 Phase 3 选择）"
        echo "2. 完成 Propose 阶段（提交当前 artifacts）"
        echo "i. 其他输入"
    fi
fi
```

**用户输入处理（case handler）**：

当用户输入不在上述有效选项内时，按以下 case 分支处理：

```bash
case "$choice" in
  q|quit|exit) exit 0 ;;
  r|refresh) continue ;;  # 重新展示菜单
  ?|help) echo "可用命令: [数字选项], q(退出), r(刷新), ?(帮助)" ;;
  *) echo "❌ 无效输入 '$choice',请重试或输入 ? 查看帮助" ;;
esac
```

---

## 多次调用说明

本技能可以反复调用，每次调用：

1. **Phase 0**：读取已有的 `proposal-suggestions.md`，移除已创建为 change 的条目
2. **Phase 1-2**：扫描是否有新产生的建议（新 ADR、新 TODO），与新发现合并
3. **Phase 3-4**：只展示尚未被创建的 propose
4. **Phase 5**：更新 proposal-suggestions.md（移除已创建的）

这样 `proposal-suggestions.md` 成为持续的待办清单，多次调用逐步消耗。

---

## 关键约束

1. **只读不写代码**：本技能只分析文档和创建 artifacts，不修改源代码
2. **串行执行**：每个 propose 依次创建，不并行
3. **建议 vs 决定**：建议列表只是参考，用户决定最终创建哪些
4. **proposal-suggestions.md 是持久化文件**：随 git 版本控制，每次执行时增量更新
5. **错误容错**：单个 propose 创建失败不影响后续（skip 继续）
6. **Roadmap 兼容**：无 roadmap.md 时以兼容模式运行（所有 change 归为 default 阶段）
7. **分类验证**：roadmap 模式下，change 的分类必须在当前阶段的有效分类中
