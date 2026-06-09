---
name: propose
description: 分析项目文档与代码的差距，生成 propose 建议列表，用户选择后执行 openspec-propose 命令序列创建 artifacts。被 guide-spec 调用（不在 archive/ 阶段直接调用）。
license: MIT
compatibility: Requires openspec CLI v1.3.1+. Reads docs/adr/, docs/architecture/, docs/developer_guide/, roadmap.md.
metadata:
  author: sisyphus
  version: "2.0"  # P0: Roadmap 驱动，支持分阶段 change 生成
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

`proposal-suggestions.md` 是持久化文件（随 git 版本控制），每次执行时更新：新增扫描发现的建议，移除已创建的 propose。

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
STATE_FILE="$PROJECT_ROOT/.zcf/.roadmap-state.json"

# 加载 state.sh 辅助函数（safe_python_json, safe_python_yaml）
# P2-3: state.json 读取改为防御式 (read+write 路径使用 safe_python_json 预检)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$SCRIPT_DIR/_lib/state.sh" ]; then
  source "$SCRIPT_DIR/_lib/state.sh"
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
    # 当 roadmap.md 不存在但 .zcf/.roadmap-state.json 仍存在,说明:
    #   - 之前启用过 roadmap,后来切换到兼容模式
    #   - 或 roadmap.md 被误删/未提交
    # 此时不自动恢复,只提示用户,避免误覆盖用户数据
    if [ -f "$STATE_FILE" ]; then
        echo ""
        echo "⚠️  roadmap.md 已不存在，但 .zcf/.roadmap-state.json 存在"
        echo "   推测：roadmap 模式已切换为兼容模式"
        echo "   已有的 roadmap-meta.yaml 不会自动更新 .roadmap-state.json"
        echo "   如需重新启用 roadmap，请运行：skill_use(\"roadmap\", \"init\")"
    fi
fi
```

---

### Phase 0：加载现有建议列表

读取已有的 `proposal-suggestions.md`（如果存在），并移除已创建为 change 的条目：

使用 Python 读取 YAML 结构并过滤（比 bash 解析 YAML 更可靠）：

```bash
# 自动检测项目根目录（用于全局安装的技能）
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
if [ -f "proposal-suggestions.md" ]; then
    echo "📂 加载已有的 proposal-suggestions.md"
    # P1-7: 文件格式已规范化为 JSON 列表
    #       用 skills/_lib/state.sh::read_suggestions 读取
    #       用源生的 json.load / json.dump 替代 yaml.safe_load
    #       移除已创建为 change 的条目后用 write_suggestions 写回
    python3 -c "
import json, os, sys, subprocess

project_root = subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel'], text=True
).strip()

try:
    with open('proposal-suggestions.md') as f:
        entries = json.load(f)

    if not isinstance(entries, list):
        print('⚠️  proposal-suggestions.md 顶层不是 JSON 数组，跳过加载', file=sys.stderr)
        sys.exit(0)

    kept = []
    removed = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get('name')
        if name and os.path.isdir(f'{project_root}/openspec/changes/{name}/'):
            removed.append(name)
        else:
            kept.append(entry)

    # 写回过滤后的内容（使用 ensure_ascii=False 保留中文）
    with open('proposal-suggestions.md', 'w') as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)
        f.write('\n')

    if removed:
        print(f'  已从建议列表移除: {\", \".join(removed)}')
    print(f'  剩余 {len(kept)} 个建议')

except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f'⚠️  proposal-suggestions.md 解析失败: {e}', file=sys.stderr)
    print('  保留原文件，继续执行扫描阶段')
" || echo "⚠️ Python 执行失败，跳过加载"
fi
```

> **首次执行**（文件不存在时）：跳转到 Phase 1。

---

### Phase 1：扫描项目文档与代码

扫描以下资料，收集新的差距信息。新发现的建议会与 Phase 0 加载的现有建议合并（按 name 去重）。

**1a. 扫描 ADR 文件**

```bash
ls docs/adr/ADR-*.md
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
ls docs/architecture/*-gap-analysis.md
ls docs/architecture/*-architecture.md
ls docs/architecture/PHASE*-ARCHITECTURE.md

# 开发指南中的技术报告和模式文档
ls docs/developer_guide/tech-reports/
ls docs/developer_guide/patterns/
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

---

### Phase 4：串行创建每个 propose

对每个选中的 propose，按以下步骤串行创建（每次成功后继续下一个）：

```bash
# P0-3: 精确跟踪本次会话成功创建的 change 名称（避免危险的 `git add openspec/changes/*/` glob）
THIS_SESSION_CREATED=()

for each selected propose <name>:
    # ---------------------------------------------------------------
    # Step 4a: Guardrail — 检查 change 是否已存在
    # ---------------------------------------------------------------
    if [ -d "$PROJECT_ROOT/openspec/changes/<name>/" ]; then
        echo "⚠️ Change <name> 已存在，跳过"
        continue
    fi

    # ---------------------------------------------------------------
    # Step 4b: 创建 change 目录
    # ---------------------------------------------------------------
    openspec new change "<name>"
    if [ $? -ne 0 ]; then
        echo "❌ 创建 change <name> 失败，跳过"
        continue
    fi

    # P0-3: 记录成功创建的 change 名（仅本次会话、仅 openspec new 成功后的）
    THIS_SESSION_CREATED+=("<name>")
    
    # ---------------------------------------------------------------
    # Step 4c: 获取 artifact 构建顺序，循环创建
    # ---------------------------------------------------------------
    # 获取初始状态，找出 applyRequires 的 artifact 列表
    STATUS=$(openspec status --change "<name>" --json)
    
    # 使用 jq --arg 传参，避免多行字符串内插导致的语法错误
    APPLY_REQUIRES=$(echo "$STATUS" | jq -r '.applyRequires | join("\n")')
    ARTIFACTS=$(echo "$STATUS" | jq -r --arg req "$APPLY_REQUIRES" '
        .artifacts[] | select(
            .id as $id | ($req | split("\n") | index($id))
        ) | .id
    ')
    
    # 按依赖顺序逐个创建 artifact
    for each artifact_id in artifact_order:
        # 获取 instructions（含 template、context、rules、outputPath）
        INSTR=$(openspec instructions "$artifact_id" --change "<name>" --json)
        OUTPUT_PATH=$(echo "$INSTR" | jq -r '.outputPath')
        
        # 读取依赖 artifacts 作为上下文
        DEPS=$(echo "$INSTR" | jq -r '.dependencies[]')
        for each dep in DEPS:
            读取 dep 文件内容
        
        # 使用 instruction 中的 context/rules 作为约束
        # 使用 template 作为输出文件的结构
        # 写入 OUTPUT_PATH
        
        # 验证文件已创建
        test -f "$OUTPUT_PATH" || { echo "❌ artifact $artifact_id 创建失败"; break; }
        echo "  已创建: $artifact_id → $OUTPUT_PATH"
    
    # 验证所有 applyRequires artifacts 完成
    FINAL_STATUS=$(openspec status --change "<name>" --json)
    echo "✅ propose <name> 所有 artifacts 已就绪"
    
    # ---------------------------------------------------------------
    # Step 4d: 创建 roadmap-meta.yaml（roadmap 驱动）
    # ---------------------------------------------------------------
    if [ "$ROADMAP_MODE" = true ]; then
        # 从建议条目读取 phase 和 category
        # P1-7: 文件格式已规范化为 JSON 列表
        #       用 json.load 替代 yaml.safe_load（避免依赖 PyYAML）
        #       用 try/except 捕获 FileNotFoundError + json.JSONDecodeError
        CHANGE_PHASE=$(python3 -c "
import json, sys
try:
    with open('proposal-suggestions.md') as f:
        entries = json.load(f)
    if not isinstance(entries, list):
        print('$CURRENT_PHASE')
        sys.exit(0)
    for entry in entries:
        if isinstance(entry, dict) and entry.get('name') == '<name>':
            print(entry.get('phase', '$CURRENT_PHASE'))
            break
    else:
        print('$CURRENT_PHASE')
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f'⚠️ lookup phase 失败: {e}', file=sys.stderr)
    print('$CURRENT_PHASE')
" 2>/dev/null)

        CHANGE_CATEGORY=$(python3 -c "
import json, sys
try:
    with open('proposal-suggestions.md') as f:
        entries = json.load(f)
    if not isinstance(entries, list):
        print('general')
        sys.exit(0)
    for entry in entries:
        if isinstance(entry, dict) and entry.get('name') == '<name>':
            print(entry.get('category', 'general'))
            break
    else:
        print('general')
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f'⚠️ lookup category 失败: {e}', file=sys.stderr)
    print('general')
" 2>/dev/null)
        
        # 验证分类是否在当前阶段的有效分类中
        VALID_CAT_LIST=$(echo "$VALID_CATEGORIES" | cut -d: -f1 | tr '\n' ' ')
        if ! echo "$VALID_CAT_LIST" | grep -qw "$CHANGE_CATEGORY"; then
            echo "⚠️  Change '<name>' 的分类 '$CHANGE_CATEGORY' 不在当前阶段 '$CURRENT_PHASE' 的有效分类中"
            echo "   有效分类: $VALID_CAT_LIST"
            echo ""
            echo "请选择:"
            echo "1. 使用 'general' 分类"
            echo "2. 选择其他有效分类"
            echo "3. 编辑 roadmap.md 添加此分类"
            # 根据用户选择处理
            CHANGE_CATEGORY="general"
        fi
        
        # 创建 roadmap-meta.yaml
        cat > "$PROJECT_ROOT/openspec/changes/<name>/roadmap-meta.yaml" << EOF
roadmap:
  phase: "$CHANGE_PHASE"
  category: "$CHANGE_CATEGORY"
  priority: "$PRIORITY"
  gate_checklist: []
  cross_phase_deps: []
  category_validation:
    valid: true
    reason: ""
EOF
        echo "  已创建: roadmap-meta.yaml (phase: $CHANGE_PHASE, category: $CHANGE_CATEGORY)"
        
        # 更新 .roadmap-state.json
        # P2-3: 用 safe_python_json 预检文件可解析性 + 内部 try/except 双保险
        # 写回路径需要完整对象,不能直接用 safe_python_json 替代读路径
        if [ -f "$STATE_FILE" ] && safe_python_json "$STATE_FILE" "current_phase" >/dev/null 2>&1; then
            python3 -c "
import json, sys
try:
    with open('$STATE_FILE') as f:
        state = json.load(f)

    if '$CHANGE_PHASE' in state['phases'] and '$CHANGE_CATEGORY' in state['phases']['$CHANGE_PHASE']['categories']:
        cat_data = state['phases']['$CHANGE_PHASE']['categories']['$CHANGE_CATEGORY']
        if '<name>' not in cat_data['changes']:
            cat_data['changes'].append('<name>')
            cat_data['total_changes'] = len(cat_data['changes'])

        with open('$STATE_FILE', 'w') as f:
            json.dump(state, f, indent=2)
        print('  已更新: .roadmap-state.json')
except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
    print(f'⚠️  更新 .roadmap-state.json 失败: {e}', file=sys.stderr)
    sys.exit(0)  # graceful exit, 不中断 propose 流程
"
        fi
    fi
    
    # ---------------------------------------------------------------
    # Step 4e: 用结构化需求描述作为 openspec-propose 的输入
    # ---------------------------------------------------------------
    # 创建 artifact（尤其是 proposal.md）时，使用 Phase 2 中 description 字段的
    # /opsx:propose 格式作为完整需求描述。该格式包含五大板块：
    #
    # ## 架构依据
    #   ADR 条款引用（§章节号 + 条款标题），建立需求与架构决策的追溯链。
    #   例如：ADR-022 §3.2: Stream 管道操作符设计决策
    #   这确保生成的 change 有明确的架构和 ADR 依据。
    #
    # ## 范围
    #   In Scope / Out Scope（明确变更边界）
    #
    # ## 关键场景
    #   GIVEN/WHEN/THEN 格式（核心功能场景）
    #
    # ## 技术约束
    #   MUST / MUST NOT / SHOULD（实现限制和规范）
    #
    # ## 验收标准
    #   量化指标和测试要求（定义"完成"的标准）
    #
    # 这五个板块直接嵌入 proposal.md 的需求背景部分，作为
    # openspec-propose 命令序列生成 artifacts 时的上下文。
    # 
    # openspec-propose 命令序列等同于 Phase 4 的全部步骤：
    #   Step 4a: openspec new change "<name>"
    #   Step 4b: openspec status --change "<name>" --json
    #   Step 4c: openspec instructions "<artifact>" --change "<name>" --json（循环）
    #   Step 4d: 按 /opsx:propose 格式生成 proposal.md 内容
    
# 所有 propose 创建完成
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
        git add "openspec/changes/$name/"
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
    REMAINING=$(python3 -c "
import json, sys
try:
    with open('proposal-suggestions.md') as f:
        entries = json.load(f)
    if not isinstance(entries, list):
        print(0)
        sys.exit(0)
    count = sum(1 for e in entries if isinstance(e, dict) and e.get('status') == '待创建')
    print(count)
except (FileNotFoundError, json.JSONDecodeError):
    print(0)
" 2>/dev/null)
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
