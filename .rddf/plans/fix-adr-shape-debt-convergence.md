# fix-adr-shape-debt-convergence Implementation Plan (P0-1)

> **For agentic workers:** Implement this plan task-by-task, following the TDD 5-step structure below. Steps use checkbox (`- [ ]`) syntax for tracking.

> **⚠️ 本 change 立项后**分批推进**（实施纪律见 proposal §实施纪律）**：每批 ≤10 文件、每批单独 commit。
> 原因：存量收敛若一次性做会变成 50+ 文件重写（ADR-0060 明确反对）；且 ratchet 基线要求每批修改后
> 立刻 `--write-baseline`，否则下一批的 diff 会把上一批的修改当成新 finding。

**Goal:** 让 ADR 形态门从「永远 opt-in」变成「可用的增量门」—— 存量 findings 冻结进 per-file × per-signal 基线，
CI 只拦**新增**形态债；新增 ADR 必洁；判据（信号集 / 预算 / severity）一条不放宽。

**Architecture:** 三层改动 ——
① **基线机制**（`_lib/arch_quality_gate.py`）：per-file × per-signal 清单 + 增量比对 + ratchet 守卫；
② **CLI 语义**（`skills/rdd-arch/scripts/adr_shape_check.sh`）：新增 `--baseline` / `--diff-baseline` / `--summary` / `--write-baseline`；
③ **状态可机读**（`_lib/adr_index_generator.py`）：`extract_metadata` 增 `status_class`（6 值枚举）+ `status_raw`（原文不动）。

**Tech Stack:** Python 3（`_lib/`，mypy strict）、bash（`skills/rdd-arch/scripts/`）、pytest、GitHub Actions。

---

## File Structure

### Production Code (MODIFY)

| File | Responsibility |
|---|---|
| `_lib/arch_quality_gate.py` | 基线读写 + 增量比对 + ratchet 守卫（**只加基线逻辑，不改信号集 / 预算 / severity**） |
| `skills/rdd-arch/scripts/adr_shape_check.sh` | 4 个新 flag；判定逻辑仍委托 `_lib/arch_quality_gate.py`（脚本不得内联复制规则） |
| `_lib/adr_index_generator.py` | `extract_metadata` 增 `status_class` / `status_raw` 两键 |
| `docs/adr/ADR-0055-guide-orchestrator-session-event-bus.md` | Status 行去掉 commit 号（触发 `ARCH_ADR_STATUS_MAX`） |
| `.github/workflows/test.yml` | 新增 `ARCH_SHAPE_CHECK=yes` + `--diff-baseline` step（**必须实际执行**，skip 不算通过） |

### Production Code (CREATE)

| File | Responsibility |
|---|---|
| `docs/adr/.adr-shape-baseline.json` | per-file × per-signal 冻结清单（committed，随语料演进） |

### Tests (MODIFY)

| File | Responsibility |
|---|---|
| `tests/unit/test_arch_quality_gate.py` | 新增用例：① 基线非空守卫 ② 增量只报新 finding ③ `--write-baseline` 拒绝新增条目 ④ `status_class` 分类 |

---

## Pre-flight

- [ ] **Step 0.1: 记录当前基线事实（供实施期对照）**

```bash
bash skills/rdd-arch/scripts/adr_shape_check.sh --all
```

Expected（2026-11-24 实测）: 63 份正式 ADR（不含 `ADR-0000-template.md`）、**163** 项 findings 分布在 62 个文件、9 个信号
（`missing_verification` 56 / `missing_section` 25 / `alternatives_table_no_conclusion_column` 24 / `shape_sprawl_heading` 19 /
`line_budget` 17 / `alternatives_table_missing` 10 / `process_log_heading` 9 / `verification_section_empty` 2 / `process_log` 1）。

> ⚠️ 这张表**随语料漂移，不是判据**。实施时以实测为准，不要拿它写死进代码或测试。

- [ ] **Step 0.2: 确认判据真源与不可动的边界**

```bash
grep -n 'def adr_shape_findings' -A 20 _lib/arch_quality_gate.py
grep -n '_DEFAULT_ADR_LINE_LIMIT\|_DEFAULT_ADR_STATUS_MAX' _lib/arch_quality_gate.py
```

Expected: 判据唯一真源 = `_lib/arch_quality_gate.py::adr_shape_findings()`；预算 = 250 行 / 200 字符（Status 行）。
**本 change 不允许改这两处**（改了 = 放宽判据 = 需要新 ADR）。

---

### Task 1: 基线文件 + 增量比对（核心）

**Files:**
- Modify: `_lib/arch_quality_gate.py`
- Create: `docs/adr/.adr-shape-baseline.json`
- Test: `tests/unit/test_arch_quality_gate.py`

- [ ] **Step 1.1: 先写失败测试** —— 基线非空守卫

新增用例：`baseline 为空 dict` ⇒ 增量模式 **exit 2**（不是「全绿」）。
变异验证：把基线清空 ⇒ 必须报错退出，**不得**返回 0。

- [ ] **Step 1.2: 实现基线读写**（`_lib/arch_quality_gate.py`）

数据结构（**per-file × per-signal，不是标量总数** —— 标量在 ADR 增删后无意义）：

```json
{
  "ADR-0055-guide-orchestrator-session-event-bus.md": {
    "line_budget": {"detail": "453 行 > 250 行", "recorded_at": "2026-11-24"}
  }
}
```

新增 3 个公共入口（命名可微调，语义固定）：
- `read_shape_baseline(project_root) -> dict`
- `write_shape_baseline(project_root, findings) -> None`（**唯一写路径**；其它路径一律只读）
- `diff_shape_findings(findings, baseline) -> list[ShapeFinding]`（只返回 baseline 中不存在的 finding）

- [ ] **Step 1.3: 先写失败测试** —— 增量只报新 finding

新增用例：给某 ADR 加一节 `## v9 修订日志` ⇒ 增量模式只报**这一条**（存量折叠成一行计数）。

- [ ] **Step 1.4: 实现增量比对 + 让 Step 1.1/1.3 的测试转绿**

- [ ] **Step 1.5: 生成初始基线**

```bash
bash skills/rdd-arch/scripts/adr_shape_check.sh --all --write-baseline
```

Expected: 写出 `docs/adr/.adr-shape-baseline.json`，条目数 = 有 finding 的文件数（当前 62）。

---

### Task 2: ratchet 三守卫

**Files:**
- Modify: `_lib/arch_quality_gate.py`
- Test: `tests/unit/test_arch_quality_gate.py`

- [ ] **Step 2.1: 守卫① —— 非空**：基线条目数 > 0，否则 exit 2（已含在 Step 1.1）
- [ ] **Step 2.2: 守卫② —— 单调不增**：`--write-baseline` 在「新结果含基线中不存在的 finding」时**拒绝写入并 exit 1**
      （变异验证：手工往基线塞一条不存在的 finding ⇒ 拒绝）
- [ ] **Step 2.3: 守卫③ —— 单一写路径**：只有 `--write-baseline` 能写基线文件；其它入口写 ⇒ 报错
      （理由：本仓刚被 `KNOWN_FAILURES.txt` 截断咬过一次 —— 「可被掏空的数据」必须有机械守卫）

---

### Task 3: CLI 语义补全

**Files:**
- Modify: `skills/rdd-arch/scripts/adr_shape_check.sh`

- [ ] **Step 3.1: 新增 4 个 flag**：`--baseline`（读基线）/ `--diff-baseline`（增量）/ `--summary`（折叠计数）/ `--write-baseline`（写基线）
- [ ] **Step 3.2: `--help` 写明**：`--diff-baseline` 与 `alternatives_table_missing` / `missing_section` 的**互斥关系**
      （补章节会换成另一个信号，净收益 0 —— 避免实施者用「造假备选表」凑数）
- [ ] **Step 3.3: 判定逻辑仍委托 `_lib/arch_quality_gate.py`**（脚本不得内联复制规则；脚本头注释已声明此约束）
- [ ] **Step 3.4: 退出码语义**：`--diff-baseline` 当前语料 ⇒ exit 0；出现新 finding ⇒ exit 1；基线非法/为空 ⇒ exit 2

---

### Task 4: `status_class` / `status_raw`（P2-5 状态可机读）

**Files:**
- Modify: `_lib/adr_index_generator.py`
- Test: `tests/unit/test_arch_quality_gate.py`（或该模块的既有测试文件）

- [ ] **Step 4.1: 先写失败测试** —— 分类枚举 ≤ 6 个取值，`status_raw` 与原文逐字符相等
- [ ] **Step 4.2: 实现**：`extract_metadata` 增两键
      - `status_class` ∈ {`draft`, `proposed`, `accepted`, `amended`, `superseded`, `rejected`}
      - `status_raw` = Status 行原文（**逐字符保留**，分类不得丢信息）
- [ ] **Step 4.3: 对全部 63 份正式 ADR 运行分类** ⇒ 取值集 ≤ 6
      （40 份 ADR 的 Status 是自由文本 —— 分类在**生成器侧**完成，**不改任何 ADR 的 Status 行**）

---

### Task 5: ADR-0055 Status 行去 commit 号 + 重建索引

**Files:**
- Modify: `docs/adr/ADR-0055-guide-orchestrator-session-event-bus.md`（**仅 Status 行**）

- [ ] **Step 5.1: 现状取证**

```bash
grep -nE 'commit|@[0-9a-f]{7}' docs/adr/ADR-0055-guide-orchestrator-session-event-bus.md
```

Expected: Status 行含 `commit f5eb49c / bf6a7fc / 89117dc` ⇒ 触发 `ARCH_ADR_STATUS_MAX`（200 字符预算）。
- [ ] **Step 5.2: 只改 Status 行** —— 去掉 commit 号，**保留**「已实施」与「Superseded by ADR-0063」语义
- [ ] **Step 5.3: 重建 ADR 索引**（Status 行变了 ⇒ 索引内容变）
      ⚠️ 不重建会让 `test_adr_index_gate.py` 的逐字节断言变红

---

### Task 6: CI 接入（增量模式，存量不阻断）

**Files:**
- Modify: `.github/workflows/test.yml`

- [ ] **Step 6.1: 新增 step**：`ARCH_SHAPE_CHECK=yes` + `adr_shape_check.sh --all --diff-baseline`
      —— **该 step 必须实际执行**（`skip` 不算通过；AC 明确写死这一点）
- [ ] **Step 6.2: 确认 step 在 PR 中会跑**（不是 `if:` 条件跳过）
- [ ] **Step 6.3: 本地复现 CI 行为**：`ARCH_SHAPE_CHECK=yes bash skills/rdd-arch/scripts/adr_shape_check.sh --all --diff-baseline` ⇒ exit 0

---

### Task 7: 负例夹具 + 判据未被放宽的证明

**Files:**
- Test: `tests/unit/test_arch_quality_gate.py`

- [ ] **Step 7.1: 每条新信号配双向夹具** —— 「精确踩它」+「形似但不该报」各一份（沿用 ADR-0060 V-11 的模式）
- [ ] **Step 7.2: 判据未被放宽的自证**

```bash
git diff -- _lib/arch_quality_gate.py | grep -E '^[+-].*(missing_verification|missing_section|line_budget|_DEFAULT_ADR_)' 
```

Expected: **无输出**（只应有基线读写与 Status 解析相关的改动）

---

## 回滚

回滚 `_lib/arch_quality_gate.py` + `skills/rdd-arch/scripts/adr_shape_check.sh` + `_lib/adr_index_generator.py` 的改动，
删除 `docs/adr/.adr-shape-baseline.json`，还原 ADR-0055 的 Status 行并重建索引。无外部依赖，无数据迁移。

## 不做（明确排除）

- 为存量 ADR 补写 Verification 判据（伪造证据；ADR-0060 Out Scope「不追溯」）
- 修改 `adr_shape_findings` 的信号集 / 预算 / severity（**它们是 ADR-0060 的已签批决策**）
- 修改 ADR-0060 的 Decision（不改判据 ⇒ 无需新 ADR）
- 一次性改 50+ 份存量 ADR（分批推进，每批 ≤10 文件 + 单独 commit）
- `docs/adr/README.md` 散文段纳入生成（属 `fix-doc-drift-residual` P2-1）

