---
SCOPE: shared
STATUS: PROPOSED
---

## Context

spec-workflow v2.0.2 已完成核心架构迁移 (arch → plan → ship 三阶段) + rddf-session binding + iteration lifecycle + arch quality gate + change alignment。本 change 是 **2026-07-14 全量债务审计**的修复执行。

审计基于 code-review-graph 结构分析 (1416 节点 / 10533 边) + 手动 grep/read 三方交叉验证,发现 22 项债务。本 change 覆盖其中 **11 项立即修复 + 本迭代修复**,其余 P3 观察项留待后续。

### 真值分层

修复过程中,以下层级为准:

| 优先级 | Surface | 角色 |
|--------|---------|------|
| 1 (权威) | `skills/_lib/*.py` / `rddf` | **生产代码 — 文档必须对齐到它** |
| 2 | `tests/` | 保护网 — 修复后新增测试 | 
| 3 | `docs/adr/ADR-*.md` | 决策源 — ADR-0018 定义质量门控语义 |
| 4 | `AGENTS.md` / `README.md` | 文档面 — 修复后必须与 code 一致 |

## Goals / Non-Goals

**Goals:**

- Pre-Wave: 修复元债务 (`npm test` 缺口) + 基线确认
- Wave 1: 5 P0 修复 — ADR docstring + state.sh 恢复 + smoke.bats + 文档 + **sync_state 删除** (从 P2 提升)
- Wave 2: 5 P1 修复 — Python 3.14 ast + phase-gate-report 彻底删除(含测试) + rddf 测试 + CI 更新 + 文档同步
- Wave 3: 3 P2 改进 — atomic_write 统一(5 处) + god class 拆分 + 审计闭环(含 sync_state 文档清理)
- 每个 Wave 完成后,CI 全绿 (pytest 545+ + 新增 bats 全通过)
- 修复后 `grep -rn "ADR-0013" skills/` 只有 `extract-scan-state` 语义的引用

**Non-Goals:**

- 不改变任何运行时 workflow 行为
- 不修改 v1.x archived change
- 不新增 production 功能的 spec (债务修复不需要新 spec)
- P3 观察项 (命名漂移 `guide-spec` 残留 3 处, 版本号 `generatedBy` → `evolved-from`) 留待后续

## Decisions

### Decision 1: ADR-0013 引用修正 — 分两路映射

v2.0.2 重编号后,`ADR-0013` 语义分裂,需要按上下文分两路修正:

| 引用位置 | 实际语义 | 正确 ADR |
|---------|---------|----------|
| `arch_quality_gate.py` 5 处 docstring + `guide-arch.md:870` | 架构质量门控 (ghost ref / gap / placeholder / handoff) | **ADR-0018** |
| `propose.md:463` | skeleton branching (debt/fix- 前缀自动 skeleton 模式) | **ADR-0020** |

**选择**: 分两路 — `arch_quality_gate.py` + `guide-arch.md:870` → ADR-0018; `propose.md:463` → ADR-0020。

**理由**:
- Metis 审查发现 `propose.md:463` 上下文是 "v2.0.1+: Name-pattern skeleton branching",对应 ADR-0020 incremental-skeleton-planning,而非 ADR-0018 质量门控
- 不能一刀切,必须按语义分路修正
- 同步更新 `tests/unit/test_arch_quality_gate.py:3` 和 `tests/unit/test_gate.py:122` 中的 ADR-0013 引用

### Decision 2: state.sh 恢复 helper 函数

当前 `state.sh` 是 3 行 stub,但 `propose.md` 和 `roadmap.md` 实际调用 `safe_python_json` / `safe_python_yaml`。同时有回归测试 `test_json_safety.bats` 和 `test_roadmap_skill.bats` 锁定此行为。

| 选项 | 做法 | 利弊 |
|------|------|------|
| A: 恢复 state.sh | 把 safe_python_json/safe_python_yaml 重新加回 state.sh | 保持与回归测试一致,消除运行时静默失败 |
| B: 改用 inline | propose.md + roadmap.md 中直接 inline python3 | 遵循 stub 决策,但需大幅改写测试 |

**选择**: **A — 恢复 `state.sh` 的 helper 函数**。

**理由**:
- 运行时调用是**真实的** (propose.md 和 roadmap.md 实际依赖这些函数),stub 的 "no production callers" 声明错误
- 回归测试 `test_json_safety.bats` (CI 内) 和 `test_roadmap_skill.bats` 锁定此行为,inline 会破坏保护网
- 恢复 helper 是**最小 diff**,不需要改写测试

### Decision 3: smoke.bats 动态化

当前 smoke.bats 硬编码 10 个文件名。动态化有两种方式:

| 选项 | 做法 | 利弊 |
|------|------|------|
| A: glob + count | `count=$(ls skills/*.md \| wc -l); [ "$count" -ge 10 ]` | 简单,但阈值需要手动维护 |
| B: 显式 glob 检查 | `for f in skills/*.md; do [ -f "$f" ]; done` | 自动覆盖所有 skill,无需维护阈值 |

**选择**: **B — 显式 glob 检查**。

**理由**:
- 选项 B 零维护开销 — 新增 skill 自动进入检查范围
- 选项 A 的阈值 (ge 10) 需要未来手动更新 (13→14 时)
- 选项 B 的行为等同于"如果 skills/ 下有 .md 文件,就验证它们存在且可读"

**同时保留**: 将原有 10 文件显式检查保留为单独的 `@test "all v1.x baseline skill files still exist"`,确保向后兼容。

### Decision 4: rddf 拆分 vs 测试

`rddf` 1505 行 monolith 是 CLI 入口,包含 ~27 个函数。完全拆分 (`rddf.d/` 目录) 是 4-6 小时的复杂重构,不宜与 P0 修复耦合。

**选择**: Wave 2 先做出 **"独立 CLI vs 集成" 的显式决策** + 添加 bats 基础测试;完整拆分留待后续 change。

**决策标准**:
- 如果 `rddf` 被视为 spec-workflow 的一部分 → Wave 2 只加测试,后续 change 做拆分
- 如果 `rddf` 被视为独立 CLI → Wave 2 将它移出到独立仓库

**默认假设**: `rddf` 是 spec-workflow CLI 入口,保持集成,本 change 只加测试。

### Decision 5: sync_state.py 的去留

`sync_state.py` 提供 v1.x → v2.0 状态文件迁移。0 生产 caller,仅测试使用。

**选择**: **删除 — 含文档引用清理**。

**理由**:
- v2.0 已稳定运行 > 3 周,不再需要 v1.x → v2.0 迁移工具
- 如果有未来 v2→v3 迁移需求,可以写新的迁移工具
- Metis 审查发现 `docs/v2-api-reference.md` 和 `docs/migration/v1-to-v2.md` 仍有 sync_state API 引用,必须同步清理

### Decision 6: phase-gate-report 彻底删除 (含测试更新)

现状是半死不活: `roadmap.md:675` 写 `phase-gate-report.md`(无点),`scan-state.sh:117` 读 `.phase-gate-report.md`(有点),`guide.md` 未接入。但 CI 内 `test_gate_report.bats` 和 `test_guide_scan.bats` 锁定此行为。

| 选项 | 做法 |
|------|------|
| A: 修复 wiring | 统一 dot 约定 + guide.md 接入 + 保留测试 |
| B: 彻底删除 | 删除 writer/reader + 更新相关测试 |

**选择**: **B — 彻底删除**。

**理由**:
- 审计和 ADR-0006 均标记为死代码风险,从未被真正消费
- 修复 wiring (让 guide.md 接入) 会产生新的运行时行为,超出本 change "不改 workflow 行为" 的约束
- 删除涉及的测试更新:
  - `tests/integration/test_gate_report.bats` — 删除或改为 assert absence
  - `tests/integration/test_guide_scan.bats` P1-3 — 改为 assert scan-state.sh 不再检查 phase-gate-report
  - `tests/integration/test_roadmap_skill.bats` — 移除 gate-report command 断言
  - `tests/_lib/test_skill.bats` — 更新 roadmap commands count (6→5)
  - `docs/adr/ADR-0006-state-vector-event-log.md` — 移除 "死代码风险" 标注

### Decision 7: 新增 bats 测试加入 CI

Wave 2 新增的 bats 测试文件如果不加入 `.github/workflows/test.yml` 的显式列表,CI 不会执行它们。

**选择**: **允许修改 CI**,将新增测试文件显式加入 static 列表。

**理由**:
- 测试不进 CI 等于没写 — CI 是唯一保护网
- `npm test` (bats tests/) 只跑顶层 smoke.bats,无法自动发现子目录新文件
- CI 用显式枚举列表,新增文件必须手动加入

---

## Metis 审查记录

本 change 经 Metis (Pre-Planning Consultant) 审查,发现 7 处结构性缺陷并修正:
- `propose.md:463` ADR 映射 → ADR-0020 (原计划误归为 ADR-0018)
- `roadmap.md` state.sh 依赖遗漏 → 纳入修复,决策从 inline 改为恢复 helper
- `phase-gate-report` 与现有测试冲突 → 增加 Decision 6 彻底删除含测试更新
- `atomic_write` 遗漏 2 处 → 合并范围从 3 处扩大到 5 处
- 新增测试不进 CI → Decision 7 允许修改 CI
- `bats tests/` 只跑 smoke → 所有 acceptance 改用具体文件路径
- sync_state 文档引用遗漏 → 纳入 Decision 5

## Oracle 审查记录

本 change 经 Oracle (High-IQ Architecture Review) 审查,发现 3 个深层问题并修正:

1. **点号之殇**: phase-gate-report writer 写 `phase-gate-report.md`(无点),reader 读 `.phase-gate-report.md`(有点)—**是不同文件**,机制从未工作过。T33 的测试锁住了一个死胎。
2. **npm test 元债务**: `bats tests/` 不递归,50+ integration bats 只在 CI 跑,开发者循环中不可见。→ 增加 Pre-Wave Task 0.1 修复 `package.json` test 脚本。
3. **D5 执行顺序**: sync_state 删除必须**先于** D7 CI 更新,否则 CI 出现 ImportError。→ D5 从 Wave 3 提升到 Wave 1。同时 `test_gate.py:122,134` 和 `test_arch_quality_gate.py:3` 也需要 ADR 更新 (→ 扩展 D1 scope),`test_state.bats` 需要与 D2 同步更新。

## Risks / Mitigations

| 风险 | 缓解 |
|------|------|
| ADR 替换后仍有遗漏 | `grep -rn "ADR-0013" skills/ tests/unit/` 扫描,质量门控语义全改 ADR-0018,skeleton 语义改 ADR-0020 |
| state.sh helper 恢复引入新代码 | 使用标准 `python3 -c "import json..."` 包装的 try/except 模式,与 `test_json_safety.bats` 预期一致 |
| ast.Constant 替换影响 AST 安全沙箱 | `loop_engine.py` 的 `_SAFE_NODES` 已有测试覆盖 (`test_loop_engine.py`),替换后用 `python3 -W error::DeprecationWarning` 验证 0 warning |
| phase-gate-report 删除打破 CI | 同步更新 5 个被测文件 (见 Decision 6);CI static 列表中的 `test_gate_report.bats` 改为 assert absence |
| smoke.bats 动态化漏检 corrupt skill | `test_skill_metadata_consistency.bats` 已覆盖 frontmatter 完整性,smoke.bats 只做存在性检查 |
| 新 bats 测试不进 CI | Decision 7: 允许修改 `.github/workflows/test.yml`,新文件显式加入 static 列表 |
| `bats tests/` 只跑 smoke,不是全量 | 每个 task acceptance 使用具体文件路径 (如 `bats tests/integration/test_rddf_cli.bats`),不用 `bats tests/` |
| atomic_write 合并遗漏 validate_report/de d eps_out put  | 合并前用 `grep -n "_atomic_write" skills/_lib/*.py` 全量扫描,确保覆盖 5 处 |
| sync_state 删除后文档仍有引用 | Decision 5 明确同步清理 `docs/v2-api-reference.md` + `docs/migration/v1-to-v2.md` |