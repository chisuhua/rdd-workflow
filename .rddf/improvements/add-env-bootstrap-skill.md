---
name: add-env-bootstrap-skill
priority: P1
phase: phase-3
category: ux-improvements
type: feature
状态: approved
依赖: fix-skill-post-install-discoverability
主题: 流程定制层
approved_at: 2026-09-22
approved_by: rdd-planner
review_notes: |
  s → y: 5 段审核通过 (5-segment compliance) + 2 项 AC 修正
  - AC-1.6 rddf-session binding (per ADR-0017)
  - AC-6.5 setup ai-context --yes 幂等性验证
  recommended_route: complex (per ADR-0050; 7 files / >3 tasks / 风险关键词 auto-fix)
  awaiting next stage: rdd-builder P0 (generate openspec proposal + 实施契约)
来源: 2026-09-21 fix-skill-post-install-discoverability 实施收尾对话 — 用户洞察"我希望通过一个技能能编排检查用户项目环境，检查环境问题，并可以执行初始化和修复"。L0→L3 部署后缺"一键编排 + 引导式修复"层。
生成时间: 2026-09-21
roadmap_ref:
  project_id: 流程定制层
  phase: phase-3
---

# add-env-bootstrap-skill

**主题**: 流程定制层

## 架构依据

**问题陈述**

`fix-skill-post-install-discoverability` (P0, 2026-09-21 已批准归档) 实现了 Layer 0→3 渐进式上下文注入架构：
- Layer 0 = `rddf setup ai-context` CLI（部署 AI 协议块到目标项目）
- Layer 1 = SKILL.md 自包含（零外部 docs/ 引用）
- Layer 2 = `install.sh --with-docs`（可选 docs/ 分发）
- Layer 3 = 开发者本地 docs/

但实施后用户体验仍存在**编排层缺口**：

| 用户场景 | 现状 | 痛点 |
|---|---|---|
| 第三方项目首次启用 rdd-workflow | 必须手动跑 4 个独立命令 | 不知道该先跑哪个 |
| Layer 0 是否已部署 | `rddf doctor --category ai-context-bootstrap` 只读 | 知道问题但不会修 |
| 批量修复 doctor WARNING | 不可行（doctor 只读） | 必须逐个切换命令 |
| 修复后验证 | 再跑一次 doctor | 又一次手动调用 |

**核心缺口**：
- **无编排层**：4 个独立命令（init / setup / doctor / 修复）需要用户手动串联
- **doctor 只读**：发现 WARNING 后无引导修复路径
- **无入口**：用户不知道"该先跑哪个"

**用户原话**（2026-09-21 对话）：
> "我希望通过一个技能能编排检查用户项目环境，检查环境问题，并可以执行初始化和修复"

**用户洞察（4 轮方案演进）**

| 轮次 | 方案 | 拒绝原因 |
|---|---|---|
| 1 | `doctor --fix` 选项 | 模糊 doctor 只读语义，复杂度爆炸 |
| 2 | 新增 `rddf fix` 子命令 | Unix 单一职责好，但缺编排层 |
| 3 (采纳) | **独立 skill `rdd-env-bootstrap` 编排** | doctor 保持只读；`rddf fix` 可作为编排内 action；编排层补完整用户体验 |

**触发场景**

- 场景 A：用户刚 `bash install.sh --global` 完，进入新项目目录，不知道下一步该跑什么 → 期望 `rddf env-bootstrap` 一键引导
- 场景 B：`rddf doctor` 报 N 个 WARNING，用户想批量修复 → 期望 `rddf env-bootstrap --auto-fix` 自动处理可修复项
- 场景 C：CI 环境跑自动化健康检查 → 期望 `--check-only --json` 输出供 CI 消费
- 场景 D：用户重复跑同一个项目，想看上次报告 → 期望 `.rddf/state/.env-bootstrap-report.json` 记录历史

**不修的代价**

- 第三方项目用户从"5 步手动串联"→ 持续低采用率（与 fix-skill-post-install-discoverability 的目标矛盾）
- `rddf doctor` 的价值打折（发现问题但不能修，用户继续手动查文档）
- 与现有 skill UX 不一致：其他 skill（如 `rdd-env-check` / `rdd-hub-bootstrap`）都是编排层，只有这块留空

## Why

第三方项目用户从 `fix-skill-post-install-discoverability` 部署完 L0-L3 后，仍需手动串联 4 个独立命令（`rddf init` / `rddf setup ai-context` / `rddf doctor` / 修复）。rdd-doctor 是只读工具，发现 WARNING 后用户必须切到其他命令逐个修复，缺少"一键编排 + 引导式修复"的体验层。本提案引入 `rdd-env-bootstrap` skill 作为编排入口，doctor 保持只读语义边界，env-bootstrap 串联 init / setup / doctor / 修复为 4 阶段工作流（detect → diagnose → suggest → guided-fix）。

## What Changes

新增独立 skill `rdd-env-bootstrap` + CLI 子命令 `rddf env-bootstrap` + 报告文件 `.rddf/state/.env-bootstrap-report.json`（version 1 schema）。修改 `_lib/cli/__init__.py` + `_lib/cli/__main__.py`（扩展 `_NO_STATE_CHECK`）。不修改 `rdd-doctor`（保持只读）、不修改 `rddf setup ai-context`（已是底层原语）、不修改 `rddf init`、不修改 `install.sh`。

## 范围

**In Scope**

### 1. 新增 skill `rdd-env-bootstrap`

位置：`skills/rdd-env-bootstrap/`

- `SKILL.md`：含完整 frontmatter (name/description/license/compatibility/metadata/role)
- `references/fix-decisions.md`：自动修复决策表
- `scripts/`：辅助脚本（如 Phase 1 检测、报告生成）

**4 阶段编排工作流**：

```
Phase 1: Project Env Detection（环境检测，只读）
  ├─ git 仓库? .rddf/ 存在? 项目语言检测 (Python/Node/Go/Rust)?
  ├─ rdd-workflow 是否已全局安装 (which rddf + version)?
  └─ 检测目标项目已有哪些 AI 配置文件 (.cursorrules / CLAUDE.md / AGENTS.md)

Phase 2: Health Diagnosis（诊断，只读，委托 rddf doctor）
  ├─ 调用 `rddf doctor --json` 获取 findings
  ├─ 按 category 过滤 env-bootstrap 关心的 finding
  │   ├─ ai-context-bootstrap → 可自动修复
  │   ├─ gitignore → 不可自动修复（用户决策）
  │   ├─ docs-consistency → 不可自动修复（半自动）
  │   └─ bypass-audit / orphan-gates → 不可自动修复（人工审计）
  └─ 分类: [auto-fixable] | [user-decision] | [manual-only]

Phase 3: Init Suggestion（初始化建议，只读 + 写报告）
  ├─ 基于 Phase 1+2 结果建议用户执行:
  │   ├─ 缺失 .rddf/project.yaml → 建议 `rddf init`
  │   ├─ 缺失 Layer 0 → 建议 `rddf setup ai-context`
  │   └─ 缺失 Layer 2 docs → 建议 `install.sh --with-docs`
  └─ 写报告到 `.rddf/state/.env-bootstrap-report.json`

Phase 4: Guided Fix（引导式修复，写入）
  ├─ 遍历 [auto-fixable] findings:
  │   ├─ 默认模式: 每个修复点 prompt [Y/n]，用户确认后 fork 子进程执行
  │   └─ --auto-fix 模式: 无 prompt，全部执行 (需 --yes)
  ├─ [user-decision] findings: 输出建议，不自动执行
  └─ [manual-only] findings: 报告 + 跳过
```

### 2. 新增 CLI 子命令 `rddf env-bootstrap`

位置：`_lib/cli/env_bootstrap.py`

```bash
rddf env-bootstrap [options]
  --check-only        # 仅 Phase 1-2, 不写任何文件
  --auto-fix          # Phase 4 无 prompt 全部执行 (需 --yes)
  --yes               # 跳过 Phase 4 每个 prompt
  --target <path>     # 目标项目根 (默认 cwd)
  --report <path>     # 报告输出路径 (默认 .rddf/state/.env-bootstrap-report.json)
```

注册：
- `_lib/cli/__init__.py`：注册 `env_bootstrap` subcommand
- `_lib/cli/__main__.py`：扩展 `_NO_STATE_CHECK = {"setup", "doctor", "env-bootstrap"}`

### 3. Phase 4 自动修复决策表（白名单）

| Finding category | 可自动修复？ | 执行命令 | 风险 |
|---|---|---|---|
| `ai-context-bootstrap: 未部署` | ✅ | `rddf setup ai-context --yes` | 低（幂等 sentinel） |
| `ai-context-bootstrap: 块已陈旧` | ✅ | `rddf setup ai-context --yes` | 低（force overwrite sentinel） |
| `gitignore: openspec/ 缺失` | ❌ | 输出建议 | 中（影响 git 行为） |
| `docs-consistency: ADR drift` | ❌ | 输出建议 + 重建脚本提示 | 中（影响文档同步） |
| `bypass-audit: bypass > 阈值` | ❌ | 输出审计报告 | 高（需人工审查） |
| `orphan-gates: gate 失效` | ❌ | 输出诊断 | 高（影响 phase 安全） |
| `migration-residue` | ❌ | 输出清单 | 中（影响 schema 一致性） |

**安全原则**：任何会修改 `.gitignore`、tracked files、`.rddf/state/*.json`（除 bootstrap-report）的修复默认**不可自动执行**，必须用户显式确认。

### 4. 报告 schema（version 1）

`.rddf/state/.env-bootstrap-report.json`：

```json
{
  "version": 1,
  "generated_at": "2026-09-21T...",
  "project_root": "/path/to/project",
  "phase_1_detection": {
    "is_git_repo": true,
    "has_rddf_dir": false,
    "language_hints": ["python"],
    "rddf_installed": true,
    "rddf_version": "4.0.x",
    "ai_config_files_detected": [".cursorrules", "CLAUDE.md"]
  },
  "phase_2_diagnosis": {
    "doctor_invoked": true,
    "total_findings": 3,
    "auto_fixable": 1,
    "user_decision": 1,
    "manual_only": 1
  },
  "phase_3_init_suggestion": [
    "rddf init (生成 .rddf/project.yaml)",
    "rddf setup ai-context (部署 Layer 0)"
  ],
  "phase_4_guided_fix": {
    "executed": [
      {"finding": "ai-context-bootstrap: 未部署", "command": "rddf setup ai-context --yes", "status": "success"}
    ],
    "skipped": [],
    "manual_required": [
      {"finding": "gitignore: openspec/ 缺失", "recommendation": "添加 'openspec/' 到 .gitignore"}
    ]
  },
  "exit_code": 0
}
```

### 5. Skill description 符合 ADR-0051

```yaml
description: |
  Environment bootstrap orchestrator for new/existing rdd-workflow projects.
  Invoke when:
    1. User just installed rdd-workflow in a new project
    2. User wants guided remediation of doctor findings
    3. User says "set up rdd-workflow" / "bootstrap environment" / "fix my env"
  Default: 4-phase flow (detect → diagnose → suggest → guided-fix).
  With --check-only: phases 1-2 only (read-only).
  With --auto-fix: phase 4 executes all safe fixes without prompts.
  Boundary: owns orchestration; delegates fixes to setup/init/init.
```

### 6. 测试覆盖

- `tests/integration/test_env_bootstrap.bats` (≥ 8 cases)
- `tests/unit/test_env_bootstrap.py` (≥ 5 cases)

### 7. 文档同步

- `README.md` 技能列表（27 → 28）
- `AGENTS.md` 关键约定段
- 新增 ADR-0053 (Layer 0 编排层)

**Out of Scope**

- 不修改 `rdd-doctor`（保持只读语义边界，per 用户 4 轮讨论结论）
- 不修改 `rddf setup ai-context`（已是底层原语，env-bootstrap 通过 CLI fork 调）
- 不修改 `rddf init`（同上）
- 不修改 `install.sh`（不涉及安装流程）
- 不实现跨机器协调（仅本地用户项目目录）
- 不替代 `rdd-env-check`（后者是 phase 内嵌快速检查，env-bootstrap 是用户主动全流程）
- 不引入新依赖（Pure bash + Python 3.11 stdlib）

## Capabilities

### 关键场景

#### 场景 1：第三方项目首次启用 rdd-workflow

- GIVEN 用户在 `/path/to/new-project` 目录
- AND 已全局安装 rdd-workflow (`bash ~/.agents/skills/rdd-workflow/install.sh --global`)
- AND 目标项目无 `.rddf/`、无 AI 配置文件
- WHEN 用户跑 `cd /path/to/new-project && rddf env-bootstrap`
- THEN Phase 1 检测: 是 git 仓库 + Python 项目 + 无 `.rddf/` + 无 AI 配置
- AND Phase 2 调用 `rddf doctor`, 产生 1 个 `ai-context-bootstrap: 未部署` finding
- AND Phase 3 建议: `rddf init` + `rddf setup ai-context`
- AND Phase 4 prompt: "运行 `rddf setup ai-context --yes`? [Y/n]"
- AND 用户输入 `y` → 子进程执行 → 创建 `AGENTS.md` + 部署 Layer 0
- AND 退出码 0, 报告写入 `.rddf/state/.env-bootstrap-report.json`

#### 场景 2：CI / 脚本自动修复

- GIVEN CI 环境 `CI=1` 环境变量已设
- AND 用户在 `rddf env-bootstrap --auto-fix --yes` 后跑测试
- THEN Phase 4 不 prompt, 直接执行所有 [auto-fixable] 项
- AND 任何 [user-decision] / [manual-only] 项写入报告但不执行
- AND 退出码: 全部成功 0, 部分成功 1, 关键失败 2

#### 场景 3：仅诊断（dry-run）

- GIVEN 用户想检查环境但不动任何文件
- WHEN `rddf env-bootstrap --check-only`
- THEN Phase 1+2 跑完, Phase 3 输出建议列表
- AND Phase 4 输出"如需修复请去掉 --check-only"提示
- AND 退出码 0, 不写 `.rddf/state/.env-bootstrap-report.json`

#### 场景 4：非 rdd-workflow 项目目录

- GIVEN 用户在 `/tmp/random-dir` 跑 `rddf env-bootstrap`
- AND 该目录不是 rdd-workflow 项目（无 `.rddf/state/`, 无 `_lib/`）
- THEN CLI 检测到非 rdd-workflow 项目, 输出友好提示:
  "此命令需要全局安装 rdd-workflow。可执行: bash ~/.agents/skills/rdd-workflow/install.sh --global"
- AND 退出码 3 (沿用 openspec validate 约定)

#### 场景 5：已 bootstrap 过的项目

- GIVEN 用户重复跑 `rddf env-bootstrap`
- AND `.rddf/state/.env-bootstrap-report.json` 已存在 (version=1)
- THEN 复用 Phase 1 检测结果 (避免重复文件系统扫描)
- AND Phase 2 仍然调 doctor (findings 可能变化)
- AND Phase 4 仅修复新增 finding (idempotent)

### 技术约束

#### 必须遵循

1. **ADR-0016 Arch Discovery Contract** — Phase 1 检测 arch 工件走 `.arch-handoff.json` 三层 fallback (env var > handoff > 默认)
2. **ADR-0028 Role Model** — 新 skill 必须有 `role:` frontmatter 字段 (owns/not_owns 清晰)
3. **ADR-0051 Skill Description Convention** — 顶层 description 必须明确 invoke when / default / boundary
4. **ADR-0017 Session Binding** — skill 入口应 bind 到 rddf-session (per `owner_opencode_session_id`)
5. **Oracle C1 Security** — env-var 模式传参, 禁止 bash `$VAR` 字符串插值
6. **`_NO_STATE_CHECK` 扩展** — `env-bootstrap` 加入白名单 (与 setup/doctor 对齐)
7. **bash + Python 3.11** — 沿用项目语言, 无新依赖
8. **失败容忍** — Phase 4 任何单个 fix 失败不阻断其他 fix, 写入报告即可

#### 性能预算

- Phase 1 检测: < 200ms (1 个 `git rev-parse` + 1 个 `which rddf` + N 个 file exists check)
- Phase 2 调用 doctor: < 1s (doctor 本身 TTL 3600s 缓存)
- Phase 3 建议生成: < 50ms (纯计算)
- Phase 4 fork 子进程: 每个 fix ≤ 5s (setup ai-context 实测 ~200ms)

总时长预算: < 10s (含 1-3 个 fix)

#### 错误处理

| 错误 | 处理 |
|---|---|
| `which rddf` 找不到 | 退出码 3, 提示用户安装 |
| Phase 1 检测失败 | 跳过该项, 报告 partial detection |
| doctor 调用失败 | 跳过 Phase 2, 仍可执行 Phase 1+3 |
| Phase 4 子进程失败 | 记录到 report.executed[].status="failed", 不中断其他 fix |
| 报告写盘失败 | stderr warning, 不影响退出码 |

## Impact

### 用户体验

- **正面**：第三方项目用户从"5 步手动串联"→"1 个命令完成"，大幅降低使用门槛
- **负面**：新增 skill 需维护；CLI 增加一个 subcommand 需保证不破坏现有命令

### 代码/架构

- **正面**：doctor 保持只读语义边界（user insight 采纳）
- **正面**：复用现有 `rddf setup / init / doctor`（不重新实现）
- **负面**：env-bootstrap 自身复杂度（4 阶段 + 决策表 + 报告 schema）需后续维护

### 风险

| 风险 | 等级 | 缓解 |
|---|---|---|
| 自动修复越界（修改 tracked files） | 中 | 修复白名单固定，仅 ai-context-bootstrap 两类 |
| 退出码语义混乱 | 低 | 严格对齐 openspec validate (0/1/2/3) |
| 子进程 fork 失败容错 | 中 | try/except 包裹 + 报告记录失败 |
| 报告 schema 版本不兼容 | 低 | version 字段 const=1，bump version 强制迁移 |
| 与 `rdd-env-check` 职责重叠 | 中 | 文档明确分工：rdd-env-check = phase 内嵌快速；env-bootstrap = 用户主动全流程 |

## Acceptance

### AC-1: Skill 入口完整性

- [ ] `skills/rdd-env-bootstrap/SKILL.md` 存在, 含完整 frontmatter (name/description/license/compatibility/metadata/role)
- [ ] `role.boundaries.owns` 列出 `.rddf/state/.env-bootstrap-report.json`
- [ ] `role.boundaries.not_owns` 列出 `_lib/cli/setup_cmd.py` + `skills/rdd-doctor/`
- [ ] 顶层 description 含 3 个 invoke when 触发条件 + default 行为 + boundary 声明
- [ ] SKILL.md 引用 Phase 1-4 详细文档 (`references/fix-decisions.md`)
- [ ] **skill 入口绑定 `owner_opencode_session_id` (per ADR-0017), 失败友好降级** (reviewer 追加)

### AC-2: CLI 子命令注册

- [ ] `rddf env-bootstrap --help` 输出一致 (与 setup/doctor 风格对齐)
- [ ] `rddf env-bootstrap --check-only` 跑 Phase 1-2, 不写任何文件
- [ ] `rddf env-bootstrap` 默认 Phase 1-4, Phase 4 每个 fix prompt
- [ ] `rddf env-bootstrap --auto-fix --yes` Phase 4 无 prompt
- [ ] `rddf env-bootstrap --target /path/to/project` 支持任意路径
- [ ] 在非 rdd-workflow 项目目录友好退出 (exit 3)

### AC-3: `_NO_STATE_CHECK` 扩展

- [ ] `_lib/cli/__main__.py` 把 `env-bootstrap` 加入 `_NO_STATE_CHECK`
- [ ] 单元测试覆盖: 在非 rdd-workflow 目录调用不报"未初始化"错误

### AC-4: Phase 1 检测准确性

- [ ] 检测 `.git/` 存在 (git 仓库)
- [ ] 检测 `.rddf/` 存在 (已初始化)
- [ ] 检测项目语言 (Python `setup.py`/`pyproject.toml`, Node `package.json`, Go `go.mod`, Rust `Cargo.toml`)
- [ ] 检测 `rddf` CLI 可用 + 版本 (`which rddf` + `rddf --version`)
- [ ] 检测目标项目 AI 配置文件 (.cursorrules / CLAUDE.md / AGENTS.md / .clinerules / .continue/rules/ + .github/copilot-instructions.md)
- [ ] 检测全部 < 200ms

### AC-5: Phase 2 诊断集成

- [ ] 调用 `rddf doctor --json` 成功
- [ ] 解析 JSON, 按 category 过滤
- [ ] 分类: auto-fixable / user-decision / manual-only
- [ ] Phase 1 检测有缓存时跳过重复扫盘

### AC-6: Phase 4 自动修复白名单

- [ ] 仅 [auto-fixable] 项可执行 (ai-context-bootstrap 部署 + 块陈旧刷新)
- [ ] 任何不在白名单的 fix prompt 时默认 [N] 跳过
- [ ] 每个 fix fork 子进程, 失败容错
- [ ] 报告 `phase_4_guided_fix.executed[]` 记录每次 fix 状态
- [ ] **实施前必须验证 `rddf setup ai-context --yes` 幂等 (重复跑结果一致, AGENTS.md 块不被覆盖丢失)** (reviewer 追加)

### AC-7: 报告 schema

- [ ] `.rddf/state/.env-bootstrap-report.json` 落盘
- [ ] schema 版本 `version: 1`
- [ ] 字段完整: phase_1_detection / phase_2_diagnosis / phase_3_init_suggestion / phase_4_guided_fix / exit_code
- [ ] 可重入 (v1 报告已存在时复用 phase_1)

### AC-8: 退出码语义 (对齐 openspec validate)

- [ ] 0 = 全部健康 + 所有 fix 成功
- [ ] 1 = 有 WARNING 但 fix 已自动执行
- [ ] 2 = 有 CRITICAL 或有 manual-only 未处理
- [ ] 3 = 环境错误 (rddf 未装 / cwd 非项目)

### AC-9: 测试覆盖

- [ ] `tests/integration/test_env_bootstrap.bats` (≥ 8 cases)
  - help 输出
  - check-only 不写文件
  - 默认模式 prompt 行为
  - auto-fix 模式无 prompt
  - 非 rdd-workflow 目录友好退出
  - 白名单决策 (auto-fixable 修复)
  - 报告 schema 落盘
  - 退出码语义
- [ ] `tests/unit/test_env_bootstrap.py` (≥ 5 cases)
  - Phase 1 检测函数纯函数化测试
  - 修复决策表纯函数化测试
  - 报告生成纯函数化测试
  - 子进程 fork 边界
  - 错误处理路径

### AC-10: 全量回归

- [ ] 跑 `./test.sh --full --regression` 无新增失败
- [ ] 2 个 pre-existing 失败 (brainstorm-hardgate + v3-rename-guard) 仍仅在 KNOWN_FAILURES.txt

### AC-11: 文档同步

- [ ] `README.md` 添加 `rdd-env-bootstrap` 到 27 技能列表 (变 28)
- [ ] `AGENTS.md` 关键约定段添加新 skill 引用
- [ ] 新增 ADR-0053 (env-bootstrap 编排层架构)

## 后续改进 (Out of Scope, 留待 P2+)

- `--fix-rules <yaml>` 用户自定义白名单
- 跨项目 federation (多 project_root 串联)
- 修复历史记录 (`.rddf/state/.env-bootstrap-history.jsonl`)
- 集成 `rddf-hub-bootstrap` (Hub repo 引导式初始化)
- `rdd-env-bootstrap --check-only --json` 输出供 CI 消费