# fix-post-flow-classifier-ordering

## Why

ADR-0027 §1.2 规定 classifier 三段式(usage / environment / flow-bug)+ 4 类触发分类(F1 traceback in `_lib/` → `phase-crash`,F2 ConfigError / gate raised → `gate-failure`,F3 invalid state / unexpected status → `flow-bug`,F4-gate 自定义 → `gate-failure`)。

**Oracle 复核发现三个矛盾**(审计 2026-08-24 §5.3 G5):

### 矛盾 1:F2(F3)匹配顺序导致 F2 不可达

`_lib/post_flow_analysis.py:234` 的 F3 状态违反(`invalid state`)正则**先于** `:246` 的 F2 ConfigError 分支匹配 → 含 "invalid state" 的错误文本只能走 F3 → **F2 路径不可达**,gate-failure 只剩 ConfigError 一条路径。

### 矛盾 2:两个分类器对同一信号分类不一致

`analyze_phase_trace:490` 的 F2-cumulative 把同一"invalid state"文本映射为 `gate-failure`;`report_flow_bug:234` 的主路径把它映射为 `flow-bug`。

### 矛盾 3:F4-gate 规则缺失

ADR §1.2 明确承诺的 `F4-gate`(gate raised → `gate-failure`)规则完全未实现。这意味着 `arch_debt_recorded`、`change_adr_refs_valid`、`review_debt_recorded` 等 gate raise 不会触发 issue 上报——这恰恰是 §1.2 标注为"ADR-0018/0019 自身实现问题"的核心场景。

## What Changes

**In Scope**:

- 检测 stderr 含 `gate raised` / `gate failure` / `_check_*` 调用栈
- 匹配后归类为 `gate-failure`
- **不**改 `_should_auto_submit`(env 解析逻辑无关本提案)
- **不**改 `report_flow_bug` 的外发路径(由 PR-1 修复)
- **不**引入新分类类别(ADR §1.1 类别清单**不**扩展)
- **不**改 buffer / report / triage / close 环(本提案只触及 detect)
- **不**为每个 gate 自定义独立 issue 类别(避免 L2 GitHub label 爆炸)
- **不**改 `_classify_interrupted_phase` 的"phase-interrupted"类别命名(由 PR-6 文档对齐处理)

### 关键场景

### 场景 A:traceback in `_lib/`(F1 主路径)

**GIVEN** `_lib/post_flow_analysis.py` 抛 `ZeroDivisionError`,stderr 含 traceback 帧
**WHEN** classifier 执行
**THEN**
- F1 正则匹配(`Traceback` + 栈帧路径含 `skills/_lib/` 或 `_lib/`)
- 分类为 `phase-crash`
- `dedup_hash` 基于前 3 个 stack frame 归一化

### 场景 B:gate raised(F4 新实现)

**GIVEN** `_lib/gate.py::_check_arch_debt` raise `ConfigError`,stderr 含 `gate raised in _check_*`
**WHEN** classifier 执行
**THEN**
- F4 正则匹配(优先于 F3)
- 分类为 `gate-failure`
- Reporter 段记 `skill_invoked: gate-system`

### 场景 C:ConfigError(F2 之前不可达,现在可达)

**GIVEN** schema 加载抛 `ConfigError`,stderr 含 `"Config validation failed: ..."`(不含 "gate raised")
**WHEN** classifier 执行
**THEN**
- F2 正则匹配(优先于 F3)
- 分类为 `gate-failure`
- **不再是 F3-mislabeled as flow-bug**

### 场景 D:invalid state(F3 路径)

**GIVEN** 状态机分支错误,stderr 含 `"invalid state: expected 'arch_done', got 'plan_done'"`
**WHEN** classifier 执行
**THEN**
- F2 / F4 不匹配
- F3 正则匹配
- 分类为 `flow-bug`(与现有契约一致)

### 场景 E:usage / environment(原 priority 不变)

**GIVEN** 缺参数或缺工具(usage / environment)
**WHEN** classifier 执行
**THEN** 不进入 F1-F4,直接走 environment / usage 三段式 first match,exit 0(UI 提示,不报 issue)

**Out of Scope**:

- (no items specified)

## Capabilities

- (no items specified)

## Impact

- (no items specified)

## Acceptance

### 功能验收

- [ ] **AC-1**:F1 traceback 路径仍分类为 `phase-crash`(回归)
- [ ] **AC-2**:F2 ConfigError 路径可达(回归测试)
- [ ] **AC-3**:F3 invalid state 仍为 `flow-bug`(回归)
- [ ] **AC-4**:**新增**:F4 gate-raised 路径可达且分类为 `gate-failure`
- [ ] **AC-5**:`analyze_phase_trace` 与 `classify_phase_outcome` 对同一输入返回相同分类(回归)
- [ ] **AC-6**:模块级导出 4 个 `_RE` 常量,docstring 引 ADR-0027 §1.2 对应关系

### 测试

- [ ] 4 unit 测试(场景 A-D 各一)
  - `tests/unit/test_post_flow_classifier.py` 新建或扩充
  - `test_f1_traceback_in_lib_classified_as_phase_crash`
  - `test_f2_config_error_classified_as_gate_failure` **(新增覆盖 F2 可达性)**
  - `test_f3_invalid_state_unchanged`
  - `test_f4_gate_raised_new_path`
- [ ] 1 regression 测试(场景 E 主 + 副路径)
  - `test_analyze_phase_trace_consistent_with_main_classifier`(同输入同输出)
- [ ] 1 sanity 测试(命名常量导出)
  - `test_module_exports_f_re_constants`

