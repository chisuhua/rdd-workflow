"""范围节解析 —— 纯表格 / 混排 / header 注解 / 表内逗号 / Out 段只出现一次（AC1、AC2、AC6）。

背景（2026-11-26，CppTLM `cep-ssp-cp-q1b-landing` 立项会话实测）：improvement 用**表格**写
In Scope ⇒ 解析不出条目 ⇒ 落进逗号兜底 ⇒ 表格第 2 行的 `x.hh:43-53,56,79-89,106-113`
被切成 4 个条目、`**In Scope（6 项）**` 整行成为条目、**Out of Scope 整段重复两遍**。
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_SCRIPT = _ROOT / "skills" / "rdd-builder" / "scripts" / "generate_full_proposal.py"
_spec = importlib.util.spec_from_file_location("gen_fp_scope_table", _SCRIPT)
gen_fp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_fp)


def _scope(body: str) -> str:
    return f"## 范围\n\n{body}\n"


def test_table_only_section_yields_one_item_per_row() -> None:
    md = _scope(
        """**In Scope（3 项）**

| # | 改动 | 落点 |
|:--:|---|---|
| 1 | `a` | `x.hh` |
| 2 | `b` | `y.hh` |
| 3 | `c` | `z.hh` |

**Out of Scope**

- 不做 `d`
"""
    )
    in_items, out_items = gen_fp._extract_scope_items(md)
    assert len(in_items) == 3, in_items
    assert all("|" not in i for i in in_items), in_items
    assert all("\n" not in i for i in in_items), in_items
    assert out_items == ["不做 `d`"], out_items


def test_annotated_header_is_recognized_as_header() -> None:
    """带括号注解的 header 必须被**识别为标题**（否则其后的条目无处归属）。"""
    md = _scope(
        """**In Scope（6 项 · contract 面）**

- 一项

**Out of Scope**

- 二项
"""
    )
    in_items, out_items = gen_fp._extract_scope_items(md)
    assert in_items == ["一项"], in_items
    assert out_items == ["二项"], out_items

    # 注解 header 之后的条目必须归 in-scope（不是「被丢弃」）
    md2 = _scope(
        """**In Scope（6 项 · contract 面）**

| # | 改动 | 落点 |
|:--:|---|---|
| 1 | `a` | `x.hh` |

**Out of Scope**

- 二项
"""
    )
    in2, out2 = gen_fp._extract_scope_items(md2)
    assert len(in2) == 1, in2
    assert out2 == ["二项"], out2


def test_table_under_bullet_stays_attached() -> None:
    md = _scope(
        """**In Scope**

- 父项

  | 列 | 值 |
  |---|---|
  | a | b |

**Out of Scope**

- 不做
"""
    )
    in_items, _ = gen_fp._extract_scope_items(md)
    assert len(in_items) == 1, in_items
    assert "父项" in in_items[0]
    assert "| 列 | 值 |" in in_items[0]


def test_out_scope_appears_once() -> None:
    md = _scope(
        """**In Scope**

- 一项

**Out of Scope**

- 不做 `d`
"""
    )
    _, out_items = gen_fp._extract_scope_items(md)
    assert out_items == ["不做 `d`"], out_items


def test_table_cell_with_comma_is_not_split() -> None:
    md = _scope(
        """**In Scope**

| # | 改动 | 落点 |
|:--:|---|---|
| 1 | `family` enum 加 `user-defined`；`pattern` 改**两分支** | `a.hh:43-53,56,79-89` |

**Out of Scope**

- 不做
"""
    )
    in_items, _ = gen_fp._extract_scope_items(md)
    assert len(in_items) == 1, in_items
    assert "43-53,56,79-89" in in_items[0], in_items


def test_unparseable_scope_is_preserved_verbatim(capsys) -> None:
    """AC2：解析不出条目 ⇒ **保留原文** + stderr 提示，**不**按逗号切碎。"""
    md = _scope(
        """本节只有散文说明：改动 a、改动 b、改动 c，全部落在同一个文件里。

**Out of Scope**

- 不做 `d`
"""
    )
    out = gen_fp.generate_full_proposal("probe", md)
    err = capsys.readouterr().err
    # 原文必须**逐字**保留（未被逗号切成三条）
    assert "改动 a、改动 b、改动 c" in out, out
    assert "保留原文" in err, err
    # 不得出现逗号切出的碎片
    assert "- 改动 a\n" not in out, out


def test_both_sections_present_prefers_range(capsys) -> None:
    """AC6：`## 范围` 与 `## What Changes` 并存 ⇒ 取候选序靠前者 + 歧义提示。"""
    md = """## 范围

**In Scope**

- 中文项

## What Changes

- 英文项
"""
    out = gen_fp.generate_full_proposal("probe", md)
    err = capsys.readouterr().err
    assert "中文项" in out, out
    assert "英文项" not in out, out
    assert "歧义" in err, err


def test_only_english_section_present_is_used(capsys) -> None:
    """AC6（另一半）：只有 `## What Changes` ⇒ 取它，不报错。"""
    md = """## What Changes

- 英文项
"""
    out = gen_fp.generate_full_proposal("probe", md)
    assert "英文项" in out, out
    assert "歧义" not in capsys.readouterr().err
