# fix-append-approved-output

**优先级**: P2 | **来源**: 会话复盘 2026-07-23 — approve_proposal.sh 双重 echo
**阶段**: v2.1 | **分类**: core
**类型**: feature

## 架构依据

- `state.sh::append_approved` 函数内部 `echo "✅ $name added to approved list"`
- 外部调用循环也有 `echo "  ✅ $name"`
- 导致每次批准都输出两行重复信息

## 范围

- **In Scope**:
  - 移除 `append_approved` 内部的成功 echo（函数应返回状态码，由调用方决定输出格式）
  - 或者：将内部 echo 改为 `>&2` 输出到 stderr，保持调用方输出干净
- **Out Scope**:
  - 不修改 `list_approved` / `list_improvements` 等其他函数

## 关键场景

- GIVEN 批量批准 10 个提案, WHEN 调用 append_approved, THEN 每个提案只输出一行
- GIVEN append_approved 静默模式, WHEN 调用方不想显示输出, THEN 可重定向

## 技术约束

- MUST 保持函数返回值语义不变（0=成功，1=失败）
- SHOULD 将日志信息输出到 stderr 或移除

## 验收标准

- 批量批准时每个提案只占一行输出
- 函数调用方可自行控制输出格式
