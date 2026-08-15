# add-strict-human-approval-for-cross-repo-changes

**优先级**: P1 | **来源**: 架构差距分析 ADR-0030 / multi-project-ai-collaborative-development Step 1.5
**阶段**: v2.2 | **分类**: cross-repo-federation | **类型**: security-fix
**依赖 ADR**: ADR-0030, ADR-0025 (design 阶段提案创建), ADR-0027 (持续演进反馈环 L2 上报)
**关联差距**: multi-project-ai-collaborative-development §3 差距 #5
**状态**: 已批准 (2026-08-15)

## 架构依据

**背景**

跨项目场景下 AI 误操作代价极高：一旦 AI 自动批准了一个错误的 RFC，可能导致多个 Spoke 仓库同步错误。当前 `approve_proposal.sh` **可被 AI 自动执行**（当 `SKIP_DESIGN_HANDOFF` 或 `STRICT_DESIGN_GATE` 未启用时），缺乏强制人类决策点。

**关键风险（来自差距分析 §3 差距 #5）**

> AI 直接决策：当前 approve_proposal.sh 可被 AI 自动执行，没有强制人类兜底

**触发场景**

1. AI 在 guide-design 阶段发现提案涉及跨项目契约 → 自动调用 `approve_proposal.sh` → 多个 Spoke 同步污染
2. AI 误判 RFC Status（如将「已 Review」识别为「Approved」）→ 解除本地挂起 → 错误地进入 plan 阶段
3. AI 在没有人类审查的情况下修改 Hub `contracts/` → 跨项目契约不一致

**已有机制（加固而非替换）**

- `STRICT_DESIGN_GATE=yes` — 当前已有的严格门控（ADR-0025）
- `SKIP_DESIGN_HANDOFF=yes` — 当前可绕过门控（需保留为紧急逃生口）
- `RDDF_PROPOSAL_AUTO_ACCEPT=no` — 当前已有的"AI 不自动确认"语义（ADR-0025 D1 Step 2）

## 范围

**In Scope**:

- 升级 `approve_proposal.sh`：检测 `**分类**: cross-repo-federation` 时，**硬阻断 AI 自动批准**
- 升级 `STRICT_DESIGN_GATE=yes`：当检测到 Hub Issue 未 Approved 时，禁止 design-done
- 新增 `RDDF_REQUIRE_HUB_APPROVAL=yes` 环境变量：显式启用跨项目强制门控（无逃生口）
- 升级 `skills/guide-design/scripts/design_content_review.sh`：新增 cross-repo 类别审查
- 升级 `.openspec.yaml` schema：新增 `cross_repo_review.required` 字段
- 新增 `docs/adr/ADR-0031-human-in-loop-cross-repo.md`（紧随 ADR-0030 之后）：明确"跨项目 RFC 必须人类决策"原则

**Out Scope**:

- **不修改** 单仓库 proposal 审批流程（保持现有 `y/N` 交互）
- **不创建** 新的交互模式（Human-in-Loop 节点类型不变，参考 ADR-0005）
- **不实现** Hub 端人类兜底（属于 Hub Repo 自身范围）

## 关键场景

### 场景 1：AI 尝试自动批准跨项目提案

```bash
# Spoke 仓库（repo-frontend），AI 执行
$ rddf approve-proposal cross-repo-auth-v2 --auto-accept
# 实际行为：
⛔ [STRICT] 提案 'cross-repo-auth-v2' 标记为 cross-repo-federation，
   AI 自动批准被硬阻断。
   需要在 Hub Issue (org/rdd-hub#42) 状态变为 ✅ Approved 后，
   由人类通过 'rddf approve-proposal cross-repo-auth-v2 --manual' 确认。
   
   exit code: 3 (cross-repo requires human approval)
```

### 场景 2：本地 design-done 检测 Hub 状态

```bash
# 在 Spoke 仓库执行 guide-design Phase 4 门控
$ rddf design-gate-check
# 实际行为：
🛡️  检测到 1 个挂起的 cross-repo 提案：
   - cross-repo-auth-v2 (Hub Issue #42, Status: 📢 RFC)
   
   设置 STRICT_DESIGN_GATE=yes 时硬阻断 design-done。
   当前设置: STRICT_DESIGN_GATE=yes
   决策: ❌ design-done 失败，需等待 Hub 审批
   
   exit code: 1
```

### 场景 3：人类手动确认（强制流程）

```bash
# 人类架构师在 Hub Issue 状态变为 ✅ Approved 后执行（交互式 prompt）
$ rddf approve-proposal cross-repo-auth-v2 --manual \
    --hub-issue "org/rdd-hub#42"
🔐 检测到 cross-repo 提案,需要人工确认
   请输入你的 GitHub 用户名 (会记录到 audit log):
   > alice
   请确认决策: [y/N]: y
   
# 实际行为：
✅ 提案 'cross-repo-auth-v2' 已被 alice 手动确认
   Hub Issue: org/rdd-hub#42 (Status: ✅ Approved)
   本地 design-done 门控解除，进入 plan 阶段
```

## 技术约束

1. **不可绕过**：除 Hub 端 `STRICT_HUB_APPROVAL=no` 由 Hub 维护者裁决（需 PR 审计）外，**无任何 Spoke 端绕过路径**（P1 安全门控不允许逃生口）
2. **可审计**：所有 cross-repo 决策记录到 `.rddf/state/.cross-repo-audit.jsonl`
3. **同步性**：本地决策必须与 Hub Issue 状态一致（避免本地"Approved"但 Hub 仍"RFC"）
4. **交互式 prompt**：`--approved-by` 改为 stdin 提示（避免 process listing 泄露）
5. **Hub Issue 状态主动校验**：本地批准前必须重新拉取 Hub Issue 状态（防 race condition）

## 验收标准

- [ ] `approve-proposal --auto-accept` 对 cross-repo 提案硬阻断（exit code 3）
- [ ] `STRICT_DESIGN_GATE=yes` + Hub Issue 未 Approved → design-done 失败
- [ ] `RDDF_REQUIRE_HUB_APPROVAL=yes` 显式启用强制门控
- [ ] `--manual` 交互式 prompt 记录人类决策者（GitHub username）到 audit log
- [ ] `.cross-repo-audit.jsonl` 包含 timestamp / proposal_name / hub_issue / approver / decision
- [ ] 本地批准前必须重新拉取 Hub Issue 状态（防 race condition）
- [ ] 单元测试覆盖 5 个关键路径（auto-block / gate-detect / manual-confirm / audit-write / hub-state-recheck）
- [ ] README §跨项目协同 章节明确"AI 不能跨项目自动批准"原则
- [ ] **无 Spoke 端 bypass 路径**（hub 端 `STRICT_HUB_APPROVAL=no` 需 PR 审计）
