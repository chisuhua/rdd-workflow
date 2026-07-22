---
SCOPE: shared
STATUS: PROPOSED
---

## Context

仓库当前结构：

```text
skills/
├── *.md                  # 13 个 skill 描述文件
├── loop_engine.py         # 当前不被 install.sh 复制
└── _lib/                  # 49 个 Python 模块 + 4 个子目录
    ├── *.py               # 内部 cross-import: from skills._lib.X import Y
    ├── __pycache__/        # 不应分发
    ├── plugins/            # dev-only 扩展点（只有 README.md）
    ├── schedulers/         # 已有 __init__.py；dev-only
    └── schemas/            # 7 个 JSON Schema，运行时校验需要
```

`_lib/` 当前在仓库内能正常 import 是因为 `tests/conftest.py` 把项目根加进了 `sys.path`。一旦 `install.sh` / `INSTALL.md` 复制 `_lib` 到目标项目的 `.opencode/skills/rdd-workflow/skills/_lib/`，**绝对导入路径 `skills._lib.X` 不会工作**——除非 `skills/` 在目标项目里也是合法 Python package（需要 `__init__.py`）。

依赖链关键点：

```text
skills/feature.md         (depends-on: [iteration, deps_output])
   └─→ skills._lib.iteration.py
   └─→ skills._lib.deps_output.py

skills/rddf-session.md    (depends-on: [rddf_session])
   └─→ skills._lib.rddf_session.py
         └─→ skills._lib.lock.FileLock
         └─→ skills._lib.state_vector.StateVector
         └─→ skills._lib.event_log.EventLog
         └─→ skills._lib.event_types.{Event, EventType, Severity}

skills/loop_engine.py
   └─→ skills._lib.{state_vector, event_log, event_types, loop_state, config}
```

49 个 `.py` 文件中约有 20 个被 `feature.md` / `rddf-session.md` / `loop_engine.py` / 各 `guide-*.md` 间接依赖。这些是 npm 用户必须拿到的。

## Goals / Non-Goals

**Goals:**
- 让 npm-installed 用户拿到 `skills/_lib/` 的运行时所需 Python 模块
- 通过新增 `__init__.py` 让绝对导入在目标项目里可解析
- 排除 dev-only 子目录（`__pycache__`、`plugins`、`schedulers`）
- 修复 `INSTALL.md` 三处描述/字符串漂移（description 12/13、fallback 11、L115 vs L118）
- 加反漂移测试锁定分发契约

**Non-Goals:**
- 不修改 `_lib/*.py` 实际内容
- 不重构 `loop_engine.py` 导入路径
- 不构建 wheel / sdist
- 不动 `package.json::skills[]`（那是 `sync-workflow-contracts` 的范围）

## Decisions

### Decision 1: `__init__.py` 是否新增

**选 A：新增两个空 `__init__.py`**（`skills/` 和 `skills/_lib/`）。

Rationale:
- 49 个 `_lib/*.py` 用 `from skills._lib.X import Y` 形式互相 import，**强制要求 `skills/` 是合法 Python package**
- 空 `__init__.py` 是 Python 3.3+ namespace package 的替代，但显式 marker 更稳定、跨工具兼容（mypy、pytest 插件、IDE 索引）
- 仓库内现有 `tests/conftest.py` 已经把项目根加 `sys.path`，新增 `__init__.py` 不会破坏现有测试
- 风险：极低（一个 0 字节文件）

### Decision 2: 安装范围

**选 C：全量 `.py` + `schemas/`，排除 `__pycache__` / `plugins` / `schedulers`**。

Rationale:
- 全量 `.py` 简单一致，避免"白名单依赖"漂移
- `schemas/`（7 个 JSON Schema）必须随 `_lib/` 一起分发，否则 `feature_view.py` 等模块的 `jsonschema.validate()` 会失败
- `__pycache__` 必须排除——它在 build host 是污染源
- `plugins/` 只有 README.md，本身不含可分发代码（dev 扩展点）
- `schedulers/` 已有 `__init__.py`，但内容是 LoopEngine 调度器（v3 候选，未启用）—— 当前不参与生产 skill 运行时

具体 glob（参考实现，写入 install.sh / INSTALL.md）：

```bash
# 复制 _lib/*.py 和 schemas/*.json，排除三个子目录
find "$PACKAGE_DIR/skills/_lib" \
    -type d \( -name __pycache__ -o -name plugins -o -name schedulers \) -prune \
    -o -type f \( -name '*.py' -o -name '*.json' \) -print | \
while read -r src; do
    rel="${src#$PACKAGE_DIR/}"
    mkdir -p "$TARGET_DIR/.opencode/skills/rdd-workflow/$(dirname "$rel")"
    cp -f "$src" "$TARGET_DIR/.opencode/skills/rdd-workflow/$rel"
done
```

### Decision 3: fallback 字符串维护方式

**选 B：用 `python3 -c` 动态推导，不再硬编码**。

Rationale:
- 当前 L115 fallback 硬编码 11 个 skill 名，每次上游加 skill 都要同步改 INSTALL.md——已知 drift 源
- 改为：如果源 `package.json` 存在，用 `python3 -c "import json; print(','.join(json.load(open(...))['skills']))"` 推导；否则保持 fallback 字符串但加注释说明它是"最低保底列表"
- 这样未来加 skill 不需要改 INSTALL.md
- 风险：python3 必须可用（已在前置检查中确认）

### Decision 4: INSTALL.md description

**选 B：改为计数式描述，不再列举名字**。

Rationale:
- 当前 L3 写"全部 13 个子技能（INSTALL/.../feature）"——括号内只有 12 个名字，缺 `rddf-session`
- 列举名字本身脆弱：未来加 skill 必然漂移
- 改为类似："全部 13 个子技能，详见 `skills/` 目录与 `package.json::skills[]`"
- 反漂移测试可断言 description 包含"13 个子技能"数字（从 `len(package.json::skills[])` 推导）

## Alternatives Considered

### Alt 1: 把 `_lib/*.py` 改成相对导入（`from .lock import FileLock`）

**Rejected**:
- 涉及 ~30+ 个文件的批量修改
- 需要每个子目录都有 `__init__.py`（`plugins/` / `schedulers/` 也要）
- 引入相对导入与绝对导入的混合风格
- 远超本 change scope

### Alt 2: 用 `pip install` 路径，把 `_lib/` 打成 wheel

**Rejected**:
- 需要新增 `pyproject.toml` 或 `setup.py`
- 引入 build 步骤，复杂度大幅上升
- 仓库目前没有 Python package metadata（`setup.py` 不存在）
- 与 INSTALL skill 的"零依赖"哲学冲突

### Alt 3: 不分发 `_lib`，让 npm 用户自己跑 `python3 -m pip install rdd-workflow`

**Rejected**:
- `rdd-workflow` 目前不是 PyPI 包（只是 npm 元仓）
- 引入 PyPI 发布节奏，受 release cycle 约束
- npm install + pip install 是两套分发渠道，文档/测试要维护两套
- 用户体验差（要装两次）

## Risks / Trade-offs

| # | Risk | Mitigation |
|---|------|------------|
| 1 | 新增 `__init__.py` 后 import 路径解析行为变化 | 仓库内测试必须保留 `tests/conftest.py` 加 sys.path；CI 必须 zero regression |
| 2 | `__pycache__` 被错误分发（979KB 含 2 个 __pycache__） | install.sh 用 `find -name __pycache__ -prune` 显式排除 |
| 3 | `plugins/schedulers` 被错误分发 | install.sh 显式排除这两个目录名 |
| 4 | dev-only `.py` 模块（`arch_quality_gate.py`、`validate_report.py`）被 npm 用户拿到 | 可接受——不依赖外部资源，体积 <50KB；如需 slim package 加 `.npmignore`（后续 change） |
| 5 | 引入 `__init__.py` 改变 Python 解析顺序（namespace package vs regular package） | 显式 `__init__.py` 优先级高于 implicit namespace；即使原仓库隐式依赖 namespace package，显式 marker 是更强契约 |
| 6 | 反漂移测试 `test_install_lib_distribution.bats` 误报 | 用稳定锚点（`grep -F` 完整字符串 + `--` 终止选项）+ `find -prune` 显式排除子目录 |

## Verification

```bash
# 单元测试：关键 _lib 模块导入
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_install_lib_distribution.py -v
# Expected: 全部通过

# bats 测试：安装路径断言
bats tests/integration/test_install_lib_distribution.bats
# Expected: 全部通过

# 现有测试零回归
python3 -m pytest tests/unit/ -q --tb=short
python3 -m pytest tests/integration/ -q --tb=short
bats tests/smoke.bats

# OpenSpec 校验
openspec validate fix-install-lib-distribution --strict
# Expected: 'Change fix-install-lib-distribution is valid'

# CI 质量门控
! grep -rn 'assert.*or True\|assert True' tests/
# Expected: exit 0
```

## Open Questions

- **Q**: 是否需要在 npm 端加 `.npmignore` 进一步 slim package？
  **A**: 不在 v1 scope。当前 ~1MB 对 npm 用户是合理代价；后续如需 slim 包可单独 change。
- **Q**: `__init__.py` 加完后，`tests/conftest.py` 加 sys.path 还需要吗？
  **A**: 需要保留（`tests/conftest.py` 是测试侧的事，不影响目标项目）。
- **Q**: `skills/` 顶层也加 `__init__.py` 会和 `tests/conftest.py` 加 sys.path 重复吗？
  **A**: 不会冲突。`sys.path` 加项目根让 `import skills` 可解析；`__init__.py` 让 `skills` 是合法 package。两者各管一端。

## Out of Scope (Explicit)

- ❌ 修改 `skills/*.md` 中的 prose（除 `INSTALL.md` 的 description + 安装步骤段）
- ❌ 修改 `skills/_lib/*.py` 实际内容（除新增两个 `__init__.py` 空文件）
- ❌ 重构 `loop_engine.py` 绝对导入为相对导入
- ❌ 构建 wheel / sdist
- ❌ 修改 `package.json::skills[]`（那是 `sync-workflow-contracts` Decision 1 的范围）
- ❌ 创建 worktree / branch / commit / push