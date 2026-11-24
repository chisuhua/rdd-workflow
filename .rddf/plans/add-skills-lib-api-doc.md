# add-skills-lib-api-doc Implementation Plan (P0-1)

> **For agentic workers:** Implement this plan task-by-task, following the TDD 5-step structure below. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `skills/_lib/` 的**双层**模块目录文档 —— 仓库根 `_lib/`（真实现层）+ `skills/_lib/`（shim 层），
外加 1 页 `INDEX.md` 速查表，让新 skill 作者不必 grep 源码反向发现 helper。

**Architecture:** **纯文档，零代码改动**。README 的目录数据**不得手抄** —— 必须由脚本从磁盘采集，
否则文档自己会变成新的漂移源（本仓已因 `KNOWN_FAILURES.txt` 硬编码计数被守卫咬过一次）。

**Tech Stack:** Markdown（2 个新文件）、bash（目录采集）、pytest/ruff（门禁）。

---

## File Structure

### Production Code (CREATE)

| File | Responsibility |
|---|---|
| `skills/_lib/README.md` | 6 节：§1 Overview（两层结构）/ §2 Module Catalog（双层分栏）/ §3 Helper Entry Points（project_root 3 层）/ §4 ADR References / §5 Onboarding Guide（≥5 步）/ §6 Cross-Layer Consistency |
| `skills/_lib/INDEX.md` | 1 页速查表：helper + import path + 用途，按 use case 分组 |

### Production Code (MODIFY)

**无。** 本 change 不改任何 `.sh` / `.py` / `.bats`（MN-API-1 / MN-API-2）。

---

## Pre-flight

- [ ] **Step 0.1: 采集目录事实（脚本，不手抄）**

```bash
ls -1 _lib/*.py | wc -l          # 期望 89
ls -1 _lib/*.sh | wc -l          # 期望 20
find _lib -maxdepth 1 -mindepth 1 -type d ! -name '__pycache__' | wc -l   # 期望 10
ls -1 skills/_lib/*.sh | wc -l   # 期望 16
ls -1 skills/_lib/*.py | wc -l   # 期望 19（含 __init__.py）
find skills/_lib -maxdepth 1 -mindepth 1 -type d ! -name '__pycache__' | wc -l   # 期望 6
```

> ⚠️ 这些数字会随语料漂移 ⇒ **只能写进 README 的说明文字，不能写进断言**。
> AC-API-3 的判据是「表格行数 ≥ 46 且出现两层对照表」，不是「等于某个数字」。

- [ ] **Step 0.2: 核对契约与测试文件真实存在**

```bash
ls _lib/_resolve_project_root_contract.yaml
ls tests/unit/test_resolve_project_root_contract_bash.sh
ls tests/unit/test_resolve_project_root_contract_python.py
```

Expected: 三者都存在（AC-API-4 / AC-API-7 引用它们 —— 不得臆造文件名）。

---

### Task 1: 采集模块清单（脚本化，避免手抄漂移）

- [ ] **Step 1.1: 采集真实现层的模块名 + 首行 docstring**

```bash
python3 - <<'PY'
from pathlib import Path
for p in sorted(Path('_lib').glob('*.py')):
    head = p.read_text(encoding='utf-8').splitlines()[:3]
    doc = next((l.strip().strip('#').strip() for l in head if l.strip().startswith(('"""', "'''"))), '')
    print(p.name, '|', doc)
PY
```

Expected: 89 行输出（每行 = 模块名 + 用途短语）。**用途短语缺失时留空**，不臆造。
- [ ] **Step 1.2: 采集子包清单**（10 个：`cli core dashboard iteration loop plugins schedulers schemas templates verifier`）
- [ ] **Step 1.3: 采集 shim 层清单**（16 `.sh` + 19 `.py` + 6 子目录）

---

### Task 2: 写 `skills/_lib/README.md`

- [ ] **Step 2.1: §1 Overview —— 两层结构**
      表格：真实现层（仓库根 `_lib/`）/ shim 层（`skills/_lib/`）+ `__path__` 加宽说明
- [ ] **Step 2.2: §2 Module Catalog —— 双层分栏**
      §2.1 真实现层：≥30 条，覆盖**全部 10 个子包**；
      §2.2 shim 层：逐条列全（16 `.sh` + 19 `.py`）
- [ ] **Step 2.3: §3 Helper Entry Points —— project_root 的 3 层**
      bash `_resolve_project_root` / skill wrapper / CLI dispatcher；指向 `_lib/_resolve_project_root_contract.yaml`
- [ ] **Step 2.4: §4 ADR References**（≥3 个，且每个编号在 `docs/adr/` 磁盘上存在）
- [ ] **Step 2.5: §5 Onboarding Guide —— ≥5 步，编号连续**
- [ ] **Step 2.6: §6 Cross-Layer Consistency**（引用两个真实契约测试文件）
- [ ] **Step 2.7: 自检** —— 表格行数 ≥ 46、章节数 = 6、行数 ≥ 150

---

### Task 3: 写 `skills/_lib/INDEX.md`

- [ ] **Step 3.1: 1 页速查表** —— helper + import path + 用途，按 use case 分组
- [ ] **Step 3.2: 自检** —— 行数 ≤ 120（是「1 页」不是「一本」）

---

### Task 4: 收口验证

- [ ] **Step 4.1: 文档漂移守卫** —— `python3 -m pytest tests/unit/test_doc_contracts.py -q` 全绿
      （该守卫禁止 README/AGENTS.md 硬编码「N 个」类漂移计数 —— README 里的数字必须写成「约」或注明采集日期）
- [ ] **Step 4.2: `python3 -m ruff check skills/_lib/` 通过**（⚠️ 仓库门禁口径是 `skills/_lib/`，**不是** `.` —— `ruff check .` 在主仓同样有 533 个既存错误，与本 change 无关）
- [ ] **Step 4.3: `rddf doctor --category docs-consistency` 无新增 finding**
      （会扫文档里的 ADR 编号引用，对磁盘缺失报 WARNING）
- [ ] **Step 4.4: 逐条勾回 `proposal.md` 的 8 条 AC**
- [ ] **Step 4.5: 全量回归门** `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression`
- [ ] **Step 4.6: 归档** `bash skills/rdd-builder/scripts/phase3_archive.sh add-skills-lib-api-doc`

---

## 回滚

删除 `skills/_lib/README.md` 与 `skills/_lib/INDEX.md` 两个新文件即可 —— 无代码改动、无状态文件、无副作用。

## 不做（明确排除）

- 任何 `.sh` / `.py` / `.bats` 文件（MN-API-1：纯文档化）
- 新增依赖（MN-API-2：纯 markdown）
- 每个 module 的详细 API doc（MN-API-3：那是 docstring 的活）
- 修改 `skills/_lib/__init__.py` 的 `__path__` 语义（现状已正确，文档只需描述）
