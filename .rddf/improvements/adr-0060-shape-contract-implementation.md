---
优先级: P2
来源: 2026-11-05 归档收尾审查 — ADR-0060（ADR 形态契约与门禁降级）已采纳并实施（commit 4b5a971），但未走 openspec change 流程，architect 产出形态契约要求的「关联 change」指针因此缺失，审计链在这一环断开
阶段: v5.x
分类: governance
类型: process
---

**优先级**: P2 | **来源**: 2026-11-05 归档收尾审查 — ADR-0060 已采纳并实施（commit 4b5a971），但未走 openspec change 流程，architect 产出形态契约要求的「关联 change」指针缺失
**阶段**: v5.x | **分类**: governance
**类型**: process

> **范围定位**：本提案**只做登记**，不改任何实现。ADR-0060 的决策内容、模板、门禁、守卫与测试均已落地（commit `4b5a971`），本提案把「决策 → 实现 → 验证」的链路补成可审计形态。
>
> ADR 元数据里的「关联 change」指针回填属于 **architect** 角色职责（`docs/adr/**` 在其可写范围内），本提案不代改 ADR 正文，只提供指针载体。

## Why

### 现象

ADR-0060（`docs/adr/ADR-0060-adr-shape-contract-and-gate-demotion.md`，状态「已采纳」）在 2026-11-05 的 commit `4b5a971` 中连同实现一起落地：

| 实施物 | 位置 |
|---|---|
| ADR 形态检查 | `_lib/arch_quality_gate.py::_check_adr_shape` |
| ADR 形态 CLI | `skills/rdd-arch/scripts/adr_shape_check.sh` |
| 关键词门禁降级为 advisory | `skills/rdd-arch/scripts/adr_gate.sh` |
| 模板收紧（Verification 章 / 三列备选表 / 体量提示） | `docs/adr/ADR-0000-template.md` |
| 流程侧提示词 | `skills/rdd-arch/SKILL.md` Phase 2 |
| 回归测试 | `tests/unit/test_arch_quality_gate.py`（36 例）+ `tests/integration/test_adr_gate.bats` + `test_adr_gate_flow.bats` |

但它**没有走 openspec change 流程** —— 即没有 `openspec/changes/<name>/`，也没有 `.rddf/improvements/<name>.md`。

### 为什么这是缺陷

architect 产出形态契约（「ADR 完成的标志」第 4 条）要求每份已决 ADR 的「关联 change」二选一：

- 已立项 → 指向 `openspec/changes/<name>/`
- 尚未立项 → 登记为 `backlog: <improvement 名>`

ADR-0060 两条都不满足 —— 元数据里既没有 change 指针，也没有 backlog 登记。后果：

1. **审计链断在实施这一环**：拿到 ADR-0060 的人无法从 ADR 走到实现（commit）与验证证据。
2. **ADR 与实现可能漂移无告警**：没有 change 就没有 tasks.md 的完成度记录，也没有 verdict cache 与归档记录；ADR 被改而实现没跟上时，没有任何机制会发现。
3. **同类路径无先例可循**：下一份「architect 直接写 ADR + 顺手实现」的文档仍会重复这个缺口 —— 本提案同时是**登记**与**先例**。

### 与「存量不追溯」的边界

ADR-0060 的**决策内容**不动。本提案不重新评审、不改判、不改任何已落地实现，只补指针。

### 两个未决外溢（不在本提案解决，但必须写明）

1. **本提案不固化流程**：登记 ≠ 流程修复。ADR-0060 的 Context 章已经点明「真正生效的约束在提示词层（`prompts/build.md`），两处需同源」—— 本提案只补事后登记这一环，**不**给「architect 直写 ADR」这条路径加 gate。下一次有人绕过 openspec 直接写 ADR 并实现时，仍然可以不登记。本提案确立的「先例」是「事后登记的做法」，不是「可以绕过」的许可。
2. **`backlog:` 指针的生命周期未定义**：build.md 契约只覆盖「立项后回填 `openspec/changes/<name>/`」，没有覆盖「实施之后才补登记」这一场景 —— 本 improvement 若走完 rdd-builder 流程并归档，`backlog: adr-0060-shape-contract-implementation` 何时、是否更新为已归档 change 的路径，契约未定义。**本提案沿用 `backlog:` 写法并显式承认这一空白**，由 architect 在回填时按当时的契约判断，不在本提案内预设规则。

## What Changes

1. **本文件作为 ADR-0060 的登记载体**：`backlog: adr-0060-shape-contract-implementation`。
2. **ADR 元数据回填一行指针**（architect 执行）：在 ADR-0060 的元数据块加 `> **关联 change**: backlog: adr-0060-shape-contract-implementation`。
3. **Verification 实测记录**：把 ADR-0060 `## Verification` 的 8 条判据（V-1..V-8）的实跑结果落成本文件 `## Acceptance` 的证据。

**不改**：ADR-0060 的 Decision / Consequences / 选项对比表 / Verification 章；`_lib/arch_quality_gate.py`；`skills/rdd-arch/scripts/adr_gate.sh`；`adr_shape_check.sh`；模板；任何测试。

## Acceptance

### 已实施证据（2026-11-05 实跑；本提案不改实现，verifier 可抽验复跑）

- [x] **V-1** `bash skills/rdd-arch/scripts/adr_gate.sh "rv32i-fetch-skid-buffer"` ⇒ stdout 仍为 `IMPLEMENTATION`，stderr 含 `advisory`
- [x] **V-2** `ADR_GATE_MODE=block bash ... adr_gate.sh "Fix typo"` ⇒ stderr **无** advisory
- [x] **V-3** `ADR_GATE_CLASS=ARCHITECTURE bash ... adr_gate.sh "rv32i-fetch-skid-buffer"` ⇒ stdout 为 `ARCHITECTURE`
- [x] **V-4** `python3 -m pytest tests/unit/test_arch_quality_gate.py -q` ⇒ 全部通过
- [x] **V-5** `bats tests/integration/test_adr_gate.bats tests/integration/test_adr_gate_flow.bats` ⇒ 全部通过
- [x] **V-6** `ARCH_SHAPE_CHECK=yes` 时 `ArchQualityReport.verify('.')` 的 `detail` 含 `adr_shape`；未设该变量时**不含**。复跑命令：

  ```bash
  ARCH_SHAPE_CHECK=yes python3 -c "
  import sys; sys.path.insert(0,'.')
  from _lib.arch_quality_gate import ArchQualityReport
  print('adr_shape' in ArchQualityReport.verify('.').detail)"
  # => True（未设 ARCH_SHAPE_CHECK 时同一命令输出 False）
  ```

- [x] **V-7** 一份正文 > 300 行的 ADR ⇒ `adr_shape_check.sh <file>` 报出该文件与超出行数
- [x] **V-8** `docs/adr/ADR-0000-template.md` 仍含 `## Context` / `## Decision` / `## Consequences` / `## References` 四段

### 本提案待办

- [ ] **A-0** 本文件同时含 ADR-0060 的路径指针与实现 commit `4b5a971` 的指针（双向可溯）
- [ ] **A-1** ADR-0060 元数据块含 `> **关联 change**: backlog: adr-0060-shape-contract-implementation`（**architect 回填**）

  > **不阻塞归档**：按 build.md「architect 产出形态契约」的跨角色收口条款，A-1 属跨角色收口项，不要求在本回合完成 —— builder 在 P3 archive gate 看到 A-1 未勾时**不得因此卡住**；由 architect 在任意后续回合回填并补勾。

- [ ] **A-2**（记录现状，非断言）`skills/rdd-doctor/scripts/checks/arch_audit_check.py` 当前只有 3 项检查 —— theme-doc inventory / ADR inventory / arch-handoff sanity —— **没有**「关联 change 缺失」检查。因此 doctor 无法自动发现本次这类缺口；契约检查落地后应补一条自动判据（另案立项）。

## Capabilities

**不新增 capability。** 本提案不改变任何对外契约面 —— ADR-0060 的契约面（模板、门禁、守卫）已在 commit `4b5a971` 落地并被 V-1..V-8 验证。

## Impact

| 维度 | 影响 |
|---|---|
| 运行时 | 无（纯文档登记） |
| 对外契约 | 无 |
| 测试 | 无新增；引用既有的 `test_arch_quality_gate.py` / `test_adr_gate*.bats` |
| 回滚 | 删除本文件 + 移除 ADR 元数据那一行指针，无副作用 |
| 后续 | 本提案为「architect 直写 ADR + 顺手实现」路径提供**事后登记**的先例；流程固化（登记步骤写进 architect 产出契约）与 doctor 自动判据均**另案**，本提案不覆盖 |
| 证据保鲜 | V-1..V-8 验证的是已合入的实现。若 `adr_gate.sh` / `arch_quality_gate.py` / `adr_shape_check.sh` / 模板被修改，这些证据即失效 —— 本 improvement 归档后无机制自动告警，需在实现下次被改动时重新抽验 |
