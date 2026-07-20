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
  }
]
