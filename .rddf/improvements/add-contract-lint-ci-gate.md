# add-contract-lint-ci-gate

**优先级**: P1 | **来源**: 架构差距分析 ADR-0030 / multi-project-ai-collaborative-development Step 5
**阶段**: v2.2 | **分类**: cross-repo-federation | **类型**: feature
**依赖 ADR**: ADR-0030, add-rdd-hub-cross-repo-federation
**状态**: 已批准 (2026-08-15)

## 架构依据

**背景**

当前 rdd-workflow 没有 **契约一致性校验**机制：跨项目接口（OpenAPI / Protobuf / Schema）变更后，无法自动检测 Spoke 仓库的实现是否与 Hub 契约一致。这导致：

1. Spoke A 修改了实现但未同步 Hub 契约 → 契约漂移
2. Hub 契约更新但 Spoke 仓库未拉取 → 集成失败
3. AI 自动生成的代码与现有契约不一致 → 类型错误

**触发场景**

- 跨项目 RFC 批准后，Hub `contracts/auth-v2.yaml` 更新，但 Spoke 仓库 A 的实际实现未跟进
- Spoke 仓库 B 在 guide-ship 阶段准备合并代码时，未校验与 Hub 契约一致性

**已有机制（集成而非替换）**

- `execute` step 7 已有 L2 上报通道（可扩展为契约 lint 上报）
- `STRICT_DESIGN_GATE=yes` 已有门控升级模式
- `skills/_lib/validate_delta_targets.py` 已有 schema 校验模式

## 范围

**In Scope**:

- 新增 `rddf contract-check` 命令：使用 OpenAPI Diff 校验本地实现与 Hub 契约一致性
- 在 Hub 仓库部署 `.github/workflows/contract-lint.yml`：当 `contracts/` 变更时自动通知 Spoke
- 在 Spoke 仓库 `guide-ship` 阶段增加契约 lint 检查（默认 warn，`STRICT_CONTRACT_GATE=yes` 升级为硬阻断）
- 新增 `skills/_lib/contract_diff.py`：封装 OpenAPI Diff 调用 + 结果格式化
- 新增 `docs/contract-conventions.md`：定义 Spoke 仓库契约实现规范

**Out Scope**:

- **不实现** Hub CI 详细配置（属于 Hub Repo 自身）
- **不集成** 非 OpenAPI 格式（仅 OpenAPI 3.0+ / Protobuf 3+）
- **不替代** Spoke 仓库自身 CI（契约 lint 是补充，不是替代）

## 关键场景

### 场景 1：Spoke 仓库本地校验

```bash
# 在 Spoke 仓库执行
$ rddf contract-check --contract auth-v2.yaml --impl src/api/auth.py
# 实际输出：
📋 契约校验报告: auth-v2.yaml vs src/api/auth.py
   
   ✅ 接口路径一致 (12 个端点)
   ⚠️ 请求 schema 差异：
      - POST /v2/login: 缺少 device_fingerprint 字段 (Hub 要求)
      - POST /v2/refresh: 返回缺少 expires_in 字段
   ❌ 响应 schema 严重不一致：
      - GET /v2/user/profile: Hub 定义包含 email_verified 字段，本地未实现
   
   总结: 1 严重 / 2 警告
   决策: STRICT_CONTRACT_GATE=yes → ❌ 阻塞 ship 阶段
```

### 场景 2：Hub 端契约变更通知

```yaml
# .github/workflows/contract-lint.yml (Hub 仓库)
name: Contract Lint & Notify
on:
  push:
    branches: [main]
    paths: ['contracts/**']

jobs:
  notify-spokes:
    runs-on: ubuntu-latest
    steps:
      - name: Detect changed contracts
        run: |
          CHANGED=$(git diff --name-only HEAD~1 HEAD contracts/)
          echo "$CHANGED" > changed_contracts.txt
      - name: Notify Spoke Repos
        uses: actions/github-script@v7
        with:
          script: |
            const contracts = require('fs').readFileSync('changed_contracts.txt', 'utf8');
            // 解析受影响 Spoke 仓库，创建 sync Issue
            for (const repo of spokes) {
              await github.rest.issues.create({
                owner: repo.owner, repo: repo.name,
                title: `[Hub] Contract sync required: ${contracts}`,
                body: `Hub 仓库 contracts/ 目录变更，请执行 rddf sync-hub`,
                labels: ['cross-repo', 'contract-sync']
              });
            }
```

### 场景 3：CI 集成（Spoke 仓库）

```yaml
# .github/workflows/contract-lint.yml (Spoke 仓库)
name: Contract Lint
on: [pull_request]

jobs:
  contract-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install rdd-workflow
        run: pip install rdd-workflow
      - name: Run contract check
        run: rddf contract-check --all --strict
        env:
          RDDF_HUB_OWNER: ${{ secrets.HUB_OWNER }}
          RDDF_HUB_TOKEN: ${{ secrets.HUB_TOKEN }}
```

## 技术约束

1. **格式支持**：仅 OpenAPI 3.0+ / Protobuf 3+（其他格式后续 ADR 评估）
2. **差异分级**：Breaking-Change / Non-Breaking / New-Contract 三级
3. **缓存友好**：契约版本缓存在 `.rddf/state/.contract-cache.json`
4. **离线模式**：Hub 不可达时使用本地缓存 + 警告（不阻断）

## 验收标准

- [ ] `rddf contract-check --contract X --impl Y` 输出标准化报告（JSON / Markdown）
- [ ] Hub CI 自动检测 `contracts/` 变更并通知 Spoke
- [ ] Spoke CI 集成 `rddf contract-check` 在 PR 时自动校验
- [ ] `STRICT_CONTRACT_GATE=yes` 时 Breaking-Change 阻断 ship
- [ ] `--strict` / `--warn-only` / `--diff-only` 三个 mode 工作正常
- [ ] `.contract-cache.json` 缓存契约版本 + SHA
- [ ] 单元测试覆盖 5 个关键路径（OpenAPI / Protobuf / cache-hit / hub-offline / breaking-detect）
- [ ] README §跨项目协同 章节增加 CI 集成示例
