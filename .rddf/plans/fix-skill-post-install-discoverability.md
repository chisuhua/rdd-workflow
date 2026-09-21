# fix-skill-post-install-discoverability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 install.sh 分发鸿沟（SKILL.md 外部 docs/ 引用失效 + 第三方项目 AI agent 不可发现），新增 `rddf setup ai-context` CLI 实现 Layer 0 渐进式上下文注入。

**Architecture:** 四层架构（Layer 0 AI 协议块 → Layer 1 SKILL.md 自包含 → Layer 2 可选 docs/ 分发 → Layer 3 仓库参考）的分阶段实施。所有非代码产出（ADR、架构文档）先产出，代码实现后执行，测试最后验证。

**Tech Stack:** Python 3.11 (CLI), bash (install.sh), bats (shell tests), pytest (Python unit tests), markdown (docs/ADR)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/templates/layer0_rdd_workflow_usage.md` | SSOT 模板 — Layer 0 协议块唯一来源（≤ 30 行，5 段结构） |
| `_lib/cli/setup_cmd.py` | `rddf setup ai-context` 子命令实现（AI 配置文件检测/追加/创建/卸载） |
| `_lib/cli/setup.py` | `rddf setup` CLI 组注册入口 |
| `install.sh` | 扩展 `--with-docs` flag（仅复制被引用子集，默认 OFF） |
| `skills/roadmap/SKILL.md` | Layer 1 章节重写为自包含版（≤ 40 行，无 docs/ 引用） |
| `skills/rdd-hub-bootstrap/SKILL.md` | Layer 1 章节重写为自包含版（≤ 40 行，无 docs/ 引用） |
| `skills/status/SKILL.md` | rddf init hint 追加（可选后置） |
| `skills/add-improve/SKILL.md` | 新增 "attach --project-id 实际语义" 章节 |

### rdd-doctor / CLI

| File | Responsibility |
|---|---|
| `skills/rdd-doctor/scripts/doctor.sh` | 新增 `ai-context-bootstrap` category |
| `skills/rdd-doctor/scripts/doctor_ai_context.py` | doctor ai-context-bootstrap 检测逻辑 |
| `_lib/cli/doctor_cmd.py` (若存在) | CLI 注册 `--category ai-context-bootstrap` |

### Docs / ADR

| File | Responsibility |
|---|---|
| `docs/adr/ADR-0052-layer-0-progressive-context.md` | 新 ADR: 分层 + SSOT + 默认 OFF + sentinel + 多文件决策 |
| `docs/architecture/layer-0-progressive-context.md` | 渐进式上下文架构文档（Mermaid 图 + 多重保险 + 上下文预算） |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_setup_ai_context.bats` | ≥ 8 cases: 6 文件追加 + 幂等 + dry-run + uninstall + UTF-8 + Hub 共存 |
| `tests/integration/test_skill_layer1_self_contained.bats` | ≥ 3 cases: grep 检查 SKILL.md 无外部 docs/ 引用 |
| `tests/integration/test_install_with_docs.bats` | ≥ 5 cases: --with-docs 只复制子集 + 幂等 + 不写项目根 |
| `tests/integration/test_doctor_ai_context_bootstrap.bats` | ≥ 4 cases: doctor 在各种 AI 配置状态下输出正确 |
| `tests/integration/test_layer0_sentinel_order.bats` | Hub + Layer 0 sentinel 顺序稳定性 |
| `tests/unit/test_rddf_setup_help.bats` | `--help` 含 ai-context 子命令 |
| `tests/unit/test_layer0_template_sso.bats` | Layer 0 渲染 == SSOT 模板 |
| `tests/integration/test_rddf_init_hint.bats` | rddf init 输出末尾含 setup hint |

---

### Task 1: ADR-0052 — 渐进式上下文架构决策记录

**Files:**
- Create: `docs/adr/ADR-0052-layer-0-progressive-context.md`

- [ ] **Step 1: Write ADR-0052 content**

使用 ADR 模板，涵盖 5 主题：
(a) install ≠ setup ≠ doctor 三层分工及理由
(b) Layer 0 块 SSOT 与 ≤30 行纪律
(c) `--with-docs` 默认 OFF 决策
(d) sentinel 命名约定 `RDD-WORKFLOW-*-START`
(e) 多 AI 配置文件并存时"都追加"决策

- [ ] **Step 2: Verify ADR format**

Run: `ls docs/adr/ADR-0052-layer-0-progressive-context.md`
Expected: 文件存在，frontmatter 完整，格式匹配 ADR-0000 模板

---

### Task 2: 架构文档 — layer-0-progressive-context.md

**Files:**
- Create: `docs/architecture/layer-0-progressive-context.md`

- [ ] **Step 1: Write architecture doc**

包含：渐进式上下文架构说明（Layer 0→1→2→3）+ Mermaid 架构图 + 多重保险机制矩阵 + 上下文窗口预算 + 扩展性约定

- [ ] **Step 2: Verify doc exists**

Run: `ls docs/architecture/layer-0-progressive-context.md`
Expected: 文件存在，内容完整

---

### Task 3: Layer 1 — SKILL.md 自包含重写

**Files:**
- Modify: `skills/roadmap/SKILL.md` (L21-29 重写)
- Modify: `skills/rdd-hub-bootstrap/SKILL.md` (L46-50 重写)

- [ ] **Step 1: Read current SKILL.md files to find the sections to rewrite**

Run: `grep -n 'docs/' skills/roadmap/SKILL.md skills/rdd-hub-bootstrap/SKILL.md`
Expected: Found the lines with `../../docs/` references

- [ ] **Step 2: Rewrite `skills/roadmap/SKILL.md` Layer 1 section (≤40 行)**

替换外部 docs/architecture/roadmap-organization.md 引用为自包含精简版：
- Roadmap 5 维概念（theme / phase / priority / status / category）
- 主文档 sentinel 区域说明
- Sprint/Phase 正交关系

- [ ] **Step 3: Verify roadmap SKILL.md has no external docs/ reference**

Run: `grep -c '../../docs/' skills/roadmap/SKILL.md`
Expected: 0

- [ ] **Step 4: Rewrite `skills/rdd-hub-bootstrap/SKILL.md` Layer 1 section (≤40 行)**

替换外部 `../../docs/rdd-hub-bootstrap.md` 引用为自包含版：
- rdd-hub 核心用法
- 安装命令及入口

- [ ] **Step 5: Verify rdd-hub-bootstrap SKILL.md has no external docs/ reference**

Run: `grep -c '../../docs/' skills/rdd-hub-bootstrap/SKILL.md`
Expected: 0

- [ ] **Step 6: Verify both sections ≤ 40 行**

Run: Check that the Layer 1 section in each file is ≤ 40 lines
Expected: Both sections within limit

---

### Task 4: SSOT 模板 — layer0_rdd_workflow_usage.md

**Files:**
- Create: `_lib/templates/layer0_rdd_workflow_usage.md`

- [ ] **Step 1: Create directory and SSOT template**

```bash
mkdir -p _lib/templates
```

模板内容（≤30 行，5 段结构）：
1. 身份声明：本项目已安装 rdd-workflow (OpenSpec 工作流技能包)
2. 推荐入口：`skill_use("guide")`
3. 核心流程：`rdd-arch → rdd-planner → rdd-builder → rdd-verifier`
4. 旁路规则：≤2 文件且 ≤3 任务且无公开 API 变更 → `skill_use("rdd-quick")`
5. 自助诊断：`rddf doctor --category ai-context-bootstrap`

- [ ] **Step 2: Verify template ≤ 30 行**

Run: `wc -l _lib/templates/layer0_rdd_workflow_usage.md`
Expected: ≤ 30

---

### Task 5: rddf CLI — `rddf setup ai-context` 子命令

**Files:**
- Create: `_lib/cli/setup.py` (CLI group)
- Create: `_lib/cli/setup_cmd.py` (ai-context subcommand)

- [ ] **Step 1: Read existing rddf CLI registration pattern**

Review how other subcommands (`status`, `doctor`, `deps`) are registered.

- [ ] **Step 2: Implement `_lib/cli/setup.py` — CLI group registration**

注册 `rddf setup` 命令组及 `--help` 显示。

- [ ] **Step 3: Implement `_lib/cli/setup_cmd.py` — `rddf setup ai-context`**

核心功能：
- 检测目标项目 AI 配置文件（AGENTS.md → .cursorrules → CLAUDE.md → .clinerules → .continue/rules/*.md → .github/copilot-instructions.md）
- 都不存在 → 创建 AGENTS.md 含 Layer 0 块
- 存在 → 追加到末尾（sentinel 幂等）
- 多文件并存 → 都追加
- 支持 `--dry-run`（预览）、`--yes`（跳过确认）、`--uninstall`（移除）
- 删除块后重跑 → 重新追加（删除即重置）
- 从 SSOT 模板 `_lib/templates/layer0_rdd_workflow_usage.md` 读取内容
- Layer 0 块 sentinel：`<!-- RDD-WORKFLOW-CORE-USAGE-START -->` / `<!-- RDD-WORKFLOW-CORE-USAGE-END -->`

- [ ] **Step 4: Verify CLI registration**

Run: `rddf setup --help 2>&1 | grep -c 'ai-context'`
Expected: ≥ 1 (ai-context 子命令可见)

- [ ] **Step 5: Verify basic functionality — dry-run in tmpdir**

Run: `cd /tmp/test-setup && rddf setup ai-context --dry-run`
Expected: 预览输出显示将创建 AGENTS.md（无实际写入）

---

### Task 6: install.sh `--with-docs` flag

**Files:**
- Modify: `install.sh`

- [ ] **Step 1: Read install.sh structure**

Review `install_per_project()` function to understand extension point.

- [ ] **Step 2: Add `--with-docs` flag to install.sh**

在 `install_per_project()` 末尾新增逻辑：
- 默认 OFF，仅 `--with-docs` 显式开启
- 只复制被引用子集：`docs/architecture/roadmap-organization.md` + `docs/rdd-hub-bootstrap.md`
- 复制到 `$TARGET_DIR/.opencode/skills/rdd-workflow/docs/`
- 幂等 sentinel 检测
- 不写入项目根

- [ ] **Step 3: Verify default behavior unchanged**

Run: `diff <(bash install.sh --dry-run) <(bash install.sh)` or check script parses
Expected: 无 `--with-docs` 时行为字节级不变（约束 3）

---

### Task 7: rdd-doctor `ai-context-bootstrap` category

**Files:**
- Create: `skills/rdd-doctor/scripts/doctor_ai_context.py`
- Modify: `skills/rdd-doctor/scripts/doctor.sh`

- [ ] **Step 1: Read existing doctor pattern**

Review how existing doctor categories are registered and called.

- [ ] **Step 2: Implement `doctor_ai_context.py` — bootstrap detection logic**

静态检测目标项目 AI 配置文件状态：
- AGENTS.md 已含 Layer 0 块 → ✅ 健康
- 不存在 → ⚠️ WARN 提示 `rddf setup ai-context` 可用
- 已含但缺失 Hub 协议 → INFO 提示 spoke-system-prompt-injection
- 不修改文件（read-only）

- [ ] **Step 3: Register `ai-context-bootstrap` category in doctor.sh**

用 CLI 路径而非 bash skills/.../（per Oracle P0）。

- [ ] **Step 4: Verify CLI invocation works**

Run: `rddf doctor --category ai-context-bootstrap 2>&1`
Expected: 输出正确状态报告（不报错）

---

### Task 8: rdd-doctor `docs-consistency` 增强

**Files:**
- Modify: `skills/rdd-doctor/scripts/doctor.sh`

- [ ] **Step 1: Enhance docs-consistency category**

在现有 `docs-consistency` category 中增加静态检查：
- 对所有 `skills/*/SKILL.md` 里 grep 搜索 `../docs/` `../../docs/` 引用
- 报告 WARNING 列出所有违规 SKILL.md
- 不阻断（CI 可配置 STRICT_DOCS_CONSISTENCY_GATE=yes）

- [ ] **Step 2: Verify detection works**

Run: `rddf doctor --category docs-consistency 2>&1 | grep -c 'WARNING\|CRITICAL'` (before fix = has warnings, after Task 3 = zero)
Expected: reports exist（修复前应有 warning，修复后应为 0）

---

### Task 9: `rddf init` hint

**Files:**
- Modify: `skills/_lib/cli/` or the relevant rddf init entry point

- [ ] **Step 1: Find rddf init entry point**

Identify where `rddf init` command outputs its final message.

- [ ] **Step 2: Add setup hint to successful init output**

成功执行后追加：
"💡 下一步：`rddf setup ai-context`（让 AI agent 启动时知道本项目装了 rdd-workflow）"

- [ ] **Step 3: Verify hint appears**

Run: `rddf init --help 2>&1` or check the success output path
Expected: hint 文本出现在相关输出中

---

### Task 10: `add-improve` SKILL.md 文档缺口修复

**Files:**
- Modify: `skills/add-improve/SKILL.md`

- [ ] **Step 1: Read current add-improve SKILL.md attach section**

找到 `--project-id` 相关文档。

- [ ] **Step 2: Add "attach --project-id 实际语义" 章节**

文档化：`--project-id` 实际是 Phase Skeleton Theme 列的精确字符串（中文），不是项目名。
示例：`--project-id "流程定制层" --phase phase-3`
引用 `rddf planner attach --help` 输出同步。

- [ ] **Step 3: Verify the section was added**

Run: `grep -c 'attach.*--project-id' skills/add-improve/SKILL.md`
Expected: ≥ 1（新章节存在）

---

### Task 11: Test — test_setup_ai_context.bats

**Files:**
- Create: `tests/integration/test_setup_ai_context.bats`

- [ ] **Step 1: Write test file with ≥ 8 cases**

8 个测试用例覆盖：
1. AGENTS.md 创建（空项目）
2. .cursorrules 追加
3. CLAUDE.md 追加
4. 多文件并存时都追加
5. 幂等（重复运行不重复注入）
6. --dry-run 输出格式
7. --uninstall 移除
8. UTF-8/中文内容保留
9. 非 git 目录兼容
10. Hub 协议共存

- [ ] **Step 2: Run tests**

Run: `bats tests/integration/test_setup_ai_context.bats`
Expected: ≥ 8 pass（大部分可能因 mock 环境先 fail，验证测试结构正确）

---

### Task 12: Test — test_skill_layer1_self_contained.bats

**Files:**
- Create: `tests/integration/test_skill_layer1_self_contained.bats`

- [ ] **Step 1: Write test file with ≥ 3 cases**

测试 grep 检查所有 SKILL.md 无 `../docs/` `../../docs/` 外部引用。

- [ ] **Step 2: Run the test**

Run: `bats tests/integration/test_skill_layer1_self_contained.bats`
Expected: ≥ 3 pass（或合理 skip）

---

### Task 13: Test — test_install_with_docs.bats

**Files:**
- Create: `tests/integration/test_install_with_docs.bats`

- [ ] **Step 1: Write test file with ≥ 5 cases**

1. `--with-docs` 只复制被引用子集（2 篇，非整个 docs/）
2. 幂等（重复运行不重复复制）
3. 不写入项目根
4. 默认 OFF 验证
5. 被引用文件内容完整

- [ ] **Step 2: Run the test**

Run: `bats tests/integration/test_install_with_docs.bats`
Expected: ≥ 5 pass（或合理 skip）

---

### Task 14: Test — test_doctor_ai_context_bootstrap.bats + sentinel order

**Files:**
- Create: `tests/integration/test_doctor_ai_context_bootstrap.bats`
- Create: `tests/integration/test_layer0_sentinel_order.bats`
- Create: `tests/unit/test_rddf_setup_help.bats`
- Create: `tests/unit/test_layer0_template_sso.bats`
- Create: `tests/integration/test_rddf_init_hint.bats`

- [ ] **Step 1: Write test_doctor_ai_context_bootstrap.bats (≥ 4 cases)**

测试 doctor 在各种 AI 配置状态下输出正确。

- [ ] **Step 2: Write test_layer0_sentinel_order.bats**

Hub sentinel + Layer 0 sentinel 顺序稳定性（重复交替运行 deploy.sh + setup 不互相移动）

- [ ] **Step 3: Write test_rddf_setup_help.bats (unit)**

`rddf setup --help` 包含 ai-context 子命令文档。

- [ ] **Step 4: Write test_layer0_template_sso.bats (unit)**

Layer 0 协议块渲染输出 == SSOT 模板（防漂移）。

- [ ] **Step 5: Write test_rddf_init_hint.bats (integration)**

`rddf init` 成功输出末尾含 setup hint。

- [ ] **Step 6: Run all new tests**

Run: `bats tests/integration/test_doctor_ai_context_bootstrap.bats tests/integration/test_layer0_sentinel_order.bats tests/unit/test_rddf_setup_help.bats tests/unit/test_layer0_template_sso.bats tests/integration/test_rddf_init_hint.bats`
Expected: All tests run（部分因 mock 环境可能 skip/fail — 记录 baseline）

---

### Task 15: 全量回归验证

**Files:**
- Run: `./test.sh --full --regression`

- [ ] **Step 1: Run full regression suite**

Run: `./test.sh --full --regression`
Expected: 无新增失败（仅 KNOWN_FAILURES baseline）

- [ ] **Step 2: Update improvement-approved.md status**

Mark acceptance checkbox: "全量回归 ./test.sh --full --regression 通过"

---

### Task 16: Final — archive change

**Files:**
- Run: rdd-builder P3 archive

- [ ] **Step 1: Commit all changes in worktree with conventional commit**

```bash
git add -A && git commit -m "feat(fix-skill-post-install-discoverability): Layer 0→3 progressive context injection

- SKILL.md self-contained (roadmap + rdd-hub-bootstrap)
- rddf setup ai-context CLI command with SSOT template
- install.sh --with-docs flag (default OFF, referenced subset only)
- rdd-doctor ai-context-bootstrap + docs-consistency enhancement
- rddf init output hint
- ADR-0052 + layer-0-progressive-context architecture doc
- 8 test files covering all scenarios"
```

- [ ] **Step 2: Run rdd-builder P3 archive**

Execute archive gate → openspec archive → cleanup