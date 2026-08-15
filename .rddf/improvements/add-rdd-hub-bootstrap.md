# add-rdd-hub-bootstrap

**优先级**: P0 | **来源**: 架构差距分析 ADR-0030 / multi-project-ai-collaborative-development Step 1
**阶段**: v2.2 | **分类**: cross-repo-federation | **类型**: infrastructure
**依赖 ADR**: ADR-0030 (Hub-and-Spoke 联邦协同架构)
**阻塞**: 所有其他 5 个 Hub-and-Spoke 提案（Step 2-6）
**状态**: 已批准 (2026-08-15)

## 架构依据

**背景**

ADR-0030 确立 Hub-and-Spoke 联邦架构后，**所有 5 个实现细节提案（Step 2-6）都依赖一个独立的 Hub 仓库 `rdd-hub` 存在**。但差距分析 §4 Step 1 明确指出："创建独立仓库 `rdd-hub`，配置 GitHub Projects V2 看板"——这本身就是一个需要单独实施的工程任务，没有相应的改进提案。

**本提案填补缺失**：提供 `rdd-hub` 仓库的初始化脚本、目录结构模板、Projects V2 看板配置、CI 自动化脚手架。

**为何 P0**（不是 P1）：
- 这是阻断性前置依赖，无此仓库则 Step 2-6 全无基础
- 一次性初始化工作（~2-3 天脚本开发 + 1 天模板配置）
- 决策"是否要 Hub"已由 ADR-0030 完成，本提案只解决"如何创建"

**架构依据**（引用 ADR-0030 §Decision）：
> Hub Repo 是不存放任何业务代码的独立仓库；存放跨项目契约（OpenAPI / Schema）、全局架构决策（Global ADR）和协同看板。

**已有能力（集成而非替换）**：
- `skills/_lib/gh_repo_detect.py` — GitHub 仓库路径检测
- `skills/add-improve/scripts/from_issue.sh` — Issue 驱动创建（ADR-0029）
- `skills/propose/scripts/propose_change.py` — 变更创建流程
- `install.sh` — 项目 / 全局安装脚本

## 范围

**In Scope**：

- 新增 `skills/rdd-hub-bootstrap/SKILL.md` — 引导式初始化 skill
- 新增 `skills/rdd-hub-bootstrap/scripts/init_hub.sh` — 一键初始化脚本
  - 创建 GitHub 仓库 `rdd-hub`（Org 级）
  - 配置 GitHub Projects V2 看板（6 字段：Status / Initiator / Stakeholders / Review-Progress / RDD-Gate / Contract-Impact）
  - 部署 Hub 目录结构（contracts/ / global-adr/ / .github/workflows/ / docs/）
- 新增 `skills/rdd-hub-bootstrap/templates/contracts/` — 契约模板（OpenAPI 示例）
- 新增 `skills/rdd-hub-bootstrap/templates/workflows/` — GitHub Actions 模板
  - `contract-lint.yml` — 契约变更通知（占位，完整实现在 `add-contract-lint-ci-gate`）
  - `stale-rfc.yml` — Stale RFC 清理（占位）
- 新增 `skills/rdd-hub-bootstrap/templates/mcp-protocols.md` — MCP 协议文档模板
- 新增 `docs/rdd-hub-bootstrap.md` — 完整使用文档
- 新增 `tests/integration/test_rdd_hub_bootstrap.bats` — 集成测试（dry-run 模式）

**Out Scope**：

- **不实现** MCP Server 自身（属于 `add-mcp-cross-repo-protocol` 提案）
- **不集成** 跨项目 RFC 发起流程（属于 `add-rdd-hub-cross-repo-federation` 提案）
- **不部署** 契约 lint CI（属于 `add-contract-lint-ci-gate` 提案）
- **不创建** Spoke 端 System Prompt 注入（属于 `add-spoke-system-prompt-injection` 提案）

## 关键场景

### 场景 1：初次 Hub Repo 初始化（人类 + gh CLI）

```bash
# 1. 人类架构师在 GitHub Org 创建 rdd-hub 仓库（手动，需 Org 权限）
# 2. 在本地执行初始化 skill
$ skill_use("rdd-hub-bootstrap")
$ PROJECT_ROOT=. bash init_hub.sh --org "my-org" --repo "rdd-hub"
# 实际行为：
🔧 初始化 Hub Repo: my-org/rdd-hub
   
   📁 创建目录结构：
   - contracts/        ✅
   - global-adr/       ✅
   - docs/             ✅
   - .github/workflows/ ✅
   
   📋 配置 Projects V2 看板：
   - "RDD Cross-Repo Sync"  ✅
   - 6 字段配置        ✅
   
   ⚙️ 部署工作流模板：
   - contract-lint.yml (占位)   ✅
   - stale-rfc.yml (占位)       ✅
   
   ✅ 初始化完成。下一步：运行 'rddf sync-hub' 验证连接。
```

### 场景 2：Dry-run 模式（CI 测试）

```bash
$ bash init_hub.sh --dry-run --org "fake-org" --repo "fake-hub"
# 实际行为：
🧪 Dry-run 模式：跳过实际 API 调用
   
   预演操作：
   - 创建 GitHub repo my-org/rdd-hub
   - 创建 Projects V2 "RDD Cross-Repo Sync"
   - 配置 6 字段
   - 部署 2 个 workflow 模板
   
   ✅ Dry-run 成功，无实际变更
```

### 场景 3：复用现有 Hub Repo（幂等性）

```bash
$ bash init_hub.sh --org "my-org" --repo "rdd-hub"
# 实际行为：
⚠️  Hub Repo 已存在（my-org/rdd-hub）
   仅更新缺失的 workflow 模板（contract-lint.yml）
   跳过 Projects V2（已存在）
   ✅ 幂等更新完成
```

## 技术约束

1. **幂等性**：多次运行结果一致，不重复创建
2. **Dry-run 模式**：所有 destructive 操作必须支持 `--dry-run`
3. **权限最小**：仅需 Org 成员权限，不要求 Owner
4. **版本兼容**：gh CLI v2.0+ / GitHub API v3
5. **可审计**：所有初始化操作记录到 `rdd-hub-bootstrap.log`

## 验收标准

- [ ] `init_hub.sh --org my-org --repo rdd-hub` 成功创建仓库 + 6 字段 Project V2
- [ ] `--dry-run` 模式不实际调用 API
- [ ] 重复运行（existing repo）只更新缺失文件
- [ ] `tests/integration/test_rdd_hub_bootstrap.bats` 覆盖 5 个关键路径（create / idempotent / dry-run / fields-config / workflow-deploy）
- [ ] `docs/rdd-hub-bootstrap.md` 包含 step-by-step 截图 + 故障排除指南
- [ ] 初始化完成后 Hub Repo 可被 `rddf sync-hub` 正常访问
- [ ] 与 ADR-0029 (`add-improve --from-issue`) 兼容：Hub 创建的 RFC Issue 可直接导入
- [ ] README §跨项目协同 章节增加 Hub 自举命令示例
