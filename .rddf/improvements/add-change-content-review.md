# add-change-content-review

**优先级**: P1 | **来源**: add-propose-content-review 讨论 — plan 阶段 change artifact 内容审查缺位
**阶段**: v2.1 | **分类**: quality
**类型**: feature

## 架构依据
- add-propose-content-review 解决的是 improvement 提案审批阶段的内容审查（arch 阶段 human-in-loop）
- 但 change artifact (proposal.md / design.md / tasks.md) 生成后同样缺乏内容审查 — `propose_quality_check.py` 只做 5 项结构检查（长度/ADR 引用/scope 章节/任务数/roadmap 对齐），不做内容质量判断
- ADR-0003 三阶段架构: 此审查发生在 plan 阶段 plan-done gate 前，是 plan → ship 衔接前的最后质量门
- 与改进提案审批不同，change artifact 的内容审查不需要人工介入：生成者是 AI（propose 技能），审查者也可以是 AI（Metis），发现问题后自动修订
- 仅当 Metis 遇到无法自动决断的重大歧义时才升级到人工
- **设计哲学**: 自动化优先 — Metis 审 + 自动修订，人只处理 AI 无法决断的边缘情况

## 范围
- **In Scope**:
  - 新建 `change_content_review.py`: 调用 Metis agent 做 5 项内容审查，输出结构化结果并自动修订
  - Metis 检查 5 项:
    1. **proposal 清晰度**: Why/What Changes 是否具体可执行（非抽象大词）
    2. **design 完整性**: 架构决策是否说明原因和备选方案（per ADR 模板）
    3. **tasks 粒度**: 每个任务是否原子化（≤3 tool calls 可完成）
    4. **一致性**: proposal/design/tasks 三者之间是否矛盾或遗漏
    5. **依赖标注**: tasks.md 中是否标注了与其他 change 的依赖关系
  - **自动修订**: Metis 发现可修订问题时（如 tasks 粒度太粗、design 缺少备选方案），直接编辑文件修订
  - **升级条件**: 仅当 Metis 发现以下情况时暂停并等待人工决策:
    - proposal 的核心动机（Why）与 ADR 引用的含义矛盾
    - design 的两个备选方案各有不可调和利弊，无法判断推荐哪一个
    - tasks 缺失关键步骤导致整个 change 无法执行
  - **挂载点**: `guide-plan` Phase 4 plan-done gate 前（plan 阶段所有 change artifact 全部生成完毕后、plan-done 双重门控运行前）
  - `SKIP_CHANGE_CONTENT_REVIEW=yes` 完全跳过 Metis 审查
  - `CHANGE_CONTENT_REVIEW_AUTO_REVISE=no` 仅出报告不自动修订（降级为 observation 模式）
  - Metis 审查报告写入 `.rddf/state/change-review-<name>.json`
  - 对应 unit test
- **Out Scope**:
  - 不使用 Oracle（Oracle 是 read-only 顾问，Metis 可以做编辑）
  - 不使用 Tribunal（ADR-0015 约束）
  - 不做 improvement 提案审查（那是 add-propose-content-review 的职责）
  - 不在 guide-ship 阶段再审查（change 应该在 plan 阶段质量就已到位）

## 关键场景
- GIVEN guide-plan Phase 4 所有 change artifact 已生成完毕, WHEN SKIP_CHANGE_CONTENT_REVIEW != yes, WHEN plan-done 双重门控运行前, THEN Metis 检查 5 项，自动修订可修订问题，报告结果
- GIVEN Metis 发现 tasks.md 某任务粒度太粗（估计需要 10+ tool calls）, WHEN 自动修订可行, THEN Metis 将任务拆分为 3 个原子任务并更新 tasks.md
- GIVEN Metis 发现 proposal 的 Why 与引用的 ADR-0015 含义矛盾, WHEN 无法自动判断哪个正确, THEN 暂停输出升级提示，等待人工决定: (1) 修改 proposal (2) 修改 ADR (3) 标记为已知矛盾继续
- GIVEN CHANGE_CONTENT_REVIEW_AUTO_REVISE=no, WHEN Metis 发现问题, THEN 仅输出报告，不编辑文件
- GIVEN 所有 5 项通过或自动修订成功, WHEN 审查完毕, THEN 输出 "✅ 内容审查通过" 并继续 plan-done gate
- GIVEN Metis 调用失败或超时, WHEN 异常发生, THEN 输出 "Metis 审查不可用，跳过" 并继续（非致命）

## 技术约束
- MUST 使用 Metis agent（非 Oracle，因为需要编辑能力做自动修订）
- MUST NOT 阻断默认流程（审查失败不阻止 plan-done）
- MUST 自动修订后运行 `lsp_diagnostics` 确认无语法错误
- MUST 自动修订后保留原始文件的 git 历史（修改而非覆盖重写）
- SHOULD Metis prompt 包含完整的 proposal.md + design.md + tasks.md 全文 + 对应的 ADR 引用内容
- SHOULD 升级条件收紧 — 宁可漏审也不频繁打断自动化流程

## 验收标准
- `change_content_review.py` 含 5 项 Metis 检查 + 自动修订逻辑
- SKIP_CHANGE_CONTENT_REVIEW=yes 跳过
- CHANGE_CONTENT_REVIEW_AUTO_REVISE=no 仅出报告不编辑
- 自动修订后 lsp_diagnostics 通过
- 升级到人工时输出明确的 2-3 选项供选择
- 审查报告写入 .rddf/state/change-review-<name>.json
- 所有现有测试通过