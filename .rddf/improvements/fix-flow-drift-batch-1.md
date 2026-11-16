---
优先级: P2
priority: P2
来源: 2026-11-16 rddf-layout-manifest 验收/归档过程发现（follow-up F-1 残余 + F-2 + F-5）——三处契约/行为漂移：文档正则缺变体、fix_hint
  给文件加尾斜杠、--dry-run 仍写盘
阶段: phase-2
分类: bugfix
类型: bugfix
状态: approved
approved_at: 2026-11-16
approved_by: rdd-planner
review_notes: "metis 1 轮（2026-11-16，5 份合并调用，每份 1 轮在预算内）；4 处 P0 采纳并重写草案，逐条处置见正文「## 审稿记录」；7 段 + 主题校验 PASS；已 attach 到 阶段步骤化执行/phase-2"

生成时间: 2026-11-16
roadmap_ref:
  project_id: 阶段步骤化执行
  phase: phase-2
---

# fix-flow-drift-batch-1

**主题**: 阶段步骤化执行

## 审稿记录

metis 1 轮（2026-11-16，planner 阶段 gap 分析）。逐条处置：

- **采纳 P1-2（元测试换行为测试）**：原草案要加「文档正则 == 实现正则」的跨文件字符串比对 ——
  SKILL.md 里是代码块、`protocol.py` 里是 Python 原始字符串，逐字比对会因格式而非语义断裂。已改为
  三条行为断言（三种段头各一）+ 一条存在性断言。
- **采纳 P1-3（dry-run 边界写全）**：补 `--dry-run --stage` 的处理（定死为互斥、argparse 报错 exit 2），
  并要求 dry-run 输出 `Would migrate N ...`（信息不丢、副作用归零），而不是静默跳过。
- **采纳（glob 条目）**：`layout_check.py` 有 `_is_glob`，但 `RDFF_LAYOUT` 当前只有 `dir`(12) /
  `file`(2) ⇒ 已注明二元分支现状，若将来加 glob 按「指向目录则加斜杠」补分支。
- **采纳（既有 dry-run 测试的行数断言风险）**：已注明实施时需确认
  `test_rdd_verifier_skip.bats:73-75` / `test_rdd_verifier_e2e.bats:115-121` 是否依赖整段输出。
- **采纳（`--stage` 迁移必要性）**：确认 `--stage` 分支在 dry-run 判断之前（`:418-429`）就 return，
  迁移对它仍是必要的 ⇒ AC 明确「`--stage` 保留迁移」。
- **记录**：`protocol.py:33-35` 注释提到与 `ac_verifier` 同源；本项只对齐 SKILL.md 与
  `protocol.py` 两处，第三份副本（若存在）需另行确认，不并入本项范围。

## 架构依据

三条独立的小缺陷，共同点是「契约说 A、行为是 B」，且都不阻断主流程、只在特定路径上误导人或写错盘：

1. **文档正则缺变体**：`skills/rdd-verifier/SKILL.md:155` 写
   `^##\s+(?:验收标准|Acceptance Criteria)\s*$`，而实现 `_lib/verifier/protocol.py:34` 是
   `^##\s+(?:验收标准|Acceptance Criteria|Acceptance)\s*$`。**实现是对的，文档没跟上** ——
   按文档照做的 agent 会误判 `## Acceptance` 段不被识别（本次验收我就在这上面误判过一轮）。
   注意这是**文档漂移**，不是运行时缺陷：实测 `ac_count: 18`，`## Acceptance` 一直被正确解析。
2. **fix_hint 对 file 条目加尾斜杠**：`skills/rdd-doctor/scripts/checks/layout_check.py:126` 统一生成
   `f"create .rddf/{e.path}/ — see docs/architecture/rddf-layout.md"`，而 `RDFF_LAYOUT` 的 14 条里有
   2 条是 **file**（`roadmap.md` / `project.yaml`）⇒ 实测输出 `create .rddf/roadmap.md/`，指向一个
   不可能创建的目录名。
3. **`--dry-run` 仍写盘**：`_lib/cli/rdd_verify_cmd.py:410` 的 `_migrate_legacy_state(project_root)`
   在 dry-run 判断（`:440` / `:461`）**之前**无条件执行。fixture 实测：
   `rddf rdd-verify --dry-run` 先输出 `📦 moved legacy verifier state → .rddf/state/verifier/.ac-verdict-probe.json`
   并把文件真移走，然后才打印 `[dry-run] Would ...`。dry-run 的契约是「不改变磁盘状态」。
   附带边界：`--stage` 分支（`:418-429`）在 dry-run 判断之前就 `return 0`，因此
   `--dry-run --stage` 会**写出** context 文件 —— 同一契约的第二个面，需一并定死。

## 范围

- **In Scope**：① 对齐 SKILL.md 的正则并加**行为**测试；② fix_hint 按 `kind` 分支 + bats 两条断言；③ `--dry-run` 零副作用（含迁移的报告化）+ `--dry-run --stage` 的互斥定死。
- **Out Scope**：不重构 `layout_check.py` 的三支判据；不改 `migrate_legacy_state` 的迁移规则（只加 dry-run 参数）；不改 `RDFF_LAYOUT` 条目集合；不动 SKILL.md 其他段落；不引入跨文件字符串相等比对（见下）。

## Why

三条各自都很小，合并成一批是为了不各占一个 improvement 的立项/审稿成本；但它们**不该被各自忽视**
的理由一致：都是「说一套、做一套」。

`--dry-run` 写盘最危险 —— 用户/CI 拿它做预演，结果它改了状态。本次只是移了几个旧状态文件，但同一模式
下任何新增写动作都会被误认为是「安全的预演」。

`fix_hint` 的错路径会被用户/agent 直接照抄执行（`create .rddf/roadmap.md/` 必然失败）。

`SKILL.md` 的正则漂移会让读文档的 agent 重复我这次的误判 —— 代价是一次错误的「假阴性」结论和一轮返工。

## What Changes

1. **SKILL.md 对齐实现**：`skills/rdd-verifier/SKILL.md:155` 改成与 `protocol.py:34` 一致的三变体。
   **测试用行为断言**：三个 fixture proposal 分别用 `## 验收标准` / `## Acceptance Criteria` /
   `## Acceptance` 作段头，断言 `parse_acs` 均得到预期条数；另加一条存在性断言（SKILL.md 同时含三个
   变体字符串）。**不做「文档字符串 == 实现字符串」的跨文件比对** —— 前者在 Markdown 代码块里、后者是
   Python 原始字符串，逐字比对会因格式而非语义断裂。
2. **fix_hint 按 kind 分支**：`target = f".rddf/{e.path}/" if e.kind == "dir" else f".rddf/{e.path}"`
   （当前 `kind` 取值只有 `dir`(12) / `file`(2)；`layout_check.py` 虽有 `_is_glob` 用于匹配，
   但清单里暂无 glob 条目 —— 若将来新增，实施时按「globs 指向目录则加斜杠」补分支并在文档注明）。
   bats 加两条断言：dir 条目有尾斜杠、file 条目无尾斜杠。
3. **`--dry-run` 零副作用**：
   - 给 `_lib/verifier/cache.py::migrate_legacy_state(project_root, dry_run=False)` 加参数，
     dry-run 时返回 `("would-move", name)` 而不移动；
   - `rdd_verify_cmd.py:410` 的调用改为传入 `parsed.dry_run`，并把 `would-move` 打印成
     `[dry-run] Would migrate N legacy verifier state file(s): ...`（**信息不丢、副作用归零**，
     而不是静默跳过）；
   - `--dry-run --stage` 定死为**互斥**：同时给出时 argparse 层报用法错误并 exit 2（`--stage`
     本身会写 context 文件，与 dry-run 契约冲突）。
4. 测试：pytest 对 legacy fixture 断言 `--dry-run` 前后 `.rddf/state/` 文件快照一致；
   bats 断言 `--dry-run` 输出含 `Would migrate`（当存在 legacy 文件时）。

## Acceptance

- [ ] SKILL.md 的正则含 `验收标准` / `Acceptance Criteria` / `Acceptance` 三变体
- [ ] 行为测试：三种段头的 fixture proposal 经 `parse_acs` 均得到预期条数（3 个用例）
- [ ] `layout_check.py` 的 missing-required fix_hint：`file` 条目无尾斜杠、`dir` 条目有尾斜杠（bats 两条断言）
- [ ] `rddf rdd-verify --dry-run` 对含 legacy 状态文件的 fixture**不产生任何写入**（前后目录快照一致）
- [ ] `--dry-run` 在有 legacy 文件时输出 `Would migrate N ...`（信息不丢）
- [ ] `--dry-run --stage <change>` 报用法错误并 exit 2（互斥定死）
- [ ] `rddf rdd-verify --stage <change>` 仍会迁移旧 cache 并正常 stage（stage 路径未被 dry-run 修复破坏）
- [ ] `./test.sh --unit` + `bats tests/integration/test_rdd_verifier_skip.bats` +
      `bats tests/integration/test_rdd_verifier_e2e.bats` + `bats tests/integration/test_doctor_layout.bats` 全绿

## Capabilities

- 文档与实现的正则契约由行为测试守（三种段头都验），不再靠人眼比对
- doctor 的 fix_hint 对 file / dir 给出可执行路径
- `--dry-run` 恢复「零副作用」契约，且仍报告待迁移数量
- `--dry-run --stage` 的不确定组合被显式拒绝，而不是各自按自己的语义执行

## Impact

- **影响面**：`skills/rdd-verifier/SKILL.md`（一行）、`skills/rdd-doctor/scripts/checks/layout_check.py`（一处）、
  `_lib/verifier/cache.py`（加一个参数）、`_lib/cli/rdd_verify_cmd.py`（调用 + 参数校验）+ 对应测试。
- **风险**：`--dry-run` 的输出行序/行数会变（迁移从「先执行」变为「报告」）——
  `tests/integration/test_rdd_verifier_skip.bats:73-75` 与 `test_rdd_verifier_e2e.bats:115-121`
  用子串断言，实施时需确认它们不依赖整段输出（若依赖则一并更新）。
- **兼容性**：`migrate_legacy_state` 新参数默认 `False` ⇒ 既有调用方行为不变；
  三处输出改动均为措辞/副作用修正，无 API 破坏。
