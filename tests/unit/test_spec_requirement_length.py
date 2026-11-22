"""Guard: `openspec validate` 的 **`very long`** issue 集合必须保持已知状态。

## 为什么需要这个守卫

`openspec validate` 的**文本输出不显示** `requirements[N]` 这类 issue —— 只有 `--json` 才报。
⇒ 早期批次的验收判据「`openspec validate` 输出逐字节相同」（用文本输出）**从未覆盖**
`very long` 增量。实测：历史批次合计引入了 **25 条** `very long` advisory，无人验过。

本文件把那个维度变成**常驻守卫**：任何后续批次若让 Requirement 正文跨过 500，
断言会红 ⇒ 必须显式更新冻结清单（并在同一提交里说明「新增的 very long 是否可接受」）。

## ⚠️ 执法点是**本地**，不是 CI

`openspec/` 整树被 `.gitignore:45` 排除 ⇒ **CI 上 `openspec/specs/` 不存在** ⇒ 守卫在 CI 上
恒 `skip`（这**是预期行为**：CI 上没有可校验的 spec，让它 fail 只会让 CI 恒红）。
⇒ 守卫的执法时机 = **本地执行批次时**（agent 跑批次、改 spec 的那一刻）。
台账：`.rddf/reviews/spec-very-long-baseline-2026-11-21.md`。

## 口径

**完全交给 openspec 自己**（CI 装 `@fission-ai/openspec@1.14.3`，与本仓一致）⇒
**零口径漂移** —— 不在 Python 里复刻 openspec 的 parser。

- 断言 **A**：当前 `openspec/specs/` 的 `requirements[N]: very long` 多重集
  == :data:`FROZEN_VERY_LONG`（62 条 / 38 spec）—— 抓「出现 / 消失 / 换位」。
- 断言 **B**：「注入造成的增量」== :data:`FROZEN_INJECTED_VL`（25 条 / 13 spec）——
  **直接针对判据缺口**：任何批次的新注记若把 Requirement 推过 500 ⇒ 红。

断言 B 的实现：在临时项目里放一份「去掉全部注入内容」的 `openspec/specs/` 副本 ⇒
跑同一个 CLI ⇒ 与当前清单求差集 ⇒ 差集 = 注入造成的。

### 前提：临时项目不拷 `openspec/config.yaml`

本仓的 `openspec/config.yaml` 当前只有 `defaultSchema: spec-driven`（对 `very long` 无影响）
⇒ 不拷它不影响判定。⚠️ **若将来 config 增加了影响校验的项，断言 A 的口径会静默偏离真实仓库**
⇒ 届时必须把 config 一并拷进临时项目。

## 「注入内容」的识别规则（4 类形态，全仓实测）

===============  ==================================================  =====
形态              规则                                                计数
===============  ==================================================  =====
① 标注            ``^<!-- v4-residue:allow=[a-z-]+ -->$``（独占行）    207
② 批 5 先例       ``^- \\*\\*NOTE\\*\\* \\(retired ``（独占行）           2
③ 批 7a 注记      ``^> \\*\\*已退役（YYYY-MM-DD）``（独占行）              5
④ 退役注记        ``^> \\*\\*(RETIRED|已退役)`` 开头的**引用块序列**       45 块
===============  ==================================================  =====

**④「引用块序列」的定义**：从 `> **RETIRED|已退役` 行起，**连续**的 `>` 行与
`<!-- v4-residue:allow=… -->` 标注行属于**同一注记单元** ⇒ 整段剥除；**空行中断**
（隔空的独立说明性引用块**保留** —— 它们可能是正常内容，不是注记）。

⚠️ ④ 必须**整段**剥除 —— 只去首行会**低估**注入贡献（2026-11-21 第一版还原法只识别 ①②③，
测出「仅 +7」；补上 ④ 才是真实的 +25）。

⚠️ **不属注入、不得去掉**：
- ``- **THEN** （已退役）…`` / ``- **AND** （已退役）…``（6 处）—— 这些是**被替换的判据行**
  （原文已改写成退役提示），去掉会**丢原文**；两版都保留 ⇒ 对差值无影响。
- 批 6 的**改指**（换 token）—— 两版都带改指后的 token ⇒ 对差值无影响。
- 隔空的独立说明性引用块（如 ``> 保留原文与 Scenario 作为历史记录。`` 独立出现时）。

## ⚠️ 归因漂移边界（读断言消息前必看）

若新增的 `very long` 来自**第 5 类形态**（不被 `_strip_injected` 识别的新注记形态），
断言 **B 不会红**（该增量会被算进 baseline 侧）⇒ 只更新 `FROZEN_VERY_LONG` 就能转绿，
而 `FROZEN_INJECTED_VL` 永远不用动 ⇒ **注入 / 存量的归因静默腐化**。

⇒ **规则**：断言 A 红且增量疑似来自新注记形态时，**必须同步扩展 `_strip_injected` 的规则**，
**不得只改冻结值**。（这正是 2026-11-21 台账 §2 教训的复发路径。）

## skip-not-fail

openspec CLI 不可用、或 `openspec/specs/` 不存在（如 CI 的 fresh checkout）时**跳过**
（仓库既有先例：`tests/unit/test_cross_repo_schemas.py`）。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPECS_DIR = REPO_ROOT / "openspec" / "specs"

#: 当前 `openspec/specs/` 的 `very long` 清单（spec id → `requirements[N]` 路径）。
FROZEN_VERY_LONG: dict[str, list[str]] = {
    'add-plan-done-reflect-hook': ['requirements[0]'],
    'add-skill-layer-resolve-project-root-helper': ['requirements[0]'],
    'agent-interface-contracts': ['requirements[5]'],
    'archive-auto-commit': ['requirements[0]'],
    'archive-gate-verification': ['requirements[3]'],
    'archive-iteration-sync': ['requirements[0]', 'requirements[3]'],
    'c-layer-4-skills': ['requirements[0]'],
    'consolidate-resolve-project-root-helpers': ['requirements[0]'],
    'design-content-review': ['requirements[2]'],
    'design-proposal-creation': ['requirements[0]'],
    'diagnose-changes': ['requirements[1]'],
    'doc-architecture-v4-sync': ['requirements[0]'],
    # 2026-11-22（fix-doc-truth-sync-false-assertions）：退役 `v2-api-ref-path-corrections`
    # 后，后续 Requirement 的**序号整体前移 1**。`very long` 的仍是同两条
    # （doc-contract-tests-required / doc-surfaces-share-truth-source），总数 62 / 38 spec 不变。
    'doc-truth-sync': ['requirements[5]', 'requirements[6]'],
    'external-testbed-coop': ['requirements[0]'],
    'fix-33-handlers-project-root-anti-pattern': ['requirements[0]'],
    'fix-skill-layer-project-root-anti-pattern': ['requirements[0]'],
    'fix-skill-layer-resolution-bash': ['requirements[0]'],
    'inline-ac-verifier-into-rdd-verifier': ['requirements[6]', 'requirements[7]'],
    'iterative-plan-fill': ['requirements[0]', 'requirements[1]', 'requirements[2]',
                            'requirements[3]', 'requirements[4]', 'requirements[5]'],
    'mcp-trace': ['requirements[4]'],
    'openspec-version-degradation': ['requirements[0]'],
    'plan-intake-bootstrap': ['requirements[1]'],
    'post-archive-cleanup-hook': ['requirements[0]', 'requirements[1]', 'requirements[3]',
                                  'requirements[4]', 'requirements[5]'],
    'project-setup-check': ['requirements[8]'],
    'proposal-lifecycle-sync': ['requirements[0]', 'requirements[1]', 'requirements[2]',
                                'requirements[3]'],
    'rdd-hub-bootstrap': ['requirements[2]'],
    'roadmap-feature-fragment': ['requirements[3]'],
    'roadmap-incremental': ['requirements[0]'],
    'roadmap-proposal-guidance': ['requirements[3]', 'requirements[4]'],
    'ship-done-orphan-cleanup': ['requirements[2]', 'requirements[4]'],
    'skeleton-planning': ['requirements[2]'],
    'skill-role-model': ['requirements[1]'],
    'spec-validation-gates': ['requirements[4]'],
    'three-phase-skills': ['requirements[0]', 'requirements[1]'],
    'verifier-lifecycle': ['requirements[1]'],
    'verifier-v2-hardening': ['requirements[9]'],
    'workflow-design-phase': ['requirements[0]', 'requirements[1]', 'requirements[2]',
                               'requirements[3]', 'requirements[4]', 'requirements[6]'],
    'worktree-context-persistence': ['requirements[0]', 'requirements[2]'],
}

#: 上述清单中**由标注 / 注记注入造成**的部分（25 条 / 13 spec）。
#: 其余 37 条是**存量固有**（注入前就 very long），与残留处置工作无关。
FROZEN_INJECTED_VL: dict[str, list[str]] = {
    'archive-gate-verification': ['requirements[3]'],
    'inline-ac-verifier-into-rdd-verifier': ['requirements[6]', 'requirements[7]'],
    'iterative-plan-fill': ['requirements[1]', 'requirements[2]', 'requirements[3]',
                            'requirements[4]', 'requirements[5]'],
    'openspec-version-degradation': ['requirements[0]'],
    'plan-intake-bootstrap': ['requirements[1]'],
    'project-setup-check': ['requirements[8]'],
    'roadmap-feature-fragment': ['requirements[3]'],
    'roadmap-incremental': ['requirements[0]'],
    'roadmap-proposal-guidance': ['requirements[3]', 'requirements[4]'],
    'ship-done-orphan-cleanup': ['requirements[2]', 'requirements[4]'],
    'three-phase-skills': ['requirements[0]'],
    'workflow-design-phase': ['requirements[0]', 'requirements[2]', 'requirements[3]',
                               'requirements[4]', 'requirements[6]'],
    'worktree-context-persistence': ['requirements[0]', 'requirements[2]'],
}

FROZEN_TOTAL = 62
FROZEN_INJECTED_TOTAL = 25

_ANNOT_RE = re.compile(r"^<!-- v4-residue:allow=[a-z-]+ -->\s*$")
_NOTE5_RE = re.compile(r"^- \*\*NOTE\*\* \(retired ")
_NOTE7_RE = re.compile(r"^> \*\*已退役（\d{4}-\d{2}-\d{2}）")
_QUOTE_HEAD_RE = re.compile(r"^> \*\*(RETIRED|已退役)")


def _strip_injected(lines: list[str]) -> list[str]:
    """去掉 4 类注入内容（见模块 docstring 的规则表）。

    ④「引用块序列」：从 ``> **RETIRED|已退役`` 起，连续的 ``>`` 行与标注行属同一注记单元 ⇒
    整段剥除；**空行中断**。
    """
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if _ANNOT_RE.match(line) or _NOTE5_RE.match(line) or _NOTE7_RE.match(line):
            i += 1
            continue
        if _QUOTE_HEAD_RE.match(line):
            i += 1
            while i < n and (lines[i].startswith(">") or _ANNOT_RE.match(lines[i])):
                i += 1
            continue
        out.append(line)
        i += 1
    return out


def _very_long_for(specs_dir: Path) -> dict[str, list[str]]:
    """把 ``specs_dir`` 拷进临时项目，跑 ``openspec validate --all --json``。

    返回 ``{spec id: [requirements[N], ...]}`` —— 只取 ``type == "spec"`` 的 item，
    ⇒ **不受活跃 change 的 delta 影响**（否则每批 change 存续期间清单都会漂移）。
    """
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "openspec" / "specs"
        dst.parent.mkdir(parents=True)
        shutil.copytree(specs_dir, dst)
        proc = subprocess.run(
            ["openspec", "validate", "--all", "--json"],
            capture_output=True, text=True, cwd=td,
        )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:  # pragma: no cover - 只在 CLI 行为异常时触发
            pytest.fail(
                "openspec validate --all --json 的 stdout 不是 JSON\n"
                f"stdout: {proc.stdout[:500]}\nstderr: {proc.stderr[:500]}"
            )
    found: dict[str, list[str]] = defaultdict(list)
    for item in payload.get("items", []):
        if item.get("type") != "spec":
            continue
        for issue in item.get("issues", []):
            if "very long" in issue.get("message", ""):
                found[item["id"]].append(issue["path"])
    return {k: sorted(v) for k, v in sorted(found.items())}


def _current_very_long() -> dict[str, list[str]]:
    """当前仓库的 very long 清单。"""
    if shutil.which("openspec") is None:
        pytest.skip("openspec CLI 不可用（skip-not-fail）")
    if not SPECS_DIR.is_dir():
        pytest.skip("openspec/specs/ 不存在（CI 的 fresh checkout：本仓 openspec/ 被 gitignore）")
    return _very_long_for(SPECS_DIR)


def _noinject_dir(root: Path) -> Path:
    """造一份「去掉全部注入内容」的 `openspec/specs/` 副本。

    ``root`` 由 pytest 的 ``tmp_path`` fixture 提供 ⇒ 自动清理（隔离门要求）。
    """
    tmp = root / "noinject"
    tmp.mkdir(parents=True, exist_ok=True)
    for spec_dir in sorted(SPECS_DIR.iterdir()):
        src = spec_dir / "spec.md"
        if not src.is_file():
            continue
        lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
        dst = tmp / spec_dir.name
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "spec.md").write_text(
            "\n".join(_strip_injected(lines)) + "\n", encoding="utf-8"
        )
    return tmp


def test_very_long_issue_set_is_frozen():
    """断言 A：`very long` 的 (spec, path) 多重集必须与冻结清单一致。

    变化时 pytest 会打印 diff —— 新增/消失/换位都能一眼看出。
    ⚠️ 只比 issue，**不比** `durationMs`（每次都变）。
    ⚠️ 若新增项疑似来自**新的注记形态**，必须同步扩展 `_strip_injected` 的规则，
    **不得只改冻结值**（否则断言 B 的注入/存量归因会静默腐化）。
    """
    actual = _current_very_long()
    total = sum(len(v) for v in actual.values())
    assert total == FROZEN_TOTAL, (
        f"very long 总数变了：期望 {FROZEN_TOTAL}，实际 {total}\n"
        f"实际清单：{actual}\n"
        "⚠️ 若新增项疑似来自新的注记形态（不被 _strip_injected 识别），"
        "必须同步扩展 _strip_injected 的规则，不得只改冻结值。"
    )
    assert actual == FROZEN_VERY_LONG, (
        "very long 清单与冻结值不一致 —— 若新增的是本批注记造成的，"
        "请在同一提交里更新 FROZEN_VERY_LONG 并说明「新增的 very long 是否可接受」"
    )


def test_injected_very_long_increment_is_frozen(tmp_path: Path):
    """断言 B：**注入造成的** very long 增量必须与冻结清单一致。

    这条直接补上原判据的缺口 —— 原来只比文本输出，看不到 `requirements[N]`。
    """
    actual = _current_very_long()
    baseline = _very_long_for(_noinject_dir(tmp_path))

    injected: dict[str, list[str]] = {}
    for spec, paths in actual.items():
        extra = sorted(set(paths) - set(baseline.get(spec, [])))
        if extra:
            injected[spec] = extra

    total = sum(len(v) for v in injected.values())
    assert total == FROZEN_INJECTED_TOTAL, (
        f"注入造成的 very long 增量变了：期望 {FROZEN_INJECTED_TOTAL}，实际 {total}\n"
        f"实际增量：{injected}\n"
        "⚠️ 若增量下降，说明 _strip_injected 的规则与实际注入形态脱节 —— "
        "请检查规则表是否仍覆盖全部形态。"
    )
    assert injected == FROZEN_INJECTED_VL, (
        "注入造成的 very long 增量与冻结值不一致 —— 新增说明本批的注记"
        "把某个 Requirement 推过了 500（advisory，非 ERROR）。"
        "请在同一提交里更新 FROZEN_INJECTED_VL 并说明「新增的 very long 是否可接受」"
    )
