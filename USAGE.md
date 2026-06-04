# OpenSpec 工作流技能使用指南

> 基于 `spec-workflow-guide` 推荐器（spec-side 调 `spec-workflow-guide-spec`，ship-side 调 `spec-workflow-guide-ship`），覆盖从提案到归档的完整生命周期。
> 支持多 change 并行执行，可分离到不同终端同时运行。

---

## 核心概念

### 两种执行模式

| 模式 | 说明 | 场景 |
|------|------|------|
| **🔒 阻塞执行** | 在当前 session 执行，等待任务完成 | 小改动、快速验证 |
| **🔓 分离执行** | 在新终端执行，当前 session 立即返回 | 多 change 并行、长任务 |

### 状态文件

| 文件 | 位置 | 用途 |
|------|------|------|
| `workflow-state.md` | 项目根目录 | 当前进度、变更列表、执行状态 |
| `workflow-progress.md` | 项目根目录 | 操作日志、每步记录 |
| `proposal-suggestions.md` | 项目根目录 | 扫描出的建议列表，随 git 版本控制 |

### 执行状态

| 状态 | 含义 |
|------|------|
| ⏳ 等待执行 | 未开始 |
| 🔒 执行中 | 在此 session 阻塞执行 |
| 🔓 分离执行 | 在新终端执行，不阻塞 |
| ✅ 完成 | 所有任务完成 |

---

## 快速开始

### 启动交互式向导

```
用户: skill_use("spec-workflow-guide")
```

向导会自动检查状态并给出当前合适的选项菜单。无需指定参数。

---

## 完整流程

### Phase 1 — Setup（环境检查）

首次启动向导时自动进入。

**检测项**：
- openspec CLI 是否可用
- git 工作区是否干净
- 当前分支
- 已有的 worktree 列表
- 构建目录是否存在

**菜单示例**：

```
环境检查完成。

  openspec CLI: ✅ 1.3.1
  git 工作区:  ✅ 干净
  当前分支:    main
  Worktrees:   无
  构建目录:    ✅ 存在
  活跃 changes: 0

请选择:
1. ✅ 继续 → 进入 Propose 阶段
2. 🔄 重新检查
i. 其他操作
```

---

### Phase 2 — Propose（扫描并创建 Change）

扫描 ADR 和代码 TODO，生成建议列表，用户选择后创建 artifacts。

**行为**：
1. 扫描 `docs/adr/ADR-*.md` — 找到已采纳但未实现的 ADR 项
2. 扫描 `docs/architecture/*-gap-analysis.md` — 找到功能缺口
3. 扫描代码中的 `TODO`/`FIXME` 标记
4. 生成 `proposal-suggestions.md` 建议列表

**菜单示例**：

```
建议列表（来自 ADR 扫描 + 代码 TODO）：

🔴 高优先级
1. fix-ns-pollution  — 修复命名空间污染 (ADR-033, 3 个任务)
2. add-stream-pipes  — 实现 Stream 管道操作符 (ADR-022, 5 个任务)

🟡 中优先级
3. add-cdc-support   — 跨时钟域支持

当前已创建: 无

请选择:
1. 创建 fix-ns-pollution
2. 创建 add-stream-pipes
3. 创建 add-cdc-support
4. ✅ 完成 Propose 阶段 → 进入 Plan 阶段
5. 📋 查看所有已创建的 change 详情
i. 手动输入 change 名称
```

**创建后重新进入此阶段**——可以连续创建多个 change，然后选选项 4 完成。

---

### Phase 3 — Plan（创建 Worktree + 生成计划）

为已创建的 change 创建 worktree 并生成 Prometheus 计划。

**行为**：
1. 展示所有活跃 changes 的状态表
2. 用户选择要处理的 change
3. 执行 COMMIT GATE（脏检测 + 已提交验证）
4. 创建 branch + worktree
5. 在 worktree 内生成 Prometheus 计划
6. **立即选择执行模式**

**菜单示例**：

```
Plan 阶段

📋 活跃 Changes:
| 变更 | Artifacts | Worktree | 计划文件 |
|-----|-----------|----------|---------|
| fix-ns-pollution | ✅ | ❌ | ❌ |
| add-stream-pipes | ✅ | ❌ | ❌ |

请选择:
1. 为 fix-ns-pollution 创建 worktree + 生成计划
2. 为 add-stream-pipes 创建 worktree + 生成计划
3. 批量处理：全部为已提交的变化创建 worktree
4. 🔄 切换当前焦点变更
5. ↩️ 返回 Propose 阶段（创建更多 change）
i. 其他输入
```

**Worktree 创建完成 → 立即选择执行模式**：

```
fix-ns-pollution worktree 已就绪，请选择执行方式：

📋 fix-ns-pollution 状态:
  Worktree: .zcf/fix-ns-pollution-wt
  计划文件: .sisyphus/plans/fix-ns-pollution.md ✅
  任务数: 3

请选择执行方式:
1. 🔒 在此 session 执行（阻塞）— 等待任务完成后返回
2. 🔓 分离执行（新终端）— 给出操作指引，立即返回
i. 其他输入
```

**分离执行指引**：

```
🔓 分离执行指引

为 fix-ns-pollution 启动分离执行：

1. 在新终端中执行：
   cd /workspace/project/CppHDL/.zcf/fix-ns-pollution-wt
   skill_use("spec-workflow-execute")

2. execute 结果会自动写入 tasks.md

3. 完成后，在此 session 运行 guide 查看最新进度

当前状态：fix-ns-pollution 🔓 等待分离执行
```

**返回 Plan 前的检查 — 是否进入监控**：

当有 worktree 已就绪时，提示选择进入监控或继续返回 Plan：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 发现 1 个 worktree 已就绪

请选择:
1. ✅ 进入 Execute 监控模式（实时监控所有 worktree 进度）
2. 🔄 继续返回 Plan 阶段（创建更多 worktree）
i. 其他输入
```

---

### Phase 4 — Execute（监控与执行）

Execute 阶段是**监控模式**——读取 tasks.md 进度、显示所有 worktree 状态、提供执行入口。不是实际执行者。

**监控模式入口点**（三处均可进入）：

| 入口点 | 触发条件 |
|--------|---------|
| **工作流状态恢复** | 新 session 调用 guide，检测到已有 worktree |
| **Plan 返回前** | worktree 创建完成后选择执行模式前 |
| **Execute 菜单** | 任何时候可刷新或返回 Plan |

**前置检测**（每次入口执行）：

```bash
# 读取所有 tasks.md 的实际进度
LAST_CHECK=$(date "+%Y-%m-%d %H:%M:%S")

for wt in $(git worktree list | grep "openspec/" | awk '{print $1}'); do
    branch=$(git worktree list | grep "$wt" | awk '{print $3}')
    name=$(echo "$branch" | sed 's|openspec/||')
    tasks_file="$wt/openspec/changes/$name/tasks.md"

    total=$(grep -c "^- \[" "$tasks_file" 2>/dev/null || echo 0)
    done=$(grep -c "^- \[x\]" "$tasks_file" 2>/dev/null || echo 0)
    progress="${done}/${total}"
    echo "  $name → $progress"
done

echo ""
echo "上次检测: $LAST_CHECK"
```

**菜单示例**：

```
Execute 阶段（监控模式）

📋 所有 Worktrees 状态:（实时读取 tasks.md）
| 变更 | Worktree | 进度 | 执行状态 |
|-----|----------|------|---------|
| fix-ns-pollution | .zcf/fix-ns-pollution-wt | 1/3 | 🔒 执行中 |
| add-stream-pipes | .zcf/add-stream-pipes-wt | 2/5 | 🔓 分离执行 |

上次检测: 2026-05-18 10:35:00

请选择:
1. 🔒 在此 session 执行 fix-ns-pollution（阻塞）
2. 🔓 分离执行 fix-ns-pollution（新终端）
3. 🔒 在此 session 执行 add-stream-pipes（阻塞）
4. 🔓 分离执行 add-stream-pipes（新终端）
5. 📋 查看任务列表（指定变更）
6. 🔧 运行构建验证（指定变更）
7. 🔄 刷新进度（重新读取所有 tasks.md）
8. ↩️ 返回 Plan 阶段（创建更多 worktree）
i. 其他输入
```

**关键特性**：
- 任何时候可以返回 Plan 阶段添加更多 worktree
- 进度来自 tasks.md 实际读取，每次入口自动刷新
- 「🔄 刷新进度」可手动重新读取所有 tasks.md
- 「上次检测」时间戳让用户知道状态是实时的

📋 所有 Worktrees 状态:
| 变更 | Worktree | 进度 | 执行状态 |
|-----|----------|------|---------|
| fix-ns-pollution | .zcf/fix-ns-pollution-wt | 1/3 | 🔒 执行中 |
| add-stream-pipes | .zcf/add-stream-pipes-wt | 0/5 | ⏳ 等待 |

请选择:
1. 🔒 在此 session 执行 fix-ns-pollution（阻塞）
2. 🔓 分离执行 fix-ns-pollution（新终端）
3. 🔒 在此 session 执行 add-stream-pipes（阻塞）
4. 🔓 分离执行 add-stream-pipes（新终端）
5. 📋 查看任务列表（指定变更）
6. 🔧 运行构建验证（指定变更）
7. ↩️ 返回 Plan 阶段（创建更多 worktree）
i. 其他输入
```

**关键特性**：
- 任何时候可以返回 Plan 阶段添加更多 worktree
- 进度来自 tasks.md 实际读取，不依赖 state
- 分离执行的 change 在新终端完成后自动同步进度

---

### Phase 5 — Status + Archive（状态检查与归档）

检查所有 change 状态，独立归档。

**菜单示例**：

```
Status 阶段

📋 所有 Changes 状态:
| 变更 | Worktree | 任务进度 | 状态 |
|-----|----------|---------|------|
| fix-ns-pollution | .zcf/fix-ns-pollution-wt | 3/3 ✅ | 可归档 |
| add-stream-pipes | .zcf/add-stream-pipes-wt | 2/5 🔄 | 进行中 |

请选择:
1. 归档 fix-ns-pollution（merge → archive → cleanup）
2. 归档 add-stream-pipes（需先完成所有任务）
3. 📊 全局概览（所有 change + worktree）
4. 🔍 详细检测（同步问题等）
5. ↩️ 返回 Execute 阶段
i. 其他输入
```

**归档流程**：

```bash
# 1. Merge worktree → main
cd ".zcf/${CHANGE_NAME}-wt"
git checkout main
git merge --ff-only "openspec/${CHANGE_NAME}"

# 2. Archive
openspec archive "${CHANGE_NAME}" --yes

# 3. Cleanup
git worktree remove ".zcf/${CHANGE_NAME}-wt"
git branch -d "openspec/${CHANGE_NAME}"

cd /workspace/project/CppHDL
```

---

## 并行执行示例

### 场景：同时处理 fix-ns-pollution 和 add-stream-pipes

**Terminal A（主控 session）**：

```
skill_use("spec-workflow-guide-ship")
→ Plan 阶段 → 创建 fix-ns-pollution worktree
→ 选择 🔓 分离执行
→ 切换 add-stream-pipes → 创建 worktree
→ 选择 🔓 分离执行
→ 进入 Execute 监控模式

（主控 session 保持可操作，可继续其他操作或等待）
```

**Terminal B（fix-ns-pollution 执行）**：

```
cd /workspace/project/CppHDL/.zcf/fix-ns-pollution-wt
skill_use("spec-workflow-execute")
→ 阻塞执行所有任务
→ 更新 tasks.md
→ 返回
```

**Terminal C（add-stream-pipes 执行）**：

```
cd /workspace/project/CppHDL/.zcf/add-stream-pipes-wt
skill_use("spec-workflow-execute")
→ 阻塞执行所有任务
→ 更新 tasks.md
→ 返回
```

**回到 Terminal A**：

```
skill_use("spec-workflow-guide-ship")
→ Execute 监控模式检测到 tasks.md 进度已更新
→ 显示最新进度
→ 可选择归档或继续监控
```

---

## 状态文件格式

### workflow-state.md

```markdown
# OpenSpec 工作流状态

## 元信息
- **版本**: 1
- **创建时间**: 2026-05-18T10:00:00+08:00
- **最后更新**: 2026-05-18T10:30:00+08:00

## 工作流进度

### 阶段完成情况

| 阶段 | 状态 | 完成时间 |
|------|------|---------|
| setup | ✅ 完成 | 2026-05-18T10:00:00+08:00 |
| propose | 🔄 进行中 | 2026-05-18T10:15:00+08:00 |
| plan | ⏳ 未开始 | — |
| execute | ⏳ 未开始 | — |
| status_archive | ⏳ 未开始 | — |
| cleanup | ⏳ 未开始 | — |

## 当前状态

- **当前阶段**: propose
- **当前恢复点**: propose.scan_done

### Changes（支持多 change 并行）

| 变更名称 | Worktree | Artifacts | 执行状态 | 当前操作 |
|----------|----------|-----------|---------|---------|
| fix-ns-pollution | .zcf/fix-ns-pollution-wt | ✅ 已提交 | ⏳ 等待 | — |
| add-stream-pipes | — | ⏳ 未提交 | ⏳ 等待 | — |

### 恢复上下文

- **恢复点**: propose.scan_done
- **最后操作**: 扫描建议完成，等待用户选择
- **验证建议**:
  - [x] openspec CLI 可用
  - [x] git 工作区正常
  - [ ] propose artifacts 已创建（如需要）

- **活跃 Changes**: [fix-ns-pollution, add-stream-pipes]
- **当前焦点变更**: fix-ns-pollution
- **Worktree 映射**:
  - fix-ns-pollution → .zcf/fix-ns-pollution-wt (openspec/fix-ns-pollution)
  - add-stream-pipes → (未创建)

## 操作历史

| 时间 | 阶段 | 操作 | 结果 |
|------|------|------|------|
| 2026-05-18T10:00:00+08:00 | setup | env_check | ok |
| 2026-05-18T10:15:00+08:00 | propose | select_change | fix-ns-pollution |
```

---

### workflow-progress.md 格式

```markdown
# OpenSpec 工作流进度日志

## Session 信息
- **开始时间**: 2026-05-18T10:00:00+08:00
- **结束时间**: —
- **活跃 Changes**: fix-ns-pollution, add-stream-pipes

## 操作日志
```

---

## 错误处理

| 错误场景 | 检测方式 | 修复指引 |
|----------|----------|----------|
| 未 commit 就 plan | `git status --porcelain` + `git show HEAD:` 失败 | 提示先 commit artifacts |
| artifacts 有未提交修改 | `git status --porcelain openspec/changes/<name>/` 非空 | 提示先 commit 再 plan |
| worktree 目录冲突 | `-d .zcf/<name>-wt` 但 `git worktree list` 未注册 | 提示 `rm -rf .zcf/<name>-wt` |
| tasks.md 不同步 | tasks.md 进度与 state 不一致 | Guide 入口时自动从 tasks.md 同步 |
| worktree 分支冲突 | `git worktree add` 失败 | 提供 `git worktree list` 查看现有 |
| 未 plan 就 status | `.sisyphus/plans/<name>.md` 不存在 | 提示先执行 plan |
| execute 不在 worktree 内 | `git branch --show-current` 非 `openspec/` | 提示先进入 worktree 或使用分离执行 |

---

## 技能注册表

| Skill | 用途 | 触发方式 |
|-------|------|---------|
| `spec-workflow-guide` | 推荐器入口（扫描状态，建议调 spec 或 ship） | `skill_use("spec-workflow-guide")` |
| `spec-workflow-guide-spec` | Spec 端状态机（setup → roadmap → propose → deps） | `skill_use("spec-workflow-guide-spec")` |
| `spec-workflow-guide-ship` | Ship 端状态机（discover → worktree → plan → execute → archive） | `skill_use("spec-workflow-guide-ship")` |
| `spec-workflow-propose` | 扫描 ADR/代码生成建议列表 | 被 guide-spec 调用，或单独使用 |
| `spec-workflow-execute` | 在 worktree 内执行任务 | 被 guide-ship 调用，或在 worktree 内单独使用 |
| `spec-workflow-status` | 状态查看/归档 | 被 guide-ship 调用，或单独使用 |

---

## 关键约束提醒

1. **COMMIT GATE**：worktree 创建前必须 commit，否则 `git worktree add` 看不到 artifacts
2. **Branch 检查**：`git branch --show-current` 必须是 `main` 或 `master` 才能创建 worktree
3. **不同步处理**：用 `awk index()` 直接修改 tasks.md，不重新 run plan（会覆盖 `.sisyphus/plans/`）
4. **Execute 只写 tasks.md**：不写 state.md，由 guide 从 tasks.md 同步进度
5. **任何时候可返回 Plan**：Execute 菜单有「返回 Plan 阶段」选项，可添加更多 worktree
