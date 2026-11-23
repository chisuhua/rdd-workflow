# `.rddf/` 布局

> **真源 = `_lib/core/rddf_layout.py`；本页为解释。**
> 对外出口有两个，各司其职：
> - **`rddf layout --json`** —— 清单视图（机器可读，给消费方与第三方 CI 读）
> - **`rddf doctor --category layout`** —— 诊断视图（给项目自检，只读不写盘）

本页的表格若与 `_lib/core/rddf_layout.py` 不一致，**以代码为准**（那是声明点）。

## 背景

ADR-0026 定义了 `.rddf/` 的命名约定与两类存储（`runtime-only` / `committed`），但那张表没有机器可执行形态 —— 路径常量散落在各模块，散文只覆盖少数几个目录，doctor 也没有布局类目。`RDFF_LAYOUT` 把 ADR-0026 的决策落成可执行的清单：谁读、谁写、什么时候必须存在、是否入库，全部是**可观测事实**（能指到 `file:line`），不是判断。

## 顶层条目

| 条目 | kind | read_by | write_by | required_when | class |
|---|---|---|---|---|---|
| `.roadmap-migrate-backup-*` | dir | rdd | rdd | never | runtime-only |
| `actions` | dir | rdd | user | never | runtime-only |
| `config` | dir | external-tool | external-tool | never | committed |
| `detectors` | dir | rdd | user | never | runtime-only |
| `improvements` | dir | rdd | rdd, agent | always | committed |
| `issues` | dir | rdd | rdd | never | runtime-only |
| `plans` | dir | rdd | rdd, agent | always | committed |
| `project.yaml` | file | rdd | user | always | committed |
| `reviews` | dir | agent | agent | never | committed |
| `roadmap` | dir | rdd | agent | always | committed |
| `roadmap.md` | file | rdd | agent | always | committed |
| `skill-profiles` | dir | rdd | user | never | committed |
| `state` | dir | rdd | rdd, agent | always | runtime-only |
| `wt` | dir | rdd | git | worktree | runtime-only |

字段含义：

| 字段 | 取值 | 说明 |
|---|---|---|
| `path` | 相对 `.rddf/` 的顶层条目名（允许 glob） | 只扫一层，glob 不跨 `/` |
| `kind` | `dir` \| `file` | 决定 ignore 探测用不用探针路径 |
| `read_by` / `write_by` | `rdd` \| `agent` \| `user` \| `git` \| `external-tool` | 可观测事实，逐条有 `file:line` 依据 |
| `required_when` | `always` \| `worktree` \| `never` | `always` = 启用 rdd 后应当存在；`worktree` = 仅 worktree 模式；`never` = **不要求存在** |
| `transient` | bool | 临时候选项（如迁移 backup），判据②对它放行 |
| `class` | `runtime-only` \| `committed` | 直接取自 ADR-0026；`gitignored` 由它派生 |
| `severity` | `WARNING` \| `INFO` | 该条目「缺失」类判据的定档 |

### 读法上的三个约定

- **`external-tool` 条目**（如 `config/`）rdd **不读、不写、不校验内容**。它是消费方的私有目录，登记它只是为了声明边界：`reviews/` 同理，只由 agent 写，rdd 零引用。
- **`state/` 是混写目录**。目录级条目只能声明「rdd 与 agent 都写」；**哪些文件归谁，见下方文件级的「治理状态（opencode 角色层）」表**。
- **用户自建目录是被允许的**。doctor 对未登记的顶层条目报 **INFO**（不阻断）。第三方项目可以在 `.rddf/` 下放自己的东西 —— 但若希望它被工具识别，就要登记进 `RDFF_LAYOUT`。
- **`wt/` 只在 worktree 模式要求存在**。轻量模式（直接在主仓实施）永不创建它。
- **判据③判定的是 ignore 规则本身，与条目是否存在无关**。若项目的 `.gitignore` 用 `.rddf/*` 这类通配写法，尚未创建的目录也会被判为 class 不符 —— 这是 advisory WARNING，不阻断。

## 新增一个顶层条目的三步

与 [ADR-0026](../adr/ADR-0026-internal-metadata-namespace-convention.md) 的「添加新 metadata 类别」指引一致：

1. **路径**：必须是 `.rddf/<category>/`（dot-prefix 命名约定）。
2. **类型决策**：评估是 `runtime-only`（临时状态、per-machine）还是 `committed`（跨机器共享的元数据）。
3. **gitignore**：`runtime-only` 加进 `.gitignore`；`committed` **不写进** `.gitignore`（靠「不写」实现 tracked）。
4. **登记**：在 `_lib/core/rddf_layout.py` 加一条 `LayoutEntry`，逐字段填 `read_by` / `write_by`（要有 `file:line` 依据）与 `required_when`。

第 4 步不做的话，`rddf doctor --category layout` 会报「未登记」（INFO，不阻断）。

## 文件级

`.rddf/` 顶层之外的**文件**不在清单条目里（清单只管顶层），但同样有明确的读写方。下表**以代码为源**：

**verifier 状态命名空间**（`_lib/verifier/state_paths.py:34-41` 的 `SKILL_OWNS_PATHS`）：

| 文件 | 说明 |
|---|---|
| `.rddf/state/verifier/<name>.json` | 每 change 的 verifier 状态 |
| `.rddf/state/verifier/<name>.audit.jsonl` | 审计日志 |
| `.rddf/state/verifier/.ac-verdict-*.json` | AC 判决缓存（归档门输入） |
| `.rddf/state/verifier/.ac-verification.jsonl` | 验证事件流 |
| `.rddf/state/verifier/.ac-verifier-blocked.jsonl` | 受阻记录流 |
| `.rddf/state/verifier/rdd-verify-context-<name>.json` | 分阶段上下文 |

**跨阶段 handoff**（写在 `.rddf/state/`）：

| 文件 | 写方 | 读方 |
|---|---|---|
| `.arch-handoff.json` | `rdd-arch`（`skills/rdd-arch/scripts/write_arch_handoff.py:194`） | `rdd-planner` / `rdd-builder` |
| `.planner-handoff.json` | `rdd-planner`（`_lib/planner_handoff.py:77`） | `rdd-builder`（`_lib/builder_deps.py:234`） |
| `.planner-feedback.json` | `rdd-builder`（`_lib/builder_feedback_router.py:48`） | `rdd-planner` / `rdd-arch` |

**治理状态（opencode 角色层）** —— 写在 `.rddf/state/` 与 `.rddf/reviews/`，**由消费方（opencode build agent）写，rdd-workflow 不读不写**：

| 文件 | 写方 | 读方 | 说明 |
|---|---|---|---|
| `.rddf/state/role.json` | opencode 角色层 | opencode 角色层 | 治理身份状态（schema `role-v2`，含 `sessions` 分区）。**不是** rdd 的工件。 |
| `.rddf/state/pair.json` | opencode 角色层 | opencode 角色层 | 派发登记（pair-v2）。`required_when=never` —— 未启用派发时不落盘。 |
| `.rddf/reviews/*.md` | opencode 角色层 | opencode 角色层 | 验收报告（verifier 角色）与审稿报告（architect 角色）。**产品落点**。 |

> 为什么单列一栏：`.rddf/state/` 是**目录级**清单条目（清单只管顶层，见 `tests/unit/test_rddf_layout.py`），
> 而 `state/` 目录里同时住着两类文件 —— rdd 写的运行时状态（state vector / event log / handoff /
> verifier 命名空间）与 agent 写的治理状态（上表）。目录级条目只能声明「两者都写」，
> **逐文件归属以本表为准**。

## 边界

- 本清单描述**默认布局**。`RDDF_STATE_DIR` 环境变量重定向状态目录（`_lib/session_stats.py:24`、`_lib/rfc_interview_state.py:17`、`_lib/subagent_strategy.py:104`）**不在契约内** —— 清单描述的是路径约定，不是可重定向的运行时配置。
- 清单与代码里的硬编码路径目前仍是**双写**。两条断言覆盖了 `defaults.DEFAULTS` 的路径类条目与 5 个模块常量（`STATE_VECTOR_PATH` / `EVENT_LOG_PATH` / `MEMORY_PATH` / `DETECTOR_PLUGIN_DIR` / `ACTION_PLUGIN_DIR`），但 `Path(root) / ".rddf" / X` 这类拼接形态**不在断言范围内**。不得声称「全覆盖」。
- `_lib.core.rddf_layout` 的 **import 路径不是稳定 API**。第三方通过 `rddf layout --json` 消费。

## `schema_version` 演进策略

`rddf layout --json` 的 payload 带 `schema_version`（当前 `1`）与 `tool_version`。

| 变更 | 是否升版本 |
|---|---|
| 增字段 | 否 |
| 增 entry | 否 |
| 改 entry 语义（字段含义/取值域变化） | **是** |
| 删 entry | **是** |

消费方约定：**忽略未知字段**，按 `path` 做**集合比较**（不要假设条目数量或顺序稳定 —— 输出按 `path` 排序，但增删 entry 会改变集合）。

输出**不含时间戳字段** ⇒ 同一安装的两次运行字节一致，消费方可直接 diff。
