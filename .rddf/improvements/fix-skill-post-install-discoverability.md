---
name: fix-skill-post-install-discoverability
priority: P1
phase: phase-3
category: infra-setup
type: debt
状态: pending
依赖: ADR-0021, add-spoke-system-prompt-injection
主题: 流程定制层
来源: 2026-09-21 对话发现(roadmap-organization.md 沉淀时触发)+ add-spoke-system-prompt-injection
  复用模式
生成时间: 2026-09-21
roadmap_ref:
  project_id: 流程定制层
  phase: phase-3
---

# fix-skill-post-install-discoverability

## 架构依据

**问题陈述**

`install.sh` 当前只分发 `skills/` 子目录 + `_lib/` + `package.json`,**不**分发 `docs/` 与项目 README/USAGE/ONBOARDING。这造成三重鸿沟:

1. **Skill Layer 1 自包含失效**:SKILL.md 顶部导览若引用外部 `docs/architecture/*.md`,install.sh 安装后**必然 404**(目标项目无 docs/ 父目录)。**实际影响 2 个 SKILL.md**(经 2026-09-21 grep 验证):
   - `skills/roadmap/SKILL.md` L29:`../../docs/architecture/roadmap-organization.md` — 2026-09-21 沉淀 roadmap-organization.md 时新增
   - `skills/rdd-hub-bootstrap/SKILL.md` L50:`../../docs/rdd-hub-bootstrap.md` — 已存在 2+ 月的隐性 bug,本次首次发现
2. **第三方项目 AI agent 不可发现**:Spoke 项目安装 rdd-workflow 后,AI 代理(Claude Code / Cursor / Copilot)**完全不知道** rdd-workflow 已安装,不知道有 `skill_use("guide")` 等 27 个入口。`spoke-system-prompt-injection` 已注入 Hub 协议,但**没有 rdd-workflow 核心用法块** — 不对等。
3. **rdd-workflow 核心用法无法触达**:第三方开发者阅读 `.opencode/skills/rdd-workflow/skills/` 时,看不到 `README.md` / `USAGE.md` / `ONBOARDING.md` / `docs/architecture/` 中沉淀的核心概念。

**根因 — 2026-09-21 对话根本性语义纠正**:

之前提案把 Layer 0 部署挂在 `install.sh --spoke-init` 下是**根本性的语义错误**。`install.sh` 的真实语义是**开发者一次性安装 rdd-workflow 工具**(到 `~/.agents/skills/` 或当前项目 `.opencode/skills/rdd-workflow/`),**不**是"在每个用户项目里配置 rdd-workflow"。混淆这两件事会导致:
- 用户期望"装完即用",但 install.sh 跑完并不会让该项目的 AI agent 知道 rdd-workflow
- Layer 0 部署混在工具安装流程里,职责不清

**正确分层**(per 2026-09-21 用户纠正):

| 层 | 工具 | 触发 | 生命周期 |
|---|---|---|---|
| **工具安装**(开发者侧) | `bash install.sh [--global]` | 开发者装环境时一次性 | 一次 |
| **项目配置 Layer 0**(用户侧) | `rddf setup ai-context` | 每个用户项目首次使用 rdd-workflow 时 | 每项目一次 |
| **项目诊断** | `rdd-doctor --category ai-context-bootstrap` | 任何时候可主动检查 | 按需 |
| **Skill Layer 1**(用户调用时) | SKILL.md 自包含 | 用户调 `skill_use("guide")` 等 | 每次 |
| **docs/ 分发**(工具内部 docstring) | `install.sh --with-docs`(默认 OFF) | 工具安装时可选 | 一次 |

**触发场景**

- 场景 A:用户在新项目执行 `bash install.sh`,期望"装完即用",实际 SKILL.md 中 docs/architecture/* 反向引用全部失效。
- 场景 B:第三方项目下,AI agent 启动新 session,看到 `skill_use()` 列表但不知道何时调哪个,推荐器 `guide` 未被显式调用 → 用户提问"如何管理 change?"时 AI 不会主动建议 rdd-workflow。
- 场景 C:Hub-Spoke 联邦已用 `spoke-system-prompt-injection` 注入 Hub 协议,但**没有 rdd-workflow 核心用法块** — Spoke AI 知道 Hub,但不知道怎么用 rdd-workflow。

**不修的代价**

- 226 个现有 improvement 中,任何引用 `docs/architecture/*` 的 SKILL.md 都会失效(目前经 grep 验证有 2 处:`skills/roadmap/SKILL.md` + `skills/rdd-hub-bootstrap/SKILL.md`)。
- 第三方项目采用率下降(用户装完发现"装了什么不知道")。
- 与 `add-spoke-system-prompt-injection`(已批准)的 Hub 协议不对等(Hub 协议有注入,rdd-workflow 核心用法没有)。

## 范围

**In Scope**

1. **Layer 1 修复 — SKILL.md 自包含**(per Oracle 评审,grep 验证仅 2 处失效,**不**扩散修其他 25 个 skill):把现有 2 个 SKILL.md 顶部"概念入门"章节从"链接外部 docs/"改为**自包含精简版**(每文件 ≤ 40 行),**不**依赖外部 docs/:
   - `skills/roadmap/SKILL.md` L21-29 重写(roadmap 5 维概念 + 主文档 sentinel 区域 + Sprint/Phase 正交关系)
   - `skills/rdd-hub-bootstrap/SKILL.md` L46-50 重写(rdd-hub 核心用法 + 安装命令 + 入口)
   - 用 `rdd-doctor --category docs-consistency` 静态拦截其余 25 个 skill 引入新外部引用

2. **Layer 0 修复 — AI agent 上下文入口**(per 2026-09-21 语义纠正):**新增 `rddf setup ai-context` 命令 + 新增 `_lib/cli/setup_cmd.py`**,部署 Layer 0 协议块到目标项目根的 AI 配置文件:
   - **SSOT 模板**:`_lib/templates/layer0_rdd_workflow_usage.md`(单一 source of truth,任何部署路径引用同一文本)
   - **协议块内容 5 段结构**(per Oracle 设计):
     1. 身份声明:本项目已安装 rdd-workflow(OpenSpec 工作流技能包)
     2. 推荐入口:`skill_use("guide")`
     3. 核心流程:`rdd-arch → rdd-planner → rdd-builder → rdd-verifier`
     4. 旁路规则:≤2 文件且 ≤3 任务且无公开 API 变更 → `skill_use("rdd-quick")`
     5. 自助诊断:`rddf doctor --category ai-context-bootstrap`
   - **检测顺序**:`AGENTS.md` → `.cursorrules` → `CLAUDE.md` → `.clinerules` → `.continue/rules/*.md` → `.github/copilot-instructions.md`
   - **多文件并存行为**:若存在多个 AI 配置文件,**都追加**(各自 sentinel,内容相同 — 牺牲 token 换多工具覆盖;幂等 sentinel 防重复)
   - **都不存在** → **创建 `AGENTS.md`**(per 决策"也创建 AGENTS.md(默认)")
   - **Sentinel**:`<!-- RDD-WORKFLOW-CORE-USAGE-START -->` / `<!-- RDD-WORKFLOW-CORE-USAGE-END -->`,幂等
   - **块大小 ≤ 30 行**(约 400-600 tokens/文件)
   - **支持 `--dry-run`**(预览)+ **`--yes`**(跳过确认,CI 用)+ **`--uninstall`**(移除已注入块,对等 spoke-system-prompt-injection 的 `--uninstall`)
   - **用户删除 Layer 0 块后重跑** → sentinel 消失 → 重新追加(删除即重置,文档化此行为;不引入 dismissed 状态记忆,过度设计)

3. **rdd-doctor 新 category**:`ai-context-bootstrap`(独立于 `docs-consistency`):
   - 静态检测目标项目 AI 配置文件状态
   - 报告:WARN/INFO 提示 `rddf setup ai-context` 可用
   - **调用路径**:`rddf doctor --category ai-context-bootstrap`(CLI 注册,可发现;**不**用 `bash skills/...`,因第三方项目无 `skills/` 相对路径 — per Oracle P0 修正)

4. **`rddf init` 输出末尾 hint**:成功执行后打印 "💡 下一步:`rddf setup ai-context`(让 AI agent 启动时知道本项目装了 rdd-workflow)";在 ADR-0052 记录为何 `rddf setup` 不合并为 `rddf init --ai-context`(保持 install ≠ config 语义,per Oracle P1)

5. **install.sh 扩展 — 可选 docs/ 分发**(工具内部 docstring 引用,**仅复制被引用子集**:per Oracle P2 优化):在 `install_per_project()` 末尾新增 `--with-docs` flag,**默认 OFF**,显式开启后**只复制**被 SKILL.md 引用的 2 个文件:
   - `docs/architecture/roadmap-organization.md`(供 `skills/roadmap/SKILL.md` Layer 1 章节内部引用)
   - `docs/rdd-hub-bootstrap.md`(供 `skills/rdd-hub-bootstrap/SKILL.md` Layer 1 章节内部引用)
   - 复制到 `$TARGET_DIR/.opencode/skills/rdd-workflow/docs/`(注意:**在工具子目录**,不是项目根)

6. **新文档**:`docs/architecture/layer-0-progressive-context.md`(独立文档,非 Layer 0 块本身;per Oracle 设计):详细描述渐进式上下文架构(Layer 0 → 1 → 2 → 3)+ Mermaid 架构图 + 多重保险机制矩阵 + 上下文窗口预算 + 扩展性约定。**供开发者参考,不通过 install.sh 分发**。

7. **测试覆盖**(per Oracle P2 缺口补充):
   - `tests/integration/test_setup_ai_context.bats`(≥ 8 cases):AGENTS.md 创建、6 种 AI 配置文件追加、幂等、`--dry-run` 输出格式、`--uninstall` 移除、UTF-8/中文内容保留、目标目录非 git 仓库、Hub 协议共存
   - `tests/integration/test_skill_layer1_self_contained.bats`(≥ 3 cases):SKILL.md 无外部 docs/ 引用(`../docs/` `../../docs/` 零匹配)
   - `tests/integration/test_install_with_docs.bats`(≥ 5 cases):`--with-docs` 复制**被引用子集**而非整个 docs/、幂等、不写入项目根
   - `tests/integration/test_doctor_ai_context_bootstrap.bats`(≥ 4 cases):`rddf doctor --category ai-context-bootstrap` 在各种 AI 配置状态下输出正确
   - `tests/integration/test_layer0_sentinel_order.bats`(NEW per Oracle):Hub sentinel 与 Layer 0 sentinel **顺序稳定性**(重复交替运行 deploy.sh + setup 不互相移动对方块)
   - `tests/unit/test_rddf_setup_help.bats`:`rddf setup --help` 包含 ai-context 子命令文档
   - `tests/unit/test_layer0_template_sso.bats`:**Layer 0 协议块渲染输出 == SSOT 模板**(防漂移)
   - `tests/integration/test_rddf_init_hint.bats`:`rddf init` 成功输出末尾含 setup hint

8. **新增 ADR-0052**(per Oracle 范围建议:单 ADR):内容 = (a) install≠setup≠doctor 三层分工及理由;(b) Layer 0 块 SSOT 与 ≤30 行纪律;(c) `--with-docs` 默认 OFF;(d) sentinel 命名约定 `RDD-WORKFLOW-*-START`;(e) 多 AI 配置文件并存时"都追加"决策。

9. **rdd-doctor `docs-consistency` category 增强**:静态检查所有 `skills/*/SKILL.md` 中无 `../docs/` `../../docs/` 引用。

**Out Scope**

- **不修改 `_lib/` 既有模块**;允许新增 `_lib/cli/setup_cmd.py` + `_lib/templates/layer0_*.md` + `_lib/cli/setup.py`(per Oracle P0 修正:CLI 必须落在 `_lib/cli/`)
- 不修改 226 个现有 improvement 中已批准归档的(只新增 Layer 0 测试 + 安装路径)
- 不支持 **Per-tool Layer 0 块自定义**(Layer 0 块是单一 source of truth,统一附加到任何 AI 配置文件)
- 不创建独立 skill `rdd-workflow-bootstrap`(避免 skill 数量膨胀;改用 CLI 命令 `rddf setup ai-context`)
- **不修改 spoke-system-prompt-injection**(本提案 Layer 0 完全独立实现,零代码共享 — per Oracle P0 修正;仅复用 sentinel 追加模式作为设计参考)
- 不修改 install.sh 默认行为(`bash install.sh` 无参数字节级不变)
- 不实现 `--with-docs` 默认 ON(per 决策 Q2)
- 不在 install.sh 中嵌入 Layer 0 部署(per 2026-09-21 语义纠正)
- **不引入 dismissed 状态记忆**(per Oracle P1:删除即重置是最简可预测语义,过度设计)
- 不支持 Layer 4/5/6 扩展(per Oracle P2:层数封顶 3,扩展走"新 sentinel 块"维度如 `RDD-WORKFLOW-HUB-USAGE`)

## 关键场景

### 场景 1:第三方项目安装 — SKILL.md 自包含

```text
GIVEN  第三方项目执行 bash install.sh(无 --with-docs)
AND    skills/roadmap/SKILL.md 顶部 Layer 1 章节已重写为自包含版
WHEN   安装完成
THEN   $TARGET/.opencode/skills/rdd-workflow/skills/roadmap/SKILL.md 中
       无任何 ../docs/ 或 ../../docs/ 引用
AND    AI agent 阅读 SKILL.md 时即可获得 Roadmap 概念入门
       无需访问目标项目 docs/ 目录
```

### 场景 2:第三方项目安装 + docs/ 分发(显式 opt-in)

```text
GIVEN  第三方项目执行 bash install.sh --with-docs
WHEN   安装完成
THEN   $TARGET/.opencode/skills/rdd-workflow/docs/architecture/roadmap-organization.md 存在
AND    SKILL.md 中可选引用(如保留相对路径)能解析到该文件
AND    重复运行 --with-docs 检测 sentinel 不重复复制
```

### 场景 3:第三方项目首次使用 — Layer 0 部署(per 2026-09-21 语义纠正)

```text
GIVEN  开发者已运行 bash install.sh --global(开发者侧一次性)
AND    第三方项目 /path/to/project 是该开发者的一个新项目
WHEN   开发者运行 cd /path/to/project && rddf setup ai-context
THEN   检测目标项目 AI 配置文件:
       - 都不存在 → 创建 ./AGENTS.md 含 Layer 0 协议块
       - .cursorrules 存在 → 追加到末尾(sentinel 幂等)
       - CLAUDE.md 存在 → 追加到末尾
       - 多个存在 → 都追加(各自 sentinel)
AND    Layer 0 块内容 ≤ 30 行:已安装 rdd-workflow + 推荐入口 skill_use("guide") +
       核心流程 4 阶段 + rdd-quick 旁路
AND    重复运行检测 sentinel 不重复注入(idempotent)
```

### 场景 4:第三方项目首次 — 自动引导(诊断 + 推荐)

```text
GIVEN  第三方项目已运行 rddf setup ai-context 完成
WHEN   开发者运行 rddf doctor --category ai-context-bootstrap
       (per Oracle P0:用 CLI 而非 bash skills/.../,因第三方项目无 skills/ 相对路径)
THEN   报告目标项目 AI 上下文状态:
       - AGENTS.md 已含 Layer 0 块: ✅ 健康
       - AGENTS.md 不存在: ⚠️ WARN 提示 rddf setup ai-context 可用
       - 已含但缺失 Hub 协议(若用 Hub): INFO 提示 spoke-system-prompt-injection
AND    不修改文件(read-only)
```

### 场景 5:Hub 项目 + Layer 0 共存

```text
GIVEN  rdd-hub 项目同时启用 Hub-Spoke 联邦 + rdd-workflow
WHEN   bash install.sh --spoke-init(部署 Hub 协议)
       + rddf setup ai-context(部署 rdd-workflow Layer 0)
THEN   .cursorrules 同时包含 <!-- RDD-HUB-PROTOCOL-START --> 块
                          + <!-- RDD-WORKFLOW-CORE-USAGE-START --> 块
AND    两个 sentinel 互不干扰,idempotent 重复运行
       (顺序稳定性测试:test_layer0_sentinel_order.bats)
```

### 场景 6:AI Agent 启动 — 渐进式上下文加载

```text
GIVEN  目标项目已部署 Layer 0(AGENTS.md 含 Layer 0 块)
WHEN   AI agent(Claude Code / Cursor / ...)启动新 session
THEN   自动加载 AGENTS.md 内容(Layer 0)
AND    AI 知道:已装 rdd-workflow + 推荐入口 skill_use("guide") + 核心流程 + rdd-quick 旁路
WHEN   AI agent 看到用户问题"如何管理 change?"
THEN   AI 主动建议:本项目已装 rdd-workflow,推荐 skill_use("guide")
WHEN   用户调用 skill_use("guide")
THEN   guide skill 加载 skills/guide/SKILL.md(Layer 1)
       → 给出工作流推荐 + 详细命令
WHEN   用户进一步调 skill_use("rdd-arch") 等
THEN   对应 SKILL.md 自包含该 skill 的概念入门(Layer 1 +)
```

### 场景 7:静态检查拦截 SKILL.md 外部引用

```text
GIVEN  skills/<X>/SKILL.md 包含 ../docs/ 或 ../../docs/ 引用
WHEN   跑 rddf doctor --category docs-consistency
       (per Oracle P0:用 CLI 而非 bash skills/...)
THEN   报告 WARNING/CRITICAL 列出所有违规 SKILL.md
AND    不阻断,但 CI 可配置 STRICT_DOCS_CONSISTENCY_GATE=yes 升级为硬阻断
```

### 场景 8:`--uninstall` 对等 spoke-system-prompt-injection

```text
GIVEN  目标项目已部署 Layer 0(任一 AI 配置文件含 Layer 0 块)
WHEN   开发者运行 rddf setup ai-context --uninstall
THEN   移除所有 AI 配置文件中的 <!-- RDD-WORKFLOW-CORE-USAGE-START --> ... <!-- END --> 块
AND    保留其他内容(Hub 协议块、用户原内容)不变
AND    退出 0,打印"Layer 0 block removed from N files"
```

### 场景 9:用户删除 Layer 0 块后重跑 setup

```text
GIVEN  目标项目 AGENTS.md 原含 Layer 0 块
AND    用户手动删除该块(或个人偏好不需要)
WHEN   开发者重跑 rddf setup ai-context
THEN   sentinel 消失 → setup 重新追加(删除即重置,最简可预测语义)
AND    文档化此行为,不引入 dismissed 状态文件(过度设计)
```

## 技术约束

1. **MUST NOT 改动 `_lib/` 任何 Python 代码**(本提案是 install.sh + docs + SKILL.md + rddf CLI 新增子命令 + rdd-doctor 新 category 改动)
2. **MUST NOT 修改 226 个现有 improvement 中已批准的提案**(避免回溯)
3. **MUST 保持 install.sh 向后兼容**:`bash install.sh`(无参数)行为字节级不变;新 flag 默认关闭
4. **MUST 不在 install.sh 中嵌入 Layer 0 部署**(per 2026-09-21 语义纠正:install.sh 是开发者侧工具安装,不是用户侧项目配置)
5. **MUST 保持 idempotent**:`rddf setup ai-context` 重复运行 + `--with-docs` 重复运行都检测 sentinel 不重复注入
6. **MUST NOT 隐式修改用户项目根目录**:`--with-docs` 必须显式 flag 开启;`rddf setup ai-context` 创建 AGENTS.md 时必须明确提示用户(确认 prompt 或 dry-run)
7. **SHOULD 单一 source of truth**:Layer 0 块文本由 `_lib/templates/layer0_rdd_workflow_usage.md` 维护,任何 AI 工具部署时引用同一文本
8. **MUST 验证 SKILL.md Layer 1 自包含**:通过 grep 静态检查所有 `skills/*/SKILL.md` 中无 `../docs/` `../../docs/` 引用(可在 rdd-doctor 加 category)
9. **Layer 0 协议块大小上限 ≤ 30 行**(避免污染 AI 配置文件)
10. **MUST 修复 `add-improve` SKILL.md 文档缺口**(per 2026-09-21 attach 失败教训):`--project-id` 实际是 Phase Skeleton Theme 列精确字符串(中文),不是项目名;必须新增"attach --project-id 实际语义"章节 + 用 `rddf planner attach --help` 输出同步
11. **Layer 0 部署应支持 dry-run**:首次部署前给用户预览(避免静默写入);`--yes` 跳过确认

## 验收标准

- [ ] `skills/roadmap/SKILL.md` Layer 1 章节 ≤ 40 行,无外部 docs/ 引用
- [ ] `skills/rdd-hub-bootstrap/SKILL.md` Layer 1 章节 ≤ 40 行,无外部 docs/ 引用
- [ ] `bash install.sh`(默认)行为字节级不变(diff 验证)
- [ ] `bash install.sh --with-docs` **只复制被引用子集**(`roadmap-organization.md` + `rdd-hub-bootstrap.md` 2 篇,非整个 docs/)到 `$TARGET/.opencode/skills/rdd-workflow/docs/`
- [ ] `bash install.sh` 不嵌入 Layer 0 部署(语义纠正验证)
- [ ] 新增 `_lib/cli/setup_cmd.py`,`rddf setup ai-context` 子命令注册到 `rddf --help`
- [ ] `rddf setup ai-context` 在空目标项目根创建 `AGENTS.md` 含 Layer 0 块(≤ 30 行,**5 段结构**含旁路规则)
- [ ] `rddf setup ai-context` 在已存在 `.cursorrules` / `CLAUDE.md` 的项目追加 Layer 0 块
- [ ] `rddf setup ai-context` 在多个 AI 配置文件并存时**都追加**(按工具维度覆盖)
- [ ] `rddf setup ai-context` 重复运行检测 sentinel 不重复注入(idempotent)
- [ ] `rddf setup ai-context --dry-run` 给出部署预览
- [ ] `rddf setup ai-context --uninstall` 移除所有 AI 配置文件中的 Layer 0 块(保留其他内容)
- [ ] `rddf setup ai-context` 在用户删除块后重跑时**重新追加**(删除即重置)
- [ ] `rddf doctor --category ai-context-bootstrap` ≥ 4 cases(per Oracle 路径修正:CLI 而非 bash)
- [ ] `rddf doctor --category docs-consistency` ≥ 3 cases 静态检查 SKILL.md 外部 docs/ 引用
- [ ] `rddf init` 成功输出末尾含 "💡 下一步:`rddf setup ai-context`" hint
- [ ] Layer 0 协议块 ≤ 30 行,内容**5 段结构**(身份 + 入口 + 4 阶段 + 旁路规则 + 自助诊断)
- [ ] Layer 0 协议块渲染输出 == SSOT 模板 `_lib/templates/layer0_rdd_workflow_usage.md`(防漂移)
- [ ] `tests/integration/test_setup_ai_context.bats` ≥ 8 cases 全绿(含 6 文件追加 + 幂等 + dry-run + uninstall + UTF-8 + 非 git 目录 + Hub 共存)
- [ ] `tests/integration/test_skill_layer1_self_contained.bats` ≥ 3 cases 全绿
- [ ] `tests/integration/test_install_with_docs.bats` ≥ 5 cases 全绿(验证只复制被引用子集)
- [ ] `tests/integration/test_doctor_ai_context_bootstrap.bats` ≥ 4 cases 全绿
- [ ] `tests/integration/test_layer0_sentinel_order.bats`(NEW):Hub sentinel + Layer 0 sentinel 顺序稳定性
- [ ] `tests/unit/test_rddf_setup_help.bats` 验证 `--help` 包含 ai-context 子命令
- [ ] `tests/unit/test_layer0_template_sso.bats`:Layer 0 渲染 == SSOT 模板
- [ ] `tests/integration/test_rddf_init_hint.bats`:`rddf init` 输出末尾含 setup hint
- [ ] `docs/architecture/layer-0-progressive-context.md` 新增(含 Mermaid 架构图 + 多重保险机制 + 上下文窗口预算 + 扩展性约定)
- [ ] `docs/adr/ADR-0052-layer-0-progressive-context.md` 已采纳(单 ADR,5 主题:分层 + SSOT + 默认 OFF + sentinel 约定 + 多文件决策)
- [ ] `add-improve` SKILL.md 新增"attach --project-id 实际语义"章节
- [ ] `improvement-suggestions.md` 状态由 pending → approved
- [ ] 全量回归 `./test.sh --full --regression` 通过(无新增失败)

## 能力清单 (Capabilities)

本次实施为 rdd-workflow 新增 3 项能力:

1. **`--with-docs` flag** — install.sh 项目内安装可选分发 docs/architecture/,第三方项目可获得完整架构文档(默认 OFF)
2. **Layer 0 协议块** — spoke-system-prompt-injection 扩展,5 种 AI 工具配置文件自动包含 rdd-workflow 核心用法提示(已安装 + 推荐入口 + 4 阶段 + rdd-quick 旁路)
3. **SKILL.md Layer 1 自包含** — 所有 SKILL.md 顶部导览不再依赖 docs/ 外部引用,install.sh 安装后零 404

## 影响 (Impact)

| 维度 | 影响 |
|---|---|
| **正面** | 修复 SKILL.md 反向引用失效(本提案直接消除 2026-09-21 发现的 roadmap-organization.md 失效问题);第三方项目 AI agent 可发现 rdd-workflow;安装后用户能获得完整架构文档;与 spoke-system-prompt-injection Hub 协议对等 |
| **负面/风险** | `--with-docs` 默认 OFF 避免噪音;Layer 0 协议块 ≤ 30 行,不污染 AI 配置文件;对现有 226 个 improvement 无回溯影响 |
| **兼容性** | install.sh 默认行为字节级不变;spoke-system-prompt-injection Hub 协议不变;Layer 0 是纯新增独立 sentinel |
| **依赖** | 复用 `skills/spoke-system-prompt-injection` 的部署机制(per `add-spoke-system-prompt-injection` 提案 L122-128 deploy.sh 结构) + sentinel 模式(per ADR-0021 per-skill 迁移模式) |
| **覆盖范围** | 7 个新文件(install.sh + 4 个测试 + ADR-0052 + spoke-system-prompt.md 章节)+ 3 个文件修改(SKILL.md + spoke-system-prompt-injection/templates + rdd-doctor 类别) |

---

## 决策记录

### 2026-09-21 初始决策(用户批准)

| 决策点 | 用户选择 |
|---|---|
| 提案命名 | `fix-skill-post-install-discoverability` |
| `--with-docs` flag 默认行为 | 默认 OFF,显式开启 |
| Layer 0 协议块内容范围 | 含完整 4 阶段 + rdd-quick 旁路 |
| Layer 0 部署目标 | 也创建 AGENTS.md(默认),不存在时主动创建 |

### 2026-09-21 根本性语义纠正(对话第 9 轮)

| 决策点 | 旧(错) | 新(正) |
|---|---|---|
| Layer 0 部署触发器 | `bash install.sh --spoke-init`(挂在工具安装流程) | `rddf setup ai-context`(独立 CLI 命令) |
| 责任分层 | install.sh 双向职责混合 | install.sh = 开发者装工具;rddf setup = 用户配项目 |
| 配置入口选择 | spoke-system-prompt-injection(Hub-Spoke 联邦附属) | rdd-doctor + 新 CLI 命令(独立可发现) |

**纠正理由**:用户明确指出 "install.sh 只是安装项目,而配置用户项目我认为用 rdd-doctor 技能更好"。我之前把 Layer 0 部署挂在 install.sh 下是**根本性的语义错误** — install.sh 是开发者一次性安装 rdd-workflow 工具,不是"在每个用户项目里配置 rdd-workflow"。

### 2026-09-21 attach 命令错误教训

`rddf planner attach --project-id` 的实际语义是 Phase Skeleton Theme 列的精确中文字符串,不是项目名。我之前给的 `rddf planner attach fix-skill-post-install-discoverability --project-id rdd-workflow --phase phase-3` 失败,正确命令是 `--project-id "流程定制层" --phase phase-3`。此教训已加入验收标准(`add-improve` SKILL.md 文档缺口修复)。

### 2026-09-21 Oracle 评审补充(`ses_f3d1321d5ffed98yuqtGZXdk4B`)

Oracle 评审给出 ⚠️ partial 结论,识别 **3 个 P0 内部矛盾** + **3 个 P1 语义模糊** + **编辑瑕疵**,并设计完整的渐进式上下文架构(Mermaid 图 + 4 层规范 + 多重保险矩阵)。

**已应用的 Oracle 建议**:

| # | 类别 | 修改 |
|---|---|---|
| 1 | P0 | 技术约束放宽:允许新增 `_lib/cli/setup_cmd.py` + `_lib/templates/layer0_*.md` |
| 2 | P0 | 能力清单 + Out Scope 统一:Layer 0 完全独立实现,零代码共享 |
| 3 | P0 | 场景 4 doctor 路径改 `rddf doctor`(bash skills/.../ 在第三方项目失效) |
| 4 | P1 | 多 AI 配置文件并存"都追加"加理由说明(按工具维度覆盖) |
| 5 | P1 | `rddf init` 输出末尾 hint 引导(避免 setup / init 混淆) |
| 6 | P1 | 用户删除块后重跑 setup 行为文档化(删除即重置,不引入 dismissed 状态) |
| 7 | P2 | Layer 0 块升级为 5 段结构(增加"旁路规则"段:≤2 文件 & ≤3 任务 → rdd-quick) |
| 8 | P2 | Layer 2 docs/ 分发**只复制被引用子集**(`roadmap-organization.md` + `rdd-hub-bootstrap.md`),非整个 docs/ |
| 9 | P2 | Layer 1 不扩散(只修 2 个 SKILL.md,其余 25 个用 docs-consistency 静态拦截) |
| 10 | P2 | 新增 `--uninstall`(对等 spoke-system-prompt-injection 的 `--uninstall`) |
| 11 | P2 | Layer 0 块 SSOT 模板 `_lib/templates/layer0_rdd_workflow_usage.md` |
| 12 | P2 | ADR-0052 范围明确(单 ADR,5 主题) |
| 13 | P2 | 测试缺口补充:UTF-8 保留、非 git 目录、sentinel 顺序稳定性、Layer 0 SSOT、rddf init hint |
| 14 | P2 | 场景编号去重(原 6 + 6 改为 6 + 7 + 8 + 9) |
| 15 | 编辑 | 删除重复段(L50-60 触发场景 + 不修的代价 2 次重复) |

**Oracle 4 个关键决策建议采纳**:
1. ✅ 新增 `_lib/cli/setup_cmd.py` 并放宽约束 1
2. ✅ doctor 统一走 `rddf doctor` CLI
3. ✅ Layer 0 默认追加到所有已存在的 AI 配置文件
4. ✅ 不提供 dismissed 状态记忆

**Oracle 上下文窗口预算分析采纳**:
- 30 行块 ≈ 400-600 tokens/文件
- 单项目多工具并存时最坏 ~1800 tokens,占主流模型 context <1%
- 纪律:Layer 0 永远 ≤30 行,增量需求走新 sentinel 块

**Oracle 扩展性约定采纳**:
- 不增加 Layer 4/5/6
- 层数封顶 3(0=协议块 / 1=SKILL 自包含 / 2=分发 docs / 3=仓库参考)
- 扩展走"新 sentinel 块"维度(`RDD-WORKFLOW-*-START` 命名约定)

---

*提案生成背景: 2026-09-21 对话发现 — 用户在为 roadmap-organization.md 沉淀时,识别出 install.sh 分发鸿沟导致 SKILL.md 反向引用必然失效,且第三方项目 AI agent 不知道 rdd-workflow 已安装。讨论后同意通过走完整 rdd-workflow 流程(arch → planner → builder → verifier)实施完整修复。经过 attach 失败教训 + 根本性语义纠正 + Oracle 评审补充(3 P0 + 3 P1 + 编辑瑕疵 + 渐进式架构设计)后,提案已重构为正确的 install.sh(开发者侧)/ rddf setup ai-context(用户侧)/ rdd-doctor(诊断侧)三层架构 + 完整 Layer 0→1→2→3 渐进式上下文注入设计。*
