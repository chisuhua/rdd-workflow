---
name: roadmap
description: 路线图管理技能——初始化、编辑、验证项目路线图。被 guide-arch 调用执行 init/status/edit/validate/advance 命令。
license: MIT
compatibility: Requires spec-workflow v2.0+
metadata:
  version: "2.0"
  author: sisyphus
  evolved-from: "iterate of v1.0"
---

# OpenSpec 工作流 — Roadmap 管理

管理项目级路线图，定义阶段和任务分类，验证 change 的阶段归属，支持阶段门控。

## 工作流位置

```
guide → roadmap（本技能）→ propose → deps → plan → execute → status
         ↑_________________________________________________|
```

## 命令

| 命令 | 说明 |
|------|------|
| `init` | 初始化路线图文件 |
| `status` | 查看路线图状态 |
| `edit` | 编辑路线图（交互式） |
| `validate <change-name>` | 验证 change 的分类 |
| `advance` | 推进到下一阶段 |

---

## 全局：自动检测项目根目录

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
# ADR-0016: read DISCOVERED_ROADMAP_PATH from handoff; fallback to v2.0 default.
ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"
if [ -f "$ARCH_HANDOFF" ]; then
    ROADMAP_FILE="$PROJECT_ROOT/$(jq -r '.roadmap_path // "roadmap.md"' "$ARCH_HANDOFF")"
    ADR_DIR=$(jq -r '.adr_dir // "docs/adr"' "$ARCH_HANDOFF")
    ADR_PATTERN=$(jq -r '.adr_pattern // "ADR-*.md"' "$ARCH_HANDOFF")
else
    ROADMAP_FILE="$PROJECT_ROOT/roadmap.md"
    ADR_DIR="docs/adr"
    ADR_PATTERN="ADR-*.md"
fi
STATE_FILE="$PROJECT_ROOT/.rddf/state/roadmap-state.json"

# 加载 state.sh 辅助函数（safe_python_json, safe_python_yaml）
# P2-3: 所有 json.load(open(...)) 一行式调用改为 safe_python_json
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
if [ -f "$SCRIPT_DIR/_lib/state.sh" ]; then
  source "$SCRIPT_DIR/_lib/state.sh"
fi
```

---

## 命令：init — 初始化路线图

### 步骤 1：检查现有路线图

```bash
if [ -f "$ROADMAP_FILE" ]; then
    echo "⚠️  roadmap.md 已存在"
    echo "   位置: $ROADMAP_FILE"
    echo ""
    echo "请选择:"
    echo "1. 覆盖创建新路线图"
    echo "2. 查看现有路线图"
    echo "3. 取消"
    # 根据用户选择继续
fi
```

### 步骤 2：选择模板

```bash
echo "选择路线图模板:"
echo "1. C++ 库项目（基础 → 核心 → 高级）"
echo "2. Web 应用（MVP → 功能 → 优化）（即将推出）"
echo "3. 空白模板（自定义）"
echo "4. 基于现有 ADR 生成"
```

### 步骤 3：生成路线图文件

**模板分发**（按 `TEMPLATE` 变量选择）：

```bash
# 1 = C++ (上面的 heredoc)
# 2 = Web (即将推出,被忽略)
# 3 = 空白 (基于 ROADMAP_PHASE_COUNT)
# 4 = 基于现有 ADR
# 默认 = 1 (C++)
TEMPLATE="${TEMPLATE:-1}"
```

**模板 1：C++ 库项目**

```bash
cat > "$ROADMAP_FILE" << 'EOF'
# 项目路线图

## 元信息
- **版本**: 1
- **创建时间**: $(date -Iseconds)
- **最后更新**: $(date -Iseconds)
- **当前阶段**: phase-1

## 阶段定义

### Phase 1: 基础架构 (phase-1)
**目标**: 建立项目基础架构和核心抽象
**状态**: 🔄 进行中
**完成条件**:
  - [ ] 所有分类的 change 完成
  - [ ] 核心接口稳定
  - [ ] 基础测试覆盖 > 80%

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 |
|--------|------|------|--------|
| arch-design | 架构设计 | 核心架构和接口设计 | P0 |
| infra-setup | 基础设施 | 构建系统、CI/CD、工具链 | P0 |
| core-impl | 核心实现 | 基础类和核心功能实现 | P1 |
| core-test | 核心测试 | 单元测试和集成测试 | P1 |

### Phase 2: 核心功能 (phase-2)
**目标**: 实现主要业务功能
**状态**: ⏳ 未开始
**前置阶段**: phase-1
**完成条件**:
  - [ ] 所有分类的 change 完成
  - [ ] 功能测试通过
  - [ ] 性能基准达标

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 |
|--------|------|------|--------|
| feature-impl | 功能实现 | 业务功能实现 | P0 |
| feature-test | 功能测试 | 功能验证测试 | P0 |
| perf-opt | 性能优化 | 性能调优 | P1 |

### Phase 3: 高级特性 (phase-3)
**目标**: 高级功能和优化
**状态**: ⏳ 未开始
**前置阶段**: phase-2

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 |
|--------|------|------|--------|
| advanced | 高级功能 | 高级业务功能 | P0 |
| optimization | 系统优化 | 整体优化 | P1 |
EOF
```

**模板 3：空白模板（自定义）**

> 使用 `ROADMAP_PHASE_COUNT` 环境变量指定阶段数量(默认 1,AI 环境不会因 stdin 阻塞)。生成一个最小骨架,用户可手动编辑添加更多 phase。

```bash
# Template 3 (Blank): Interactive Q&A via env var (no stdin blocking)
if [ "$TEMPLATE" = "3" ]; then
  echo "📝 创建空白路线图(交互式)"
  PHASE_COUNT="${ROADMAP_PHASE_COUNT:-3}"

  cat > "$ROADMAP_FILE" << EOF
# 项目路线图

## 元信息
- **版本**: 1
- **创建时间**: $(date -Iseconds)
- **最后更新**: $(date -Iseconds)
- **当前阶段**: phase-1

## 阶段定义

### Phase 1: 阶段 1 (phase-1)
**目标**: 用户自定义
**状态**: 🔄 进行中
**完成条件**:
  - [ ] 所有分类的 change 完成

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 |
|--------|------|------|--------|
| general | 通用 | 用户自定义分类 | P0 |
EOF
  echo "✅ 空白路线图已创建(包含 1 个示例 phase,可手动编辑添加更多)"
  echo "   ROADMAP_PHASE_COUNT=$PHASE_COUNT(可手动编辑 $ROADMAP_FILE 添加更多 phase)"
fi
```

**模板 4：基于现有 ADR 生成**

> 扫描 `docs/adr/ADR-*.md` 文件,统计数量并按状态分组生成路线图。

```bash
# Template 4 (ADR-based): Scan ADR directory from handoff (ADR-0016)
if [ "$TEMPLATE" = "4" ]; then
  echo "📋 从 $ADR_DIR 生成路线图"
  if [ ! -d "$PROJECT_ROOT/$ADR_DIR" ]; then
    mkdir -p "$PROJECT_ROOT/$ADR_DIR"
  fi
  # ⚠️ partial-quote for glob expansion (see propose.md rationale)
  ADR_COUNT=$(ls "$PROJECT_ROOT/$ADR_DIR"/$ADR_PATTERN 2>/dev/null | grep -v -- '-0000-template\.md$' | wc -l)
  if [ "$ADR_COUNT" -eq 0 ]; then
    echo "❌ $ADR_DIR 中未发现 $ADR_PATTERN 文件"
    exit 1
  fi

  echo "📊 扫描到 $ADR_COUNT 个 ADR,生成阶段..."

  # Group ADRs by status (extracted from "**状态**:" line)
  # For simplicity, all "已采纳" ADRs go to phase-1, others to phase-2
  cat > "$ROADMAP_FILE" << EOF
# 项目路线图

## 元信息
- **版本**: 1
- **创建时间**: $(date -Iseconds)
- **最后更新**: $(date -Iseconds)
- **当前阶段**: phase-1

## 阶段定义

### Phase 1: 已采纳 ADR (phase-1)
**目标**: 实现已采纳的 ADR
**状态**: 🔄 进行中
**来源**: $ADR_COUNT 个 ADR 扫描

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 |
|--------|------|------|--------|
| adr-impl | ADR 实现 | 来自 docs/adr/ | P0 |

EOF
  echo "✅ 从 $ADR_COUNT 个 ADR 生成路线图"
fi
```

### 步骤 4：初始化状态文件

```bash
mkdir -p "$PROJECT_ROOT/.zcf"

python3 -c "
import json
from datetime import datetime

state = {
    'version': 1,
    'updated_at': datetime.now().isoformat(),
    'current_phase': 'phase-1',
    'phases': {
        'phase-1': {
            'status': 'in_progress',
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'categories': {
                'arch-design': {'total_changes': 0, 'completed_changes': 0, 'changes': []},
                'infra-setup': {'total_changes': 0, 'completed_changes': 0, 'changes': []},
                'core-impl': {'total_changes': 0, 'completed_changes': 0, 'changes': []},
                'core-test': {'total_changes': 0, 'completed_changes': 0, 'changes': []}
            },
            'gate_status': {
                'all_changes_complete': False,
                'checklist': {
                    '核心接口定义完成': False,
                    '单元测试覆盖 > 80%': False
                }
            }
        },
        'phase-2': {
            'status': 'pending',
            'started_at': None,
            'completed_at': None,
            'categories': {
                'feature-impl': {'total_changes': 0, 'completed_changes': 0, 'changes': []},
                'feature-test': {'total_changes': 0, 'completed_changes': 0, 'changes': []},
                'perf-opt': {'total_changes': 0, 'completed_changes': 0, 'changes': []}
            },
            'gate_status': {
                'all_changes_complete': False,
                'checklist': {}
            }
        },
        'phase-3': {
            'status': 'pending',
            'started_at': None,
            'completed_at': None,
            'categories': {
                'advanced': {'total_changes': 0, 'completed_changes': 0, 'changes': []},
                'optimization': {'total_changes': 0, 'completed_changes': 0, 'changes': []}
            },
            'gate_status': {
                'all_changes_complete': False,
                'checklist': {}
            }
        }
    }
}

with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)

print('✅ 路线图状态文件已创建: $STATE_FILE')
"
```

### 步骤 5：输出结果

```
✅ 路线图初始化完成

文件:
  - roadmap.md          # 路线图定义
  - .rddf/state/roadmap-state.json  # 状态追踪

当前阶段: phase-1 (基础架构)
任务分类:
  - arch-design: 架构设计
  - infra-setup: 基础设施
  - core-impl: 核心实现
  - core-test: 核心测试

下一步:
  skill_use("guide")  # 进入工作流向导
```

---

## 命令：status — 查看路线图状态

### 步骤 1：读取路线图和状态

```bash
if [ ! -f "$ROADMAP_FILE" ]; then
    echo "❌ roadmap.md 不存在"
    echo "请先初始化: skill_use(\"roadmap\", \"init\")"
    exit 1
fi

if [ ! -f "$STATE_FILE" ]; then
    echo "⚠️  状态文件不存在，正在重建..."
    # 调用 rebuild 逻辑
fi
```

### 步骤 2：解析并展示

```bash
python3 -c "
import re
import json

# 读取 roadmap
with open('$ROADMAP_FILE') as f:
    roadmap_content = f.read()

# 读取状态
with open('$STATE_FILE') as f:
    state = json.load(f)

# 提取当前阶段
current_phase = state.get('current_phase', 'unknown')

print('📊 路线图状态')
print('=' * 50)
print(f'当前阶段: {current_phase}')
print('')

# 展示各阶段进度
for phase_id, phase_data in state.get('phases', {}).items():
    status = phase_data.get('status', 'unknown')
    status_icon = {
        'completed': '✅',
        'in_progress': '🔄',
        'pending': '⏳'
    }.get(status, '❓')
    
    total = sum(len(c.get('changes', [])) for c in phase_data.get('categories', {}).values())
    completed = sum(len(c.get('completed_changes', [])) for c in phase_data.get('categories', {}).values())
    
    print(f'{status_icon} {phase_id}: {completed}/{total} change 完成 ({status})')
    
    # 展示分类详情
    for cat_id, cat_data in phase_data.get('categories', {}).items():
        cat_total = len(cat_data.get('changes', []))
        cat_completed = len(cat_data.get('completed_changes', []))
        if cat_total > 0:
            print(f'   - {cat_id}: {cat_completed}/{cat_total}')

print('')

# 阶段门控状态
if current_phase in state.get('phases', {}):
    gate = state['phases'][current_phase].get('gate_status', {})
    print('阶段门控:')
    print(f'  所有 change 完成: {\"✅\" if gate.get(\"all_changes_complete\") else \"❌\"}')
    for check, checked in gate.get('checklist', {}).items():
        print(f'  {check}: {\"✅\" if checked else \"❌\"}')
"
```

---

## 命令：edit — 编辑路线图

### 交互式编辑菜单

```
路线图编辑

请选择操作:
1. 添加新阶段
2. 修改现有阶段
3. 添加/修改任务分类
4. 修改完成条件
5. 修改当前阶段
6. 返回
```

### 添加新阶段

```bash
# 用户输入阶段信息
echo "输入新阶段 ID (如: phase-4):"
read PHASE_ID
echo "输入阶段名称:"
read PHASE_NAME
echo "输入前置阶段 ID (可选):"
read PREREQ_PHASE

# 追加到 roadmap.md
python3 -c "
with open('$ROADMAP_FILE', 'a') as f:
    f.write(f''\n\n### {PHASE_NAME} ({PHASE_ID})\n''')
    f.write(f''**目标**: \n''')
    f.write(f''**状态**: ⏳ 未开始\n''')
    if '$PREREQ_PHASE':
        f.write(f''**前置阶段**: $PREREQ_PHASE\n''')
    f.write(f''**完成条件**:\n''')
    f.write(f''  - [ ] 所有分类的 change 完成\n''')
    f.write(f''\n#### 任务分类\n''')
    f.write(f''| 分类ID | 名称 | 描述 | 优先级 |\n''')
    f.write(f''|--------|------|------|--------|\n''')
"

# 更新状态文件
python3 -c "
import json
with open('$STATE_FILE') as f:
    state = json.load(f)

state['phases']['$PHASE_ID'] = {
    'status': 'pending',
    'started_at': None,
    'completed_at': None,
    'categories': {},
    'gate_status': {
        'all_changes_complete': False,
        'checklist': {}
    }
}

with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
"
```

---

## 命令：validate — 验证 change 分类

### 验证逻辑

```bash
CHANGE_NAME=$1

if [ -z "$CHANGE_NAME" ]; then
    echo "❌ 请提供 change 名称"
    echo "用法: skill_use(\"roadmap\", \"validate\", \"change-name\")"
    exit 1
fi

META_FILE="$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/roadmap-meta.yaml"

if [ ! -f "$META_FILE" ]; then
    echo "❌ Change '$CHANGE_NAME' 不存在或没有 roadmap 元数据"
    exit 1
fi

python3 -c "
import yaml
import re

# 读取 change meta
with open('$META_FILE') as f:
    meta = yaml.safe_load(f)

change_phase = meta.get('roadmap', {}).get('phase', 'unknown')
change_category = meta.get('roadmap', {}).get('category', 'unknown')

# 读取 roadmap
with open('$ROADMAP_FILE') as f:
    roadmap = f.read()

# 验证阶段存在
phase_pattern = rf'### .*? \({change_phase}\)'
if not re.search(phase_pattern, roadmap):
    print(f'❌ 阶段 \"{change_phase}\" 不存在于 roadmap')
    exit(1)

# 验证分类存在
# 找到阶段部分
phase_section = re.search(rf'### .*? \({change_phase}\).*?(?=### |## |$)', roadmap, re.DOTALL)
if phase_section:
    # 在阶段部分查找分类
    cat_pattern = rf'\|\s*{change_category}\s*\|'
    if not re.search(cat_pattern, phase_section.group()):
        print(f'⚠️  分类 \"{change_category}\" 不在阶段 \"{change_phase}\" 中')
        print('')
        print('有效分类:')
        # 提取所有分类
        cats = re.findall(r'\|\s*(\S+)\s*\|\s*([^|]+)\|', phase_section.group())
        for cat_id, cat_name in cats:
            print(f'  - {cat_id}: {cat_name.strip()}')
        exit(1)

print(f'✅ Change \"$CHANGE_NAME\" 验证通过')
print(f'   阶段: {change_phase}')
print(f'   分类: {change_category}')
"
```

---

## 命令：advance — 推进阶段

### 前置检查

```bash
# 检查当前阶段是否已完成
python3 -c "
import json

with open('$STATE_FILE') as f:
    state = json.load(f)

current = state['current_phase']
phase_data = state['phases'].get(current, {})

# 检查所有 change 完成
all_complete = True
for cat_id, cat_data in phase_data.get('categories', {}).items():
    total = len(cat_data.get('changes', []))
    completed = len(cat_data.get('completed_changes', []))
    if completed < total:
        all_complete = False
        print(f'❌ 分类 {cat_id} 未完成: {completed}/{total}')

# 检查门控条件
checklist = phase_data.get('gate_status', {}).get('checklist', {})
for check, checked in checklist.items():
    if not checked:
        all_complete = False
        print(f'❌ 门控条件未完成: {check}')

if not all_complete:
    print('')
    print('当前阶段未完成，无法推进')
    print('请完成所有 change 和门控条件后重试')
    exit(1)

print(f'✅ 阶段 {current} 已完成，可以推进')
"
```

### 执行推进

```bash
# 找到下一个阶段
NEXT_PHASE=$(python3 -c "
import re
with open('$ROADMAP_FILE') as f:
    content = f.read()

phases = re.findall(r'\((phase-\d+)\)', content)
current = '$CURRENT_PHASE'

try:
    idx = phases.index(current)
    if idx + 1 < len(phases):
        print(phases[idx + 1])
    else:
        print('LAST')
except ValueError:
    print('UNKNOWN')
")

if [ "$NEXT_PHASE" = "LAST" ]; then
    echo "🎉 已是最后一个阶段"
    exit 0
elif [ "$NEXT_PHASE" = "UNKNOWN" ]; then
    echo "❌ 无法确定下一阶段"
    exit 1
fi

# 更新状态
python3 -c "
import json
from datetime import datetime

with open('$STATE_FILE') as f:
    state = json.load(f)

current = state['current_phase']

# 标记当前阶段完成
state['phases'][current]['status'] = 'completed'
state['phases'][current]['completed_at'] = datetime.now().isoformat()

# 激活下一阶段
state['current_phase'] = '$NEXT_PHASE'
state['phases']['$NEXT_PHASE']['status'] = 'in_progress'
state['phases']['$NEXT_PHASE']['started_at'] = datetime.now().isoformat()
state['updated_at'] = datetime.now().isoformat()

with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)

print(f'✅ 已推进到阶段: $NEXT_PHASE')
"

# 更新 roadmap.md
python3 -c "
with open('$ROADMAP_FILE', 'r') as f:
    content = f.read()

# 更新当前阶段标记
content = content.replace(
    f'**当前阶段**: {current}',
    f'**当前阶段**: $NEXT_PHASE'
)

# 更新阶段状态
content = content.replace(
    f'**状态**: 🔄 进行中\n**前置阶段**: {current}',
    f'**状态**: 🔄 进行中\n**前置阶段**: {current}'
)

with open('$ROADMAP_FILE', 'w') as f:
    f.write(content)

print('✅ roadmap.md 已更新')
"
```

---


## 辅助函数

### 获取当前阶段

```bash
get_current_phase() {
    # P2-3: 用 safe_python_json 替代内联 python — 缺失/损坏 JSON 不再崩溃
    # safe_python_json 已检查文件存在性,无需 if [ -f ... ] 外层判断
    safe_python_json "$STATE_FILE" "current_phase"
}
```

### 获取阶段的有效分类

```bash
get_phase_categories() {
    PHASE=$1
    python3 -c "
import re
with open('$ROADMAP_FILE') as f:
    content = f.read()

phase_section = re.search(rf'### .*? \($PHASE\).*?(?=### |## |$)', content, re.DOTALL)
if phase_section:
    cats = re.findall(r'\|\s*(\S+)\s*\|\s*([^|]+)\|', phase_section.group())
    for cat_id, cat_name in cats:
        print(f'{cat_id}:{cat_name.strip()}')
"
}
```

### 更新 change 计数

```bash
update_change_count() {
    CHANGE_NAME=$1
    PHASE=$2
    CATEGORY=$3
    OPERATION=${4:-"add"}  # add 或 remove
    
    python3 -c "
import json

with open('$STATE_FILE') as f:
    state = json.load(f)

if '$PHASE' in state['phases'] and '$CATEGORY' in state['phases']['$PHASE']['categories']:
    cat_data = state['phases']['$PHASE']['categories']['$CATEGORY']
    
    if '$OPERATION' == 'add':
        if '$CHANGE_NAME' not in cat_data['changes']:
            cat_data['changes'].append('$CHANGE_NAME')
            cat_data['total_changes'] = len(cat_data['changes'])
    elif '$OPERATION' == 'remove':
        if '$CHANGE_NAME' in cat_data['changes']:
            cat_data['changes'].remove('$CHANGE_NAME')
            cat_data['total_changes'] = len(cat_data['changes'])
        if '$CHANGE_NAME' in cat_data.get('completed_changes', []):
            cat_data['completed_changes'].remove('$CHANGE_NAME')
    
    with open('$STATE_FILE', 'w') as f:
        json.dump(state, f, indent=2)
"
}
```

---

## 关键约束

1. **roadmap.md 是用户可编辑的**：提供模板，但允许用户自由修改
2. **状态文件自动维护**：.roadmap-state.json 由技能自动更新，用户不直接编辑
3. **兼容模式**：无 roadmap.md 时，所有 change 归为 "default" 阶段
4. **阶段门控可跳过**：提供 `--force` 选项强制推进阶段（不推荐）
5. **分类动态调整**：支持在任何时候添加/修改分类定义
