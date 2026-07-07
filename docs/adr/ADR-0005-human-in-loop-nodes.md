# ADR-0005: Human-in-Loop 节点定义与菜单系统

> **状态**: 已采纳
> **日期**: 2026-06-22
> **决策者**: sisyphus
> **依据**: ADR-0002 (交互模式配置), ADR-0003 (三阶段架构), ADR-0004 (Loop 引擎)

## Context

在 ADR-0002 中，我们定义了三种交互模式（loop/menu/hybrid），其中 **hybrid 模式**需要在"关键节点"保留 human-in-loop（显示菜单询问用户）。但以下问题需要明确决策：

1. **哪些节点是关键节点？**: 不是所有决策点都需要人工介入，需要明确定义标准
2. **菜单如何显示？**: 在 hybrid 模式下，菜单的格式、选项、默认行为需要统一规范
3. **如何跳过菜单？**: 用户可能希望在某些场景下跳过特定节点的菜单（通过配置）
4. **如何防止菜单阻塞 AI 助手？**: v1.x 的 `read -p` 阻塞问题（P0-1, P0-9）必须在 v2.x 彻底解决

**约束**:
- **菜单不能完全移除**: 是 human-in-loop 的核心机制
- **必须可配置**: 用户可通过 `.rddf.json` 自定义关键节点列表
- **AI 助手兼容**: 菜单必须支持环境变量或非阻塞输入

**设计原则**:
1. **高风险操作必须人工确认**: merge、archive、delete 等破坏性操作
2. **架构决策必须人工审查**: ADR 创建、roadmap 定义
3. **常规操作可自动跳过**: worktree 创建、计划生成、单元测试
4. **错误/冲突必须人工介入**: 自动化无法解决的情况

## Decision

我们定义 **7 类关键节点**，每类节点有统一的菜单格式、配置项、跳过条件：

### 关键节点分类

#### 1. 架构定义节点 (arch 阶段)

| 节点 ID | 节点名称 | 触发条件 | 菜单内容 | 跳过条件 |
|---------|---------|---------|---------|---------|
| `arch.adr_create` | ADR 创建确认 | 检测到新架构决策需要记录 | 显示 ADR 草案，确认/编辑/跳过 | 无（必须确认） |
| `arch.roadmap_define` | Roadmap 定义 | roadmap.md 不存在或需要重大更新 | 显示 roadmap 模板，选择/自定义 | 已有 roadmap.md 且 `skip_existing_roadmap: true` |
| `arch.gap_analysis` | 架构差距分析 | 检测到架构差距文档缺失 | 显示差距分析草案，确认/编辑 | `auto_skip_gap_analysis: true` |

**菜单示例** (`arch.adr_create`):
```
=== 关键决策点: ADR 创建 ===

检测到新的架构决策需要记录:
  决策: 采用 JWT 认证替代 Session
  影响范围: 认证模块、API 网关、前端

ADR 草案已生成: docs/adr/ADR-0005-jwt-authentication.md

请选择操作:
  1. 确认并保存 ADR
  2. 编辑 ADR 内容
  3. 跳过（不记录此决策）

输入编号 (1-3) [默认: 1]:
```

#### 2. 变更生成节点 (plan 阶段)

| 节点 ID | 节点名称 | 触发条件 | 菜单内容 | 跳过条件 |
|---------|---------|---------|---------|---------|
| `plan.change_select` | Change 选择 | 检测到多个 change 候选 | 显示候选列表，选择要处理的 | `auto_select_changes: true`（选择全部） |
| `plan.propose_confirm` | Change 内容确认 | propose 生成 artifacts 后 | 显示 proposal.md 摘要，确认/编辑 | `auto_confirm_proposal: true` |
| `plan.deps_review` | 依赖分析报告审查 | deps 分析完成后 | 显示依赖冲突/建议，确认继续 | `auto_skip_deps_review: true` |

**菜单示例** (`plan.change_select`):
```
=== 关键决策点: Change 选择 ===

检测到 3 个 change 候选:

  1. add-auth          (从 ADR-0005: JWT 认证)
  2. refactor-db       (从 TODO: 数据库重构)
  3. add-rate-limiting (从架构差距: 限流机制)

请选择要处理的 changes:
  1. 选择全部 (3 个)
  2. 手动选择
  3. 跳过此轮扫描

输入编号 (1-3) [默认: 1]:
```

#### 3. Worktree 创建节点 (ship 阶段)

| 节点 ID | 节点名称 | 触发条件 | 菜单内容 | 跳过条件 |
|---------|---------|---------|---------|---------|
| `ship.worktree_create` | Worktree 创建确认 | 为新 change 创建 worktree 前 | 显示 worktree 配置（分支名、并行数） | `auto_create_worktree: true` |
| `ship.parallel_limit` | 并行限制调整 | 检测到多个 changes 待处理 | 确认并行 worktree 数量 | 使用配置默认值 |

**菜单示例** (`ship.worktree_create`):
```
=== 关键决策点: Worktree 创建 ===

即将为以下 changes 创建 worktrees:

  1. add-auth          → openspec/add-auth
  2. refactor-db       → openspec/refactor-db

配置:
  并行数量: 2 (最大: 3)
  分支命名: openspec/<change-name>

请选择操作:
  1. 确认创建
  2. 修改并行数量
  3. 只创建部分 worktrees
  4. 跳过（稍后手动创建）

输入编号 (1-4) [默认: 1]:
```

#### 4. 计划生成节点 (ship 阶段)

| 节点 ID | 节点名称 | 触发条件 | 菜单内容 | 跳过条件 |
|---------|---------|---------|---------|---------|
| `ship.plan_review` | Prometheus 计划审查 | 计划生成完成后 | 显示任务列表摘要，确认/调整 | `auto_confirm_plan: true` |
| `ship.plan_fallback` | 计划回退决策 | Prometheus 不可用时 | 选择回退策略（superpowers/手动） | 无（必须选择） |

#### 5. 执行监控节点 (ship 阶段)

| 节点 ID | 节点名称 | 触发条件 | 菜单内容 | 跳过条件 |
|---------|---------|---------|---------|---------|
| `ship.execute_error` | 执行错误处理 | work unit 执行失败 | 显示错误详情，选择修复策略 | `auto_retry: true`（自动重试 3 次） |
| `ship.execute_stuck` | 执行卡住检测 | worktree 长时间无进度 | 显示进度详情，选择继续/跳过/中止 | `auto_skip_stuck: true` |

**菜单示例** (`ship.execute_error`):
```
=== 关键决策点: 执行错误处理 ===

Work Unit 5/15 执行失败 (change: add-auth):

  错误: ctest 测试失败
  失败测试: test_jwt_token_validation
  错误详情: expected 200, got 401

建议修复策略:
  1. 自动试 (重新生成代码)
  2. 查看失败详情，手动修复
  3. 跳过此 Work Unit (标记为待办)
  4. 中止此 worktree 执行

重试次数: 0/3
输入编号 (1-4) [默认: 1]:
```

#### 6. 归档确认节点 (ship 阶段)

| 节点 ID | 节点名称 | 触发条件 | 菜单内容 | 跳过条件 |
|---------|---------|---------|---------|---------|
| `ship.archive_confirm` | Archive 前确认 | worktree 执行完成，准备归档 | 显示 merge + archive 操作详情 | `auto_archive: true` |
| `ship.merge_conflict` | Merge 冲突处理 | merge 时检测到冲突 | 显示冲突文件，选择解决策略 | 无（必须处理） |

**菜单示例** (`ship.archive_confirm`):
```
=== 关键决策点: Archive 确认 ===

Change "add-auth" 已完成 (15/15 work units):

即将执行的操作:
  1. Merge openspec/add-auth → main (fast-forward)
  2. openspec archive add-auth
  3. 删除 worktree (.rddf/state/add-auth-wt/)
  4. 删除分支 (openspec/add-auth)

验证:
  ✅ 所有 work units 完成
  ✅ 测试通过 (15/15)
  ✅ 无 merge 冲突

请选择操作:
  1. 确认归档
  2. 查看详细报告
  3. 跳过归档（保留 worktree）
  4. 中止

输入编号 (1-4) [默认: 1]:
```

#### 7. 清理确认节点 (ship 阶段)

| 节点 ID | 节点名称 | 触发条件 | 菜单内容 | 跳过条件 |
|---------|---------|---------|---------|---------|
| `ship.cleanup_confirm` | Cleanup 前确认 | 清理残留 worktrees/branches | 显示待删除列表，确认 | `auto_cleanup: true` |
| `ship.force_delete` | 强制删除确认 | 分支有未合并提交 | 警告风险，确认强制删除 | 无（必须确认） |

### 菜单系统统一规范

#### 菜单格式

```
=== 关键决策点: <节点名称> ===

[上下文信息]
[选项列表]
[默认值提示]

输入编号 (1-N) [默认: 1]:
```

#### 菜单实现 (非阻塞)

```bash
# skills/_lib/interaction.sh

show_menu() {
    local node_id="$1"
    local menu_content="$2"
    local default_choice="${3:-1}"
    
    # 检查是否可自动跳过
    if can_skip_node "$node_id"; then
        echo "ℹ️  节点 $node_id 已自动跳过 (配置允许)"
        return 0
    fi
    
    # 显示菜单
    echo "$menu_content"
    
    # 非阻塞读取 (支持环境变量覆盖)
    local choice="${RDDF_MENU_CHOICE:-}"
    if [ -z "$choice" ]; then
        # interactive 模式：读取用户输入
        read -r choice
        choice="${choice:-$default_choice}"
    fi
    
    # 记录事件
    log_event "human_in_loop" "{\"node\": \"$node_id\", \"choice\": \"$choice\"}"
    
    echo "$choice"
}

can_skip_node() {
    local node_id="$1"
    
    # 检查配置
    local skip_config=$(jq -r ".interaction.menu.human_in_loop_nodes[] | select(. == \"$node_id\") | .skip_if" .rddf.json 2>/dev/null)
    
    if [ "$skip_config" = "always" ]; then
        return 0
    elif [ "$skip_config" = "no_errors" ]; then
        # 检查是否有错误
        if jq -e '.arch_side.health.errors | length == 0' .rddf/state/state-vector.json >/dev/null 2>&1; then
            return 0
        fi
    fi
    
    return 1
}
```

#### 环境变量支持

| 环境变量 | 用途 | 示例 |
|---------|------|------|
| `RDDF_MENU_CHOICE` | 预设菜单选择（AI 助手用） | `RDDF_MENU_CHOICE=1 skill_use("loop")` |
| `RDDF_INTERACTION_MODE` | 交互模式 | `loop`, `menu`, `hybrid` |
| `RDDF_SKIP_NODES` | 跳过节点列表（逗号分隔） | `plan.change_select,ship.archive_confirm` |
| `RDDF_TIMEOUT` | 菜单超时（秒） | `30` (超时使用默认值) |

### 配置文件扩展

```json
{
  "interaction": {
    "mode": "hybrid",
    "menu": {
      "show_tips": true,
      "confirm_destructive": true,
      "timeout_seconds": 30,
      "human_in_loop_nodes": [
        {
          "node": "arch.adr_create",
          "skip_if": "never",
          "description": "ADR 创建必须人工确认"
        },
        {
          "node": "plan.change_select",
          "skip_if": "auto_select_changes",
          "description": "可配置自动选择全部 changes"
        },
        {
          "node": "ship.archive_confirm",
          "skip_if": "auto_archive",
          "description": "可配置自动归档"
        }
      ]
    }
  }
}
```

### 影响范围

- **In Scope**:
  - 新增 `skills/_lib/interaction.sh` (菜单系统实现)
  - 修改 `skills/guide-arch.md`、`skills/guide-plan.md`、`skills/guide-ship.md` (插入关键节点)
  - 更新 `.rddf.json` Schema (human_in_loop_nodes 配置)
  - 新增菜单单元测试
  
- **Out Scope**:
  - 不改变现有 phase 逻辑（只在关键节点插入菜单）
  - 不改变子技能接口

### 备选方案

| 备选 | 理由 |
|------|------|
| **固定关键节点** | 拒绝：缺乏灵活性，不同项目需求不同 |
| **完全可配置** | 拒绝：配置过于复杂，用户难以理解 |
| **分类定义 + 部分可配置** | 接受：平衡灵活性和易用性 |

## Consequences

### 正面

- **Human-in-Loop 保障**: 关键决策点强制人工确认，避免自动化风险
- **灵活性**: 用户可通过配置跳过非关键节点
- **AI 友好**: 环境变量支持，AI 助手可预设菜单选择
- **一致性**: 统一菜单格式，降低学习成本
- **可观测性**: 每次菜单交互记录到事件流

### 负面 / 风险

- **菜单数量增加**: 7 类节点可能显示频繁
  - **缓解**: hybrid 模式只在真正需要时显示，loop 模式完全跳过
- **配置复杂度**: human_in_loop_nodes 配置需要理解节点 ID
  - **缓解**: 提供配置模板和文档
- **超时处理**: 菜单超时使用默认值可能不符合用户意图
  - **缓解**: 超时前显示警告，允许延长超时

### 后续待办

- [ ] 实现 `skills/_lib/interaction.sh` (菜单系统)
- [ ] 在三阶段状态机中插入关键节点
- [ ] 添加菜单单元测试（非阻塞、环境变量、超时）
- [ ] 添加集成测试（hybrid 模式 × 关键节点）
- [ ] 编写菜单系统文档和配置示例
- [ ] 提供默认 `.rddf.json` 模板

## References

- ADR-0002 — 目标驱动接口与交互模式配置
- ADR-0003 — 三阶段架构 (arch → plan → ship)
- ADR-0004 — Loop 引擎核心设计
- `docs/audit/2026-06-05-workflow-audit.md` §15.2 — `read -p` 阻塞反模式
- `skills/_lib/interaction.sh` — 菜单系统实现（待创建）
- Cursor Agent — human-in-loop 节点设计参考

