---
优先级: P1
来源: 2026-11-27 用户裁决（OC-1c = 上 baseline / known_failures 机制）+ oracle 建议 11（先评估两个更便宜替代）+ critic SHOULD_FIX 4/6
阶段: phase-3
分类: quality-gate
类型: improvement
状态: 已批准（planner 2026-11-27）· **SU 前置已满足**（治理仓 `ADR-commit-verification-gate` Status Update **Accepted** 2026-11-27，判据见 D10 + Verification V20–V25）· **实现载体迁到治理仓**（§9.4 归属仓 = 治理仓；本稿的 AC 需按「治理仓 bun test + rdd-workflow 巡检载体」两仓重排后方可立项）
主题: commit-gate 声明支持 baseline / known_failures —— 有存量红的仓也能声明门禁
---

**优先级**: P1 | **来源**: 2026-11-27 用户裁决 | **阶段**: phase-3 | **分类**: quality-gate | **类型**: improvement

## metis 结论（2026-11-27 · 本轮 1 轮覆盖 9 份草稿 · 载体=头部段）

- **AC5（SU 前置）跨仓不可机判**（本仓 CI 读不到治理仓 ADR 文档 ⇒ 永远红或永远 skip）⇒ **降级为 design 阶段 checklist**，不做测试断言。
- **单调性守卫的执行层未定** ⇒ 裁决建议：commit-gate 内只做「命中 / 未命中」；「baseline ⊆ 当前实际失败集合」放 doctor 巡检层（否则每次 commit 跑两遍验证命令）。
- **命名撞车**：本仓已有 `add-known-failures-baseline.md`（bats 基线）+ `report_regression.sh` 对比机制 ⇒ 必须**复用其 diff/清单形态**，禁发明第二套语义（同名不同义必被误用）。
- **与 U7 的 doctor 巡检面重叠**（U7 空壳检测 vs U8 baseline 可清理 WARNING）⇒ 两者的检测面划界写进各自范围。
- 已改：AC5 降级为 design checklist；技术约束增「机制复用 + 两个必答裁决」。


**主题**: commit-gate 声明支持 baseline / known_failures

## 架构依据

`verify_commands` 是**硬门**：任一命令非 0 ⇒ 拒绝提交（`ADR-commit-verification-gate` D2）。⇒
**有存量红的仓无法声明门禁** ⇒ 门禁在有历史债的仓里只能关着。

实测（2026-11-26，CppTLM）：`./scripts/build/format.sh --check` 报 5 个文件需格式化，**全是本次未触碰的存量文件**
⇒ 该仓若声明 `format.sh --check` ⇒ 每次 commit 都被拒 ⇒ 实际只能不声明 ⇒ 门禁**完全不存在**（且无痕迹）。

**用户已裁决**（2026-11-27）：走 baseline / known_failures 机制。
**但 oracle 建议 11 要求先评估两个更便宜替代**（本提案把它们作为 design 阶段的**必答题**）：
① 先修掉那 5 个存量红（一次性成本，不引入制度）；② `verify_commands` 支持「仅暂存文件」占位符（schema 小改）。

**决策前置**：本提案**必须**是 `ADR-commit-verification-gate` 的 **Status Update**（改的是已签批 ADR 的判据语义
⇒ 属决策变更 ⇒ 走 SU，不走实现细节）。本 improvement 只负责**起草** SU 所需的设计与判据，**不直接改 ADR**。

## 范围

**In Scope**:

- **design 阶段必答题**（未答 ⇒ 不进入实现）：
  - 替代①：修存量红的成本 vs 制度成本（**给出本仓的实测数字**）；
  - 替代②：`verify_commands` 占位符（如「仅对暂存文件生效」）的最小 schema 改动量；
  - 取舍结论 + 理由（**不预设答案**）。
- **baseline 机制本体**（若裁决走它）：声明文件增加 `known_failures`（每条含命令 + 判定模式）⇒
  命令非 0 时，若失败**命中 baseline** ⇒ 视为通过（**检测 ≠ 拦截**在 baseline 内不适用：baseline 是显式放行）；
- baseline 的**单调性**要求：baseline 只能**减少**不能增长（新增失败必须红 ⇒ 强制修）⇒ 守卫断言 baseline 条目 ⊆ 当前实际失败集合；
- baseline 的**载体与机制复用**：与本仓既有 `add-known-failures-baseline.md`（bats 基线，`report_regression.sh` 对比机制）
  **对齐并复用其 diff/清单形态**，**禁**发明第二套语义（否则同名不同义 ⇒ 必被误用）；
  ⚠ **两处 design 裁决必答**：① 单调性守卫的**执行层**（commit-gate 内只做「命中 / 未命中」判定；
  「baseline ⊆ 当前实际失败集合」放 doctor 巡检层 —— 否则每次 commit 要跑两遍验证命令）；
  ② 是否**直接复用** `report_regression.sh` 的失败清单 diff 逻辑（复用 ⇒ 少一套机制）。
- doctor 巡检：baseline 中「已不再失败」的条目 ⇒ WARNING（可清理）；baseline 外的失败 ⇒ 硬红。

**Out of Scope**:

- 不改三判据的其它判据（暂存 / 写集）—— 拆判据属另案（`OC-1b`，待 SU）；
- 不改 D3 的「未声明 ⇒ 不设门禁」（另案）；
- 不实现「自动生成 baseline」（人工登记 + 守卫）；
- 不替用户仓修存量红（项目侧）。

## 关键场景

1. 声明含 baseline，命令非 0 但失败**命中 baseline** ⇒ 放行（并在输出里指出「命中 baseline 条目 N」）。
2. 声明含 baseline，命令非 0 且失败**不在** baseline ⇒ 拒绝（与今天一致）。
3. baseline 里某条目**已不再失败** ⇒ doctor WARNING（可清理），**不**阻断。
4. baseline 被**新增**条目以掩盖新失败 ⇒ 守卫红（单调性断言）。
5. 无 baseline 的声明 ⇒ 行为与今天**完全一致**（零回归）。

## 技术约束

- **须先有 ADR SU**（改已签批 ADR 的判据语义）⇒ 实现前 SU 必须 Accepted；
- baseline **只减不增**（单调）⇒ 守卫可机判；
- baseline 与 `tests/KNOWN_FAILURES.txt` **形态对齐**（不发明第二套语义）；
- 零回归：无 baseline 时行为**逐字节等价**；
- 不引入「按时间窗口忽略失败」这类不可判定的机制。

## SU 落地后的口径订正（2026-11-27 · planner）

治理仓 ADR 的 **Status Update 已 Accepted**（D10 + V20–V25）⇒ 本提案的前置**已满足**。
实现按 SU 的口径分两层，**不得**再合并成一件事：

| 层 | 归属仓 | 交付 | 判据载体 |
|---|---|---|---|
| ① commit 路径的命中判定 | **治理仓** | `lib/commit-gate.ts` 读 `known_failures` ⇒ 命中放行 / 未命中仍拒；`match` 特异性守卫；运行时留痕 | 治理仓 `bun test tests/`（**不**在 rdd-workflow） |
| ② 巡检层（防腐坏 + 可清理提示） | 治理仓 doctor **或** 使用方仓 CI（**载体自选但必须存在**） | 集合比对；缺席 ⇒ `known_failures` 字段无效 ⇒ 退回硬门 | 同上 |
| ③ 声明内容守卫（**防增**） | **治理仓** | D9① 形态扩展到 `known_failures` 字段：逐项相等断言，改清单 ⇒ 守卫红 | 同上 |
| ④ D9⑰ 登记 + 回滚清单同批 | **治理仓** | D9⑰（ADR 表（真源）+ 三处载体同批）+ `.rddf/rollback/commit-gate.json` 同批更新（SU D10⑥） | 同上 |
| ⑤ 使用方仓的巡检载体 | rdd-workflow（**可选**） | doctor category（形态对齐 `tests/KNOWN_FAILURES.txt` 的集合比对） | 本仓 `./test.sh` |

⚠ **「baseline 不能增」不由 ⊆ 断言交付**（同一次提交里「制造新失败 + 登记对应条目」仍能通过 ⊆）⇒ 由 ③ 承担。

## 验收标准

- [ ] **AC1（红→绿）** 新增 `tests/unit/test_commit_gate_baseline.ts`（治理仓侧）：命中 baseline 的失败 ⇒ **放行**；
      未命中 ⇒ **拒绝** ⇒ 修复前红 ⇒ 修复后绿；
- [ ] **AC2（红→绿）** 同文件用例：baseline 条目**已不再失败** ⇒ doctor WARNING 且不阻断；
- [ ] **AC3（单调）** 同文件用例：baseline 新增条目以掩盖新失败 ⇒ 守卫红（断言 baseline ⊆ 当前实际失败集合）；
- [ ] **AC4（零回归）** 既有 commit-gate 用例**零回归**（`bun test tests/` 全绿）；
- [ ] **AC5（SU 前置 —— design checklist，非测试）** 实现落地前 `docs/adr/ADR-commit-verification-gate.md` 的
      **Status Update** 已存在且 Status 已转 ⇒ **跨仓不可机判**（本仓 CI 读不到治理仓文档）⇒
      **降级为 design 阶段 checklist 项**，**不做**测试断言（review 判定：永远红或永远 skip 的 AC 是假判据）；
- [ ] **AC6（判别力）** 把 baseline 判定短路为「恒放行」⇒ AC1 的第 2 个用例必须红；
- [ ] **AC7（门）** `./test.sh --gates` 与 `./test.sh --unit` 全绿（治理仓侧另跑 `bun test tests/`）。

## Capabilities

- MUST: 有存量红的仓也能声明门禁，且**新失败**仍然阻断。
- MUST: baseline 只减不增（掩盖新失败必须红）。
- MUST: 无 baseline 时行为与今天完全一致。
- MUST NOT: 引入时间窗口类不可判定机制；不发明与 `KNOWN_FAILURES.txt` 平行的第二套语义。
- MUST: 实现前 `ADR-commit-verification-gate` 的 Status Update 已 Accepted。

## Impact

| 面 | 影响 |
|---|---|
| 治理仓 `lib/commit-gate.ts` + `plugins/commit-gate.ts` | baseline 判定（**机制面 ⇒ builder 实施**） |
| 治理仓 `docs/adr/ADR-commit-verification-gate.md` | **Status Update**（**architect 域 ⇒ 须先 SU**） |
| 声明 schema | `known_failures` 字段（schema 扩展） |
| doctor | baseline 巡检（已不再失败的条目 WARNING） |
| 使用方仓 | 各仓自行登记 baseline（人工） |
