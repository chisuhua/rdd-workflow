# migrate-improvements-to-rddf-namespace

## Why

- **问题陈述**：`improvements/*.md` 共 133 个文件被 opencode-skillfull 插件自动索引为 slash commands，注入到 system prompt 的 `<available_skills>` 块。静态 token 占用 **~4,887 tokens**（133 entries × ~147 chars ÷ 4）。每次误调用额外消耗 50-150 行历史内容。
- **POC 验证（2026-08-11）**：
  - **A 失败**：SKILL.md frontmatter `user-invocable: false` — 插件不读取 frontmatter（用户实测确认条目仍出现）
  - **B 成功**：dot-prefix 目录被插件过滤（用户实测 `.poc-test-skillignore/probe` 不在 available_skills）
- **预存先例**：`.rddf/plans/` 已经是"dot-prefix tracked exception"模式（`.gitignore` 注释明示）。迁移 `.rddf/improvements/` 完全对齐此先例。
- **反向论证**（为何不只是 cosmetic 优化）：
  - rdd-workflow 是 self-hosted，133 个 improvements 文件中相当一部分（约 90%）是"已完成"历史提案，对当前 opencode 用户**没有任何价值**，仅消耗 context
  - 未来任何人添加新 metadata 类别（如 `.rddf/notes/`、`.rddf/experiments/`）若不约定 dot-prefix，会重蹈覆辙
  - 必须有 ADR 固化命名约定
- **反向风险**（为何不立即做）：
  - 改动面 ~50 个文件，影响 add-improve/scan-state.sh 等核心 workflow 路径解析
  - 任何遗漏会导致 add-improve 创建文件失败或 scan-state 状态错乱
  - 因此需要完整 plan-done gate + 全量回归测试

## What Changes

**In Scope**:

- 目录迁移：`improvements/` → `.rddf/improvements/`（git mv，保留历史）
- 路径常量更新：37 个 `skills/_lib/` 文件（add-improve/scan-state.sh/guide-design scripts/propose scripts）
- Markdown 链接更新：`proposal-approved.md` 134 个 `[...](improvements/X.md)` → `[...](.rddf/improvements/X.md)`
- 文档同步：`docs/proposal-{suggestions,approved}-format.md` 路径说明
- 测试 fixture 更新：`tests/fixtures/diseased-repo/proposal-suggestions.md` 等
- 集成测试更新：`tests/integration/*.bats` 中 grep `improvements/` 的路径断言
- 安装文档：`INSTALL.md`, `USAGE.md`（如果提到路径）
- ADR 创建：`docs/adr/ADR-0026-internal-metadata-namespace-convention.md`
- 回归验证：`./test.sh --full --regression` 全绿 + opencode 重启后 available_skills 不含 improvements/*
- 修改 `proposal-suggestions.md` 的表头/格式
- 修改 add-improve UX/CLI
- 重命名 ADR 编号
- 删除/归档已有 133 个 proposals
- 修改 scan-state.sh 业务逻辑
- 改 test 测试逻辑
- 改 opencode-skillfull 插件行为（上游）

### 关键场景

- **SC-1 新建提案**: GIVEN 用户调用 `add-improve` skill, WHEN skill 完成 5 段设计 + 用户批准, THEN `.rddf/improvements/<name>.md` 被创建（不是 `improvements/`），且 `proposal-suggestions.md` 表格中的链接指向新路径
- **SC-2 状态扫描**: GIVEN scan-state.sh 在 guide 入口被调用, WHEN 扫描改进提案状态, THEN 从 `.rddf/improvements/*.md` 读取，输出中显示 133 个文件
- **SC-3 设计审查**: GIVEN 用户调用 `guide-design`，待审提案存在, WHEN skill 读取提案内容做内容审查, THEN 读取 `.rddf/improvements/<name>.md` 成功，批准后写入 `proposal-approved.md` 时链接使用新路径
- **SC-4 上下文节省**: GIVEN 迁移已完成 + opencode 重启, WHEN opencode 构建 system prompt, THEN `<available_skills>` 中**不**包含任何 `improvements/<name>` 条目（节省 ~4,887 tokens）
- **SC-5 文档链接**: GIVEN 用户在 IDE/浏览器打开 `proposal-approved.md`, WHEN 点击任一提案链接, THEN 跳转到 `.rddf/improvements/<name>.md`，**不**是 404
- **SC-6 Git 历史**: GIVEN 用户运行 `git log --follow .rddf/improvements/foo.md`, WHEN git 自动检测 rename, THEN 显示完整历史（包括迁移前的 `improvements/foo.md` 提交）
- **SC-7 测试 fixture**: GIVEN CI 运行 `./test.sh --full --regression`, WHEN 执行 `tests/integration/*.bats` 中包含 `improvements/` 字符串的测试, THEN 所有断言通过
- **SC-8 ADR 文档**: GIVEN 用户阅读 ADR-0026, WHEN 在 `docs/adr/ADR-0026-...md` 中查找 dot-prefix 命名规则, THEN 文档明确说明 `.rddf/<category>/` 是 rdd-workflow internal metadata 标准路径

**Out of Scope**:

- (TBD)

## Capabilities

- 使用 `git mv` 移动文件（保留 git history / rename detection）：
- `.gitignore` 不需要新增（`.rddf/` 默认全 ignore，靠"不写进去"实现 tracked exception，与 `.rddf/plans/` 一致）
- `proposal-approved.md` 134 个链接用 `sed -i 's|](improvements/|](.rddf/improvements/|g'` 一次性更新
- 37 个 skills/_lib/ 文件逐一用 `grep -rln "improvements/"` 定位 + 手工 review 替换（避免误改非路径字符串）
- 测试通过：迁移后 `./test.sh --full --regression` 全绿
- 完整 TDD plan：通过 `rdd-workflow-writing-plans` 生成 `.rddf/plans/migrate-improvements-to-rddf-namespace.md`（5 步：Write failing test → Verify fail → Implement → Verify pass → Commit）
- ADR-0026 创建（dot-prefix 命名规则 + 已存在实例 + 未来添加新 metadata 类别的指引）
- 零中间态：任何时刻 `git status` 必须是单一 atomic commit（不出现 broken state commit）
- 不使用 symlink 兼容垫片
- 不修改任何 improvement 文件内容
- 不修改 `proposal-suggestions.md` 的表头/格式
- 不重新编号 ADR
- 不修改 add-improve UX
- 不修改 scan-state.sh 业务逻辑（仅改路径字面量）
- 不修改 test 测试逻辑（仅改 fixture 路径）
- 不创建 workaround 脚本（一次性手工 + sed 解决）
- 执行后用 `rdd-doctor` 扫描验证没有遗漏的路径引用
- 更新 `docs/proposal-suggestions-format.md` 和 `proposal-approved-format.md` 路径示例
- 更新 `INSTALL.md` 如果提到 `improvements/` 目录
- 更新 `USAGE.md` + `README.md` 同上
- 运行 `bash tests/scripts/report_regression.sh` 对比 KNOWN_FAILURES baseline
- commit message 写明影响面：`refactor(rdd-workflow): migrate improvements/ → .rddf/improvements/ for plugin filter (saves ~4,887 tokens)`

## Impact

- 使用 `git mv` 移动文件（保留 git history / rename detection）：
- `.gitignore` 不需要新增（`.rddf/` 默认全 ignore，靠"不写进去"实现 tracked exception，与 `.rddf/plans/` 一致）
- `proposal-approved.md` 134 个链接用 `sed -i 's|](improvements/|](.rddf/improvements/|g'` 一次性更新
- 37 个 skills/_lib/ 文件逐一用 `grep -rln "improvements/"` 定位 + 手工 review 替换（避免误改非路径字符串）
- 测试通过：迁移后 `./test.sh --full --regression` 全绿
- 完整 TDD plan：通过 `rdd-workflow-writing-plans` 生成 `.rddf/plans/migrate-improvements-to-rddf-namespace.md`（5 步：Write failing test → Verify fail → Implement → Verify pass → Commit）
- ADR-0026 创建（dot-prefix 命名规则 + 已存在实例 + 未来添加新 metadata 类别的指引）
- 零中间态：任何时刻 `git status` 必须是单一 atomic commit（不出现 broken state commit）
- 不使用 symlink 兼容垫片
- 不修改任何 improvement 文件内容
- 不修改 `proposal-suggestions.md` 的表头/格式
- 不重新编号 ADR
- 不修改 add-improve UX
- 不修改 scan-state.sh 业务逻辑（仅改路径字面量）
- 不修改 test 测试逻辑（仅改 fixture 路径）
- 不创建 workaround 脚本（一次性手工 + sed 解决）
- 执行后用 `rdd-doctor` 扫描验证没有遗漏的路径引用
- 更新 `docs/proposal-suggestions-format.md` 和 `proposal-approved-format.md` 路径示例
- 更新 `INSTALL.md` 如果提到 `improvements/` 目录
- 更新 `USAGE.md` + `README.md` 同上
- 运行 `bash tests/scripts/report_regression.sh` 对比 KNOWN_FAILURES baseline
- commit message 写明影响面：`refactor(rdd-workflow): migrate improvements/ → .rddf/improvements/ for plugin filter (saves ~4,887 tokens)`

## Acceptance

- **AC-1 文件迁移完整性**：
  - `[ "$(git ls-files .rddf/improvements/ | wc -l)" = "133" ]`
  - `[ ! -d improvements ] || [ -z "$(ls -A improvements)" ]`
  - `git log --follow .rddf/improvements/<sample>.md` 显示完整 history
- **AC-2 路径引用零残留**：
  - `grep -rn "improvements/" skills/ | grep -v ".rddf/improvements" | wc -l` = 0
  - `grep -rn "improvements/" _lib/ | grep -v ".rddf/improvements" | wc -l` = 0
  - `grep -rn "improvements/" tests/ | grep -v ".rddf/improvements" | wc -l` = 0
  - `grep -rn "improvements/" docs/ | grep -v ".rddf/improvements" | wc -l` = 0
- **AC-3 proposal-approved.md 链接全部可解析**：134 个 `.rddf/improvements/...` 链接全部指向存在的文件
- **AC-4 skill 行为不变**：
  - `bash tests/smoke.bats` 全绿
  - `bash tests/integration/scan_state.bats` 全绿
- **AC-5 上下文节省（用户验证）**：
  - 迁移前：`<available_skills>` 含 133 个 `improvements/*` 条目
  - 迁移后：`<available_skills>` 零 improvements 条目
  - Token 节省：~4,887 tokens
- **AC-6 全量回归测试**：`./test.sh --full --regression` 通过（0 新失败）
- **AC-7 ADR-0026 文档化**：
  - `[ -f docs/adr/ADR-0026-internal-metadata-namespace-convention.md ]`
  - 内容包含 `.rddf/<category>` 和 `opencode-skillfull` 关键字
- **AC-8 rdd-doctor 通过**：`bash skills/rdd-doctor/scripts/doctor.sh --quiet` 返回 0 CRITICAL + 0 路径相关 WARNING

