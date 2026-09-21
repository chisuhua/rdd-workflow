# ADR-0052: Layer 0 渐进式上下文注入架构

> **状态**: 已采纳
> **日期**: 2026-09-21
> **决策者**: sisyphus

## Context

`fix-skill-post-install-discoverability` 提案在对话中经历了一次**根本性语义纠正**：之前错误地把 Layer 0（AI 配置文件上下文块）部署挂载在 `install.sh --spoke-init` 下，而 `install.sh` 的真实语义是**开发者一次性安装 rdd-workflow 工具**，不是"在每个用户项目里配置 rdd-workflow"。

这暴露了三重鸿沟：
1. **Skill Layer 1 自包含失效** — SKILL.md 引用 docs/ 目录在 install.sh 后必然 404
2. **第三方项目 AI agent 不可发现** — AI 代理不知道 rdd-workflow 已安装
3. **rdd-workflow 核心用法无法触达** — 核心概念文档不随工具分发

本 ADR 记录修复这三重鸿沟的架构决策：采用**四层渐进式上下文注入架构**（Layer 0→1→2→3），并明确 install.sh / rddf setup / rdd-doctor 三层分工。

**架构依据**:
- `ADR-0021 §2`: per-skill sentinel 模式
- `add-spoke-system-prompt-injection` 提案: spoke-system-prompt-injection 的 sentinel 追加模式
- `ADR-0030`: Hub-Spoke 联邦架构

## Decision

我们采用**四层渐进式上下文注入架构**，以 `rddf setup ai-context` 作为 Layer 0 部署的唯⼀入口（而非 `install.sh`），`install.sh` 保持纯粹的开发者工具安装职责。

### 三层工具分工

| 层 | 工具 | 触发 | 生命周期 |
|---|---|---|---|
| **工具安装**（开发者侧） | `bash install.sh [--global]` | 开发者装环境时一次性 | 一次 |
| **项目配置 Layer 0**（用户侧） | `rddf setup ai-context` | 每个用户项目首次使用 rdd-workflow 时 | 每项目一次 |
| **项目诊断** | `rddf doctor --category ai-context-bootstrap` | 任何时候可主动检查 | 按需 |
| **Skill Layer 1**（用户调用时） | SKILL.md 自包含 | 用户调 `skill_use("guide")` 等 | 每次 |
| **docs/ 分发**（工具内部 docstring） | `install.sh --with-docs`（默认 OFF） | 工具安装时可选 | 一次 |

**核心决策**: `install.sh` 是开发者侧工具安装，不嵌入 Layer 0 部署。用户侧项目配置通过独立的 `rddf setup ai-context` CLI 命令完成。此分工不可合并。

### Layer 0 块纪律

1. **≤30 行**（约 400-600 tokens/文件），避免污染 AI 配置文件
2. **5 段结构**：身份声明 → 推荐入口 → 核心流程 → 旁路规则 → 自助诊断
3. **SSOT 模板**：`_lib/templates/layer0_rdd_workflow_usage.md` 是唯⼀来源，任何部署路径引用同一文本
4. **检测顺序**：`AGENTS.md` → `.cursorrules` → `CLAUDE.md` → `.clinerules` → `.continue/rules/*.md` → `.github/copilot-instructions.md`
5. **都追加**：多个 AI 配置文件并存时每个都追加（牺牲 token 换多工具覆盖）
6. **都不存在** → 创建 `AGENTS.md`

### Sentinel 命名约定

所有 rdd-workflow 注入的配置块使用以下 sentinel 格式：

```
<!-- RDD-WORKFLOW-*-START -->
<!-- RDD-WORKFLOW-*-END -->
```

- 星号位置填入大写功能标识（如 `CORE-USAGE`、`HUB-USAGE`）
- 幂等：重复运行检测 sentinel 不重复注入
- 扩展：增量需求走新 sentinel 块维度，不叠 Layer 层数

### 影响范围

- **In Scope**: `_lib/cli/setup_cmd.py`（新 CLI 命令）、`_lib/templates/layer0_*.md`（SSOT 模板）、install.sh `--with-docs` flag、SKILL.md Layer 1 自包含
- **Out Scope**: 不修改 `_lib/` 既有模块、不修改 spoke-system-prompt-injection 代码、不修改 226 个现有 improvement

### 备选方案

| 备选 | 理由 |
|------|------|
| `install.sh --spoke-init` 部署 Layer 0 | **拒绝** — 混淆工具安装与项目配置职责（语义纠正前方案） |
| 创建独立 skill `rdd-workflow-bootstrap` | **拒绝** — 避免 skill 数量膨胀；用 CLI 命令更可发现 |
| Per-tool Layer 0 块自定义 | **拒绝** — SSOT 原则，统一附加到任何 AI 配置文件 |
| 引入 dismissed 状态记忆 | **拒绝** — 删除即重置是最简可预测语义，过度设计 |

## Consequences

### 正面

- 清晰的三层分工：install.sh（工具安装）/ rddf setup（项目配置）/ rdd-doctor（诊断），职责不重叠
- SKILL.md Layer 1 自包含后 install.sh 零 404
- Layer 0 协议块 ≤30 行不对 AI 配置文件造成负担

### 负面 / 风险

- 用户需要额外步骤 `rddf setup ai-context`（通过 `rddf init` hint 引导缓解）
- 多工具并存时重复内容（约 1800 tokens 最坏情况，占模型 context <1%）
- `--with-docs` 默认 OFF 导致需要显式开启才能获得完整架构文档

### 后续待办

- [ ] Layer 0 SSOT 模板 `_lib/templates/layer0_rdd_workflow_usage.md` 创建
- [ ] `rddf setup ai-context` CLI 子命令实现
- [ ] install.sh `--with-docs` flag 实现
- [ ] SKILL.md Layer 1 自包含重写（2 个 SKILL.md）
- [ ] docs-consistency 静态检查集成到 rdd-doctor

## References

- `fix-skill-post-install-discoverability` proposal — 本 ADR 的驱动提案
- `docs/architecture/layer-0-progressive-context.md` — 渐进式上下文架构完整设计文档
- `skills/spoke-system-prompt-injection/SKILL.md` — sentinel 追加模式参考实现
- `skills/rdd-doctor/SKILL.md` — 诊断 category 注册入口