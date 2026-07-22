# ADR-0021: Phase 2 Per-Skill Helper Migration Strategy

> **v3.0.0 note**: Originally authored as "spec-workflow". Renamed to "rdd-workflow" in v3.0.0 (2026-07-22). See ADR-0023.


> **状态**: 已采纳（v2.0.8 archive 后切换）
> **日期**: 2026-07-17
> **作者**: sisyphus (with Metis hostile review of `skills-reorg-phase2-single-skeleton`)
> **evolved-from**: ADR-0003 §2.1（三阶段架构）, ADR-0013（scan-state 提取,确立"单 skill helper 隔离"原则）

## Context

`skills-reorg-phase1-skeleton` 已完成（archive 2026-07-17-...）：每个 skill 有了自己的 `skills/<name>/{SKILL.md, scripts/, references/}` 骨架，`INSTALL.md` 改为递归复制。但所有 90+ helper 文件仍平铺在 `skills/_lib/`。

`skills-reorg-phase2-single-skill` 计划将 45 个"只被 1 个 skill 引用"的 helper 从 `skills/_lib/` 移入各自 skill 的 `scripts/`。Metis 审查（plan → report, 18 项问题）发现计划存在 4 个**强耦合**的架构级决策未做：

1. **B1**: 计划声称"`from skills._lib.feature_cli import X` 移走后仍然有效"——这是错的。`scripts/` 缺 `__init__.py`、且 `from skills._lib.feature_cli` 在 `feature_cli.py` 移到 `feature/scripts/` 后立即 ModuleNotFoundError。74+ 处 Python imports 失效。
2. **N1**: 所有 `skills/*/scripts/` 当前完全为空，无 `__init__.py`。即使修复 imports，没有 `__init__.py` Python 也不识别 `scripts` 为 package。
3. **N2**: `feature_*.sh` 4 个文件用 `_SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")` 然后 `PYTHONPATH="$_SCRIPT_DIR/.."`，移到 `scripts/` 后 `..` 指向 `skills/<skill>/` 而不是 `skills/`，import 路径错误。
4. **N3**: **自相矛盾**：`rddf_session_hooks.sh`（计划留 _lib/ 共享）有 3 行 `from skills._lib.rddf_session import ...`，而 `rddf_session.py`（计划移到 `rddf-session/scripts/`）正是被它引用的。要么 `rddf_session.py` 也留 _lib/，要么 `rddf_session_hooks.sh` 也移走——不能各走各的。
5. **B8**: 121 处 prose 引用（如 `# heavy lifting in skills/_lib/ship_plan.sh`）无差别 sed 会破坏 git blame + 30+ 处 ADR 历史快照的准确性。

4 个决策彼此耦合：B1 选 A 还是 B 决定 N1 是否需要 11 个 `__init__.py`；N3 决定 `rddf_session.py` 是单 skill 还是共享；B8 决定 prose 是否动 git 历史。

**架构依据**:
- ADR-0003 §2.1 — 三阶段架构：`skills/<stage>/<skill>/` 是推荐布局
- ADR-0013 — scan-state 提取：确立了"单 skill helper 移出 _lib/"的先例
- ADR-0017 §3 — rddf-session 跨 OpenCode session 持久化

## Decision

我们采用 **4 个联合决策**（每个都不能单独做）：

### Decision 1 (B1 + N1 + N2): Python imports 用 **Option A — `__init__.py` + 路径重写**

**给每个被迁移 helper 的 skill 的 `scripts/` 添加 `__init__.py`**（11 个 skill × 1 = 11 个空文件），并将所有 Python import 从：

```python
from skills._lib.feature_cli import render_summary
```

改为：

```python
from skills.feature.scripts.feature_cli import render_summary
```

**`feature_*.sh` 的 PYTHONPATH 同时重算**（N2 解决）：从 `PYTHONPATH="$_SCRIPT_DIR/.."` 改为 `PYTHONPATH="$_SCRIPT_DIR/../.."`，确保 `_SCRIPT_DIR/../.. = skills/`，Python `from skills.X.scripts.Y import Z` 仍能解析。

**测试文件中的 import 同样改写**（覆盖 17 个 .py + 多个 .bats 中的 heredoc Python）。

**为什么不选 B (lazy re-export)**:
- B 需要在 `skills/_lib/__init__.py` 里手动维护 11+ 个 re-export，**每次 Phase 2+3+4 迁移新文件都得改** `__init__.py`，引入隐藏耦合
- B 让"代码在哪里"和"import 路径"脱节，违反 DRY + 增加认知负担
- A 是更彻底的"per-skill 自包含"，与 Phase 1 的"per-skill 目录骨架"目标一致

### Decision 2 (N3): `rddf_session.py` 与 `rddf_session_hooks.sh` **同时移到 `rddf-session/scripts/`**

**理由**：
- `rddf_session_hooks.sh` 在 3 个 skill（guide-arch、guide-plan、guide-ship）`source`，但它只是**薄包装**，核心逻辑都在 `rddf_session.py`
- 把 `hooks.sh` 留 `_lib/` 但 `rddf_session.py` 移走 → import 必然失效（已验证）
- 反之留 `rddf_session.py` 在 `_lib/` → 它就不再是"单 skill"，违反 Phase 2 前提
- **统一移到 `rddf-session/scripts/`**：hooks.sh 的 3 处 `source` 改为 `../rddf-session/scripts/rddf_session_hooks.sh`（注意 `..` 跳到 `skills/`）

**影响**:
- 3 个 skill 的 `SKILL.md` 各加 1 处 `source "$(dirname "${BASH_SOURCE[0]}:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"`
- 3 处 import 已隐含在 Decision 1 的 import 重写中（改用 `from skills.rddf_session.scripts.rddf_session import ...`）

### Decision 3 (B8): **Prose 引用策略 = SKILL.md 更新 + ADR 保留**

**`SKILL.md` 中的 prose**（如 `# heavy lifting in skills/_lib/ship_plan.sh`）→ **更新为新路径**（`scripts/ship_plan.sh`）。理由：SKILL.md 是当前实现文档，必须反映当前位置。

**`docs/adr/ADR-*.md` 和 `docs/superpowers/{plans,specs,reports}/*.md`** → **保留**（不更新）。理由：
- ADR 不可变（ADR-0000 状态生命周期规则）
- 历史快照保留 git blame 价值
- 30+ 处 ADR 引用描述的是**过去的**实现位置，反映决策演进

**实现**：`phase2_path_migrator.py` 工具接受 `--update-prose-scope` 参数（默认 `skills/`），只更新 scope 内的 prose，scope 外（如 `docs/adr/`）保持原样。

### Decision 4 (N7): **INSTALL.md 改造推迟到所有 move 完成后**

原计划 Task 1（改 INSTALL.md）在 Task 2-5（移文件）之前 → 中间态 INSTALL.md 期望的 `scripts/` 内容还没就位，下游 install 会得到空目录。

**改为**：INSTALL.md 改造放到 Task 7（commit 前），所有文件移到 `scripts/` 后再改 install copy 逻辑。中间态用 `skills/_lib/` 临时 alias 兼容（旧 install 仍能找到文件），迁移完成 + INSTALL.md 改造后再删 alias。

### 影响范围

- **In Scope**: `skills/_lib/*.py` (11 个), `skills/<skill>/scripts/` (新增 11 个), 13 SKILL.md 的 source 行 + prose, INSTALL.md (Task 7), 115+ 测试文件, Python imports 74+ 处
- **Out Scope**: `docs/adr/*` (ADR 不变), `docs/superpowers/*` (历史快照不变), `skills/_lib/*.sh` 中跨 skill 共享文件（state.sh/worktree.sh/archive.sh/rddf_session_hooks.sh 等——但 rddf_session_hooks.sh 例外，按 Decision 2 移走）

### 备选方案

| 备选 | 理由 |
|------|------|
| **(A) `__init__.py` + 路径重写（采纳）** | 与 Phase 1 per-skill 骨架一致；import 与代码位置同源；无隐藏耦合 |
| **(B) `_lib/__init__.py` lazy re-export（拒绝）** | 引入 `_lib/__init__.py` ↔ scripts/ 的同步负担；每次 Phase 2+3+4 都得改 _lib/__init__；违反 DRY |
| **(C) 全局 `from skills._lib import X` 不变，文件**物理位置**移到 scripts/（拒绝）** | Python 不会自动从 scripts/ 找到 _lib/X；必须有 symlink 或 sys.path hack，破坏 Phase 1 已确立的 per-skill 自包含 |
| **(D) rddf_session 留 _lib/（拒绝）** | 违反 Phase 2 前提"单 skill helper"；hooks.sh 与 .py 必然共生 |
| **(E) hooks.sh 也算共享（拒绝）** | 表面看合理，但 hooks.sh 本质是 rddf_session 的薄包装；强行共享会越迁越多，最终导致 rddf_session 整个留下 |

## Consequences

### 正面

- Phase 2 完成后，`skills/` 真正实现"per-skill 自包含"：每个 skill 的 helpers 与 SKILL.md 同目录，认知负担最小
- Python imports 与代码位置同源，新人能 `grep "from skills.X.scripts"` 立即定位代码
- 30+ ADR 历史快照不被破坏（git blame 完整）
- INSTALL.md 中间态不破坏下游项目

### 负面 / 风险

- 74+ Python imports 需重写（机械但量大），必须用 `phase2_path_migrator.py` 工具而非手改
- 11 个 `__init__.py` 新增文件（空文件）— 视觉上有点冗余，但 Python 包管理必需
- `rddf-session/scripts/rddf_session_hooks.sh` 移到 rddf-session 后，3 个 skill 的 SKILL.md 各加 `../rddf-session/scripts/...` 跨目录 source — 增加路径复杂度
- INSTALL.md Task 7 推迟需要小心：所有 move 完成后才动 install，不能中途 commit

### 后续待办

- [ ] 实现 `tools/phase2_path_migrator.py`（Decision 1+3 的工具支撑）— 见 `openspec/changes/skills-reorg-phase2-single-skill/tasks.md` Step 2
- [ ] 新增 `tests/integration/test_phase2_layout.bats`（锁定新布局）— 见 tasks.md Step 5
- [ ] 新增 `tests/integration/test_phase2_install_full.bats`（真实跑 INSTALL.md）— 见 tasks.md Step 5
- [ ] Phase 3 (core lib 重组) 复用本 ADR 的 Decision 1 模式
- [ ] Phase 4 (thin) 时检查本 ADR 的 Decision 4 INSTALL.md alias 是否仍兼容，必要时删

## References

- `openspec/changes/skills-reorg-phase1-skeleton/`（已完成，前置）
- `openspec/changes/archive/2026-07-17-skills-reorg-phase1-skeleton/tasks.md`（Phase 1 5 个 surprise 列表）
- `docs/adr/ADR-0003-three-phase-architecture.md` §2.1 — 三阶段架构推荐布局
- `docs/adr/ADR-0013-extract-scan-state.md` — 单 skill helper 提取的先例
- `docs/adr/ADR-0017-rddf-session.md` — rddf-session 跨 session 持久化（hooks.sh 的存在依据）
- `skills/_lib/rddf_session_hooks.sh:59,115,164` — N3 自相矛盾的源头
- `tests/_lib/test_scan_state.bats:32,46,59,74,86` — B6 7 处 source 引用
- `docs/proposal-suggestions-format.md` — ADR 引用格式 `ADR-NNN §N.M`