# docs/legacy — 考古保留

本目录保存**已退役**的实现与文档，仅作历史参考。

## 约束

- **不参与安装**：`install.sh` 只遍历 `skills/*/`，本目录下的内容不会被 symlink 到 `~/.agents/skills/`。
- **不参与类型检查**：`pyrightconfig.json` 的 `include` 只含 `skills` / `_lib` / `tests`，本目录不会被扫。
- **不参与测试**：`tests/` 不引用本目录。

## 内容

| 路径 | 退役日期 | 依据 |
|---|---|---|
| `rddf-legacy-v2.0.7.sh` | v2.0.7 | Python `rddf` CLI 替代 |
| `skills/guide/` | 2026-11-19 | ADR-0063（退役 Guide-as-Orchestrator） |
| `guide-orchestrator-flow.md` | 2026-11-19 | ADR-0063 |
