# adr-index-auto-sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 自动同步 `docs/adr/README.md` 的 ADR 索引表格 — 通过 `_lib/adr_index_generator.py` 扫描 `docs/adr/ADR-*.md` frontmatter/status 块,生成 Markdown 表格,消除"手写索引过期"问题。

**Architecture:** 用 Python 模块扫描 ADR 文件,提取 status/date/decider 三个字段(从 `> **状态**: ...` 引用块读取,因为 ADR 没用 YAML frontmatter),生成 markdown 表格插入到 `<!-- ADR_INDEX_START --> ... <!-- ADR_INDEX_END -->` 占位符之间。CI 测试验证表格 == 磁盘。

**Tech Stack:** Python 3.11+ (项目 runtime), pytest (unit), bats (integration), git (worktree)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/adr_index_generator.py` | 扫描 `docs/adr/ADR-*.md`,提取 status/date/decider,生成 markdown 表格;提供 3 个 public function: `scan_adrs()`, `extract_metadata()`, `render_table()` |
| `docs/adr/README.md` | 保留手写 header,中间表格段 `<!-- ADR_INDEX_START --> ... <!-- ADR_INDEX_END -->` 改为 generator 产物 |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_adr_index_generator.py` | 3+ pytest 测试:scan_adrs 找到 35 个,extract_metadata 解析 status/date/decider,render_table 输出 markdown 表格 |
| `tests/integration/test_adr_index.bats` | CI 守护:运行 generator 后,验证 README 表格 == 磁盘 ADR 列表 |

---

### Task 1: 创建 _lib/adr_index_generator.py 骨架 + scan_adrs()

**Files:**
- Create: `_lib/adr_index_generator.py`
- Test: `tests/unit/test_adr_index_generator.py`

- [ ] **Step 1: Write failing test (test_scan_adrs)**

```python
# tests/unit/test_adr_index_generator.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
from adr_index_generator import scan_adrs

def test_scan_adrs_returns_at_least_35_files():
    """扫描 docs/adr/ 至少返回 35 个 ADR-*.md (含 template)。"""
    repo_root = Path(__file__).resolve().parents[2]
    adrs = scan_adrs(repo_root / "docs" / "adr")
    # 35 个真实 ADR + 1 个 template = 36 (template 也要返回,但 render 时跳过)
    assert len(adrs) >= 35
    # 每个 ADR 都有 number / title / slug
    for adr in adrs:
        assert "number" in adr
        assert "title" in adr
        assert "slug" in adr
        assert "filename" in adr
```

- [ ] **Step 2: Run test, verify FAIL**

Run: `python3 -m pytest tests/unit/test_adr_index_generator.py::test_scan_adrs_returns_at_least_35_files -v`
Expected: `ModuleNotFoundError: No module named 'adr_index_generator'` (or ImportError)

- [ ] **Step 3: Implement minimal scan_adrs**

```python
# _lib/adr_index_generator.py
"""ADR Index Generator — scans docs/adr/ADR-*.md, generates markdown table.

Public API:
    scan_adrs(adr_dir) -> list[dict]
    extract_metadata(adr_path) -> dict | None
    render_table(adrs) -> str (markdown table)
"""
from pathlib import Path
import re

ADR_PATTERN = re.compile(r"ADR-(\d{4})-(.+)\.md$")


def scan_adrs(adr_dir: Path) -> list[dict]:
    """Scan adr_dir for ADR-*.md files. Return list of dicts with number/title/slug/filename."""
    adrs = []
    for path in sorted(adr_dir.glob("ADR-*.md")):
        m = ADR_PATTERN.match(path.name)
        if not m:
            continue
        number, slug = m.groups()
        title = _extract_title(path)
        adrs.append({
            "number": number,
            "slug": slug,
            "title": title,
            "filename": path.name,
            "path": path,
        })
    return adrs


def _extract_title(path: Path) -> str:
    """Extract title from ADR file (first # heading)."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return ""
```

- [ ] **Step 4: Run test, verify PASS**

Run: `python3 -m pytest tests/unit/test_adr_index_generator.py::test_scan_adrs_returns_at_least_35_files -v`
Expected: PASS

- [ ] **Step 5: Defer commit** (per repo convention; aggregate at archive phase)

---

### Task 2: 实现 extract_metadata() 解析 status/date/decider

**Files:**
- Modify: `_lib/adr_index_generator.py`
- Test: `tests/unit/test_adr_index_generator.py`

- [ ] **Step 1: Write failing test (test_extract_metadata)**

```python
# Add to tests/unit/test_adr_index_generator.py
from adr_index_generator import extract_metadata

def test_extract_metadata_parses_status_date_decider():
    """解析 ADR-0001 的 > 状态/日期/决策者 块。"""
    repo_root = Path(__file__).resolve().parents[2]
    md = extract_metadata(repo_root / "docs" / "adr" / "ADR-0001-propose-plan-execute-state-machine.md")
    assert md is not None
    assert "status" in md
    assert "已替代" in md["status"] or "已采纳" in md["status"] or "已弃用" in md["status"]
    assert "date" in md
    assert "decider" in md


def test_extract_metadata_returns_none_for_template():
    """ADR-0000 是 template,应返回 None 或标记 is_template。"""
    repo_root = Path(__file__).resolve().parents[2]
    md = extract_metadata(repo_root / "docs" / "adr" / "ADR-0000-template.md")
    # Template 没有状态/日期字段,允许 None 或缺字段
    if md is not None:
        assert md.get("is_template") is True
```

- [ ] **Step 2: Run test, verify FAIL**

Run: `python3 -m pytest tests/unit/test_adr_index_generator.py -v -k "test_extract_metadata"`
Expected: `AttributeError: module 'adr_index_generator' has no attribute 'extract_metadata'`

- [ ] **Step 3: Implement extract_metadata()**

```python
# Append to _lib/adr_index_generator.py
import re as _re

_META_PATTERN = _re.compile(
    r"^>\s*\*\*(状态|日期|决策者)\*\*:\s*(.+?)\s*$",
    _re.MULTILINE,
)


def extract_metadata(adr_path: Path) -> dict | None:
    """Extract status / date / decider from > 引用块 in ADR file.

    Returns:
        dict with keys: status, date, decider, is_template (bool)
        None if file has no metadata block (e.g. broken ADR).
    """
    text = adr_path.read_text(encoding="utf-8")
    matches = _META_PATTERN.findall(text)
    if not matches:
        return None
    metadata = {"is_template": "template" in adr_path.name}
    for key, value in matches:
        # 跳过模板字段 (e.g. "状态: 待定")
        if key == "状态":
            metadata["status"] = value.strip()
        elif key == "日期":
            metadata["date"] = value.strip()
        elif key == "决策者":
            metadata["decider"] = value.strip()
    return metadata
```

- [ ] **Step 4: Run test, verify PASS**

Run: `python3 -m pytest tests/unit/test_adr_index_generator.py -v -k "test_extract_metadata"`
Expected: 2 PASS

- [ ] **Step 5: Defer commit**

---

### Task 3: 实现 render_table() 生成 markdown 表格

**Files:**
- Modify: `_lib/adr_index_generator.py`
- Test: `tests/unit/test_adr_index_generator.py`

- [ ] **Step 1: Write failing test (test_render_table)**

```python
# Add to tests/unit/test_adr_index_generator.py
from adr_index_generator import scan_adrs, extract_metadata, render_table

def test_render_table_outputs_markdown():
    """render_table 输出 markdown 表格,header + 数据行."""
    repo_root = Path(__file__).resolve().parents[2]
    adrs = scan_adrs(repo_root / "docs" / "adr")
    table = render_table(adrs)
    # Header
    assert "| ADR |" in table
    assert "| 标题 |" in table
    assert "| 状态 |" in table
    # 至少 35 个数据行 (excluding template)
    rows = [l for l in table.splitlines() if l.startswith("| [ADR-")]
    assert len(rows) >= 35
    # 不包含 template
    assert "ADR-0000" not in table
```

- [ ] **Step 2: Run test, verify FAIL**

Run: `python3 -m pytest tests/unit/test_adr_index_generator.py -v -k "test_render_table"`
Expected: `AttributeError: module 'adr_index_generator' has no attribute 'render_table'`

- [ ] **Step 3: Implement render_table()**

```python
# Append to _lib/adr_index_generator.py


def render_table(adrs: list[dict], include_metadata: bool = True) -> str:
    """Render markdown table from scanned ADRs.

    Skips templates (ADR-0000). Includes metadata columns when available.

    Args:
        adrs: list from scan_adrs()
        include_metadata: whether to join metadata (status/date/decider)

    Returns:
        Markdown table string (header + separator + rows).
    """
    lines = [
        "| ADR | 标题 | 状态 | 日期 |",
        "|-----|------|------|------|",
    ]
    for adr in adrs:
        if "template" in adr["filename"].lower():
            continue
        meta = extract_metadata(adr["path"]) if include_metadata else None
        status = meta.get("status", "—") if meta else "—"
        date = meta.get("date", "—") if meta else "—"
        link = f"[ADR-{adr['number']}]({adr['filename']})"
        lines.append(
            f"| {link} | {adr['title']} | {status} | {date} |"
        )
    return "\n".join(lines) + "\n"


def main():
    """CLI entry: regenerate docs/adr/README.md table."""
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[1]
    adrs = scan_adrs(repo_root / "docs" / "adr")
    table = render_table(adrs)
    print(table)
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test, verify PASS**

Run: `python3 -m pytest tests/unit/test_adr_index_generator.py -v`
Expected: 4 PASS

- [ ] **Step 5: Defer commit**

---

### Task 4: 改造 docs/adr/README.md 表格段 (插 ADR_INDEX_START/END 占位符)

**Files:**
- Modify: `docs/adr/README.md`

- [ ] **Step 1: 在 README.md 中插入占位符**

手动编辑 `docs/adr/README.md`:
- 在 `## ADR 列表` 段之前的表格之前插入 `<!-- ADR_INDEX_START -->`
- 在表格结束之后 (下一个 `##` 段之前)插入 `<!-- ADR_INDEX_END -->`

预期 diff:
```markdown
<!-- ADR_INDEX_START -->
| ADR | 标题 | 状态 | 日期 |
|-----|------|------|------|
| [ADR-0001](ADR-0001-...) | ... | 已替代为 ADR-0003 | 2026-06-08 |
...
<!-- ADR_INDEX_END -->
```

- [ ] **Step 2: 验证占位符存在**

Run: `grep -E "ADR_INDEX_(START|END)" docs/adr/README.md`
Expected: 输出两行 (START + END)

- [ ] **Step 3: 运行 generator,验证输出 ≥ 35 行**

Run: `python3 _lib/adr_index_generator.py | head -10`
Expected: 看到 markdown table header + 至少 35 个 `[ADR-...]` 行

- [ ] **Step 4: Defer commit**

---

### Task 5: 创建 tests/integration/test_adr_index.bats CI 守护

**Files:**
- Create: `tests/integration/test_adr_index.bats`

- [ ] **Step 1: 写 bats test 验证 README 表格 == 磁盘**

```bash
# tests/integration/test_adr_index.bats
load 'test_helper'
load_lib adr_helpers

@test "adr-index: generator output matches disk ADR count" {
    run python3 _lib/adr_index_generator.py
    [ "$status" -eq 0 ]
    local disk_count=$(ls docs/adr/ADR-*.md | grep -v ADR-0000 | wc -l | tr -d ' ')
    local rendered_count=$(echo "$output" | grep -cE "^\| \[ADR-")
    [ "$disk_count" -eq "$rendered_count" ]
}

@test "adr-index: README contains ADR_INDEX_START and ADR_INDEX_END markers" {
    run grep -c "ADR_INDEX_START" docs/adr/README.md
    [ "$status" -eq 0 ]
    [ "$output" -eq 1 ]
    run grep -c "ADR_INDEX_END" docs/adr/README.md
    [ "$status" -eq 0 ]
    [ "$output" -eq 1 ]
}

@test "adr-index: README table inside markers includes all ADRs" {
    local content=$(awk '/<!-- ADR_INDEX_START -->/,/<!-- ADR_INDEX_END -->/' docs/adr/README.md)
    local table_rows=$(echo "$content" | grep -cE "^\| \[ADR-")
    local disk_count=$(ls docs/adr/ADR-*.md | grep -v ADR-0000 | wc -l | tr -d ' ')
    [ "$table_rows" -eq "$disk_count" ]
}
```

- [ ] **Step 2: 运行 bats 验证**

Run: `bats tests/integration/test_adr_index.bats`
Expected: 3 pass

- [ ] **Step 3: Defer commit**

---

### Task 6: AGENTS.md line 148 关键 ADR 列表加注

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: 找到 line 148 附近 "关键 ADR" 列表**

Run: `sed -n '140,160p' AGENTS.md`
Expected: 看到 ADR-0018 / ADR-0019 / ADR-0024 / ADR-0025 / ADR-0028 / ADR-0034 等关键 ADR 列表

- [ ] **Step 2: 追加注释,说明自动同步**

在列表后面 (例如紧跟 ###" 关键 ADR 列表段尾) 加注释:
```markdown
> **Note**: 此列表由人工维护;`adr-index-auto-sync` change 完成后,自动同步 README 表格段(`<!-- ADR_INDEX_START --> ... <!-- ADR_INDEX_END -->`),但此列表保持手写以确保"已实施关键 ADR"的策展判断。
```

- [ ] **Step 3: Defer commit**

---

### Task 7: 跑全量回归 + 归档前 sanity check

**Files:**
- 无 (验证步骤)

- [ ] **Step 1: 运行 unit + integration tests**

Run: `python3 -m pytest tests/unit/test_adr_index_generator.py -v`
Expected: 4 PASS

Run: `bats tests/integration/test_adr_index.bats`
Expected: 3 pass

- [ ] **Step 2: 运行 adr-index 单元测试 + integration**

Run: `python3 -c "from _lib.adr_index_generator import scan_adrs, render_table; from pathlib import Path; adrs = scan_adrs(Path('docs/adr')); print(f'scanned {len(adrs)} ADRs'); print(render_table(adrs)[:200])"`
Expected: scanned 36 ADRs (含 template), 输出 markdown 表格前 200 字符

- [ ] **Step 3: archive 前 regression (per AGENTS.md MANDATORY)**

Run: `./test.sh --full --regression`
Expected: 0 exit code (或仅 baseline 已知失败)

- [ ] **Step 4: Defer commit**

---

## Self-Review Checklist (write before archive)

- [ ] Spec 覆盖: 8 个 acceptance items 全部对应到 Task 1-7
  - Task 1: scan_adrs ✅ (#3 acceptance)
  - Task 2: extract_metadata ✅ (#1 acceptance — 3 public functions)
  - Task 3: render_table ✅ (#1 acceptance)
  - Task 4: README 占位符 ✅ (#2 acceptance)
  - Task 5: bats CI ✅ (#5 acceptance)
  - Task 6: AGENTS.md 注释 ✅ (#7 acceptance)
  - Task 7: 全量回归 ✅ (#3/#4 acceptance)
- [ ] 占位符扫描: 0 个 "TBD" / "fill in details"
- [ ] 类型一致性: 3 个 public function 签名统一 (adr_dir: Path → list[dict])
- [ ] pre-commit hook (Task 5 acceptance #8) **可选**,out-of-scope,留作 follow-up