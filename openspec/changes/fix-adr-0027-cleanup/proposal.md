# fix-adr-0027-cleanup

## Why

ADR-0027（持续演进反馈环）经过 Oracle 第一轮 review 返回 **NEEDS-REVISION**（3 Critical + 7 Major + 10 Minor），应用 20 项 fix 后 Oracle 第二轮 review 返回 **PASS-WITH-MINOR-FIXES**（Pattern 8/10、Privacy 8/10、Implementation 7/10）。本 change 收尾 5 项剩余 cleanup 并形式化采纳 ADR-0027。

5 项剩余 cleanup（按风险分级）:

| ID | 严重度 | 内容 |
|----|--------|------|
| R1 | medium | §6.3 python 骨架 env-var 位置错（命令行后置→argv 不是 env）+ 缺 `import sys` + 多余 stdin 管道 |
| R2 | low | 9 处残留旧路径/字串（`_lib/sanitizer.py` × 4、`.rddf/config.yaml` × 3、"匿名化" × 1、`conflict-report` × 1）|
| R3 | low | References 重复条目（shim 路径 × 2、ADR-0010 × 2）|
| R4 | low | triage 标签生命周期漏洞（y/n/d 动作不移除 `needs-triage` → issue 反复出现）|
| R5 | trivial | env 前缀不统一 `RDD_REPORT_*` vs `RDDF_REPORT_*` |

5 项均已在本 change 起草时全部应用。Oracle 建议："Ship it after one 30-minute cleanup pass — no re-review needed."

## What Changes

**In Scope**:

- 应用 5 项 R1-R5 cleanup 到 `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md`
- 翻转 ADR-0027 状态 `待定` → `已采纳`
- 在 ADR-0027 头部增加 Oracle 复核记录
- 更新 `docs/adr/README.md` 索引：把 ADR-0027 加入表格 + 加入 v2.1+ ADR 实施状态映射

**Out of Scope**:

- 不实施 ADR-0027 的实际代码（属于 change-a / change-b / change-c 范围）
- 不修改任何 ADR 内容决策（仅执行 Oracle 已批准的修正）
- 不创建 `openspec/changes/fix-adr-0027-cleanup/` 之外的 change
- 不修改 `_lib/` 或 `skills/` 任何运行时代码（本 change 仅文档）

### 关键场景

- GIVEN Oracle 已批准 PASS-WITH-MINOR-FIXES, WHEN 本 change 完成 5 项 R1-R5, THEN `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` 中 9 处残留字符串 + 1 处 python bug + References 重复 + triage 标签漏洞全部修复
- GIVEN 5 项 cleanup 已应用, WHEN 翻转 ADR 状态, THEN ADR-0027 头部 `**状态**` 字段从 `待定` 改为 `已采纳`，且记录 Oracle 复核日期与评分
- GIVEN 索引更新, WHEN 跑 `openspec validate fix-adr-0027-cleanup --type change`, THEN 0 errors

## Capabilities

- MUST 修复 §6.3 python 骨架 env-var 位置、补充 `import sys`、移除多余 stdin 管道
- MUST 全局替换 9 处残留字符串（5 类，详见上表）
- MUST 给 triage 菜单的 y/n/d 动作加 `--remove-label needs-triage` + 状态标签
- MUST 统一 env 前缀为 `RDDF_REPORT_*`
- MUST 翻转 ADR-0027 状态为 `已采纳` 并记录 Oracle 复核
- MUST 更新 `docs/adr/README.md` 索引
- MUST NOT 修改 ADR-0027 的任何架构决策（仅执行 Oracle 批准的编辑级修正）
- MUST NOT 引入新的运行时代码或脚本

## Impact

- 影响范围：仅 `docs/adr/ADR-0027-continuous-evolution-feedback-loop.md` 和 `docs/adr/README.md`
- 风险：低 — 纯文档修正，5 项 cleanup 均为 Oracle 验证后的具体 edit suggestion
- 兼容性：高 — 文档变更不破坏任何 API、contract 或 handoff

## Acceptance

- ADR-0027 文件中 9 处残留字符串全部替换（`grep -c` 验证 0 hit）
- §6.3 python 骨架 env-var 在命令**前**置（手工 review 通过）
- §5 triage 菜单的 y/n/d 动作后跟 `--remove-label needs-triage` 命令
- ADR-0027 头部 `**状态**` 为 `已采纳`，且包含 Oracle 复核记录
- `docs/adr/README.md` 索引表格包含 ADR-0027 行
- `openspec validate fix-adr-0027-cleanup --type change` 0 errors
- `./test.sh --quick` 0 regression（文档变更理论上无影响，跑测试作为 sanity check）
- commit message 符合 conventional commit（`docs(adr): apply Oracle review cleanup to ADR-0027`）
