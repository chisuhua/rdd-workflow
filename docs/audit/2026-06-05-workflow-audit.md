# rdd-workflow 流程审计报告

| 字段 | 值 |
|------|-----|
| **审计日期** | 2026-06-05 |
| **审计范围** | `/home/ubuntu/.agents/skills/rdd-workflow` 全仓库 |
| **审计者** | Sisyphus (MiniMax-M3) |
| **审计模式** | 只读,基于"docs 已清空"的全新起点 |
| **审计对象** | 9 个 skill 文件 + 元数据 + 安装/分发/状态文件 |
| **前置说明** | docs/ 下历史文档已由用户清理,本次审计不参考任何历史设计文档,完全基于当前代码 + README + USAGE |

---

## 0. 执行摘要

### 0.1 严重度概览

| 严重度 | 数量 | 含义 |
|--------|------|------|
| 🔴 P0 阻塞性 | **9** | 阻断流程或产生静默错误数据,必须立即修复 |
| 🟡 P1 重要 | **14** | 路径错误、契约违反、状态机歧义,本迭代修复 |
| 🟢 P2 改进 | **10** | 一致性、可维护性、文档化,下迭代处理 |
| ℹ️ P3 观察 | **5** | 工具/环境假设、未来扩展,观察项 |
| **合计** | **38** | 跨 9 个 skill 文件 |

### 0.2 三大最严重问题(速览)

1. **`prometheus-start-work` 是未声明的必需依赖** — 整个 ship 端唯一能生成实施计划文件 `.rddf/plans/<name>.md` 的途径;失败时 `guide-ship` 直接 `exit 1`;`package.json:17`、README、USAGE、INSTALL 全部未提及。

2. **`git worktree list` 字段索引 BUG 横跨 2 个 skill** — `status.md` 三处、`execute.md` 三处把 `$2`(commit hash)当作 branch 字段,导致 worktree 永远找不到;`execute.md:411` 文档表把错误模式列为"推荐解"。

3. **分离执行(🔓 detached)模式下 roadmap 进度永远不更新** — `execute.md` 在 worktree 内执行时,`PROJECT_ROOT=$(git rev-parse --show-toplevel)` 返回 worktree 自己的根,`.rddf/state/roadmap-state.json` 被写入 worktree 内 `.rddf/state/`,主 session 完全看不到。

### 0.3 修复工作量估算

- P0 修复:约 5-6 小时
- P1 修复:约 12-13 小时
- P0 + P1 合计:约 17-19 小时(可分 2-3 个迭代)

---

## 1. 流程全景图

### 1.1 阶段拓扑(基于当前代码 + README + USAGE 整合)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Phase 0  INSTALL        全局安装(唯一入口)                              │
│            ↓ 复制 skills/ → .opencode/skills/rdd-workflow/skills/        │
├──────────────────────────────────────────────────────────────────────────┤
│  Phase 0.5  guide        无状态推荐器(扫描后推荐下一步)                    │
│            ↓ 推荐 guide-spec 或 guide-ship                              │
├──────────────────────────────────────────────────────────────────────────┤
│  SPEC 端  (guide-spec)                                                     │
│  Phase 1   setup         环境检查(检测 openspec/git/worktree/build)       │
│  Phase 1.5 roadmap        roadmap 初始化(若无则自动调 roadmap init)       │
│  Phase 2   propose       扫描 ADR/差距/代码 → 创建 change artifacts      │
│  Phase 2.5 deps          候选列表 → 依赖分析 → 报告                       │
│  Phase 3   spec-done     验证所有 artifact 已 commit,交接 ship 端          │
├──────────────────────────────────────────────────────────────────────────┤
│  SHIP 端  (guide-ship)                                                     │
│  Phase 1   plan          选 change → COMMIT GATE → worktree → 计划       │
│  Phase 1.5 转监控?       worktree 创建后询问进入监控或继续                  │
│  Phase 2   execute       监控模式(读 tasks.md 进度)+ 委托 execute 技能    │
│  Phase 3   archive       merge → openspec archive → cleanup(逐 change)   │
│  Phase 4   cleanup       清理残留 worktree + branch                        │
│  Phase 5   ship-done     验证全空,可选回到 spec 端                         │
├──────────────────────────────────────────────────────────────────────────┤
│  独立子技能  propose, execute, status(A/B/C/D), roadmap, deps              │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 关键概念

| 概念 | 说明 | 当前实现 |
|------|------|---------|
| Spec/Ship 切分点 | `git commit artifacts` | 清晰,以 `.openspec.yaml` 在 HEAD 中存在为探针 |
| 状态持久化 | 文件分层 | `proposal-suggestions.md` (git) + `.rddf/state/*` (gitignore) |
| 执行隔离 | `git worktree` | `.rddf/wt/<name>/` |
| 进度同步 | tasks.md 单一事实源 | `grep -c "^- \[x\]"` 实时读取 |
| 并行执行 | 🔒 阻塞 vs 🔓 分离 | 灵活但有状态分歧(见 10.2) |
| Roadmap 模式 | vs 兼容模式 | `roadmap.md` 存在时启用,缺失则降级 |

---

## 2. Phase 0 — INSTALL(全局安装)

### 2.1 流程描述

- 用户首次从全局安装,只有 `INSTALL` 技能可见
- 执行 `skill_use("INSTALL")` 将子技能复制到项目目录 `.opencode/skills/rdd-workflow/skills/`
- 同步创建 `package.json` 和 `install-rdd-workflow.sh`(给其他 AI 助手用)

### 2.2 🔴 P0-1:openspec CLI 缺失时 `read` 阻塞 stdin

**证据** (`INSTALL.md:38-43`):

```bash
printf '%s' "按回车键退出,或输入 'y' 继续安装(不推荐): "
read -r confirm
if [ "$confirm" != "y" ]; then
    echo "已退出。请先安装 openspec CLI。"
    exit 0
fi
```

**问题**:AI 编程助手(OpenCode/Claude Code)调用此技能时,**没有 stdin 终端**,`read` 会永久挂起。

**修复建议**:

```bash
# 用 env var 替代 stdin 读取
if [ "${SKIP_OPENSPEC_PROMPT:-no}" = "yes" ]; then
  echo "⚠️  跳过 openspec 检查(SKIP_OPENSEQ_PROMPT=yes)"
elif command -v openspec >/dev/null 2>&1; then
  echo "✅ openspec CLI 已安装"
else
  echo "❌ openspec CLI 未安装"
  echo "   请运行: npm install -g openspec-cli"
  exit 1
fi
```

### 2.3 🟡 P1-1:INSTALL.md 与 install.sh 路径推断分歧

**证据**:

- `INSTALL.md:84`: `PACKAGE_DIR=$(dirname "$(dirname "$(realpath "$0" 2>/dev/null || echo "$HOME/.agents/skills/rdd-workflow")")")`
- `install.sh:9`: `PACKAGE_DIR="${PACKAGE_DIR:-$HOME/.agents/skills/rdd-workflow}"`
- `install.sh:10`: `TARGET_DIR="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`

**问题**:两份"安装"文档用不同的路径解析策略;`INSTALL.md` 依赖脚本自身位置(`$0`),`install.sh` 依赖环境变量。两者不互斥但容易让用户混淆。

**修复建议**:统一为"环境变量优先,fallback 到 `~/.agents/skills/rdd-workflow`,最后用 `realpath $0`"。

### 2.4 🟡 P1-2:环境检查遗漏 `python3` 和 `jq`

**证据** (`INSTALL.md:17-46`): 只检查 `openspec` CLI,未检查 `python3` / `jq` / `git` / `cmake`。

**实际使用** (跨文件):

| 工具 | 调用次数 | 主要位置 |
|------|---------|---------|
| `python3` | 26 | `propose.md:61-67`、`roadmap.md:139,245,558` 等 |
| `jq` | 5 | `status.md:133-135,266-268`、`propose.md:441-455` |
| `cmake` | 2 | `execute.md:177,192` |
| `git` | 50+ | 全部 skill |

**问题**:INSTALL.md 自称"前置条件检查"但只检查 1/5 外部依赖。`python3` 缺失会直接破坏 `proposal-suggestions.md` 解析、`roadmap-state.json` 更新等关键路径。

**修复建议**:在 `INSTALL.md` 步骤 1 添加:

```bash
for cmd in openspec python3 jq git cmake; do
  command -v "$cmd" >/dev/null 2>&1 || echo "⚠️  缺失依赖: $cmd"
done
```

### 2.5 🟢 P2-1:9 个 skill 的 `version` 字段语义混乱

**证据** (各文件 frontmatter `version` 字段):

| Skill | version | generatedBy |
|-------|---------|-------------|
| INSTALL | 1.0 | (无) |
| guide | **4.0** | 3.0 |
| guide-spec | 1.0 | 3.0 |
| guide-ship | 1.0 | 3.0 |
| propose | 2.0 | 2.0 |
| execute | 2.5 | 2.0 |
| status | 2.3 | 2.0 |
| roadmap | 1.0 | 2.0 |
| deps | 1.3 | 1.3.1 |

**问题**:

- `guide.md` 标 4.0 但它是新拆分出来的推荐器(代码仅 100 行),版本号不连续
- `generatedBy` 含义不明(看起来是上游工具版本,但与自身 version 不一致)

**修复建议**:建立语义图例 — `<skill> v<major>.<minor>`,`generatedBy` 重命名为 `evolved-from` 并指向上一代。

---

## 3. Phase 0.5 — guide(无状态推荐器)

### 3.1 流程描述

- 入口:`skill_use("guide")`
- 行为:只读扫描项目状态,输出"建议调用 X"一行,不修改任何文件
- 6 级优先级扫描(worktree 状态 → committed changes → roadmap → changes → suggestions)

### 3.2 🟡 P1-3:`guide.md` 扫描盲区 — 不查 `.rddf/state/roadmap-state.json`

**证据** (`guide.md:22-76`): 6 个检测项

1. worktree 存在 + tasks 未完成
2. worktree 存在 + tasks 全完成
3. committed change 但无 worktree
4. 无 `roadmap.md`
5. 无 committed change
6. `proposal-suggestions.md` 状态

**未检测**:

- `.rddf/state/roadmap-state.json` 当前阶段状态(roadmap 模式 vs 兼容模式)
- `.rddf/state/phase-gate-report.md` 存在(可能刚生成,需要查看)
- worktree 的实际执行状态(🔒 阻塞 vs 🔓 分离)— 假设分离执行后用 `guide` 会扫到 worktree 在跑,但不区分

**修复建议**:增加扫描:

```bash
# 优先检查:门控报告 + 阶段门控
[ -f "$PROJECT_ROOT/.rddf/state/phase-gate-report.md" ] && \
  RECOMMEND="status --roadmap"; REASON="阶段门控报告待 review"

# 次优先:分离执行中(主 session 不在 worktree)
DETACHED=$(git worktree list 2>/dev/null | awk '$3 ~ /^openspec\// {print $1}' | wc -l)
if [ "$DETACHED" -gt 0 ] && [ -z "$(jobs -l)" ]; then
  RECOMMEND="guide-ship"; REASON="$DETACHED 个 worktree 在跑(可能在分离终端)"
fi
```

### 3.3 🟡 P1-4:`grep "openspec/"` 误匹配风险

**证据** (`guide.md:50`): `git worktree list 2>/dev/null | grep -q "openspec/"`

**问题**:如果 worktree 路径含 `openspec/` 字符(虽然设计上是 `.rddf/wt/<name>`,但用户可能改名),会误匹配。建议用 `awk '$3 ~ /^openspec\//'` 显式匹配分支名。

---

## 4. Phase 1 — setup(guide-spec.md Phase 1)

### 4.1 流程描述

- 入口:`skill_use("guide-spec")` 或从 guide 推荐
- 5 项检测:openspec CLI、git 工作区、当前分支、构建目录、活跃 changes 数量
- 输出菜单:继续 / 重新检查 / 修复 PATH / 保存退出

### 4.2 🔴 P0-2:硬编码 `/home/ubuntu/.npm-global/bin/openspec`

**证据** (`guide-spec.md:80, 159`):

```bash
OPENSPEC_PATH=$(command -v openspec 2>/dev/null || echo "/home/ubuntu/.npm-global/bin/openspec")
```

**问题**:

1. 这是**特定用户的 home 路径**,不可移植
2. 隐式假设 openspec 安装到该路径,但 npm 全局安装默认是 `/usr/local/bin/`
3. 该路径在 macOS / Windows / 其他 Linux 发行版上不存在

**修复建议**:

```bash
# 多路径 fallback
for p in /home/ubuntu/.npm-global/bin/openspec /usr/local/bin/openspec /opt/homebrew/bin/openspec $(command -v openspec 2>/dev/null); do
  [ -x "$p" ] && OPENSPEC_PATH="$p" && break
done
```

### 4.3 🟢 P2-2:5 项检测中"构建目录"是项目特定假设

**证据** (`guide-spec.md:103-107`):

```bash
if [ -d "build" ]; then
    echo "✅ 构建目录存在 (build/)"
else
    echo "⚠️  构建目录不存在"
fi
```

**问题**:这是 C++/CMake 项目的特定概念,对其他语言项目(JS 项目的 `node_modules/`、Rust 项目的 `target/`、Python 项目的 `venv/`)不适用。

**修复建议**:通过 `roadmap.md` 模板或 `package.json` 字段推断项目类型,选择对应检测路径。

---

## 5. Phase 1.5 — roadmap(guide-spec.md Phase 1.5)

### 5.1 流程描述

- 检查 `roadmap.md` 是否存在
- **不存在** → 自动调 `skill_use("roadmap", "init")`(4 个模板)
- 存在 → 显示当前阶段和分类进度
- 菜单:继续 / 编辑 / 门控报告 / 强制推进 / 退出

### 5.2 🟡 P1-5:4 个 roadmap 模板中 3 个是空头

**证据** (`roadmap.md:66-72`):

```text
1. C++ 库项目(基础 → 核心 → 高级)  ✓ 有完整内容
2. Web 应用(MVP → 功能 → 优化)     ❌ 无内容
3. 空白模板(自定义)                ❌ 无内容
4. 基于现有 ADR 生成               ❌ 无内容
```

**问题**:用户选择 2/3/4 后,流程要么生成空 roadmap.md,要么 `cat << EOF` 输出模板不完整。

**修复建议**:至少实现模板 3(空白 + 引导式问题),或菜单中隐藏未实现模板(标"即将推出")。

### 5.3 🟡 P1-6:`roadmap.md` 删除/损坏时无警告

**证据** (`propose.md:65`): `phase_match = re.search(r'\*\*当前阶段\*\*:\s*(\S+)', content)` — 标记不存在时返回 None → `CURRENT_PHASE="unknown"`。

**问题**:用户删除或损坏 `roadmap.md` 后:

1. `propose.md` 静默切换到兼容模式
2. 已有的 `roadmap-meta.yaml` 变成孤儿
3. `roadmap-state.json` 的 `current_phase` 不再被同步
4. 没有警告或恢复提示

**修复建议**:`propose.md` Phase -1 检测到 `roadmap.md` 消失时,提示"⚠️ roadmap.md 已不存在,继续运行将进入兼容模式"。

### 5.4 🟢 P2-3:`roadmap.md:558, 624` 的 `json.load()` 无错误处理

**证据**:

```bash
python3 -c "import json; print(json.load(open('$STATE_FILE')).get('current_phase', 'unknown'))"
```

**问题**:`.rddf/state/roadmap-state.json` 缺失或损坏时直接 `FileNotFoundError` / `JSONDecodeError`,命令整体失败。

**修复建议**:

```python
try:
    with open('$STATE_FILE') as f:
        print(json.load(f).get('current_phase', 'unknown'))
except (FileNotFoundError, json.JSONDecodeError):
    print('unknown')
```

---

## 6. Phase 2 — propose(guide-spec.md Phase 2 + propose.md)

### 6.1 流程描述

- 扫描:`docs/adr/ADR-*.md` + `docs/architecture/*-gap-analysis.md` + 代码 TODO/FIXME + 测试覆盖缺口
- 分类:🔴 ADR 未实现 / 🟡 架构差距 / 🔵 计划功能 / 🟢 代码标记 / ⚪ 测试缺口
- 用户多选 → 串行执行 `openspec new change` + `openspec instructions` 循环
- 完成后 → 自动 git commit(Phase 5b)

### 6.2 🔴 P0-3:自动 commit `git add openspec/changes/*/` 的 glob 风险

**证据** (`propose.md:619`):

```bash
git add openspec/changes/*/
git add proposal-suggestions.md
```

**风险**:

1. 匹配 `openspec/changes/archive/`(openspec archive 移入的位置)— archive 不应被新 commit 触碰
2. 匹配任何已存在的、未被本会话管理的 change 目录
3. `openspec/changes/*/` glob 行为依赖 bash `globstar` 设置 — 默认开启但不保证

**修复建议**:

```bash
# 精确 add:只 add 本次创建的 change
for name in $THIS_SESSION_CREATED; do
  git add "openspec/changes/$name/"
done
git add proposal-suggestions.md
```

### 6.3 🔴 P0-4:`proposal-suggestions.md` 解析错位

**证据** (`propose.md:111-162`):

- 文件实际格式:混合 Markdown + YAML 列表
- 解析策略:行级 `if line.strip().startswith('- name:')` 分割
- 第 135 行:`project_root = os.environ.get('PROJECT_ROOT', '')` — 依赖环境变量

**问题**:

1. `PROJECT_ROOT` env var 在 bash 调用 Python 时**不一定传递**
2. `propose.md:144` 用 `os.path.isdir(f'{project_root}/openspec/changes/{name}/')` — 路径前缀若空 → 永远 False → 不会移除已创建条目 → 列表无限增长
3. 行级解析对缩进敏感,如果 `proposal-suggestions.md` 中含代码块示例(如 `- name: "foo"`)会被误识别

**修复建议**:

```python
# 改用真实 YAML 解析 + 容错
import yaml, re
content = re.sub(r'^---$', '', content, flags=re.M)  # 移除 markdown 分隔

# 用 git rev-parse 推导 project_root,不依赖 env
import subprocess
project_root = subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel'], text=True
).strip()
```

### 6.4 🟡 P1-7:`proposal-suggestions.md` 格式未规范化

**问题**:YAML 列表 + Markdown 注释(描述中含 `## 架构依据` 等) + 字段顺序自由。跨文件读取时(`guide.md:68`、`guide-spec.md:278`、`status.md:396`)、跨格式。

**修复建议**:定义 JSON Schema,文件用 JSON 而非 YAML,或严格 YAML 格式(只 `## 标题` 注释,不放 body)。

### 6.5 🟡 P1-8:`openspec/changes/<name>/` 验证用 `os.path.isfile` 而非 git HEAD

**证据** (`guide-spec.md:384-388`):

```python
# 检查 change 是否已提交(.openspec.yaml 在 HEAD 中存在)
if os.path.isfile(openspec_yaml):
    candidates.append(name)
```

**问题**:

1. 注释说"在 HEAD 中存在",代码是**文件系统**检查
2. 未提交的 change 也会进入 deps 候选
3. 进入 deps 后 `git show HEAD:` 验证会失败但 deps.md 静默跳过,流程仍继续

**修复建议**:

```python
# 真正检查 HEAD
import subprocess
result = subprocess.run(
    ['git', 'show', f'HEAD:openspec/changes/{name}/.openspec.yaml'],
    capture_output=True, text=True
)
if result.returncode == 0:
    candidates.append(name)
```

---

## 7. Phase 2.5 — deps(guide-spec.md Phase 2.5 + deps.md)

### 7.1 流程描述

- 自动触发(无菜单)
- Step 1:生成 `.rddf/state/deps-candidates.json`
- Step 2-4:静态三轴分析(文件冲突、ADR 引用、接口依赖)
- Step 3:子代理语义分析(**占位符**)
- Step 5:写入 `.rddf/state/deps-output.md`

### 7.2 🔴 P0-5:`deps.md` Step 5 实际不写文件(heredoc 是占位符)

**证据** (`deps.md:391-398`):

```bash
mkdir -p "$PROJECT_ROOT/.rddf/state/"
cat > "$DEPS_OUTPUT" << 'DEPS_EOF'
# 依赖分析报告
(5a-5e 的全部内容写入此文件,格式见下文)
DEPS_EOF
echo "✅ 依赖分析报告已写入: $DEPS_OUTPUT"
```

**问题**:

1. heredoc 内的内容是**注释字符串**,不是实际生成逻辑
2. 5a-5e 是 `<!-- TEMPLATE: ... -->` 注释(line 404, 430, 442, 450, 458)
3. 真正的静态分析结果(Step 2 的 `comm -12` 输出)未在任何代码路径中收集和写入
4. `guide-spec.md:402` 的 `cat "$PROJECT_ROOT/.rddf/state/deps-output.md"` 会显示**空文件**

**修复建议**:

- 选项 A:在 Step 2 收集结果到 bash 变量,在 Step 5 用 here-doc + 变量插值写入
- 选项 B:Step 5 改成调用 `python3 -c "..."` 用 Step 2 收集的 JSON 数据生成 Markdown
- 选项 C:明确标注"deps 当前仅打印静态分析到 stdout,不动文件"

### 7.3 🟡 P1-9:`deps.md` 与 `roadmap-meta.yaml` 脱节

**证据**:

- `propose.md:512-523` 创建 `openspec/changes/<name>/roadmap-meta.yaml`(含 phase/category/priority)
- `deps.md` Step 1 读取 `proposal.md`、`design.md` — **不读 `roadmap-meta.yaml`**
- 整个 deps 阶段与 roadmap 模式无信息交换

**问题**:`roadmap.md:23` 工作流位置图示 `guide → roadmap → propose → deps → plan` 暗示 deps 应该消费 roadmap 元数据,但代码未实现。

**修复建议**:在 `deps.md` Step 1 增加对 `roadmap-meta.yaml` 的读取,作为"阶段门控预检"。

### 7.4 🟢 P2-4:`deps.md` 子代理语义分析声明与现实不符

**证据**:

- L320:`<!-- TODO: 子代理语义分析尚未实现 -->`
- L324-334:伪代码 + `echo "🤖 正在调用子代理..."`
- L455-488:5e 章节模板中包含 `## 依赖分析报告` 等 AI 输出

**问题**:Step 5 模板中承诺的 AI 输出实际不会产生。

**修复建议**:在 `5e. 🧠 AI 分析建议` 章节明确写"AI 语义分析未启用,以下为静态分析结论"。

---

## 8. Phase 3 — spec-done(guide-spec.md Phase 3)

### 8.1 流程描述

- 触发:deps 完成后自动进入
- 验证:所有 active changes 的 `{proposal,design,tasks}.md` 在 `git show HEAD:<path>` 可达
- 通过 → 输出"Next: skill_use(\"guide-ship\")"

### 8.2 🟡 P1-10:零 active changes 时验证循环空跑直接通过

**证据** (`guide-spec.md:432-446`):

```bash
if (cd "$PROJECT_ROOT" 2>/dev/null && for d in openspec/changes/*/; do
    [ -d "$d" ] || continue
    case "$d" in */archive/) continue ;; esac
    name=$(basename "$d")
    for artifact in proposal.md design.md tasks.md; do
        if ! git show HEAD:"$d$artifact" > /dev/null 2>&1; then
            echo "❌ $name missing committed $artifact — refuse to exit spec-side"
            exit 1
        fi
    done
done); then
    echo "✅ All changes have committed artifacts. Spec side complete."
else
    exit 1
fi
```

**问题**:

1. `for d in openspec/changes/*/` — 如果无 active change 目录,**循环不执行** → 退出码 0 → 直接通过
2. 用户可能"误完成 Propose 阶段"(跳过所有建议)但通过 spec-done
3. 之后 guide-ship 也找不到 change → 死路

**修复建议**:

```bash
CHANGE_COUNT=$(ls -d openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l)
if [ "$CHANGE_COUNT" -eq 0 ]; then
  echo "❌ 没有 active change,无法退出 spec-side"
  echo "   请回到 Propose 阶段至少创建一个 change"
  exit 1
fi
```

### 8.3 🟢 P2-5:`spec-done` 与 ship-done 衔接是软契约

**问题**:

1. `guide-spec.md:458` 明确"Do NOT auto-invoke guide-ship"
2. `guide.md:54-61` 扫描到 "committed change 但无 worktree" 时推荐 `guide-ship`
3. 两条路径都通,但无显式交接文档/状态
4. 用户可能调用 `guide` 或 `guide-spec` 多次,guide 的推荐基于"当前扫描状态",可能反复推荐相同 action

**修复建议**:定义一个轻量级交接状态文件(`.rddf/state/handoff.json`)记录"spec 端已交付,等待 ship 端开始"。

---

## 9. Phase Ship.1 — plan(guide-ship.md Phase 1)

### 9.1 流程描述

- 入口:`skill_use("guide-ship")`
- 展示所有 active changes 状态表
- 用户选 change → COMMIT GATE → 创建 worktree → 生成 Prometheus 计划 → 选执行模式

### 9.2 🔴 P0-6:`prometheus-start-work` 未声明的必需依赖

**证据** (`guide-ship.md:175-195`):

```bash
if skill_use("prometheus-start-work") 2>/dev/null; then
    if [ ! -f ".rddf/plans/$CHANGE_NAME.md" ]; then
        echo "❌ Prometheus start_work 未生成计划文件"
        exit 1
    fi
    PLAN_TASK_COUNT=$(grep -c '^- \[' ".rddf/plans/$CHANGE_NAME.md" 2>/dev/null || echo 0)
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

**问题**:

1. `prometheus-start-work` 不在 `package.json:17` 的 `skills` 数组
2. `skills/` 目录下无对应 `.md` 文件
3. README/USAGE/INSTALL 全部未提及此依赖
4. `package.json:11-15` 的 `engines.dependencies` 只声明 `openspec-cli`
5. **`.rddf/plans/<name>.md` 的唯一生成途径就是它**(execute.md:200、status.md:124 都依赖此文件)
6. 失败时无清晰用户引导(只说"请确认")

**修复建议**:

- `package.json:17` 数组添加 `prometheus-start-work`
- `README.md` "前置条件"添加此项
- `INSTALL.md` 步骤 1 添加 `skill_use("prometheus-start-work") --help` 测试
- `guide-ship.md:191` 提供具体安装命令

### 9.3 🔴 P0-7:`status.md` / `execute.md` 5 处 `git worktree list` 字段索引 BUG

**证据**:`git worktree list` 输出格式为 `<path> <commit> [(<branch>)]`,即 `$1` = path,`$2` = commit,`$3` = branch。

| 位置 | 代码 | 错误 |
|------|------|------|
| `status.md:144` | `git worktree list \| awk '$2=="openspec/<name>" {print $1}'` | 🔴 `$2` 是 commit hash |
| `status.md:281` | 同上 | 🔴 |
| `status.md:387` | `git worktree list \| awk '$2 ~ /^openspec\// {print $1}'` | 🔴 |
| `execute.md:283` | `git worktree list \| awk '$2 ~ /^openspec\// && $2 != "openspec/<name>" {print $1}'` | 🔴 |
| `execute.md:287` | 同上 | 🔴 |
| `execute.md:411` | 文档表格把 `awk '$2==\"openspec/<name>\"'` 列为"正确示例" | 🔴 **错误模式被文档化** |

**对照正确模式** (`guide-ship.md:276, 503, 589`、`guide.md:32`):

```bash
git worktree list | awk '$3 ~ /^openspec\// {print $1}'  # $3 = branch
```

**问题**:

- `WORKTREE_PATH` 永远为空 → `status.md` 永远找不到 worktree
- `execute.md:283` 的 `OTHER_WTS` 永远为 0 → "发现其他 worktree" 分支永不触发
- `status.md:411` 文档表是 **anti-tutorial**

**修复建议**:

```bash
# 创建公共函数(建议放 skills/_lib/worktree.sh)
wt_path_for_branch() {
  git worktree list | awk -v br="openspec/$1" '$3 == br {print $1; exit}'
}
# 调用
WT_PATH=$(wt_path_for_branch "$CHANGE_NAME")
```

### 9.4 🟡 P1-11:`README.md` 描述的 "guide-ship phases" 与代码不一致

**证据**:

- `README.md:27` 描述 `guide-ship` 为 `discover → worktree → plan → execute → archive`
- 实际 `guide-ship.md` Phase 编号是 `plan(1) → execute(2) → archive(3) → cleanup(4) → ship-done(5)`
- **没有"discover"阶段**

**问题**:README 与代码的阶段命名/编号不一致,新用户对照 README 找不到 "discover" 阶段。

**修复建议**:统一为"plan → execute → archive → cleanup → ship-done"。

---

## 10. Phase Ship.1.5 — 转监控检查(guide-ship.md Phase 1.5)

### 10.1 流程描述

- 在 Phase 1 创建 worktree 后,询问:进入 Execute 监控 / 继续 Plan

### 10.2 🟢 P2-6:无独立编号,易被忽视

**问题**:`guide-ship.md:244-258` 的"返回 Plan 前的检查"是独立的逻辑块但没编号。

**修复建议**:改为 `Phase 1.5` 并加目录。

---

## 11. Phase Ship.2 — execute(guide-ship.md Phase 2 + execute.md)

### 11.1 流程描述

- 监控模式(guide-ship.md Phase 2):读 `tasks.md` 进度,显示所有 worktree 状态
- 实际执行(execute.md):在 worktree 内调用 Prometheus 计划,委托 deep 代理,串/并行执行 Work Unit

### 11.2 🔴 P0-8:🔓 分离执行(新终端)模式下 roadmap 进度永远不更新

**证据**:

- `execute.md:55`: `PROJECT_ROOT=$(git rev-parse --show-toplevel)` — 在 worktree 内执行时,返回**worktree 自己的根** (e.g., `.rddf/wt/<name>/`),不是主 repo 根
- `execute.md:301`: `STATE_FILE="$PROJECT_ROOT/.rddf/state/roadmap-state.json"`
- **实际路径**:`.rddf/wt/<name>/.rddf/state/roadmap-state.json` (worktree 内)
- **期望路径**:`$PROJECT_ROOT/.rddf/state/roadmap-state.json` (主 repo 根)

**问题**:

1. 分离执行时,`execute` 在新终端的 worktree 内运行
2. `git rev-parse --show-toplevel` 返回 worktree 根
3. `.rddf/state/roadmap-state.json` 被写入 **worktree 内的 `.rddf/state/`**(新建,因为不存在)
4. 主 session 完全看不到这个更新
5. 阻塞执行(🔒)也受影响(虽然工作目录回到主 session,但 execute 调用时 cwd 已在 worktree)
6. `roadmap-state.json` 的 `completed_changes` 永远不增长
7. `roadmap.md advance` 永远卡在"未完成"门控

**修复建议**:

```bash
# execute.md:55-58 区分主仓库根 vs 当前 worktree 根
MAIN_ROOT=$(git worktree list | awk '$3 == "main" || $3 == "master" {print $1; exit}')
# 或:从 worktree 的 .git 文件反向解析
GIT_COMMON_DIR=$(git rev-parse --git-common-dir)
if [[ "$GIT_COMMON_DIR" == *"/.git" ]]; then
  MAIN_ROOT=$(dirname "$GIT_COMMON_DIR")
else
  MAIN_ROOT=$(dirname "$(dirname "$GIT_COMMON_DIR")")
fi
PROJECT_ROOT="$MAIN_ROOT"
```

### 11.3 🔴 P0-9:`execute.md:122-123` 在 AI 助手中 `read -p` 阻塞

**证据** (`execute.md:122-123`):

```bash
echo "请选择要进入的 worktree(输入编号),或按 Ctrl+C 取消:"
read -p "编号: " choice
```

**问题**:在 OpenCode/Claude Code 环境中无 stdin,`read` 永久挂起。

**修复建议**:

```bash
# 选项 A:env var 优先
choice="${EXECUTE_CHOICE:-1}"
# 选项 B:基于最近活跃自动选
if [ -z "$choice" ]; then
  choice=1
  echo "ℹ️  自动选择最近 worktree: $choice"
fi
```

### 11.4 🟡 P1-12:`guide-ship` 阻塞 vs 分离路径的 roadmap 更新不对称

**与 P0-8 相关但独立**:

- 🔒 阻塞执行:`guide-ship` 内调 `execute` → execute 在 worktree 内 → 仍写入 worktree 内的 `.rddf/state/`
- 🔓 分离执行:新终端调 `execute` → 同上
- **两种路径都不更新主 repo 根的 `.rddf/state/roadmap-state.json`**

**修复建议**:见 P0-8。

### 11.5 🟢 P2-7:`guide-ship.md:204` 任务数查询路径错误

**证据** (`guide-ship.md:204`):

```bash
任务数: $(grep -c '^- \[' "$wt/openspec/changes/$name/tasks.md" 2>/dev/null || echo '?')
```

**问题**:`$wt` 是绝对路径,`$name` 是从 `branch` 推导的,两者的拼接是 `$wt/openspec/changes/$name/tasks.md`。这本身是对的,但 **`$wt` 变量未定义** — 上下文用的是 `$WT_PATH`,且此行在 echo 字符串中,不会执行实际的 grep。这只是**伪代码示例**显示在 echo 里。

**修复建议**:要么在 echo 前赋值 `$wt`,要么明确标注是伪代码。

---

## 12. Phase Ship.3 — archive(guide-ship.md Phase 3 + status.md Mode C)

### 12.1 流程描述

- 检查所有 change 状态(独立归档,逐个处理)
- 流程:merge worktree → main → `openspec archive` → `git worktree remove` → `git branch -d`
- 合并验证(BEFORE_MERGE / AFTER_MERGE)

### 12.2 🟡 P1-13:merge 验证逻辑复杂且有边界 case

**证据** (`guide-ship.md:432-481`):

```bash
BEFORE_MERGE=$(git rev-parse HEAD)
# ... merge
AFTER_MERGE=$(git rev-parse HEAD)
if [ "$BEFORE_MERGE" = "$AFTER_MERGE" ]; then
  if git merge-base --is-ancestor "openspec/$CHANGE_NAME" HEAD; then
    echo "⚠️  merge 完成但无新 commit"
  else
    echo "❌ Merge 验证失败" && exit 1
  fi
fi
```

**问题**:

1. `--ff-only` 成功时,HEAD 不变(已是 fast-forward),但 `merge-base --is-ancestor` 通过 → 警告但继续
2. `--no-ff` 成功时,HEAD 变(BEFORE ≠ AFTER)→ 通过
3. **真正问题**:如果 worktree 分支**没有新提交**(execute 未运行),`--ff-only` 仍会"成功"但没合并任何东西,`merge-base --is-ancestor` 通过
4. 边界 case:worktree 落后于 main + 已有新 commit + `--ff-only` 失败 → `--no-ff` 自动 fallback

**修复建议**:

```bash
# 在 merge 前检查 worktree 分支有新提交
WORKTREE_TIP=$(git rev-parse "openspec/$CHANGE_NAME")
WORKTREE_NEW_COMMITS=$(git rev-list --count "main..openspec/$CHANGE_NAME" 2>/dev/null || echo 0)
if [ "$WORKTREE_NEW_COMMITS" -eq 0 ]; then
  echo "❌ worktree 分支无新提交,无需 merge"
  echo "   可能 execute 未运行或无代码变更"
  exit 1
fi
```

### 12.3 🟡 P1-14:`status.md` Mode C 与 guide-ship Phase 3 归档逻辑重复

**证据**:

- `status.md:259-365` (Mode C, 107 行) 和 `guide-ship.md:378-522` (Phase 3, 145 行) 实现相同的归档流程
- 但实现有差异:
  - `status.md:317-336` 用 `MERGE_BASE` 判断后选 `--ff-only` / `--no-ff`
  - `guide-ship.md:441-448` 同样逻辑但分支条件略有不同
  - `status.md:281` 有 BUG(worktree `$2` 索引),`guide-ship.md:420` 是正确的

**问题**:归档逻辑在两个文件重复实现,任何修复都要改两处。

**修复建议**:抽取到 `skills/_lib/archive.sh`,两边都 `source` 它。

### 12.4 🟢 P2-8:归档后 `git branch -d` vs `-D` 决策不透明

**证据** (`guide-ship.md:486-493`):

```bash
if git branch -d "openspec/$CHANGE_NAME" 2>/dev/null; then
  echo "✅ Branch 已删除"
else
  echo "⚠️  Branch 有未合并的提交,强制删除"
  git branch -D "openspec/$CHANGE_NAME"
fi
```

**问题**:刚 merge 完就 `-D` 强删,说明 merge 没真正生效。这其实是上一个问题的副作用。

**修复建议**:合并成功后 `-d` 应成功;若失败,说明之前 merge 没工作 → 让用户决定(不自动 `-D`)。

---

## 13. Phase Ship.4 — cleanup(guide-ship.md Phase 4)

### 13.1 流程描述

- 清理残留 worktree + branch(若 Phase 3 未清理)
- 输出测试总结报告

### 13.2 🟢 P2-9:`--D` 强删可能丢失未 push 提交

**问题**:`cleanup` 阶段的选项 2 (`guide-ship.md:555-573`) 用 `git branch -D` 删除所有 `openspec/*` branches。如果用户在 worktree 中**额外**开发未归档的 commit,会丢失。

**修复建议**:在 `-D` 前打印每个 branch 的 `git log -1 --format` 让用户确认。

---

## 14. Phase Ship.5 — ship-done(guide-ship.md Phase 5)

### 14.1 流程描述

- 验证:`REMAINING_WT == 0` 且 `REMAINING_CHANGES == 0`
- 菜单:继续处理 / 回到 spec 端 / 完成

### 14.2 🟢 P2-10:ship-done 实际不是终态,可循环回 spec

**问题**:`ship-done` 阶段实际提供"回到 spec 端"选项(guide-ship.md:602),所以工作流**永远没有真正的终态**。从用户角度,"完成"是模糊的。

**修复建议**:明确"session 结束"语义(本次 spec/ship 配对完成)vs"项目完成"语义(不再做任何 change)。

---

## 15. 跨阶段问题

### 15.1 USAGE.md 文档与代码不一致

| 文档 | 代码 | 不一致点 |
|------|------|---------|
| `USAGE.md:155-156` "返回 Propose 阶段" 菜单 | `guide-ship.md:78-85` 无此选项 | 🔴 文档承诺的循环路径不存在 |
| `USAGE.md` 仍含旧 `workflow-state.md` 格式示例 | `guide.md:92-98` 已警告旧文件废弃 | 🟡 旧示例误导 |
| `USAGE.md:51` 提 `skill_use("guide")` | `guide.md:86` 推荐动态变量 | ℹ️ 文档/实现脱节 |
| `USAGE.md` 顶部 "Pre-refactor migration note" | 重构已完成(b3800d4) | 🟡 警告已过时 |

### 15.2 `read -p` 阻塞反模式(跨文件)

| 位置 | 严重度 |
|------|-------|
| `INSTALL.md:39` | 🔴 P0-1 |
| `execute.md:123` | 🔴 P0-9 |

### 15.3 "i. 其他输入" 17 处无 case 处理

| 文件 | 出现位置 | 严重度 |
|------|---------|-------|
| `guide-spec.md` | 134, 210, 326 | 🟡 |
| `guide-ship.md` | 84, 211, 256, 320, 403, 511, 520, 543, 597, 604 | 🟡 |
| `propose.md` | 665 | 🟡 |
| `status.md` | 111, 477 | 🟡 |
| `execute.md` | 295 | 🟡 |

**问题**:`"i. 其他输入"` 在 17 个菜单出现,但**无任何 case 处理代码**。AI 编程助手代理收到非数字输入会未定义行为。

**修复建议**:要么删除"i. 其他输入"菜单项,要么用 `case` 显式处理常见别名(`q` → 退出, `r` → 刷新, `?` → 帮助)。

### 15.4 状态文件分散(无单一权威源)

| 状态文件 | git 跟踪 | 写入者 | 读取者 |
|---------|---------|-------|-------|
| `proposal-suggestions.md` | ✅ | propose.md | guide.md, guide-spec.md, status.md |
| `roadmap.md` | ✅ | roadmap.md | propose.md, guide-spec.md, status.md |
| `openspec/changes/<n>/proposal.md` | ✅ | propose.md (via openspec CLI) | deps.md, status.md |
| `openspec/changes/<n>/design.md` | ✅ | 同上 | deps.md |
| `openspec/changes/<n>/tasks.md` | ✅ | propose.md, execute.md | guide.md, guide-ship.md, status.md |
| `openspec/changes/<n>/.openspec.yaml` | ✅ | openspec new | guide-spec.md, guide-ship.md (commit probe) |
| `openspec/changes/<n>/roadmap-meta.yaml` | ✅ | propose.md | roadmap.md, execute.md |
| `.rddf/state/roadmap-state.json` | ❌ | roadmap.md, propose.md, execute.md | roadmap.md, status.md, execute.md |
| `.rddf/state/deps-candidates.json` | ❌ | guide-spec.md | deps.md |
| `.rddf/state/deps-output.md` | ❌ | deps.md (P0-5 实际未写) | guide-spec.md |
| `.rddf/state/phase-gate-report.md` | ❌ | roadmap.md | **无人读** (死代码风险) |
| `.rddf/plans/<n>.md` | ❌ | Prometheus (外部) | execute.md, status.md |

**问题**:

- 13 个状态文件,跨 4 个不同所有者(persist/ephemeral × user/cli)
- `.rddf/state/phase-gate-report.md` 写但从不读(roadmap.md:562-612 写,grep 全仓 0 读)
- `.rddf/state/deps-output.md` 写但 P0-5 实际不写内容
- `proposal-suggestions.md` 跨 5 个文件读写,但格式不规范(见 P1-7)

**修复建议**:

- 写一个 `skills/_lib/state.sh` 统一管理 13 个状态文件路径
- 删 `.rddf/state/phase-gate-report.md` 或加 reader
- 修 `.rddf/state/deps-output.md` 写入逻辑(见 P0-5)

### 15.5 `git show HEAD:"openspec/changes/$name/.openspec.yaml"` 在 5 个文件重复

| 文件 | 行号 |
|------|------|
| `guide-spec.md` | 270, 432, 437 |
| `guide-ship.md` | 59, 100 |
| `guide.md` | 57 |

**问题**:DRY 严重违反,任何修复都要改 5 处。

**修复建议**:抽公共函数 `is_change_committed() { git show "HEAD:openspec/changes/$1/.openspec.yaml" > /dev/null 2>&1; }`。

### 15.6 外部依赖实际使用与声明对比

| 依赖 | 声明位置 | 实际使用 | 是否检查 |
|------|---------|---------|---------|
| `openspec` | `package.json:15` | 8+ 处 | ✅ INSTALL.md |
| `prometheus-start-work` | **未声明** | 1 处 (`guide-ship.md:179`) | ❌ |
| `python3` | **未声明** | 26 处 | ❌ |
| `jq` | **未声明** | 5 处 | ❌ |
| `cmake` | README "前置条件" | 2 处 (`execute.md:177,192`) | ❌ |
| `git` | `package.json:12` (`>=2.25.0`) | 50+ 处 | ⚠️ 隐式 |

---

## 16. 修复优先级总表

### 16.1 🔴 P0 立即处理(估时 5-6 小时)

| ID | 问题 | 文件:行 | 估时 |
|----|------|---------|------|
| P0-1 | `read` 阻塞 stdin(AI 环境) | `INSTALL.md:39` | 15 min |
| P0-2 | 硬编码 `/home/ubuntu/.npm-global/bin/openspec` | `guide-spec.md:80,159` | 30 min |
| P0-3 | `git add openspec/changes/*/` glob 风险 | `propose.md:619` | 30 min |
| P0-4 | `proposal-suggestions.md` 解析依赖 env var | `propose.md:135,144` | 1 hr |
| P0-5 | `deps.md Step 5` heredoc 是占位符 | `deps.md:391-398` | 1 hr |
| P0-6 | `prometheus-start-work` 未声明 | `package.json:17` + 多文件 | 1 hr |
| P0-7 | `git worktree list $2` BUG | `status.md:144,281,387` + `execute.md:283,287,411` | 30 min |
| P0-8 | 分离执行下 roadmap 进度不更新 | `execute.md:55,301` | 1 hr |
| P0-9 | `execute.md read -p` 阻塞 | `execute.md:123` | 15 min |

**P0 估时合计**:约 5-6 小时

### 16.2 🟡 P1 本迭代(估时 12-13 小时)

| ID | 问题 | 文件:行 | 估时 |
|----|------|---------|------|
| P1-1 | INSTALL.md vs install.sh 路径推断分歧 | 2 文件 | 1 hr |
| P1-2 | 遗漏 `python3`/`jq`/`cmake` 检查 | `INSTALL.md` | 30 min |
| P1-3 | `guide.md` 扫描盲区 | `guide.md` | 1 hr |
| P1-4 | `grep "openspec/"` 误匹配 | `guide.md:50` | 15 min |
| P1-5 | 4 个 roadmap 模板 3 个空头 | `roadmap.md:66-72` | 2 hr |
| P1-6 | roadmap.md 删除/损坏无警告 | `propose.md:65` | 1 hr |
| P1-7 | `proposal-suggestions.md` 格式未规范化 | 多文件 | 2 hr |
| P1-8 | deps 候选用 `os.path.isfile` 而非 git HEAD | `guide-spec.md:386` | 30 min |
| P1-9 | deps 与 `roadmap-meta.yaml` 脱节 | `deps.md` | 1 hr |
| P1-10 | 零 change 时 spec-done 直接通过 | `guide-spec.md:432-446` | 15 min |
| P1-11 | README 阶段命名与代码不一致 | `README.md:27` | 30 min |
| P1-12 | 阻塞 vs 分离 roadmap 更新不对称 | (P0-8 已涵盖) | — |
| P1-13 | merge 验证边界 case | `guide-ship.md:432-481` | 1 hr |
| P1-14 | 归档逻辑在 2 文件重复 | `status.md` + `guide-ship.md` | 2 hr |

**P1 估时合计**:约 12-13 小时

### 16.3 🟢 P2 改进项(下个迭代)

| ID | 问题 | 估时 |
|----|------|------|
| P2-1 | 9 个 skill 的 `version` 字段语义混乱 | 1 hr |
| P2-2 | "构建目录"是项目特定假设 | 1 hr |
| P2-3 | `roadmap.md:558,624` `json.load()` 无错误处理 | 30 min |
| P2-4 | `deps.md` AI 章节声明与现实不符 | 30 min |
| P2-5 | spec-done 与 ship-done 衔接是软契约 | 1 hr |
| P2-6 | 转监控检查无独立编号 | 15 min |
| P2-7 | `guide-ship.md:204` 任务数查询路径错误 | 15 min |
| P2-8 | 归档后 `git branch -d` vs `-D` 决策不透明 | 1 hr |
| P2-9 | `--D` 强删可能丢失未 push 提交 | 1 hr |
| P2-10 | ship-done 实际不是终态 | 30 min |

**P2 估时合计**:约 7-8 小时

### 16.4 ℹ️ P3 观察项

| ID | 问题 |
|----|------|
| P3-1 | `USAGE.md` 提 `skill_use("guide")` 与 `guide.md` 推荐动态变量脱节 |
| P3-2 | `USAGE.md` 顶部 migration warning 已过时 |
| P3-3 | 17 处 "i. 其他输入" 无 case 处理(已在 15.3 提及) |
| P3-4 | 跨技能版本号混乱(已在 P2-1 提及) |
| P3-5 | `.rddf/state/phase-gate-report.md` 写但从不读(死代码) |

---

## 17. 附录

### 17.1 9 个 skill 文件 + 元数据

| 文件 | 行数 | 状态机角色 |
|------|------|----------|
| `INSTALL.md` | 198 | Phase 0 入口 |
| `guide.md` | 100 | Phase 0.5 推荐器 |
| `guide-spec.md` | 458 | SPEC 端 5 阶段 |
| `guide-ship.md` | 606 | SHIP 端 5 阶段 |
| `propose.md` | 693 | Phase 2 子技能 |
| `execute.md` | 411 | Phase Ship.2 子技能 |
| `status.md` | 489 | 4 模式(A/B/C/D) |
| `roadmap.md` | 693 | Phase 1.5 子技能 |
| `deps.md` | 516 | Phase 2.5 子技能 |

### 17.2 13 个状态文件清单

详见 15.4 表格。

### 17.3 38 个问题 ID 索引

| 严重度 | 数量 | IDs |
|--------|------|-----|
| 🔴 P0 | 9 | P0-1 ~ P0-9 |
| 🟡 P1 | 14 | P1-1 ~ P1-14 |
| 🟢 P2 | 10 | P2-1 ~ P2-10 |
| ℹ️ P3 | 5 | P3-1 ~ P3-5 |

### 17.4 关键文件位置速查

- **9 个 skill**:`/home/ubuntu/.agents/skills/rdd-workflow/skills/`
- **元数据**:`/home/ubuntu/.agents/skills/rdd-workflow/{README.md, USAGE.md, package.json, install.sh}`
- **AI 编程助手配置**:`/home/ubuntu/.agents/skills/rdd-workflow/.claude-plugin/`
- **状态文档**:`/home/ubuntu/.agents/skills/rdd-workflow/.rddf/state/index.md`
- **审计文档**:`/home/ubuntu/.agents/skills/rdd-workflow/docs/audit/`(本文件位置)

---

## 18. 元信息

| 字段 | 值 |
|------|-----|
| **报告路径** | `docs/audit/2026-06-05-workflow-audit.md` |
| **审计方法** | 静态分析 + grep + read + 双 explore agent 并行深扫 |
| **使用 agent** | explore × 2(契约审计、状态机审计) |
| **样本覆盖** | 9/9 skill 文件 + 3 个元数据 + 1 个 install.sh |
| **证据引用** | 所有 P0/P1 问题均有 `文件:行号` 引用,可直接定位修复 |
| **下次审计建议** | P0 全部修复后,再做"修复合规性审计" |

---

**报告结束**
