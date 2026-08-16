## Context

当前 `deps` 阶段（`skills/deps/SKILL.md`）生成的 `deps-analysis.json` / `iteration.json` 仅表达**单仓库内**的 change 依赖关系，无法表达跨仓库依赖。这导致：

- 仓库 A 的 change X 依赖仓库 B 的 change Y 才能合并 —— 无法建模
- 仓库 A 的 change X 是仓库 B 的契约消费者 —— 必须先等 B 发布，无法追踪

需要扩展 `rddf deps` 能力，支持跨仓库依赖图生成、Kahn 拓扑排序与循环检测、ETA 估算（带三级回退）、Hub Issue 自动创建。

## Goals / Non-Goals

**Goals:**
- 实现 `rddf deps cross-repo` 命令，扫描多个 Spoke 仓库的 `iteration.json`
- 实现 Kahn 拓扑排序算法，支持强依赖（阻塞）和弱依赖（警告）两种边类型
- 实现循环检测算法，在拓扑排序前检测并报告环形依赖
- 实现 ETA Lv1/Lv2/Lv3 三级回退机制，支持 velocity cache 缺失时的优雅降级
- 实现 `.rddf/state/.cross-repo-deps-cache.json` 缓存机制（TTL 24h）
- 实现 `rddf hub issue --deps` 命令，在 Hub 创建 `[Dependency]` Issue
- 升级 `iteration.json` schema 至 v7，新增 `cross_repo_dependencies` 字段
- 升级 `guide-plan` deps 阶段，当 `STRICT_DEPS_GATE=yes` 时挂起 plan-done 门控
- 生成 Mermaid 格式跨仓库依赖图，支持 solid（强依赖）和 dashed（弱依赖）两种边
- 编写完整的单元测试和集成测试

**Non-Goals:**
- 不实现跨仓库的自动合并或 PR 创建（仅协调和跟踪）
- 不修改现有单仓库 `deps.md` 的行为（向后兼容）
- 不实现跨仓库的实时 Webhook 通知（未来可能扩展）
- 不实现跨仓库的权限检查或访问控制

## Decisions

### 1. Kahn 拓扑排序算法选择

**Decision:** 使用 Kahn 算法实现拓扑排序，而非 DFS-based 算法。

**Rationale:**
- Kahn 算法天然支持_wave_概念：同一层级的节点（无剩余入边）可并行执行
- DFS 算法生成逆序后需要额外处理才能得到并行信息
- Kahn 算法更容易检测「无法完成的图」（通过剩余节点数量判断）

**Alternatives considered:**
- DFS-based 拓扑排序：被拒绝，因为难以直接产生 wave 并行信息
- BFS 层序遍历：被拒绝，因为不能保证拓扑序（只能得到层级，不能得到依赖偏序）

### 2. ETA 三级回退机制

**Decision:** Lv1（自动化 velocity cache）→ Lv2（proposal frontmatter）→ Lv3（manual --set-eta）→ null。

**Rationale:**
- Lv1 利用历史数据自动估算，最省人力，但需要 cache 存在
- Lv2 利用维护者声明的 ETA，适合有明确里程碑的场景
- Lv3 允许临时覆盖，适合紧急调整
- null 不用于 blocking，仅用于展示

**Alternatives considered:**
- 仅用 Lv1：被拒绝，因为 velocity cache 可能缺失或过期
- 硬编码默认值（如 5d）：被拒绝，因为不同 change 复杂度差异大

### 3. 循环检测策略

**Decision:** 在拓扑排序前先执行循环检测，若有环则 abort 并报告环成员。

**Rationale:**
- Kahn 算法在有环时会剩余节点无法完成，可用于检测
- 但报告「哪些节点形成环」需要额外算法（DFS-based 追溯）
- 提前检测可提供更友好的错误信息

**Alternatives considered:**
- 依赖 Kahn 的「剩余节点」判断环存在但不报告成员：被拒绝，因为用户需要知道具体哪些 change 形成循环
- 使用 union-find 检测环：被拒绝，union-find 只检测「是否存在环」，不报告环成员

### 4. Hub Issue 创建时机

**Decision:** `STRICT_DEPS_GATE=yes` 时自动创建，而非每次 deps 分析都创建。

**Rationale:**
- 避免在普通 `rddf deps cross-repo` 时产生大量 Hub Issue
- 仅在真正需要「阻塞 plan-done」时才创建 Issue
- Issue 创建是跨仓库的副作用，应显式控制

**Alternatives considered:**
- 每次 deps 分析都创建 Issue：被拒绝，会产生过多噪声 Issue
- 仅手动创建（不自动）：被拒绝，STRICT_DEPS_GATE 的存在就是为了自动化

### 5. iteration.json Schema v7 设计

**Decision:** `cross_repo_dependencies` 作为 per-change 数组字段，而非全局图结构。

**Rationale:**
- 符合现有 `iteration.json` 的单仓库设计习惯（per-change 字段）
- 避免与单仓库 `dependencies` 字段混淆
- 每个 change 声明自己依赖哪些跨仓库 change，职责清晰

**Alternatives considered:**
- 全局 `cross_repo_graph` 节点：被拒绝，修改面更大，且与单仓库设计不一致

### 6. Mermaid 输出格式

**Decision:** 使用 `subgraph` 按 Spoke 分组，solid arrow 表示强依赖，dashed arrow 表示弱依赖。

**Rationale:**
- `subgraph` 直观展示仓库边界
- solid arrow (`-->`) 与 Mermaid 默认一致，用户熟悉
- dashed arrow (`-.->`) 视觉区分度大，适合弱依赖

**Alternatives considered:**
- 全部使用实线：被拒绝，无法区分强弱依赖
- 使用颜色区分：被拒绝，在某些渲染器上不兼容

## Risks / Trade-offs

### Risk 1: Spoke 仓库访问失败
**Description:** 某些 Spoke 仓库可能无法 clone（如权限不足、网络问题）。
**Mitigation:** 降级处理 —— 跳过不可访问的 Spoke，在 summary 中报告 skipped count。
**Trade-off:** 生成的图可能不完整，但至少是可用的。

### Risk 2: ETA 估算偏差
**Description:** velocity cache 可能不准确，导致 ETA 偏差 >50%。
**Mitigation:** 偏差 >50% 时触发警告，建议更新 cache。
**Trade-off:** 警告可能被忽略，但不会 blocking。

### Risk 3: Hub API 调用失败
**Description:** `rddf hub issue` 可能因 Hub API 限流或认证失败。
**Mitigation:** HubError 捕获与重试逻辑，输出错误而非 abort。
**Trade-off:** Issue 可能创建失败，需要人工介入。

### Risk 4: Cache 一致性
**Description:** 24h TTL 内 Spoke 数据可能已更新，但 cache 未刷新。
**Mitigation:** 提供 `--force-refresh` 手动刷新。
**Trade-off:** 默认可能显示 stale 数据。

### Risk 5: 循环依赖导致图无法排序
**Description:** 跨仓库 change 之间存在循环依赖。
**Mitigation:** 检测并报告环成员，阻止拓扑排序。
**Trade-off:** 用户需要手动解除循环。
