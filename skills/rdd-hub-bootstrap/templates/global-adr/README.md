# Global ADR Directory

本目录存放跨项目生效的全局架构决策(Global ADR)。

## 与本地 ADR 的区别

| 维度 | 本地 ADR (`docs/adr/`) | Global ADR (`global-adr/`) |
|------|------------------------|---------------------------|
| 范围 | 单个 Spoke 仓库 | 跨所有 Spoke 仓库 |
| 起草人 | Spoke 架构师 | Hub 架构师(或 RFC 批准) |
| 修改流程 | Spoke 内 PR | Hub PR + 所有 Spoke ack |

## 文件命名

- `GLOBAL-NNNN-<slug>.md` — 例如 `GLOBAL-0001-mcp-protocol-mandatory.md`
- 编号连续递增

## 模板

参考 [`docs/adr/ADR-0000-template.md`](../../docs/adr/ADR-0000-template.md)
