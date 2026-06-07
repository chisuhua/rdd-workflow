---
name: prometheus-planning
description: 在 opencode 环境内为 OpenSpec change 生成实施计划(.sisyphus/plans/<name>.md)。优先调用 oh-my-opencode 内置 Prometheus(plan)子代理;不可用时回退到 superpowers/writing-plans 技能;都不可用时报错并给出明确安装指引。被 guide-ship 在 Phase 1 plan 阶段调用。
license: MIT
compatibility: Requires opencode 1.0+, git 2.25+, openspec CLI 1.3.1+. Optional: oh-my-opencode 1.0+ (preferred) or superpowers/writing-plans 1.0+ (fallback).
metadata:
  author: sisyphus
  version: "1.0"
  evolved-from: "extracted from guide-ship.md:213-242 (P0-6 dependency rewrite)"
  user-invocable: false
  replaces: "prometheus-start-work (deprecated)"
---

# Prometheus Planning — 实施计划生成器

本技能是 `guide-ship` Phase 1 的**计划生成子模块**。它解决历史痛点:
`prometheus-start-work` 是外部黑盒依赖,未声明、未自检、失败时无清晰引导(P0-6)。

新设计: **三级回退链** + **配置文件探测 + 试调双重验证**。

## 职责边界

- **拥有**: `.sisyphus/plans/<name>.md` 的生成路径选择与契约验证
- **不拥有**: 计划内容本身(由子代理/writing-plans 决定)、`tasks.md` 更新、worktree 创建
- **被谁调用**: `guide-ship` Phase 1 末尾(Worktree 创建完成 → 进入执行模式选择之前)

## 调用契约

```
skill_use("prometheus-planning")   # 无参数,依赖 git context 自动获取 CHANGE_NAME / WT_PATH
```

不暴露参数。`CHANGE_NAME` 和 `WT_PATH` 由调用方 `guide-ship` 通过 `cd` 到 worktree 后,从 `openspec/changes/<name>/` 目录名自动推导。

---

## 执行流程(AI 按顺序执行)

### Step 1: 检测 Prometheus 可用性

```bash
# === Detection: 三级回退链探针 ===
PROMETHEUS_MODE=""

# === 路径 A: 内置 Prometheus (oh-my-opencode) — 配置文件探测 ===
# 1a. 检查 opencode 全局配置中的 plugin 声明
if [ -f "$HOME/.config/opencode/opencode.json" ] && \
   grep -qE '"oh-my-opencode"|"oh-my-openagent"' "$HOME/.config/opencode/opencode.json" 2>/dev/null; then
    PROMETHEUS_MODE="builtin-candidate"
fi

# 1b. 检查常见安装位置
if [ -z "$PROMETHEUS_MODE" ]; then
    for marker in \
        "$HOME/.config/opencode/oh-my-opencode" \
        "$HOME/.config/opencode/oh-my-openagent" \
        "$HOME/.opencode/oh-my-opencode" \
        "$HOME/.opencode/oh-my-openagent"; do
        if [ -e "$marker" ]; then
            PROMETHEUS_MODE="builtin-candidate"
            break
        fi
    done
fi

# 1c. 检查显式环境变量(AI session 启动时若检测到插件会设置)
if [ -z "$PROMETHEUS_MODE" ] && [ -n "${OH_MY_OPENCODE_ENABLED:-}" ]; then
    PROMETHEUS_MODE="builtin-candidate"
fi

# === 路径 A 验证: 试调 plan 子代理 (AI 必做的最后一步) ===
# 若 PROMETHEUS_MODE == "builtin-candidate",AI 必须执行:
#   task(subagent_type="plan", prompt="ping", run_in_background=false, load_skills=[])
# 若返回 "Plan agent not found" 或类似错误,降级为 "external"。

# === 路径 B: 外部回退 — superpowers/writing-plans 技能 ===
# 检查 superpowers/writing-plans 技能文件是否存在
# 1a. 全局 skills 目录
if [ -z "$PROMETHEUS_MODE" ]; then
    for sp_dir in \
        "$HOME/.config/opencode/skills/superpowers/writing-plans" \
        "$HOME/.agents/skills/superpowers/writing-plans" \
        "$HOME/.opencode/skills/superpowers/writing-plans"; do
        if [ -f "$sp_dir/SKILL.md" ]; then
            PROMETHEUS_MODE="external"
            WRITING_PLANS_PATH="$sp_dir"
            break
        fi
    done
fi

# 1b. 项目本地 skills 目录
if [ -z "$PROMETHEUS_MODE" ]; then
    for sp_dir in \
        ".opencode/skills/superpowers/writing-plans" \
        ".agents/skills/superpowers/writing-plans"; do
        if [ -f "$sp_dir/SKILL.md" ]; then
            PROMETHEUS_MODE="external"
            WRITING_PLANS_PATH="$sp_dir"
            break
        fi
    done
fi

# === 路径 C: 全部不可用 — 报错 ===
if [ -z "$PROMETHEUS_MODE" ]; then
    PROMETHEUS_MODE="none"
fi

echo "🔍 Prometheus 模式: $PROMETHEUS_MODE"
```

### Step 2: 按检测结果分支执行

#### 分支 A: `builtin` (内置 Prometheus 可用)

AI 必须在 worktree 内调用:

```python
task(
    subagent_type="plan",
    run_in_background=false,
    load_skills=["superpowers/writing-plans"],
    prompt=f"""为以下 OpenSpec change 生成详细实施计划:

## Change 上下文
- Change 名称: {CHANGE_NAME}
- Worktree 路径: $(pwd)
- Proposal: openspec/changes/{CHANGE_NAME}/proposal.md
- Design:   openspec/changes/{CHANGE_NAME}/design.md
- Tasks:    openspec/changes/{CHANGE_NAME}/tasks.md

## 输出要求
1. 计划文件必须写入: .sisyphus/plans/{CHANGE_NAME}.md
2. 任务格式严格遵循 superpowers/writing-plans 的 plan 格式(checkbox / WHERE-WHY-HOW-EXPECTED)
3. 不需要 git commit,plan 阶段只生成文件
4. 完成后报告: 文件路径 + 顶层任务数 (grep -c '^- \\[' 的结果)
""",
)
```

#### 分支 B: `external` (回退到 superpowers/writing-plans)

```bash
echo "⚠️  未检测到内置 Prometheus(oh-my-opencode),回退到 superpowers/writing-plans"

# AI 必须执行:
#   skill_use("superpowers/writing-plans")
# 然后按该技能的指示,在 worktree 内生成 .sisyphus/plans/<name>.md
#
# 注: superpowers/writing-plans 本身是 opencode 内置 superpowers 套件的成员技能,
#     不需要单独安装;只需调用 skill_use()。
```

#### 分支 C: `none` (全部不可用 — 明确错误)

```bash
cat << 'EOF'
❌ 必需依赖全部缺失:无任何可用的实施计划生成器

请选择一种修复方式(任选其一):

方式 1 — 安装 oh-my-opencode (推荐,内置 Prometheus 计划子代理):
    npm install -g oh-my-opencode
    # 或从源码: https://github.com/code-yeongyu/oh-my-opencode

方式 2 — 确认 superpowers 套件已加载:
    检查 ~/.config/opencode/opencode.json 是否包含 superpowers 插件。
    该套件提供 writing-plans 技能作为回退路径。

方式 3 — 临时绕过 (跳过 .sisyphus/plans/<name>.md 生成):
    export SKIP_PROMETHEUS_PLANNING=yes
    # ⚠️  不推荐:execute.md 依赖此文件,跳过会导致后续 execute 阶段无详细计划可读

详细文档: README.md "前置条件" 小节
EOF
exit 1
```

### Step 3: 契约验证(无论走哪条路径,统一断言)

```bash
# === 契约验证: 任何路径都必须产出 .sisyphus/plans/<name>.md ===
if [ ! -f ".sisyphus/plans/$CHANGE_NAME.md" ]; then
    echo "❌ 计划文件未生成: .sisyphus/plans/$CHANGE_NAME.md"
    echo "   Prometheus 模式: $PROMETHEUS_MODE"
    echo "   请检查上述模式的错误输出"
    exit 1
fi

PLAN_TASK_COUNT=$(grep -c '^- \[' ".sisyphus/plans/$CHANGE_NAME.md" 2>/dev/null || echo 0)
if [ "$PLAN_TASK_COUNT" -eq 0 ]; then
    echo "❌ 计划文件存在但无任务项 (grep '^- \\[' 返回 0)"
    echo "   文件路径: .sisyphus/plans/$CHANGE_NAME.md"
    echo "   Prometheus 模式: $PROMETHEUS_MODE"
    exit 1
fi

echo "✅ 实施计划已生成: $PLAN_TASK_COUNT 顶层任务 (模式: $PROMETHEUS_MODE)"
```

---

## 输出格式(供 `guide-ship` 消费)

成功时(Step 3 之后):

```
✅ Prometheus 计划已生成: <N> 任务 (模式: builtin | external)
   计划文件: .sisyphus/plans/<name>.md
```

失败时(分支 C 或 Step 3 失败): 退出码非零,stderr 含上述 ❌ 块。

## 与历史契约的差异

| 维度 | 旧 `prometheus-start-work` | 新 `prometheus-planning` |
|---|---|---|
| 来源 | 外部 GitHub 仓库 (黑盒) | 自包含 + 内置优先 + 外部回退 |
| 声明位置 | `engines.prometheus-start-work` (未在 skills[]) | `skills[]` 数组条目 + 可选回退 |
| 失败引导 | "请确认技能已安装" (P0-6 缺陷) | 三级回退,每级都有可执行命令 |
| 可观察性 | 不可观测子代理 | builtin 路径可看 prompt/响应 |
| 锁定 OpenSpec 兼容 | 仅外部 | 内置路径 + writing-plans + skip-env |

## 元信息

| 字段 | 值 |
|------|-----|
| 取代 | `prometheus-start-work` (deprecated, 仍可作为最后回退保留在 `engines.optionalDependencies` 提示) |
| 被取代方语义 | 任何对 `prometheus-start-work` 的引用应迁移到本技能 |
| 测试覆盖 | `tests/integration/test_prometheus_planning.bats` (新增) |
| 审计追踪 | 解决 P0-6(`docs/audit/2026-06-05-workflow-audit.md:568-605`) |
