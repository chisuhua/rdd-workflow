# adr-index-auto-sync

**优先级**: P2 | **来源**: 2026-08-26 文档与代码一致性审计
**阶段**: default | **分类**: governance
**类型**: improvement
**状态**: 已推迟

## 架构依据

`docs/adr/README.md` 是 ADR 索引文件。当前实现是**手写维护**——每次新增 ADR 都要手动更新该 README 的 ADR 列表与实施状态表。审计发现 3 类过期：

1. **line 148 关键 ADR 列表**（在 AGENTS.md）：漏 ADR-0025 / ADR-0027 / ADR-0029 / ADR-0031 / ADR-0034
2. **`docs/adr/README.md` ADR 表格**：当前手写 35 个 ADR 条目，新增 ADR 需手动添加
3. **`.rddf/improvements/*.md` 与 ADR 的交叉引用**：当前是 OpenSpec 扫描器推断，缺 ADR 时扫描器会 silent skip

新增 ADR 的开发者常忘记更新索引，造成"索引过期但 ADR 在磁盘上"的状态——这是**架构知识衰减**的典型问题。

## 范围

**In Scope**:
- 新建 `_lib/adr_index_generator.py`：扫描 `docs/adr/ADR-*.md`，提取 frontmatter（status, date, decider），自动生成 Markdown 表格
- `docs/adr/README.md` 表格改为生成产物（保留手写头注释 + 自动表格）
- pre-commit hook 集成：新增/重命名 ADR 时自动重生成 README.md
- CI 守护：`tests/integration/test_adr_index.bats` 强制验证 README 表格 == 磁盘 ADR 列表
- AGENTS.md line 148 关键 ADR 列表也接入（限定"已采纳"+"已实施"，过滤掉 待定/弃用）

**Out of Scope**:
- 修改 ADR 命名规范（`ADR-NNNN-<slug>.md`）
- 修改 ADR frontmatter schema
- 跨项目 ADR 同步（ADR-0027 L2 上报通道已存在但语义不同）

## 设计

### `_lib/adr_index_generator.py` 接口

```python
"""ADR 索引自动生成器：扫描 docs/adr/ADR-*.md frontmatter，输出 Markdown 表格."""
from pathlib import Path
import re
import frontmatter  # PyYAML extension


def parse_adr_metadata(path: Path) -> dict:
    """提取 ADR frontmatter: status / date / decider / superseded_by."""
    fm = frontmatter.load(path)
    return {
        "id": path.stem.split("-")[1],  # "0034"
        "title": fm.get("title", path.stem),
        "status": fm.get("status", "未知"),
        "date": fm.get("date", ""),
        "decider": fm.get("decider", ""),
        "superseded_by": fm.get("superseded_by", ""),
    }


def generate_table(adr_dir: Path) -> str:
    """生成 Markdown 表格 (sorted by id desc)."""
    adrs = sorted(
        [parse_adr_metadata(p) for p in adr_dir.glob("ADR-*.md") if p.stem != "ADR-0000-template"],
        key=lambda x: x["id"],
        reverse=True,
    )
    
    rows = [
        "| ADR | 标题 | 状态 | 日期 | 决策者 |",
        "|-----|------|------|------|--------|",
    ]
    for a in adrs:
        rows.append(
            f"| [{a['id']}](ADR-{a['id']}-*.md) | {a['title']} | {a['status']} | {a['date']} | {a['decider']} |"
        )
    return "\n".join(rows)


def regenerate_readme(adr_dir: Path, readme_path: Path) -> None:
    """重写 docs/adr/README.md 表格段（保留头部注释 + footer）."""
    text = readme_path.read_text()
    
    # 标记段: <!-- ADR_INDEX_START --> ... <!-- ADR_INDEX_END -->
    pattern = re.compile(
        r"<!-- ADR_INDEX_START -->.*?<!-- ADR_INDEX_END -->",
        re.DOTALL,
    )
    
    table = generate_table(adr_dir)
    new_section = f"<!-- ADR_INDEX_START -->\n{table}\n<!-- ADR_INDEX_END -->"
    
    if pattern.search(text):
        new_text = pattern.sub(new_section, text)
    else:
        # 首次生成：插入到 "## ADR 列表" 段后
        new_text = text + "\n\n" + new_section
    
    readme_path.write_text(new_text)
```

### 标记占位符

在 `docs/adr/README.md` 中插入：

```markdown
## ADR 列表（自动生成，请勿手动编辑）

<!-- ADR_INDEX_START -->
<!-- ADR_INDEX_END -->
```

### CLI 集成

```bash
# 手动重生成
python3 _lib/adr_index_generator.py

# CI 验证（test_adr_index.bats 增强）
# 检测 README.md 表格 == 磁盘 ADR 列表
```

### AGENTS.md line 148 同步

把 line 148 改为：

```markdown
关键 ADR: 见 `docs/adr/README.md` 自动生成索引（grep "已采纳" filter）
```

或保持手写但加注释"自动同步任务 adr-index-auto-sync 待实施"。

## 影响

- **正向**：新增 ADR 只需写文件，README 索引自动更新
- **正向**：CI 强制验证杜绝"索引过期"
- **正向**：AGENTS.md line 148 改为指向 README，不再独立维护
- **风险**：手写头注释（如"v2.0.9+ ADR 实施状态"）需保留不被覆盖——已用 HTML 注释 `<!-- ADR_INDEX_START -->` 包裹
- **兼容性**：纯自动化，无破坏

## 验收

- [ ] `_lib/adr_index_generator.py` 实现 3 个 public 函数
- [ ] `docs/adr/README.md` 含 `<!-- ADR_INDEX_START --> ... <!-- ADR_INDEX_END -->` 段
- [ ] 运行 `python3 _lib/adr_index_generator.py` 后，README 表格 == 磁盘 35 个 ADR
- [ ] 新增 ADR-0035 后，再次运行 README 自动包含 0035
- [ ] `tests/integration/test_adr_index.bats` 强制表格 == 磁盘
- [ ] `tests/unit/test_adr_index_generator.py` 3+ 个 unit test PASS
- [ ] AGENTS.md line 148 注释为"自动同步"或保持手写但加引用
- [ ] pre-commit hook（可选）：新增/重命名 ADR 时自动重生成 README（follow-up）

## 后续 (follow-up)

- pre-commit hook 接入
- 跨项目 ADR 索引同步（ADR-0027 L2 上报 + Hub 聚合）
- ADR 状态机自动更新（已采纳 → 已替代为 ADR-NNNN）