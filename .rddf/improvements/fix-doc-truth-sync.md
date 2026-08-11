# fix-doc-truth-sync

**优先级**: P2 | **来源**: 会话深度分析 2026-07-23 #3
**阶段**: default | **分类**: infra-setup
**类型**: feature

## 架构依据
- doc_truth_sync 测试（#214/215/218）检查 package.json ↔ skill 文件 ↔ AGENTS.md 一致性
- 根因：package.json 用 rdd-workflow-writing-plans，但 skill 的 frontmatter name 是 rdd-workflow/writing-plans
- 影响：3 个 bats 测试失败

## 范围
- **In Scope**:
  - 统一命名：选 rdd-workflow-writing-plans（目录名）或 rdd-workflow/writing-plans（frontmatter）
  - 更新 package.json 的 skills[] 数组
  - 更新 AGENTS.md 中的 skill 引用
  - 验证 3 个 doc_truth_sync 测试通过
- **Out Scope**:
  - 不改动其他目录或文件
  - 不修改 skill 功能逻辑

## 关键场景
- GIVEN package.json skills[] 与实际 skill 文件一致, WHEN 运行 doc_truth_sync 测试, THEN 全部通过

## 技术约束
- MUST 保持 backward compatibility（现有 skill_use 调用不受影响）

## 验收标准
- 3 个 doc_truth_sync 测试通过
- 所有现有 bats 测试通过
