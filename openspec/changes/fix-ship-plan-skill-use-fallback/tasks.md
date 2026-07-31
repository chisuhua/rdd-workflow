## 1. 降级检测

- [ ] 1.1 在 `ship_plan.sh::generate_implementation_plan()` 中用 `command -v skill_use >/dev/null 2>&1` 检测环境能力（而非依赖调用失败）
- [ ] 1.2 无 `skill_use` 时输出明确指引："计划文件缺失，需编排者按 rdd-workflow-writing-plans 规范生成 .rddf/plans/<name>.md"，而非"技能未找到"错误
- [ ] 1.3 降级时不返回非零退出码（当前 `return 1` 使 run_ship_phase1 失败），返回可辨识状态码

## 2. SKILL.md 说明

- [ ] 2.1 在 `skills/guide-ship/SKILL.md` Phase 1 补充说明：AI 编排环境计划生成由编排者完成
- [ ] 2.2 验证交互式 AI 环境（skill_use 可用）计划生成行为不变

## 3. 测试

- [ ] 3.1 新增 `tests/integration/test_ship_plan_extraction.bats` 降级场景用例：bash 子进程（无 skill_use）调用 run_ship_phase1，断言输出降级指引且退出码 0
- [ ] 3.2 运行 `bats tests/integration/test_ship_plan_extraction.bats` 全部通过（含新增降级用例）
