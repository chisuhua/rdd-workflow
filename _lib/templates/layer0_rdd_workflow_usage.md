<!-- RDD-WORKFLOW-CORE-USAGE-START -->
<!-- Layer 0 协议块: rdd-workflow 核心用法声明 --
     此块由 `rddf setup ai-context` 管理。 -->

本项目已安装 **rdd-workflow**（OpenSpec 工作流技能包），用于管理系统化的变更生命周期。

**推荐入口**：告诉我"使用 guide 流程"或直接调用 `skill_use("guide")` 获得当前状态推荐。

**核心流程**（4 阶段架构）：
1. `skill_use("rdd-arch")` — 架构定义（ADR + roadmap）
2. `skill_use("rdd-planner")` — 提案治理（review → approve）
3. `skill_use("rdd-builder")` — 变更执行（plan → execute → archive）
4. `skill_use("rdd-verifier")` — AC 验证

**旁路规则**：如果变更 ≤2 个文件、≤3 个任务且无公开 API 变更，可以直接 `skill_use("rdd-quick")` 快速执行。

**自助诊断**：运行 `rddf doctor --category ai-context-bootstrap` 检查本配置块状态。
<!-- RDD-WORKFLOW-CORE-USAGE-END -->