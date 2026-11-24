# fix-adr-shape-debt-convergence Implementation Plan

> **For agentic workers:** 每个 Task 按 TDD 5 步推进，checkbox 即进度。

> **⚠️ 分批纪律**（proposal §实施纪律）：存量收敛分批推进，每批 ≤10 文件、每批单独 commit；
> 每批修改后必须 `--write-baseline`，否则下一批的 diff 会把上一批的修改当成新 finding。
> **存量收敛不计入本项完成判据** —— 本项的完成判据是「门可用」（基线冻结 + 增量只报 + 判据不放宽）。

**Goal:** 让 ADR 形态门从「永远 opt-in」变成「可用的增量门」—— 存量 findings 冻结进 per-file × per-signal 基线，
CI 只拦**新增**形态债；新增 ADR 必洁；判据（信号集 / 预算 / severity）一条不放宽。

**Architecture:** 三层改动 ——
① **基线机制**（`_lib/arch_quality_gate.py`）：per-file × per-signal 清单 + 增量比对 + ratchet 守卫；
② **CLI 语义**（`skills/rdd-arch/scripts/adr_shape_check.sh`）：`--baseline` / `--diff-baseline` / `--summary` / `--write-baseline`；
③ **状态可机读**（`_lib/adr_index_generator.py`）：`extract_metadata` 增 `status_class`（6 值枚举）+ `status_raw`（原文不动）。

**Tech Stack:** Python 3（`_lib/`）、bash（`skills/rdd-arch/scripts/`）、pytest、GitHub Actions。

---

## File Structure

| File | Responsibility |
|---|---|
| `_lib/arch_quality_gate.py` | 基线读写 + 增量比对 + ratchet 守卫（**只加基线逻辑，不改信号集 / 预算 / severity**） |
| `skills/rdd-arch/scripts/adr_shape_check.sh` | 4 个新 flag；判定逻辑仍委托 Python（脚本不得内联复制规则） |
| `_lib/adr_index_generator.py` | `extract_metadata` 增 `status_class` / `status_raw` 两键 |
| `docs/adr/.adr-shape-baseline.json` | per-file × per-signal 冻结清单（committed，随语料演进，**只降不升**） |
| `docs/adr/ADR-0055-*.md` | Status 行去掉 commit 号（触发 `ARCH_ADR_STATUS_MAX`） |
| `.github/workflows/test.yml` | `ARCH_SHAPE_CHECK=yes` + `--diff-baseline` step（**必须实际执行**） |
| `tests/unit/test_arch_quality_gate.py` | 基线四守卫 + 双向夹具 |
| `tests/unit/test_adr_index_generator.py` | `status_class` 枚举 / 优先级 / `status_raw` 逐字符 |

---

## Task 1: 基线文件 + 增量比对（核心）

**Files:** Modify `_lib/arch_quality_gate.py`；Create `docs/adr/.adr-shape-baseline.json`

- [x] **Step 1: Write the failing test** —— 基线非空守卫 + 增量只报新 finding

  新增 `test_shape_baseline_is_per_file_per_signal` / `test_shape_baseline_empty_is_a_hard_error` /
  `test_shape_diff_reports_only_the_new_finding`；判据：空基线 ⇒ `ShapeBaselineError`（CLI exit 2），
  给 ADR 加一节 `## v9 修订日志` ⇒ 只报这一条。

- [x] **Step 2: Run test to verify it fails** —— `pytest tests/unit/test_arch_quality_gate.py -k 'baseline or diff'`

  实测：`ImportError: cannot import name 'ShapeBaselineError'`（red，符合预期）。

- [x] **Step 3: Write minimal implementation** —— `_lib/arch_quality_gate.py` 增 `ShapeBaselineError` +
  `shape_baseline_path` / `read_shape_baseline` / `diff_shape_findings` / `write_shape_baseline`；
  按 `(file, signal)` **计数**比对，不按 `detail` 文本（文案变化不得读成新增债务）。

- [x] **Step 4: Run test to verify it passes** —— `pytest tests/unit/test_arch_quality_gate.py -q` ⇒ 59 passed。

- [x] **Step 5: Defer commit** —— 推迟到 change 级 commit（分批纪律：本批与 T2/T3 同 commit）。

## Task 2: ratchet 三守卫

**Files:** Modify `_lib/arch_quality_gate.py`；Test `tests/unit/test_arch_quality_gate.py`

- [x] **Step 1: Write the failing test** —— 守卫①非空 / ②单调不增（拒绝写入且文件不变）/ ③单一写路径
  （只读模式跑完后基线字节不变）

- [x] **Step 2: Run test to verify it fails** —— 守卫②③对应实现尚不存在 ⇒ 红。

- [x] **Step 3: Write minimal implementation** —— 守卫①在 `read_shape_baseline(require_non_empty=True)`；
  守卫②在 `write_shape_baseline` 内**写盘前**比对并 raise（拒绝后文件字节不变）；
  守卫③：模块内只有 `write_shape_baseline` 打开基线的写路径（其余只读）。

- [x] **Step 4: Run test to verify it passes** —— `test_shape_write_baseline_refuses_growth` /
  `test_shape_read_only_modes_never_touch_the_baseline` 全绿；真语料变异：空基线 ⇒ exit 2、
  手工加新 finding 后 `--write-baseline` ⇒ exit 1 且 sha256 未变。

- [x] **Step 5: Defer commit**

## Task 3: CLI 语义补全

**Files:** Modify `skills/rdd-arch/scripts/adr_shape_check.sh`

- [x] **Step 1: Write the failing test** —— 4 个 flag 的端到端行为（`--baseline` 列出账本 /
  `--diff-baseline` 0·1·2 三态 / `--write-baseline` 成功与拒绝）；先红（旧脚本把 `--diff-baseline` 当文件名）。

- [x] **Step 2: Run test to verify it fails** —— 实测 `用法错误：--all 不能与显式文件同时使用`（4 个用例红）。

- [x] **Step 3: Write minimal implementation** —— 三模式互斥解析 + `--summary` 折叠；
  判定与基线逻辑全部委托 Python（脚本不内联规则）；`--help` 写明
  `alternatives_table_missing` 与 `missing_section` 的**互斥关系**（补章节只是换信号，净收益 0）。

- [x] **Step 4: Run test to verify it passes** —— `pytest tests/unit/test_arch_quality_gate.py -q` ⇒ 61 passed；
  真语料：`--diff-baseline` exit 0 / 空基线 exit 2 / 新增 ADR exit 1。

- [x] **Step 5: Defer commit**

## Task 4: `status_class` / `status_raw`（状态可机读）

**Files:** Modify `_lib/adr_index_generator.py`；Test `tests/unit/test_adr_index_generator.py`

- [x] **Step 1: Write the failing test** —— 枚举 ≤6 值、优先级参数化、`status_raw` 逐字符相等

- [x] **Step 2: Run test to verify it fails** —— 实测 `12 failed`（`KeyError: status_class` 族）。

- [x] **Step 3: Write minimal implementation** —— `classify_status()` + 优先级
  `superseded > rejected > amended > accepted > proposed > draft`（fallback 一律 `draft`：
  把未识别文本当成「已决」是更严重的错误）；`extract_metadata` 增两键，`status` 原值不动（索引逐字节不变）。

- [x] **Step 4: Run test to verify it passes** —— 全语料 63 份落 6 类内
  （superseded 5 / accepted 45 / amended 5 / proposed 3 / draft 5）；**未改任何 ADR 的 Status 行**。

- [x] **Step 5: Defer commit**

## Task 5: ADR-0055 Status 行去 commit 号 + 重建索引

**Files:** Modify `docs/adr/ADR-0055-*.md`、`docs/adr/README.md`（生成物）

- [x] **Step 1: Write the failing test** —— 判据取 AC-8：Status 行 `commit|@[0-9a-f]{7}` 命中必须为 0

- [x] **Step 2: Run test to verify it fails** —— 改前该行 182 字符、含 3 个 SHA ⇒ 命中 3（红）。

- [x] **Step 3: Write minimal implementation** —— **只改 Status 行**：去掉 3 个 SHA，保留
  「已采纳 + 已实施（v4.1 release，PR 1-4）」与「Superseded by ADR-0063」语义；
  随后 `python3 _lib/adr_index_generator.py --write docs/adr/README.md` 重建索引。
  SHA 仍可从 git 历史取回（`git log -p -- docs/adr/ADR-0055-*.md`），不是静默丢失。

- [x] **Step 4: Run test to verify it passes** —— Status 行 145 字符、命中 0；README 仅 1 行 diff；
  `pytest tests/unit/test_adr_index_gate.py tests/unit/test_adr_index_generator.py` ⇒ 26 passed。

- [x] **Step 5: Defer commit**

## Task 6: CI 接入（增量模式，存量不阻断）

**Files:** Modify `.github/workflows/test.yml`

- [x] **Step 1: Write the failing test** —— 静态判据：step 存在、无 `if:` 条件、`on:` 含 `pull_request`

- [x] **Step 2: Run test to verify it fails** —— 改前 `grep 'ADR shape gate'` 无命中（红）。

- [x] **Step 3: Write minimal implementation** —— 在 `Arch quality gate (strict mode)` 之后加
  `ADR shape gate (incremental, frozen baseline)`：`ARCH_SHAPE_CHECK=yes` + `--all --diff-baseline`。

- [x] **Step 4: Run test to verify it passes** —— `yaml.safe_load` 校验 step=26 且该 step 无 `if:`；
  本地复现 `ARCH_SHAPE_CHECK=yes … --diff-baseline` ⇒ exit 0。
  ⚠️ 「PR 中实际执行」只能由首次 push 后的 CI 日志确认（本次未 push，已在 tasks.md 标为待确认项）。

- [x] **Step 5: Defer commit**

## Task 7: 负例夹具 + 判据未被放宽的证明

**Files:** Test `tests/unit/test_arch_quality_gate.py`

- [x] **Step 1: Write the failing test** —— 双向夹具：「精确踩它」+「形似但不该报」

  新增：同信号多条只报**超出量**（基线 1 → 现 2 ⇒ 只报 1）、`detail` 文案变化不报、
  新增**干净** ADR 不报；既有信号的双向夹具保留（`## 验证` 认 / `### 验证 …` 不认、散文提及不报、结论列同义词认）。

- [x] **Step 2: Run test to verify it fails** —— 计数语义未实现时「超出量」用例报 2 条 ⇒ 红。

- [x] **Step 3: Write minimal implementation** —— 无新增实现（夹具锁的是 T1 的计数语义）

- [x] **Step 4: Run test to verify it passes** —— `pytest tests/unit/test_arch_quality_gate.py -q` ⇒ 61 passed；
  判据自证：`git diff -- _lib/arch_quality_gate.py | grep -E '^[+-].*(missing_verification|missing_section|line_budget|_DEFAULT_ADR_)'`
  ⇒ **无输出**，且 `git diff --stat` = 161 insertions / **0 deletions**。

- [x] **Step 5: Defer commit**

## 回滚

回滚 `_lib/arch_quality_gate.py` + `skills/rdd-arch/scripts/adr_shape_check.sh` + `_lib/adr_index_generator.py` 的改动，
删除 `docs/adr/.adr-shape-baseline.json`，还原 ADR-0055 的 Status 行并重建索引。无外部依赖，无数据迁移。

## 不做（明确排除）

- 为存量 ADR 补写 Verification 判据（伪造证据；ADR-0060 Out Scope「不追溯」）
- 修改 `adr_shape_findings` 的信号集 / 预算 / severity（ADR-0060 的已签批决策）
- 一次性改 50+ 份存量 ADR（分批推进，每批 ≤10 文件 + 单独 commit；不计入本项完成判据）
- `docs/adr/README.md` 散文段纳入生成（属 `fix-doc-drift-residual` P2-1）
