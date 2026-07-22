# ADR-0018: 架构质量门 — arch 阶段的定性检查

> **v3.0.0 note**: Originally authored as "spec-workflow". Renamed to "rdd-workflow" in v3.0.0 (2026-07-22). See ADR-0023.


> **状态**: ✅ 已采纳
> **日期**: 2026-07-10
> **决策者**: sisyphus
> **依据**: ADR-0003 (三阶段架构), ADR-0007 (门控机制), ADR-0016 (arch discovery contract)
> **版本目标**: v2.0.2

## Context

`guide-arch` Phase 5 (`arch-done`) 当前的硬门控只验证**结构性存在**：

| 门控 | 类型 | 检查内容 |
|---|---|---|
| `adr_exists` | error | ADR 目录有 ≥ 1 个文件 |
| `roadmap_defined` | error | `roadmap.md` 存在 |
| `gap_analysis_complete` | warning | **永远是 `(True, "warning")` 的 no-op** |

这导致 arch 阶段产出可能存在以下质量问题而**门控完全感知不到**：

1. **文档不对齐**：roadmap.md 或 gap-analysis 引用 `ADR-NNNN`，但对应 ADR 文件不存在（"幽灵引用"）
2. **架构债务未记录**：gap-analysis 表格中存在 `严重程度=高 / 优先级=P0 / 关联 change=(待补充)` 的未解决行
3. **ADR 仍是模板占位符**：复制模板后未填充内容，含 `<待补充>` / `<TBD>` / `NNNN` 等占位符
4. **handoff 不可指导下游**：`.arch-handoff.json` 的 `current_phase="default"` 或 `discovered.adr_dir.found=false`，导致 `guide-plan` Phase 0 入口消费失败

参考 ADR-0007 的插件机制 (`register_gate_check()`) 与 ADR-0016 的 `.arch-handoff.json` v1 schema，我们具备**复用现有基础设施**添加 warning 级检查的条件。

**关键约束**：ADR-0003 §"人工介入匹配"把 arch 标为"高人工介入"，自动门控不应过度否决架构师的判断。

## Decision

我们引入 **`arch_quality_gate`** —— arch-done 阶段的 4 个 warning 级定性检查，默认不阻塞，`STRICT_ARCH_GATE=yes` 环境变量升级为 error（仅 CI 启用）。

### 检查项

| Check 名称 | 检查内容 | 失败信号 |
|---|---|---|
| `arch_alignment` | roadmap.md + gap-analysis 中引用的 ADR 全部存在 | 任一引用为幽灵 |
| `arch_debt_recorded` | gap-analysis 表格无 `高/P0/(待补充)` 未解决行 | 存在未解决 P0/high 债务 |
| `adr_no_placeholders` | ADR 文件不含模板占位符（`<待补充>` `<TBD>` `<TODO>` `<kebab-slug>` `NNNN` 等） | 任一 ADR 是模板拷贝 |
| `arch_handoff_actionable` | `.arch-handoff.json` `current_phase` 非 `default`、`discovered.adr_dir.found=true`、`version=1` | handoff 携带字段不可消费 |

### 严重级别矩阵

| 环境 | `adr_exists` | `roadmap_defined` | 4 个质量检查 |
|---|---|---|---|
| 本地开发 | error | error | warning（不阻塞） |
| `STRICT_ARCH_GATE=yes` (CI) | error | error | error（升级） |

升级机制通过 `strict_wrap(condition)` 装饰器实现，不修改核心 `gate.py` 的 verify 逻辑。

### 影响范围

- **In Scope**:
  - `skills/_lib/arch_quality_gate.py` 新增（~210 行）
  - `skills/_lib/gate.py` `_DEFAULT_CHECKS["arch_done"]` 注册 4 个新 Check
  - `skills/guide-arch.md` Phase 5 增加质量门钩子，写入 `.rddf/state/.arch-quality-report.json`
  - `.github/workflows/test.yml` 新增 "Arch quality gate (strict mode)" 步骤
  - `tests/unit/test_arch_quality_gate.py` 25 个单元测试
  - `tests/unit/test_gate.py` 增加 1 个注册验证测试
- **Out Scope**:
  - 不修改 ADR-0007 门控机制的核心架构
  - 不修改 `.arch-handoff.json` schema（保留 v1，向后兼容）
  - 不引入新的状态字段（仅新增可选的 `.arch-quality-report.json` 视图文件）

### 备选方案

| 备选 | 理由 |
|---|---|
| 4 个检查都设为 error 级 | 拒绝——违背 ADR-0003 高人工介入设计 |
| 仅保留 1-2 个最关键检查 | 拒绝——用户确认全量实现 |
| 不实现 STRICT_ARCH_GATE 升级 | 拒绝——失去 CI 强制手段，无法保证质量 |
| 改 schema 强制字段 | 拒绝——破坏 v1 兼容性 |

## Consequences

### 正面

- arch → plan 边界有**质量保证**，downstream 不再踩坑
- 不破坏现有流程（默认 warning），本地开发体验不变
- CI 默认严格，发布前保证质量
- 复用 `register_gate_check()` 插件机制，零核心架构变更
- `.arch-quality-report.json` 提供可观测的视图文件

### 负面 / 风险

- 4 个新的正则/解析规则可能产生**误报**（例如 ADR 引用历史编号）——通过 `force_transition()` 逃生
- CI 严格模式可能**首次启用时暴露大量历史债务**——按 issue tracker 渐进修复
- 增加 ~210 行代码 + 25 个测试的维护成本

## Schema (v1)

`.arch-quality-report.json` 是**视图文件**（gitignored），由 `arch_quality_gate.ArchQualityReport.verify()` 写入：

```json
{
  "passed": true,
  "warnings": ["arch_alignment"],
  "failed_checks": [],
  "detail": {
    "arch_alignment": {"passed": false, "severity": "warning"},
    "arch_debt_recorded": {"passed": true, "severity": null},
    "adr_no_placeholders": {"passed": true, "severity": null},
    "arch_handoff_actionable": {"passed": true, "severity": null}
  },
  "strict_mode": false
}
```

## Implementation

- **`skills/_lib/arch_quality_gate.py`**: 4 个 check 函数 + `strict_wrap` + `ArchQualityReport` 聚合器（25 单元测试覆盖所有路径）
- **`skills/_lib/gate.py`**: 导入 4 个 check + `strict_wrap`，注册到 `_DEFAULT_CHECKS["arch_done"]`
- **`skills/guide-arch.md`**: Phase 5 在双重门控后追加 python3 钩子，写报告文件
- **`.github/workflows/test.yml`**: "Arch quality gate (strict mode)" 步骤设置 `STRICT_ARCH_GATE: 'yes'`
- **`tests/unit/test_arch_quality_gate.py`**: 25 个测试覆盖正常/异常路径 + env var 升级
- **`tests/unit/test_gate.py`**: 增加 `test_default_arch_done_includes_quality_checks_adr0013` 验证注册

## 验证

```bash
# 单元测试
python3 -m pytest tests/unit/test_arch_quality_gate.py -v   # 25 passed
python3 -m pytest tests/unit/test_gate.py -v                # 14 passed (含新增 1)

# CI 严格模式
STRICT_ARCH_GATE=yes python3 -m pytest tests/unit/test_arch_quality_gate.py -v
```

## 参考

- ADR-0003 §"人工介入匹配" — arch 高人工介入
- ADR-0007 §"插件机制" — `register_gate_check()` API
- ADR-0016 §"Layer 3" — `.arch-handoff.json` 字段契约
- ADR-0015 — plan_done 的 `openspec_validate` 检查（与本 ADR 同模式：复用插件机制扩展质量门）