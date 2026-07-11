# ADR-0019: change_arch_alignment — change 提案与架构对齐检查

> **状态**: ✅ 已采纳
> **日期**: 2026-07-10
> **决策者**: sisyphus
> **依据**: ADR-0003 (三阶段架构), ADR-0007 (门控机制), ADR-0016 (arch discovery), ADR-0018 (arch quality gate), Oracle 咨询 (2026-07-10, 2026-07-10)
> **版本目标**: v2.1 (候选)

## Context

ADR-0018 引入了 arch 阶段的 4 个文档级质量门（alignment/debt/clarity/handoff），但**未覆盖 change 提案层**——而架构债务最容易在 change 落地时滋生：

1. **引用过期 ADR**：`openspec/changes/<name>/design.md` 引用 `ADR-0001`，但 ADR-0001 已被 `ADR-0002+0003` 替代（ADR-0001 状态 `已替代`）
2. **语义矛盾**：design.md 主张"采用单阶段状态机"，但 ADR-0003 已采纳"三阶段状态机"
3. **任务不可追溯**：`tasks.md` 中 ≥ 50% 子任务未引用任何 ADR，无法判断是否在架构范围内

参考 ADR-0018 的 `arch_quality_gate` 模式（4 个 check + `strict_wrap` + `STRICT_ARCH_GATE`），我们具备**复用基础设施**在 `plan_done` 阶段增加对齐检查的条件。

### Oracle 咨询结论（2026-07-10）

Oracle 推荐独立 env var 方案：

> **采用 `STRICT_CHANGE_GATE=yes`（控制 `plan_done`），与现有 `STRICT_ARCH_GATE` 并列**，未来 Tier 2 用 `STRICT_CODE_GATE`（控制 `ship_done`）。每阶段一个变量，零迁移成本，CI 粒度独立。代码变更：仅需将 `strict_wrap(condition, env_var="STRICT_ARCH_GATE")` 参数化。

理由（节选）：
- 名称映射到阶段转换：自文档化
- 零迁移成本：ADR-0018 的 `STRICT_ARCH_GATE=yes` 用户无需任何更改
- CI 粒度：可单独启用某一阶段严格模式

## Decision

我们引入 **`change_arch_alignment`** —— `plan_done` 阶段的 3 个 warning 级检查，默认不阻塞，`STRICT_CHANGE_GATE=yes` 升级为 error（仅 CI 启用）。

### 三个检查项

| Check 名称 | 检查内容 | 失败信号 |
|---|---|---|
| `change_adr_refs_valid` | `openspec/changes/<name>/design.md` 中 `ADR-NNN §N.M` 引用全部存在且状态为 `已采纳`（非 `已弃用` / `已替代为 ADR-NNN`） | 引用过期或悬空 |
| `change_no_contradiction` | design.md 不含**显式反模式关键词**或含反模式关键词时同时引用 ADR 论证 | 反模式无 ADR 背书 |
| `change_task_traceability` | `tasks.md` 中 ≥ 80% 子任务能追溯到 ≥ 1 个 ADR（覆盖率指标） | 任务架构外 |

### 反模式关键词清单（v1）

Oracle 2026-07-10 咨询结论：**保守 3 条**（即按 ADR 已起草的清单直接发布），不扩张也不外置配置。

```yaml
anti_patterns:
  - pattern: "单阶段|单体架构|hard.?code|hard.?coded|硬编码"
    severity: "info"  # 仅提示，不阻断
    requires_adr_justification: true
  - pattern: "跳过.{0,5}(架构|arch|adr|ADR)"
    severity: "warn"
    requires_adr_justification: true
  - pattern: "不写测试|跳过测试|skip.{0,5}test"
    severity: "warn"
    requires_adr_justification: true
```

#### 为什么是 3 条（Oracle 论证摘要）

1. **ADR-0018 已有先例**：`arch_quality_gate.py._PLACEHOLDER_PATTERNS` = 7 条硬编码正则，未外置化，运行良好
2. **误报成本 > 漏报成本**：扩展至 `TODO`/`FIXME`/`裸 subprocess call` 等模式几乎必命中工作代码，导致检查被 `force_transition()` 绕过，v1 信誉归零
3. **无 v1 运行数据无法决定扩展什么**：必须先收集实际命中数据

#### v1 → v2 扩展触发条件

| 触发条件 | 动作 |
|---|---|
| 单条模式在连续 10 次扫描中 0 命中 | 移除（减小测试面） |
| 合理新模式被人工确认 ≥ 3 次应捕获但遗漏 | 纳入 v2 清单 + 同步测试 |
| 同一反模式出现 ≥ 3 种正则未覆盖的变体 | 泛化正则，而非新增条目 |

### 严重级别矩阵

| 环境 | `openspec_validate` (existing) | 3 个新检查 |
|---|---|---|
| 本地开发 | error | warning（不阻塞） |
| `STRICT_CHANGE_GATE=yes` (CI) | error | error（升级） |

升级机制复用 ADR-0018 的 `strict_wrap(condition, env_var="STRICT_CHANGE_GATE")`，仅需参数化扩展。

### 影响范围

- **In Scope**:
  - `skills/_lib/change_alignment.py` 新增（~180 行）：3 个 check 函数 + 关键词正则 + 任务覆盖率计算
  - `skills/_lib/arch_quality_gate.py` `strict_wrap` 参数化：`strict_wrap(condition, env_var="STRICT_ARCH_GATE")`
  - `skills/_lib/gate.py` `_DEFAULT_CHECKS["plan_done"]` 新增 3 个 Check
  - `tests/unit/test_change_alignment.py` 新增（≥ 20 个测试）
  - `tests/unit/test_arch_quality_gate.py` 新增 `strict_wrap(env_var=...)` 参数化测试
- **Out Scope**:
  - 不修改 `.arch-handoff.json` schema
  - 不修改 `openspec validate` 行为（保持现有 schema 校验）
  - 不实现 Tier 2（代码级 `code_arch_alignment`），仅在 ADR 中占位
  - 不实现自动修复（如自动重写引用过期 ADR）—— 仅警告 + 人工决策

### 备选方案

| 备选 | 理由 |
|---|---|
| 复用 `STRICT_ARCH_GATE` 控制 plan_done | 拒绝——名称语义错位，Oracle 建议 |
| 改名统一为 `STRICT_GATE` | 拒绝——破坏 ADR-0018，向后兼容成本高 |
| Tier 1 + Tier 2 同时实现 | 拒绝——Tier 2 需要架构边界 DSL，超出 v2.1 范围 |
| 不实现 | 拒绝——change 层架构债务继续积累 |

## Schema (v1)

change_alignment 不新增 handoff schema 字段。结果通过 `EventLog` 事件流记录：

```json
{
  "event_type": "gate_warning",
  "transition": "plan_done",
  "check": "change_adr_refs_valid",
  "change": "<change-name>",
  "details": {
    "invalid_refs": ["ADR-0001 §2.1"],
    "reason": "ADR-0001 status=已替代为 ADR-0002+0003"
  },
  "strict_mode": false
}
```

## Implementation Notes (Post-Oracle Review 2026-07-10)

Oracle 在实施前 review 中发现以下问题，必须在实现阶段处理：

| ID | 严重级别 | 问题 | 处理方式 |
|---|---|---|---|
| A1 | Critical | `ctx.get("change_name")` 不会工作（gate.py 注入 ctx 仅含 `project_root` + `state_vector`） | 改用 `sv.get_field("plan_side.active_change")`，回退 `arch_side.current_change` |
| A2 | Critical | ADR 状态字符串匹配不可靠（`✅ 已采纳` / `已替代为 ADR-NNN` 变体） | 改用枚举 `accepted/deprecated/unknown`，子串匹配 + 正反向清单 |
| A3 | Important | anti-pattern severity 未实现（`info` 被硬编码为 `warning`） | 三个 check 中只有 `warn` 级反模式无 ADR 时返回 warning；`info` 级仅做记录不阻断 |
| A4 | Important | `_parse_task_items` 未定义（`- [ ]` checkbox 格式） | 显式 regex `^\s*-\s*\[[ xX]\]\s+(.+)$`，并处理"无 checkbox 但有 bullet" → pass |
| A5 | Important | `design.md` 缺失场景未防御（17/17 历史 change 无 design.md） | 三个 check 函数开头防御 `if not path.is_file(): return (True, None)` |
| A7 | Nice-to-have | README 索引表状态不一致 | ✅ 已修复（2026-07-10） |

## Implementation Sketch

### `skills/_lib/arch_quality_gate.py` 参数化（向后兼容）

```python
def is_strict_mode(env_var: str = "STRICT_ARCH_GATE") -> bool:
    """Per-gate strict mode. Backward compatible default = STRICT_ARCH_GATE."""
    val = os.environ.get(env_var, "").strip().lower()
    return val in _STRICT_TRUE


def strict_wrap(
    condition: Callable,
    env_var: str = "STRICT_ARCH_GATE",
) -> Callable:
    """Wrap a check condition; under <env_var>=yes, upgrade warnings to errors."""
    def wrapped(ctx):
        passed, severity = condition(ctx)
        if not passed and severity == "warning" and is_strict_mode(env_var):
            return (False, "error")
        return (passed, severity)
    return wrapped
```

### `skills/_lib/change_alignment.py`（新模块）

```python
def _check_change_adr_refs_valid(ctx: dict) -> tuple[bool, Optional[str]]:
    """design.md ADR-NNN §N.M refs all exist + status=已采纳."""
    change_name = ctx.get("change_name")
    refs = _extract_adr_refs(change_name)
    invalid = [r for r in refs if _resolve_adr_status(r) != "已采纳"]
    return (len(invalid) == 0, "warning" if invalid else None)


def _check_change_no_contradiction(ctx: dict) -> tuple[bool, Optional[str]]:
    """design.md anti-pattern keywords either absent or accompanied by ADR justification."""
    text = _read_change_file(ctx["change_name"], "design.md")
    for ap in _ANTI_PATTERNS:
        if re.search(ap["pattern"], text, re.IGNORECASE):
            # Anti-pattern found; check if any ADR ref justifies it
            if not _ADR_REF_RE.search(text):
                return (False, "warning")
    return (True, None)


def _check_change_task_traceability(ctx: dict) -> tuple[bool, Optional[str]]:
    """≥ 80% of tasks.md list items reference ≥ 1 ADR."""
    tasks = _parse_task_items(ctx["change_name"])
    if not tasks:
        return (True, None)  # No tasks = no check
    traced = sum(1 for t in tasks if _ADR_REF_RE.search(t))
    coverage = traced / len(tasks)
    return (coverage >= 0.8, "warning" if coverage < 0.8 else None)
```

### `skills/_lib/gate.py` 注册

```python
_DEFAULT_CHECKS = {
    "plan_done": [
        # ... existing checks ...
        Check("change_adr_refs_valid",
              strict_wrap(_check_change_adr_refs_valid, env_var="STRICT_CHANGE_GATE"),
              "design.md 引用了已弃用/已替代的 ADR",
              "更新引用到当前生效的 ADR",
              "warning"),
        Check("change_no_contradiction",
              strict_wrap(_check_change_no_contradiction, env_var="STRICT_CHANGE_GATE"),
              "design.md 含反模式关键词但无 ADR 论证",
              "添加 ADR 引用说明为何选择该模式",
              "warning"),
        Check("change_task_traceability",
              strict_wrap(_check_change_task_traceability, env_var="STRICT_CHANGE_GATE"),
              "tasks.md 中 <80% 子任务能追溯到 ADR",
              "为每个架构性任务添加 ADR-NNN 引用",
              "warning"),
    ],
}
```

### CI 配置（`.github/workflows/test.yml` 新增步骤）

```yaml
- name: Change alignment gate (strict mode)
  env:
    STRICT_CHANGE_GATE: 'yes'
  run: |
    python3 -m pytest tests/unit/test_change_alignment.py -q --tb=short
    echo "✅ Change alignment gate tests passed under STRICT mode"
```

## Consequences

### 正面

- change 提案层有架构对齐保证，downstream 不会被过期 ADR 误导
- 反模式关键词清单保守，误报风险低
- 复用 ADR-0018 的 `strict_wrap` 模式（仅参数化），零架构变更
- 任务覆盖率指标驱动任务治理改进
- 为未来 Tier 2（`code_arch_alignment`）奠定基础（`STRICT_CODE_GATE`）

### 负面 / 风险

- 反模式关键词清单**维护成本**：每次新增模式需同步正则 + 测试
- 任务覆盖率 80% 阈值**主观性**：可能过低或过高，需根据项目调整
- 关键词匹配是**字符串层**而非语义层，可能漏判或误判
- 新增 ~180 行代码 + ≥ 20 测试 + 参数化 strict_wrap 的维护成本

## Future Work

### Tier 2（v2.1 后）：`code_arch_alignment` at `ship_done`

- 跨层 import 检测：基于 `# @arch-boundary: layer=plan, allow_import=ship.*` 注解
- 依赖方向验证：禁止 plan → ship 内部函数直接调用
- env var：`STRICT_CODE_GATE=yes`
- 实现成本：高（需要 AST 解析 + 注解约定文档化）

### 反模式关键词清单演进

- v1：保守清单（3 条）
- v2：基于历史 false positive 数据扩展
- v3：接入 LLM 辅助语义检测（如果 ADR 体系足够结构化）

## 验证

```bash
# 单元测试（待实现）
python3 -m pytest tests/unit/test_change_alignment.py -v        # ≥ 20 passed
python3 -m pytest tests/unit/test_arch_quality_gate.py -v      # 现有 25 + 新增 ≥ 5 参数化测试

# CI 严格模式
STRICT_CHANGE_GATE=yes python3 -m pytest tests/unit/test_change_alignment.py -v
```

## 参考

- ADR-0003 §"人工介入匹配" — 三阶段人工介入梯度
- ADR-0007 §"插件机制" — `register_gate_check()` API
- ADR-0018 §"严格模式" — `strict_wrap` 模式 + `STRICT_ARCH_GATE` 模式
- Oracle 咨询 (2026-07-10) — `STRICT_CHANGE_GATE` 独立 env var 方案推荐