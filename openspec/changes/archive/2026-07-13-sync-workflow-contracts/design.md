---
SCOPE: shared
STATUS: PROPOSED
---

## Context

spec-workflow 是元仓(meta-repo),承载 OpenSpec 工作流的 skill 集合 + Loop 引擎 + 测试基础设施。它的 7 个 "surface" 各自演进但本应保持一致:

| Surface | 角色 | 真值来源 |
|--------|------|---------|
| `skills/*.md` (13 个) | 工作流指令 + 状态机实现 | **生产事实真相**(运行时行为) |
| `skills/_lib/*.py` (37 个) | Python 工具(state/iteration/deps/gate) | 生产事实真相 |
| `openspec/specs/*/spec.md` (25 个) | 已采纳契约 | 引用生产,不是反向引用 |
| `docs/adr/ADR-*.md` (21 个) | 架构决策 | 锁定 spec 应当对齐的目标 |
| `USAGE.md` | 用户视角完整指南 | 应镜像 skill 状态机 |
| `AGENTS.md` | contributor 第一入口 | 应镜像磁盘真相 |
| `INSTALL.md` | 安装入口 | 应镜像 package.json |
| `README.md` | 项目门面 | 应镜像磁盘真相 |
| `package.json::skills[]` | npm manifest 分发元数据 | 列出"对外承诺"的 skill 集 |

最近一次 USAGE.md 大改后审计发现 7 类漂移(proposal §Why),所有漂移都是 **surface 与 surface 之间不一致**,不是 skill 内部 bug。本 change 的设计目标是在**不引入新运行时行为**的前提下,把这些 surface 锁在一起。

## Goals / Non-Goals

**Goals:**

- 以**生产 skill 代码**为权威真值,把 USAGE / AGENTS / INSTALL / README / package.json / ADR 索引 / openspec specs 对齐到它
- 在 `openspec/specs/general/spec.md::Requirement general-docs-match-code` 与 `openspec/specs/doc-truth-sync/spec.md` 用 MODIFIED Requirements 把目标字段更新到 v2.0.1
- 引入 3 个 anti-drift 测试(2 bats + 1 pytest),持续锁住以下契约:
  - 跨 doc 一致性(skill 数 / ADR 数 / phase 数 / state-file 路径)
  - ADR 索引完备性(`docs/adr/README.md` 引用的 ADR 全部真实存在)
  - spec 自洽(spec 之间不引用 v1.x 已删除的 skill / phase)
- CI 失败时给出 actionable 错误信息(指向哪个 doc 哪个字段漂移)

**Non-Goals:**

- 不实现新运行时 workflow 行为
- 不修改任何 `skills/*.md` 的 prose(只允许 INSTALL.md 的 description 改)
- 不修改 `skills/_lib/*.py`(零生产代码变更)
- 不修改 `openspec/` 之外的 spec 文件
- 不修改 `.github/workflows/test.yml`(新测试由现有 bats + pytest 步骤自动覆盖)
- 不处理 ADR-0013 dup 重编号(留给未来 `init-deep` 决策)
- 不修 v1.x archived change 的任何 doc(范围限定 v2.0+)

## Decisions

### Decision 1: 真值分层 — 谁是 ground truth

为了避免"鸡生蛋"循环,本 change 明确 4 层真值优先级:

| 层 | 角色 | 例子 |
|----|------|------|
| **L1 (最高)** | 运行时 skill 代码 | `skills/guide-ship.md` phase 编号、`skills/_lib/iteration.py` 状态机字段 |
| **L2** | 磁盘文件系统 | `ls skills/*.md` 的实际计数、`docs/adr/*.md` 的实际列表 |
| **L3** | 用户/分发契约 | `package.json::skills[]`、`openspec/specs/*/spec.md` |
| **L4 (最低)** | narrative 文档 | `USAGE.md`、`AGENTS.md`、`INSTALL.md`、`README.md` |

**对账方向**:L4 → L3 → L2 → L1。L1 永远不动;L2 由 `ls` / `git ls-files` 验证;L3 由 L2 验证;L4 由 L3 验证。

**Rationale**: skill 代码是运行时真值,改它就是改行为;L4 narrative docs 总是滞后于代码,这正常。问题在于 narrative 之间互相矛盾,所以需要 L3 specs 来锁定叙事应当遵循的字段。

### Decision 2: anti-drift test 走 error 级,不只 warning

`skills/_lib/gate.py` 的 `Check` API 已有 error/warning 分级。本 change 引入的 3 个测试**默认 error**(CI 红),不设 warning 级。

**Rationale**:

- 漂移是 silent rot — warning 容易"先放着",然后永远不修
- 3 个测试都是毫秒级(`grep` / `ls` / `python -c`),不会拖累 CI
- 阻断 archive 比阻断 commit 更合理:本 change 不影响 commit 路径(commit 时还没跑 contract test),只在 PR / CI 阶段 fail-fast
- 真实修复路径:CI fail → 看错误信息 → 编辑对应 doc → 重跑 → pass

### Decision 3: `package.json::skills[]` 走 A(发布全部 13 个 skill)

决策矩阵(见 proposal §What Changes):

| 选项 | 含义 | 副作用 |
|------|------|--------|
| **A: 现在补 `feature` + `rddf-session`** | 用户 `npm install spec-workflow` 立即看到 13 个 skill;`INSTALL.md` description 同步改为 13 个(无 src-only delta) | API surface 扩张;若后续要改这两个 skill 的接口,影响 npm 用户 |
| B: 保留 src-only + 加注释 | `package.json` 标 11 个,在文件加 `_comment` 字段声明 src-only | 用户从 npm 安装看到的 11 个 skill 列表与 AGENTS.md / USAGE.md 显式标注的"13 vs 11"差异一致 |

**选 A** 的理由:

- `feature` 与 `rddf-session` 均为 v1.0,`rddf-session` 已有 ADR-0017(已采纳),API 已经稳定
- `install.sh` 与 `INSTALL.md` **已经**通过 `cp -f skills/*.md` 把全部 13 个 .md 文件分发给目标项目,所以 `package.json::skills[]` 的 11 vs 13 差异是**虚假的**"src-only"标签——文件其实已经分发
- `_lib/*.py` 分发漏洞已由 `fix-install-lib-distribution` change(commit `171f565`)解决,从此 `feature`/`rddf-session` 的运行时依赖(rddf_session.py / iteration.py / deps_output.py)能跟随 npm 包一起到达目标项目,不再有"承诺但跑不起来"的风险
- 显式把 13 个 skill 都进 `package.json::skills[]`,消除 5 处文档(skills 表 / AGENTS.md / INSTALL.md description / general spec / doc-truth-sync spec)与 npm 元数据之间的 11/13 叙事漂移

> 注:本 change 的任务设计曾同时保留 A 与 B 两条路径(Task 2.2 / Task 2.3),目的是给 PR review 留选择空间。本设计文档采纳 A 后,Task 2.3(B 路径)被合并/废弃,tasks.md 与 `.rddf/plans/sync-workflow-contracts.md` 同步收口。

### Decision 4: ADR-0013 dup 走 C(README 显式 flag,不重编号)

`docs/adr/` 当前有两个 `ADR-0013-*.md`:`extract-scan-state` 与 `incremental-skeleton-planning`。三个选项:

- **A: 重编号**其中一个 — 破坏 git 历史,需要改 ADR 交叉引用
- **B: 合并内容到单文件** — 模糊了两个独立决策
- **C: 在 `docs/adr/README.md` 顶部加 ⚠️ 警告 + 后续决策任务** — 保持现状,把决策推迟

**选 C** 的理由:

- 重编号风险高(本 change 是 contract-only,不该碰 git 历史的语义)
- 合并会丢失两个 ADR 的独立 context
- flag 是诚实做法,后续 `init-deep` 决策可重排

### Decision 5: state-file 路径按生产事实收敛,不强制全员点号前缀

`USAGE.md` 已升级,但 `general/spec.md` 还引用 undotted 路径。本 change 把 general spec 全部更新为点号前缀,且加入两个新文件:

- `.rddf/state/.arch-handoff.json`(ADR-0016 写入,已有)
- `.rddf/state/.plan-handoff.json`(已有)
- `.rddf/state/deps-analysis.json`(v2.0.1 结构化 JSON,生产实现为无点文件)
- `.rddf/state/.deps-candidates.json`(已有)
- `.rddf/state/.deps-output.md`(兼容旧路径,新路径也保留)
- `.rddf/state/sessions.json`(ADR-0017,已有)
- `.rddf/state/iteration.json`(v2.0.1,已有)
- `.rddf/state/index.md`(已有)
- `.rddf/state/roadmap-state.json` 与 `.rddf/state/.roadmap-state.json` 当前在生产 skill 文档中并存,本 change 只要求显式标注 canonical/legacy 决策,不做实际 rename

**Rationale**: state 文件路径必须以生产代码为准,不能由叙述文档反向发明路径。当前明确事实是 `.arch-handoff.json` / `.plan-handoff.json` / `.deps-candidates.json` / `.deps-output.md` 为点文件,`deps-analysis.json` / `iteration.json` / `sessions.json` / `index.md` 为无点文件;`roadmap-state.json` 存在点/无点混用,本 change 应通过文档和测试暴露并要求维护者选择 canonical path,而不是静默改名。

### Decision 6: anti-drift test 用稳定锚点,不用脆弱的 grep

3 个测试的设计原则:

- **bat `test_doc_contracts.bats`** 用 `grep -E` + 锚定行号,例如 `assert_file_contains "USAGE.md" "Phase 1.5"`(行号不再硬编码,只断言"该字符串在文件中存在")
- **bat `test_adr_index.bats`** 用 `find docs/adr -name 'ADR-*.md' | sort` 列出真实文件,然后 `grep -F` 验证 README 表格中每个 ADR 编号都对应一个真实文件
- **python `test_doc_contracts.py`** 用 `pathlib` + `re`,直接读 spec.md 与 doc 文件,断言 5 个 surface 的关键字段一致

**Rationale**:脆弱 grep 是 anti-drift test 自己可能漂移的根源;稳定锚点确保测试只反映"契约是否一致",不被 doc 重排误伤。

## Alternatives Considered

### Alt 1: 把文档生成脚本化(`scripts/generate_docs.py`)

从 skill 代码 + package.json 自动生成 USAGE / AGENTS / README 的部分段落。

**Rejected**:

- 元仓已经有 skills 37 个 .py + 13 个 .md,生成器本身需要 reflect 这些,反而引入新漂移面
- narrative docs 需要人写(教学性、phase 解释、设计意图),机器生成会失去这段价值
- 维护生成器的成本 > 它防住的漂移
- v2.0 的核心价值是"易读 + 易理解",文档生成器会向"易维护但难读"漂移

### Alt 2: 把 anti-drift test 推到 openspec CLI 上游

类似 `add-spec-validation-gates` 的方案:把 validators 推到 `@fission-ai/openspec` 包。

**Rejected**:

- 与 `add-spec-validation-gates` 同样依赖外部 release cycle(它已在 proposal 里 reject 过类似方案)
- openspec CLI 是 generic spec-driven dev 工具,spec-workflow 自己的 contract 同步不该外溢
- 复用 `skills/_lib/gate.py` 已有 error/warning 分级足够

### Alt 3: 不修 general spec,只修 USAGE / AGENTS

把 spec 视为"已归档 contract",不再 update。

**Rejected**:

- general spec 已经是 `MODIFIED Requirements` 的合理目标(见 `add-spec-validation-gates` precedent)
- 漂移的根因之一就是 spec 与 narrative 各自独立演进;只修 narrative 不修 spec 等于治标
- 未来 contributor 看 spec 仍会拿到过时字段,继续踩坑

### Alt 4: 把 anti-drift test 做成 pre-commit hook

让 commit 时就 fail,不让 CI 才 fail。

**Rejected**:

- 元仓已有 `guide-plan` 的 `plan-done gate`,commit 时验证已经分散在多处;再加 pre-commit 是叠加复杂度
- CI fail 已经足够 fast feedback(<10s)
- pre-commit hook 依赖用户本地环境(很多人不装 pre-commit framework),反而漏检

## Risks / Trade-offs

| # | Risk | Mitigation |
|---|------|------------|
| 1 | 改 USAGE.md phase 表破坏既有读者心智模型 | 顶部加 changelog note "v2.0.2 (sync-workflow-contracts): phase count 由 5+1 升级到 7 编号子阶段" |
| 2 | ADR-0013 dup flag 长期悬挂 | 在 tasks.md 加显式 follow-up 任务 |
| 3 | doc contract test 误报(grep 匹配到注释或示例) | 测试用行首匹配 + 显式 ignore 注释行(如 `<!-- drift-ignore -->`) |
| 4 | CI 时间增加 | 3 个测试都是 grep/ls,实测 <2s |
| 5 | 改 `general/spec.md` 触发 `add-spec-validation-gates` 的 `validate_delta_targets.py` 误报 | 该 validator 检查 MODIFIED/RENAMED target 存在性,本 change 的 MODIFIED target 是 `general` spec 自己,确实存在,不会误报 |
| 6 | 改 `package.json` 改变分发契约 | 选 B(加注释),向后兼容;若选 A 需同步改 INSTALL.md description 与 USAGE.md skill 表 |
| 7 | README.md 目录树可能漏列某些 skill | 用 `ls skills/*.md` 自动生成目录树段落(在 INSTALL skill description 里已用 python 解析 package.json 的同款做法) |

## Verification

```bash
# 1. YAML 解析
python3 -c "import yaml; yaml.safe_load(open('openspec/changes/sync-workflow-contracts/.openspec.yaml'))"
echo "exit=$?"

# 2. openspec 验证
cd /workspace/project/spec-workflow
openspec validate sync-workflow-contracts

# 3. 列出创建的文件
ls -la openspec/changes/sync-workflow-contracts/
ls -la openspec/changes/sync-workflow-contracts/specs/

# 4. (实施阶段) 跑新增 anti-drift 测试
bats tests/integration/test_doc_contracts.bats
bats tests/integration/test_adr_index.bats
pytest tests/unit/test_doc_contracts.py -v

# 5. (实施阶段) 全套回归
pytest tests/unit/ -q --tb=short
bats tests/smoke.bats
```

## Open Questions

- **Q**: `package.json` 决策是否升级为 A?
  **A**: 当前推荐 B。tasks.md 留 decision task,可由 maintainer 在 PR review 时切换。
- **Q**: ADR-0013 dup 是否在 archive 前必处理?
  **A**: 不必。flag 后等 `init-deep` 决策。
- **Q**: anti-drift test 是否需要 nightly 跑(更长历史)?
  **A**: 不必。PR-time fail 就够了;nightly 反而引入误报噪声。
- **Q**: 是否同时更新 `docs/v2-adr-summary.md`(若存在)?
  **A**: 不在本 change scope;若该文件存在且过期,在 tasks.md 加 follow-up link。