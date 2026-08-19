## Context

`add-rfc-draft-template` 是 P0 #1 的"输出端补强"。检测到跨仓后，需要把 5 段结构（动机/契约草案/利益相关方/兼容策略/回滚）落到 `.rddf/improvements/<name>.md`，并支持把契约草案 base64 内联到 Hub Issue。

## Goals / Non-Goals

**Goals**:

- 5 段模板自动插入（基于 P0 #1 检测结果）
- `report_issue_rfc.py --contract-draft <path>` 支持契约草案内联
- 模板字段自动填充（stakeholders 来自检测结果）
- 单元测试覆盖：模板生成 + body 内联

**Non-Goals**:

- 模板内容的人工编辑（用户自行修改）
- Hub Issue template（GitHub 端配置）

## Technical Decisions

### TD-1: 5 段模板格式

```markdown
## 变更动机
[自动生成: 检测到的 Hub 契约]

## 契约草案
[自动生成: 引用 contracts/<name>.yaml]

## 影响仓库
[自动填充: stakeholders 检测列表]

## 兼容策略
[占位: 由人类填写]

## 回滚方案
[占位: 由人类填写]
```

### TD-2: Hub Issue body base64 内联

- `--contract-draft <path>` 参数读取本地契约文件
- base64 编码到 Issue body `<details>` 块
- 优势: Hub Issue 自带契约，Stakeholder 不必再 sync

## Implementation Notes

- 模板插入位置：`.rddf/improvements/<name>.md` 末尾（保留 head 字段 + 自定义正文）
- base64 长度限制：Hub Issue body < 65536 chars（约 48 KB base64）

## References

- ADR-0032 §阶段 A
- 依赖 P0 #1 `add-cross-repo-impact-detection`
