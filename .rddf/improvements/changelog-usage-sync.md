# changelog-usage-sync

**优先级**: P1 (↑ from P2, 2026-08-28 per feat-fix-archive-gaps-v2) | **来源**: 2026-08-26 文档与代码一致性审计
**阶段**: default | **分类**: docs
**类型**: improvement
**状态**: ⏳ 已推迟 → ⬆ P1 升级 2026-08-28 (per feat-fix-archive-gaps-v2 评估; 待 guide-design 重新审查)

## 架构依据

CHANGELOG.md 是权威的"变更日志"——记录每个 release / 阶段的变更条目。USAGE.md 是用户视角的"完整使用指南"——它需要在每个版本变更后同步更新。

2026-08-26 审计发现 USAGE.md 顶部明确写：

> **当前版本: v2.0 / v2.0.1**（三阶段架构 arch → plan → ship + ...）

但实际 v3.0.0 已发布，五阶段架构已上线。CHANGELOG.md 的 [Unreleased] 段（line 5-16）已记录 rdd-verifier 5th phase，但 USAGE.md 没跟进。

这是"文档同步"问题的典型例子——CHANGELOG 改得快，USAGE 改得慢（或忘了改）。

## 范围

**In Scope**:
- 在 `_lib/doctor.py`（或新建 `_lib/changelog_usage_sync.py`）新增检查：CHANGELOG [Unreleased] 段的"Added/Changed/Fixed"段落 → USAGE.md 是否提及相应内容
- pre-commit hook：当 CHANGELOG.md 改动时，强制要求 USAGE.md 顶部"当前版本"段更新
- `tests/integration/test_changelog_usage_sync.bats`：基础一致性测试
- USAGE.md 顶部 banner 改为 auto-generated（来自 package.json version + CHANGELOG latest tag）

**Out of Scope**:
- 自动修改 USAGE.md（保持 human-in-loop）
- CHANGELOG 格式变更（保持现有 `[Unreleased]` + `## [vX.Y.Z]` 格式）

## 设计

### 简单方案：pre-commit 提醒

```bash
# .git-hooks/pre-commit
if git diff --cached --name-only | grep -q "CHANGELOG.md"; then
    if ! git diff --cached --name-only | grep -q "USAGE.md"; then
        echo "⚠️  CHANGELOG.md 改动但 USAGE.md 未更新" >&2
        echo "   如果 CHANGELOG 是 typo/wording 修正，可忽略此提醒" >&2
        echo "   如果是新增功能/破坏变更，必须同步 USAGE.md" >&2
        # exit 1  # 默认不阻断，仅提示
    fi
fi
```

### 进阶方案：USAGE.md 顶部 banner 自动化

USAGE.md 顶部加占位符：

```markdown
<!-- VERSION_BANNER_START -->
> 当前版本: **v3.0+**（五阶段架构 arch → design → plan → ship → verify）
> `package.json` 当前版本 `3.0.0`。
<!-- VERSION_BANNER_END -->
```

脚本 `_lib/sync_usage_banner.py`：

```python
"""从 package.json + CHANGELOG.md 自动生成 USAGE.md 顶部 banner."""
from pathlib import Path
import json
import re

REPO_ROOT = Path(__file__).resolve().parents[1]


def get_latest_version() -> str:
    pkg = json.loads((REPO_ROOT / "package.json").read_text())
    return pkg["version"]


def get_phase_count() -> int:
    """5 阶段 = arch/design/plan/ship/verify；通过 AGENTS.md 阶段表确认."""
    agents = (REPO_ROOT / "AGENTS.md").read_text()
    return agents.count("| verify |") + agents.count("| design |") + 1  # arch/plan/ship 必存在


def generate_banner(version: str, phase_count: int = 5) -> str:
    stages = " → ".join(["arch", "design", "plan", "ship", "verify"][:phase_count])
    return (
        f"> 当前版本: **v{version}+**（{'/'.join([s for s in ['arch', 'design', 'plan', 'ship', 'verify'][:phase_count]])} 五阶段架构 {stages}）\n"
        f"> `package.json` 当前版本 `{version}`。\n"
    )


def regenerate() -> None:
    usage = REPO_ROOT / "USAGE.md"
    text = usage.read_text()
    
    version = get_latest_version()
    banner = generate_banner(version)
    
    pattern = re.compile(
        r"<!-- VERSION_BANNER_START -->.*?<!-- VERSION_BANNER_END -->",
        re.DOTALL,
    )
    
    new_section = f"<!-- VERSION_BANNER_START -->\n{banner}<!-- VERSION_BANNER_END -->"
    
    if pattern.search(text):
        new_text = pattern.sub(new_section, text)
    else:
        # 首次生成：插入到 USAGE.md 顶部
        new_text = new_section + "\n" + text
    
    usage.write_text(new_text)
    print(f"✅ USAGE.md banner updated to v{version}")


if __name__ == "__main__":
    regenerate()
```

CLI：

```bash
python3 _lib/sync_usage_banner.py
# 输出：✅ USAGE.md banner updated to v3.0.0
```

### CI 守护

`tests/integration/test_changelog_usage_sync.bats`：

```bats
@test "changelog-usage sync: USAGE.md banner matches package.json version" {
  run python3 - <<'PY'
import json, re
from pathlib import Path

pkg_ver = json.loads(Path("package.json").read_text())["version"]
usage = Path("USAGE.md").read_text()

# 提取 USAGE.md 顶部 banner 中的版本
m = re.search(r"v(\d+\.\d+(?:\.\d+)?)", usage)
if not m:
    raise SystemExit("USAGE.md missing version banner")

banner_ver = m.group(1)
if banner_ver != pkg_ver:
    raise SystemExit(f"USAGE.md banner={banner_ver}, package.json={pkg_ver}")
PY
  [ "$status" -eq 0 ]
}
```

## 影响

- **正向**：USAGE.md 版本 banner 永远与 package.json 一致
- **正向**：CHANGELOG 改动时 pre-commit 强制提醒（可选升级为阻断）
- **风险**：自动 banner 可能不够 human-friendly，需保留 human override 注释
- **兼容性**：纯增强，不破坏现有 CHANGELOG 格式

## 验收

- [ ] USAGE.md 含 `<!-- VERSION_BANNER_START --> ... <!-- VERSION_BANNER_END -->` 占位符
- [ ] `_lib/sync_usage_banner.py` 实现
- [ ] pre-commit hook 安装指引（不强制，可选）
- [ ] `tests/integration/test_changelog_usage_sync.bats` PASS
- [ ] CHANGELOG.md [Unreleased] 改动时，CI 跑 `python3 _lib/sync_usage_banner.py --check` 验证 USAGE.md 是否需更新

## 后续 (follow-up)

- 自动同步 README.md / INSTALL.md 顶部 banner
- CHANGELOG 自动化（Conventional Commits → CHANGELOG 条目）