---
SCOPE: shared
STATUS: PROPOSED
---

## Why

当前 `install.sh` 与 `skills/INSTALL.md` 只分发 `skills/*.md`，**不分发** `skills/_lib/*.py`：

```text
install.sh:32           → cp -f "$PACKAGE_DIR/skills/"*.md
skills/INSTALL.md:100   → cp -f "$PACKAGE_DIR/skills/"*.md
```

但 `skills/feature.md` 和 `skills/rddf-session.md` 的 frontmatter 声明了 `depends-on`：

```yaml
# skills/feature.md:9
depends-on: [iteration, deps_output]

# skills/rddf-session.md:9
depends-on: [rddf_session]
```

`iteration` / `deps_output` / `rddf_session` 都位于 `skills/_lib/*.py`。**结果是：通过 npm 或 INSTALL 安装的用户拿到了 skill 描述文件，但拿不到运行时所需的 Python 模块**——skill 在运行时是坏的。

更糟的是 `sync-workflow-contracts` 的 Decision 3（design.md:74-87）准备把 `feature` 与 `rddf-session` 从 src-only 改为 npm 发布面（Option A），但在 `_lib` 不分发的前提下做 A-flip 等于向 npm 用户**虚假承诺**一个跑不起来的 API。这是上一轮 Oracle 第二次咨询里明确指出的盲点。

> 注：本 change 与 `sync-workflow-contracts` 在前序讨论中曾用 "Decision 1" / "Decision 3" 互相指代，是命名错位——两边都是指 `package.json::skills[]` 是否补 `feature` + `rddf-session` 的同一决策点。`sync-workflow-contracts` 内部编号是 Decision 3。

另外两个相关 drift（顺带在本 change 修）：

1. `skills/_lib/` 完全没有 `__init__.py`，但内部代码用 `from skills._lib.X import Y`（绝对导入）。当前能在仓库内跑是因为 `tests/conftest.py` 把项目根加进了 `sys.path`。一旦 `_lib` 被复制到目标项目，**导入会断**——`skills/` 必须是合法的 Python package。
2. `skills/INSTALL.md:3` description 写了"全部 13 个子技能"但括号内只列了 12 个名字（缺 `rddf-session`）；L115 fallback 字符串硬编码 11 个 skill 名（缺 `feature` 和 `rddf-session`）。三处描述对不上。

## What Changes

| 文件 | 变更类型 | 职责 |
|---|---|---|
| `skills/__init__.py` | **新建**（空文件） | Python package marker，让 `from skills._lib.X import Y` 在目标项目里能解析 |
| `skills/_lib/__init__.py` | **新建**（空文件） | Python sub-package marker |
| `install.sh:32` | 修改 | 在复制 `.md` 之后，再递归复制 `skills/_lib/` 的 `.py` 和 `schemas/*.json`；显式排除 `__pycache__` / `plugins` / `schedulers` 三个子目录 |
| `skills/INSTALL.md:100` | 修改 | 镜像 `install.sh` 行为；并加 Python sys.path 提示段 |
| `skills/INSTALL.md:115` | 修改 | fallback 字符串更新为 13 个 skill 名字（或改为动态推导） |
| `skills/INSTALL.md:118` | 修改 | else 分支 fallback 同步更新 |
| `skills/INSTALL.md:3` | 修改 | description 改为计数式描述，避免列举名字带来的脆弱性 |
| `tests/integration/test_install_lib_distribution.bats` | **新建** | 5 个断言：`_lib/*.py` 在安装路径、`__init__.py` 存在、fallback 字符串、description 计数、排除 `__pycache__` |
| `tests/unit/test_install_lib_distribution.py` | **新建** | Python 单元测试：`import skills._lib.feature_view` 等关键模块都能 import |
| `openspec/specs/state-management/spec.md` | 修改 | MODIFIED Requirements 锁定 lib 分发契约（不变量 + 排除规则） |

### 关键决策（详细在 design.md）

| 决策点 | 选项 | 推荐 |
|---|---|---|
| `skills/_lib/__init__.py` 是否新增 | A: 新增（建立合法 package）/ B: 不动（依赖运行时 hack） | **A**——绝对导入需要 |
| 安装时复制 `_lib/` 的范围 | A: 全量 / B: 只复制依赖链上必须的 / C: 全量但排除 `plugins` `schedulers` | **C**——简单一致；`plugins/schedulers` 是 dev/扩展点，不应该进 npm |
| fallback 字符串维护方式 | A: 硬编码 13 个名字 / B: 用 `python3 -c` 动态推导 / C: 完全去掉 fallback | **B**——消除硬编码漂移 |
| INSTALL.md description 的 13 个 skill 名字列表 | A: 补 `rddf-session` 进括号 / B: 改为计数式描述 | **B**——消除列举脆弱性 |

## Impact

- **影响文件**:
  - `install.sh`（+~10 行）
  - `skills/INSTALL.md`（+~25 行：L100 glob 扩展 + L115/118 fallback + L3 description 改写 + sys.path 提示）
  - 新增 2 个 `__init__.py`（共 0 行实际内容，仅文件存在）
  - 新增 2 个测试文件（~150 LOC）
  - `openspec/specs/state-management/spec.md` 修改 ~30 行
- **破坏性变更**: 无。所有改动都是分发路径增量，不影响运行时已部署行为。
- **API 变更**: 无。
- **外部依赖**: 无新增。纯 Python 标准库。
- **跨仓影响**: 无。
- **运行时影响**: 零。
- **分发体积**: +979KB（`skills/_lib/` 总大小）。从 ~70KB 涨到 ~1MB。对 npm 用户是合理代价——这些模块当前已经随仓库走。

## Acceptance Criteria

- [x] `skills/__init__.py` 存在且为空
- [x] `skills/_lib/__init__.py` 存在且为空
- [x] `install.sh` 在复制 `.md` 后递归复制 `skills/_lib/*.py` 和 `skills/_lib/schemas/*.json`
- [x] `install.sh` 排除 `__pycache__/` / `plugins/` / `schedulers/` 三个子目录
- [x] `skills/INSTALL.md` L100 镜像 `install.sh` 行为
- [x] `skills/INSTALL.md` L115 fallback 字符串列全 13 个 skill 名（或动态推导）
- [x] `skills/INSTALL.md` L118 else 分支 fallback 列全 13 个 skill 名
- [x] `skills/INSTALL.md` L3 description 改为计数式，不再列举名字
- [x] `tests/integration/test_install_lib_distribution.bats` 新增且通过
- [x] `tests/unit/test_install_lib_distribution.py` 新增且通过（关键 `_lib` 模块可 import）
- [x] 既有 pytest + bats zero regression
- [x] `openspec validate fix-install-lib-distribution --strict` PASS
- [x] CI 恒真断言 grep `! grep -rn 'assert.*or True|assert True' tests/` 退出 0
- [x] 本 change 落地后，`sync-workflow-contracts` Decision 1 翻 A 成为安全操作

## Risk

| # | Risk | Mitigation |
|---|------|------------|
| 1 | 新增 `__init__.py` 后原有相对导入路径失效 | 仓库内的 `tests/conftest.py` 把项目根加 `sys.path`，绝对导入 `from skills._lib.X import Y` 已经成立；新增 `__init__.py` 只是让目标项目也能解析 |
| 2 | `__pycache__` 被错误分发 | install.sh 用 `find ... -name '__pycache__' -prune -o ...` 显式排除 |
| 3 | `plugins/schedulers` 是 dev-only 工具，被错误分发 | install.sh 显式排除；生产 skill 运行时不需要它们 |
| 4 | 部分 `_lib/*.py` 是 dev-only（`arch_quality_gate.py`, `validate_report.py`），不应该进 npm | 当前决定全量包含——dev-only 模块不依赖外部资源，体积可接受。后续如需 slim package，可加 `.npmignore` |
| 5 | 修改 `skills/INSTALL.md` 多处可能引入新 drift | Decision 改为动态推导 fallback，description 改为计数式，**从源头消除**硬编码漂移 |
| 6 | 仓库内 `__pycache__` 目录被 git 跟踪 | 确认 `.gitignore` 已含 `__pycache__/`；本 change 不创建新 `__pycache__` 跟踪 |

## Supersession / Dependencies

- **不 supersede** 任何现有 change
- **依赖**:
  - `add-rddf-session`（rddf-session 已经按 src-only ship；本 change 补齐其 `_lib` 分发）
  - `feature-management`（feature skill 同理）
- **解锁**:
  - `sync-workflow-contracts` Decision 1 翻 A（feature + rddf-session 可以诚实进入 npm 发布面）
  - 任何未来需要在 npm 上跑 `_lib` 模块的 skill

## 不做什么（显式边界）

- ❌ 不修改 `skills/*.md` 中的 prose（除 `INSTALL.md` 的 description 与安装步骤）
- ❌ 不修改 `skills/_lib/*.py` 的内容（仅新增 `__init__.py`，不碰其他模块）
- ❌ 不重构 `loop_engine.py` 的绝对导入为相对导入
- ❌ 不构建 wheel / sdist（只修 install.sh + INSTALL.md）
- ❌ 不创建 worktree / branch / commit / push