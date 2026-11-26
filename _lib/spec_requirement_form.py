"""spec / delta 的**形态判据单一真源** —— 守卫与生成器共用。

背景（2026-11-26，CppTLM 立项会话实测）：`generate_full_proposal.generate_spec_delta()`
仍在产出**被仓库形态守卫拒绝**的形态 ——

1. 无语义的 Requirement 名（`### Requirement: acceptance-3` / `capability-3`）；
2. 恒真的 Scenario WHEN（`- **WHEN** the change is applied`）。

`tests/unit/test_spec_requirement_form.py` 早已把这两类判为退化并拒绝，但**生成器与守卫各写一份**
⇒ 守卫改 A、生成器仍按 B 判 ⇒ 退化形态持续流入归档期（每次归档手工重写）。

⇒ 本模块把判据**上移**为可被两侧共同 import 的地方：
- 本仓内：`from _lib.spec_requirement_form import ...`；
- 生成器（`skills/rdd-builder/scripts/generate_full_proposal.py`）在**产出前**自检，
  命中即**拒绝生成**（exit ≠ 0）⇒ 退化形态不再落盘。

⚠ **纯 stdlib**：生成器有「无第三方依赖」的硬约束 ⇒ 本模块不得引入任何第三方依赖。
"""
from __future__ import annotations

import re

#: 判据 ① —— 无语义的 Requirement 名（AC 序号）。
MEANINGLESS_REQUIREMENT = re.compile(r"^### Requirement: acceptance-\d+\s*$", re.MULTILINE)

#: 判据 ① 的**全仓版** —— `acceptance-N` 与 `capability-N` 是同一形态退化族的两种命名
#: （自动生成的序号名 + 恒真 WHEN + `is enforced` 结尾）。
#:
#: 见 `.rddf/reviews/rewrite-acceptance-form-batch-4-2026-11-23.md` 的教训 ⑦：
#: 「**按「形态类」计数，不要按「文件名模式」计数**」—— 只治理 `acceptance-N`
#: 会整类漏掉 `capability-N`（第 4 批实漏 7 条，直到收口前自查才发现）。
DEGRADED_REQUIREMENT_NAME = re.compile(
    r"^### Requirement: (?:acceptance|capability)-\d+\s*$", re.MULTILINE
)

#: 判据 ② —— 恒真的 Scenario WHEN（对任何 change / feature 都成立）。
TAUTOLOGICAL_WHEN = re.compile(
    r"^- \*\*WHEN\*\* the (?:change|feature|it) is applied\s*$", re.MULTILINE
)

#: 判据 ③ —— 以 `is enforced` 结尾的 THEN（退化族的第三种表现）。
ENFORCED_TAIL = re.compile(r"\bis enforced\s*$", re.MULTILINE)


def find_degraded_requirements(text: str) -> list[str]:
    """返回命中的退化 Requirement 名（去重、保序）。

    >>> find_degraded_requirements("### Requirement: acceptance-1\\n")
    ['acceptance-1']
    """
    names: list[str] = []
    for m in DEGRADED_REQUIREMENT_NAME.finditer(text):
        name = m.group(0).split(":", 1)[1].strip()
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
    """文本是否含退化形态（生成时的**拒绝入口**）。"""
    return bool(find_degraded_requirements(text) or find_tautological_whens(text))


def describe_degradation(text: str) -> list[str]:
    """人类可读的退化清单（用于 stderr 诊断 ⇒ 生成器拒绝时指名缺什么）。"""
    out = [f"退化 Requirement 名: {name}" for name in find_degraded_requirements(text)]
    out += [f"恒真 WHEN: {line}" for line in find_tautological_whens(text)]
    return out
