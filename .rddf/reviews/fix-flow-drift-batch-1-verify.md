# 验收报告：fix-flow-drift-batch-1

> 验收者：verifier（角色）｜对象 `openspec/fix-flow-drift-batch-1` @ `c500265`（已合入 master，基线 `86191a5`）
> 验收时间：2026-11-17｜**已用轮次：1 / 3**
> 判定来源：`proposal.md` 的 `## Acceptance`（8 条）

| AC | 证据 | 判定 |
|---|---|---|
| 1 SKILL.md 正则含三变体 | `grep` 命中 `验收标准\|Acceptance Criteria\|Acceptance`（1 行） | pass 0.98 |
| 2 行为测试：三种段头经 `parse_acs` 均得预期条数 | `pytest tests/unit/test_rdd_verifier_protocol_headers.py` → **4 passed**（3 个 parametrize 段头 + 1 个存在性断言） | pass 0.98 |
| 3 fix_hint 按 kind（file 无斜杠 / dir 有） | `bats test_doctor_layout_fix_hint.bats` → **2/2**（改动前第 1 例红，已验红→绿） | pass 0.97 |
| 4 `--dry-run` 零写入 | `bats test_rdd_verify_dry_run.bats` ok 1：前后 `find` 快照一致、无 `verifier/` 目录 | pass 0.97 |
| 5 `--dry-run` 输出 would-migrate | ok 2：输出含 `would migrate` 与文件名 | pass 0.96 |
| 6 `--dry-run --stage` 互斥 exit 2 | ok 3：`mutually exclusive` + status 2（检查已前置到任何输出之前） | pass 0.97 |
| 7 `--stage`（非 dry-run）仍迁移并 stage | ok 4：legacy cache 被迁移到 `verifier/` 且 context 文件生成 | pass 0.96 |
| 8 `./test.sh --unit` + `test_rdd_verifier_skip.bats` 全绿 | **主仓**（合并后代码）`pytest tests/unit -q` → **3338 passed / 2 skipped / 0 failed**；`bats test_rdd_verifier_skip.bats` → **8 ok / 0 not ok** | pass 0.96 |

**结论：8/8 pass。**

## 说明

- AC-8 的「unit 全绿」在**主仓**成立（worktree 内跑会有 10 项根解析环境失败，那是 worktree 布局的信号，与本 change 无关）。本 change 的验收在主仓执行，故拿到干净数据。
- critic 第 1 轮 APPROVE（0 BLOCKER）；SHOULD_FIX（运维文档 §4 输出枚举补 `would migrate` 行）与 2 个 NIT（互斥检查前置 / SKILL.md 措辞）均已处置，并补了一条 `--stage` 非 dry-run 的显式测试。

## 遗留清扫

无 TODO/半截实现/被 skip 的测试；三处改动各自带回归测试；未触及 `openspec/specs/`、`doctor_render.py`。
