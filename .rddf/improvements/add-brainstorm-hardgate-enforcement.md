# add-brainstorm-hardgate-enforcement

**优先级**: P1 | **来源**: 2026-08-27 Hybrid path reflection (本次会话中 AI agent 直接创建 9 个 .md proposal 文件 + 修改 proposal-suggestions.md, 绕过了 rdd-workflow-brainstorm SKILL.md 的 HARD-GATE 规则)
**阶段**: phase-2 | **分类**: governance
**类型**: improvement

**主题**: 2026-08-27 Hybrid path reflection (流程改进)

## 架构依据

`skills/rdd-workflow-brainstorm/SKILL.md` 明确规定了 HARD-GATE:

> `<HARD-GATE>` 在用户批准设计之前,不得创建任何文件、写入任何提案、修改 proposal-suggestions.md 或采取任何实施行动。此规则适用于所有提案,无论看起来多么简单。`

但 SKILL.md 只在文档里规定,没有强制执行机制。2026-08-27 Hybrid path 中:
- AI agent 跳过 brainstorm 5 段澄清过程
- 直接创建 9 个 `.rddf/improvements/*.md` 文件
- 直接修改 `proposal-suggestions.md` 表格
- 所有操作未经用户对每个提案的 brainstorming 确认

后果:
- 流程纪律失败,违反 rdd-workflow-brainstorm 设计意图
- 9 个 proposal 文件虽然 5 段格式正确,但用户没有机会回答 brainstorming 澄清问题
- 无法追溯每个提案的创建上下文(谁、为什么、何种决策路径)

期望行为: 在 proposal 文件创建和 proposal-suggestions.md 修改前,必须有明确的 brainstorming 完成证据(如 user confirmation log 或 HARD-GATE token)。

## 范围

**In Scope**:

- 在 `skills/add-improve/SKILL.md` 的所有 3 种创建模式 (free / from-roadmap / from-issue) 入口增加 HARD-GATE 检查
- 在 `propose_change.sh` 的 `propose_create_change` 和 `propose_finalize_change` 函数入口增加 HARD-GATE token 检查
- 新增 `.rddf/state/.brainstorm-session.json` 记录 brainstorming 完成证据(session_id + brainstorm_completed_at + user_confirmation_ref)
- 用户在 guide-design 阶段可以强制 reset HARD-GATE token(manual override)

**Out of Scope**:

- 修改 rdd-workflow-brainstorm SKILL.md 内容本身(只增强执行)
- 改变 brainstorm 5 段流程设计
- 自动检测"伪 brainstorm"(AI 不真正对话,直接生成 scaffold)

## 关键场景

- GIVEN AI agent 收到"创建 X 改进提案"指令
  WHEN 调用 `add-improve` 创建 proposal 文件
  THEN HARD-GATE 检查 `.rddf/state/.brainstorm-session.json` 是否存在当前 session 的 brainstorm 完成记录,若不存在则拒绝并提示运行 brainstorm

- GIVEN AI agent 已完成 brainstorm 5 段对话
  WHEN 调用 `add-improve` 创建 proposal 文件
  THEN HARD-GATE token 通过,正常写入 `.rddf/improvements/<name>.md` 并注册到 `proposal-suggestions.md`

## 技术约束

- MUST: HARD-GATE 检查在所有 proposal 创建入口统一(不能绕过)
- MUST: HARD-GATE 失败时 stderr 输出明确的"先运行 brainstorm"指引
- MUST: HARD-GATE token 包含 session_id + timestamp + 至少 1 个 user 澄清问答记录
- MUST NOT: 完全阻止 manual 创建(允许 `STRICT_BRAINSTORM_GATE=no` 紧急跳过 + audit log)
- SHOULD: 提供 `--force-brainstorm-bypass` flag 配合 audit log 使用

## 验收标准

- [ ] `.rddf/state/.brainstorm-session.json` schema 定义 v1
- [ ] `skills/add-improve/scripts/{free,from_roadmap,from_issue}.sh` 入口增加 HARD-GATE 检查
- [ ] HARD-GATE 失败时 stderr 输出 "❌ brainstorm HARD-GATE not satisfied, run skill_use('rdd-workflow-brainstorm') first"
- [ ] HARD-GATE token 通过后正常写入 proposal 文件
- [ ] `STRICT_BRAINSTORM_GATE=no` 环境变量允许 emergency bypass,但记录到 `.rddf/state/.brainstorm-audit.jsonl`
- [ ] 新增 unit test 覆盖 3 个 scenarios: HARD-GATE pass / HARD-GATE fail / emergency bypass
- [ ] 历史 178 个 unmapped legacy proposals 不受 HARD-GATE 影响(legacy exception)
- [ ] `guide-design/SKILL.md` Phase 2 选项 1-3 文档更新说明 HARD-GATE 要求
- [ ] rdd-doctor 新增 `--category brainstorm-gate` 检查

## 相关

- 关联: `rdd-workflow-brainstorm/SKILL.md` HARD-GATE 设计来源
- 关联: `add-pre-commit-proposal-quality-check` (下一步提案)
- 来源: 2026-08-27 Hybrid path reflection (本次会话)
- 文件: `skills/add-improve/scripts/{free,from_roadmap,from_issue}.sh` + `skills/propose/scripts/propose_change.py`