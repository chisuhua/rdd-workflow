# fix-rddf-init-broken-layout

> **状态**: Proposed
> **日期**: 2026-08-05
> **来源**: PTX-EMU 全 rddf 子命令验证实战
> **影响范围**: rdd-workflow 包布局、`rddf init` 子命令、12 个 rddf 子命令的 PYTHONPATH 解析、所有已 init 的项目

**优先级**: P1 | **阶段**: infra-setup | **分类**: infra-setup
**类型**: refactor + bugfix

---

## 架构依据

- **ADR-0003 三阶段架构**：每个阶段有明确的 owner/artifact；`init` 是 ship 阶段入口命令，必须能从**任意源码目录** init 到目标项目（PTX-EMU 这类 nested rdd-workflow 项目、CI runner、临时 worktree 都依赖此能力）。
- **RDDF-0001（已批准）**：揭示"代码与文档/布局不一致"是 rdd-workflow 的历史债务根因（连字符目录 + 相对导入双断裂）；本提案沿用同一思路（`init_cmd.py` 假设 vs 实际包布局错配）。
- **PTX-EMU 验证证据**（2026-08-05）：
  1. `RDDF_PROJECT_ROOT=/home/ubuntu/.agents/skills/rdd-workflow rddf init /tmp/x` 报
     ```
     ❌ init: 找不到源文件: _lib, package.json, skills/cli/rddf.sh
        当前 RDDF_PROJECT_ROOT=/workspace/project/PTX-EMU
     ```
     → **Bug A**：`RDDF_PROJECT_ROOT` 被吞（`__main__.py:154` 覆盖在 init_cmd 读取之前）。
  2. 即使从 `~/.agents/skills/rdd-workflow/` 直接跑 init，仍报
     ```
     ❌ init: 找不到源文件: _lib
        当前 RDDF_PROJECT_ROOT=/workspace/project/rdd-workflow
     ```
     → **Bug B**：`init_cmd.py:_INSTALL_SOURCES` 期望 `_lib/` 在顶层，但实际在 `skills/_lib/`。

## 范围

### In Scope

1. **移动 `skills/_lib/` 到顶层 `_lib/`**（用 `git mv` 保留历史）
2. **修复 `__main__.py:154`**：从 `os.environ["X"] = Y` 改为 `os.environ.setdefault("X", Y)`，保护用户传入的 `RDDF_PROJECT_ROOT`
3. **更新所有引用 `skills._lib` 的 Python 导入**：`from skills._lib import X` → `from _lib import X`（或保留兼容 shim）
4. **更新 `install.sh` 的 PYTHONPATH 计算**（从 `PACKAGE_DIR` 改成同源位置 — `_lib/` 现已在 `PACKAGE_DIR` 下而非 `PACKAGE_DIR/skills` 下）
5. **验证 `rddf.sh` shim 的 `PACKAGE_DIR` 解析**（基于 `BASH_SOURCE` 自动适配，确认新布局下仍正确）
6. **更新 `package.json` 的 `main` 字段**（如有指向 `skills/INSTALL.md`）
7. **更新 `pyrightconfig.json`、`pyproject.toml` 中所有 `_lib` 路径引用**
8. **提供向后兼容 shim**（`skills/_lib/__init__.py` re-export from `_lib`），让已 init 的旧项目仍能 `from skills._lib import X`
9. **新增 bats 集成测试** `tests/integration/test_init_smoke.bats`：覆盖场景 1-3
10. **更新 `CHANGELOG.md`**：添加 breaking-change 条目

### Out Scope

- 不重写 `init_cmd.py` 的逻辑结构（仅调整路径常量与 copytree 源）
- 不动 12 个 rddf 子命令（archive/cleanup/dashboard/deps/feature/guide/init/monitor/sessions/status/validate/version）的业务代码
- 不动 `improvements/`、`docs/`、`openspec/`、`tests/`（除新增 init 测试）
- 不重命名 skills 子目录（保留连字符 `guide-arch` 等）
- 不动 `install.sh` 的全局安装主流程（仅调整 PYTHONPATH 计算）
- 不动 `.pth` 文件创建逻辑（install.sh 中）

## 关键场景

```gherkin
GIVEN 用户在任意目录下希望 init rdd-workflow 到目标项目
WHEN  执行 `RDDF_PROJECT_ROOT=/path/to/source rddf init /target/project`
THEN  1) RDDF_PROJECT_ROOT 被尊重（不被覆盖为 git root）
      2) _INSTALL_SOURCES 在源路径下都存在
      3) /target/project/.opencode/skills/rdd-workflow/ 包含 skills/ + _lib/ + package.json + rddf.sh
      4) 从目标项目运行 `rddf --help` 能列出全部 12 个子命令
AND   exit code = 0
```

```gherkin
GIVEN rdd-workflow 包已 init 到目标项目（位于 /tmp/init-target）
WHEN  从 /tmp/init-target 运行 `rddf version`
THEN  输出 "rddf v3.0.0 — rdd-workflow CLI"
AND   exit code = 0
```

```gherkin
GIVEN 现有全局安装 ~/.agents/skills/rdd-workflow/（旧布局，skills/_lib/）
WHEN  用户重跑 install.sh --global 升级到新版本
THEN  全局安装可用
AND   12 个 rddf 子命令行为不变（仅 init 路径修复）
AND   旧项目的 `from skills._lib import X` 通过兼容 shim 仍能工作
```

```gherkin
GIVEN PTX-EMU（已 arch-done + plan-done，~150 行 proposal-approved.md）
WHEN  在 PTX-EMU 跑 `rddf guide / dashboard / status / feature / sessions / monitor / validate / cleanup`
THEN  12 个子命令输出与本次验证（2026-08-05）的快照完全一致
AND   仅 init 子命令从"失败"变为"成功"
```

## 技术约束

### MUST

- MUST 用 `git mv` 而非 `mv` 移动 `skills/_lib/` → `_lib/`，保留 git 历史
- MUST NOT 改变 12 个 rddf 子命令的对外 API/CLI 接口（`rddf <subcmd> [args...]` 不变）
- MUST NOT 破坏 `~/.agents/skills/rdd-workflow/` 已部署的全局安装的 11 个非-init 子命令
- MUST 在每个移动/重命名的文件相关的 commit message 引用本提案（`fix(init): flatten package layout per fix-rddf-init-broken-layout`）
- MUST 保留 `__pycache__/` 在新位置（不要删除，由 Python 自动重建）
- MUST 提供 `skills/_lib/__init__.py` 向后兼容 shim，至少 6 个月内不删除
- MUST 在 PR 中包含从 PTX-EMU 跑 `RDDF_PROJECT_ROOT=~/.agents/skills/rdd-workflow rddf init /tmp/x` 的成功日志

### MUST NOT

- MUST NOT 删除 `skills/_lib/` 旧位置（保留为空 shim）
- MUST NOT 改变 `package.json` 的 `"name"`、`"version"`、`"author"` 字段
- MUST NOT 改变任何 ADR 编号或内容（仅可能新增 ADR-00XX-init-layout-decision.md）
- MUST NOT 合并本提案到已有 `proposal-approved.md` 行（独立 PR）

### SHOULD

- SHOULD 添加 bats 集成测试 `tests/integration/test_init_smoke.bats` 覆盖场景 1-3
- SHOULD 在 `CHANGELOG.md` 添加 breaking-change 条目（格式：`### Breaking — package layout: skills/_lib → _lib`）
- SHOULD 在新 `_lib/` 添加 `__init__.py` 说明路径变更
- SHOULD 更新 `README.md` 的"安装"章节反映新路径
- SHOULD 更新 `docs/architecture/` 中描述包布局的文档（如有）

### 验证门禁

- 12 个 rddf 子命令的输出快照（除 init）与 2026-08-05 验证基线 100% 一致
- `bats tests/integration/test_init_smoke.bats` 全绿
- `pytest tests/` 全绿（不允许 skip）
- `openspec validate` 在 rdd-workflow 项目内通过（修复前当前 exit 1）

## 验收标准

| # | 标准 | 验证方法 | 可量化 |
|---|---|---|---|
| 1 | `RDDF_PROJECT_ROOT=~/.agents/skills/rdd-workflow rddf init /tmp/x` 成功 | exit 0 + `/tmp/x/.opencode/skills/rdd-workflow/` 含 skills/ + _lib/ + package.json + rddf.sh | exit code + 4 文件存在 |
| 2 | init 后 `/tmp/x/.opencode/skills/rdd-workflow/_lib/cli/init_cmd.py` 可访问 | `python3 -c "import sys; sys.path.insert(0,'/tmp/x/.opencode/skills/rdd-workflow'); from _lib.cli import init_cmd"` exit 0 | python import 成功 |
| 3 | 从 PTX-EMU 跑 `rddf guide/dashboard/version/feature/status/sessions/monitor/validate/cleanup` 行为不变 | 输出 diff 为空（除 init） | 0 行 diff |
| 4 | `bats tests/integration/test_init_smoke.bats` 新增并通过 | CI green | N tests, 0 failures |
| 5 | `pytest tests/` 全部通过 | CI green | N passed, 0 failed |
| 6 | `openspec validate` 在 rdd-workflow 项目内 exit 0 | `openspec validate` | exit 0 |
| 7 | `CHANGELOG.md` 含 breaking-change 条目 | grep "skills/_lib → _lib" | 1+ 命中 |
| 8 | `git log --oneline` 显示本提案引用 | grep "fix-rddf-init-broken-layout" | 1+ commit |
| 9 | 旧项目 `from skills._lib import X` 仍可用（向后兼容） | 在 PTX-EMU 中执行 `python3 -c "from skills._lib import X"` | exit 0 |

---

## 附录 A — 受影响文件清单（预估）

| 文件 | 当前 | 修改后 | 类型 |
|---|---|---|---|
| `skills/_lib/` | 存在 | shim（re-export） | 删除/替换 |
| `_lib/` | 不存在 | 新顶层（git mv 源） | 移动 |
| `skills/_lib/cli/__main__.py:154` | `os.environ["RDDF_PROJECT_ROOT"] = project_root` | `os.environ.setdefault(...)` | 编辑 |
| `skills/_lib/cli/init_cmd.py:26` | `_INSTALL_SOURCES = [..., "_lib", ...]` | `_INSTALL_SOURCES = [..., "skills", ...]`（不变），copytree 路径调整 | 编辑 |
| `install.sh` | PYTHONPATH 计算含 `skills/_lib` | PYTHONPATH 含 `_lib` | 编辑 |
| `package.json` | `"main": "skills/INSTALL.md"` | 不变（INSTALL.md 仍在 skills/ 下） | 无需改 |
| `pyrightconfig.json` | 路径引用 | 同步更新 | 编辑 |
| `pyproject.toml` | 路径引用 | 同步更新 | 编辑 |
| `README.md` | 安装章节路径 | 同步更新 | 编辑 |
| `CHANGELOG.md` | 缺 breaking-change | 添加条目 | 编辑 |
| `tests/integration/test_init_smoke.bats` | 不存在 | 新增 | 创建 |

## 附录 B — 相关提案

- **RDDF-0001**（已批准）：修复 `rddf-session` 跨运行时导入路径断裂（连字符目录 + 相对导入双断裂）— 本提案沿用同一思路（代码与布局不一致）
- **fix-lsp-dash-bridge**（已批准）：LSP dash 桥接修复 — 同类"基础设施修复"模式
- **fix-rddf-session-owner-stability**（已批准）：rddf-session 所有者稳定性 — 同类"状态/环境隔离"修复