[
  {
    "name": "fix-silent-exception",
    "priority": "P0",
    "source": "Oracle 代码审查 2026-07-19 #4",
    "status": "已完成",
    "phase": "default",
    "category": "general",
    "description": "## 架构依据\n- Oracle 代码审查结论：`except Exception: pass` 在 loop_engine.py 中 5 处出现，位于 verify_goal/_load_interaction_mode/run 等关键路径。一旦 state schema 漂移或 event_log I/O 失败，故障表现为\"循环卡住/无输出\"，极难诊断。\n\n## 范围\n- **In Scope**:\n  - loop_engine.py:203-205 — state.update_field 失败时静默 pass → 加 event_log.record\n  - loop_engine.py:274-277 — scan_state 阶段 state 更新失败\n  - loop_engine.py:303-305 — generate_plan 阶段 state 更新失败\n  - loop_engine.py:339-342 — execute_plan 阶段 state 更新失败\n  - loop_engine.py:355-358 — adapt 阶段 state 更新失败\n  - 对应单元测试\n- **Out Scope**:\n  - 不修改 fs_watcher.py 的 `except OSError: pass`（文件监听 cleanup 的标准模式）\n  - 不修改 gate.py 已有 logging 的 except 块\n  - 不引入新的 event type\n\n## 关键场景\n- GIVEN state.update_field() 抛出异常, WHEN 静默 pass, THEN event_log 记录 ERROR_OCCURRED 事件\n- GIVEN 连续 5 处静默错误, WHEN 用户查看 event_log, THEN 五条错误日志可追溯\n\n## 技术约束\n- MUST 复用 loop_engine.py:167-173 已有的 `self.event_log.record(EventType.ERROR_OCCURRED, Severity.ERROR, ...)` 模式\n- MUST NOT 删除原有 pass（保持控制流不变），仅在 pass 前追加日志\n- SHOULD 每条记录包含异常信息作为 context\n\n## 验收标准\n- 5 处 `except Exception: pass` 全部替换为 `event_log.record` + pass 的双行模式\n- 1-2 个回归测试验证日志写入\n- 所有现有测试通过",
    "effort": "1-2h"
  },
  {
    "name": "add-config-validation",
    "priority": "P0",
    "source": "Oracle 代码审查 2026-07-19 #8",
    "status": "已完成",
    "phase": "default",
    "category": "general",
    "description": "## 架构依据\n- Oracle 结论：root config.yaml 是用户可编辑入口，config.py::ConfigParser 消费方。一旦用户改了 yaml key（如 max_iterations → maxIterations），ConfigParser 静默返回 None，Loop 引擎用默认值 100 — 静默降级而非报错。这是用户侧可触达的真问题。\n- ADR-0004 §3: Loop 引擎安全机制配置\n\n## 范围\n- **In Scope**:\n  - config.py::ConfigParser.load() 末尾加 validate() 方法\n  - skills/_lib/schemas/config_schema.json（jsonschema，项目已用）\n  - schema 校验 required keys + 类型（max_iterations, max_retries 等）\n  - 失败时 raise ConfigError(...) 而非静默 fallback\n  - 对应单元测试\n- **Out Scope**:\n  - 不修改 config.yaml 格式\n  - 不修改 LoopEngine 的配置消费逻辑\n  - 不校验 phase_templates.yaml\n\n## 关键场景\n- GIVEN config.yaml 中 max_iterations 拼写为 maxIterations, WHEN ConfigParser.load(), THEN 抛出 ConfigError 而非静默使用默认值\n- GIVEN config.yaml 合法完整, WHEN ConfigParser.load(), THEN validate() 通过, 行为不变\n\n## 技术约束\n- MUST 使用现有 skills/_lib/schemas/ 下的 jsonschema 模式（项目已有依赖）\n- MUST 保持向后兼容：缺失 schema 文件时跳过验证\n- SHOULD 验证逻辑放入 ConfigParser 的方法，而非独立函数\n\n## 验收标准\n- config_schema.json 约 50 行\n- validate() 方法在 load() 末尾被调用\n- 2-3 个单元测试覆盖合法/非法/缺失 schema 场景\n- 所有现有测试通过",
    "effort": "2-3h"
  },
  {
    "name": "remove-ci-redundant-bats",
    "priority": "P1",
    "source": "Oracle 代码审查 2026-07-19 #1 降级版",
    "status": "已完成",
    "phase": "default",
    "category": "general",
    "description": "## 架构依据\n- Oracle 验证：CI 的 `bats tests/ --recursive` 已运行全部 704 个 test cases。后续两个显式 `bats tests/integration/test_*.bats` 步骤是冗余的双重运行（静态分类 + worktree 分类），浪费 CI 时间。\n\n## 范围\n- **In Scope**:\n  - .github/workflows/test.yml 中删除两个显式 bats 步骤\n  - 保留 `bats tests/ --recursive` 作为唯一 bats 步骤\n- **Out Scope**:\n  - 不修改 Python 测试步骤\n  - 不修改 assertion quality gate\n  - 不修改其他 CI 配置\n\n## 关键场景\n- GIVEN CI 运行, WHEN 进入 bats 阶段, THEN 只运行一次 `bats tests/ --recursive`, 所有 704 个 test cases 被覆盖\n\n## 技术约束\n- MUST 保留 Python unit + integration 测试步骤\n- MUST 保留 assertion tautology gate\n- MUST 保留 arch/change alignment gate\n- MUST 保留 spec validation gate\n\n## 验收标准\n- CI 配置删除 2 个显式 bats 步骤\n- CI 运行时间缩短约 30-60 秒\n- 所有 704 个 bats test cases 仍通过 `--recursive` 覆盖",
    "effort": "5min"
  },
  {
    "name": "update-agents-module-map",
    "priority": "P1",
    "source": "Oracle 代码审查 2026-07-19 遗漏 #3",
    "status": "已完成",
    "phase": "default",
    "category": "general",
    "description": "## 架构依据\n- Oracle 发现：AGENTS.md 的关键目录章节中，\"skills/_lib/\" 列表缺少 `core/` / `loop/` / `schedulers/` 子目录标注。审查者因此误以为 loop_state.py/event_queue.py 等文件不存在。AGENTS.md 是项目主要文档入口，模块地图过时影响所有下游开发者和 AI 审查者。\n\n## 范围\n- **In Scope**:\n  - AGENTS.md \"关键目录\"章节中 _lib/ 部分更新：标注 core/（6 文件）、loop/（15 文件）、schedulers/ 子目录\n  - 更新 Python 模块描述列表，标注每个模块的子目录归属\n- **Out Scope**:\n  - 不更新 ADR 文档\n  - 不更新 skill 文件\n  - 不更新测试文档\n\n## 技术约束\n- MUST 保持 AGENTS.md 的现有格式和风格\n- MUST 更新文件计数以反映实际文件数\n- SHOULD 添加简单树形结构展示子目录层次\n\n## 验收标准\n- AGENTS.md 中 _lib/ 目录树包含 core/、loop/、schedulers/、schemas/、plugins/ 子目录\n- Python 模块列表清晰标注每个文件在子目录中的位置\n- 文件计数准确",
    "effort": "10min"
  },
  {
    "name": "split-iteration-module",
    "priority": "P1",
    "source": "Oracle 代码审查 2026-07-19 #7",
    "status": "已完成",
    "phase": "default",
    "category": "general",
    "description": "## 架构依据\n- Oracle 验证：iteration.py 739 行，是最大单 Python 文件，混合 schema 定义 + CRUD + CLI 渲染 + merge 逻辑 4 类职责。每次新增 hook 需通读全文。\n- ADR-0004 §3: 模块单一职责原则\n\n## 范围\n- **In Scope**:\n  - skills/_lib/iteration/ 子目录创建\n  - iteration/schema.py — schema 定义 + validation\n  - iteration/store.py — CRUD + atomic write + merge\n  - iteration/render.py — CLI/status 渲染\n  - iteration/__init__.py — 兼容 re-export\n  - 迁移现有 4-5 个 iteration 相关 unit 测试\n- **Out Scope**:\n  - 不修改 iteration.json schema\n  - 不修改现有 6 个 hooks 的行为\n  - 不引入新功能\n\n## 技术约束\n- MUST 保持 __init__.py re-export 兼容现有 `from skills._lib.iteration import X`\n- MUST NOT 改变公有 API 签名\n- MUST 将拆分与 iteration schema bump 同步（如有）\n\n## 验收标准\n- iteration.py 消失，iteration/ 子目录 3 文件 + __init__.py\n- 所有现有 import 正常工作\n- 所有现有测试通过\n- 无功能变化",
    "effort": "1-2d"
  },
  {
    "name": "add-progressive-linting",
    "priority": "P2",
    "source": "Oracle 代码审查 2026-07-19 #3",
    "status": "已完成",
    "phase": "default",
    "category": "general",
    "description": "## 架构依据\n- Oracle 建议：48 处 Any 用法，7,382 LOC Python 无类型检查。重构时类型回归无保护。Round A/B/C 提取 ~1,500 行 bash 后，下一步若提取 Python，缺类型检查会放大回归风险。\n\n## 范围\n- **In Scope**:\n  - CI 加入 `ruff check skills/_lib/`（快，1 分钟接 CI）\n  - CI 加入 `mypy --strict skills/_lib/core/`（仅 6 个内核文件）\n  - requirements.txt 加入 ruff + mypy\n  - 修复 ruff 发现的明显问题（未用 import、显然 bug）\n- **Out Scope**:\n  - 不对 loop/ 子目录强制类型（动态性高，性价比低）\n  - 不修复所有 48 处 Any\n  - 不引入 bandit/semgrep\n\n## 技术约束\n- MUST 渐进式：新增的 lint 步骤不得因为既有问题而阻塞 CI\n- MUST 使用 `--ignore` 或 per-file 配置来处理遗留问题\n- SHOULD 优先修复 ruff 捕获的未用 import 等安全级问题\n\n## 验收标准\n- CI 包含 ruff 检查步骤\n- CI 包含 mypy core/ 检查步骤\n- ruff 零错误（通过忽略或修复）\n- mypy strict 模式在 core/ 下零错误\n- 所有现有测试通过",
    "effort": "半天"
  },
  {
    "name": "add-plugin-loader-tests",
    "priority": "P2",
    "source": "Oracle 代码审查 2026-07-19 #5 修正版",
    "status": "已完成",
    "phase": "default",
    "category": "general",
    "description": "## 架构依据\n- Oracle 验证：plugin_loader.py 114 行做动态插件加载，是 loop 引擎的可扩展性入口。现有 except 块无 logging。无 dedicated unit test 锁定预期行为。\n\n## 范围\n- **In Scope**:\n  - 3 个 unit test：load 成功 / load 失败 / 重复 load\n  - 测试文件：tests/unit/test_plugin_loader.py\n- **Out Scope**:\n  - 不改动 plugin_loader.py 源码\n  - 不为 loop_state.py 或 event_queue.py 加测试（太小，integration 覆盖足够）\n\n## 技术约束\n- MUST 使用 pytest 和 tmp_path fixture\n- MUST 不依赖外部插件文件\n- SHOULD 测试 `except Exception` 分支（确保失败不静默）\n- SHOULD 遵循现有 test_*.py 命名和风格\n\n## 验收标准\n- tests/unit/test_plugin_loader.py 含 3 个测试函数\n- 加载成功/失败/重复加载场景覆盖\n- 所有现有测试通过",
    "effort": "1-2h"
  },
  {
    "name": "relocate-loop-engine",
    "priority": "P2",
    "source": "Oracle 代码审查 2026-07-19 遗漏 #2",
    "status": "已完成",
    "phase": "default",
    "category": "general",
    "description": "## 架构依据\n- Oracle 发现：loop_engine.py 358 行是 v2.0 引擎入口，却放在 skills/ 根目录与其他 13 个 .md skill 文件并列。AGENTS.md 注明\"在 skills/ 根, 不在 _lib/\"，是历史遗留。\n\n## 范围\n- **In Scope**:\n  - skills/loop_engine.py → skills/_lib/loop_engine.py 迁移\n  - skills/loop_engine.py 保留为 re-export shim（from skills._lib.loop_engine import *）\n  - 更新所有 import 路径\n- **Out Scope**:\n  - 不修改 loop_engine.py 内部逻辑\n  - 不修改公有 API\n\n## 技术约束\n- MUST 保留 skills/loop_engine.py 作为兼容 shim（删除原代码，单行 import）\n- MUST 更新 skills/__init__.py 如有必要\n- SHOULD 更新 AGENTS.md 和 README 中 loop_engine.py 的路径引用\n\n## 验收标准\n- skills/_lib/loop_engine.py 存在且与原文件内容一致\n- skills/loop_engine.py 为单行 re-export\n- 所有现有 import 正常工作\n- 所有现有测试通过",
    "effort": "半天"
  },
  {
    "name": "guide-plan-noninteractive",
    "priority": "P0",
    "source": "复盘改进 #1 — guide-plan 无交互模式",
    "status": "已完成",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- 复盘发现：guide-plan 是人际交互状态机（菜单+read），AI 编排器无法调用。propose_change.py 虽可用但绕过完整流程。\n\n## 范围\n- **In Scope**:\n  - guide-plan.md 入口检测 `--non-interactive` 或 `SKIP_GUIDE_PLAN_MENU=yes` env var\n  - non-interactive 模式跳过菜单，执行默认流程（scan→propose→deps→plan-done）\n  - propose 增加 `--batch-create` 批量从 proposal-suggestions.md 创建 skeleton\n  - 测试覆盖两种模式\n- **Out Scope**:\n  - 不修改人际交互菜单（向后兼容）\n  - 不修改 guide-ship\n\n## 验收标准\n- `SKIP_GUIDE_PLAN_MENU=yes skill_use(\"guide-plan\")` 自动执行完整 plan 流程\n- `skill_use(\"propose\", \"--batch-create\")` 创建所有 pending 建议的 skeleton\n- 不影响现有交互体验",
    "effort": "2-3h"
  },
  {
    "name": "auto-wave-scheduler",
    "priority": "P0",
    "source": "复盘改进 #3 + #4 — 自动 Wave 调度 + iteration 状态自动化",
    "status": "已完成",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- 复盘发现：Wave 切换靠人工判断、iteration.json 状态转换手动操作。manual_deps 已有依赖数据，缺的是自动化消费方。\n\n## 范围\n- **In Scope**:\n  - guide-arch/guide-plan/guide-ship 入口 hook 自动迭代状态转换（planned→proposed→in_worktree→archived）\n  - archived hook 扫描 iteration.json 中 blocker 已解除的 planned change\n  - 输出建议信息“bloker 已解除: change-x, change-y 可以执行”\n  - 不影响现有 hook 行为\n- **Out Scope**:\n  - 不自动调用 guide-ship（仅建议，用户确认）\n  - 不修改 DependencyScheduler（ADR-0010 v2.1 完整版留待后续）\n\n## 验收标准\n- 归档 change-a 后，若 change-b 的 manual_deps=[change-a]，自动打印“建议: change-b blocker 已解除”\n- guide-plan 入口自动设 stage_plan session 状态\n- 测试覆盖 archived→unblocked→suggest 链路",
    "effort": "3-5h"
  },
  {
    "name": "propose-quality-autohook",
    "priority": "P0",
    "source": "Oracle 架构分析 2026-07-21 — Proposal 审查机制 (P0 升级)",
    "status": "已完成",
    "phase": "v2.1",
    "category": "quality",
    "description": "## 架构依据\n- Oracle 审查结论: propose_quality_check.py 是 dead asset (5 项结构性检查存在但从未接入 propose 流程)\n- 当前 propose 没有任何审查环节，低质量 proposal 直接进入 change pipeline\n- 接入 plan_done gate 作为 warning 级 (STRICT_PROPOSE_GATE=yes 升级为 error)\n\n## 范围\n- **In Scope**:\n  - propose.md Phase 4 末尾调用 propose_quality_check.py --change <name>\n  - gate.py plan_done 注册 propose_quality_checks Check (warning 级)\n  - 输出 warnings 不阻断流程\n  - 对应 unit test\n- **Out Scope**:\n  - 不修改 propose_quality_check.py 的 5 项检查逻辑\n  - 不引入新的检查项\n  - 不做 content review (另见 add-propose-content-review)\n\n## 关键场景\n- GIVEN propose Phase 4 创建完 change artifacts, WHEN 自动触发 quality check, THEN 输出 5 项检查结果 (不阻断)\n- GIVEN plan_done 阶段, WHEN STRICT_PROPOSE_GATE=yes, THEN quality check 失败时返回 error 阻断\n\n## 技术约束\n- MUST NOT 阻断默认流程 (warning 级)\n- MUST 复用现有 propose_quality_check.py 的 run_all_checks()\n- SHOULD 遵循 ADR-0007 gate 哲学: warning 不阻断, error 才阻断\n\n## 验收标准\n- propose 执行后终端输出 quality check 结果\n- plan_done gate 含 propose_quality_checks Check\n- STRICT_PROPOSE_GATE=yes 时检查失败返回非零\n- 所有现有测试通过",
    "effort": "1-2h"
  },
  {
    "name": "update-adr-index",
    "priority": "P2",
    "source": "复盘遗留 — ADR 索引表与 README 不同步",
    "status": "已完成",
    "phase": "v2.1",
    "category": "docs",
    "description": "## 架构依据\n- 执行中发现 docs/adr/README.md 索引表只更新到 ADR-0020，但代码库已有 ADR-0021、ADR-0022。\n- test_adr_index.bats 因此一直失败（pre-existing failure #1）。\n\n## 范围\n- **In Scope**:\n  - 更新 docs/adr/README.md 索引表追加 ADR-0021、ADR-0022 行\n  - 保持表格格式一致\n- **Out Scope**:\n  - 不修改 bats 测试（预存在失败会自然解决）\n  - 不修改 ADR 文件本身\n\n## 验收标准\n- README.md 的 ADR 索引表包含 ADR-0021 和 ADR-0022\n- README.md 的进度表（v2.0 ADR 实施状态）包含 ADR-0022\n- test_adr_index.bats 中 ADR 文件检查通过",
    "effort": "15min"
  },
  {
    "name": "fix-rddf-schema-validation",
    "priority": "P0",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W0-1",
    "status": "已完成",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- RDDF session schema validation 基础设施从未生效: SCHEMA_PATH 指向不存在的目录，validate=True 从未传参\n\n## 范围\n- **In Scope**:\n  - 修正 SCHEMA_PATH 指向 skills/_lib/schemas/sessions_schema.json\n  - 在 _read_unlocked() 中启用 schema validation\n  - 3 个 schema validation 测试\n- **Out Scope**:\n  - 不修改 session 数据模型\n  - 不修改 sessions_schema.json 内容\n\n## 验收标准\n- SCHEMA_PATH 指向正确路径且 validation 生效\n- 非法 fields 的 sessions.json 被正确拒绝\n- 合法 sessions.json 正常通过",
    "effort": "0.5天"
  },
  {
    "name": "audit-attach-detach-calls",
    "priority": "P0",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W0-2",
    "status": "已完成",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- 不清楚 attach_change/detach_change 是否被 guide 技能实际调用\n\n## 范围\n- **In Scope**:\n  - 查找所有调用 attach_change / detach_change 的位置\n  - 确认 guide-arch/guide-plan/guide-ship 的 hook 调用链\n  - 输出 audit report\n- **Out Scope**:\n  - 不修改代码（仅 audit）\n\n## 验收标准\n- audit report 列出所有调用点 + 缺失的 hook",
    "effort": "0.25天"
  },
  {
    "name": "add-heartbeat-config",
    "priority": "P1",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W1-1",
    "status": "已完成",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 30 * 60 硬编码\n\n## 范围\n- **In Scope**:\n  - RddfSessionCoordinator 构造函数支持 RDDF_HEARTBEAT_TIMEOUT_SECONDS 环境变量\n  - 支持 RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS 环境变量\n  - check_heartbeat_timeouts() 使用实例属性而非模块常量\n- **Out Scope**:\n  - 不修改 sessions_schema.json（运行时配置）\n\n## 验收标准\n- 默认值仍为 30min / 5min\n- 环境变量可覆盖\n- 3 个测试（默认/覆盖/非法值）",
    "effort": "0.5天"
  },
  {
    "name": "add-rddf-concurrency-tests",
    "priority": "P1",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W1-2",
    "status": "已完成",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- _with_file_lock 使用 LOCK_NB（非阻塞 fail-fast），并发调用会失败而非排队\n- 需要测试验证这一真实语义\n\n## 范围\n- **In Scope**:\n  - tests/integration/test_rddf_session_concurrency.py: multiprocessing.Pool 并发 100 次 create_session\n  - tests/integration/test_rddf_session_cross_session_recovery.py: session 超时→orphaned→恢复全链路\n- **Out Scope**:\n  - 不修改 rddf_session.py 逻辑\n\n## 验收标准\n- 并发测试验证 LOCK_NB 行为（非破坏，非无限重试）\n- 跨 session 恢复测试验证 find_next_recommendation + transfer_ownership",
    "effort": "1.5天"
  },
  {
    "name": "fix-attach-detach-symmetry",
    "priority": "P1",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W1-3",
    "status": "已完成",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- attach_change/detach_change 调用点不对称（基于 W0-2 audit）\n\n## 范围\n- **In Scope**:\n  - rddf_session_hooks.sh 新增 rddf_session_hook_attach\n  - guide-plan Phase 2 完成后调用 attach\n  - guide-ship Phase 1 plan 生成后调用 attach\n- **Out Scope**:\n  - 不修改 detach 逻辑（heartbeat hook 不变）\n\n## 验收标准\n- attach/detach 调用对称\n- 4 个测试（attach 正常/idempotent/detach/hook 集成）",
    "effort": "1天"
  },
  {
    "name": "split-rddf-god-class",
    "priority": "P2",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W2-1",
    "status": "已完成",
    "phase": "v2.1",
    "category": "refactor",
    "description": "## 架构依据\n- RddfSessionCoordinator 507 行，自认 god class\n- 拆分方案: facade + _store.py + _commands.py + _binding.py + _types.py\n\n## 范围\n- **In Scope**:\n  - 拆分 RddfSessionCoordinator 为 5 个模块\n  - facade 保留全部公共方法签名不变\n  - 所有现有调用点不受影响\n- **Out Scope**:\n  - 不修改 schema validation（已在 W0-1 修复）\n  - 不修改会话数据模型\n\n## 验收标准\n- 所有现有 24+10 测试通过（回归）\n- lsp_find_references 验证无遗漏调用点",
    "effort": "1.5天"
  },
  {
    "name": "add-workflow-synthesizer",
    "priority": "P0",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W3-1",
    "status": "已完成",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- 核心诉求：guide 运行时知道哪些阶段已完成/待处理，建议 resume 还是 restart\n- 只读模块，不写 sessions.json\n- 与 add-guide-dashboard 互补：synthesizer 提供数据，dashboard 提供展示\n\n## 范围\n- **In Scope**:\n  - skills/_lib/workflow_synthesizer.py：读取 sessions.json + handoff + iteration + git 状态\n  - 结构化推荐：WorkflowRecommendation + PhaseStatus dataclass\n  - 推荐逻辑：resume/restart/start-arch/all-done 决策树\n  - scan-state.sh 集成 synthesizer 输出到 CONTEXT_LINES\n- **Out Scope**:\n  - 不修改 sessions_schema.json（只读）\n  - 不自动执行推荐（仅建议，用户确认）\n\n## 验收标准\n- synthesizer 输出 WorkflowRecommendation with 置信度\n- 10 个测试覆盖每一条推荐路径",
    "effort": "2天"
  },
  {
    "name": "fix-scan-state-binding",
    "priority": "P0",
    "source": "设计规范前置依赖: docs/superpowers/specs/2026-07-20-dashboard-design.md §Prerequisite",
    "status": "已完成",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- 仪表盘设计规范 docs/superpowers/specs/2026-07-20-dashboard-design.md 明确列出的前置依赖\n- scan-state.sh line 232 存在 syntax bug（变量展开缺闭合 brace），阻塞 session 绑定检测\n\n## 范围\n- **In Scope**:\n  - skills/guide/scripts/scan-state.sh:232 — 修复 local owner 变量展开语法（缺 }）\n  - 将 check_heartbeat_timeouts() 从 scan_session_binding 中解耦提取为独立函数\n  - 验证 rddf dashboard session 区块正确显示绑定\n- **Out Scope**:\n  - 不修改 rddf_session.py（仅修复调用方）\n  - 不修改 dashboard 渲染逻辑\n\n## 验收标准\n- rddf dashboard session 区块显示当前 session 绑定而非 \"(no active session)\"\n- scan_session_binding 不因语法错误提前中断\n- 所有现有测试通过",
    "effort": "0.5h"
  },
  {
    "name": "add-parent-feature-param",
    "priority": "P0",
    "source": "Oracle 架构分析 2026-07-21 — --parent-feature 参数设计",
    "status": "已完成",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- Oracle 审查结论: iteration_schema.json 中 parent_feature 字段已定义 (L99-102) 但从未被任何代码写入 — 是 dead field\n- 当前所有 7 个 changes 全在 __ungrouped__，因为没有 feature- 前缀也没有 parent_feature\n- 激活 parent_feature 字段即可让 change 归入 feature 组，无需新增 feature 状态机\n- 与 ADR-0016 \"extend not replace\" 原则一致 — 扩展已有字段而非新建结构\n- Schema 零变更 (字段已存在)，只需修复写入端\n\n## 范围\n- **In Scope**:\n  - propose_change.py::create_skeleton_change + update_iteration_proposed 加 parent_feature 可选参数\n  - propose_change.sh bash wrapper 加 --parent-feature 参数解析\n  - propose.md Phase 3 菜单交互: 可选 \"归属 feature\" 输入\n  - 拒绝 parent_feature=__ungrouped__ (保留字)\n  - 前向声明语义: parent_feature 指向不存在的 feature 时视为定义新 feature\n  - unit test + bats integration test\n- **Out Scope**:\n  - 不写 feature_view (保持纯派生，feature 命令自动重算)\n  - 不新增 feature create 命令\n  - 不自动从命名约定推导 feature 并提示\n\n## 关键场景\n- GIVEN propose --parent-feature feature-rddf, WHEN 创建 change, THEN iteration.json 该 change 的 parent_feature 字段 = \"feature-rddf\"\n- GIVEN parent_feature 已设置, WHEN 运行 feature summary, THEN 该 change 显示在对应 feature 组下 (非 __ungrouped__)\n- GIVEN 第一个 change 使用 parent_feature=\"new-feat\", WHEN 第二个 change 也使用 parent_feature=\"new-feat\", THEN 两个 change 自动归入同一组\n\n## 技术约束\n- MUST 拒绝 parent_feature=__ungrouped__ (保留字)\n- MUST 不校验 parent_feature 是否已存在 (前向声明)\n- MUST 显式 parent_feature 优先于 feature- 命名约定 (derive_feature_name 既有优先级)\n- SHOULD 保持向后兼容 (不传 --parent-feature 时行为不变)\n\n## 验收标准\n- --parent-feature <name> 参数可用\n- iteration.json change 条目含 parent_feature 字段\n- feature summary 显示正确的 feature 分组\n- parent_feature=__ungrouped__ 被拒绝\n- 4 个 unit test + 2 个 integration test\n- 所有现有测试通过",
    "effort": "半天"
  },
  {
    "name": "add-propose-content-review",
    "priority": "P1",
    "source": "Oracle 架构分析 2026-07-21 — Proposal 内容审查机制",
    "status": "已完成",
    "phase": "v2.1",
    "category": "quality",
    "description": "## 架构依据\n- Oracle 审查结论: Proposal 需要内容审查 (主观判断)，但不应强行自动化\n- ADR-0015 决策 1 拒绝 Tribunal 做 plan critique — 内容审查同样不应引入多 agent 交叉验证\n- 推荐: 单次 Oracle 调用做 4 项内容审查 (scope 清晰度、ADR 引用相关性、验收标准可测性、范围边界合理性)\n- proposal-suggestions.md 的 5 段式 description 结构适合被审查\n- 与 ADR-0007 gate 哲学一致: warning 级 + 可跳过 (SKIP_CONTENT_REVIEW=yes)\n\n## 范围\n- **In Scope**:\n  - 新建 propose_content_review.py: 单 Oracle 调用 + 结构化输出 + 写 .rddf/state/propose-review.json\n  - Oracle 检查 4 项: scope 清晰度 / ADR 引用相关性 / 验收标准可测性 / 范围边界合理性\n  - propose.md Phase 4 末尾可选调用 (SKIP_CONTENT_REVIEW=yes 跳过)\n  - 输出 warning 级不阻断流程\n  - 对应 unit test\n- **Out Scope**:\n  - 不引入 Tribunal (ADR-0015 约束)\n  - 不做批准/拒绝/打回 (human-in-loop 节点留待后续 ADR)\n  - 不做 plan 阶段内容审查 (仅 proposal 阶段)\n\n## 关键场景\n- GIVEN propose 创建完 change, WHEN SKIP_CONTENT_REVIEW != yes, THEN Oracle 检查 4 项并输出结果到终端 + .rddf/state/propose-review.json\n- GIVEN Oracle 发现 scope 不清晰, WHEN 输出 warning, THEN 不阻断流程 (用户自行决定是否修改)\n- GIVEN SKIP_CONTENT_REVIEW=yes, WHEN propose 完成, THEN 跳过 content review\n\n## 技术约束\n- MUST 使用单次 Oracle 调用 (非 Tribunal)\n- MUST 输出 warning 级不阻断\n- MUST NOT 引入新的 event type (写到 propose-review.json 足矣)\n- SHOULD Oracle prompt 包含 proposal 的 5 段 description 全文\n\n## 验收标准\n- propose_content_review.py 含 4 项检查 + Oracle prompt\n- SKIP_CONTENT_REVIEW=yes 跳过内容审查\n- 输出写入 .rddf/state/propose-review.json\n- 所有现有测试通过",
    "effort": "半天"
  },
  {
    "name": "archive-iteration-sync",
    "priority": "P0",
    "source": "Session 复盘 2026-07-21",
    "status": "已完成",
    "phase": "v2.1",
    "category": "planning",
    "description": "## 架构依据\n- 复盘发现：archive.sh 归档流程完成后，iteration.json 中 5/8 个 change 缺少 `archived_at` 时间戳，feature_view.archived_count 与实际值差 5\n- 根因：skeleton→archive 快速路径跳过了 iteration 同步步骤\n\n## 范围\n- **In Scope**:\n  - archive.sh::archive_change() 末尾强制调用 `iteration.mark_archived(name)` 写入 archived_at 时间戳\n  - feature_view 的 archived_count 从 iteration 动态计算，不依赖缓存字段\n  - 3 个回归测试：正常归档、重复归档幂等、archive 失败不写入\n- **Out Scope**:\n  - 不修改 guide-ship 的轻量模式归档逻辑（仅 worktree 模式）\n\n## 验收标准\n- archive 后迭代 iteration.json，archived_at 存在且 archived_count 正确\n- 3 个 bats 回归测试通过",
    "effort": "0.5-1天"
  },
  {
    "name": "guide-cross-validate",
    "priority": "P1",
    "source": "Session 复盘 2026-07-21",
    "status": "已完成",
    "phase": "v2.1",
    "category": "planning",
    "description": "## 架构依据\n- 复盘发现：`./rddf guide` 推荐 guide-ship 处理 add-rddf-cli-v1，但它已在 3 天前归档\n- 根因：guide 推荐器只读 plan-handoff.committed_changes，未交叉验证 openspec/changes/archive/ 目录\n\n## 范围\n- **In Scope**:\n  - guide.md 推荐逻辑增加交叉验证步骤：对比 committed_changes 与 archive 目录\n  - 自动跳过已归档的 change，不将其纳入 active_changes 计数\n  - 2 个 bats 测试：有 stale handoff 时的推荐、handoff + archive 交叉验证\n- **Out Scope**:\n  - 不修改 plan-handoff 文件本身（那是 guide-plan plan-done 的职责）\n\n## 验收标准\n- `./rddf guide` 不推荐已归档的 change\n- 2 个 bats 测试通过",
    "effort": "0.5-1天"
  },
  {
    "name": "agent-completion-contract",
    "priority": "P1",
    "source": "Session 复盘 2026-07-21",
    "status": "已完成",
    "phase": "v2.1",
    "category": "planning",
    "description": "## 架构依据\n- 复盘发现：8 个 deep agent 中仅 3 个完成了完整的自清理（archive 目录 + iteration sync + worktree/branch 删除）\n- 5/8 个 agent 需要手动介入清理残留 worktree 或归档目录\n\n## 范围\n- **In Scope**:\n  - 在 guide-ship 的 Agent 任务 prompt 模板中增加明确的完成契约清单（3 项强制验收点）\n  - 新增 `verify-agent-completion.sh` — orchestrator 在每个 agent 完成后运行，检查 archive 目录存在、iteration.json 已 sync、worktree 已删\n  - 失败时输出警告并尝试自动修复（force-remove worktree、补写 iteration 条目）\n  - 2 个 bats 测试：三契约全部通过、一项失败时的修复行为\n- **Out Scope**:\n  - 不修改 agent 框架本身（prompt 模板变更即可）\n\n## 验收标准\n- prompt 模板包含 3 项完成契约\n- verify 脚本能检测并修复缺失的清理步骤\n- 2 个 bats 测试通过",
    "effort": "0.5-1天"
  },
  {
    "name": "task-parallel-throttle",
    "priority": "P1",
    "source": "Session 复盘 2026-07-21",
    "status": "已完成",
    "phase": "v2.1",
    "category": "planning",
    "description": "## 架构依据\n- 复盘发现：8 个 deep agent 同时发起导致 volcengine-plan 限流 + kimi-code 配额耗尽，6/8 个 agent 需要 2-3 次重试才能完成\n- 总延迟从线性变为超线性（约 20 分钟 vs 预期 10 分钟）\n\n## 范围\n- **In Scope**:\n  - ./rddf ship --parallel 命令增加 `--max-concurrent=<N>` 参数，默认值 3\n  - 超过限制的 agent 排队等待而非立即发起\n  - 排队逻辑用 bash 实现：wait -n + 自旋检查\n  - 1 个 bats 测试：验证并发数不超过限制\n- **Out Scope**:\n  - 不修改 task() 函数本身（平台层）\n\n## 验收标准\n- 3 agent 并发时不超 3 个同时发起\n- 1 个 bats 测试通过",
    "effort": "0.5-1天"
  },
  {
    "name": "skill-name-auto-resolve",
    "priority": "P2",
    "source": "Session 复盘 2026-07-21",
    "status": "已完成",
    "phase": "v2.1",
    "category": "planning",
    "description": "## 架构依据\n- 复盘发现：第一轮 8 个 task() 全部因 `load_skills=[\"rdd-workflow/writing-plans\"]` 失败\n- 根因：skill 名缺少 `rdd-workflow/skills/` 前缀，无自动补全机制\n\n## 范围\n- **In Scope**:\n  - 在 task() 调用前增加 skill 名校验步骤：从 available list 中搜索匹配\n  - 短名匹配逻辑：`rdd-workflow/writing-plans` → 自动补全为 `rdd-workflow/skills/rdd-workflow/writing-plans`\n  - 歧义时报错（多个匹配），无匹配时提示候选项\n  - 1 个 bats 测试：短名 → 全名映射、歧义场景、无匹配场景\n- **Out Scope**:\n  - 不修改 task() 平台实现（适配层）\n\n## 验收标准\n- `resolve-skill-name rdd-workflow/writing-plans` 输出全名\n- 1 个 bats 测试通过",
    "effort": "0.5-1天"
  },
  {
    "name": "archive-update-proposal-status",
    "priority": "P1",
    "source": "Session 复盘 2026-07-21",
    "status": "已完成",
    "phase": "v2.1",
    "category": "planning",
    "description": "## 架构依据\n- 复盘发现：8 个 P0 全部归档后，proposal-suggestions.md 中仍标记为 \"skeleton\"，未更新为 \"已完成\"\n- 根因：archive 流程缺少 proposal-suggestions.md 状态同步钩子\n\n## 范围\n- **In Scope**:\n  - archive.sh::archive_change() 成功后自动调用 update_proposal_status(name, \"已完成\")\n  - 函数实现：读取 proposal-suggestions.md JSON → 匹配 name → 更新 status → 写回\n  - 3 个 bats 测试：正常更新、条目不存在时跳过、写入失败容错\n- **Out Scope**:\n  - 不修改 proposal-suggestions.md 格式\n\n## 验收标准\n- archive 后 proposal-suggestions.md 中对应条目 status 变为 \"已完成\"\n- 3 个 bats 测试通过",
    "effort": "0.5-1天"
  },
  {
    "name": "preship-dirty-check",
    "priority": "P2",
    "source": "Session 复盘 2026-07-21",
    "status": "已完成",
    "phase": "v2.1",
    "category": "planning",
    "description": "## 架构依据\n- 复盘发现：主仓库有预存脏文件（dashboard/__init__.py, renderer.py）未提交，导致 guide-plan-noninteractive 的 git merge 失败\n- 根因：archive 流程未检查主仓库 working tree 清洁度\n\n## 范围\n- **In Scope**:\n  - guide-ship Phase 3 (archive) 前增加 `check_main_repo_clean()` 检查\n  - 如果有脏文件且不涉及当前 change → 警告 + 建议 stash/commit\n  - 如果有脏文件且涉及当前 change → 阻止归档，要求先 commit\n  - 1 个 bats 测试：脏文件检测\n- **Out Scope**:\n  - 不自动 stash（避免意外数据丢失）\n\n## 验收标准\n- 有脏文件时归档被阻止并给出建议\n- 1 个 bats 测试通过",
    "effort": "0.5-1天"
  },
  {
    "name": "rddf-sessions-gc",
    "priority": "P2",
    "source": "Session 复盘 2026-07-21",
    "status": "已完成",
    "phase": "v2.1",
    "category": "planning",
    "description": "## 架构依据\n- 复盘发现：sessions.json 中有 1 个 owner=\"current\"（字面字符串）的废弃 session，且本次 8-P0 全流程从未被记录\n- 根因：session 创建时 owner_opencode_session_id 使用了占位符 \"current\" 而非真实 session ID，且无 GC 机制\n\n## 范围\n- **In Scope**:\n  - `./rddf sessions gc` 子命令：扫描并清理 owner 为字面字符串 \"current\"、状态 abandoned/orphaned 超 7 天的 session\n  - `./rddf sessions gc --dry-run` 预览模式\n  - 修复 session 创建逻辑：确保 owner 获取真实 session ID（从环境变量 OPENAICODE_SESSION 或 guidgen 生成）\n  - 2 个 bats 测试：GC 清理废弃 session、dry-run 不实际删除\n- **Out Scope**:\n  - 不修改 session 数据模型\n\n## 验收标准\n- `./rddf sessions gc --dry-run` 能找到 \"current\" owner 的废弃 session\n- `./rddf sessions gc` 清理后 sessions.json 干净\n- 2 个 bats 测试通过",
    "effort": "0.5-1天"
  }
]
