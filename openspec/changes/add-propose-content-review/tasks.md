## 1. Create propose_content_review.py
- [ ] 1.1 实现 4 项 Oracle 检查：scope 清晰度 / ADR 引用相关性 / 验收标准可测性 / 范围边界合理性
- [ ] 1.2 单次 Oracle 调用结构化输出（warning 级别，非阻断性）
- [ ] 1.3 写入 `.rddf/state/propose-review.json`（含 4 维度评分 + 总评 + 建议）
- [ ] 1.4 环境变量 `SKIP_CONTENT_REVIEW=yes` 跳过逻辑

## 2. Wire into Propose Phase & Tests
- [ ] 2.1 `propose.md` Phase 4 末尾可选调用 `propose_content_review.py`
- [ ] 2.2 unit test 覆盖正常/跳过/错误场景
- [ ] 2.3 验证所有现有测试通过