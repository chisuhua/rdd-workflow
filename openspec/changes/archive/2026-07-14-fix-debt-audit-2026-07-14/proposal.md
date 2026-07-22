---
SCOPE: shared
STATUS: PROPOSED
---

## Why

2026-07-14 对 rdd-workflow 仓库 (116 文件 / 1416 节点 / 7766 行代码) 进行全量架构/技术/代码债务审计,发现 **22 项债务** (3 P0 / 6 P1 / 8 P2 / 5 P3)。pytest 545/545 + bats 7/7 全绿,但以下问题形成系统性风险:

### P0 立即修复 (数据完整性影响)

**漂移 1 — ADR-0013 文档引用指向错误 ADR (7 处)**

v2.0.2 将 `ADR-0013-incremental-skeleton-planning.md` 重编号为 `ADR-0020`,但 `skills/_lib/arch_quality_gate.py` 的所有 docstring (5 处) + `skills/guide-arch.md` + `skills/propose.md` 仍然引用 "ADR-0013 §3.X"。磁盘上的 ADR-0013 现在是 `extract-scan-state`,与质量门控语义完全无关。正确的 ADR 应该是 ADR-0018 (`arch-quality-gate`)。

影响: `arch_quality_gate.py` 是架构质量门控的参考实现,其文档是下游消费者理解门控语义的**唯一来源**。文档指向错误 ADR 会误导所有基于此实现开发的门控逻辑。

**漂移 2 — `propose.md` 在 stub `state.sh` 上 source (运行时静默失败风险)**

`skills/propose.md:52-55` source `skills/_lib/state.sh` 以获取 `safe_python_json` / `safe_python_yaml`,但该文件已被缩减为 3 行 stub (注释声明 "No production callers were found")。bash 的 `source` 在文件存在但无函数定义时**不报错**,但后续函数调用会无提示失败,propose 流程可能以部分损坏状态继续。

影响: 运行时静默失败,无错误信息,状态可能不一致。

**漂移 3 — `tests/smoke.bats` 硬编码 10 个 skill,不保护新增 skill**

smoke.bats:19 声明 "all 10 skill files exist" 并显式检查 10 个文件名。AGENTS.md 和 README 说 13 个 skill,磁盘上也是 13 个。stale 测试不会 fail (因为抽查的文件都在),但新增的 `feature`, `rddf-session`, `rdd-workflow-writing-plans` 不在保护范围内。

### P1 本迭代 (架构/测试债务)

**漂移 4 — `rddf` 1505 行单文件 monolith,核心 CLI 0 测试覆盖**

`rddf` 是 27 个函数的 bash 单体,知识图谱显示 `rdd-workflow-rddf` community (36 nodes) 与库模块零耦合 — 已退化成独立 CLI。`rddf_archive`, `rddf_help`, `rddf_cleanup`, `rddf_init` 等核心入口函数全部在 `untested_hotspots` 列表中 (degree 29-53)。

**漂移 5 — Python 3.14 弃用警告 82 个**

`skills/loop_engine.py:83` 在 `_SAFE_NODES` 白名单中使用 `ast.Num`, `ast.Str`, `ast.NameConstant`,这些已被 Python 3.12 弃用,Python 3.14 将移除 (硬错误)。

**漂移 6 — `.rddf/state/phase-gate-report.md` 语义僵尸**

`roadmap.md:675` 写入,`scan-state.sh:117` 仅检测存在性作为 trigger,内容从未被消费。ADR-0006 标注为 "死代码风险",但未修复。

**漂移 7 — 测试热力图极度不均**

- `tests/unit/test_iteration.py` 888 行 测试 `iteration.py` 614 行 (1.45:1)
- `tests/unit/test_feature_view.py` 430 行 测试 `feature_view.py` 363 行 (1.18:1)
- `rddf` 1505 行, `archive.sh` 356 行, `scan-state.sh` 245 行 → **零 bats 测试**

### P2 下迭代 (代码质量/DRY)

- `sync_state.py` 仅测试使用 (0 生产 caller) — YAGNI
- `atomic_write` 在 3 个文件重复实现 (state_vector / iteration / rddf_session)
- `git show "HEAD:openspec/..."` 探针重复 6 处,`is_change_committed()` 仍未抽出
- `RddfSessionCoordinator` 402 行 god class (6 subcommand + JSON I/O + lock + binding)

## What Changes

### Wave 1 — P0 立即修复 (3 项)

1. **ADR-0013 → ADR-0018 替换**: `arch_quality_gate.py` docstring 5 处 + `guide-arch.md` + `propose.md` 共 7 处替换,同步更新 AGENTS.md ADR 引用说明
2. **propose.md 移除 source state.sh**: 将 `safe_python_json` / `safe_python_yaml` 调用替换为 inline `python3 -c "import json..."` 模式
3. **smoke.bats 动态化**: 替换硬编码 10 路径为 `for f in skills/*.md; do [ -f "$f" ]` 模式,确保未来新增 skill 自动进入烟雾测试范围

### Wave 2 — P1 本迭代 (4 项)

4. **Python 3.14 ast 迁移**: `loop_engine.py` 替换 ast.Num/Str/NameConstant/Bytes → ast.Constant
5. **phase-gate-report.md 死代码清理**: 删除 `roadmap.md:675` 写入逻辑 + `scan-state.sh:117` 检测逻辑,或补充 reader
6. **rddf 拆分决策 + 基础覆盖**: 做出 "独立 CLI 或集成" 决策;为核心 shell 代码 (`rddf`, `archive.sh`, `scan-state.sh`) 添加 bats 基础测试
7. **文档漂移同步**: 修复 AGENTS.md / README 中过时的 skill 数 (12→13)、test_readme 中 hardcoded 测试文件列表等

### Wave 3 — P2 下迭代 (4 项)

8. **sync_state.py 清理**: 移除非生产的 v1.x → v2.0 遗留迁移层
9. **atomic_write 统一**: 抽 `skills/_lib/atomic_write.py` 公共 helper
10. **RddfSessionCoordinator 拆分**: 按职责分离 Persistence / Lock / Commands
11. **审计闭环**: 审计本 change 的完成度 (post-wave-3 "修复合规性审计")

## Impact

- **受影响文件**: `skills/_lib/arch_quality_gate.py`, `skills/_lib/loop_engine.py`, `skills/propose.md`, `skills/guide-arch.md`, `skills/roadmap.md`, `rddf`, `skills/_lib/scan-state.sh`, `tests/smoke.bats`, `AGENTS.md`, `README.md`, `tests/README.md`, 新增 `tests/` bats/pytest 测试
- **风险等级**: Low — 大部分是文档修复 + 局部代码改动;Python 3.14 迁移是安全的替换;shell 测试是纯新增
- **测试影响**: 新增 bats 测试覆盖 rddf/archive.sh/scan-state.sh; 更新 smoke.bats; 修复 82 个 DeprecationWarning