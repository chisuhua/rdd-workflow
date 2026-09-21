# ADR-0053: rdd-env-bootstrap 编排层

> **状态**: 已采纳
> **日期**: 2026-09-22
> **决策者**: rdd-planner
> **关系**: 接续 ADR-0052 (Layer 0→3 渐进式上下文注入架构)

## Background

`fix-skill-post-install-discoverability` (ADR-0052, 2026-09-21) 实现了 Layer 0→3 渐进式上下文注入架构, 第三方项目用户从此可以在安装后立刻使用 rdd-workflow。但部署完成后, 用户仍需手动串联 4 个独立命令 (`rddf init` / `rddf setup ai-context` / `rddf doctor` / 修复) 才能完成"新项目启用 rdd-workflow"的标准流程。

核心缺口:

1. **无编排层**: 4 个独立命令需要用户手动串联
2. **doctor 只读**: 发现 WARNING 后无引导修复路径
3. **无入口**: 用户不知道"该先跑哪个"

用户原话 (2026-09-21 对话):

> "我希望通过一个技能能编排检查用户项目环境, 检查环境问题, 并可以执行初始化和修复"

## Decision

### D1: 新增独立 skill `rdd-env-bootstrap` + CLI 子命令 `rddf env-bootstrap`

不修改既有命令 (`rdd-doctor` / `rddf setup ai-context` / `rddf init` / `install.sh`),保持单一职责与边界清晰。

### D2: 4 阶段工作流

```
Phase 1 (detect, read-only)  → 文件检测: git/.rddf/语言/rddf CLI/AI config 文件, <200ms
Phase 2 (diagnose, read-only) → fork `rddf doctor --json`, 分类 findings, <1s
Phase 3 (suggest, read+report) → 基于 Phase 1+2 输出建议列表, <50ms
Phase 4 (guided-fix, write)   → fork subprocesses for [auto-fixable] items, ≤10s 总
```

Phase 1-3 只读, Phase 4 在用户确认或 `--auto-fix --yes` 模式下写。

### D3: 修复白名单固定

仅 `ai-context-bootstrap: 未部署` + `ai-context-bootstrap: 块已陈旧` 两类可自动修复。任何涉及 `.gitignore` / tracked files / `.rddf/state/*.json` 的修复**禁止自动执行**, 必须用户显式确认。

白名单理由:
- `rddf setup ai-context` 是幂等的 (有 sentinel 块标记)
- 不修改 `.gitignore` / tracked files
- 不写 `.rddf/state/` (除自己的 report)

### D4: 报告 schema version=1 锁定

报告路径: `<target>/.rddf/state/.env-bootstrap-report.json`
Schema: `_lib/schemas/env_bootstrap_report_schema.json` v1
字段: `version` / `generated_at` / `project_root` / `phase_1_detection` / `phase_2_diagnosis` / `phase_3_init_suggestion` / `phase_4_guided_fix` / `exit_code`

版本不兼容时 bump version 强制迁移。

### D5: 退出码对齐 openspec validate

| Code | 含义 |
|---|---|
| 0 | 健康 / 所有 WARNING 已自动修复 |
| 1 | 有 WARNING 但 fix 已自动执行 |
| 2 | 有 CRITICAL 或有 manual-only 未处理 |
| 3 | 环境错误 (rddf 未装 / cwd 非 rdd-workflow 项目) |

与 `_lib/cli/__main__.py::_NO_STATE_CHECK` 配合: `env-bootstrap` 加入 `{"setup", "doctor", "env-bootstrap"}` 白名单, 在非 rdd-workflow 项目目录友好提示而非报错。

## Boundary vs 既有 skill

| 既有 | 与 rdd-env-bootstrap 的关系 |
|---|---|
| `rdd-env-check` (phase 内嵌快速检查, ≤200ms 缓存) | rdd-env-bootstrap 是用户主动全流程编排 (≤10s 含 1-3 个 fix), 不同的 scope |
| `rdd-doctor` (只读 + 多 category 诊断) | rdd-env-bootstrap 调 doctor 但本身可引导式修复 (doctor 不动, env-bootstrap 加修复路径) |
| `rdd-hub-bootstrap` (Hub repo 引导式初始化) | Hub repo 用 (Projects V2 board + CI), 任意第三方项目用 env-bootstrap |
| `rddf setup ai-context` (单原语) | env-bootstrap 通过 subprocess fork 调用, 不修改 |
| `rddf init` (单原语) | env-bootstrap 通过 subprocess fork 调用, 不修改 |

## Consequences

### 正面
- 第三方项目用户从 "5 步手动串联" → "1 个命令完成", 大幅降低使用门槛
- doctor 保持只读语义边界 (user insight 采纳)
- 复用现有 `rddf setup / init / doctor` (不重新实现)
- 与现有 skill UX 一致 (其他 skill 如 rdd-env-check / rdd-hub-bootstrap 都是编排层)

### 负面
- 新增 skill 需维护; CLI 增加一个 subcommand 需保证不破坏现有命令
- env-bootstrap 自身复杂度 (4 阶段 + 决策表 + 报告 schema) 需后续维护
- 增加一个报告文件路径需 `.gitignore` 管理 (per-project local file)

### 风险与缓解

| 风险 | 等级 | 缓解 |
|---|---|---|
| 自动修复越界 (修改 tracked files) | 中 | 修复白名单固定, 仅 ai-context-bootstrap 两类 |
| 退出码语义混乱 | 低 | 严格对齐 openspec validate (0/1/2/3) |
| 子进程 fork 失败容错 | 中 | try/except 包裹 + 报告记录失败 |
| 报告 schema 版本不兼容 | 低 | version 字段 const=1, bump version 强制迁移 |
| 与 `rdd-env-check` 职责重叠 | 中 | 文档明确分工 (本 ADR §Boundary) |
| 隐藏复杂度 (user 选 dispatch-quick 后的 hidden signals) | 低 | rdd-env-bootstrap 不参与 dispatch-quick 路由 (rdd-quick 旁路独立, per ADR-0047) |
| Session binding 失败影响入口 | 低 | 友好降级 (proceed without binding per ADR-0017) |

## ADR 索引同步

- ADR-0016 (Arch Discovery Contract) — Phase 1 检测 arch 工件走 `.arch-handoff.json` 三层 fallback
- ADR-0017 (Session Binding) — skill 入口 bind 到 rddf-session, 失败友好降级
- ADR-0028 (Role Model) — `role:` frontmatter 字段定义 owns/not_owns
- ADR-0051 (Skill Description Convention) — description 必须明确 invoke when / default / boundary
- ADR-0052 (Layer 0 Progressive Context) — 前置架构 (fix-skill-post-install-discoverability)
- ADR-0053 (本 ADR) — rdd-env-bootstrap 编排层

## References

- `.rddf/improvements/add-env-bootstrap-skill.md` — 5 段设计草稿
- `.rddf/plans/add-env-bootstrap-skill.md` — TDD 5 步实施契约
- `skills/rdd-env-bootstrap/SKILL.md` — skill frontmatter + 4 阶段 prose
- `skills/rdd-env-bootstrap/references/fix-decisions.md` — 修复白名单
- `_lib/cli/env_bootstrap_cmd.py` — CLI 入口
- `_lib/env_bootstrap_report.py` — 数据层
- `_lib/schemas/env_bootstrap_report_schema.json` — 报告 schema v1
