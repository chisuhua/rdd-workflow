## 0. 前置调研 (P0,不改代码)

- [ ] 0.1 核实 `docs/proposal-suggestions-format.md` 中 `状态` 列的精确合法值集合(预期 `{待讨论, 已批准, 已拒绝, 延迟}`),记录到 design.md §2.1(已完成:与设计一致则无需改动)
- [ ] 0.2 用 `grep -rn "arch_proposal_review" skills/ tests/` 枚举全部调用方与调用形式(source 后调用 / 直接执行),产出清单,确认 P2 的 shim 覆盖全部形式
- [ ] 0.3 核实 `install.sh` / `skills/INSTALL.md` 是否硬编码子技能列表(还是 glob 自动发现 `skills/*/SKILL.md`),结论写入 P8 任务前提
- [ ] 0.4 核实 `tests/smoke.bats` 是否动态 glob `skills/*/SKILL.md`(AGENTS.md 称 v2.0.3 起动态 glob,覆盖 13 skill;新增后应为 14),结论写入 P8 任务前提

## 1. Schema & Python Helper (P1-T1)

- [ ] 1.1 创建 `skills/_lib/schemas/design_handoff_schema.json`(v1,4 个 required 字段: `design_complete_at` / `proposals_reviewed` / `all_proposals_have_decision` / `version=1`,`additionalProperties: false`)
- [ ] 1.2 创建 `skills/guide-design/scripts/write_design_handoff.py`(`write_design_handoff(project_root, proposals_reviewed)`,env-var 模式,Oracle C1 合规)
- [ ] 1.3 创建 `skills/guide-design/scripts/write_design_handoff.sh` bash wrapper(env 传参,无字符串插值)
- [ ] 1.4 创建 `tests/unit/test_design_handoff.py` 4 cases: schema v1 合法写入、version≠1 拒绝、缺 required 字段拒绝、proposals_reviewed=0 边界
- [ ] 1.5 验证: `python3 -m pytest tests/unit/test_design_handoff.py -q` 全绿

## 2. 脚本迁移 + guide-design SKILL.md (P2,同组完成,杜绝双份代码窗口)

- [ ] 2.1 复制 `skills/guide-arch/scripts/arch_proposal_review.sh` → `skills/guide-design/scripts/design_proposal_review.sh`,函数重命名 `arch_proposal_review` → `design_proposal_review`,修正内部脚本名引用
- [ ] 2.2 复制 `skills/guide-arch/scripts/approve_proposal.sh` → `skills/guide-design/scripts/approve_proposal.sh`(纯路径搬移)
- [ ] 2.3 **同 commit**: 将老路径 `guide-arch/scripts/arch_proposal_review.sh` 内容整体替换为包装函数 shim(design.md §7.2 模板,含 `BASH_SOURCE == $0` 直接执行守卫)
- [ ] 2.4 **同 commit**: 将老路径 `guide-arch/scripts/approve_proposal.sh` 内容整体替换为转发 shim(函数名不变,加 DEPRECATED 警告)
- [ ] 2.5 用 P0.2 清单逐一验证所有调用方经 shim 工作正常(source 后调用 + 直接执行两种形式)
- [ ] 2.6 创建 `skills/guide-design/SKILL.md`(Phase 1-5,~250 行;frontmatter `version: "1.0"`,`evolved-from: "extracted from guide-arch.md v2.0 Phase 5.5"`;Phase 5 调用 1.3 的 helper,禁止内联 `python3 -c`)
- [ ] 2.7 SKILL.md 内错误处理全部为函数 `return 1`,无 `exit 1`(用 `ast-grep` 或 grep 验证)
- [ ] 2.8 创建 `tests/integration/test_guide_design_phase.bats` 8 cases: arch-handoff 缺失拒绝 / 双源扫描 / y/n/d/s 四决策 / design-done 门控 / handoff 写入 + session 关闭 / 重复运行无新提案 NOOP / 重复运行有新增仅审新增
- [ ] 2.9 新增 shim 行为测试 1 case: 调老路径 `arch_proposal_review`,断言 stderr 含统一 DEPRECATED 文本且功能正常
- [ ] 2.10 验证: `bats tests/integration/test_guide_design_phase.bats` 全绿

## 3. guide-arch 简化 (P3-T1)

- [ ] 3.1 删除 `skills/guide-arch/SKILL.md` Phase 5.5 全节(~100 行),含菜单选项 3、PHASE_5_5_ENTRY 分支
- [ ] 3.2 frontmatter 之后、`## Phase 1` 之前插入 deprecation notice 框(文本以 spec.md deprecation-text Scenario 为准,单一 source of truth)
- [ ] 3.3 Phase 6 arch-done 输出去掉提案计数行,末行加 `💡 Next: skill_use("guide-design")`
- [ ] 3.4 检查 `tests/integration/test_guide_arch_skill.bats` 是否存在 Phase 计数/标题断言,有则更新预期
- [ ] 3.5 更新 `tests/integration/test_proposal_defer.bats` 4 个结构性 grep 的目标路径: `guide-arch/scripts/arch_proposal_review.sh` → `guide-design/scripts/design_proposal_review.sh`
- [ ] 3.6 新增 `tests/integration/test_arch_phase55_deprecation.bats` 2 cases: deprecation notice 存在且文本与 spec 一致 / Phase 5 门控(ADR+roadmap)在 Phase 5.5 删除后仍正常通过
- [ ] 3.7 验证: `bats tests/integration/test_guide_arch_skill.bats tests/integration/test_proposal_defer.bats tests/integration/test_arch_phase55_deprecation.bats` 全绿

## 4. guide-plan 门控 + 同 commit banner (P4,硬切换点,不可部分提交)

- [ ] 4.1 `skills/guide-plan/scripts/plan_intake.sh` 新增 `check_design_handoff()`(~15 行,env-var 模式): handoff 存在→校验 schema v1 + `all_proposals_have_decision=true`;不存在→尝试 `check_direct_create_fallback` 豁免;否则拒绝并提示 `skill_use("guide-design")`
- [ ] 4.2 门控插入位置: `SKIP_ARCH_HANDOFF=yes` 判断与 arch-handoff 检查**之后**(SKIP_ARCH_HANDOFF 同时跳过 arch+design,提示文案同步更新)
- [ ] 4.3 新增 `SKIP_DESIGN_HANDOFF=yes` 单独逃生口(仅跳过 design 门控,输出警告),默认不设
- [ ] 4.4 更新 `skills/guide-plan/SKILL.md` Phase 1 文档:新增门控说明 + 错误提示 + 两个逃生口语义
- [ ] 4.5 **同 commit**: `README.md` 顶部插入 v2.1 banner(新增 design 阶段说明 + 存量项目指引 + 逃生口说明)
- [ ] 4.6 **同 commit**: `AGENTS.md` 三阶段架构表改四阶段 + 同样的 banner 提示
- [ ] 4.7 创建 `tests/integration/test_plan_design_handoff.bats` 6 cases: arch-only 拒绝 / invalid schema 拒绝 / valid handoff 通过 / SKIP_ARCH_HANDOFF=yes 双跳过 / SKIP_DESIGN_HANDOFF=yes 单跳过 / direct-create fallback 豁免通过
- [ ] 4.8 创建 `tests/integration/test_plan_design_gate_legacy_break.bats`: 仅有 `.arch-handoff.json` 的存量项目 plan intake 正确失败且提示含 `skill_use("guide-design")`(锁定 D2 破坏性变更)
- [ ] 4.9 验证: `bats tests/integration/test_plan_design_handoff.bats tests/integration/test_plan_design_gate_legacy_break.bats tests/integration/test_plan_intake_staleness.bats` 全绿

## 5. 双扫描器 4-state (P5,两个扫描器同进同退)

- [ ] 5.1 修改 `skills/_lib/cli/guide_cmd.py::_scan_state()`: 按 design.md §5.1 阶梯插入 1b/2 分支,7b 未审批提案路由改 `guide-design`,保留其余全部分支(ADR<1 / stale plan-handoff / 无 roadmap / worktree / committed change)
- [ ] 5.2 修改 `skills/guide/scripts/scan-state.sh::scan_state()`: 与 5.1 完全一致的阶梯(bash 版),保证两个入口推荐一致
- [ ] 5.3 `cmd_guide()` 输出增加 `.design-handoff.json` 状态行;`guide` 技能状态展示同步
- [ ] 5.4 更新 `tests/unit/test_cli_guide.py` 4 cases: arch-only→guide-design / arch+design→guide-plan / arch 但 ADR<1→guide-arch / 无 handoff 有未审批提案→guide-design
- [ ] 5.5 创建 `tests/integration/test_guide_recommender_4state.bats` 7 cases(7 种 handoff 组合: arch-only / arch+design / arch+design+plan / plan-only / design+plan / 全无+未审批提案 / 全无+无提案),每个 case 同时断言 `rddf guide` 与 bash 扫描器输出一致
- [ ] 5.6 验证: `python3 -m pytest tests/unit/test_cli_guide.py -q && bats tests/integration/test_guide_recommender_4state.bats` 全绿

## 6. rddf-session stage_design (P6-T1)

- [ ] 6.1 `skills/rddf-session/scripts/rddf_session_pkg/_types.py`: `_VALID_KINDS` 追加 `"stage_design"`,`_KIND_ALIAS` 追加 `"guide-design": "stage_design"`
- [ ] 6.2 `skills/_lib/schemas/sessions_schema.json`: `kind` 枚举追加 `"stage_design"`,`goal.intent` 枚举追加 `"guide-design"`,`version` 保持 `const: 1`(additive,不迁移既有数据)
- [ ] 6.3 `skills/rddf-session/scripts/rddf_session_hooks.sh`: `parent_kind_map` 追加 `"stage_design": "stage_arch"`,修改 `"stage_plan"` 的 parent 为 `"stage_design"`
- [ ] 6.4 更新 `tests/unit/test_rddf_session.py` 1 case: stage_design kind 通过 schema 校验
- [ ] 6.5 创建 `tests/integration/test_rddf_session_design.bats` 4 cases: stage_design create / resume / abandon / **完整链**(stage_arch close → stage_design 以 stage_arch 为 parent → close → stage_plan 以 stage_design 为 parent,断言 ancestor 链含 3 stages)
- [ ] 6.6 验证: `python3 -m pytest tests/unit/test_rddf_session.py -q && bats tests/integration/test_rddf_session_design.bats` 全绿

## 7. add-improve 与 guide 菜单集成 (P7-T1)

- [ ] 7.1 `skills/add-improve/SKILL.md` Phase 3: "批准流程" 引用从 `guide-arch Phase 5.5` 改为 `guide-design`
- [ ] 7.2 `skills/guide/SKILL.md` 推荐菜单插入 `guide-design` 条目,位置严格在 `guide-arch` 之后、`guide-plan` 之前,label 含"审查改进提案"语义
- [ ] 7.3 创建 `tests/integration/test_add_improve_to_design_e2e.bats` 3 cases: add-improve 创建提案 → design 扫描可见 / y 批准后落入 `proposal-approved.md` 且 suggestions 状态列更新 / add-improve 独立调用(不经 design)行为不变
- [ ] 7.4 验证: `bats tests/integration/test_add_improve_to_design_e2e.bats` 全绿

## 8. 文档与安装验证 (P8-T1)

- [ ] 8.1 更新 `docs/proposal-suggestions-format.md` §3 审查流程: `guide-arch Phase 5.5` → `guide-design Phase 3`
- [ ] 8.2 更新 `docs/proposal-approved-format.md` 相应引用
- [ ] 8.3 更新 `proposal-suggestions.md` 头注释: "guide-arch Phase 5.5 逐个审查" → "guide-design 逐个审查"
- [ ] 8.4 更新 `USAGE.md` 与 `docs/ONBOARDING.md` 工作流描述为四阶段
- [ ] 8.5 新建 `docs/v2-design-phase-guide.md`(~200-300 行: 引言 / 入口 / Phase 1-5 速查 / 与 arch/plan/ship 关系 / deprecated path 与 v2.2.0 移除计划)
- [ ] 8.6 按 P0.3 结论处理 `install.sh` / `skills/INSTALL.md`(硬编码列表→更新;glob 自动发现→NOOP 并在 commit message 说明)
- [ ] 8.7 按 P0.4 结论验证 `tests/smoke.bats` 动态 glob 覆盖 14 个 SKILL.md(写死则修)
- [ ] 8.8 创建 `tests/integration/test_install_smoke_coverage.bats` 2 cases: 安装产物含 guide-design / smoke glob 计数 ≥14
- [ ] 8.9 检查 `docs/change-quality-guide.md` 是否引用三阶段流程,有则更新
- [ ] 8.10 验证: `bats tests/integration/test_install_smoke_coverage.bats tests/smoke.bats` 全绿

## 9. 终验 (P9-T1,全部自动化)

- [ ] 9.1 `npm test` bats 全量绿
- [ ] 9.2 `python3 -m pytest tests/unit/ -q --tb=short` 全绿
- [ ] 9.3 `python3 -m pytest tests/integration/ -q --tb=short` 全绿
- [ ] 9.4 `openspec validate add-guide-design-phase --strict` 返回 0
- [ ] 9.5 rollback rehearsal: 在临时 worktree revert P4-P6 改动,跑 `python3 -m pytest tests/unit/test_rddf_session.py -q && bats tests/smoke.bats`,确认 session 模块与冒烟不崩溃(验证 design.md §10 回滚路径)
- [ ] 9.6 人工 sanity check 1 轮(可选,可跳过): 走一遍 add-improve → guide-design → guide-plan 完整链路
- [ ] 9.7 更新 `CHANGELOG.md` v2.1 release notes(四阶段架构 / 硬切换说明 / 逃生口 / shim v2.2.0 移除计划)