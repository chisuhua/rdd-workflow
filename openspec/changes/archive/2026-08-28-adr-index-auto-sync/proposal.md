# adr-index-auto-sync

## Why

`docs/adr/README.md` 是 ADR 索引文件。当前实现是**手写维护**——每次新增 ADR 都要手动更新该 README 的 ADR 列表与实施状态表。审计发现 3 类过期：

1. **line 148 关键 ADR 列表**（在 AGENTS.md）：漏 ADR-0025 / ADR-0027 / ADR-0029 / ADR-0031 / ADR-0034
2. **`docs/adr/README.md` ADR 表格**：当前手写 35 个 ADR 条目，新增 ADR 需手动添加
3. **`.rddf/improvements/*.md` 与 ADR 的交叉引用**：当前是 OpenSpec 扫描器推断，缺 ADR 时扫描器会 silent skip

新增 ADR 的开发者常忘记更新索引，造成"索引过期但 ADR 在磁盘上"的状态——这是**架构知识衰减**的典型问题。

## What Changes

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

## Capabilities

- (no items specified)

## Impact

- (no items specified)

## Acceptance

- [ ] `_lib/adr_index_generator.py` 实现 3 个 public 函数
- [ ] `docs/adr/README.md` 含 `<!-- ADR_INDEX_START --> ... <!-- ADR_INDEX_END -->` 段
- [ ] 运行 `python3 _lib/adr_index_generator.py` 后，README 表格 == 磁盘 35 个 ADR
- [ ] 新增 ADR-0035 后，再次运行 README 自动包含 0035
- [ ] `tests/integration/test_adr_index.bats` 强制表格 == 磁盘
- [ ] `tests/unit/test_adr_index_generator.py` 3+ 个 unit test PASS
- [ ] AGENTS.md line 148 注释为"自动同步"或保持手写但加引用
- [ ] pre-commit hook（可选）：新增/重命名 ADR 时自动重生成 README（follow-up）

