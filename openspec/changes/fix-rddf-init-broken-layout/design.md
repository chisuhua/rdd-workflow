# fix-rddf-init-broken-layout — Design

> Schema: spec-driven
> Created: 2026-08-05
> See: `proposal.md` for motivation, scope and acceptance criteria.

## Context

rdd-workflow 当前的包布局把共享 Python 模块放在 `skills/_lib/` 下，导致两个相互关联的问题：

1. **`rddf init` 命令路径错配**（Bug B）：`init_cmd.py:_INSTALL_SOURCES` 期望在源码根找到 `_lib/`，但实际位置在 `skills/_lib/`。即使从 `~/.agents/skills/rdd-workflow/` 直接运行 init，初始化到 `/tmp/x` 也会报"找不到源文件: _lib"。
2. **`RDDF_PROJECT_ROOT` 环境变量被吞**（Bug A）：`__main__.py:154` 在读取子命令之前用 `os.environ["RDDF_PROJECT_ROOT"] = project_root` 覆盖了用户传入的值，导致 nested rdd-workflow 项目（如 PTX-EMU）和 CI runner 无法在任意源目录下 init。

历史背景（RDDF-0001 已批准）：rdd-workflow 已发现"代码与文档/布局不一致"是核心债务根因（连字符目录 + 相对导入双断裂）。本提案沿用同一思路（`init_cmd.py` 假设 vs 实际包布局错配）。

**Stakeholders**: rdd-workflow 自身维护者、PTX-EMU 等嵌套项目维护者、CI runner 使用者。

## Goals / Non-Goals

**Goals:**
- 让 `RDDF_PROJECT_ROOT=/path/to/source rddf init /target` 从**任意源码目录**都能成功（PTX-EMU、CI、临时 worktree）
- 修复 `__main__.py:154` 的 `setdefault` 语义，保护用户传入的环境变量
- 把 `skills/_lib/` 移到顶层 `_lib/`（用 `git mv` 保留历史）
- 提供 `skills/_lib/__init__.py` 向后兼容 shim，至少 6 个月内不删除
- 保留 12 个 rddf 子命令的对外 CLI 接口不变
- 保留 `~/.agents/skills/rdd-workflow/` 已部署全局安装的 11 个非-init 子命令行为不变

**Non-Goals:**
- 不重写 `init_cmd.py` 的逻辑结构（仅调整路径常量与 copytree 源）
- 不动 12 个 rddf 子命令的业务代码（archive/cleanup/dashboard/deps/feature/guide/init/monitor/sessions/status/validate/version）
- 不重命名 skills 子目录（保留连字符 `guide-arch` 等）
- 不动 `install.sh` 的全局安装主流程（仅调整 PYTHONPATH 计算）
- 不动 `.pth` 文件创建逻辑
- 不改变 `package.json` 的 `name`/`version`/`author` 字段
- 不改变任何 ADR 编号或内容

## Decisions

### Decision 1: `git mv skills/_lib/ → _lib/` 而非符号链接

**Rationale**: 用 `git mv` 而非 `mv` 保留 git blame/history；符号链接会破坏 Python 的 `__pycache__` 缓存语义、IDE 索引、import 解析的一致性。

**Alternatives considered**:
- 软链接 `skills/_lib → ../_lib` → 拒绝：破坏 Python 缓存 + 跨平台兼容性差
- 复制 `skills/_lib`（双份维护）→ 拒绝：违反 DRY
- 仅修复 `init_cmd.py` 路径（不改物理布局）→ 部分缓解但不解决根本问题

### Decision 2: 保留 `skills/_lib/` 作为空 shim，向后兼容

**Rationale**: 已 init 的项目（PTX-EMU 等）会从 `.opencode/skills/rdd-workflow/skills/_lib/` 导入。直接删除会破坏所有已部署的项目。

**Implementation**:
- `skills/_lib/__init__.py` 用 `from _lib import *` re-export
- `skills/_lib/` 下的所有子目录转为 `__init__.py` re-export shim
- shim 至少保留 6 个月，后续在独立提案中决定是否删除

**Alternatives considered**:
- 完全删除旧路径（硬破坏）→ 拒绝：破坏 PTX-EMU 等已部署项目
- 仅在 README 标注迁移指南 → 拒绝：用户不会主动改代码

### Decision 3: `os.environ.setdefault()` 替代 `os.environ[...] = ...`

**Rationale**: `setdefault` 仅在用户未设置时才填默认值，符合"尊重用户输入"的语义；直接赋值会覆盖。

**Implementation** (`__main__.py:154`):
```python
# Before:
os.environ["RDDF_PROJECT_ROOT"] = project_root
# After:
os.environ.setdefault("RDDF_PROJECT_ROOT", project_root)
```

**Alternatives considered**:
- 删除环境变量赋值，让 init_cmd 内部用 fallback → 拒绝：增加 init_cmd 复杂度
- 用 argparse 参数替代环境变量 → 部分缓解但破坏现有用户习惯

### Decision 4: `rddf.sh` shim 的 `PACKAGE_DIR` 自动适配

**Rationale**: `rddf.sh` 通过 `BASH_SOURCE` 解析包根。新布局下 `skills/` 仍在原位，所以 `PACKAGE_DIR` 解析不变。但 `install.sh` 的 PYTHONPATH 需要从 `PACKAGE_DIR/skills/_lib` 改为 `PACKAGE_DIR/_lib`。

**Implementation**:
- `rddf.sh`: 无需改动（基于 `BASH_SOURCE[0]` 自动适配）
- `install.sh`: 更新 PYTHONPATH 计算（`${PACKAGE_DIR}/skills/_lib` → `${PACKAGE_DIR}/_lib`）
- `pyrightconfig.json`/`pyproject.toml`: 同步更新 `_lib` 路径引用

### Decision 5: 独立 PR，不合并到已有 `proposal-approved.md` 行

**Rationale**: 本提案修改包布局（breaking change），影响 26+ ADR、48+ 提案、12 个 rddf 子命令、57 个 Python 单测。属于独立可发布单元，必须独立 PR。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 已 init 项目（PTX-EMU）的 `from skills._lib import X` 在新布局下失效 | `skills/_lib/__init__.py` re-export shim 保留 6 个月 |
| `git mv` 期间 working tree 中有未提交修改 → mv 失败 | 提案 MUST: 在执行 `git mv` 前确认 `git status` 干净（ship 阶段 worktree 内执行即可） |
| Python `__pycache__` 在新位置触发误判 → 测试假阳性 | 提案 MUST: 保留 `__pycache__/`，由 Python 自动重建 |
| `install.sh` 的 `.pth` 文件路径错误导致全局安装失效 | ship 阶段验证：装完后跑 `rddf version` + `from _lib import X` |
| 向后兼容 shim 增加维护负担 | shim 是 1 行 re-export，零业务逻辑；6 个月后单独提案评估删除 |
| 26 个 ADR 引用 `skills/_lib` 路径的文档失效 | 提案 MUST NOT 改变 ADR 编号/内容，仅在 CHANGELOG.md 标注 breaking change |
| 12 个 rddf 子命令（除 init）的回归 | ship 阶段强制跑全量 bats（smoke + static + git-worktree）+ pytest |

## Migration Plan

### Deployment Steps
1. 在 worktree 内执行 `git mv skills/_lib/ _lib/`（保留 history）
2. 创建 `skills/_lib/__init__.py` re-export shim
3. 编辑 `__main__.py:154`：`os.environ[...] = ...` → `os.environ.setdefault(...)`
4. 编辑 `init_cmd.py::_INSTALL_SOURCES`：路径常量对齐新布局
5. 编辑 `install.sh`：PYTHONPATH 从 `skills/_lib` 改为 `_lib`
6. 同步更新 `pyrightconfig.json`/`pyproject.toml`
7. 新增 `tests/integration/test_init_smoke.bats` 覆盖场景 1-3
8. 更新 `CHANGELOG.md` 添加 breaking-change 条目

### Rollback Strategy
- shim 在 6 个月内保留 → 任何已 init 项目回滚到旧版本无破坏
- git revert 单 PR 可恢复所有改动（一次 commit 聚合所有相关修改）
- 旧版本 `~/.agents/skills/rdd-workflow/` 全局安装继续可用，无需更新

### Validation Gates
- `pytest tests/` 全绿（不允许 skip）
- `bats tests/integration/test_init_smoke.bats` 全绿
- 从 PTX-EMU 跑 11 个非-init 子命令输出零差异
- `openspec validate` 在 rdd-workflow 项目内 exit 0（修复前当前 exit 1）
- PR 中附 `RDDF_PROJECT_ROOT=~/.agents/skills/rdd-workflow rddf init /tmp/x` 成功日志

## Open Questions

无。所有范围/约束/验证标准均已在 proposal 中明确。