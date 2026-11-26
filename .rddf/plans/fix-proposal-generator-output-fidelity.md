# fix-proposal-generator-output-fidelity Implementation Plan

> **For agentic workers:** Implement this plan task-by-task, following the TDD 5-step structure below. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 proposal 生成器的「范围节」解析与 spec delta 的形态/语义**一次成型** —— 表格不再被逗号切碎、delta 不再产出退化形态、改既有 capability 的 change 产出 MODIFIED 而非 ADDED。

**Architecture:** 三处改动同批落地：① `generate_full_proposal.py` 的解析层（header 正则 / item 解析 / 删除逗号兜底 / 标题优先级）；② 新增两个**纯 stdlib 共享模块**（`_lib/spec_requirement_form.py` 形态判据单一真源、`_lib/openspec_version.py` 版本语义化比较）；③ `phase0_approval.sh` 的落盘层（delta 落点目录语义 + 临时文件/mv 半成品防护）。形态守卫在**生成时**拒绝退化形态；载体用**粗体头行**（`delta` / `语义要求`），与 ADR-0025 D6 的既有头部机制一致。

**Tech Stack:** Python 3（stdlib only）/ pytest / bash（`phase0_approval.sh`）/ openspec CLI（版本探测 + delta 语义）

> ⚠ **本仓附加的第 6 步**：凡拥有**变异类 AC**（AC4 / AC5 / AC12 / AC13）的 Task，在标准 5 步之后追加
> **Step 6: 变异验证（判别力证明）** —— 把实现改坏（退回旧行为 / 改退化分类器 / 版本比较退化为字符串比较）⇒ 对应用例**必须红**。
> 没有这一步的 Task，其「先红」可能来自「测试写错」而非「功能未实现」。

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/rdd-builder/scripts/generate_full_proposal.py` | 范围节解析（header 注解 / 表格行 / 归属规则 / 无逗号兜底）+ `generate_spec_delta()` 形态自检与 MODIFIED 生成 + 载体（粗体头行）解析 |
| `_lib/spec_requirement_form.py`（新） | 形态判据单一真源（无语义 Requirement 名 / 恒真 WHEN 的三条正则与谓词函数） |
| `_lib/openspec_version.py`（新） | `openspec --version` 的**语义化**解析与比较（`1.14.3 > 1.7.0` 必须成立） |
| `skills/rdd-builder/scripts/phase0_approval.sh` | delta 落点目录语义（`specs/<target-capability>/`）+ 临时文件 + 成功后 `mv` 的半成品防护 + 拒绝时非零退出 |
| `_lib/validate_delta_targets.py` | 接线点：目标存在性 + Scenario 守恒的**本地预检**（默认 target 解析随新目录语义同步） |
| `skills/rdd-builder/SKILL.md` | delta 契约段（载体 / MODIFIED 保留既有 Scenario / 版本口径） |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_spec_requirement_form.py`（改） | 改为**引用**共享判据模块（断言内容不变）—— 单一真源的载体 |
| `tests/unit/test_generate_full_proposal_scope_table.py`（新） | 表格范围节 / 混排 / header 注解 / 表内逗号 / Out 段重复（AC1、AC2、AC6） |
| `tests/unit/test_generate_full_proposal_corpus.py`（新） | 语料 golden snapshot 断言 + 形态标签表 + 动态计数（AC4） |
| `tests/unit/test_spec_delta_generator_shape.py`（新） | 形态守卫三类拒绝 + 无误拒（AC7、AC12） |
| `tests/unit/test_spec_delta_generator_modified.py`（新） | 载体 / MODIFIED 目标 / Scenario 守恒 / 版本分支（AC8、AC9、AC13） |
| `tests/unit/test_rdd_builder_skill_contract.py`（新） | SKILL.md delta 契约三锚点（AC11） |
| `tests/integration/test_phase0_partial_artifact.bats`（新） | 拒绝时无空文件 / 无半成品 / 可重试（AC14）+ 跨轴端到端（AC15） |

---

### Task 1: 形态判据共享模块（D-2 · AC10）

**Files:**
- Create: `_lib/spec_requirement_form.py`
- Modify: `tests/unit/test_spec_requirement_form.py`（改为 import 共享判据，**断言内容不变**）

- [ ] **Step 1: Write the failing test**

在 `tests/unit/test_spec_requirement_form.py` 末尾追加：

```python
def test_generator_and_guard_share_one_predicate_source() -> None:
    """单一真源：守卫与生成器引用同一模块 ⇒ 复制第二份即红。"""
    import importlib

    from _lib import spec_requirement_form as shared

    guard = importlib.import_module("tests.unit.test_spec_requirement_form")
    assert guard._DEGRADED_REQUIREMENT_NAME.pattern == shared.DEGRADED_REQUIREMENT_NAME.pattern
    assert guard._TAUTOLOGICAL_WHEN.pattern == shared.TAUTOLOGICAL_WHEN.pattern
    assert guard._MEANINGLESS_REQUIREMENT.pattern == shared.MEANINGLESS_REQUIREMENT.pattern
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_spec_requirement_form.py -q`
Expected: FAIL —— `ModuleNotFoundError: No module named '_lib.spec_requirement_form'`

- [ ] **Step 3: Write minimal implementation**

创建 `_lib/spec_requirement_form.py`：

```python
"""形态判据的**单一真源** —— 生成器与仓库的形态守卫共用。

判据来源：本仓 `tests/unit/test_spec_requirement_form.py`（2026-11 起）。
上移为共享模块的理由：生成器仍在产出被守卫拒绝的形态（`acceptance-N` / `capability-N`
需求名 + 恒真 WHEN）⇒ 生成器必须能引用**同一份**判据，否则两处实现必然漂移。
"""
from __future__ import annotations

import re

#: 判据 ① —— 无语义的 Requirement 名（AC 序号）。
MEANINGLESS_REQUIREMENT = re.compile(r"^### Requirement: acceptance-\d+\s*$", re.MULTILINE)

#: 判据 ① 的**全仓版** —— `acceptance-N` 与 `capability-N` 是同一形态退化族的两种命名。
DEGRADED_REQUIREMENT_NAME = re.compile(
    r"^### Requirement: (?:acceptance|capability)-\d+\s*$", re.MULTILINE
)

#: 判据 ② —— 恒真的 Scenario WHEN（对任何 change / feature 都成立）。
TAUTOLOGICAL_WHEN = re.compile(
    r"^- \*\*WHEN\*\* the (?:change|feature|it) is applied\s*$", re.MULTILINE
)


def find_degraded_requirements(text: str) -> list[str]:
    """返回命中的退化 Requirement 名（去重、保序）。"""
    names: list[str] = []
    for m in DEGRADED_REQUIREMENT_NAME.finditer(text):
        name = m.group(0).strip().split(":", 1)[1].strip()
        if name not in names:
            names.append(name)
    return names


def find_tautological_whens(text: str) -> list[str]:
    """返回命中的恒真 WHEN 行（去重、保序）。"""
    out: list[str] = []
    for m in TAUTOLOGICAL_WHEN.finditer(text):
        line = m.group(0).strip()
        if line not in out:
            out.append(line)
    return out


def is_degraded(text: str) -> bool:
    """delta 文本是否含退化形态（生成时守卫的判定入口）。"""
    return bool(find_degraded_requirements(text) or find_tautological_whens(text))
```

然后把 `tests/unit/test_spec_requirement_form.py` 顶部的三条正则**替换**为从共享模块导入（**断言内容不变**）：

```python
from _lib.spec_requirement_form import (
    DEGRADED_REQUIREMENT_NAME as _DEGRADED_REQUIREMENT_NAME,
    MEANINGLESS_REQUIREMENT as _MEANINGLESS_REQUIREMENT,
    TAUTOLOGICAL_WHEN as _TAUTOLOGICAL_WHEN,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_spec_requirement_form.py -q`
Expected: PASS（既有断言 + 新增「单一真源」断言）

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更在 archive 阶段统一提交。

---

### Task 2: 范围节解析 —— header 注解 + 表格行 + 归属规则（AC1）

**Files:**
- Modify: `skills/rdd-builder/scripts/generate_full_proposal.py:28-30`（header 正则）、`:112-150`（item 解析）
- Test: `tests/unit/test_generate_full_proposal_scope_table.py`（新建）

- [ ] **Step 1: Write the failing test**

新建 `tests/unit/test_generate_full_proposal_scope_table.py`：

```python
"""范围节解析的纯表格 / 混排 / header 注解形态（AC1）。"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_SCRIPT = _ROOT / "skills" / "rdd-builder" / "scripts" / "generate_full_proposal.py"
_spec = importlib.util.spec_from_file_location("gen_fp", _SCRIPT)
gen_fp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_fp)


def _md(body: str) -> str:
    return f"## 范围\n\n{body}\n"


def test_table_only_section_yields_one_item_per_row() -> None:
    md = _md("""**In Scope（3 项）**

| # | 改动 | 落点 |
|:--:|---|---|
| 1 | `a` | `x.hh` |
| 2 | `b` | `y.hh` |
| 3 | `c` | `z.hh` |

**Out of Scope**

- 不做 `d`
""")
    in_items, out_items = gen_fp._extract_scope_items(md)
    assert len(in_items) == 3
    assert all("|" not in i for i in in_items)
    assert out_items == ["不做 `d`"]


def test_annotated_header_is_not_an_item() -> None:
    md = _md("""**In Scope（6 项 · contract 面）**

- 一项

**Out of Scope**

- 二项
""")
    in_items, _ = gen_fp._extract_scope_items(md)
    assert in_items == ["一项"]


def test_table_under_bullet_stays_attached() -> None:
    md = _md("""**In Scope**

- 父项

  | 列 | 值 |
  |---|---|
  | a | b |

**Out of Scope**

- 不做
""")
    in_items, _ = gen_fp._extract_scope_items(md)
    assert len(in_items) == 1
    assert "父项" in in_items[0]


def test_out_scope_appears_once() -> None:
    md = _md("""**In Scope**

- 一项

**Out of Scope**

- 不做 `d`
""")
    _, out_items = gen_fp._extract_scope_items(md)
    assert out_items == ["不做 `d`"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_generate_full_proposal_scope_table.py -q`
Expected: FAIL —— 纯表格节返回 0 条（或被逗号兜底切成碎片）；带括号注解的 header 被当成条目。

- [ ] **Step 3: Write minimal implementation**

① header 正则允许尾部括号/方括号注解：

```python
_SCOPE_HEADER_RE = re.compile(
    r"^[\s#*\-]*((?:out\s+of|out|in)\s+scope)"
    r"(?:[\s*（(\[【][^\n]*)?[\s*:：]*$",
    re.IGNORECASE,
)
```

② 在 `_extract_scope_items` 的循环里，**先**判定「当前行是表格数据行」：

```python
_TABLE_ROW_RE = re.compile(r"^\|.*\|$")
_TABLE_ALIGN_RE = re.compile(r"^\|[\s:|-]+\|$")
```

表格行（排除对齐行）⇒ **在该节无任何 bullet/编号条目时**各自成条目；否则**归入上一个条目**（与既有 spec
`generator-scope-extraction` 的「bullet 下的表格归该 bullet」一致）：

```python
        if _TABLE_ROW_RE.match(stripped) and not _TABLE_ALIGN_RE.match(stripped):
            if not _TABLE_ALIGN_RE.match(stripped) and current == "in" and not in_items and not pending:
                # 纯表格节（该节尚无任何条目）⇒ 每行一个条目
                pending = stripped.strip("|").strip()
                pending_scope = current
                continue
            # 已有条目 ⇒ 归入上一个条目（沿既有 spec 语义）
            if pending is not None:
                pending += "\n" + stripped
            continue
```

③ 逗号兜底删除（`:238-243` 段）：**不猜** —— 解析不出条目时保留原文：

```python
    if not in_scope_items and scope:
        in_scope_items = [scope.strip()]  # 保留原文，不猜
        print("⚠️  proposal: 范围节未解析出条目 ⇒ 保留原文（不再按逗号切分）", file=sys.stderr)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_generate_full_proposal_scope_table.py -q`
Expected: PASS（4 个用例全绿）

- [ ] **Step 5: Defer commit**

- [ ] **Step 6: 变异验证（AC5 · 判别力）** —— 把 `_extract_scope_items` 的表格识别退回「只认 bullet」
  ⇒ **本轴 AC1** 的纯表格用例**必须红**（证明它真的在测表格解析，而不是恒绿）

---

### Task 3: 兜底删除 + 标题优先级（AC2 / AC6）

**Files:**
- Modify: `skills/rdd-builder/scripts/generate_full_proposal.py:238-243`（兜底）、`:232-235`（`_extract_section` 候选序）
- Test: `tests/unit/test_generate_full_proposal_scope_table.py`（追加 2 个用例）

- [ ] **Step 1: Write the failing test**

追加：

```python
def test_unparseable_scope_is_preserved_verbatim(capsys) -> None:
    md = _md("""**In Scope**

| a | b |
|---|---|
| 1 | 2, 3 |
""")
    out = gen_fp.generate_full_proposal("probe", md)
    assert "| 1 | 2, 3 |" in out
    assert "保留原文" in capsys.readouterr().err


def test_both_sections_present_prefers_range(capsys) -> None:
    md = """## 范围

**In Scope**

- 中文项

## What Changes

- 英文项
"""
    out = gen_fp.generate_full_proposal("probe", md)
    assert "中文项" in out
    assert "英文项" not in out
    assert "歧义" in capsys.readouterr().err
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_generate_full_proposal_scope_table.py -q`
Expected: FAIL —— 逗号兜底把表格切碎；并存时无「歧义」提示。

- [ ] **Step 3: Write minimal implementation**

- 兜底段替换为「保留原文 + stderr」（见 Task 2 ③）；
- `_extract_section` 的候选序显式固定为 `("范围", "What Changes", "Scope")`，并在**命中多个候选**时写 stderr：

```python
    hits = [c for c in candidates if re.search(rf"^##\s*{re.escape(c)}\s*$", text, re.M)]
    if len(hits) > 1:
        print(f"⚠️  proposal: 范围节候选歧义（{hits}）⇒ 取候选序靠前者", file=sys.stderr)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_generate_full_proposal_scope_table.py -q`
Expected: PASS（6 个用例全绿）

- [ ] **Step 5: Defer commit**

---

### Task 4: 语料 golden snapshot + 形态标签表（AC4）

**Files:**
- Create: `tests/unit/test_generate_full_proposal_corpus.py`、`tests/fixtures/proposals_corpus_snapshot.json`
- Modify: `skills/rdd-builder/scripts/generate_full_proposal.py`（仅在需要暴露「逐行形态标签」时加一个**公开**辅助函数）

- [ ] **Step 1: Write the failing test**

新建 `tests/unit/test_generate_full_proposal_corpus.py`：

```python
"""语料 golden snapshot（AC4）：当前生成结果 == 入库期望输出。"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_SCRIPT = _ROOT / "skills" / "rdd-builder" / "scripts" / "generate_full_proposal.py"
_spec = importlib.util.spec_from_file_location("gen_fp", _SCRIPT)
gen_fp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_fp)

_SNAPSHOT = _ROOT / "tests" / "fixtures" / "proposals_corpus_snapshot.json"
_IMPROVEMENTS = sorted((_ROOT / ".rddf" / "improvements").glob("*.md"))


def test_snapshot_metadata_is_dynamic() -> None:
    data = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    assert data["corpus_count"] == len(_IMPROVEMENTS)
    assert data["generated_at"]
    assert set(data["shape_labels"]) == {"table_row", "bullet", "numbered", "other"}


def test_generated_output_matches_golden_snapshot() -> None:
    data = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    for path in _IMPROVEMENTS:
        md = path.read_text(encoding="utf-8")
        out = gen_fp.generate_full_proposal(path.stem, md)
        expected = data["outputs"].get(path.stem)
        assert expected is not None, f"快照缺 {path.stem} ⇒ 同 PR 必须刷新快照"
        assert out == expected, f"{path.stem} 的生成结果与 golden snapshot 不一致"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_generate_full_proposal_corpus.py -q`
Expected: FAIL —— 快照文件不存在（`FileNotFoundError`）。

- [ ] **Step 3: Write minimal implementation**

① 在生成器暴露形态标签函数（供快照生成与测试共用）：

```python
def shape_labels(text: str) -> dict[str, int]:
    """按**行首形态**统计行数（table_row / bullet / numbered / other）—— 差异可按标签归类。"""
    counts = {"table_row": 0, "bullet": 0, "numbered": 0, "other": 0}
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if _TABLE_ROW_RE.match(s) and not _TABLE_ALIGN_RE.match(s):
            counts["table_row"] += 1
        elif re.match(r"^-\s+", s):
            counts["bullet"] += 1
        elif re.match(r"^\d+[.)]\s+", s):
            counts["numbered"] += 1
        else:
            counts["other"] += 1
    return counts
```

② 新增快照生成脚本 `tests/fixtures/refresh_proposals_corpus_snapshot.py`（**一次性/按需运行**）：

```python
"""刷新语料 golden snapshot（AC4）：新增 improvement 后必须同 PR 运行。"""
import importlib.util, json, pathlib, sys, datetime

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "gen_fp", ROOT / "skills/rdd-builder/scripts/generate_full_proposal.py")
gen_fp = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen_fp)

improve = sorted((ROOT / ".rddf/improvements").glob("*.md"))
outputs, labels = {}, {"table_row": 0, "bullet": 0, "numbered": 0, "other": 0}
for p in improve:
    md = p.read_text(encoding="utf-8")
    outputs[p.stem] = gen_fp.generate_full_proposal(p.stem, md)
    for k, v in gen_fp.shape_labels(md).items():
        labels[k] += v

snapshot = {
    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "corpus_count": len(improve),
    "shape_labels": labels,
    "outputs": outputs,
}
(ROOT / "tests/fixtures/proposals_corpus_snapshot.json").write_text(
    json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"snapshot refreshed: {len(improve)} improvements")
```

③ 运行它生成快照（**在 Task 1–3 落地之后**）：

Run: `python3 tests/fixtures/refresh_proposals_corpus_snapshot.py`

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_generate_full_proposal_corpus.py -q`
Expected: PASS（2 个用例全绿）

- [ ] **Step 5: Defer commit**

- [ ] **Step 6: 变异验证（AC4 · 判别力）** —— 把形态标签分类器改坏（如把 `table_row` 归成 `other`）
  ⇒ 语料用例**必须红**（证明形态标签表参与判别，而不是摆设）

---

### Task 5: delta 载体 + 形态守卫 + MODIFIED 生成 + 版本探测（AC7 / AC8 / AC9 / AC13）

**Files:**
- Create: `_lib/openspec_version.py`
- Modify: `skills/rdd-builder/scripts/generate_full_proposal.py`（`generate_spec_delta()` + 载体解析）
- Test: `tests/unit/test_spec_delta_generator_shape.py`、`tests/unit/test_spec_delta_generator_modified.py`（新建）

- [ ] **Step 1: Write the failing test**

新建 `tests/unit/test_spec_delta_generator_shape.py`：

```python
"""形态守卫：退化形态在**生成时**被拒（AC7）。"""
from __future__ import annotations

import importlib.util, pathlib, sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
_spec = importlib.util.spec_from_file_location(
    "gen_fp", _ROOT / "skills/rdd-builder/scripts/generate_full_proposal.py")
gen_fp = importlib.util.module_from_spec(_spec); spec.loader.exec_module(gen_fp)


def test_acceptance_n_name_is_refused() -> None:
    md = "## Acceptance\n\n- [ ] `family` enum 含 4 值\n"
    try:
        gen_fp.generate_spec_delta(md, "probe")
    except ValueError as exc:
        assert "acceptance" in str(exc).lower()
        return
    raise AssertionError("退化形态未被拒绝")


def test_tautological_when_is_refused() -> None:
    md = "## Acceptance\n\n- [ ] `family` enum 含 4 值\n"
    try:
        gen_fp.generate_spec_delta(md, "probe")
    except ValueError:
        return
    raise AssertionError("恒真 WHEN 未被拒绝")
```

新建 `tests/unit/test_spec_delta_generator_modified.py`（要点）：

```python
def test_modified_target_is_emitted(tmp_path, monkeypatch) -> None:
    md = (
        "**delta**: modified cep-core-contracts\n\n"
        "## 语义要求\n\n"
        "- `family-domain-has-four-values` | 实例声明其来源族\n\n"
        "## Acceptance\n\n- [ ] `family` enum 含 4 值\n"
    )
    out = gen_fp.generate_spec_delta(md, "probe")
    assert out.splitlines()[0] == "## MODIFIED Requirements"


def test_legacy_version_branch_guards_scenarios(monkeypatch) -> None:
    monkeypatch.setattr(gen_fp, "openspec_version_at_least", lambda v: False)
    # <1.7.0 ⇒ 自实现 missing == ∅（缺失列表为空即通过）
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_spec_delta_generator_shape.py tests/unit/test_spec_delta_generator_modified.py -q`
Expected: FAIL —— 当前 `generate_spec_delta()` 照常产出 `acceptance-N` + 恒真 WHEN，且无载体解析。

- [ ] **Step 3: Write minimal implementation**

① `_lib/openspec_version.py`（语义化）：

```python
"""openspec CLI 版本探测（纯 stdlib · 语义化比较）。"""
from __future__ import annotations

import re, subprocess

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def parse_version(text: str) -> tuple[int, int, int]:
    m = _VERSION_RE.search(text or "")
    if not m:
        raise ValueError(f"无法解析 openspec 版本：{text!r}")
    return tuple(int(g) for g in m.groups())  # type: ignore[return-value]


def current_version(cli: str = "openspec") -> tuple[int, int, int]:
    out = subprocess.run([cli, "--version"], capture_output=True, text=True, timeout=30)
    return parse_version(out.stdout + out.stderr)


def at_least(minimum: tuple[int, int, int], actual: tuple[int, int, int] | None = None) -> bool:
    """**语义化**比较（`1.14.3 > 1.7.0` 必须成立 ⇒ 禁字符串比较）。"""
    return (actual if actual is not None else current_version()) >= minimum
```

② 生成器侧：

```python
_HEAD_FIELD_RE = re.compile(r"^\*\*(?P<key>[^*]+)\*\*\s*[:：]\s*(?P<value>.+?)\s*$", re.MULTILINE)


def _head_field(text: str, key: str) -> str | None:
    """读粗体头行（与 ADR-0025 D6 的「头部」一致；纯 stdlib）。"""
    for m in _HEAD_FIELD_RE.finditer(text):
        if m.group("key").strip() == key:
            return m.group("value").strip()
    return None


def _semantic_requirements(text: str) -> list[tuple[str, str]]:
    """解析 `## 语义要求` 段：`- \`name\` | WHEN 文本`。"""
    out: list[tuple[str, str]] = []
    m = re.search(r"^##\s*语义要求\s*$(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not m:
        return out
    for line in m.group(1).splitlines():
        s = line.strip()
        if not s.startswith("-"):
            continue
        body = s.lstrip("- ").strip()
        if "`" in body and "|" in body:
            name, when = body.split("|", 1)
            out.append((name.strip().strip("`").strip(), when.strip()))
    return out
```

`generate_spec_delta()` 改为：先取载体（`delta` / `语义要求`）⇒ 无载体 ⇒ `raise ValueError(...)`；有载体 ⇒ 生成语义化 Requirement + 非恒真 WHEN；**产出前**用共享判据 `is_degraded()` 自检 ⇒ 命中 ⇒ `raise ValueError(...)`。

③ 版本分流：`>= (1,7,0)` ⇒ 走原生语义（本地预检只做目标存在性）；`< (1,7,0)` ⇒ 自实现 `missing == ∅`。

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_spec_delta_generator_shape.py tests/unit/test_spec_delta_generator_modified.py -q`
Expected: PASS

- [ ] **Step 5: Defer commit**

- [ ] **Step 6: 变异验证（AC12 / AC13 · 判别力）** —— ① 把共享模块的 `acceptance-N` 正则退回不匹配 ⇒ **AC7** 必须红；
  ② 把版本比较退化为**字符串比较**（`1.14.3` 会被判成 `< 1.7.0`）⇒ 版本分支用例必须红

---

### Task 6: 半成品防护 + 守卫接线 + SKILL 契约 + 跨轴端到端（AC11 / AC14 / AC15）

**Files:**
- Modify: `skills/rdd-builder/scripts/phase0_approval.sh:160-183`、`skills/rdd-builder/SKILL.md`
- Test: `tests/integration/test_phase0_partial_artifact.bats`（新建）、`tests/unit/test_rdd_builder_skill_contract.py`（新建）

- [ ] **Step 1: Write the failing test**

新建 `tests/unit/test_rdd_builder_skill_contract.py`：

```python
"""SKILL.md 的 delta 契约三锚点（AC11）。"""
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SKILL = _ROOT / "skills" / "rdd-builder" / "SKILL.md"


def test_skill_documents_delta_contract() -> None:
    text = _SKILL.read_text(encoding="utf-8")
    assert "粗体头行" in text, "缺锚点①载体"
    assert "既有 Scenario" in text, "缺锚点②MODIFIED 保留既有 Scenario"
    assert "1.7.0" in text, "缺锚点③版本口径"
```

新建 `tests/integration/test_phase0_partial_artifact.bats`（要点）：

```bash
@test "delta 拒绝 ⇒ 不留空文件、不留半成品、可重试" {
  cd "$BATS_TMPDIR/proj"
  # 造一个只含 acceptance-N 的 improvement ⇒ 形态守卫必然拒绝
  mkdir -p .rddf/improvements openspec/changes
  printf '## Acceptance\n\n- [ ] x\n' > .rddf/improvements/probe.md
  run bash "$REPO_ROOT/skills/rdd-builder/scripts/phase0_approval.sh" probe
  [ "$status" -ne 0 ]
  [ ! -f openspec/changes/probe/specs/probe/spec.md ]
  [ ! -s openspec/changes/probe/proposal.md ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_rdd_builder_skill_contract.py -q` 与 `bats tests/integration/test_phase0_partial_artifact.bats`
Expected: FAIL —— SKILL.md 无 delta 契约段；P0 拒绝后留下空 delta 文件。

- [ ] **Step 3: Write minimal implementation**

① `phase0_approval.sh`：写入改「临时文件 + 成功后 `mv`」：

```bash
        TMP_DELTA="${DELTA_FILE}.tmp"
        if ! OUTPUT_MODE=spec-delta CHANGE_NAME="$CHANGE_NAME" \
             IMPROVEMENTS_PATH="$IMPROVEMENT_FILE" \
             python3 "$SCRIPT_DIR/generate_full_proposal.py" > "$TMP_DELTA"; then
            rm -f "$TMP_DELTA"
            echo "❌ delta 生成失败 ⇒ 已清理临时文件（不留空文件、可重试）" >&2
            exit 1
        fi
        mv "$TMP_DELTA" "$DELTA_FILE"
```

（proposal 同理：`PROPOSAL_FILE` ⇒ 临时文件 + `mv`；失败 ⇒ 删临时文件并 `exit 1`。）

② `skills/rdd-builder/SKILL.md` 增「delta 契约」段（三锚点：载体 = **粗体头行** / MODIFIED **保留既有 Scenario** / 版本口径 **1.7.0** 分流）。

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_rdd_builder_skill_contract.py -q` 与 `bats tests/integration/test_phase0_partial_artifact.bats`
Expected: PASS

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更在 archive 阶段统一提交。
