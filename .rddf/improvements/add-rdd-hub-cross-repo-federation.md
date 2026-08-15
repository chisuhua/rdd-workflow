# add-rdd-hub-cross-repo-federation

**优先级**: P1 | **来源**: 架构差距分析 ADR-0030 / multi-project-ai-collaborative-development Step 2
**阶段**: v2.2 | **分类**: cross-repo-federation | **类型**: feature
**依赖 ADR**: ADR-0030 (Hub-and-Spoke 联邦协同架构)
**状态**: 已批准 (2026-08-15)

## 架构依据

**背景**

当前 `rddf report-issue` 是**单向 / 后置**通道：仅在执行失败（flow-bug / gate-failure / phase-crash）时上报，**不是协同工具**。当跨项目 RFC 流程在 ADR-0030 中确立后，需要扩展 L2 上报为「双向协同通道」：

1. 上行通道：`rddf report-issue --category=rfc` 在 Hub 创建 `[RFC]` Issue
2. 下行通道：`rddf sync-hub` 拉取 Hub `contracts/` 到本地 openspec/
3. 监听通道：`rddf watch-hub` 监听 Hub Issue Status 变化 → 触发本地 design-done 解除挂起

**架构依据（引用 ADR-0030 §Decision）**

> Hub-and-Spoke 模型下，Hub Repo 是跨项目契约 / 全局决策 / 协同看板的 SSOT。L2 上报通道从「单向上报」升级为「双向协同通道」是 Step 2 的核心。

**已有能力（不重复造轮子）**

- `skills/execute/scripts/execute_step7.py` — 当前 L2 上报执行器（含 `RDDF_REPORT_*` env vars）
- `skills/_lib/gh_repo_detect.py` — GitHub 仓库自动检测
- `README §L2 上报 opt-in` — 三重 opt-in 文档（`RDDF_REPORT_ENABLED` / `RDDF_REPORT_AUTO_SUBMIT` / `RDDF_REPORT_SUBMIT_CATEGORIES`）

## 范围

**In Scope**:

- 扩展 `rddf report-issue` 接受 `--category=rfc` 类型
- 新增 `rddf sync-hub <contract_path>` 命令：从 Hub `rdd-hub/contracts/` 拉取到本地 `openspec/`
- 新增 `rddf watch-hub --once --owner=<org/rdd-hub>` 命令：执行一次状态轮询；由 cron/CI 调度，不在 CLI 内维护长驻 daemon
- 扩展 `.rddf/state/.cross-repo-pending.json`：记录本地挂起的 Hub Issue 链接 + 期望解除条件
- 升级现有 L2 上报 env vars 增加 `--rfc` 模式选项

**Out Scope**:

- **不修改** Hub Repo 自身创建脚本（属于 `add-rdd-hub-bootstrap` 后续提案）
- **不集成** MCP 协议（属于 `add-mcp-cross-repo-protocol` 提案）
- **不实现** 跨项目依赖编排（属于 `add-cross-repo-deps-orchestration` 提案）

## 关键场景

### 场景 1：Spoke 仓库 AI 发起 RFC

```bash
# 在 Spoke 仓库（repo-frontend）
$ RDDF_REPORT_GH_REPO=org/rdd-hub rddf report-issue \
    --category=rfc \
    --title "[RFC] 重构用户鉴权流程 (Auth V2)" \
    --stakeholders "org/repo-backend,org/repo-data" \
    --gate "Design-Gate" \
    --contract-impact "Breaking-Change"
# → 在 Hub 创建 Issue，Status=📢 RFC
# → 在本地 .rddf/state/.cross-repo-pending.json 记录 Issue 链接
# → design-done 门控自动挂起
```

### 场景 2：拉取 Hub 最新契约

```bash
# 任意 Spoke 仓库
$ rddf sync-hub --contract auth-v2.yaml
# → 从 rdd-hub/contracts/auth-v2.yaml 拉取最新版本
# → 更新本地 openspec/specs/auth-v2/spec.md
# → 触发 design-done 门控重检
```

### 场景 3：监听 Hub 状态变化

```bash
# 一次性轮询；由 cron/CI 调度（不在 CLI 内维护长驻 daemon）
$ rddf watch-hub --once --owner=org/rdd-hub --filter "Stakeholders:[email protected]"
# → 当指派给自己的 Issue 状态变为 ✅ Approved
# → 自动执行本地 approve_proposal.sh 解除挂起
```

## 技术约束

1. **幂等性**：`rddf sync-hub` 必须幂等（同一文件重复拉取不应产生 diff）
2. **离线模式**：Hub 网络不可达时，应回退到本地缓存 + 警告，不阻断流程
3. **权限最小**：只读 GitHub token 即可运行 `sync-hub` / `watch-hub`；`report-issue` 需要写权限
4. **GitHub API 速率限制**：遵守 5000 req/hour 限制；批量操作使用 GraphQL

## 验收标准

- [ ] `rddf report-issue --category=rfc` 成功在 Hub 创建 `[RFC]` Issue
- [ ] Hub Issue 自动关联到 `RDD Cross-Repo Sync` Project V2，并设置正确字段
- [ ] `.rddf/state/.cross-repo-pending.json` 正确记录挂起状态
- [ ] design-done 门控检测到 Hub Issue 未 Approved 时硬阻断
- [ ] `rddf sync-hub <contract>` 拉取文件后 `git diff` 仅显示目标文件变化
- [ ] `rddf watch-hub --once` 在单次轮询中正确检测 Issue Status，并由 cron/CI 以 ≤5 分钟间隔调度后解除本地挂起
- [ ] 所有命令支持 `--dry-run` 模式
- [ ] README §跨项目协同 章节更新文档
