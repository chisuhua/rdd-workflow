## Goals

完成 ADR-0015 中「后续待办」第一条：

> `guide-plan.md` 在 Phase 4 调用 `validate_report.write_report()` 刷新 report 文件

让 `openspec validate` 的结构化结果在 plan-done 时被独立运行并持久化到
`.rddf/state/openspec-validate.json`，为下游 consumers（plan-done gate、
未来 archive hook、`plan.review_validation` 人工节点）提供 O(structure)
的读取契约，避免每次 consumer 需要时都重新跑一次 CLI。

## Non-Goals

- **不修改 `skills/_lib/gate.py`**：`_check_openspec_validate` 已经在
  gate 转换时运行 `openspec validate`，但其结果是临时消费（直接读
  `summary.totals.failed` 后丢弃），不持久化。本 change 不动 gate.py。
- **不修改 `skills/_lib/validate_report.py`**：现有的 `write_report()`
  / `load_report()` API 已足够支撑本 change 的需求，无需扩展。
- **不修改 `skills/_lib/human_nodes.py`**：`plan.review_validation`
  节点的实装留给后续 ADR。
- **不修改 `archive.sh`**：archive 前检查最近一次 validate 结果留给
  ADR-0015 后续待办第三条。
- **不改变 plan-done gate 行为**：新 wiring 块是 non-fatal 的持久化
  步骤，不影响 `run_plan_done_gate` 的 pass/fail 决策。

## Architecture

### 现状（before this change）

```
guide-plan.md Phase 4 (plan-done)
    │
    ├─ run_plan_done_gate()         ← triple-gate (Gate 0/1/2)
    │     └─ gate.py::_check_openspec_validate
    │           └─ subprocess.run("openspec validate --all --strict --json")
    │           └─ 读取 summary.totals.failed 后丢弃 (no persistence)
    │
    ├─ write_plan_handoff()         ← 写 .rddf/state/.plan-handoff.json
    │
    └─ rddf_session_hook_close()
```

**问题**：`_check_openspec_validate` 在 gate 内部跑 `openspec validate`，
但结果只在 `subprocess.run` 返回值中存活几毫秒就被丢弃。下游 consumers
想读 validate 结果时只能：(a) 再跑一次 CLI（latency + cost），或
(b) 不读，等于 ADR-0015 §决策 5 设计的 view 文件契约形同虚设。

### 目标（after this change）

```
guide-plan.md Phase 4 (plan-done)
    │
    ├─ run_plan_done_gate()         ← 不变
    │
    ├─ 【NEW】persist_openspec_validate()   ← ADR-0015 wiring
    │     └─ for each active change:
    │           └─ openspec validate <change-name> --json
    │           └─ validate_report.write_report(project_root, raw_report)
    │                 └─ 写 .rddf/state/openspec-validate.json
    │
    ├─ write_plan_handoff()         ← 不变
    │
    └─ rddf_session_hook_close()
```

**关键决策**：

1. **独立运行而非复用 gate 结果**：`gate.py::_check_openspec_validate`
   不暴露 raw JSON（只返回 `(passed: bool, severity: str)`）。要在
   guide-plan.md 拿到 raw JSON 有两条路：
   - (a) 修改 gate.py 让它把 raw JSON 也返回 → 违反「不修改 gate.py」约束
   - (b) 在 guide-plan.md 独立跑一次 → 本 change 选择

  代价是多跑一次 `openspec validate`。但 plan-done 是低频人工触发的
   过渡点，且 `openspec validate --all` 在大项目上秒级，可接受。

2. **per-change 而非 `--all`**：gate.py 用 `--all --strict` 验证全部
   specs + changes。本 wiring 改为 per-change (`openspec validate
   <change-name> --json`)，理由：
   - plan-done 关心的是当前 active changes 是否符合 OpenSpec schema
   - specs 的全量校验是 ADR-0015 后续待办第四条「评估 `with_change`
     范围」的范畴
   - per-change 让 `.rddf/state/openspec-validate.json` 反映「最近一次
     plan-done 时各 active change 的状态」而非「全项目状态」

   **注意**：`write_report()` 当前覆盖式写单一文件（`REPORT_PATH_TEMPLATE
   = ".rddf/state/openspec-validate.json"`，不带 change 名后缀），所以
   多 change 循环时后写者覆盖前写者。这是 ADR-0015 §决策 5 既定的
   「单 view 文件」契约，本 change 不改。最终持久化的是**最后一个被
   验证的 active change** 的 report。TODO（见下方）会标注此限制。

3. **non-fatal**：`openspec validate` 失败（例如 skeleton change 没有
   delta）、`openspec` 二进制不在 PATH、`write_report` 抛异常——全部
   不阻断 plan-done。理由：
   - plan-done 的阻断决策已经由 `run_plan_done_gate` + gate.py 的
     `_check_openspec_validate` 做出，本 wiring 块只负责持久化
   - skeleton change（`planned` 状态）会自然 validate 失败，但 plan-done
     gate 0 已经通过 `list_ready_for_ship` 过滤掉它们
   - 持久化失败不应该让用户卡在 plan-done 退出点

4. **PYEOF + env-var 传递**：遵循 Round A Task 3 (`plan_intake.sh`)
   和 Task 4 (`plan_done_gate.sh`) 确立的 Oracle C1 安全模式——
   `PROJECT_ROOT` 通过 env var 传给 Python，**不**通过 bash 字符串
   插值。`report_json` 是 `openspec validate` 的 stdout，通过 stdin
   pipe 传给 Python（避免 bash 插值 + 单引号转义陷阱）。

### Dual-Run 说明（短期 vs 长期）

**短期**（本 change 实装）：

```
plan-done 触发时：
  1. gate.py::_check_openspec_validate       → 跑 1 次 openspec validate --all --strict
                                              → 只返回 (passed, severity)，丢弃 raw JSON
  2. guide-plan.md persist_openspec_validate  → 跑 N 次 openspec validate <change> --json
                                              → 持久化到 .rddf/state/openspec-validate.json
```

**问题**：双跑。同一个 plan-done 转换里 `openspec validate` 被执行
N+1 次（1 次 `--all` + N 次 per-change），latency 累加。

**长期**（TODO，留给后续 change）：

合并 gate.py 和本 wiring：让 `_check_openspec_validate` 在跑完
`openspec validate --all --strict --json` 后，直接把 raw JSON 通过
`validate_report.write_report()` 持久化，然后返回 `(passed, severity)`。
这样：

```
plan-done 触发时：
  1. gate.py::_check_openspec_validate       → 跑 1 次 openspec validate --all --strict
                                              → 持久化 + 返回 (passed, severity)
  [guide-plan.md persist 步骤删除]
```

**为什么本 change 不直接做合并**：

- gate.py 的 `_check_openspec_validate` 在 `tests/unit/test_gate.py`
  有锁住「返回值契约」的单元测试，改返回值要同步改测试，扩大 blast
  radius
- 合并需要决定「`--all` 模式下如何把多 change 结果拆分到 per-change
  view 文件」——这触及 ADR-0015 §决策 5 的「单 view 文件」契约，
  需要单独 ADR 讨论
- 本 change 的目标是**先把 wiring 跑通**让下游 consumer 有 view 文件
  可读，长期合并是「refactor」而非「wire」

TODO 在 guide-plan.md Phase 4 的 wiring 注释中明确标注。

## Alternatives Considered

| 备选 | 拒绝理由 |
|------|---------|
| A: 修改 gate.py 让 `_check_openspec_validate` 也持久化 | 违反本 change「不修改 gate.py」约束；扩大 blast radius 到 test_gate.py |
| B: 在 `propose.md` Phase 4 持久化（而非 guide-plan.md） | propose 创建单个 change，但 plan-done 是所有 active changes 的统一退出点；放 propose 会让 view 文件只反映最后一个被 propose 的 change |
| C: 用 `--all` 模式跑一次，把整段 JSON 写入 view 文件 | 违反 ADR-0015 §决策 5 的「单 view 文件 + per-change failed_items」契约；downstream consumer 难以判断是哪个 change 失败 |
| D: 让 `write_report()` 接受 change_name 参数并写 per-change 文件 | 改动 `validate_report.py` 的 API + schema，违反本 change「不修改 validate_report.py」约束；触发 schema version bump |
| E: 不在 plan-done 持久化，让 consumer 自己 lazy 调用 | 每次消费都重跑 CLI，latency 累加；ADR-0015 §决策 5 明确要求「view 文件契约」 |

## Risks

| 风险 | 缓解 |
|------|------|
| Dual-run 增加 plan-done latency | `openspec validate` 秒级；plan-done 是低频人工触发点；长期 TODO 合并 |
| Skeleton change（`planned` 状态）会 validate 失败 | Gate 0 已通过 `list_ready_for_ship` 过滤；wiring 块 non-fatal |
| `openspec` 不在 PATH | wiring 块 `command -v openspec` 短路；non-fatal |
| 单 view 文件被后写者覆盖 | ADR-0015 §决策 5 既定契约；本 change 不改；TODO 标注 |
| bash 字符串插值注入风险 | 全程使用 env-var + stdin pipe 传递，遵循 Oracle C1 模式 |

## Dependencies

- **ADR-0015**：本 change 实装的 ADR 依据
- **`skills/_lib/validate_report.py`**：`write_report(project_root,
  raw_report)` API（已存在，v1 schema）
- **`openspec` CLI 1.3.1+**：`openspec validate <name> --json` 命令
  （package.json engines 已声明 `>=1.3.1`）
- **`skills/guide-plan/SKILL.md` Phase 4**：wiring 插入点
- **`skills/guide-plan/scripts/plan_done_gate.sh`**：existing helper，
  本 change 不修改，只在 guide-plan.md 主文件加新块

## Testing Strategy

1. **Integration test** (`tests/integration/test_adr_0015_wiring.bats`)：
   - 验证 `validate_report.write_report` 函数存在且可 import
   - 验证 ADR-0015 状态字段为「已采纳」
   - 验证 guide-plan.md Phase 4 含 ADR-0015 wiring 块标记
2. **Existing tests 回归**：跑全量 pytest unit + bats integration，
   确保 663 个已有测试全部 pass
3. **不新增 unit test**：本 change 不新增 Python 函数（只加 bash 块），
   无新单元可测

## References

- `docs/adr/ADR-0015-integrate-openspec-validate-as-plan-critic.md` -
  本 change 实装的 ADR
- `docs/adr/ADR-0015-integrate-openspec-validate-as-plan-critic.md`
  §后续待办 第一条 - 本 change 的明确触发点
- `skills/_lib/validate_report.py` - `write_report()` / `load_report()`
  API
- `skills/_lib/gate.py:201-236` - `_check_openspec_validate`（dual-run
  的另一端，本 change 不修改）
- `skills/guide-plan/SKILL.md` Phase 4 - wiring 插入点
- `skills/guide-plan/scripts/plan_done_gate.sh` - existing helper
- Oracle C1 安全模式 - Round A Task 3/4 确立的 env-var 传递模式
