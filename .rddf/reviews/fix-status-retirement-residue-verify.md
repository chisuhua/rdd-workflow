# 验收报告 — fix-status-retirement-residue

- **change**：`openspec/changes/fix-status-retirement-residue/`
- **验收时间**：2026-11-20
- **实现提交**：`（待提交）`
- **跨仓提交**：`~/.config/opencode` 仓 `c149934`（`fix(rdd-skills): 从 fallback 清单移除已退役的 status`）
- **判据来源**：`openspec/changes/fix-status-retirement-residue/proposal.md` 的 `## Acceptance`（AC-1 ~ AC-14）

## 审查链（实施前）

| 环节 | 结论 | 处置 |
|---|---|---|
| oracle（`审查域: 治理面`，跨仓部分） | **治理面判定: PASS** | 采纳其措辞要求：注释必须点明能力由 `rddf status` CLI 承接，不得照抄 execute 的「无对应 CLI」句式 |
| critic（`review_profile: build, plan`） | **APPROVE_WITH_CONDITIONS**，mergeable: yes，scope_exceeded: true（1 条范围外） | 3 条 SHOULD_FIX 全部并入本 change（SHOULD_FIX #1 `_lib/iteration/` 两处 docstring；#2 tasks 须含守卫红测 + 跨仓人工 verify；#3 `phase2_path_migrator.py` docstring 计数失真） |

**BLOCKER**：无。

## 逐条判定与证据

| AC | 判定 | 证据（命令 → 输出摘要） |
|---|---|---|
| AC-1 工具映射表清空 | **pass** | `python3 tools/phase2_path_migrator.py list-skills` → 改前含 9 个 key（`guide` / `guide-arch` / `guide-plan` / `guide-ship` / `propose` / `feature` / `status` / `deps` / `rddf-session`），改后仅 4 个（`propose` / `feature` / `deps` / `rddf-session`）；`grep -cE '^(guide\|guide-arch\|guide-plan\|guide-ship\|status):'` → 改前 **5** → 改后 **0** |
| AC-2 工具文件零残留 | **pass** | `! grep -q 'status_helpers\|scan-state\|guide-ship' tools/phase2_path_migrator.py` → 通过；`! grep -q '"guide"\|"guide-arch"\|"guide-plan"\|"guide-ship"\|"status"' tools/phase2_path_migrator.py` → 通过；`python3 -m py_compile tools/phase2_path_migrator.py` → OK |
| AC-3 INSTALL.md | **pass** | `! grep -n 'status\.md\|status_helpers' skills/INSTALL.md` → 0 命中 |
| AC-4 测试注释/docstring | **pass** | `! grep -n 'status_helpers\|scan-state\|status\.md\|guide-ship' tests/integration/test_install_lib_distribution.bats tests/integration/test_roadmap_extraction.bats` → 0 命中；`! grep -nE 'skill_use\("status"\|guide-ship\|guide-spec\|execute skill\|status\.md' tests/integration/test_hook_boundary.py` → 0 命中（**判据收窄**：该文件大量用 `status="proposed"` 作测试夹具，宽判据会误报） |
| AC-5 迁移文档 | **pass** | `grep -c 'skills/status/' docs/migration/v3-to-v4.md` → **3**（≥1）；`grep -q 'rm -f ~/.agents/skills/status'` → 通过 |
| AC-6 活代码零引用 | **pass** | `! grep -rnI --exclude-dir=__pycache__ 'skill_use("status"' _lib/ skills/ tests/ tools/` → 0 命中（**必须带 `-I` 与 `--exclude-dir=__pycache__`**：陈旧 `.pyc` 内嵌旧 docstring 字符串会二进制命中 —— 首次执行时正是因此命中 `_lib/iteration/__pycache__/*.pyc`） |
| AC-7 守卫红测 | **pass** | 注入 `skill_use("status")` 到 `README.md` 代码块 → `bats tests/integration/test_v4_doc_drift_contracts.bats` → **rc=1**，输出 `not ok 13 ...` + `# AC-11 violation: live skill_use("status") in code block of README.md`；`git checkout -- README.md` 还原后同一命令 → **rc=0**；`git status --porcelain README.md` → 空 |
| AC-8 跨仓人工 verify | **pass** | `~/.config/opencode/scripts/rdd-skills.sh`：`grep -c '^  status$'` → **0**；BUILTIN 项数 → **26**；`bash -n` → syntax OK。主路径 `bash scripts/rdd-skills.sh --json` → `available: 26`、`含 status: False`、`skills_source: manifest:/home/ubuntu/.agents/skills/rdd-workflow`、`installed_count: 26`、**rc=0**（改前同为 26/False ⇒ 行为等价）。fallback 路径（`HOME=/tmp/opencode/fakehome` 模拟零安装）→ `skills_source: builtin`、`available: 0`、`installed_count: 0`、**rc=1**（改前同 —— builtin 只影响「报告列出哪些名字」，不影响 installed/available 判定） |
| AC-9 相关测试 | **pass** | `bats tests/integration/test_v4_doc_drift_contracts.bats tests/integration/test_install_lib_distribution.bats tests/integration/test_roadmap_extraction.bats` → **rc=0**；`python3 -m pytest tests/integration/test_hook_boundary.py -q` → **6 passed** |
| AC-10 无新增失败 | **pass** | `python3 -m pytest tests/unit/ -q` → **3455 passed, 3 skipped**（与 `retire-status-skill` 验收时的基线一致） |
| AC-11 全量门 | **pass** | `BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression` → **`GATE_RC=0` / `✅ ALL PASSED`**。分项：isolation gate OK / ruff OK / mypy strict OK / rdd-doctor structural 10 类全过（2 类 warning）/ **bats regression: 评估 228/228，未评估 0，新增失败 0（482s）** / pytest unit **3455 passed, 3 skipped** / pytest integration **192 passed** |
| AC-12 原子性 | **pass** | rdd-workflow 仓单提交（待提交后确认 `git status --porcelain` 为空）+ opencode 仓单提交 `c149934`（`1 file changed, 5 insertions(+), 2 deletions(-)`） |

## 环境问题记录（首次全量门失败的真实原因）

第一次全量门（`/tmp/opencode/full_gate2.log`）报 `GATE_RC=1`，形态为 **pytest 5 failed + 77 errors，1.11s 跑完**。根因**不是本 change 的改动**：

```
E   OSError: could not create numbered dir with prefix test_xxx in /tmp/pytest-of-ubuntu/pytest-440 after 10 tries
```

→ `df -h /tmp` ⇒ **`overlay 30G 100% 满，Avail 0`**。即 pytest 无法创建 tmpdir，全部 setup 失败。

**修复**：清理运行时垃圾（`/tmp/pytest-of-ubuntu/*`、`~/.cache/pip`、仓库内全部 `__pycache__`）⇒ 释放 **6.5G**（30G→22G used）。

**同一份日志里的 bats 阶段是绿的**：`评估 228/228 个文件 / 未评估 0 / 新增失败 0 / OK (531s)` ⇒ bats 与 pytest 的失败**互不相干**，前者不受磁盘影响（bats 用 `BATS_TMPDIR` 且已有空间）。

**清理后单独复验**：`python3 -m pytest tests/integration/ -q` ⇒ **192 passed (155.79s)**（此前同一命令在该环境下是 5 failed + 77 errors）。

⇒ 按 verifier 契约的分类，这属**环境信号**（tmpdir 创建失败 = 资源耗尽），非判据信号，不得据此判 `ac-fail`。修复环境后重跑全量门。
| AC-13 孤立 `.pyc` 已清 | **pass** | `ls skills/__pycache__/ \| grep -E 'guide_arch\|guide_plan\|populate_roadmap'` → 0 命中（改前 3 个：`guide_arch` / `guide_plan` / `populate_roadmap_from_arch`，源文件均已不存在） |
| AC-14 零残留（语境收窄） | **pass** | a) `! grep -rnI --exclude-dir=__pycache__ 'status_render_mode_a' _lib/ skills/ tests/ tools/` → 0；b) `! grep -rnI --exclude-dir=__pycache__ 'skills/status/' _lib/ skills/ tools/` → 0；c) `! grep -rnI --exclude-dir=__pycache__ 'skills/status/' tests/ \| grep -v 'docs/legacy/'` → 0。全仓 `skills/status/` 剩余提及经逐条语境核对，**全部为正当命中**：`docs/migration/v3-to-v4.md` 的 3 处（归档记录小节）+ 守卫注释 1 处（说明归档位置）+ 本 change 工件 + 历史 superpowers 设计文档 |

## 判据缺陷修正记录

本次实施暴露了 **2 处 AC 判据本身的缺陷**（均已修正并回写工件，不改实现）：

1. **AC-4 过宽** —— 原判据 `! grep -n 'guide-ship\|execute\|status' tests/integration/test_hook_boundary.py` 会把该文件里大量 `status="proposed"` **测试夹具**误判为漂移。收窄为只查 skill 引用形态。
2. **AC-6 / AC-14 未考虑二进制 `.pyc`** —— 原判据 `! grep -rn 'skill_use("status"' ...` 命中了 `_lib/iteration/__pycache__/*.pyc`（陈旧字节码内嵌旧 docstring 字符串）。收窄为 `grep -rnI --exclude-dir=__pycache__`，并追加 AC-13 清掉 3 个孤立 `.pyc`。

⇒ 这两条印证了既有教训：**零残留判据必须区分「活指令」与「历史说明」，且必须带 `-I` 与 `--exclude-dir=__pycache__`**。

## 遗留清扫

- 本次范围内：T7.6 —— `git diff HEAD | grep -E '^\+.*(TODO|FIXME|breakpoint\(|pdb\.|console\.log)'` → **0 命中**；`git diff HEAD -- tests/ | grep -E '^\+.*\bskip\b'` → **0 命中**（无 TODO、无新增调试日志、无新增 skip、无未替换 mock）。
- 范围外既有遗留（**只记录，本 change 不承担**）：
  - `tools/phase2_path_migrator.py` 的 `SHARED_IN_LIB` 里其余 15 个 MISS 项（`state_vector.py` / `event_log.py` / `lock.py` 等）—— 已被 commit `c3a90fe`（flatten package layout）搬进 `_lib/core/` 与 `_lib/loop/` 子目录，属扁平化遗留。
  - `_lib/iteration/render.py::print_view` —— status 退役后**零生产调用方**（仅 `tests/unit/test_iteration_render_l2.py` 引用）⇒ 新死代码候选。
  - `docs/architecture/workflow-phases.md:331` 的 `` `status` (archive, P3) `` —— 归后续漂移 change。

## 失败项与路由建议

无。`implementation_gap` / `proposal_drift` 均不适用。

## 备注（不阻断）

1. **实施中修正了 2 处 AC 判据自身缺陷**（不改实现，已回写 proposal/tasks）—— AC-4 过宽、AC-6/AC-14 未排除 `.pyc`。详见上方「判据缺陷修正记录」。
2. **首次全量门失败是环境问题**（磁盘 100% 满），与改动无关 —— 详见上方「环境问题记录」。清理 6.5G 后重跑 `GATE_RC=0`。
3. **跨仓改动已先行提交**（`c149934`），因为它与主仓改动**互不依赖**、且另一并行会话正在 opencode 仓工作（`docs/CHANGELOG.md` / `docs/MULTI-AGENT-DESIGN.md` / `docs/adr/ADR-commit-verification-gate.md` / `tests/config-guards.test.ts` 有未提交改动，非本次产生）—— 及早提交可避免被 `git add -A` 类操作误带。opencode 仓的两条验证命令（`bun test tests/` 996 pass / 0 fail；`check-upstream-anchors.sh` 29/29 OK）在提交前实测通过。
4. **`skills/__pycache__/` 的 3 个孤立 `.pyc`** 已纳入本 change（AC-13）—— 它们会污染本 change 自身的零残留判据，且为 gitignored 未跟踪工件，删除零风险。**同时清理了全仓 `__pycache__`（释放约 7G，这是磁盘满的主因）**，该清理不进提交（gitignored）。
5. **`_lib/iteration/render.py::print_view` 已成为零生产调用方**（status 退役的连带后果，仅 `tests/unit/test_iteration_render_l2.py` 引用）⇒ 新死代码候选，记入后续。
