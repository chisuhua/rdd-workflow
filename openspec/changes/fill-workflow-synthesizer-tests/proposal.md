## P1: ## 架构依据
- test_workflow_synthesizer.py 797 行但零测试函数
- workflow_synthesizer.py 784...

## 架构依据
- test_workflow_synthesizer.py 797 行但零测试函数
- workflow_synthesizer.py 784 行是 guide 推荐器的核心决策逻辑
- 决定 resume/restart/start-arch/all-done 等关键推荐路径
- 无测试覆盖意味着推荐器行为不可验证

## 范围
- **In Scope**:
  - 为 WorkflowRecommendation 决策树添加测试（resume/restart/start-arch/all-done）
  - 测试 sessions.json 缺失/存在/过期状态的处理
  - 测试 handoff 优先级逻辑
  - 测试 git 状态检测
- **Out Scope**:
  - 不修改 workflow_synthesizer.py 源码
  - 不依赖真实 git history（使用 tmp_path + git init）

## 关键场景
- GIVEN sessions.json 含 active session, WHEN synthesize(), THEN 推荐 resume
- GIVEN sessions.json 不存在或全部 abandoned, WHEN synthesize(), THEN 推荐 restart

## 技术约束
- MUST 使用 pytest + tmp_path fixture
- MUST 保持只读（不写入 sessions.json）
- SHOULD 覆盖 5 条推荐路径

## 验收标准
- 至少 10 个测试函数
- 所有测试通过
- 不修改现有 workflow_synthesizer 源码