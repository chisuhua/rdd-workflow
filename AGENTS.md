# AGENTS.md — spec-workflow

> OpenSpec 工作流技能包: `propose → plan → execute → status → archive` change lifecycle.
> npm 包, v2.0.0-beta. 安装到项目后作为 OpenCode/Claude Code/Cursor 等 AI 助手的 skill 使用。

## 快速命令

```bash
npm test                  # bats tests/ (全部 bats 测试)
python3 -m pytest tests/unit/ -q --tb=short   # Python 单元测试 (29 个文件)
pip install -r requirements.txt                # Python 依赖 (PyYAML, jsonschema, pytest)
bats tests/smoke.bats                          # 快速冒烟测试
bats tests/_lib/test_skill.bats                # skill.bash 单元测试 (8 cases)
```

CI 在 `.github/workflows/test.yml`，按序执行: 安装 deps → 断言质量门控 → Python 单元测试 → Bats smoke。

## 架构

**三阶段架构** (ADR-0003): `arch → plan → ship`

| 阶段 | Skill | 职责 |
|------|-------|------|
| arch | `guide-arch` | 架构定义: ADR, 差距分析, roadmap |
| plan | `guide-plan` | 变更生成: scan, propose, deps |
| ship | `guide-ship` | 变更执行: worktree/轻量, execute, archive, cleanup |

`guide-ship` 自动检测并行冲突：
- 无其他 worktree **且** 仅此一个 change → ⚡ **轻量模式**（创建 branch，直接在主仓库执行，跳过 worktree）
- 有活跃 worktree **或** 多个 change → 🔀 **worktree 模式**（创建隔离 worktree）

`guide-spec` 是向后兼容别名，内部自动调用 `guide-arch` → `guide-plan`。
`guide` 是无状态推荐器，扫描项目状态推荐下一步。

## 关键目录

```
skills/               # Markdown skills (12+ 文件)
  _lib/               # 共享 bash 库 + Python 模块 (33 个文件)
  loop_engine.py      # v2.0 Loop 引擎 (state_vector, event_log, gate, tribunal 等)
tests/
  test_helper.bash    # load_lib 解析器 + 断言辅助
  smoke.bats          # 基础设施冒烟
  unit/               # 29 个 Python 单元测试
  integration/        # 47+ bats 集成测试
  _lib/               # bash helpers (skill.bash, deps-subagent.bash 等)
docs/adr/             # ADR-0000 模板, ADR-0001~0012 (12 个)
```

## 关键约定 (容易踩坑)

### 状态文件 (`.rddf/state/`, gitignored)

| 文件 | 用途 |
|------|------|
| `.rddf/state/arch-handoff.json` | arch→plan 交接 |
| `.rddf/state/plan-handoff.json` | plan→ship 交接 |
| `.rddf/state/deps-analysis.json` | 依赖分析结果 |
| `.rddf/state/deps-candidates.json` | deps 候选列表 |
| `.rddf/state/handoff.json` | spec→ship 软交接 |
| `.rddf/state/index.md` | change 索引 |

`.rddf/state/` 和 `.rddf/wt/` 全部被 `.gitignore` 排除；`.rddf/plans/` 随 git 版本控制。
**`proposal-suggestions.md` 在项目根目录，随 git 版本控制** (JSON 列表格式)。

### Skill 文件规范

- 每个 `skills/*.md` 以 YAML frontmatter 开头 (`---` 分隔)
- frontmatter 包含: `name`, `version`, `evolved-from`, `metadata.author`, `license`, `compatibility`
- `version: X.Y` semver 风格, `evolved-from: "..."` 记录重构历史来源
- frontmatter 是**只读的** —— metadata/version/name 不可修改

### 分支与 Worktree

- Branch 命名: `openspec/<change-name>`
- Worktree 路径: `.rddf/wt/<change-name>`
- Plan 文件路径: `.rddf/plans/<name>.md`
- Worktree 创建前必须 commit (COMMIT GATE) —— `git worktree add` 需要看到 artifacts
- 创建 worktree 时必须在 `master` (或 default) 分支
- `find_default_branch()` (在 `skills/_lib/worktree.sh`) 动态检测 main/master/develop，不要硬编码
- `main_repo_root()` 用 `git rev-parse --git-common-dir` 获取主仓库路径(worktree 安全)

### ADR 规范

- 命名: `ADR-NNNN-<kebab-slug>.md` (NNNN 4位零填充, 0000 保留为模板)
- 状态生命周期: `待定 → 已采纳 → 已弃用 / 已替代为 ADR-NNNN`
- 引用格式: `ADR-NNN §N.M` (例如 `ADR-0003 §2.1`)
- 模板: `docs/adr/ADR-0000-template.md` (不要给真实 ADR 分配 0000)
- 最新 ADR 编号: 查看 `docs/adr/` 目录中的最大编号

### 测试约定

- bats `@test` 命名格式: `"模块: 场景描述"`
- 每个 `.bats` 文件顶部 `load test_helper`
- `load_lib <name>` 按序查找: `tests/_lib/<name>.bash` → `skills/_lib/<name>.sh` → `tests/_lib/<name>.sh`
- 辅助断言: `assert_file_exists`, `assert_file_contains`, `assert_cmd_succeeds`
- Python 测试在 `tests/unit/` 用 pytest 运行
- 集成 bats 测试在 `tests/integration/`
- CI 有**恒真断言门控**: `grep -rn "assert.*or True\|assert True" tests/` 会直接 CI FAIL

### 归档流程 (`guide-ship` Phase 3)

`guide-ship` 归档时自动检测模式：
- **worktree 模式**: 调用 `skills/_lib/archive.sh` 的 `archive_change <name>` 执行 full 归档
- **轻量模式**: 直接在 main repo merge branch + 删除分支 + `openspec archive`

`archive_change` 内部步骤:
1. 找到 worktree path + default branch
2. 检查 worktree 分支是否有新提交
3. 切换到 default branch
4. 按是否分叉选择 `--ff-only` 或 `--no-ff` merge
5. 验证 merge 结果 (HEAD 变化或分支是祖先)
6. `openspec archive <name> --yes`
7. 清理 worktree + branch (`-D` 需环境变量 `FORCE_BRANCH_DELETE=yes`)

### Python 后端 (v2.0)

`skills/_lib/` 包含完整的 Python 模块:
- `loop_engine.py` — Loop 引擎入口
- `state_vector.py` — 原子化状态持久化 (JSON schema + checksum)
- `event_log.py` — 追加式事件日志 (10K 事件 < 100ms 查询)
- `gate.py` — 插件式质量门控 (error/warning)
- `tribunal.py` — 多 agent 交叉验证 + 加权评分
- `sanitizer.py` — API key/密码/敏感路径脱敏 (< 10ms/次)
- `memory.py` — LoopMemory 历史追踪 + 中断恢复
- `session_manager.py` — Session 协调器 + 父子 session 追踪
- `agents.py` — Planner/Executor/Verifier 协调
- `detectors.py` / `actions.py` — Loop 引擎检测器与动作 (8 内置检测器, 7 内置动作)
- 配置: `config.py`, `defaults.py`, `schemas/`, `plugins/`

## 常见陷阱

1. **git worktree list branch 在第 3 列** —— `awk '$3 ~ /openspec\//'` (不是 `$2`, 不是 `$4`)
2. **`git show HEAD:<path>` 要求 repo 相对路径** — 先用 `cd $PROJECT_ROOT`，再用相对 glob
3. **`main_repo_root()` vs `git rev-parse --show-toplevel`** — worktree 内必须用 `--git-common-dir`，否则返回 worktree 根目录
4. **`find_default_branch()` 不从 worktree 的 HEAD 推断** — 优先读 `refs/remotes/origin/HEAD`，防 self-merge
5. **Execute 只写 `tasks.md`** — 不写 state 文件, guide 从 tasks.md 同步进度
6. **execute 阶段不 commit/push** — plan 明确 commit 留到 archive 阶段
7. **`guide-arch` 不调用 `guide-plan`** — arch-done 后用户必须手动切换
8. **`guide-spec` 是别名** — 内部按序调用 `guide-arch` → `guide-plan`，v3.0 会移除
9. **Loop 引擎 max_iterations: 100, max_retries: 3** — 配置在 `interaction` 模式配置中
10. **proposal-suggestions.md 格式为 JSON** — 用 `json.load()` 解析, 不用 grep (避免 description 字段误匹配)

## 前置条件

- `openspec` CLI v1.3.1+
- `git` 2.25+
- `cmake` 3.16+
- `bats-core` 1.10+ (可选, 用于跑测试)
- Python 3.11+ (v2.0 Loop 引擎 + 单元测试)