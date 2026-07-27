# add-workflow-reflect-engine

**优先级**: P1 | **来源**: 用户反馈
**阶段**: default | **分类**: core-impl
**类型**: feature

## 架构依据

参照以下 ADR 作为设计基础：

| ADR | 关联 |
|-----|------|
| **ADR-0003** 三阶段架构 | 反思 hook 挂载在 arch-done / plan-done / archive-done 三个 gate 上 |
| **ADR-0017** rddf-session | 反思的输入数据来源——session 生命周期、event log、tasks.md 进度 |
| **ADR-0007** gate 机制 | 反思引擎复用 gate 的插件式架构：`reflect_engine.py` 作为 gate 的后置 hook，不阻塞 gate 通过判定 |
| **ADR-0011** phase-step pipeline | 反思是 pipeline 中的"后处理步骤"——在 phase 完成、gate 通过之后、下一阶段开始之前执行 |

设计原则：
- 反思引擎读取但不修改现有状态文件，遵循 Oracle 模式的只读原则
- 去重机制复用 `proposal-suggestions.md` 的已有 improvements 索引
- Issue 创建走 GitHub API（`gh issue create`），自动填入模板化的标题和正文
- 冷却记录写入 `.rddf/state/reflect-cooldown.json`（fingerprint → last_triggered_at）

与现有流程的关系：
```
guide-arch:  Phase 5 gate →  arch-done pass →  reflect_engine(arch)
guide-plan:  Phase 4 gate →  plan-done pass →  reflect_engine(plan)
guide-ship:  Phase 3 archive →  archive完成 →  reflect_engine(ship)
```

## 范围

### In Scope

| 功能 | 说明 |
|------|------|
| 反思引擎 `reflect_engine.py` | 独立 Python 模块，统一分析逻辑，可独立测试 |
| 3 个 gate hook 点 | `write_arch_handoff`、`plan_done_gate`、`archive()` 末尾追加调用 |
| 错误触发 | `execute` 步骤不可恢复失败（max_retries 耗尽、gate error 级失败） |
| 分层阈值 | ship=任何不可恢复失败，plan=同一根因≥2次，arch=仅日志 |
| 去重匹配 | 模糊匹配 `improvements/` 目录 + `proposal-suggestions.md` + `proposal-approved.md` |
| GitHub issue 创建 | `gh issue create` 走 GitHub CLI，自动填入标题/正文模板 |
| 冷却记录 | `.rddf/state/reflect-cooldown.json`，按 fingerprint 24h |
| `--no-reflect` 开关 | 环境变量 `SKIP_WORKFLOW_REFLECTION=1` |

### Out Scope（v1 不做）

| 项目 | 原因 |
|------|------|
| 全自动 file（无需确认） | Oracle 建议：先跑 2-4 周收集确认/拒绝比后再决定 |
| 摩擦信号实时提示（C 类） | 只收集到日志，不进确认流程，留给 v2 periodic digest |
| 语义聚类 fingerprint | v1 只做 `gate名称 + 错误类别` 简单匹配 |
| 自动修复建议 | 反思只判定+提 issue，不给修复方案 |
| 跨 session 反思聚合 | 每次反思只分析当前 session 上下文 |

## 关键场景

- GIVEN ship 阶段执行中，agent 在 execute 步骤耗尽 max_retries(3次) 仍失败
  WHEN 错误被标记为 unrecovered_failure
  THEN reflect_engine(ship) 自动触发，分析 event log + tasks.md，发现根因为 worktree 创建超时 → 判定为 rdd-workflow 问题 → 去重通过 → 生成 issue 草案，提示用户确认 → 用户确认后 `gh issue create` 到 chisuhua/rdd-workflow

- GIVEN plan-done gate 因"propose 质量门未达标"失败，用户修改后再次提交仍失败
  WHEN 同一 gate 同根因失败次数 ≥2
  THEN reflect_engine(plan) 触发，去重发现已存在 `propose-quality-autohook` improvements → 提示"已有相关提案，是否追加评论？"

- GIVEN arch 阶段 gate 通过，但 event log 显示用户重做了 4 次 ADR 编辑才通过质量门
  WHEN reflect_engine(arch) 触发
  THEN 判定为"摩擦信号" → 不弹出确认提示 → 写入 `.rddf/state/reflect-friction.log`

- GIVEN fingerprint `plan-done:propose-quality-gate-fail` 在 12 小时前已触发过一次
  WHEN 同一 fingerprint 再次触发
  THEN reflect_engine 静默跳过，不重复分析也不提示

## 技术约束

**MUST**
- 反思引擎必须只读——不修改任何状态文件
- gate 非阻塞——反思失败不得阻止 gate 通过
- fingerprint 格式固定为 `{phase}:{gate_name}:{error_category}`
- 去重必须覆盖 `improvements/` 目录 + `proposal-suggestions.md` + `proposal-approved.md`
- `gh issue create` 必须可退出——用户拒绝确认时不得创建 issue
- 输入必须从现有数据源获取（event log + tasks.md + session 状态），不做全仓库扫描

**MUST NOT**
- 不自动 file issue（v1 永远需用户确认）
- 不进行语义聚类 fingerprint——只用字面匹配
- 不触发实时摩擦信号提示（只记录到日志）
- 冷却期内不得重复分析同一 fingerprint
- 不阻塞或延迟 gate 判定（超时 10s 后自动放弃）

**SHOULD**
- 使用 GitHub CLI (`gh`) 而非直接 HTTP API（减少依赖）
- 分析结果写入 `.rddf/state/reflect-analysis.json` 供审计
- issue 模板包含：触发阶段、session ID、错误摘要、event log 相关片段
- `SKIP_WORKFLOW_REFLECTION=1` 时完全跳过，不产生任何副作用

## 验收标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | `reflect_engine.py` 独立可测试，单元测试覆盖率 ≥80% | `pytest tests/unit/test_reflect_engine.py` |
| 2 | 3 个 gate hook 点均追加调用，gate 通过后自动触发分析 | 集成测试：模拟 arch-done / plan-done / archive-done 各 1 次 |
| 3 | 分层阈值正确：ship=任意不可恢复失败触发，plan=同根因≥2次触发，arch=仅日志不弹窗 | 集成测试每种组合 |
| 4 | 去重命中时提示"已有提案 XXX"而非生成新 issue | 预置匹配 improvements 的测试数据 |
| 5 | `gh issue create` 成功后输出 issue URL | E2E：用 `--dry-run` 模式验证模板内容 |
| 6 | 冷却期（24h）内同一 fingerprint 静默跳过 | 单元测试：连续调用两次同一 fingerprint |
| 7 | `SKIP_WORKFLOW_REFLECTION=1` 完全禁用，无日志、无分析 | 集成测试：设置 env var 后 gate 通过无副作用 |
| 8 | 反思引擎失败/超时（>10s）不阻塞 gate 通过 | 单元测试：模拟超时异常，gate 仍返回 pass |
| 9 | issue 路由正确：skills/_lib/ 或 docs/adr/ 路径 → rdd-workflow，其他 → 用户项目 | 单元测试：两种路径模式各 1 个 case |
