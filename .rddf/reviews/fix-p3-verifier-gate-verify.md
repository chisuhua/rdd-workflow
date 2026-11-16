# 验收报告：fix-p3-verifier-gate

> 验收者：verifier（角色）
> 验收对象：`openspec/fix-p3-verifier-gate` @ `2372dd6`（worktree `.rddf/wt/fix-p3-verifier-gate`，分支 `openspec/fix-p3-verifier-gate`，基线 `a63b692`）
> 验收时间：2026-11-16
> **已用轮次：1 / 3**（`RDDF_VERIFIER_MAX_LOOPS=3`）

## 判定来源

| 优先级 | 来源 | 采用 |
|---|---|---|
| 1 | 用户本次明确给出的验收条件 | 无（用户只说「merge / 继续」） |
| 2 | `proposal.md` 的 `## Acceptance` 段 | ✅ **采用（9 条）** |
| 3 | 本次变更自身声明的行为 | 备查（commit message + plan） |
| 4 | ADR 的 Verification 章 | 不适用（ADR-0035/0045 无 Verification 章） |

verdict cache：`.rddf/state/verifier/.ac-verdict-fix-p3-verifier-gate.json`（`codebase_commit = 2372dd6`，`verification_state: passed`，`failed_acs: []`）
audit log：`.rddf/state/verifier/.ac-verification.jsonl` 追加 1 行
归档门完整性校验（按门的方式传参）：`{"complete": true, "problems": [], "schema_version": 2}`

## 逐条判定（9/9 pass）

| AC | 判据要点 | 证据（工具 / 命令 / 结果） | 判定 |
|---|---|---|---|
| AC-1 | P3 归档前调用 `archive_gate_check`，无「`VERIFIER_EXIT` 初值 0 ⇒ 放行」 | `grep -n 'archive_gate_check\|VERIFIER_EXIT\|route_verifier_verdict\|increment_retry' phase3_archive.sh` → 仅命中 `:91` 的 `archive_gate_check "$CHANGE_NAME" "$TASKS_ROOT" \|\| exit 7` 与 `:87-88` 的可用性守卫；三个失效标识零命中。`bats test_rdd_builder_phase3_archive.bats` → 12/12 | **pass** (0.97) |
| AC-2 | `skills/` + `_lib/` 无 `verifier_run` 残留 | `grep -rn 'verifier_run' skills/ _lib/` → 零命中；`pytest tests/unit/test_phase3_verifier_wiring.py` → 2 passed（含静态守卫） | **pass** (0.98) |
| AC-3 | `openspec_tracked=false` 路径上 `archive_gate_check` 被执行（无 cache ⇒ 拒绝） | `bats test_archive_gate_tracked_false.bats` → ok 13 拒绝 / ok 14「拒绝来自 AC 门而非 worktree 查找」（status=3）/ ok 15 有 cache 放行 / ok 16 tracked 路径不变；`sed -n '607,622p' _lib/archive.sh` → false 分支新增 `archive_gate_check "$name" "$main_root" \|\| return 3` | **pass** (0.97) |
| AC-4 | cache 缺失 / 不完整 ⇒ P3 非零退出，文案复用 `:551-555`（三条出路） | `bats` → ok 1（缺失 ⇒ status 7 + 输出含 `no valid verdict cache`）、ok 8（verdict 不完整 / AC 集合不匹配 ⇒ status 7 + 输出含 `incomplete`）；`git diff master..HEAD -- _lib/archive.sh \| grep 'no valid verdict cache'` → diff 中无该文案 ⇒ 原样复用；`_lib/archive.sh:551-556` → 三条出路（`rddf rdd-verify` / `SKIP_RDD_VERIFIER` + REASON / cache 路径） | **pass** (0.95) |
| AC-5 | `SKIP_RDD_VERIFIER=yes` 无理由 fail closed；有理由写 `.bypass-audit.jsonl` | `bats` → ok 4（无 `RDDF_VERIFIER_BYPASS_REASON` ⇒ status 7 且输出含该变量名）、ok 5（有理由 ⇒ status 0 且 `.rddf/state/.bypass-audit.jsonl` 存在） | **pass** (0.97) |
| AC-6 | cache `codebase_commit` 与 HEAD 不符 ⇒ 不放行 | `bats` → ok 3（cache sha 为全 0 ⇒ status 7，输出含 stale / no valid verdict cache） | **pass** (0.96) |
| AC-7 | failed-AC 行为写死 + `STRICT_AC_GATE` 两态各一 | `bats` → ok 9（failed AC 且未开 strict ⇒ status 0，输出含 `failed ACs`）、ok 10（`STRICT_AC_GATE=yes` ⇒ status 7）；`grep -n 'Failed-AC policy' phase3_archive.sh` → 注释写明两态 | **pass** (0.96) |
| AC-8 | P3 bats 覆盖 complete / missing / stale-sha 三态并通过 | `bats test_rdd_builder_phase3_archive.bats` → 12 例全过，含 complete(ok 2) / missing(ok 1) / stale-sha(ok 3)，另加 incomplete(ok 8)、failed-AC 两态(ok 9/10)、worktree 缺失(ok 6)、0 完成任务(ok 7)、pkg-root 解析链(ok 11)、无 exit-code 判据(ok 12) | **pass** (0.97) |
| AC-9 | `run_verification.sh` 的 staging 语义与既有测试不变 | `git diff master..HEAD --stat -- skills/rdd-verifier/` → **空**（未触碰）；`bats tests/integration/test_rdd_verifier_*.bats` → **55 ok / 0 not ok**；`pytest tests/unit -q` → 3324 passed / 10 failed / 2 skipped ※见 D-1 | **pass** (0.96) |

**结论：9/9 pass，`verification_state: passed`，`failed_acs: []`。**

### 端到端复现（门的真实调用路径）

```
$ cd .rddf/wt/fix-p3-verifier-gate
$ bash -c 'source _lib/archive.sh; archive_gate_check fix-p3-verifier-gate "$(pwd)"'
⚠️  verifier contract: verification missing: rdd-verifier not run (legacy fallback …)
♻️  Reusing verifier verdict cache (commit 2372dd659c53b377b26a311adec0ebfb888a6a93)
  gate exit=0
```

对照（以主仓为 tasks_root）：`❌ 未实现 (0 个完成任务)` ⇒ exit 1 —— 说明门确实按 `$tasks_root` 定位输入，不是无条件放行。

## 判据本身的偏差（不改变 pass 判定，但必须记录）

**D-1（AC-9 的「全绿」前提在本仓不成立）**：`pytest tests/unit` 有 **10 项失败**，与本改动**逐条无关**：
`test_doc_contracts.py` ×4、`test_resolve_project_root_contract_python.py` ×5、`test_skills_lib_python_resolve_project_root.py` ×1 —— 全部是「项目根解析」类，断言期望 worktree 根、实际返回主仓根。
**基线对照**：在未含本改动的 `a63b692` 上另建 worktree 跑同样 3 个文件 → **同样 10 项失败、失败信息逐条相同** ⇒ 环境信号（worktree 内跑套件），非本 change 引入。
AC-9 的**实质意图**（`run_verification.sh` 的 staging 语义不变）由「目录零改动 + 55 例 bats 全绿」证实；「全绿」这一字面表述在本仓当前状态下无法满足（既有失败），按更严格的语义判定。

**D-2（AC-4 的「文案复用」在两条分支上措辞不同）**：cache **缺失**走 `:551-555`（三条出路）；cache **不完整**走 `:501`（`cached verdict is incomplete` + problems 列表），不含三条出路。两条都是门内既有文案，本 change 未新写。AC 判为 pass（复用成立），但「含三条出路」只对缺失分支成立。

## 遗留清扫复核

| 检查项 | 结果 |
|---|---|
| TODO / FIXME / 临时调试输出 | `_lib/archive.sh`、`skills/rdd-builder/scripts/phase3_archive.sh` 内无 |
| 半截实现 / 注释掉的代码 | 无（旧实现 92 行整体删除，非注释保留） |
| 被 skip 的测试 | 本 change 的 12 + 4 个 bats、2 个 pytest 全执行，无 skip |
| 未替换的 mock | 仅 bats fixture 内的 `bin/openspec` 桩与 `_lib` 符号链接（有意） |
| 越界改动 | `skills/rdd-verifier/`、`openspec/specs/`、`doctor_render.py` 均未动 |
| 意外入提交的文件 | `tests/KNOWN_FAILURES.txt` 曾被测试污染清空并误入提交 → 已回滚（87 行）并 amend，当前工作树干净 |

## 本轮发现的产品缺陷（转 follow-up，不阻断本 change）

| # | 缺陷 | 证据 | 建议 |
|---|---|---|---|
| **F-A** | **门读 cache 的位置与 agent 写 cache 的位置不同源**：门读 `$tasks_root/.rddf/state/verifier/`，而 agent 的 canonical resolver 把 cache 写到主仓 ⇒ worktree 模式下「照默认跑一次 rdd-verify」必然被判 stale | 实测：cwd=worktree 时 `rdd_verify_cmd --stage` 写到 `/workspace/main/rdd-workflow/.rddf/state/verifier/`；门以 wt 为 tasks_root 时读 wt 侧 | 已在本 change 的 phase3 注释里写明契约（验证必须在 `$TASKS_ROOT` 内进行）；**根修**（门内解耦 tasks_root 与 cache root）留给 `fix-worktree-archive-path` 或新提案 |
| **F-B** | `verifier_contract_check` 内部按 `_main_repo_root` 解析 cache（与 bash 的 `$tasks_root` 不同）⇒ worktree 模式下恒报「verification missing」，只靠 legacy fallback 降级为 WARNING | 实跑输出：`⚠️ verifier contract: verification missing: rdd-verifier not run` | 与 F-A 同源，一并处理 |
| **F-C** | `phase1_5_deps.sh:55` 的 `task_count = 5` 是**硬编码**（不读 tasks.md）⇒ mode 判定不准 | 读源码 | 观察项 |
| **F-D** | 测试污染两处：① `test_known_failures_baseline.bats` 直接写真实 `tests/KNOWN_FAILURES.txt`（setup 备份/teardown 还原，还原失效即留残值）；② `phase0: approve writes spec.md` 只断言 `openspec/specs/test-change/spec.md` **存在**，而该文件是历史残留 ⇒ 干净环境下必失败、主仓「通过」是污染凝视 | 实测：主仓存在该残留文件；clean worktree 缺失 ⇒ 用例失败 | 测试隔离缺陷（既有主题 `feat-fix-test-isolation-and-hygiene`），建议另立 |
| **F-E** | 全量 bats `--regression` 的 baseline 与现状不符：`已知失败: 11` 已登记，但另有 2 项实际失败未被登记（其中 1 项就是 F-D 的污染凝视，另 1 项 `run_arch_env_check_discovers_counts` 主仓同样失败、baseline 里只有一句「→ passes」的 stale 注释） | 全量 bats 回归输出 + 主仓逐条复现 | baseline 需要一次 refresh（`tests/scripts/refresh_known_failures.sh`） |

## 结论

**9/9 AC pass，verdict cache 完整且被归档门接受（`{"complete": true, "problems": []}`），可进入 P3 归档。**

F-A / F-B 是本 change 暴露出的**架构级耦合**（worktree 模式 + canonical 状态根 + 单根 gate 假设），本 change 已用「同根契约 + 注释」把行为固定下来，根修留给下一项 `fix-worktree-archive-path`；F-C / F-D / F-E 为观察与既有缺陷，不阻断本 change。
