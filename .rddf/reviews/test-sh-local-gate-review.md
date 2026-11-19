# 本地门镜像 CI（"中"路线）—— 审稿记录

- **主题**：让 `./test.sh` 成为「本地门」：镜像 CI 的静态门（ruff / mypy strict / doctor structural），
  并把 lint 口径从「工具版本的默认规则集」拿回到配置里。
- **审查**：`metis`（差距分析，1 轮）→ `oracle`（会怎么坏，1 轮）。结论 **APPROVE**（带先决修正）。
- **实施**：rdd-quick（mode b）。改动 10 个文件，产品代码只碰 `skills/_lib/iteration/__init__.py`（1 处 import 移位）。
- **已用轮次**：metis 1 轮 / oracle 1 轮（未触发复审预算）。

## 1. 决策与意图（可判定）

**问题**：master 的 CI **一直是红的**（最近 5 次 push 全 failure），而本地 `./test.sh` 全绿。
根因两层：
(a) **工具版本漂移** —— `requirements.txt` 写 `ruff>=0.1`（无上限）⇒ CI 每次装到最新 ruff（0.17.5），
    其默认规则集比 2024 年宽（多了 I/S/UP）⇒ `ruff check skills/_lib/` 报 36 个 error。
    `pyproject.toml` 的注释一直写着本仓的**意图**是「E+F 的窄集」，但配置里没有 `select` ⇒
    **意图被工具版本悄悄改写**。
(b) **本地门没镜像 CI** —— CI 有 13 个 step，本地只镜像了「断言质量门 + 测试隔离门」两道。

**范围边界**：不扩大 CI 的 lint 覆盖范围（`ruff check skills/_lib/` 仍只查 shim 层；
`mypy --strict skills/_lib/core/` 仍只查 0-def shim ⇒ 这道门目前近乎空转，覆盖漏洞另案）；
不改 doctor 的 26 个 category 注册表；不改回归门（bats）的任何语义。

**交付**：
1. lint 口径显式化（`pyproject.toml` 的 `select`）+ 版本钉死（`requirements.txt`，ruff 与 mypy 一起钉）
   ⇒ 门的语义不再随工具版本漂移。
2. `test.sh` 新增 `--gates` 模式（只跑 4 道门）+ `--quick` 加 ruff + `--full` 跑全 4 道。
3. doctor 新增 `--gate structural` / `--gate advisory`（清单下沉到 `doctor_main.py`），
   CI workflow 与本地门调**同一条命令** ⇒ 清单只有一份。
4. 防漂移测试 `tests/unit/test_ci_local_mirror.py`（三层：命令镜像 / 覆盖台账 / 反向）。
5. 口径说明同步三处：`test.sh` 头注释、`print_help`、`AGENTS.md`。

## 2. metis 的 14 条建议 —— 逐条应答

| # | 建议 | 处置 |
|---|---|---|
| 1 | 「本地门」没定义；doctor 的判定无法用一条命令表达 | **采纳**：doctor 侧实现 `--gate`（rc>=2 聚合，与 CI 现行语义逐字一致），清单下沉 ⇒ 命令与判定同源 |
| 2 | 「命令与 CI 逐字一致」对 doctor 不可实现（第三份清单） | **采纳**：`--gate structural`（CI yml 与 test.sh 都调它） |
| 3 | preflight 查 PATH 上的 `ruff` 还是 `python3 -m ruff` | **采纳**：一律 `python3 -m ruff` / `python3 -m mypy`（绑定到跑 pytest 的同一解释器，免疫 PATH 影子）；CI yml 也改成 `python3 -m`（字面同口） |
| 4 | 「钉版本」写在哪、约束谁 | **采纳**：写在 `requirements.txt`（CI 与本地都装它）；`test.sh` 从**同一份** requirements.txt 读出钉版做版本比对 |
| 5 | 「钉死不掩埋」还是「钉死即掩埋」 | **部分采纳**：口径用 `select` 显式化（= 意图写回配置，不是变严）；被推迟的 34+3 个发现**不靠沉默处理**，落 `.rddf/improvements/fix-lint-deferred-findings.md`（机读债务位）。未采纳 metis 建议的「先修 34 个」——理由见 §4 决策说明 |
| 6 | 「本地门」缺可执行定义（防 help 文本腐烂） | **采纳**：`NOT_MIRRORED` 常量 + `tests/unit/test_ci_local_mirror.py` 三层契约 |
| 7 | `--quick` 只加 ruff；mypy/doctor 放 `--full` 与 `--gates` | **采纳**（与 oracle 一致）：mypy 冷缓存 8-15s 且只覆盖 0-def shim；doctor 的 findings 依赖本地工作状态 |
| 8 | 逃生阀必须走 `audit_bypass_log`，不能静默 env skip | **采纳**：`SKIP_LOCAL_GATES=1` → `audit_bypass_log "SKIP_LOCAL_GATES" … "local-gates"`；**不复用** `ALLOW_TEST_POLLUTION`（一个门两个旁路 = 混乱源） |
| 9 | `.gitignore` 加 `.mypy_cache/` / `.ruff_cache/`；doctor 显式钉 `RDDF_PROJECT_ROOT` | **采纳**：两项都做了（doctor 用 `env RDDF_PROJECT_ROOT="$(pwd)"`） |
| 10 | 顺手修 `test.sh:133/144` 的 `FAILED=1` | **采纳**：改为 `FAILED=$((FAILED + 1))`（两处） |
| 11 | `--help` 里的「未镜像清单」是散文，会漂移 | **采纳的变体**：散文保留（给人看），**真源**是 `NOT_MIRRORED` 数组 + 契约测试（散文不许单独存在） |
| 12 | 三处文案（test.sh 头注释 / print_help / AGENTS.md）不一致 | **采纳**：三处都同步，耗时改成实测值并标注测量日期 |
| 13 | 先提交 lint 修复、push、观察一次 CI，再决定镜像什么 | **部分采纳**：实施顺序照此（口径钉死在前），但**没有 push 等 CI**（push 需用户确认）⇒ 观察窗口留给用户 |
| 14 | 34 个发现的处置方案要落 `.rddf/improvements/` | **采纳**：`.rddf/improvements/fix-lint-deferred-findings.md`（逐规则处置 + 「不许用 ruff --fix 批量修 shim」的约束 + 验收标准） |

## 3. oracle 的先决修正 —— 逐条应答

| # | 修正 | 处置 |
|---|---|---|
| 1 | `--gate` 的聚合语义（rc>=2 拦、rc=1 放行）与 rc=3 不存在 | **采纳**（实测确认：checker 异常会被 `aggregate_findings` 转成 `file="(checker)"` 的 CRITICAL ⇒ 经 doctor.sh 出站的 rc 只有 {0,1,2}）。**附带修一个现存洞**：原 yml 循环里 doctor 整体崩溃时每个 category rc=1 < 2 ⇒ **门静默判绿**；`--gate` 在进程内跑 ⇒ 崩溃即非零 ⇒ fail-closed（commit message 已注明这是修复不是回归） |
| 2 | 不要复用 `render_quiet`（成功时只打「✅ OK」，看不出跑了哪些类）；`--gate` 要自己的渲染器 | **采纳**：每类一行 `✅/⚠️/❌ <category> (critical=… warning=… info=…)` |
| 3 | `::error title=rdd-doctor::` 注解由 doctor 自己在 `GITHUB_ACTIONS=true` 时输出 | **采纳**：doctor 侧输出 `::error` / `::warning`（本地就是普通文本） |
| 4 | Q1「藏发现」的传播点排序：pyproject 注释 > CI step 名 > commit message | **采纳**：① pyproject 注释点名 I/S/UP 并指向 debt 工件；② CI 的 step 改名带规则集（`Ruff lint check (skills/_lib shims, E4/E7/E9/F)`） |
| 5 | Q3 版本检查：**警告 + 用当前版本跑，绝不硬失败** | **采纳**：不符时每次打印 `pinned: … actual: …` + 安装提示，**不硬失败**（硬失败会把「跑一下门」变成「先升级环境」） |
| 6 | Q4 防漂移测试：step 名是自由文本 ⇒ 改用**命令锚** + PyYAML 三层设计 | **采纳**：`tests/unit/test_ci_local_mirror.py` 用 `yaml.safe_load` 解析；① 9 条命令片段必须同时出现在 test.sh 与 test.yml；② 未被命令覆盖的 CI step 必须进 `NOT_MIRRORED`；③ `NOT_MIRRORED` 每项必须真的存在于 yml |
| 7 | Q5 mypy 别进 `--quick`；「~45s」这个数字现在大概率已经是假的 | **采纳**：`--quick` = 隔离门 + ruff；实测 `--quick` = **105s**、`--full` 见 §5，文案改成实测值 + 测量日期 |

## 4. 实施中偏离建议的地方（及理由）

1. **没有先修那 37 个发现**（metis 建议先修、oracle 建议延后）——**采纳 oracle**：
   口径显式化后它们对门的收益为零；而 34/37 落在 identity-merge shim 上，批量 `ruff --fix`
   会重排 import（`sys.path` / `sys.modules` 必须先于 import 生效）⇒ 纯风险。
   延后的代价用**机读债务工件**兜住（不是沉默）。
2. **没有为 mypy/doctor 的覆盖漏洞扩大 CI 范围** —— 超出「中」路线的范围（会改 CI 的检查面），
   记在 debt 工件的 Out of Scope 里。
3. **CI 的两个 shrink-only step 仍然红**（`KNOWN_UNEVALUATED.txt` / `KNOWN_FAILURES.txt`）：
   它们用 `git show origin/master:… || git show HEAD~1:…` 取基线，而 `actions/checkout@v4`
   默认 `fetch-depth: 1` ⇒ 两个 ref 都不存在 ⇒ 基线为空 ⇒ 当前文件所有行都被判「新增」⇒ exit 1。
   **与本次改动无关**，修它要改 checkout 深度 ⇒ 另案。⇒ commit message 写「让 Ruff step 转绿」，
   不写「让 CI 转绿」。

## 5. 验证（证据）

| 判据 | 结果 |
|---|---|
| lint 口径与工具版本无关 | `ruff 0.15.22` 与 `ruff 0.17.5`（CI 会装的版本）对 `skills/_lib/` **都** `All checks passed!` |
| 本地门四道 | `./test.sh --gates` ⇒ 隔离门 OK(1s) / ruff OK(0s) / mypy OK(2s) / doctor structural OK(1s) ⇒ **ALL PASSED** |
| doctor `--gate` 语义与 CI 原循环一致 | 10 类逐行输出；`arch-audit` 有 5 warning ⇒ ⚠️ 但**不拦**（rc>=2 才拦）⇒ rc=0；advisory 门恒不拦（原 yml 语义） |
| 门能变红（ruff） | 变异：`skills/_lib/tasks_count.py` 加一个未用导入 ⇒ `❌ ruff lint FAILED (exit=1)` ⇒ `FAILURES DETECTED (1 step(s) failed)`；恢复 ⇒ ALL PASSED |
| 门能变红（doctor） | 变异：`.rddf/state/events.jsonl` 追加一行坏 JSON ⇒ `❌ state (critical=2)` ⇒ 门红；恢复 ⇒ ALL PASSED |
| 镜像契约能变红 | 变异：`test.sh` 里把 `ruff check skills/_lib/` 改成别的路径 ⇒ `test_ci_local_mirror.py` 的 `test_mirrored_command_present_in_both_files[ruff check skills/_lib/]` 红；恢复 ⇒ 12 passed |
| 防漂移测试本身 | `tests/unit/test_ci_local_mirror.py` ⇒ 12 passed |
| `--quick` | 105s（隔离门 + ruff + smoke + pytest unit 103s）⇒ ALL PASSED |
| `--full --regression` | 见 §6（追加段） |
| doctor | 0 CRITICAL / 8 WARNING（基线） |
| 隔离门 | `bash tests/scripts/check_test_isolation.sh` ⇒ exit 0 |

## 6. 全量门（本次改动后）

```
./test.sh --full --regression --no-color
  ✅ test isolation gate (anti-pollution) OK (1s)
  ✅ ruff lint (skills/_lib/) OK (0s)
  ✅ mypy strict (skills/_lib/core/) OK (1s)
  ✅ rdd-doctor structural gate (10 categories) OK (2s)
  📊 评估 258/258 个文件 · 未评估 0 · 已知失败 11 · 新增失败 0
  ✅ bats regression (baseline-aware) OK (722s)
  ✅ pytest unit OK (105s)          （3427 passed）
  ✅ pytest integration OK (104s)   （196 passed）
  ✅ ALL PASSED   EXIT=0
```

`--quick` 实测 **105s**（隔离门 1s + ruff 0s + smoke 1s + pytest unit 103s），
`--gates` 实测 **~4s**（4 道门），`--full` 实测 **~15min**（2026-11-19，机器空载）。

## 7. 未镜像的 CI 门（诚实台账）

`test.sh` 的 `NOT_MIRRORED`（由 `tests/unit/test_ci_local_mirror.py` 守住双向一致）：

| CI step | 本地为什么不镜像 |
|---|---|
| Install Python deps / Install bats | 环境准备，不是判定 |
| Assertion quality gate | **已被** `check_test_isolation.sh` 的 check #4 覆盖（同一份 grep） |
| Arch quality gate (strict mode) | 需要 `STRICT_ARCH_GATE=yes` 的 strict 语境，属另一类门 |
| Change alignment gate (strict mode) | 同上 |
| Spec validation gate (baseline + delta targets) | 依赖 CI 里 `openspec/changes/` 的存在与基线文件 |
| rdd-doctor advisory gate | 非阻断的告警门，本地门只镜像阻断型的 structural |
| KNOWN_UNEVALUATED / KNOWN_FAILURES shrink-only | 依赖 CI 的 `origin/master` 基线（浅克隆里取不到 ⇒ 见 §4.3） |
| Regression-gate bypass must not be set in CI | CI 专属断言（本地没有 CI 环境可被污染） |

## 8. 最终结论

**通过。** 交付的 5 项（口径显式化 / 三道镜像 / doctor `--gate` 单源清单 / 防漂移契约 / 三处口径同步）
全部落地并有证据：口径对两个 ruff 版本都绿；门能因 ruff 与 doctor 的真实缺陷变红（变异验证），
镜像契约被破坏时契约测试变红；全量门 ALL PASSED。

**两个「已知红」不在本批范围**（已在 §4 与 commit message 写明，不要被误读成「CI 已全绿」）：
CI 的两个 shrink-only step（浅克隆取不到基线）；lint/type 门的覆盖漏洞
（ruff 只查 shim 层、mypy 只查 0-def shim ⇒ mypy 门近乎空转）。

**下一步建议**（按优先级）：
1. push 后观察一次 CI —— Ruff step 应转绿；shrink-only 两步仍红（预期内）。
2. 决定是否修 shrink-only（给 checkout 加 `fetch-depth: 0`）——这是让 CI **真正**全绿的最后一块。
3. 另案处理 lint 覆盖漏洞与 debt 工件里的 37 个发现。
