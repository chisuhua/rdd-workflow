---
name: guide-ship
description: Ship-side state machine for OpenSpec workflow — guides user from committed changes through worktree creation, Prometheus plan generation, execution, archive, and cleanup. Owns git worktrees and tasks.md progress. Called by user when starting work on a committed change.
license: MIT
compatibility: Requires openspec CLI v1.3.1+, git 2.25+, Prometheus start_work skill
metadata:
  author: sisyphus
  version: "1.0"  # P0: Ship-side state machine, split from guide + plan
  generatedBy: "3.0"
  user-invocable: true
---

# OpenSpec 工作流 — Ship-Side Guide

本技能是 OpenSpec 工作流的 **ship 端状态机**：负责在 git 提交 OpenSpec change artifacts 之后的所有工作——为已提交的 change 创建 worktree、生成 Prometheus 实施计划、监控执行、归档清理。spec 端（`guide-spec`）在 artifacts 提交后发出 "ready for guide-ship" 交接信号，本技能接管从 worktree 到归档的全流程。

**职责边界**：
- **拥有**：git worktree、`.sisyphus/plans/<name>.md`、归档（merge → archive → cleanup）
- **不拥有**：`openspec/changes/<name>/{proposal,design,tasks}.md` 的创建与提交（这些由 `guide-spec` 处理）
- **状态持久化**：不写状态文件；ship 端状态由 git worktree 列表和 `tasks.md` 进度反映（on-the-fly 读取）

**调用方式**：

```
skill_use("guide-ship")   # 无参数版本
```

---

## Phase 1: plan — Commit + Worktree + 计划

**入口条件**：spec 端已完成且 `openspec/changes/<name>/{proposal,design,tasks}.md` 已 git 提交（可用 `git show HEAD:<path>` 验证）。

**前置说明**：

每个 change 独立经历 plan→execute→archive。用户选择要处理的 change 后，为其创建 worktree 并生成计划。

**行为**：

1. 展示所有活跃 changes 的状态列表
2. 用户选择要处理的 change（或选「全部创建 worktree」）
3. 对选中的 change 执行 COMMIT GATE
4. 创建 branch + worktree
5. 在 worktree 内生成 Prometheus 计划

**展示所有活跃 changes 的状态**：

```bash
# Reconstruct ACTIVE_CHANGES from filesystem (was in spec-side before refactor)
ACTIVE_CHANGES=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | xargs -n1 basename 2>/dev/null | tr '\n' ' ')

echo "📋 所有活跃 Changes:"
echo ""
echo "| 变更 | Artifacts | Worktree | 计划文件 |"
echo "|-----|-----------|----------|---------|"
# git show HEAD:<path> 要求相对于 repo root 的相对路径。
# 把整个表格生成放在 (cd ... && ...) 子 shell 里,这样 git show 可以用相对路径。
(cd "$PROJECT_ROOT" 2>/dev/null && for name in $ACTIVE_CHANGES; do
    committed=$(git show HEAD:"openspec/changes/$name/.openspec.yaml" > /dev/null 2>&1 && echo "✅" || echo "⏳")
    wt_path="$PROJECT_ROOT/.zcf/${name}-wt"
    wt_exists=$([ -d "$wt_path" ] && git worktree list | grep -q "$wt_path" && echo "✅" || echo "❌")
    plan_exists=$([ -f "$wt_path/.sisyphus/plans/$name.md" ] 2>/dev/null && echo "✅" || echo "❌")
    echo "| $name | $committed | $wt_exists | $plan_exists |"
done)
```

**选择要处理的 change**：

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
4. 🔄 切换当前焦点变更（选择另一个变更作为焦点）
0. 退出（worktree 保留，下次 skill_use("guide-ship") 可继续）
i. 其他输入
```

**选项 1/2 执行内容**（以 fix-ns-pollution 为例）：

```bash
CHANGE_NAME="fix-ns-pollution"

# COMMIT GATE - 脏检测
if [ -n "$(git status --porcelain "$PROJECT_ROOT/openspec/changes/$CHANGE_NAME/")" ]; then
    echo "⚠️  检测到未提交的修改，提示用户提交或放弃"
fi

# COMMIT GATE - 是否已 commit
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    # git show HEAD:<path> 要求相对于 repo root 的相对路径,所以包一层 (cd ... && ...)。
    if ! (cd "$PROJECT_ROOT" 2>/dev/null && git show HEAD:"openspec/changes/$CHANGE_NAME/.openspec.yaml" > /dev/null 2>&1); then
        echo "❌ Artifacts 尚未提交，请先提交"
        # 回到菜单
    fi
else
    echo "❌ 当前仓库没有任何提交（HEAD 不存在）"
    echo "请先 git commit 一些文件后再执行 plan"
    exit 1
fi

# 创建 branch（如不存在）
if ! git branch --list "openspec/$CHANGE_NAME" | grep -q "openspec/$CHANGE_NAME"; then
    git branch "openspec/$CHANGE_NAME" HEAD
fi

# 创建 worktree（带目录冲突检测）
if [ -d "$PROJECT_ROOT/.zcf/${CHANGE_NAME}-wt" ]; then
    if git worktree list | grep -q "$PROJECT_ROOT/.zcf/${CHANGE_NAME}-wt"; then
        echo "⚠️  Worktree 已存在"
    else
        echo "❌ 目录冲突，请先清理: rm -rf \"$PROJECT_ROOT/.zcf/${CHANGE_NAME}-wt\""
    fi
else
    git worktree add "$PROJECT_ROOT/.zcf/${CHANGE_NAME}-wt" "openspec/$CHANGE_NAME"
fi

# ============================================================
# WORKTREE VERIFICATION GATE (P0 FIX)
# 验证 worktree 是否正确关联到分支，防止 detached HEAD 问题
# ============================================================
WT_PATH="$PROJECT_ROOT/.zcf/${CHANGE_NAME}-wt"
WT_BRANCH=$(git worktree list --porcelain | awk -v path="$WT_PATH" '
    $1 == "worktree" && $2 == path { found=1; next }
    found && $1 == "branch" { print $2; exit }
    found && $1 == "detached" { print "DETACHED"; exit }
')

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Worktree 验证"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Worktree 路径: $WT_PATH"
echo "  分支状态: ${WT_BRANCH:-未找到}"

if [ "$WT_BRANCH" = "DETACHED" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "❌ 错误：Worktree 处于 detached HEAD 状态！"
    echo ""
    echo "  这通常意味着 worktree 分支创建失败。"
    echo "  新提交的代码将无法被 main 分支 merge。"
    echo ""
    echo "  请执行以下命令修复："
    echo "    cd $WT_PATH"
    echo "    git checkout openspec/$CHANGE_NAME"
    echo ""
    echo "  或删除 worktree 重新创建："
    echo "    git worktree remove $WT_PATH"
    echo "    git branch -D openspec/$CHANGE_NAME"
    echo "    skill_use(\"guide-ship\")  # 重新进入 Plan 阶段"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
elif [ -z "$WT_BRANCH" ]; then
    echo "⚠️  警告：无法确定 worktree 分支状态"
fi

# 验证 worktree 分支是否指向 change 分支
EXPECTED_BRANCH="refs/heads/openspec/$CHANGE_NAME"
if [ "$WT_BRANCH" != "$EXPECTED_BRANCH" ] && [ "$WT_BRANCH" != "openspec/$CHANGE_NAME" ]; then
    echo "⚠️  警告：Worktree 分支 $WT_BRANCH 与预期不符"
fi

echo "✅ Worktree 验证通过"
```

```bash
# === Prometheus start_work invocation ===
# Generate detailed implementation plan via Prometheus
cd "$WT_PATH" || { echo "❌ 进入 worktree 失败: $WT_PATH"; exit 1; }

if skill_use("prometheus-start-work") 2>/dev/null; then
    if [ ! -f ".sisyphus/plans/$CHANGE_NAME.md" ]; then
        echo "❌ Prometheus start_work 未生成计划文件"
        exit 1
    fi
    PLAN_TASK_COUNT=$(grep -c '^- \[' ".sisyphus/plans/$CHANGE_NAME.md" 2>/dev/null || echo 0)
    if [ "$PLAN_TASK_COUNT" -eq 0 ]; then
        echo "❌ 计划文件存在但无任务项"
        exit 1
    fi
    echo "✅ Prometheus 计划已生成: $PLAN_TASK_COUNT 任务"
else
    echo "❌ Prometheus start_work 调用失败"
    echo "   请确认 prometheus-start-work 技能已安装"
    exit 1
fi
```

**Worktree 创建完成 → 进入执行模式选择**：

```
${CHANGE_NAME} worktree 已就绪，请选择执行方式：

📋 ${CHANGE_NAME} 状态:
  Worktree: .zcf/${CHANGE_NAME}-wt
  计划文件: .sisyphus/plans/${CHANGE_NAME}.md
  任务数: $(grep -c '^- \[' "$wt/openspec/changes/$name/tasks.md" 2>/dev/null || echo '?')

请选择执行方式:
1. 🔒 在此 session 执行（阻塞）— 等待任务完成后返回
2. 🔓 分离执行（新终端）— 给出操作指引，立即返回
0. 退出（worktree 保留，下次 skill_use("guide-ship") 可继续）
i. 其他输入
```

**选项 1（阻塞执行）执行内容**：

```bash
cd "$PROJECT_ROOT/.zcf/${CHANGE_NAME}-wt" || exit 1
skill_use("execute")
cd "$PROJECT_ROOT" || exit 1
# execute 会阻塞直到所有任务完成
```

**选项 2（分离执行）输出指引**：

```bash
echo ""
echo "🔓 分离执行指引"
echo ""
echo "为 ${CHANGE_NAME} 启动分离执行："
echo ""
echo "1. 在新终端中执行："
echo "   cd $(pwd)/\"$PROJECT_ROOT/.zcf/${CHANGE_NAME}-wt\""
echo "   skill_use(\"execute\")"
echo ""
echo "2. execute 结果会自动写入 tasks.md"
echo ""
echo "3. 完成后，在此 session 运行 guide-ship 查看最新进度"
echo ""
echo "当前状态：${CHANGE_NAME} 等待分离执行"
```

**返回 Plan 前的检查 — 是否进入监控**：

```bash
# 检查所有已创建 worktree 的数量
WORKTREE_COUNT=$(git worktree list | grep -c "openspec/" || true)

if [ "$WORKTREE_COUNT" -gt 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 发现 $WORKTREE_COUNT 个 worktree 已就绪"
    echo ""
    echo "请选择:"
    echo "1. ✅ 进入 Execute 监控模式（实时监控所有 worktree 进度）"
    echo "2. 🔄 继续返回 Plan 阶段（创建更多 worktree 或处理其他 change）"
    echo "i. 其他输入"
fi
```

---

## Phase 2: execute — 监控与执行

**定位**：Execute 阶段是**监控模式**——读取 tasks.md 进度、显示所有 worktree 状态、提供执行入口。不是实际执行者。

**前置检测（每次入口执行）**：

```bash
# 读取所有 tasks.md 的实际进度
echo "📋 所有 Worktrees 实际进度:"

LAST_CHECK=$(date "+%Y-%m-%d %H:%M:%S")

mapfile -t wt_list < <(git worktree list --porcelain | awk '/^worktree / {path=$2} /^branch refs\/heads\/openspec\// {print path}')
for wt in "${wt_list[@]}"; do
    branch=$(git worktree list | grep -F "$wt" | awk '{print $3}')
    name=$(echo "$branch" | sed 's|openspec/||')
    # P0 FIX: tasks.md 在 worktree 内的 openspec/changes/<name>/ 目录下
    # wt 已经是完整路径，不需要再拼接 PROJECT_ROOT
    tasks_file="$wt/openspec/changes/$name/tasks.md"

    if [ -f "$tasks_file" ]; then
        # P1 FIX: 正确统计 tasks.md 中所有 - [ ] 任务项（不分章节）
        total=$(grep -c '^- \[' "$tasks_file" 2>/dev/null || echo 0)
        done=$(grep -c '^- \[x\]' "$tasks_file" 2>/dev/null || echo 0)
        progress="${done}/${total}"
    else
        progress="? (文件不存在)"
    fi
    echo "  $name → $progress"
done

echo ""
echo "上次检测: $LAST_CHECK"
```

**菜单选项**：

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
0. 退出（下次 skill_use("guide-ship") 继续）
i. 其他输入
```

**选项 7（刷新进度）执行内容**：

```bash
# 重新读取所有 tasks.md 进度
echo "🔄 正在刷新进度..."
LAST_CHECK=$(date "+%Y-%m-%d %H:%M:%S")
# 重新显示表格
# 用户选择后继续循环
```

**选项 1/3（阻塞执行）执行内容**：

```bash
CHANGE_NAME="fix-ns-pollution"
WORKTREE_PATH="$PROJECT_ROOT/.zcf/${CHANGE_NAME}-wt"

cd "$WORKTREE_PATH" || { echo "❌ 无法进入 worktree 目录: $WORKTREE_PATH"; exit 1; }
skill_use("execute")
# 阻塞等待所有任务完成
cd "$(git rev-parse --show-toplevel)"
```

**选项 2/4（分离执行）输出指引**：

```bash
echo ""
echo "🔓 分离执行指引"
echo ""
echo "为 ${CHANGE_NAME} 启动分离执行："
echo ""
echo "1. 在新终端中执行："
echo "   cd $(pwd)/\"$PROJECT_ROOT/.zcf/${CHANGE_NAME}-wt\""
echo "   skill_use(\"execute\")"
echo ""
echo "2. execute 结果会自动写入 tasks.md"
echo ""
echo "3. 完成后，在此 session 运行 guide-ship 查看最新进度"
echo ""
echo "当前状态：${CHANGE_NAME} 🔓 分离执行中"
```

**状态更新**：将执行状态设为 🔓，下次入口时通过 tasks.md 同步实际进度。

**监控说明**：

- Guide-ship 不执行任务，只监控
- 进度来自 tasks.md 的 `grep -c "^- \[x\]"`
- 执行状态列说明：
  - 🔒 执行中 — 此 session 正在阻塞执行
  - 🔓 分离执行 — 在新终端执行，不阻塞
  - ⏳ 等待 — 未开始
  - ✅ 完成 — 所有任务完成

---

## Phase 3: archive — 状态检查与归档

**入口条件**：execute 已完成（所有 worktree 的任务都完成），或用户主动选择此阶段。

**前置说明**：

每个 change 独立归档。可以一次性归档所有已完成的 change，或逐个处理。

**展示所有 change 状态**：

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

**归档流程（选项 1/2）**：

```bash
# 对选定的 change 执行归档
CHANGE_NAME="fix-ns-pollution"
WT_PATH="$PROJECT_ROOT/.zcf/${CHANGE_NAME}-wt"

# ============================================================
# MERGE VERIFICATION GATE (P0 FIX)
# 在 merge 前验证 worktree 分支是否包含新提交
# ============================================================
echo "🔍 验证 worktree 分支状态..."

# 检查 worktree 是否关联到正确分支（防止 detached HEAD）
WT_BRANCH=$(git worktree list --porcelain | awk -v path="$WT_PATH" '
    $1 == "worktree" && $2 == path { found=1; next }
    found && $1 == "branch" { print $2; exit }
    found && $1 == "detached" { print "DETACHED"; exit }
')

if [ "$WT_BRANCH" = "DETACHED" ]; then
    echo "❌ 错误：Worktree 处于 detached HEAD，无法 merge"
    echo "   请先切换到正确分支："
    echo "   cd $WT_PATH && git checkout openspec/$CHANGE_NAME"
    exit 1
fi

# 获取 merge 前 main 的最新 commit
BEFORE_MERGE=$(git rev-parse HEAD)

# 1. merge worktree → main
cd "$WT_PATH" || exit 1
git checkout main || { echo "❌ 切换 main 分支失败"; exit 1; }

DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@.*/@@' || git rev-parse --abbrev-ref HEAD)
MERGE_BASE=$(git merge-base "openspec/$CHANGE_NAME" "$DEFAULT_BRANCH" 2>/dev/null)
MAIN_TIP=$(git rev-parse "$DEFAULT_BRANCH" 2>/dev/null)
if [ "$MERGE_BASE" = "$MAIN_TIP" ]; then
    git merge --ff-only "openspec/$CHANGE_NAME" || { echo "❌ merge 失败"; exit 1; }
else
    echo "⚠️ Worktree 分支已落后于 $DEFAULT_BRANCH，创建 merge commit"
    git merge --no-ff "openspec/$CHANGE_NAME" -m "merge: $CHANGE_NAME change" || { echo "❌ merge 失败"; exit 1; }
fi

cd "$PROJECT_ROOT" || exit 1

# ============================================================
# POST-MERGE VERIFICATION GATE (P0 FIX)
# 验证 merge 是否真正产生了变更
# ============================================================
AFTER_MERGE=$(git rev-parse HEAD)

if [ "$BEFORE_MERGE" = "$AFTER_MERGE" ]; then
    # 进一步检查：分支是否包含 main 没有的提交
    if git merge-base --is-ancestor "openspec/$CHANGE_NAME" HEAD; then
        echo "⚠️  merge 完成但无新 commit（change 分支已是 HEAD 的祖先）"
    else
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "❌ Merge 验证失败！"
        echo ""
        echo "  可能原因："
        echo "  1. worktree 分支没有新提交"
        echo "  2. 新提交没有在预期文件中"
        echo ""
        echo "  请检查："
        echo "  - worktree 分支历史："
        echo "    git log openspec/$CHANGE_NAME --oneline -5"
        echo "  - worktree 新文件是否在分支上："
        echo "    git ls-tree --name-only openspec/$CHANGE_NAME | grep -E 'topology|parser'"
        echo ""
        echo "  诊断："
        echo "    git log openspec/$CHANGE_NAME --stat --name-only | head -30"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        exit 1
    fi
fi

# 2. archive
openspec archive "$CHANGE_NAME" --yes

# 3. cleanup
git worktree remove "$PROJECT_ROOT/.zcf/${CHANGE_NAME}-wt"
if git branch -d "openspec/$CHANGE_NAME" 2>/dev/null; then
    echo "✅ Branch 已删除: openspec/$CHANGE_NAME"
else
    echo "⚠️  Branch 有未合并的提交，强制删除"
    git branch -D "openspec/$CHANGE_NAME"
fi

cd "$PROJECT_ROOT" || exit 1

echo "✅ $CHANGE_NAME 已归档"

# ============================================================
# P0 FIX: 归档后检查是否还有其他 change 需要处理
# ============================================================
# 使用 awk 检查分支名（第三列，git worktree list 输出: <path> <commit> <branch>）而非路径，避免路径含 openspec/ 的误匹配
REMAINING_WT=$(git worktree list | awk '$3 ~ /^openspec\// {print $1}' | grep -c . || true)
if [ "$REMAINING_WT" -gt 0 ]; then
    echo ""
    echo "📋 还有 $REMAINING_WT 个 worktree 正在进行"
    echo ""
    echo "请选择:"
    echo "1. 继续处理其他 worktree（进入 Execute 阶段）"
    echo "2. 返回 Plan 阶段（为其他 change 创建 worktree）"
    echo "i. 其他输入"
else
    # 没有更多 worktree,本批次 ship 端工作完成
    echo ""
    echo "📋 所有 worktree 已处理完毕"
    echo ""
    echo "请选择:"
    echo "1. 进入 cleanup 阶段"
    echo "2. 完成 workflow（进入 ship-done）"
    echo "i. 其他输入"
fi
```

---

## Phase 4: cleanup — 测试清理

**入口条件**：所有活跃 changes 均已归档后，或用户主动选择。

**菜单选项**：

```
清理选项

📋 Worktrees: (列出所有剩余 worktree)
📋 Branches: (列出所有 openspec/* branches)

请选择:
1. 🧹 清理指定 worktree + branch
2. 🗑️ 清理所有 worktree + openspec/* branches
3. 📝 输出测试总结报告（所有 changes 的执行记录）
4. ↩️ 返回上一阶段
i. 其他输入
```

**选项 1 执行**：

```
请选择要清理的 worktree:
1. fix-ns-pollution (.zcf/fix-ns-pollution-wt)
2. add-stream-pipes (.zcf/add-stream-pipes-wt)
```

**选项 2 执行**：

```bash
# 清理所有 worktree
mapfile -t wt_list < <(git worktree list --porcelain | awk '/^worktree / {path=$2} /^branch refs\/heads\/openspec\// {print path}')
for wt in "${wt_list[@]}"; do
    git worktree remove "$wt" 2>/dev/null || true
done

# 清理所有 openspec/* branches
git branch | grep "openspec/" | while read branch; do
    if git branch -d "$branch" 2>/dev/null; then
        :
    else
        echo "⚠️  Branch $branch 有未合并的提交，强制删除"
        git branch -D "$branch" 2>/dev/null || true
    fi
done

echo "✅ 所有 worktree 和 openspec/* branches 已清理"
```

---

## Phase 5: ship-done (Exit)

Triggered when all committed changes have been archived (or no changes remain).

**Loop check:**

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# Count remaining unprocessed changes
REMAINING=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l)
REMAINING_WT=$(git worktree list 2>/dev/null | awk '$3 ~ /^openspec\// {print $1}' | wc -l)

if [ "$REMAINING_WT" -gt 0 ] || [ "$REMAINING" -gt 0 ]; then
    echo "📋 还有 $REMAINING_WT 个 worktree 在跑,$REMAINING 个未处理 change"
    echo ""
    echo "请选择:"
    echo "1. 继续处理 (skill_use(\"guide-ship\"))"
    echo "2. 退出 (稍后手动继续)"
    echo "i. 其他输入"
else
    echo "✅ 所有 changes 已处理完毕"
    echo ""
    echo "请选择:"
    echo "1. 回到 spec 端 (skill_use(\"guide-spec\")) — 创建更多 changes"
    echo "2. 完成 (本批次结束)"
    echo "i. 其他输入"
fi
```
