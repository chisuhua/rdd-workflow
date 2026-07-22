---
SCOPE: shared
STATUS: PROPOSED
---

# Tasks: fix-install-lib-distribution

> **Goal**: Make `skills/_lib/*.py` installable via `install.sh` and `skills/INSTALL.md` so that `feature.md` and `rddf-session.md` (which declare `depends-on` on `_lib` modules) actually work for npm-installed users. Prerequisite for `sync-workflow-contracts` Decision 1 → A.
> **Risk**: medium (touches install paths; Python package structure addition; ~979KB new bytes in install).
> **Estimated effort**: 1-2 d.

---

## 1. Pre-flight（读，验证现状）

> 跑在动手改任何文件之前，确认现状可复现。

- [ ] **Task 1.1**: 记录 lib-distribution 现状

```bash
cd /workspace/project/rdd-workflow
echo "=== _lib file count ===" && find skills/_lib -maxdepth 1 -name '*.py' | wc -l
echo "=== _lib subdirs ===" && find skills/_lib -maxdepth 1 -mindepth 1 -type d
echo "=== install.sh:32 ===" && sed -n '30,33p' install.sh
echo "=== INSTALL.md:100 ===" && sed -n '99,101p' skills/INSTALL.md
echo "=== INSTALL.md:115 fallback ===" && grep -n "PKG_SKILLS" skills/INSTALL.md
echo "=== feature.md depends-on ===" && grep -A1 depends-on skills/feature.md
echo "=== rddf-session.md depends-on ===" && grep -A1 depends-on skills/rddf-session.md
echo "=== has __init__.py ===" && ls skills/__init__.py 2>&1 || true
echo "=== has _lib/__init__.py ===" && ls skills/_lib/__init__.py 2>&1 || true
echo "=== __pycache__ locations ===" && find skills/_lib -name __pycache__ -type d
echo "=== total size ===" && du -sh skills/_lib/
```

Expected:
- 49 files / 4 subdirs (`__pycache__ plugins schedulers schemas`)
- install.sh:32 = `cp -f "$PACKAGE_DIR/skills/"*.md ...`
- INSTALL.md:100 = `cp -f "$PACKAGE_DIR/skills/"*.md "$SKILLS_DIR/skills/"`
- INSTALL.md:115 fallback list = 11 skills (no `feature`, no `rddf-session`)
- feature.md → `depends-on: [iteration, deps_output]`
- rddf-session.md → `depends-on: [rddf_session]`
- `skills/__init__.py` 不存在 / `skills/_lib/__init__.py` 不存在
- `__pycache__` 至少在 `_lib/` 根 + `schedulers/` 中
- 总大小 ≈ 979KB

- [ ] **Task 1.2**: 跑 baseline 测试，确认改动前绿

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
bats tests/smoke.bats 2>&1 | tail -5
```

Expected: 全部既有测试通过。

---

## 2. Python package marker（`__init__.py` + TDD 失败测试）

> 这一组先写失败测试，验证当前 import 状态；再加 `__init__.py` 让测试绿。

- [ ] **Task 2.1**: 写失败测试 — 验证 install 路径下 `_lib` 模块可 import

```bash
mkdir -p tests/integration
cat > tests/integration/test_install_lib_distribution.bats <<'EOF'
#!/usr/bin/env bats

setup() {
  REPO_ROOT="${BATS_TEST_DIRNAME}/../.."
  cd "$REPO_ROOT"
}

@test "install_lib: skills/ has __init__.py (Python package marker)" {
  [ -f "skills/__init__.py" ]
}

@test "install_lib: skills/_lib/ has __init__.py (Python sub-package marker)" {
  [ -f "skills/_lib/__init__.py" ]
}

@test "install_lib: install.sh copies skills/_lib/*.py (recursive)" {
  run grep -E 'cp.*_lib.*\*\.py|cp.*skills/_lib' install.sh
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "install_lib: install.sh excludes __pycache__ / plugins / schedulers" {
  run grep -E '__pycache__|plugins|schedulers' install.sh
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "install_lib: INSTALL.md L100 mirrors install.sh (also copies _lib)" {
  run grep -nE '_lib.*\.py|skills/_lib' skills/INSTALL.md
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "install_lib: INSTALL.md fallback lists all 13 skills (or dynamic)" {
  # Either hardcoded 13 skills, OR a dynamic python3 derivation.
  # Static check: count the escaped \"<name>\" entries in fallback strings.
  count=$(grep -oE '\\\\"[A-Za-z0-9_-]+\\\\"' skills/INSTALL.md | sort -u | wc -l)
  if [ "$count" -lt 13 ]; then
    # Try without escape
    count=$(grep -oE '"[A-Za-z0-9_-]+"' skills/INSTALL.md | sort -u | wc -l)
  fi
  [ "$count" -ge 13 ]
}

@test "install_lib: INSTALL.md L3 description uses count-based phrasing (no enumerated names)" {
  # Description should NOT contain a comma-separated list of skill names inside parentheses
  desc=$(sed -n '1,15p' skills/INSTALL.md | grep -E "description:")
  # If it lists skill names separated by /, that's the fragile form
  if echo "$desc" | grep -qE "全部 [0-9]+ 个子技能.*\\(.*/.*\\)"; then
    # Check that the parenthetical list has fewer entries than claimed
    count_in_paren=$(echo "$desc" | sed -E 's/.*\((.*)\).*/\1/' | tr '/' '\n' | wc -l)
    claimed=$(echo "$desc" | grep -oE '全部 [0-9]+' | grep -oE '[0-9]+')
    if [ -n "$claimed" ] && [ "$count_in_paren" -lt "$claimed" ]; then
      echo "INSTALL.md description claims $claimed but lists $count_in_paren names"
      return 1
    fi
  fi
}

@test "install_lib: _lib/schemas/*.json are listed in install" {
  run grep -E 'schemas.*\.json|_lib/schemas' install.sh skills/INSTALL.md
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}
EOF
chmod +x tests/integration/test_install_lib_distribution.bats
```

- [ ] **Task 2.2**: 看红（预期多数断言失败）

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_install_lib_distribution.bats 2>&1 | tail -20
```

Expected: ≥ 6 个 `@test` 失败（因为还没改任何文件）。

- [ ] **Task 2.3**: 新增两个 `__init__.py`

```bash
cd /workspace/project/rdd-workflow
touch skills/__init__.py
touch skills/_lib/__init__.py
ls -la skills/__init__.py skills/_lib/__init__.py
```

- [ ] **Task 2.4**: 看部分红转绿

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_install_lib_distribution.bats 2>&1 | grep -E "^(ok|not ok)"
```

Expected: 至少 2 个 `@test` 转绿（`__init__.py` 那两个），其他仍红。

- [ ] **Task 2.5**: 写 Python 端 import 测试

```bash
mkdir -p tests/unit
cat > tests/unit/test_install_lib_distribution.py <<'EOF'
"""Lock the contract that all production-critical _lib modules are importable.

Mirrors the dependency chain declared in feature.md and rddf-session.md frontmatter:
- feature depends on [iteration, deps_output]
- rddf-session depends on [rddf_session]

These imports must work post-install (i.e., after copying _lib/ to a project).
With empty __init__.py markers on skills/ and skills/_lib/, the absolute
import `from skills._lib.X import Y` resolves as long as the project root is on
sys.path (which tests/conftest.py ensures for the test runtime).
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_repo_root_on_path() -> None:
    """Mirror what install.sh would do: keep project root on sys.path."""
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


@pytest.fixture(autouse=True)
def _repo_root_on_path() -> None:
    _ensure_repo_root_on_path()


@pytest.mark.parametrize("module_name", [
    "skills._lib.iteration",
    "skills._lib.deps_output",
    "skills._lib.rddf_session",
    "skills._lib.state_vector",
    "skills._lib.event_log",
    "skills._lib.lock",
    "skills._lib.feature_view",
    "skills._lib.gate",
])
def test_lib_module_importable(module_name: str) -> None:
    """Each _lib module declared as a dependency MUST import without error."""
    importlib.import_module(module_name)


def test_lib_has_init_marker() -> None:
    assert (REPO_ROOT / "skills" / "__init__.py").exists(), (
        "skills/__init__.py must exist for skills to be a Python package"
    )
    assert (REPO_ROOT / "skills" / "_lib" / "__init__.py").exists(), (
        "skills/_lib/__init__.py must exist for skills._lib to be importable"
    )


def test_init_markers_are_empty_or_minimal() -> None:
    """__init__.py should be empty (or near-empty) — no side-effect imports."""
    for rel in ("skills/__init__.py", "skills/_lib/__init__.py"):
        text = (REPO_ROOT / rel).read_text()
        # Allow empty, docstring, or one-line comment; no import statements
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
        for ln in lines:
            assert not ln.startswith(("import ", "from ")), (
                f"{rel} contains a side-effect import: {ln!r}"
            )
EOF
```

- [ ] **Task 2.6**: 跑 Python 测试 — 应该全绿（仓库内 conftest.py 已加 sys.path）

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/test_install_lib_distribution.py -v
```

Expected: 全部通过（8 个 parametrized + 2 个独立）。

- [ ] **Task 2.7**: 提交

```bash
cd /workspace/project/rdd-workflow
git add skills/__init__.py skills/_lib/__init__.py tests/integration/test_install_lib_distribution.bats tests/unit/test_install_lib_distribution.py
git commit -m "feat(install): add Python package markers + _lib import contract tests"
```

---

## 3. install.sh + INSTALL.md 复制逻辑（glob 扩展 + 排除规则）

- [ ] **Task 3.1**: 修改 `install.sh` L29-32 — 加 `_lib/` 递归复制

```bash
cd /workspace/project/rdd-workflow
# Read current L29-33
sed -n '29,33p' install.sh
```

期望 L29 是 `mkdir -p`，L32 是 `cp -f` `.md`。具体修改用 Edit：

**Old**:
```bash
# 创建目标目录
mkdir -p "$TARGET_DIR/.opencode/skills/rdd-workflow/skills"

# 复制所有子技能
cp -f "$PACKAGE_DIR/skills/"*.md "$TARGET_DIR/.opencode/skills/rdd-workflow/skills/"

# 复制 package.json（如果存在）
```

**New**:
```bash
# 创建目标目录
mkdir -p "$TARGET_DIR/.opencode/skills/rdd-workflow/skills"
mkdir -p "$TARGET_DIR/.opencode/skills/rdd-workflow/skills/_lib/schemas"

# 复制所有子技能（.md）
cp -f "$PACKAGE_DIR/skills/"*.md "$TARGET_DIR/.opencode/skills/rdd-workflow/skills/"

# 复制 skills/_lib/ 运行时所需 Python 模块与 schemas（排除 __pycache__ / plugins / schedulers）
# 这样 feature.md 和 rddf-session.md 的 depends-on 模块才能在目标项目里 import
if [ -d "$PACKAGE_DIR/skills/_lib" ]; then
    find "$PACKAGE_DIR/skills/_lib" \
        -type d \( -name __pycache__ -o -name plugins -o -name schedulers \) -prune \
        -o -type f \( -name '*.py' -o -name '*.json' \) -print 2>/dev/null | while read -r src; do
        rel="${src#$PACKAGE_DIR/}"
        mkdir -p "$TARGET_DIR/.opencode/skills/rdd-workflow/$(dirname "$rel")"
        cp -f "$src" "$TARGET_DIR/.opencode/skills/rdd-workflow/$rel"
    done
fi

# 复制 package.json（如果存在）
```

- [ ] **Task 3.2**: 跑 bats 看红 → 改完看绿

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_install_lib_distribution.bats 2>&1 | grep -E "^(ok|not ok)"
```

预期：3 个 install.sh 相关 `@test` 由红转绿。

- [ ] **Task 3.3**: 修改 `skills/INSTALL.md` L98-104 — 镜像 `install.sh`

```bash
cd /workspace/project/rdd-workflow
sed -n '98,104p' skills/INSTALL.md
```

**Old**:
```bash
# 复制所有子技能
cp -f "$PACKAGE_DIR/skills/"*.md "$SKILLS_DIR/skills/"

echo "✅ 子技能已复制:"
ls -1 "$SKILLS_DIR/skills/"
```

**New**:
```bash
# 复制所有子技能（.md）
cp -f "$PACKAGE_DIR/skills/"*.md "$SKILLS_DIR/skills/"

# 复制 skills/_lib/ 运行时所需 Python 模块与 schemas
# 这样 feature.md (depends-on: [iteration, deps_output]) 和 rddf-session.md (depends-on: [rddf_session])
# 在目标项目里也能正常 import
if [ -d "$PACKAGE_DIR/skills/_lib" ]; then
    mkdir -p "$SKILLS_DIR/skills/_lib/schemas"
    find "$PACKAGE_DIR/skills/_lib" \
        -type d \( -name __pycache__ -o -name plugins -o -name schedulers \) -prune \
        -o -type f \( -name '*.py' -o -name '*.json' \) -print 2>/dev/null | while read -r src; do
        rel="${src#$PACKAGE_DIR/}"
        mkdir -p "$SKILLS_DIR/$(dirname "$rel")"
        cp -f "$src" "$SKILLS_DIR/$rel"
    done
fi

# Python sys.path 提示：target 项目的 root 需要在 sys.path 才能 `from skills._lib.X import Y`
# 在 AI 助手环境中通常已经满足（conftest.py 自动加）; 在 npx 直接调用场景需用户配置
cat >> "$SKILLS_DIR/INSTALL_NOTES.txt" << 'NOTES'
skills/ 已被复制到本项目 .opencode/skills/rdd-workflow/ 下。

要让 skills/*.md 中的 Python depends-on 模块能 import，需要：
1. 确保本项目根目录在 Python sys.path 中（多数 AI 编程助手自动处理）
2. skills/ 目录下存在 __init__.py 文件（已包含在本次安装中）

如果运行 skill 报 ImportError，请检查上述两点。
NOTES

echo "✅ 子技能已复制:"
ls -1 "$SKILLS_DIR/skills/"
echo "✅ _lib 模块已复制（49 .py + 7 schema）:"
find "$SKILLS_DIR/skills/_lib" -type f \( -name '*.py' -o -name '*.json' \) | wc -l
```

- [ ] **Task 3.4**: 跑 bats 全绿

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_install_lib_distribution.bats 2>&1 | grep -E "^(ok|not ok)"
```

预期：所有 `@test` 全绿（除 INSTALL.md fallback / description 那两个 Task 4 处理）。

- [ ] **Task 3.5**: 提交

```bash
cd /workspace/project/rdd-workflow
git add install.sh skills/INSTALL.md
git commit -m "feat(install): distribute skills/_lib/*.py + schemas with proper exclusions"
```

---

## 4. INSTALL.md 三处漂移修复（description / fallback L115 / fallback L118）

- [ ] **Task 4.1**: 修改 L3 description（计数式，不列举名字）

```bash
cd /workspace/project/rdd-workflow
sed -n '1,8p' skills/INSTALL.md
```

**Old** (frontmatter):
```yaml
description: 安装 RDD Workflow 技能到项目目录。执行后会将全部 13 个子技能（INSTALL/guide/guide-arch/guide-plan/guide-ship/propose/roadmap/deps/execute/status/rdd-workflow-writing-plans/feature）复制到项目的 .opencode/skills/ 目录。
```

**New**:
```yaml
description: 安装 RDD Workflow 技能到项目目录。执行后会将 skills/ 目录下所有子技能（含运行时 Python 模块）复制到项目的 .opencode/skills/rdd-workflow/ 目录。
```

注：不再列举具体 skill 名字，避免未来加 skill 时描述漂移。具体 skill 数量由 `ls skills/*.md | wc -l` 动态决定（当前 13）。

- [ ] **Task 4.2**: 修改 L115 + L118 fallback（动态推导 + 最小保底）

```bash
cd /workspace/project/rdd-workflow
sed -n '113,120p' skills/INSTALL.md
```

**Old**:
```bash
        PKG_SKILLS=$(python3 -c "import json,sys;print(','.join(['\"'+s+'\"' for s in json.load(open('$PACKAGE_DIR/package.json'))['skills']]))" 2>/dev/null || echo '"INSTALL","guide","guide-arch","guide-plan","guide-ship","propose","execute","status","roadmap","deps","rdd-workflow-writing-plans"')
    else
        PKG_VERSION="2.0.0-beta"
        PKG_SKILLS='"INSTALL","guide","guide-arch","guide-plan","guide-ship","propose","execute","status","roadmap","deps","rdd-workflow-writing-plans"'
    fi
```

**New**:
```bash
        # 动态推导 skills 列表（避免硬编码漂移）
        PKG_SKILLS=$(python3 -c "import json;print(','.join(['\"'+s+'\"' for s in json.load(open('$PACKAGE_DIR/package.json'))['skills']]))" 2>/dev/null)
    else
        PKG_VERSION="2.0.0-beta"
        # 磁盘推导 fallback：从 skills/*.md 动态生成 skill 列表（避免与 package.json 漂移）
        # 这样无论 sync-workflow-contracts Decision 3 是 A（13）还是 B（11），fallback 都正确反映磁盘真相
        PKG_SKILLS=$(ls "$PACKAGE_DIR/skills/"*.md 2>/dev/null \
            | xargs -n1 basename 2>/dev/null \
            | sed 's/\.md$//' \
            | sort -u \
            | awk 'BEGIN{ORS=""; printf "\""}{printf "\"" $0 "\","}' \
            | sed 's/,$//')
    fi
    # 当 PKG_SKILLS 仍为空（python3 与 source 都不可用）的兜底
    if [ -z "$PKG_SKILLS" ]; then
        PKG_SKILLS='"INSTALL"'
    fi
```

- [ ] **Task 4.3**: 跑 bats 全绿

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_install_lib_distribution.bats 2>&1 | grep -E "^(ok|not ok)"
```

预期：所有 `@test` 全绿。

- [ ] **Task 4.4**: 提交

```bash
cd /workspace/project/rdd-workflow
git add skills/INSTALL.md
git commit -m "fix(install): make INSTALL.md description + fallback drift-free"
```

---

## 5. 验证（Verification）

- [ ] **Task 5.1**: 跑新增 anti-drift 测试

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_install_lib_distribution.bats
python3 -m pytest tests/unit/test_install_lib_distribution.py -v
```

Expected: 全绿。

- [ ] **Task 5.2**: 跑既有测试零回归

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/ -q --tb=short 2>&1 | tail -3
python3 -m pytest tests/integration/ -q --tb=short 2>&1 | tail -3
bats tests/smoke.bats 2>&1 | tail -3
```

Expected: 所有既有测试继续通过。

- [ ] **Task 5.3**: 跑 OpenSpec 校验

```bash
cd /workspace/project/rdd-workflow
openspec validate fix-install-lib-distribution --strict
```

Expected: `Change 'fix-install-lib-distribution' is valid`.

- [ ] **Task 5.4**: CI 质量门控

```bash
cd /workspace/project/rdd-workflow
! grep -rn 'assert.*or True\|assert True' tests/
```

Expected: exit 0.

- [ ] **Task 5.5**: 端到端模拟 — 手动验证 install 后 import

```bash
cd /workspace/project/rdd-workflow

# 临时创建一个模拟 install 路径
TMP=$(mktemp -d)
mkdir -p "$TMP/.opencode/skills/rdd-workflow/skills/_lib/schemas"
SKILLS_DIR="$TMP/.opencode/skills/rdd-workflow"

# 复刻 install.sh 的核心步骤
cp -f skills/*.md "$SKILLS_DIR/skills/"
find skills/_lib \
    -type d \( -name __pycache__ -o -name plugins -o -name schedulers \) -prune \
    -o -type f \( -name '*.py' -o -name '*.json' \) -print | while read -r src; do
    rel="${src}"
    mkdir -p "$SKILLS_DIR/$(dirname "$rel")"
    cp -f "$src" "$SKILLS_DIR/$rel"
done
touch "$SKILLS_DIR/skills/__init__.py" "$SKILLS_DIR/skills/_lib/__init__.py"

# 验证：在 TMP 模拟安装目录里能 import
cd "$SKILLS_DIR"
PYTHONPATH="$SKILLS_DIR" python3 -c "
import sys
sys.path.insert(0, '$SKILLS_DIR')
from skills._lib.iteration import save, load
from skills._lib.deps_output import build_analysis
from skills._lib.rddf_session import RddfSessionCoordinator
print('OK: 所有依赖 _lib 模块在 install 路径下可 import')
"

# 清理
cd /workspace/project/rdd-workflow
rm -rf "$TMP"
```

Expected: 打印 `OK: 所有依赖 _lib 模块在 install 路径下可 import`。

---

## 6. Acceptance + 提交

- [ ] **Task 6.1**: tick proposal.md 的 acceptance criteria

把 `openspec/changes/fix-install-lib-distribution/proposal.md` 中 `## Acceptance Criteria` 段的 `- [ ]` 改为 `- [x]`（仅已完成的项）。

- [ ] **Task 6.2**: 终态汇报

```bash
cd /workspace/project/rdd-workflow

echo "=== openspec validate ==="
openspec validate fix-install-lib-distribution --strict

echo "=== pytest unit ==="
python3 -m pytest tests/unit/ -q --tb=short

echo "=== pytest integration ==="
python3 -m pytest tests/integration/ -q --tb=short

echo "=== bats all ==="
bats tests/

echo "=== CI gate ==="
if grep -rn 'assert.*or True\|assert True' tests/; then
    echo "FAIL"
else
    echo "PASS"
fi

echo "=== git status ==="
git status --short
```

---

## 7. Follow-ups（显式推迟）

- ❌ **F1**: npm 端 slim package（`.npmignore` 排除 dev-only `arch_quality_gate.py` 等）—— 不在 v1 scope。
- ❌ **F2**: 重构 `_lib/*.py` 之间的相对导入（`from .lock import FileLock`）—— 大批量改动，超出 scope。
- ❌ **F3**: `sync-workflow-contracts` Decision 3 (design.md:74-87) 翻 A 必须在**本 change 落地后**才能做——这是设计上的硬顺序依赖。
  > 注：本 change 与 sync-workflow-contracts 在文档中曾用 "Decision 1" 与 "Decision 3" 互相指代，是命名错位（实际指同一件事，即 `package.json::skills[]` 是否补 `feature` + `rddf-session`）。F3 中的 "Decision 3" 是 sync-workflow-contracts 设计中的真实编号。
- ❌ **F4**: `arch_quality_gate.py` ADR-0013 → ADR-0018 错引修复——独立 change。