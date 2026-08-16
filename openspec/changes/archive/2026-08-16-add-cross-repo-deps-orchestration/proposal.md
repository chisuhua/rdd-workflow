# add-cross-repo-deps-orchestration

## Why

**背景**

当前 `deps` 阶段（`skills/deps/SKILL.md`）生成的 `deps-analysis.json` / `iteration.json` 仅表达**单仓库内**的 change 依赖关系，无法表达跨仓库依赖：

- 仓库 A 的 change X 依赖仓库 B 的 change Y 才能合并
- 仓库 A 的 change X 是仓库 B 的契约消费者 → 必须先等 B 发布

**触发场景**

- repo-frontend 准备发布新特性，但需要 repo-backend 先发布 auth-v2 接口
- repo-data 等待 repo-infra 完成存储迁移才能开始数据导入
- 跨项目联合重构需要 N 个 Spoke 同步合并

**已有能力（扩展而非替换）**

- `skills/deps/SKILL.md` Step 1-6 — 单仓库依赖分析
- `manual_deps` 字段（ADR-0022） — 人工声明依赖
- `iteration.json` v6 — 当前单仓库 sprint 视图
- `add-proposal-deps-and-features` 历史提案 — proposal 层依赖建模

## What Changes

**In Scope**:

- 新增 `rddf deps cross-repo`：扫描多个 Spoke 仓库的 `iteration.json`，生成跨仓库依赖图
- 新增 `rddf hub issue --deps`：在 Hub 创建 `[Dependency]` Issue，指派给上游 Spoke
- 升级 `guide-plan` deps 阶段：识别跨仓库强依赖 → 自动挂起 plan-done 门控
- 升级 `iteration.json` schema（v7）：新增 `cross_repo_dependencies` 字段
- 新增 `skills/_lib/cross_repo_deps.py`：跨仓库依赖图算法

### 关键场景

### 场景 1：生成跨仓库依赖图

```bash
# 在 Hub 仓库或任意 Spoke 仓库执行
$ rddf deps cross-repo --spokes "org/repo-frontend,org/repo-backend,org/repo-data"
# 输出：
🌐 跨仓库依赖图（3 个 Spoke，扫描 18 个 changes）

📊 依赖矩阵：
| Spoke Change | 依赖 | 类型 |
|--------------|------|------|
| repo-frontend/auth-v2-impl | repo-backend/auth-v2-publish | strong |
| repo-data/migrate-imports | repo-infra/storage-v3 | weak |
| repo-frontend/checkout-v3 | (无) | independent |

🎯 推荐执行顺序（3 waves）：
  Wave 1 (并行): repo-infra/storage-v3, repo-frontend/checkout-v3
  Wave 2 (并行): repo-backend/auth-v2-publish
  Wave 3: repo-frontend/auth-v2-impl, repo-data/migrate-imports

📋 阻断报告：
  - repo-frontend/auth-v2-impl 被 repo-backend/auth-v2-publish 强依赖
  - 预计 5 天延迟（基于各 change ETA — 见下方"ETA 数据源"）
```

### ETA 数据源（明确估算依据）

跨仓库依赖图中的 `eta_days` 字段来自以下三级来源（按优先级）：

**Lv1 - 自动化（强优）**：
- 从各 Spoke 仓库的 `tasks.md` 自动计算
  - 读取未完成 checkbox 数量
  - 若存在历史速率缓存 `~/.rddf/state/.velocity-cache.json`（TTL 7 天），乘以历史平均速率
  - 公式：`eta_days = (unchecked_count * historical_avg_days_per_task)`
- 来源：`rddf estimate --change <name>`（参考 `rddf worktree` 模式）
- **降级规则**：velocity cache 缺失、过期或格式无效时，Lv1 返回 `null` 并自动回退 Lv2/Lv3；ETA 仅用于展示，不得作为唯一 blocking 条件

**Lv2 - 协议声明（中等）**：
- 从各 change 的 `openspec/changes/<name>/proposal.md` frontmatter 读取
  - 字段：`eta: "2026-09-15"` 或 `eta: "5d"`
- 维护者可手动覆盖

**Lv3 - 人工输入（fallback）**：
- `rddf deps cross-repo --set-eta "org/repo-backend/auth-v2-publish=5d"`
- 或 PR 评论：`@rddf eta: 5d`

**ETA 优先级**：`Lv1 > Lv2 > Lv3 > null`
- 缺失时显示 "ETA 未知（请补充）"，不用于 blocking 决策
- ETA 偏差 >50% 时触发警告（提示更新速率缓存）

**审计**：
- 所有 ETA 估算记录到 `.rddf/state/.cross-repo-deps-cache.json` 的 `eta_evidence` 字段
- Lv1 自动 / Lv2 frontmatter / Lv3 manual -- 标识来源

### 场景 2：在 Hub 创建 Dependency Issue

```bash
# 自动触发：当本地 plan-done 检测到跨仓库强依赖
$ rddf hub issue --deps \
    --from "org/repo-frontend/auth-v2-impl" \
    --depends-on "org/repo-backend/auth-v2-publish" \
    --eta "2026-09-15"
# 输出：
✅ 已创建 Hub Issue #43 [Dependency] auth-v2-impl 等待 auth-v2-publish
   Stakeholders: org/repo-backend
   Status: 🚧 Blocked (waiting for upstream)
   
   本地 plan-done 门控已挂起，等待 Hub Issue #43 解除。
```

### 场景 3：plan-done 跨仓库门控

```bash
# 在 repo-frontend 执行 guide-plan Phase 4 (plan-done)
$ rddf plan-gate-check
# 输出：
🔍 跨仓库依赖检查：
   - 检测到 1 个跨仓库强依赖（Hub Issue #43）
   - 当前状态: 🚧 Blocked (waiting for repo-backend/auth-v2-publish)
   - 设置 STRICT_DEPS_GATE=yes 时硬阻断 plan-done
   
   决策: ❌ plan-done 失败，需等待上游仓库
   
   exit code: 1
```

**Out of Scope**:

- **不实现** 跨仓库合并编排（GitHub Actions 自动化合并属于 Hub Repo）
- **不创建** 新的依赖类型（仅扩展 `depends_on` / `blocks` / `manual_deps` 现有语义）
- **不集成** Jira / Linear 等外部依赖系统

## Capabilities

- **图算法**：使用 Kahn's algorithm 拓扑排序，输出 wave-based 推荐顺序
- **缓存**：`cross-repo-deps-cache.json` 缓存扫描结果（TTL 3600s）
- **可观测性**：跨仓库依赖图渲染为 Mermaid 格式
- **Schema 兼容**：iteration.json v7 必须向后兼容 v6（缺字段时默认空数组）

## Impact

- (no items specified)

## Acceptance

- [ ] `rddf deps cross-repo --spokes X,Y,Z` 生成 Mermaid 图 + 推荐顺序
- [ ] `rddf hub issue --deps` 在 Hub 创建 `[Dependency]` Issue 并设置正确字段
- [ ] `STRICT_DEPS_GATE=yes` 时 plan-done 检测跨仓库阻塞
- [ ] iteration.json v7 schema 校验通过（保留 v6 字段）
- [ ] 拓扑排序结果稳定（同一输入多次运行结果一致）
- [ ] 单元测试覆盖 5 个关键路径（topo-sort / cycle-detect / hub-create / gate-detect / cache-hit）
- [ ] README §跨项目协同 章节增加跨仓库依赖示例
- [ ] 集成测试：在临时 git 仓库模拟多仓库依赖场景

