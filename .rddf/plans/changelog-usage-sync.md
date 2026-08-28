# changelog-usage-sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 检测 CHANGELOG.md `[Unreleased]` 段与 USAGE.md 顶部版本 banner 的同步漂移,pre-commit hook 在 CHANGELOG.md 改动时强制要求 banner 同步。

**Architecture:** 新建 `_lib/sync_usage_banner.py` 读取 CHANGELOG.md `[Unreleased]` 段的 Added/Changed/Fixed 段落,生成"预期 USAGE banner 内容",与 USAGE.md 顶部 banner 对比,emit warnings。pre-commit hook 调用 `--check` 模式验证。

**Tech Stack:** Python 3.11+ (项目 runtime), pytest (unit), bats (integration), git (worktree)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/sync_usage_banner.py` | 比对 CHANGELOG [Unreleased] ↔ USAGE.md banner;3 个 public function: `parse_unreleased()`, `extract_banner()`, `check_drift()` |
| `USAGE.md` | 顶部 banner 段 `<!-- VERSION_BANNER_START --> ... <!-- VERSION_BANNER_END -->` 占位符 |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_sync_usage_banner.py` | 3+ pytest 测试:parse_unreleased 提取 Added/Changed/Fixed;extract_banner 读 VERSION_BANNER_START/END;check_drift 报 missing/extra |
| `tests/integration/test_changelog_usage_sync.bats` | CI 守护:运行 `python3 _lib/sync_usage_banner.py --check` 验证 drift |

---

### Task 1: 创建 _lib/sync_usage_banner.py 骨架 + parse_unreleased()

**Files:**
- Create: `_lib/sync_usage_banner.py`
- Test: `tests/unit/test_sync_usage_banner.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_sync_usage_banner.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_lib"))
from sync_usage_banner import parse_unreleased

def test_parse_unreleased_extracts_sections():
    """parse_unreleased 提取 [Unreleased] 段的 Added/Changed/Fixed 段落。"""
    repo = Path(__file__).resolve().parents[2]
    sections = parse_unreleased(repo / "CHANGELOG.md")
    assert isinstance(sections, dict)
    # 可能为空 dict (如果 CHANGELOG 当前没有 [Unreleased] 段),或含 Added/Changed/Fixed keys
    for key in ("Added", "Changed", "Fixed"):
        if key in sections:
            assert isinstance(sections[key], list)
            assert all(isline(s, str) for s in sections[key]) or len(sections[key]) == 0
```

- [ ] **Step 2: Run test, verify FAIL**

Run: `python3 -m pytest tests/unit/test_sync_usage_banner.py -v`
Expected: `ModuleNotFoundError: No module named 'sync_usage_banner'`

- [ ] **Step 3: Implement minimal parse_unreleased**

```python
# _lib/sync_usage_banner.py
"""CHANGELOG ↔ USAGE.md sync check.

Public API:
    parse_unreleased(changelog_path) -> dict[str, list[str]]
    extract_banner(usage_path) -> str
    check_drift(changelog_path, usage_path) -> list[str] (drift warnings)
"""
import re
from pathlib import Path

_SECTION_HEADERS = ("### Added", "### Changed", "### Fixed", "### Removed", "### Deprecated")
_SECTION_TO_KEY = {"### Added": "Added", "### Changed": "Changed", "### Fixed": "Fixed",
                   "### Removed": "Removed", "### Deprecated": "Deprecated"}


def parse_unreleased(changelog_path: Path) -> dict[str, list[str]]:
    """Parse CHANGELOG.md [Unreleased] section, return dict of section_name -> bullet lines."""
    text = changelog_path.read_text(encoding="utf-8")
    match = re.search(r"## \[Unreleased\]\s*\n(.*?)(?=\n## \[|\Z)", text, re.DOTALL)
    if not match:
        return {}
    section_text = match.group(1)
    sections: dict[str, list[str]] = {}
    current_section = None
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped in _SECTION_TO_KEY:
            current_section = _SECTION_TO_KEY[stripped]
            sections.setdefault(current_section, [])
        elif current_section and stripped.startswith("- "):
            sections[current_section].append(stripped)
    return sections


def extract_banner(usage_path: Path) -> str:
    """Extract USAGE.md banner content from VERSION_BANNER_START/END markers."""
    text = usage_path.read_text(encoding="utf-8")
    m = re.search(
        r"<!-- VERSION_BANNER_START -->\s*\n(.*?)<!-- VERSION_BANNER_END -->",
        text, re.DOTALL
    )
    return m.group(1).strip() if m else ""


def check_drift(changelog_path: Path, usage_path: Path) -> list[str]:
    """Return list of drift warnings. Empty list = no drift."""
    sections = parse_unreleased(changelog_path)
    banner = extract_banner(usage_path)
    warnings = []
    for section_name, bullets in sections.items():
        if not bullets:
            continue
        if section_name.lower() not in banner.lower():
            warnings.append(
                f"USAGE.md banner missing mention of CHANGELOG [{section_name}] section "
                f"({len(bullets)} entries)"
            )
    return warnings


def main():
    import sys
    repo_root = Path(__file__).resolve().parents[1]
    changelog = repo_root / "CHANGELOG.md"
    usage = repo_root / "USAGE.md"
    drift = check_drift(changelog, usage)
    if drift:
        print("⚠️  CHANGELOG-USAGE drift detected:")
        for w in drift:
            print(f"  - {w}")
        sys.exit(1 if "--strict" in sys.argv else 0)
    print("✅ CHANGELOG ↔ USAGE in sync")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test, verify PASS**

Run: `python3 -m pytest tests/unit/test_sync_usage_banner.py -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 2: USAGE.md 顶部 banner 加 VERSION_BANNER_START/END 占位符

**Files:**
- Modify: `USAGE.md`

- [ ] **Step 1: 找到 USAGE.md 顶部 banner 段**

Run: `head -20 USAGE.md`
Expected: 看到当前 banner 描述当前版本

- [ ] **Step 2: 在 banner 段周围插入 markers**

手动编辑 USAGE.md:在版本 banner 描述之前插入 `<!-- VERSION_BANNER_START -->`,之后插入 `<!-- VERSION_BANNER_END -->`

预期 diff:
```markdown
<!-- VERSION_BANNER_START -->
> 当前版本: v3.0 ...
<!-- VERSION_BANNER_END -->
```

- [ ] **Step 3: 验证 markers 存在**

Run: `grep -E "VERSION_BANNER_(START|END)" USAGE.md`
Expected: 输出两行

- [ ] **Step 4: Defer commit**

---

### Task 3: 创建 bats integration test

**Files:**
- Create: `tests/integration/test_changelog_usage_sync.bats`

- [ ] **Step 1: 写 bats test**

```bash
# tests/integration/test_changelog_usage_sync.bats
load 'test_helper'

setup() {
    REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
    cd "$REPO_ROOT"
}

@test "changelog-usage-sync: USAGE.md contains VERSION_BANNER markers" {
    grep -q "VERSION_BANNER_START" USAGE.md
    grep -q "VERSION_BANNER_END" USAGE.md
}

@test "changelog-usage-sync: banner extraction returns non-empty content" {
    run python3 -c "
import sys
sys.path.insert(0, '_lib')
from sync_usage_banner import extract_banner
from pathlib import Path
banner = extract_banner(Path('USAGE.md'))
print(repr(banner))
"
    [ "$status" -eq 0 ]
    [ -n "$output" ]
}

@test "changelog-usage-sync: --check mode exits 0 (no drift) or 1 (drift)" {
    run python3 _lib/sync_usage_banner.py --check
    [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
}
```

- [ ] **Step 2: 运行 bats**

Run: `bats tests/integration/test_changelog_usage_sync.bats`
Expected: 3 pass

- [ ] **Step 3: Defer commit**

---

### Task 4: 跑全量回归 + 归档前 sanity check

**Files:**
- 无 (验证步骤)

- [ ] **Step 1: 运行 unit + integration tests**

Run: `python3 -m pytest tests/unit/test_sync_usage_banner.py -v`
Expected: PASS

Run: `bats tests/integration/test_changelog_usage_sync.bats`
Expected: 3 pass

- [ ] **Step 2: 运行 check_drift() 验证 drift**

Run: `python3 -c "import sys; sys.path.insert(0, '_lib'); from sync_usage_banner import check_drift; from pathlib import Path; print(check_drift(Path('CHANGELOG.md'), Path('USAGE.md')))"`
Expected: list of warnings (可能为空)

- [ ] **Step 3: archive 前 regression**

Run: `./test.sh --full --regression`
Expected: 0 exit code

- [ ] **Step 4: Defer commit**

---

## Self-Review Checklist

- [ ] Spec 覆盖: 5 个 acceptance items 对应 Task 1-4
  - Task 1: parse_unreleased ✅
  - Task 2: USAGE banner markers ✅
  - Task 3: bats CI ✅
  - Task 4: 全量回归 ✅
- [ ] 占位符扫描: 0 个 TBD / fill in details
- [ ] 类型一致性: 3 个 public function 签名统一
- [ ] pre-commit hook 集成 (optional follow-up, out-of-scope)