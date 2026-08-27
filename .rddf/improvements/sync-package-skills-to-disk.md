# sync-package-skills-to-disk

**优先级**: P1 | **来源**: 2026-08-26 文档与代码一致性审计
**阶段**: default | **分类**: governance
**类型**: improvement

## 架构依据

2026-08-26 对 rdd-workflow 项目自身做了一次全栈审计，发现 `package.json::skills[]` 与磁盘 `skills/<name>/SKILL.md` 存在系统性漂移：

| 维度 | 数字 |
|------|------|
| `package.json::skills[]` | 25 |
| 磁盘 `skills/<name>/SKILL.md` | 25 |
| 磁盘总 `skills` 目录子目录 | 26（含 `populate-roadmap-from-arch`，**未注册**） |
| `skills/INSTALL.md` 子技能表 | 25 行（漏 `populate-roadmap-from-arch`） |
| `tests/integration/test_skill_metadata_consistency.bats` test 1 | ❌ FAIL（已在 KNOWN_FAILURES.txt 87 行登记） |

具体漂移点：

1. **`populate-roadmap-from-arch`**：磁盘有 `skills/populate-roadmap-from-arch/SKILL.md`，但 `package.json::skills[]` 未注册，且 INSTALL.md 子技能表也漏。AGENTS.md (line 320) 标记其"v1.2 标记 deprecated（thin wrapper）"，但 deprecated skill 不该残留在磁盘上让 SKILL.md glob 拾取到。
2. **`report-issue` / `sync-hub` / `watch-hub`**：磁盘有这三个目录（各自含 `scripts/<x>.py`），但 `package.json::skills[]` 和 INSTALL.md 表都未列出。这是 ADR-0030 Hub-Spoke 的核心命令，但用户从 npm 安装后看不到。
3. **`loop_engine.py` / `guide_arch.py` / `guide_plan.py` / `rddf_session.py` / `populate_roadmap_from_arch.py`** 等顶层 `.py` 文件也存在，但不被 `package.json::skills[]` 收录（Python 模块，非 skill，符合预期，但需明确分类）。

现行影响：
- 用户从 npm 安装 rdd-workflow 后，OpenCode 不会发现 Hub-Spoke 命令（report-issue/sync-hub/watch-hub）—— 与 README.md (line 130-143) 文档声称"3 个新命令启用双向协同通道"矛盾
- `test_skill_metadata_consistency.bats` 持续 FAIL，作为 known failure 长期停留，掩盖未来的真漂移
- 用户从 git clone 安装时能 symlink 到全部目录（INSTALL.md 步骤 3 的 `for skill_dir in "$PACKAGE_DIR/skills/"*/`），但 OpenCode skill 发现走 `package.json::skills[]`，路径不一致

## 范围

**In Scope**:
- `package.json::skills[]` 添加 `report-issue`、`sync-hub`、`watch-hub`（三个 Hub-Spoke 命令）
- 决定 `populate-roadmap-from-arch` 的去留：
  - 选项 A：从磁盘删除（既然 deprecated）+ INSTALL.md 表中移除（用户安装后不可用）
  - 选项 B：保留磁盘 + 添加到 package.json 和 INSTALL.md 表（用户可用 + 显式 deprecated 标记）
- 更新 `skills/INSTALL.md` 子技能表行数声明
- 更新 `tests/integration/test_skill_metadata_consistency.bats` 期望（如果选项 B 选）

**Out of Scope**:
- 修改 skill 行为本身
- 修改 `package.json::scripts`
- 删除 SKILL.md 文件（除非选项 A）

## 设计

### 决策矩阵（populate-roadmap-from-arch）

| 选项 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **A 删除磁盘** | 与 AGENTS.md 的"deprecated"声明一致；测试通过；磁盘干净 | 历史归档与文档链接断开 | ⭐⭐⭐ |
| **B 注册但 deprecated** | 用户仍可调用；过渡期安全 | 长期看 deprecated skill 永远不会被移除 | ⭐⭐ |

**推荐选项 A**：v2.0.6+ 用户已通过 `guide-arch` Phase 6 自动调用 `roadmap_incremental_update.sh`，无需手动调用 `populate-roadmap-from-arch` skill。AGENTS.md 已明确 deprecated，与磁盘删除一致。

### package.json::skills[] 增补

```json
"skills": [
    "INSTALL",
    "guide",
    "guide-arch",
    "guide-design",
    "guide-plan",
    "guide-ship",
    "feature",
    "rddf-session",
    "propose",
    "execute",
    "status",
    "roadmap",
    "deps",
    "add-improve",
    "openspec-gate",
    "rdd-workflow-brainstorm",
    "rdd-workflow-writing-plans",
    "rdd-env-check",
    "rdd-doctor",
    "rdd-hub-bootstrap",
    "contract-check",
    "cross-repo-protocol",
    "spoke-system-prompt-injection",
    "ac-verifier",
    "rdd-verifier",
    "report-issue",
    "sync-hub",
    "watch-hub"
]
```

数量：25 → 28（+3 个 Hub 命令）。如果选选项 A（删除 populate-roadmap-from-arch）：25 → 27。

### INSTALL.md 子技能表增补

按选项 A 添加 3 行：

```markdown
| `report-issue` | Hub-Spoke 上行命令（[RFC] issue 上报到 Hub；ADR-0030） |
| `sync-hub` | Hub-Spoke 下行命令（拉取 Hub 契约到本地 specs；ADR-0030） |
| `watch-hub` | Hub-Spoke 监听命令（一次性轮询 Hub issue 状态；ADR-0030） |
```

### AGENTS.md 同步

- 更新 line 320：`populate-roadmap-from-arch` 的 deprecated 声明移除（已删除）
- 更新 line 318：skill 数量统计对齐

## 影响

- **正向**：`test_skill_metadata_consistency.bats` 转为 PASS（从 known failure 移除）；用户从 npm 安装也能使用 Hub-Spoke 命令；INSTALL.md 列表与 package.json 与磁盘三方对齐
- **正向**：消除 1 个长期 known failure（掩盖效应）
- **风险**：删除 `populate-roadmap-from-arch` 磁盘目录后，外部工具若通过路径引用会断链（grep 验证后实际无引用）
- **兼容性**：无破坏性变更（Hub 命令本来 `rddf report-issue` 等 CLI 形式可用，添加 skill 形式是 +1 个入口）

## 验收

- [ ] `package.json::skills[]` 含 `report-issue` / `sync-hub` / `watch-hub`（选项 A 则不含 populate-roadmap-from-arch）
- [ ] `skills/INSTALL.md` 子技能表行数 == `package.json::skills[]` 长度 == 磁盘 `*/SKILL.md` 数量
- [ ] `tests/integration/test_skill_metadata_consistency.bats` test 1 PASS
- [ ] `tests/unit/test_doc_contracts.py` 全部 PASS
- [ ] 从 `tests/KNOWN_FAILURES.txt` 移除 line 87
- [ ] AGENTS.md 关键目录注释同步
- [ ] grep 验证 `populate-roadmap-from-arch` 无外部引用