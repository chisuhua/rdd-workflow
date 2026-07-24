# Tasks: fix-append-approved-output

## Implementation Steps

- [ ] 移除 `skills/_lib/state.sh` 中 `append_approved` 函数的内部 echo
  - 删除 `echo "✅ $name added to approved list"` 行
  - 函数仅负责状态变更 + 返回码
- [ ] 验证返回值语义不变
  - 0=成功，1=失败
  - 调用方依赖返回码而非输出文本
- [ ] 验证调用方输出不受影响
  - 外部调用循环的 `echo "  ✅ $name"` 保持不变
  - 批量批准时每个提案只占一行

## Verification (验收标准)

- [ ] 批量批准时每个提案只占一行输出
- [ ] 函数调用方可自行控制输出格式

## Key Scenarios (关键场景)

- [ ] GIVEN 批量批准 10 个提案, WHEN 调用 append_approved, THEN 每个提案只输出一行
- [ ] GIVEN append_approved 静默模式, WHEN 调用方不想显示输出, THEN 可重定向
