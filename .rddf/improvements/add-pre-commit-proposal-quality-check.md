# add-pre-commit-proposal-quality-check

**优先级**: P1 | **来源**: 2026-08-27 Hybrid path reflection (创建 9 个 proposal 文件后未运行 propose_quality_check.py 验证,直到后期才补救)
**阶段**: phase-3 | **分类**: governance
**类型**: improvement

**主题**: 2026-08-27 Hybrid path reflection (流程改进)

## 架构依据

`skills/propose/scripts/propose_quality_check.py` 已存在,支持 `--change <name>` 验证单个 proposal。但当前未集成到自动流程:

- AI agent 创建 proposal 后,必须手动运行验证
- 2026-08-27 Hybrid path 中:9 个文件创建后才用 inline python 检查,发现 verify 脚本本身需用 inline-aware regex(行首字段定义 vs inline 字段定义)
- 无 git hook / pre-commit 强制检查
- 无 CI 自动跑 proposal quality check

后果:
- AI 创建低质量 proposal(缺字段、格式错误)无即时反馈
- 直到 guide-design 阶段 review 才被发现
- 178 个 unmapped legacy proposal 中可能有格式缺陷未被捕获

期望行为: proposal 创建后(无论 AI agent 还是 manual)立即自动运行 quality check,失败时阻止 proposal-suggestions.md 注册。

## 范围

**In Scope**:

- 新增 `.git/hooks/pre-commit`(or `.githooks/pre-commit`)包含 proposal quality check:
  - 检测 staged changes 是否包含 `.rddf/improvements/*.md` 或 `proposal-suggestions.md`
  - 若是,运行 `python3 skills/propose/scripts/propose_quality_check.py --all` (或每个 file)
  - 失败时 exit 1,阻止 commit
- 在 `add-improve` 脚本出口自动调用 quality check
- `guide-design` Phase 3 review 时显示 quality check 结果
- `rdd-doctor` 新增 `--category proposal-quality` 定期巡检所有 `.rddf/improvements/*.md`

**Out of Scope**:

- 修改 `propose_quality_check.py` 的核心验证逻辑(独立提案)
- 阻止 178 个 legacy proposals 的 commit(legacy exception)
- CI 配置(独立项目)

## 关键场景

- GIVEN 用户 commit 修改了 `.rddf/improvements/<new-proposal>.md`
  WHEN git pre-commit hook 触发
  THEN 自动运行 quality check,验证 12 个 field,任何缺失 → exit 1 阻止 commit

- GIVEN AI agent 通过 `add-improve` 创建 proposal
  WHEN proposal 写入完成后
  THEN quality check 自动运行,失败时 stderr 输出缺失字段列表

- GIVEN 178 个 legacy proposal 中存在格式缺陷
  WHEN `rdd-doctor --category proposal-quality` 巡检
  THEN 列出格式缺陷但只 WARNING(不阻断 ship)

## 技术约束

- MUST: pre-commit hook 不能修改 proposal 内容,只检查并报告
- MUST: hook 可通过 `SKIP_PROPOSAL_QUALITY_CHECK=yes` 跳过(emergency bypass)
- MUST: quality check 必须支持 inline 字段格式(如 `**优先级**: P0 | **来源**: ...`)
- MUST NOT: 在 pre-commit hook 中执行超过 30s 的检查(否则拖慢 commit)
- SHOULD: 提供 `--strict-proposal-quality` flag 升级 WARNING 为 block
- SHOULD: rdd-doctor 巡检只 WARNING 不 blocking

## 验收标准

- [ ] `.githooks/pre-commit` 脚本实现(proposal quality check)
- [ ] `git config core.hooksPath .githooks` 设置文档化在 README.md / AGENTS.md
- [ ] `add-improve/scripts/{free,from_roadmap,from_issue}.sh` 出口自动调用 quality check
- [ ] `propose_quality_check.py --all` 子命令实现(批量验证所有 `.rddf/improvements/*.md`)
- [ ] `propose_quality_check.py` 修复 inline 字段检测(支持 `**优先级**: P0 | **来源**: ...` 一行格式)
- [ ] `rdd-doctor --category proposal-quality` 巡检命令实现,178 legacy 只 WARNING 不 block
- [ ] `SKIP_PROPOSAL_QUALITY_CHECK=yes` 环境变量跳过 hook
- [ ] 新增 unit test 覆盖 scenarios: 字段缺失 / inline 字段 / 5 段缺失 / 主题缺失
- [ ] 测试: hook 在 30s 内完成(performance)
- [ ] 文档: AGENTS.md 增加"提案质量保证"章节

## 相关

- 关联: `propose_quality_check.py` 现有实现
- 关联: `add-brainstorm-hardgate-enforcement` (前置提案,先确保 brainstorm 流程)
- 关联: `add-proposal-source-tracking` (同时补充字段元数据)
- 来源: 2026-08-27 Hybrid path reflection (本次会话)
- 文件: `.git/hooks/` → `.githooks/pre-commit` + `skills/propose/scripts/propose_quality_check.py`