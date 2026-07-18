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
  }
]
