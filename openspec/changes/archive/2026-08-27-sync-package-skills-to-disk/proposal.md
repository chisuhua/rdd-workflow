# sync-package-skills-to-disk

## Why

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

## What Changes

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

## Capabilities

- (no items specified)

## Impact

- (no items specified)

## Acceptance

- [ ] `package.json::skills[]` 含 `report-issue` / `sync-hub` / `watch-hub`（选项 A 则不含 populate-roadmap-from-arch）
- [ ] `skills/INSTALL.md` 子技能表行数 == `package.json::skills[]` 长度 == 磁盘 `*/SKILL.md` 数量
- [ ] `tests/integration/test_skill_metadata_consistency.bats` test 1 PASS
- [ ] `tests/unit/test_doc_contracts.py` 全部 PASS
- [ ] 从 `tests/KNOWN_FAILURES.txt` 移除 line 87
- [ ] AGENTS.md 关键目录注释同步
- [ ] grep 验证 `populate-roadmap-from-arch` 无外部引用

