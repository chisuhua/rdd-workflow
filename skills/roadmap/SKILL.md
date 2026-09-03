---
name: roadmap
description: 路线图管理技能——初始化、编辑、验证项目路线图。被 rdd-arch 调用执行 init/status/edit/validate/advance 命令。
license: MIT
compatibility: Requires rdd-workflow v3.0+
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
source "${PROJECT_ROOT:-/nonexistent}/.opencode/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
SCRIPT_DIR="$(resolve_rdd_skill_dir roadmap)"
if [ -f "$SCRIPT_DIR/../_lib/state.sh" ]; then
  source "$SCRIPT_DIR/../_lib/state.sh"
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

| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构设计 | 核心架构和接口设计 | P0 | RBAC权限模型；事件总线契约；模块边界 |
| infra-setup | 基础设施 | 构建系统、CI/CD、工具链 | P0 | Docker镜像；GitHub Actions |
| core-impl | 核心实现 | 基础类和核心功能实现 | P1 |  |
| core-test | 核心测试 | 单元测试和集成测试 | P1 |  |

> **预期改进方向** (v2.2 新增): 可选第 5 列,内容为 `主题1；主题2` 分号分隔。guide-design 进入时会读取此列计算覆盖率。空 cell 表示该分类无主题约束 (向后兼容)。
> 
> **主题状态词汇**:
> - `未覆盖` — roadmap 定义但无 proposal 匹配 (计入分母)
> - `已覆盖` — 至少一个 proposal 的 `**主题**:` 字段精确匹配 (不计入分母)
> - `~skipped~` — 在 cell 末尾追加 `~skipped~`,显式豁免 (排除出分母)
> 
> **向后兼容**: 4 列旧表格按"无约束"处理,`roadmap_state.get_phase_themes()` 返回空列表。

### Phase 2: 核心功能 (phase-2)
**目标**: 实现主要业务功能
**状态**: ⏳ 未开始
**前置阶段**: phase-1
**完成条件**:
  - [ ] 所有分类的 change 完成
  - [ ] 功能测试通过
  - [ ] 性能基准达标

#### 任务分类

| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| feature-impl | 功能实现 | 业务功能实现 | P0 |  |
| feature-test | 功能测试 | 功能验证测试 | P0 |  |
| perf-opt | 性能优化 | 性能调优 | P1 |  |

### Phase 3: 高级特性 (phase-3)
**目标**: 高级功能和优化
**状态**: ⏳ 未开始
**前置阶段**: phase-2

#### 任务分类

| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| advanced | 高级功能 | 高级业务功能 | P0 |  |
| optimization | 系统优化 | 整体优化 | P1 |  |
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

| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| general | 通用 | 用户自定义分类 | P0 |  |
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
  ADR_COUNT=$(ls "$PROJECT_ROOT/$ADR_DIR"/$ADR_PATTERN 2>/dev/null | grep -v -- '-0000-template\.md$' | wc -l | tr -d '[:space:]')
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

状态初始化逻辑已抽取到 `_lib/roadmap_state.py::init_state()`,默认生成 phase-1/2/3 模板。bash 端只保留 source + 1 行调用,确保 AI 助手有可执行规约可循。

```bash
# init Step 4: 状态文件初始化（已抽取到 _lib/roadmap_state.py::init_state）
#   init_state(state_file, current_phase='phase-1')
#   默认 3-phase 模板（arch-design/infra-setup/core-impl/core-test 等），
#   函数内部处理 mkdir + 原子写入。

PROJECT_ROOT="$PROJECT_ROOT" STATE_FILE="$STATE_FILE" python3 -c '
import os, sys
sys.path.insert(0, os.path.join(os.environ["PROJECT_ROOT"]))
from skills._lib.roadmap_state import init_state
init_state(os.environ["STATE_FILE"])
'
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

读取 + 展示已合并抽取到 `_lib/roadmap_state.py::render_status_view()`。模块函数内部处理 roadmap.md 缺失、state.json 缺失、阶段进度、门控状态展示。

```bash
# status Step 1: 渲染路线图状态（已抽取到 _lib/roadmap_state.py::render_status_view）
#   render_status_view(roadmap_file, state_file) → 返回 0/1
#   roadmap.md 缺失时返回 1 + 友好提示,不抛错。

PROJECT_ROOT="$PROJECT_ROOT" ROADMAP_FILE="$ROADMAP_FILE" STATE_FILE="$STATE_FILE" python3 -c '
import os, sys
sys.path.insert(0, os.path.join(os.environ["PROJECT_ROOT"]))
from skills._lib.roadmap_state import render_status_view
sys.exit(render_status_view(
    os.environ["ROADMAP_FILE"],
    os.environ["STATE_FILE"],
))
'
```

### 步骤 2：解析并展示

见 Step 1 — 已合并到 `render_status_view()` 单次调用。阶段进度、分类详情、门控状态都在模块内部统一处理。

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

# 追加到 roadmap.md + 更新状态文件（已抽取到 _lib/roadmap_state.py::add_phase）
PROJECT_ROOT="$PROJECT_ROOT" ROADMAP_FILE="$ROADMAP_FILE" STATE_FILE="$STATE_FILE" \
PHASE_ID="$PHASE_ID" PHASE_NAME="$PHASE_NAME" PREREQ_PHASE="$PREREQ_PHASE" python3 -c '
import os, sys
sys.path.insert(0, os.path.join(os.environ["PROJECT_ROOT"]))
from skills._lib.roadmap_state import add_phase
sys.exit(add_phase(
    os.environ["ROADMAP_FILE"],
    os.environ["STATE_FILE"],
    os.environ["PHASE_ID"],
    os.environ["PHASE_NAME"],
    os.environ.get("PREREQ_PHASE", ""),
))
'
```

---

## 命令：validate — 验证 change 分类

### 验证逻辑

校验逻辑已抽取到 `_lib/roadmap_state.py::validate_change()`,函数内部用 `yaml.safe_load` 解析 meta、用 regex 解析 roadmap 阶段 + 分类结构,保留所有原有错误提示与成功消息字符串。

```bash
# validate: 校验 change 分类（已抽取到 _lib/roadmap_state.py::validate_change）
#   validate_change(roadmap_file, meta_file, change_name) → 返回 0/1
#   函数内部处理: meta 缺失 / yaml 解析失败 / 阶段不存在 / 分类不在阶段中

PROJECT_ROOT="$PROJECT_ROOT" ROADMAP_FILE="$ROADMAP_FILE" \
META_FILE="$META_FILE" CHANGE_NAME="$CHANGE_NAME" python3 -c '
import os, sys
sys.path.insert(0, os.path.join(os.environ["PROJECT_ROOT"]))
from skills._lib.roadmap_state import validate_change
sys.exit(validate_change(
    os.environ["ROADMAP_FILE"],
    os.environ["META_FILE"],
    os.environ["CHANGE_NAME"],
))
'
```

---

## 命令：migrate — 9 步原子化迁移到 `.rddf/roadmap/`

**目的**: 从单文件 `roadmap.md` 迁移到 `.rddf/roadmap.md` 主文档 + `.rddf/roadmap/{phases,features,archive}/` fragment 树（全部 git tracked）。

**使用**:

```bash
rddf roadmap migrate --dry-run          # 预览切片（不修改任何文件）
rddf roadmap migrate --execute --yes    # 执行迁移（需 --yes 显式确认）
rddf roadmap migrate --rollback <backup-dir> --yes  # 回滚到指定 backup
```

**9 步流程**: preflight → parse main → plan slice → dry-run → backup → execute → validate → archive hint → rollback hint

**约束**:

- 拒绝 `--execute` 不带 `--yes`（safety gate）
- 自动创建 backup 到 `.rddf/.roadmap-migrate-backup-<timestamp>/`（含 3 文件：root `roadmap.md` + `openspec/changes/<name>/tasks.md` + `.arch-handoff.json`）
- 如在 git 仓库，自动 `git tag pre-roadmap-migrate-<timestamp>`
- 任何写入失败保留 backup + 删除已写入 + `exit 1`（不留半迁移状态）
- 解析支持两种 phase 格式：`| phase-N | theme | ... |` (table row) 和 `### Phase N: theme` (heading)

**双格式支持**: awk parser 同时识别 table row 和 heading 两种格式,实际 rdd-workflow `roadmap.md` 主要用 `### Phase N: title` heading, 因此 parse 9 个 phase 而非 0。

---

## 命令：validate-fragments — 8 规则 R1-R8 校验

**目的**: 对 `.rddf/roadmap/` 跑 8 条校验规则，exit code 0/1/2/3 对齐 `openspec validate`。

**使用**:

```bash
rddf roadmap validate-fragments                       # 默认 WARNING 级
STRICT_ROADMAP_REFS_GATE=yes rddf roadmap validate-fragments  # CRITICAL 阻断
SKIP_ROADMAP_REFS_GATE=yes rddf roadmap validate-fragments    # 跳过
```

**8 条规则**:

| 规则 | 严重度 | 说明 |
|------|--------|------|
| R1 | CRITICAL | feature.phase_refs 必须引用主文档已注册的 phase |
| R2 | CRITICAL | fragment id 全局唯一 |
| R3 | CRITICAL | kind 必须是 `phase` 或 `feature` |
| R4 | CRITICAL | phase id 命名 `^phase-\d+(\.\d+)?$`（严格化后） |
| R5 | WARNING | feature 必须有非空 phase_refs |
| R6 | CRITICAL | phase fragment id 必须在主文档 phase table 注册 |
| R7 | WARNING | fragments_dir 缺失（v1 handoff 向后兼容） |
| R8 | CRITICAL | 主文档 phase table 不允许重复 id |

**双入口**: 同一 `validate_fragment_refs` 实现由两个入口调用：
- 用户门控（`roadmap validate-fragments`，exit code 严格）
- 诊断（`rdd-doctor --category roadmap-refs`，CRITICAL/WARNING/INFO 分级报告，仍只读）

---

## 命令：add-feature — 创建 feature fragment

创建 `.rddf/roadmap/features/feat-<name>.md` 文件并刷新 `.rddf/roadmap.md` AUTO-INDEX。

### 用法

```bash
rddf roadmap add-feature <name> --phase-refs <p1,p2,...> --theme "<text>" [--status a|d|x] [--force]
```

### 选项

| 选项 | 必填 | 说明 |
|------|------|------|
| `--phase-refs` | 是 | 逗号分隔的 phase IDs；每个 ID 必须存在于 `list_active_fragments(kind="phase")` |
| `--theme` | 是 | 单行主题（中文短句，≤ 50 字推荐） |
| `--status` | 否 | `a` (active) / `d` (done) / `x` (archived)；默认 `a` |
| `--force` | 否 | 覆盖已存在的 `feat-<name>.md`（不 merge，销毁旧 body） |

### 示例

```bash
# 最小化：创建跨 phase-2 和 phase-3 的 active feature
rddf roadmap add-feature auth-v2 \
    --phase-refs phase-2,phase-3 \
    --theme "RBAC 权限模型"

# 创建时标 done（罕见）
rddf roadmap add-feature deprecate-legacy-auth \
    --phase-refs phase-3 \
    --theme "下线旧版认证" \
    --status d

# 覆盖已有 fragment（销毁 body 编辑）
rddf roadmap add-feature auth-v2 \
    --phase-refs phase-2,phase-3 \
    --theme "RBAC 权限模型 (v2 重生)" \
    --force
```

### 退出码

| Code | 含义 |
|------|------|
| 0 | 成功 |
| 1 | 校验错误（phase_refs 不存在 / 重复无 --force / name 非 kebab-case / theme 为空） |
| 2 | 使用错误（缺少必填参数 / 非法 flag） |

### 底层实现

`_lib/roadmap_state.py::add_feature`（Python）+ `skills/roadmap/scripts/roadmap_add_feature.sh`（shell wrapper）。
该 primitive 是 `add-hierarchical-roadmap-structure`（shipped 2026-08-20）"关键场景 3"的操作入口补全。

---

## 嵌套阶段语法

**Sub-phase** (如 `phase-3.1`) 通过 promote 创建：从 `phases/phase-3.md` 内的 section 拆出为独立 `phases/phase-3.1.md`，frontmatter 含 `id: phase-3.1` + `kind: phase` + `phase_refs: [phase-3]`。R4 严格化后只允许 `phase-N` 或 `phase-N.M`（单层 sub-phase），禁止 `phase-1-2` 嵌套命名。

**Feature** (跨阶段) 是 `features/<id>.md`，`kind: feature` + 非空 `phase_refs: [phase-X, phase-Y, ...]`。feature 主题是 metadata，不参与主文档 theme 覆盖度计算（保持 proposal `roadmap-proposal-guidance` 的设计）。

---

## 命令：advance — 推进阶段

### 前置检查 + 执行推进（合并）

前置检查(分类完成 + 门控条件)与执行推进(找下一阶段 + 更新 state)已合并抽取到 `_lib/roadmap_state.py::advance_phase()`,函数内部用 re.findall 提取阶段列表、用 json 读写 state,保留所有原输出字符串。

```bash
# advance: 推进阶段（已抽取到 _lib/roadmap_state.py::advance_phase）
#   advance_phase(roadmap_file, state_file) → 返回 0/1
#   函数内部: 1) 预检分类完成 2) 预检门控条件 3) 找下一阶段
#             4) 标记当前完成 5) 激活下一阶段 6) 写回 state

PROJECT_ROOT="$PROJECT_ROOT" ROADMAP_FILE="$ROADMAP_FILE" STATE_FILE="$STATE_FILE" python3 -c '
import os, sys
sys.path.insert(0, os.path.join(os.environ["PROJECT_ROOT"]))
from skills._lib.roadmap_state import advance_phase
sys.exit(advance_phase(
    os.environ["ROADMAP_FILE"],
    os.environ["STATE_FILE"],
))
'
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
    PROJECT_ROOT="$PROJECT_ROOT" ROADMAP_FILE="$ROADMAP_FILE" \
    PHASE="$PHASE" python3 -c '
import os, sys
sys.path.insert(0, os.path.join(os.environ["PROJECT_ROOT"]))
from skills._lib.roadmap_state import get_phase_categories
get_phase_categories(os.environ["ROADMAP_FILE"], os.environ["PHASE"])
'
}
```

### 更新 change 计数

```bash
update_change_count() {
    CHANGE_NAME=$1
    PHASE=$2
    CATEGORY=$3
    OPERATION=${4:-"add"}  # add 或 remove
    PROJECT_ROOT="$PROJECT_ROOT" STATE_FILE="$STATE_FILE" \
    CHANGE_NAME="$CHANGE_NAME" PHASE="$PHASE" CATEGORY="$CATEGORY" OPERATION="$OPERATION" python3 -c '
import os, sys
sys.path.insert(0, os.path.join(os.environ["PROJECT_ROOT"]))
from skills._lib.roadmap_state import update_change_count
update_change_count(
    os.environ["STATE_FILE"],
    os.environ["CHANGE_NAME"],
    os.environ["PHASE"],
    os.environ["CATEGORY"],
    os.environ.get("OPERATION", "add"),
)
'
}
```

---

## 嵌套阶段语法（可选扩展）

对于业务演进包含子阶段的项目（如 CppTLM Phase 7.A-7.F / Phase 9.0-9.6），roadmap 支持嵌套 ID：

```markdown
### Phase 7: CPU+GPGPU Fused SoC (APU-first) (phase-3)
**目标**: ...
**完成条件**:
  - [ ] phase-3.1 ~ phase-3.6 全部完成

#### 任务分类                    ← 【硬性约束】必须先于所有 ### 子阶段 heading
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| gpu-infra | 7.A GPU 基础设施 | (phase-3.1) | P0 | ... |
| ... | | | | |

### 7.A GPU 基础设施 (phase-3.1)  ← 子阶段 heading
#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| gpu-bundle | ... | ... | P0 | ... |
```

**约束**：

1. 父 phase 伞表必须先于所有 `###` 子阶段 heading（`get_phase_categories` section 边界 regex 限制）
2. change meta `roadmap.phase` 可指向子阶段 ID（`phase-3.3`）
3. `advance_phase` 自动聚合子阶段完成度
4. 嵌套 ID 语法：`phase-N.M`（数字后缀），业务标签（7.A/9.0）出现在 heading 文本
5. 嵌套是正向扩展，平铺 `phase-N` 仍完全支持

---

## 关键约束

1. **roadmap.md 是用户可编辑的**：提供模板，但允许用户自由修改
2. **状态文件自动维护**：.roadmap-state.json 由技能自动更新，用户不直接编辑
3. **兼容模式**：无 roadmap.md 时，所有 change 归为 "default" 阶段
4. **阶段门控可跳过**：提供 `--force` 选项强制推进阶段（不推荐）
5. **分类动态调整**：支持在任何时候添加/修改分类定义
