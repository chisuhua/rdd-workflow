# v2.x → v3.0 迁移指南

> **适用对象**: 正在使用 rdd-workflow v2.x（任何 2.0.x 至 2.1.x）的项目，升级到 v3.0+。
> **参考 ADR**: [ADR-0023](../adr/ADR-0023-v3-rename-spec-workflow-to-rdd-workflow.md)（v3.0.0 包名重命名）
> **升级目标版本**: `v3.0.0`（major bump）

---

## TL;DR — 3 步升级

```bash
# 1. 删除旧安装（仅 skill 目录，无状态数据）
rm -rf ~/.agents/skills/spec-workflow
rm -rf .opencode/skills/spec-workflow   # 如果走项目安装

# 2. 重装（v3.0+）
git clone https://github.com/chisuhua/rdd-workflow.git ~/.agents/skills/rdd-workflow
bash ~/.agents/skills/rdd-workflow/install.sh --global

# 3. 更新 skill 调用引用
# 任何 skill_use("spec-workflow/...") → skill_use("rdd-workflow/...")
# 数据（.rddf/state/）无需迁移
```

---

## 背景：为什么要 v3.0

v2.x 期间 GitHub 仓库名已对齐（`chisuhua/rdd-workflow`），但其他层级的命名仍停留在历史命名 `spec-workflow`：

| 层级 | v2.x | v3.0+ |
|------|------|-------|
| GitHub repository | `chisuhua/rdd-workflow` ✅ | `chisuhua/rdd-workflow` ✅ |
| npm package | `spec-workflow` | **`rdd-workflow`** |
| Skill name | `spec-workflow/writing-plans` | **`rdd-workflow/writing-plans`** |
| Install path | `~/.agents/skills/spec-workflow/` | **`~/.agents/skills/rdd-workflow/`** |
| Project install | `.opencode/skills/spec-workflow/` | **`.opencode/skills/rdd-workflow/`** |
| 内部引用 | `spec-workflow` 散落 | **`rdd-workflow`** 统一 |

**核心冲突**: 用户每次 install / readme / CLI help 都要在两种名字间切换，认知负担严重。

---

## Breaking Changes（v3.0.0）

### 1. Skill 名称 — 必须更新所有调用

```diff
- skill_use("spec-workflow/writing-plans")
+ skill_use("rdd-workflow/writing-plans")
```

**搜索并替换所有项目脚本**:

```bash
# 在 shell 脚本中查找残留
grep -rn "spec-workflow/" .opencode/ scripts/ Makefile 2>/dev/null

# 或全局
grep -rn "spec-workflow/" --include="*.md" --include="*.sh" --include="*.py" 2>/dev/null
```

### 2. Install 路径

```bash
# v2.x
~/.agents/skills/spec-workflow/

# v3.0+
~/.agents/skills/rdd-workflow/
```

⚠️ **不要尝试做软链接兼容** — v3.0 完全 breaking，不保留 shim。

### 3. npm package

```diff
- npm install spec-workflow
+ npm install rdd-workflow
```

### 4. 不变的部分

| 不变项 | 说明 |
|--------|------|
| `rddf` CLI 命令名 | 仍是 `rddf`（与 `rdd-workflow` 包名有意不一致，per ADR-0023 Decision 5） |
| `.rddf/state/` 路径 | 数据目录不变；`.rddf/state/` 内不引用包名 |
| `.rddf/plans/` 路径 | 执行契约路径不变 |
| `rddf_session` Python 模块 | 仍用下划线命名（snake_case） |
| `rdd-session` / `rdd-arch` 子技能 | 子技能命名不变（已用 dash 分隔，与新包名格式一致） |

---

## 风险与回滚

### 风险

- ❌ **完全 breaking**: 所有 v2.x 安装需要重装（无自动迁移）
- ❌ 文档/ADR/specs/archive 历史引用需批量 rename（v3.0.0 已 runtime 执行）
- ⚠️ CI/CD pipeline / 个人脚本引用 `spec-workflow` 字面量会失效

### 回滚

v3.0 不提供自动回滚脚本。如需回退到 v2.x:

```bash
rm -rf ~/.agents/skills/rdd-workflow
git clone https://github.com/chisuhua/rdd-workflow.git --branch v2.1.x ~/.agents/skills/spec-workflow
bash ~/.agents/skills/spec-workflow/install.sh --global
```

---

## v3.0+ 新增能力（顺手了解）

除包名重命名外，v3.0+ 引入：

| 新增 | 说明 | ADR |
|------|------|-----|
| **5 阶段架构**（arch → design → plan → ship → verify） | 在 v2.1 四阶段基础上新增 `rdd-verifier` 第五阶段 | [ADR-0034](../adr/ADR-0034-rdd-verifier-verify-phase-architecture.md) |
| **verifier ↔ archive_gate 双轨边界** | 明确 rdd-verifier 与 archive_gate_check 的责任划分 | [ADR-0035](../adr/ADR-0035-verifier-archive-gate-boundary.md) |
| **rdd-arch rename 预备**（v3.0+ 兼容期） | `guide-arch` 在 v3.0+ 准备重命名为 `rdd-arch`（正式 v4.0 完成） | [ADR-0042](../adr/ADR-0042-rdd-arch-rdd-planner-bidirectional-feedback.md) §D1a |

> 注: 这些是 v3.0 范围而非必读；建议直接看 [v3.0 → v4.0 迁移指南](v3-to-v4.md)。

---

## 常见问题

### Q1: v2.x 安装仍在跑怎么办？

不会自动失效，但下次 `install.sh --global` 时会被 v3.0+ 替代。建议主动升级以避免后续 skill name 解析失败。

### Q2: 数据 (.rddf/state/) 需要迁移吗？

**不需要**。`.rddf/state/` 不包含包名引用，结构与命名无关。

### Q3: 我的脚本调 `rddf` CLI 会受影响吗？

**不会**。CLI 命令名不变。

### Q4: 我能用别名或软链接兼容吗？

**不建议**。v3.0 完全 breaking 的设计是显式选择（per ADR-0023 Decision 2）。软链接会埋下未来 v4+ 升级的二次迁移负担。

### Q5: v3.0 是 LTS 吗？

v3.0+ 持续维护直到 v4.0 稳定（v4.0 已于 2026-09-04 发布，per [ADR-0043](../adr/ADR-0043-rdd-workflow-v4-stage-merge.md)）。建议直接升级到 v4.0+。

---

## 替代方案评估（per ADR-0023 §替代方案评估）

| 方案 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| `rddf-workflow` | 与 CLI `rddf` / 目录 `.rddf/` 完全一致 | 比 `rdd-workflow` 多一个字符 | ❌ |
| 保留 `spec-workflow` | 零迁移成本 | GitHub 已重命名，持续混淆 | ❌ |
| `rdd-flow` | 短名 | 不直观 | ❌ |
| **`rdd-workflow`** | 与 GitHub 对齐 | 与 `rddf` CLI 格式冲突 | ✅ 采用 |

---

## See Also

- [`v1-to-v2.md`](v1-to-v2.md) — 上一版本迁移（Loop 引擎引入）
- [`v3-to-v4.md`](v3-to-v4.md) — 下一版本迁移（5 阶段合并为 4 阶段 + rdd-quick 旁路）
- [`../adr/ADR-0023-v3-rename-spec-workflow-to-rdd-workflow.md`](../adr/ADR-0023-v3-rename-spec-workflow-to-rdd-workflow.md) — 包名重命名 ADR 全文
- [`../adr/README.md`](../adr/README.md) — 完整 ADR 索引
- [`../architecture/historical-evolution.md`](../architecture/historical-evolution.md) — 完整架构演进史