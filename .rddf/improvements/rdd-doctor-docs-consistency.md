# rdd-doctor-docs-consistency

**优先级**: P1 | **来源**: 2026-08-26 文档与代码一致性审计
**阶段**: default | **分类**: governance
**类型**: feature

## 架构依据

`rdd-doctor` 当前只校验 5 类结构化文件（`.rddf/state/*.json` schema / `.rddf/plans/*.md` TDD 5 步 / `openspec/changes/*/roadmap-meta.yaml` / `proposal-*.md` 表格 / `openspec/changes/*/tasks.md` checkbox）。它是 read-only 的诊断工具，输出 CRITICAL/WARNING/INFO 三级报告。

2026-08-26 审计发现 6 类**文档一致性**问题，均为 rdd-doctor 当前不覆盖：

| 问题类型 | 出现位置 | rdd-doctor 当前覆盖？ |
|----------|----------|---------------------|
| 子技能数量不一致 | README (12) / INSTALL (20) / USAGE (13) / package.json (25) / 磁盘 (25) | ❌ |
| 阶段架构数字不一致 | README (4) / USAGE (3) / AGENTS (4+5 混合) | ❌ |
| npm test 行为反向提示 | README/AGENTS/CHANGELOG/USAGE (4 处声称"不跑 Python") vs package.json (跑) | ❌ |
| 版本号冲突 | README (v2.1+) / package.json (v3.0.0) / INSTALL (2.0.0-beta) | ❌ |
| 关键 ADR 列表过期 | AGENTS.md line 148 漏列 ADR-0025/0027/0029/0031/0034 | ❌ |
| 角色 frontmatter 不一致 | AGENTS.md 称"4 个阶段技能 role:"，但 `rdd-verifier` 也有 role: | ❌ |

每一类都是"软腐烂"——单独看每个文档都没大问题，但叠加起来造成用户**理解错位**（以为是 v2.0 但实际是 v3.0；以为没有 verify 但实际有）。

新增 `--category docs-consistency` 让 rdd-doctor 能定期巡检，CI 或开发者在 commit 前能自查。

## 范围

**In Scope**:
- `_lib/cli/doctor_cmd.py` 新增 `--category docs-consistency` 路由
- `_lib/doctor.py` 或新建 `_lib/docs_consistency.py` 实现 6 类检查：
  1. 子技能数量：package.json::skills[] == INSTALL.md 表行数 == 磁盘 `*/SKILL.md` 数
  2. 阶段架构数字：grep "三阶段\|四阶段\|五阶段\|3 阶段\|4 阶段\|5 阶段" 在 README/USAGE/AGENTS 中应一致
  3. npm test 行为：grep "npm test.*不跑" 应为空（v3.0+ 修正后）
  4. 版本号：package.json version 字符串 == README/INSTALL 顶部 banner 中的版本（允许 "vX.Y+" 模式）
  5. ADR 列表：AGENTS.md line 148 列出的 ADR 编号都在 `docs/adr/ADR-*.md` 实际存在
  6. 阶段 skill 数量：`grep -l "^role:" skills/{guide-arch,guide-design,guide-plan,guide-ship,rdd-verifier}/SKILL.md` 期望 5 个
- `tests/integration/test_rdd_doctor.bats` 添加 6 个新 case
- `tests/unit/test_docs_consistency.py` 添加 6 个新 unit test
- 不破坏现有 5 类 category 的行为

**Out of Scope**:
- 自动修复文档（rdd-doctor 保持 read-only；自动修复属 P2 changelog-usage-sync 提案）
- 跨项目扫描（rdd-doctor 是项目本地工具；跨项目治理属 ADR-0027 L2 上报）
- ADR 自动生成（属 P2 adr-index-auto-sync 提案）

## 设计

### CLI 集成

```bash
# 单类别
bash skills/rdd-doctor/scripts/doctor.sh --category docs-consistency

# 完整巡检（含现有 5 类 + docs-consistency）
bash skills/rdd-doctor/scripts/doctor.sh --category all

# JSON 输出
bash skills/rdd-doctor/scripts/doctor.sh --category docs-consistency --json
```

### 实现骨架（`_lib/docs_consistency.py`）

```python
"""docs-consistency doctor category: 6 类文档与代码一致性校验."""
from pathlib import Path
import json
import re

REPO_ROOT = Path(__file__).resolve().parents[1]


def check_skill_count() -> list[dict]:
    """子技能数量三方对齐."""
    issues = []
    pkg = json.loads((REPO_ROOT / "package.json").read_text())
    declared = len(pkg["skills"])
    disk = len(list((REPO_ROOT / "skills").glob("*/SKILL.md")))
    
    if declared != disk:
        issues.append({
            "severity": "CRITICAL",
            "name": "skill-count-package-vs-disk",
            "detail": f"package.json skills[]={declared}, disk */SKILL.md={disk}",
            "fix_command": "see sync-package-skills-to-disk proposal",
        })
    
    install = (REPO_ROOT / "skills/INSTALL.md").read_text()
    # INSTALL.md 表行数 = ... (extract table rows)
    ...
    return issues


def check_stage_count() -> list[dict]:
    """阶段架构数字一致 (5 阶段：arch/design/plan/ship/verify)."""
    issues = []
    expected = "五阶段\|5 阶段\|five-stage\|arch → design → plan → ship → verify"
    
    for doc in ("README.md", "USAGE.md", "AGENTS.md"):
        text = (REPO_ROOT / doc).read_text()
        # 三阶段 / 四阶段 / 5 阶段 grep
        stage_mentions = re.findall(r"[三四五六]阶段", text)
        inconsistent = [m for m in stage_mentions if m not in ("五阶段",)]
        if inconsistent:
            issues.append({
                "severity": "WARNING",
                "name": f"stage-count-{doc}",
                "detail": f"在 {doc} 中发现 {len(inconsistent)} 处非'五阶段'提及: {set(inconsistent)}",
                "fix_command": f"手动更新 {doc}",
            })
    return issues


def check_npm_test_caveat() -> list[dict]:
    """v3.0+ npm test 同时跑 bats + pytest; 不应有反向提示."""
    issues = []
    for doc in ("README.md", "AGENTS.md", "USAGE.md", "skills/INSTALL.md", "CHANGELOG.md"):
        text = (REPO_ROOT / doc).read_text()
        # 反向提示（"npm test 不跑 Python" / "npm test 不会"）
        anti_patterns = re.findall(
            r"npm test\s*(只跑|不会|不跑|仅跑).{0,40}Python", text
        )
        if anti_patterns:
            issues.append({
                "severity": "CRITICAL",
                "name": f"npm-test-anti-pattern-{doc}",
                "detail": f"v3.0+ 已修正，{doc} 中发现 {len(anti_patterns)} 处反向提示",
                "fix_command": f"手动更新 {doc}",
            })
    return issues


def check_version_consistency() -> list[dict]:
    """package.json version vs 文档顶部 banner."""
    pkg = json.loads((REPO_ROOT / "package.json").read_text())
    expected = pkg["version"]
    issues = []
    
    for doc in ("README.md", "skills/INSTALL.md"):
        text = (REPO_ROOT / doc).read_text()
        # 允许 "vX.Y+" / "vX.Y" / "vX.Y.Z" 模式
        versions = re.findall(r"v(\d+\.\d+(?:\.\d+)?)\+?", text)
        if versions:
            # 与 expected 不一致的版本号
            inconsistent = [v for v in set(versions) if not _is_compatible(v, expected)]
            if inconsistent:
                issues.append({
                    "severity": "WARNING",
                    "name": f"version-drift-{doc}",
                    "detail": f"package.json={expected}, {doc} 提到 {sorted(set(inconsistent))}",
                    "fix_command": f"手动更新 {doc} 顶部 banner",
                })
    return issues


def check_adr_list_completeness() -> list[dict]:
    """AGENTS.md 列出的 ADR 都存在."""
    issues = []
    agents = (REPO_ROOT / "AGENTS.md").read_text()
    # extract ADR-NNNN refs
    referenced = set(re.findall(r"ADR-(\d{4})", agents))
    
    adr_dir = REPO_ROOT / "docs/adr"
    real = {p.stem.split("-")[1] for p in adr_dir.glob("ADR-*.md") if p.stem.startswith("ADR-")}
    # 提取 4 位数字
    
    missing_in_disk = {f"ADR-{n}" for n in referenced if n not in real}
    if missing_in_disk:
        issues.append({
            "severity": "WARNING",
            "name": "adr-list-refs-missing",
            "detail": f"AGENTS.md 引用但磁盘无: {sorted(missing_in_disk)}",
            "fix_command": "删除 AGENTS.md 中的引用",
        })
    return issues


def check_role_frontmatter() -> list[dict]:
    """5 个阶段 skill 都有 role: frontmatter."""
    issues = []
    phase_skills = ("guide-arch", "guide-design", "guide-plan", "guide-ship", "rdd-verifier")
    missing = []
    for skill in phase_skills:
        path = REPO_ROOT / "skills" / skill / "SKILL.md"
        if not path.exists():
            missing.append(skill)
            continue
        text = path.read_text()
        if not re.search(r"^role:", text, re.MULTILINE):
            missing.append(skill)
    
    if missing:
        issues.append({
            "severity": "WARNING",
            "name": "role-frontmatter-missing",
            "detail": f"缺少 role: frontmatter: {missing}",
            "fix_command": "添加 role: 字段 (per ADR-0028)",
        })
    return issues


def run_all() -> list[dict]:
    """聚合所有 docs-consistency 检查."""
    return (
        check_skill_count() +
        check_stage_count() +
        check_npm_test_caveat() +
        check_version_consistency() +
        check_adr_list_completeness() +
        check_role_frontmatter()
    )
```

### 测试覆盖

`tests/unit/test_docs_consistency.py`：

```python
def test_skill_count_aligned():
    issues = check_skill_count()
    assert issues == [], f"skill count drift: {issues}"


def test_stage_count_consistent():
    issues = check_stage_count()
    assert issues == [], f"stage count drift: {issues}"


def test_no_npm_test_anti_pattern():
    issues = check_npm_test_caveat()
    assert issues == [], f"npm test anti-patterns: {issues}"


# ... 其余 3 个
```

`tests/integration/test_rdd_doctor.bats` 添加：

```bats
@test "rdd-doctor docs-consistency: detects skill count drift" {
  # 模拟 drift
  cp package.json /tmp/package.json.bak
  echo '{"skills":["INSTALL","guide"]}' > package.json
  run bash skills/rdd-doctor/scripts/doctor.sh --category docs-consistency --quiet
  assert_failure
  # 还原
  cp /tmp/package.json.bak package.json
}

@test "rdd-doctor docs-consistency: all 6 checks pass on master" {
  run bash skills/rdd-doctor/scripts/doctor.sh --category docs-consistency --quiet
  assert_success
}
```

## 影响

- **正向**：rdd-doctor 巡检从 5 类扩展到 11 类（5 现有 + 6 新），覆盖文档腐烂盲区
- **正向**：开发者 commit 前可自查（pre-commit hook 集成是 follow-up）
- **正向**：CI 可在 `bats tests/integration/test_rdd_doctor.bats` 强制文档与代码一致
- **风险**：docs-consistency 检查是 project-local，跨 fork 项目（npm 安装到第三方项目）的 rdd-doctor 不会强制；保留 read-only 不影响用户
- **兼容性**：不破坏现有 `--category state|plan-tdd|roadmap-meta|proposal-table|tasks-checkbox` 行为；`--category all` 自动包含新类

## 验收

- [ ] `_lib/docs_consistency.py` 6 个检查函数实现
- [ ] `_lib/cli/doctor_cmd.py` 新增 `--category docs-consistency` 路由
- [ ] `bash skills/rdd-doctor/scripts/doctor.sh --category docs-consistency` 在 master 分支运行 0 CRITICAL + 0 WARNING
- [ ] `bash skills/rdd-doctor/scripts/doctor.sh --category all` 包含 docs-consistency
- [ ] `tests/unit/test_docs_consistency.py` 6+ 个 unit test PASS
- [ ] `tests/integration/test_rdd_doctor.bats` 新增 6+ 个 integration test PASS
- [ ] 文档同步：CHANGELOG.md 添加本次 change 条目；README/AGENTS rdd-doctor 描述更新
- [ ] 新提案：把 docs-consistency 检查接入 pre-commit hook 作为 follow-up