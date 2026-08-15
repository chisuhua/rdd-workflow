# add-spoke-system-prompt-injection

**优先级**: P1 | **来源**: 架构差距分析 ADR-0030 / multi-project-ai-collaborative-development §3 差距 #8 + Step 3.5
**阶段**: v2.2 | **分类**: cross-repo-federation | **类型**: feature
**依赖 ADR**: ADR-0030, add-rdd-hub-bootstrap, add-mcp-cross-repo-protocol
**关联差距**: multi-project-ai-collaborative-development §3 差距 #8
**状态**: 已批准 (2026-08-15)

## 架构依据

**背景**

跨项目协同协议 (`rdd-hub/docs/mcp-protocols.md`) 仅靠**人类文档**无法强制执行：Spoke AI（Claude / Cursor / Continue）默认不知道 Hub 存在、不知道如何通过 MCP 发起 RFC、不知道何时使用 `--hub-issue` 参数。必须通过**强制系统提示词注入**确保每个 Spoke 仓库的 AI 环境都遵循 Hub 协议。

**触发场景**：
- 新接入 Spoke 仓库的 AI 不知道 Hub 存在 → 跨项目变更直接在本地闭环
- Spoke AI 不知道 Hub Issue 状态如何监听 → 错过解除 design-done 挂起的时机
- Spoke AI 误用 `--auto-accept` → 跨项目提案自动批准（即便有 `add-strict-human-approval` 兜底）

**已有能力（集成而非替换）**：
- `install.sh` — 全局 / 项目安装脚本
- `add-rdd-hub-bootstrap`（Step 1）— Hub 仓库初始化
- `add-mcp-cross-repo-protocol`（Step 3）— MCP 协议实现

**为何 P1**：
- 协议文档有了但没人读 → AI 注入是唯一的可靠入口
- 一次性模板开发（~1-2 天），后续只需要维护
- 缺失时整个 Hub-and-Spoke 架构仍可工作，但容易被 AI 误操作

**架构依据**（引用 ADR-0030 §Decision）：
> 在 Hub 仓库创建 `RDD Cross-Repo Sync` Project，配置多维字段替代点对点 Source/Target 模型。

## 范围

**In Scope**：

- 新增 `skills/spoke-system-prompt-injection/SKILL.md` — 强制注入 skill
- 新增 `skills/spoke-system-prompt-injection/templates/` — 5 种 AI 工具模板
  - `.cursorrules.cross-repo-hub` — Cursor 工具
  - `.clinerules.cross-repo-hub` — Cline 工具
  - `.continue/rules/cross-repo-hub.md` — Continue 工具
  - `.github/copilot-instructions.md` — GitHub Copilot
  - `CLAUDE.md` — Claude Code
- 新增 `skills/spoke-system-prompt-injection/scripts/deploy.sh` — 一键部署脚本
  - 检测目标 AI 工具（通过 `find` 查找配置文件）
  - 注入对应模板（合并或创建）
  - 支持 `--uninstall` 回滚
- 新增 `skills/spoke-system-prompt-injection/inject.md` — 模板内容
  - 联邦协同协议（核心原则）
  - RFC 发起流程（参照 Step 2）
  - RFC 审查流程（响应 Stakeholders）
  - 契约同步与解除挂起
  - 禁止事项（AI 不能跨项目自动批准）
- 新增 `install.sh --spoke-init` 子命令：将部署脚本接入主安装流程
- 新增 `docs/spoke-system-prompt.md` — 使用文档

**Out Scope**：

- **不覆盖** MCP 协议底层实现（属于 `add-mcp-cross-repo-protocol`）
- **不修改** Hub 仓库自身（属于 `add-rdd-hub-bootstrap`）
- **不强制**所有 AI 工具（仅支持上述 5 种主流工具）

## 关键场景

### 场景 1：新 Spoke 仓库接入

```bash
# 人类架构师在 repo-frontend 仓库执行
$ skill_use("spoke-system-prompt-injection")
$ deploy.sh --tools cursor,claude
# 实际行为：
🔧 检测 AI 工具配置：
   - .cursorrules          ✅ 找到
   - CLAUDE.md             ✅ 找到
   - .clinerules           ❌ 未找到（跳过）
   
📝 部署协议模板：
   - 追加到 .cursorrules       ✅
   - 追加到 CLAUDE.md          ✅
   
⚠️  请 commit 这些修改并通知团队成员重启 AI 工具
```

### 场景 2：Spoke AI 启动时识别 Hub 协议

```text
# Claude Code 启动时（注入 CLAUDE.md 后）
你当前处于 Spoke 节点：org/repo-frontend
你的本地工作流受 rdd-workflow 状态机控制，但所有跨项目交互
必须严格遵守 Hub 协议。

跨域路由判断 (Design 阶段)
当你在 guide-design 阶段审查 .rddf/improvements/<name>.md 时：
- 如果提案仅影响本仓库，正常执行本地 approve_proposal.sh
- 如果提案涉及修改跨项目接口、数据模型或强依赖其他仓库，
  绝对禁止在本地直接批准。必须触发【RFC 发起流程】

RFC 发起流程 (作为 Initiator)
使用 GitHub MCP 在 rdd-hub 仓库创建 Issue...
```

### 场景 3：uninstall 回滚

```bash
$ deploy.sh --uninstall --tools cursor
# 实际行为：
🧹 卸载 Hub 协议注入：
   - 从 .cursorrules 移除相关段落 ✅
   - 备份原文件到 .cursorrules.bak.YYYYMMDD ✅
```

## 技术约束

1. **幂等性**：重复运行结果一致（追加模式检测标记 `<!-- RDD-HUB-PROTOCOL-START -->`）
2. **备份机制**：修改前自动备份原文件
3. **工具检测**：通过 `find` 查找配置文件，不强制依赖特定工具
4. **模板版本**：所有模板引用相同协议版本（`protocol_version: 1.0`）
5. **可扩展性**：新增 AI 工具支持仅需添加新模板文件

## 验收标准

- [ ] `deploy.sh --tools cursor` 成功在 `.cursorrules` 追加 Hub 协议
- [ ] 5 种 AI 工具模板全部覆盖（Cursor / Cline / Continue / Copilot / Claude）
- [ ] 重复运行检测到标记后不重复注入
- [ ] `--uninstall` 成功回滚并保留备份
- [ ] `tests/integration/test_spoke_injection.bats` 覆盖 5 个关键路径（deploy / idempotent / multi-tool / uninstall / backup）
- [ ] `install.sh --spoke-init` 在新项目安装时自动运行
- [ ] 注入内容包含 RFC 发起 / 审查 / 同步 3 个核心流程
- [ ] 注入内容明确"AI 不能跨项目自动批准"
- [ ] README §跨项目协同 章节增加 Spoke 接入指南
