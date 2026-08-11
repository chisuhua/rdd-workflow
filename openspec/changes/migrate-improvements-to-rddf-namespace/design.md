## Context

`improvements/` 目录是 rdd-workflow 的提案池，存放 133 个已实施或待审的改进提案（每个为独立的 `.md` 文件）。这些文件经由 opencode-skillfull 插件自动索引为 slash commands，注入到 system prompt 的 `<available_skills>` 块中，静态消耗 **~4,887 tokens**（133 entries × ~147 chars ÷ 4）。

2026-08-11 的 skill-context-audit POC 验证了以下结论：
- 插件不读取 frontmatter 元数据（`user-invocable: false` 字段无效）
- 插件过滤 dot-prefix 目录（`.poc-test-skillignore/probe` 实测不在 available_skills 中）
- 现有 `.rddf/plans/` 已是"dot-prefix tracked exception"先例

`.rddf/` 目录采用"tracked by omission"模式：默认全 gitignore，但 `.rddf/plans/` 靠"不写进 gitignore"实现 tracked。

## Goals / Non-Goals

**Goals:**
- 将 `improvements/` 重定位到 `.rddf/improvements/`，被 opencode-skillfull 自动过滤
- 节省 system prompt ~4,887 tokens 静态占用
- 与 `.rddf/plans/` 命名约定保持一致，统一所有 rdd-workflow internal metadata
- 通过 ADR-0026 固化命名约定，避免未来添加新 metadata 类别时重蹈覆辙
- 保留全部 134 个文件的 git history（rename detection）
- 不破坏 add-improve/scan-state.sh 等核心 workflow

**Non-Goals:**
- 修改 `proposal-suggestions.md` 表头/格式
- 修改 add-improve 用户交互流程
- 重命名 ADR 编号
- 删除/归档已有 134 个 proposals
- 修改 scan-state.sh 业务逻辑（仅改路径字面量）
- 改 opencode-skillfull 插件行为（上游）
- 添加 symlink 兼容垫片

## Decisions

### 决策 1：迁移到 `.rddf/improvements/` 而非 `.improvements/`
**Rationale**: 与 `.rddf/plans/` 已存在的"dot-prefix tracked exception"模式完全对齐。语义上更明确（属于 rdd-workflow internal namespace），gitignore 不需新增。
**Alternatives considered**:
- `.improvements/` (top-level dot-prefix): 也可工作，但破坏 rdd-workflow metadata 统一在 `.rddf/` 下的命名约定
- symlink `improvements/` → `.rddf/improvements/`: 引入新维护面，N 版本后需清理
- 移动到 `openspec/changes/archive/`: 语义错误（这些是活跃提案池，不是归档）

### 决策 2：atomic commit，不分阶段
**Rationale**: 37 个文件 + 134 链接 + 11 测试需同时更新。任何中间态都会破坏 add-improve/scan-state 流程。atomic commit 简化 review 和 revert。
**Alternatives considered**:
- 分阶段 (git mv 优先 → 再更新引用): 中间态破损
- 多次 PR: 增加 review 负担，无收益

### 决策 3：使用 `git mv` 而非 `mv`
**Rationale**: 保留 rename detection 记录，git 自动识别为 rename（相似度阈值）。`git log --follow` 可显示完整历史。
**Alternatives considered**:
- 直接 `mv` + commit: git 可能误判为 delete+add，丢失 rename 信息

### 决策 4：proposal-approved.md 134 个链接用 sed 批量替换
**Rationale**: 134 个链接格式一致（`...](improvements/X.md)`），sed 一行命令完成。手动逐个修改易出错。
**Alternatives considered**:
- Python 脚本遍历: 等价但更复杂
- 手工逐个修改: 134 个易漏易错

### 决策 5：skills/_lib/ 37 个文件路径用 grep + 手工 review
**Rationale**: 这些文件中 `improvements/` 可能是路径常量、文档字符串、示例代码、注释，sed 易误改非路径。手工 review 一次保证零误改。
**Alternatives considered**:
- 全自动 sed: 风险高，可能误改非路径字符串

### 决策 6：ADR-0026 同步创建
**Rationale**: 命名约定需文档化以避免未来添加新 metadata 类别时重蹈覆辙（如 `.rddf/notes/`、`.rddf/experiments/`）。
**Alternatives considered**:
- 仅迁移 + commit message: 文档缺失，未来人不知道 WHY

## Risks / Trade-offs

- **[风险 1: 路径替换遗漏]** → Mitigation: 验收 AC-2 强制 0 残留（grep 全目录验证）+ AC-8 rdd-doctor 通过
- **[风险 2: 测试 fixture 改不全]** → Mitigation: 验收 AC-6 强制 `./test.sh --full --regression` 全绿（0 新失败）
- **[风险 3: 现有用户的 IDE/书签失效]** → Out of Scope 决策 — proposal-approved.md 是唯一引用源，新链接完全替换后无 404
- **[风险 4: git rename detection 失败（相似度低）]** → Mitigation: 文件名不变仅路径变，git rename detection 准确率应 100%。验收 AC-1c 验证
- **[风险 5: opencode 重启后插件未生效]** → Mitigation: 验收 AC-5 强制用户验证 available_skills 行为
- **[Trade-off: 134 个 markdown 链接重写]** → 不可避免；接受一次性 sed 成本

## Migration Plan

### 步骤 1: 准备
- 在 worktree 中执行（隔离 master）
- 验证 master 工作区干净（`git status` 无未提交改动）
- 读 `.rddf/state/.plan-handoff.json` 获取 ship 阶段入口

### 步骤 2: git mv（原子移动）
```bash
mkdir -p .rddf/improvements
git mv improvements/*.md .rddf/improvements/
rmdir improvements
```
预期：1 个 commit rename 操作，保留全部 history

### 步骤 3: 批量链接更新
```bash
sed -i 's|](improvements/|](.rddf/improvements/|g' proposal-approved.md
```
预期：134 个链接全部更新

### 步骤 4: skills/_lib/ 路径常量
- 用 `grep -rln "improvements/" skills/ _lib/` 定位 37 个文件
- 逐文件 review 替换（每文件可能 1-3 处）
- 重点关注：`add-improve/SKILL.md`, `guide*/scripts/*.sh`, `propose/scripts/*.py`, `rdd-doctor/scripts/checks/*.py`

### 步骤 5: 文档同步
- `docs/proposal-suggestions-format.md`: 路径示例改新
- `docs/proposal-approved-format.md`: 路径示例改新
- `INSTALL.md`, `USAGE.md`, `README.md`: 路径提及
- `docs/adr/ADR-0024-deps-driven-execution-mode.md`, `ADR-0025-design-proposal-creation.md`: 文中提到 improvements 的地方

### 步骤 6: ADR-0026 创建
文件：`docs/adr/ADR-0026-internal-metadata-namespace-convention.md`
内容：dot-prefix 命名规则、已存在实例（plans/、improvements/）、未来添加新类别指引

### 步骤 7: 测试 fixture + 集成测试
- `tests/fixtures/diseased-repo/proposal-suggestions.md`
- `tests/integration/*.bats` 中所有 `improvements/` 字面量

### 步骤 8: 验证
- `./test.sh --full --regression` (AC-6)
- `git ls-files .rddf/improvements/ | wc -l` == 133 (AC-1a)
- `grep -rn "improvements/" skills/ _lib/ tests/ docs/ | grep -v ".rddf/improvements" | wc -l` == 0 (AC-2)
- 用户重启 opencode 验证 available_skills (AC-5)

### 步骤 9: worktree 内部 commit + merge
- 1 个聚合 commit（不逐任务 commit）
- merge 到 default branch

### Rollback Strategy
`git revert <commit-hash>` 即可。提案级 8 个 AC 中任何一个失败 → 立即 revert + 调查。

## Open Questions

- **Q1**: 是否需要保留 improvements/ → .rddf/improvements/ symlink 作为 N 版本过渡期？
  - **Decision**: 否。atomic 迁移 + 134 链接全替换，无外部依赖，不需 symlink。

- **Q2**: 未来若新增 `.rddf/notes/` 等新 metadata 类别，是否需要单独提案？
  - **Decision**: 是。ADR-0026 将明确"添加新 metadata 类别需先提案"。
