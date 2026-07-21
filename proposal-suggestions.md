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
    "name": "refresh-input-sources",
    "priority": "P0",
    "source": ".omo/plans/improve-change-quality-index.md — Plan C",
    "status": "skeleton",
    "phase": "v2.1",
    "category": "planning",
    "description": "## 架构依据\n- Plan C: 刷新输入源\n\n## 范围\n- **In Scope**:\n  - 扩展 roadmap.md 完整 v2.1/v3.0 的 change 映射\n  - 运行 gap-analysis 扫描 ADR 差距\n  - 扫描 TODO/FIXME 找出未跟踪问题\n  - 扫描 test 缺口\n- **Out Scope**:\n  - 不创建新 change\n  - 不修改 propose 技能\n\n## 关键场景\n- GIVEN roadmap.md 只有标题，WHEN 刷新完成，THEN 所有 v2.1/v3.0 change 有完整映射\n- GIVEN gap-analysis 运行，WHEN 完成，THEN 发现新 gaps 写入 proposal-suggestions.md\n\n## 技术约束\n- MUST 保持 roadmap.md 向后兼容（旧解析器仍可解析）\n- MUST 使用 propose.md 现有扫描逻辑\n- SHOULD 按 plan-queue-overview 格式组织输出\n\n## 验收标准\n- roadmap.md 含 v2.1 + v3.0 全部 6 个 change 映射\n- proposal-suggestions.md 中新发现的 gap 条目 ≤ 5 个",
    "effort": "1-2h"
  },
  {
    "name": "refine-adr-0015-wiring",
    "priority": "P0",
    "source": ".omo/plans/improve-change-quality-index.md — Plan A",
    "status": "skeleton",
    "phase": "v2.1",
    "category": "quality",
    "description": "## 架构依据\n- ADR-0015: openspec validate 集成为 plan-critic\n- Plan A: 补完 ADR-0015 链路\n\n## 范围\n- **In Scope**:\n  - guide-plan.md Phase 4 插入 PYEOF 块运行 openspec validate 并写入 report\n  - ADR-0015 状态: 待定 → 已采纳（原文 + README + AGENTS.md 同步）\n  - 端到端集成测试\n- **Out Scope**:\n  - 不修改 gate.py（双跑问题短期可接受）\n  - 不修改 validate_report.py（已有 write_report/load_report）\n\n## 技术约束\n- MUST 复用 validate_report.py 的 write_report()\n- MUST 在 guide-plan.md 独立运行 openspec validate（gate.py 不暴露 raw JSON）\n- MUST 同步 ADR-0015 状态三处一致\n\n## 验收标准\n- guide-plan.md Phase 4 运行 openspec validate 并写入 .rddf/state/openspec-validate.json\n- ADR-0015 状态为已采纳\n- 1-2 个集成测试验证",
    "effort": "2-3h"
  },
  {
    "name": "add-propose-output-validation",
    "priority": "P1",
    "source": ".omo/plans/improve-change-quality-index.md — Plan B",
    "status": "skeleton",
    "phase": "v2.1",
    "category": "quality",
    "description": "## 架构依据\n- ADR-0015: openspec validate 集成为 plan-critic\n- Plan B: Propose 输出验证\n\n## 范围\n- **In Scope**:\n  - iteration_schema v3→v4 + 迁移函数\n  - 5 个 check 函数（含 Why-to-roadmap-gap）\n  - STRICT_PROPOSE_GATE strict mode\n  - propose_quality_check.py 模块\n- **Out Scope**:\n  - 不修改 propose.md 主流程\n  - 不引入新外部依赖\n\n## 技术约束\n- MUST 设计阈值统一为 500 字符\n- MUST propose_quality_check.py 放在 skills/propose/scripts/（非 store.py）\n- MUST 有 __main__ 入口 + CLI 调用补全\n\n## 验收标准\n- iteration_schema v4 含 quality_warnings\n- 5 个 check 函数（含 quality_warnings 输出）\n- STRICT_PROPOSE_GATE=yes 升级为 error\n- 单元测试覆盖全部 5 个 check",
    "effort": "6-8h"
  },
  {
    "name": "add-change-quality-guide",
    "priority": "P1",
    "source": ".omo/plans/improve-change-quality-index.md — Plan D",
    "status": "skeleton",
    "phase": "v2.1",
    "category": "docs",
    "description": "## 架构依据\n- Plan D: 质量标准模板\n- ADR-0019: change_arch_alignment 反模式清单\n\n## 范围\n- **In Scope**:\n  - docs/change-quality-guide.md\n  - AGENTS.md 引用\n  - propose.md 引用\n- **Out Scope**:\n  - 不强制执行规则（仅文档）\n  - 不修改 CI\n\n## 技术约束\n- MUST 引用 ADR-0019 反模式清单（单一真相源）\n- MUST 量化阈值与 Plan B 对齐（500 字符、80% ADR）\n- MUST 在 Plan B 之后实施（描述 B 实际行为）\n- SHOULD 维护规则明确（量化阈值变更需同步 Plan B）\n\n## 验收标准\n- change-quality-guide.md 存在且引用 ADR-0019\n- 阈值与 Plan B 一致\n- AGENTS.md 和 propose.md 引用该文档",
    "effort": "2-3h"
  },
  {
    "name": "split-rddf-session-coordinator",
    "priority": "P2",
    "source": "gap-analysis: refresh-input-sources (docs/audit/2026-07-14-debt-fix-compliance.md §5 item 1)",
    "status": "pending",
    "phase": "v2.1",
    "category": "refactor",
    "description": "## 架构依据\n- docs/audit/2026-07-14-debt-fix-compliance.md §5 (Pre-Existing Issues) item 1:\n  \"RddfSessionCoordinator is still 491 lines / 16 methods. Full god-class split deferred to follow-up change.\"\n- 当前实际状态: skills/rddf-session/scripts/rddf_session.py 为 506 行 (经审计后增长 15 行)，含 RddfSessionState + RddfSessionError + SchemaValidationError + ConflictError + RddfSession + RddfSessionCoordinator 6 个类，混合 schema + IO + 协调 + 冲突检测 4 类职责。\n- ADR-0017 (rddf-session) §决策 3: 单文件实现可接受，但应在职责膨胀时拆分。\n\n## 范围\n- **In Scope**:\n  - skills/rddf-session/scripts/rddf_session.py -> rddf-session/scripts/ 子模块拆分\n  - schema.py - RddfSessionState + schema validation\n  - coordinator.py - RddfSessionCoordinator 核心\n  - conflict.py - ConflictError + detect_conflict 逻辑\n  - __init__.py - 兼容 re-export\n  - 迁移现有 test_rddf_session.py 测试\n- **Out Scope**:\n  - 不修改 RddfSessionCoordinator 公有 API\n  - 不修改 sessions.json schema\n  - 不引入新功能\n\n## 关键场景\n- GIVEN rddf_session.py 506 行 6 个类, WHEN 拆分完成, THEN 每个子模块 < 200 行且单一职责\n- GIVEN 现有 import `from skills.rddf-session.scripts.rddf_session import RddfSessionCoordinator`, WHEN 拆分后, THEN 原路径仍可 import (兼容 shim)\n\n## 技术约束\n- MUST 保持 rddf_session.py 作为 re-export shim (类似 loop_engine.py 模式)\n- MUST NOT 改变公有 API 签名\n- SHOULD 参考 iteration.py v2.0.8 拆分模式 (schema/store/render)\n\n## 验收标准\n- rddf_session.py 拆分为 3-4 个子模块 + __init__.py\n- 所有现有 import 正常工作\n- 所有现有测试通过 (test_rddf_session.py 22 个测试 + test_rddf_binding.py)\n- 无功能变化",
    "effort": "1-2d",
    "type": "refactor"
  },
  {
    "name": "split-gate-module",
    "priority": "P2",
    "source": "gap-analysis: refresh-input-sources (skills/_lib/gate.py 460 lines, 17 functions)",
    "status": "pending",
    "phase": "v2.1",
    "category": "refactor",
    "description": "## 架构依据\n- skills/_lib/gate.py 当前 460 行，含 GateResult + GateMechanism 2 个类 + 17 个函数/方法，混合 gate 定义、注册、执行、质量检查 4 类职责。\n- 类比 split-iteration-module (已完成) 的拆分模式：iteration.py 739 行 -> iteration/ 子目录 3 文件 + __init__.py。\n- ADR-0007 (gate-mechanism) §3: gate 机制应支持插件式扩展，单文件阻碍新 gate 添加。\n\n## 范围\n- **In Scope**:\n  - skills/_lib/gate.py -> skills/_lib/gate/ 子目录\n  - gate/result.py - GateResult dataclass\n  - gate/mechanism.py - GateMechanism 核心协调\n  - gate/builtin_checks.py - 内置检查函数 (adr_refs_valid, placeholder_scan 等)\n  - gate/__init__.py - 兼容 re-export\n  - 迁移 test_gate.py 测试 (如有必要)\n- **Out Scope**:\n  - 不修改 GateMechanism 公有 API\n  - 不引入新 gate 类型\n  - 不修改 arch_quality_gate.py (已有独立模块)\n\n## 关键场景\n- GIVEN gate.py 460 行混合 4 类职责, WHEN 拆分完成, THEN 每个子模块 < 200 行\n- GIVEN 现有 `from skills._lib.gate import GateMechanism, GateResult`, WHEN 拆分后, THEN 原路径仍可 import\n\n## 技术约束\n- MUST 保持 skills/_lib/gate.py 或 skills/_lib/gate/__init__.py 作为 re-export 入口\n- MUST NOT 改变公有 API 签名\n- SHOULD 参考 iteration/ 拆分模式 (schema/store/render)\n\n## 验收标准\n- gate.py 拆分为 3 个子模块 + __init__.py\n- 所有现有 import 正常工作\n- 所有现有测试通过 (test_gate.py)\n- 无功能变化",
    "effort": "1-2d",
    "type": "refactor"
  },
  {
    "name": "guide-plan-noninteractive",
    "priority": "P0",
    "source": "复盘改进 #1 — guide-plan 无交互模式",
    "status": "待创建",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- 复盘发现：guide-plan 是人际交互状态机（菜单+read），AI 编排器无法调用。propose_change.py 虽可用但绕过完整流程。\n\n## 范围\n- **In Scope**:\n  - guide-plan.md 入口检测 `--non-interactive` 或 `SKIP_GUIDE_PLAN_MENU=yes` env var\n  - non-interactive 模式跳过菜单，执行默认流程（scan→propose→deps→plan-done）\n  - propose 增加 `--batch-create` 批量从 proposal-suggestions.md 创建 skeleton\n  - 测试覆盖两种模式\n- **Out Scope**:\n  - 不修改人际交互菜单（向后兼容）\n  - 不修改 guide-ship\n\n## 验收标准\n- `SKIP_GUIDE_PLAN_MENU=yes skill_use(\"guide-plan\")` 自动执行完整 plan 流程\n- `skill_use(\"propose\", \"--batch-create\")` 创建所有 pending 建议的 skeleton\n- 不影响现有交互体验",
    "effort": "2-3h"
  },
  {
    "name": "auto-wave-scheduler",
    "priority": "P0",
    "source": "复盘改进 #3 + #4 — 自动 Wave 调度 + iteration 状态自动化",
    "status": "待创建",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- 复盘发现：Wave 切换靠人工判断、iteration.json 状态转换手动操作。manual_deps 已有依赖数据，缺的是自动化消费方。\n\n## 范围\n- **In Scope**:\n  - guide-arch/guide-plan/guide-ship 入口 hook 自动迭代状态转换（planned→proposed→in_worktree→archived）\n  - archived hook 扫描 iteration.json 中 blocker 已解除的 planned change\n  - 输出建议信息“bloker 已解除: change-x, change-y 可以执行”\n  - 不影响现有 hook 行为\n- **Out Scope**:\n  - 不自动调用 guide-ship（仅建议，用户确认）\n  - 不修改 DependencyScheduler（ADR-0010 v2.1 完整版留待后续）\n\n## 验收标准\n- 归档 change-a 后，若 change-b 的 manual_deps=[change-a]，自动打印“建议: change-b blocker 已解除”\n- guide-plan 入口自动设 stage_plan session 状态\n- 测试覆盖 archived→unblocked→suggest 链路",
    "effort": "3-5h"
  },
  {
    "name": "propose-quality-autohook",
    "priority": "P1",
    "source": "复盘改进 #6 — propose_quality_check.py 接入 propose 流程",
    "status": "待创建",
    "phase": "v2.1",
    "category": "quality",
    "description": "## 架构依据\n- 复盘发现：propose_quality_check.py 已存在但未接入 propose 流程，需手动调用。\n\n## 范围\n- **In Scope**:\n  - propose.md Phase 4 写入 artifacts 后自动调用 quality check\n  - 失败为 warning 级别，不阻断 propose 流程\n  - 只在 `STRICT_PROPOSE_GATE=yes` 时升级为 error\n- **Out Scope**:\n  - 不修改 propose_quality_check.py 的检查逻辑\n  - 不修改 iteration_schema\n\n## 验收标准\n- `skill_use(\"propose\")` 创建 change 后自动打印质量检查结果\n- `STRICT_PROPOSE_GATE=yes` 时检查失败退出 1\n- 不影响现有 propose 流程",
    "effort": "1-2h"
  },
  {
    "name": "update-adr-index",
    "priority": "P2",
    "source": "复盘遗留 — ADR 索引表与 README 不同步",
    "status": "待创建",
    "phase": "v2.1",
    "category": "docs",
    "description": "## 架构依据\n- 执行中发现 docs/adr/README.md 索引表只更新到 ADR-0020，但代码库已有 ADR-0021、ADR-0022。\n- test_adr_index.bats 因此一直失败（pre-existing failure #1）。\n\n## 范围\n- **In Scope**:\n  - 更新 docs/adr/README.md 索引表追加 ADR-0021、ADR-0022 行\n  - 保持表格格式一致\n- **Out Scope**:\n  - 不修改 bats 测试（预存在失败会自然解决）\n  - 不修改 ADR 文件本身\n\n## 验收标准\n- README.md 的 ADR 索引表包含 ADR-0021 和 ADR-0022\n- README.md 的进度表（v2.0 ADR 实施状态）包含 ADR-0022\n- test_adr_index.bats 中 ADR 文件检查通过",
    "effort": "15min"
  },
  {
    "name": "add-guide-dashboard",
    "priority": "P0",
    "source": "复盘改进 — guide 技能增强为工作流仪表盘",
    "status": "待创建",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- guide 技能目前是无状态推荐器，只输出一行推荐\n- 用户需要完整的工作流状态概览 + 可交互的下一步选择\n- 与 rddf-session、iteration.json、proposal-suggestions.md 联动\n\n## 范围\n- **In Scope**:\n  - scan-state.sh 增强：额外收集 iteration.json 状态、待创建提案数、session 状态\n  - 新增 render-dashboard.sh：格式化的仪表盘输出（路线图 / changes / session / 下一步）\n  - guide SKILL.md 输出格式从单行推荐改为多区块仪表盘\n  - 仪表盘末尾提供编号操作选项（1-N，含 rddf-session resume）\n- **Out Scope**:\n  - 不修改 guide-arch/guide-plan/guide-ship（仅推荐器层）\n  - 不新增状态文件（只读扩展）\n  - 不修改 scan_session_binding 的 Python 后端\n\n## 关键场景\n- GIVEN 项目有已归档 changes，WHEN 调 guide, THEN 仪表盘显示归档数 + 待创建提案数 + 建议继续 propose\n- GIVEN 存在 orphaned rddf-session，WHEN 调 guide, THEN 仪表盘显示恢复选项\n\n## 验收标准\n- skill_use(\"guide\") 输出至少 4 区块：路线图 / changes / session / 下一步操作\n- 下一步操作至少包含：继续 propose、查看 features、rddf-session 操作\n- 所有现有 tests 通过\n- 不修改任何状态文件（只读）",
    "effort": "3-4h"
  },
  {
    "name": "fix-rddf-schema-validation",
    "priority": "P0",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W0-1",
    "status": "待创建",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- RDDF session schema validation 基础设施从未生效: SCHEMA_PATH 指向不存在的目录，validate=True 从未传参\n\n## 范围\n- **In Scope**:\n  - 修正 SCHEMA_PATH 指向 skills/_lib/schemas/sessions_schema.json\n  - 在 _read_unlocked() 中启用 schema validation\n  - 3 个 schema validation 测试\n- **Out Scope**:\n  - 不修改 session 数据模型\n  - 不修改 sessions_schema.json 内容\n\n## 验收标准\n- SCHEMA_PATH 指向正确路径且 validation 生效\n- 非法 fields 的 sessions.json 被正确拒绝\n- 合法 sessions.json 正常通过",
    "effort": "0.5天"
  },
  {
    "name": "audit-attach-detach-calls",
    "priority": "P0",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W0-2",
    "status": "待创建",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- 不清楚 attach_change/detach_change 是否被 guide 技能实际调用\n\n## 范围\n- **In Scope**:\n  - 查找所有调用 attach_change / detach_change 的位置\n  - 确认 guide-arch/guide-plan/guide-ship 的 hook 调用链\n  - 输出 audit report\n- **Out Scope**:\n  - 不修改代码（仅 audit）\n\n## 验收标准\n- audit report 列出所有调用点 + 缺失的 hook",
    "effort": "0.25天"
  },
  {
    "name": "add-heartbeat-config",
    "priority": "P1",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W1-1",
    "status": "待创建",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 30 * 60 硬编码\n\n## 范围\n- **In Scope**:\n  - RddfSessionCoordinator 构造函数支持 RDDF_HEARTBEAT_TIMEOUT_SECONDS 环境变量\n  - 支持 RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS 环境变量\n  - check_heartbeat_timeouts() 使用实例属性而非模块常量\n- **Out Scope**:\n  - 不修改 sessions_schema.json（运行时配置）\n\n## 验收标准\n- 默认值仍为 30min / 5min\n- 环境变量可覆盖\n- 3 个测试（默认/覆盖/非法值）",
    "effort": "0.5天"
  },
  {
    "name": "add-rddf-concurrency-tests",
    "priority": "P1",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W1-2",
    "status": "待创建",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- _with_file_lock 使用 LOCK_NB（非阻塞 fail-fast），并发调用会失败而非排队\n- 需要测试验证这一真实语义\n\n## 范围\n- **In Scope**:\n  - tests/integration/test_rddf_session_concurrency.py: multiprocessing.Pool 并发 100 次 create_session\n  - tests/integration/test_rddf_session_cross_session_recovery.py: session 超时→orphaned→恢复全链路\n- **Out Scope**:\n  - 不修改 rddf_session.py 逻辑\n\n## 验收标准\n- 并发测试验证 LOCK_NB 行为（非破坏，非无限重试）\n- 跨 session 恢复测试验证 find_next_recommendation + transfer_ownership",
    "effort": "1.5天"
  },
  {
    "name": "fix-attach-detach-symmetry",
    "priority": "P1",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W1-3",
    "status": "待创建",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- attach_change/detach_change 调用点不对称（基于 W0-2 audit）\n\n## 范围\n- **In Scope**:\n  - rddf_session_hooks.sh 新增 rddf_session_hook_attach\n  - guide-plan Phase 2 完成后调用 attach\n  - guide-ship Phase 1 plan 生成后调用 attach\n- **Out Scope**:\n  - 不修改 detach 逻辑（heartbeat hook 不变）\n\n## 验收标准\n- attach/detach 调用对称\n- 4 个测试（attach 正常/idempotent/detach/hook 集成）",
    "effort": "1天"
  },
  {
    "name": "split-rddf-god-class",
    "priority": "P2",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W2-1",
    "status": "待创建",
    "phase": "v2.1",
    "category": "refactor",
    "description": "## 架构依据\n- RddfSessionCoordinator 507 行，自认 god class\n- 拆分方案: facade + _store.py + _commands.py + _binding.py + _types.py\n\n## 范围\n- **In Scope**:\n  - 拆分 RddfSessionCoordinator 为 5 个模块\n  - facade 保留全部公共方法签名不变\n  - 所有现有调用点不受影响\n- **Out Scope**:\n  - 不修改 schema validation（已在 W0-1 修复）\n  - 不修改会话数据模型\n\n## 验收标准\n- 所有现有 24+10 测试通过（回归）\n- lsp_find_references 验证无遗漏调用点",
    "effort": "1.5天"
  },
  {
    "name": "add-workflow-synthesizer",
    "priority": "P0",
    "source": ".omo/plans/rddf-session-improvement-plan.md — W3-1",
    "status": "待创建",
    "phase": "v2.1",
    "category": "core",
    "description": "## 架构依据\n- 核心诉求：guide 运行时知道哪些阶段已完成/待处理，建议 resume 还是 restart\n- 只读模块，不写 sessions.json\n- 与 add-guide-dashboard 互补：synthesizer 提供数据，dashboard 提供展示\n\n## 范围\n- **In Scope**:\n  - skills/_lib/workflow_synthesizer.py：读取 sessions.json + handoff + iteration + git 状态\n  - 结构化推荐：WorkflowRecommendation + PhaseStatus dataclass\n  - 推荐逻辑：resume/restart/start-arch/all-done 决策树\n  - scan-state.sh 集成 synthesizer 输出到 CONTEXT_LINES\n- **Out Scope**:\n  - 不修改 sessions_schema.json（只读）\n  - 不自动执行推荐（仅建议，用户确认）\n\n## 验收标准\n- synthesizer 输出 WorkflowRecommendation with 置信度\n- 10 个测试覆盖每一条推荐路径",
    "effort": "2天"
  }
]
