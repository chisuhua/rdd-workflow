# Design: guide-design Phase Implementation

> **Document hierarchy**: `spec.md` 是契约 source of truth;`tasks.md` 是 work item 清单;本文件 sketches 均为 **illustrative**——实现以 tasks.md 为准,代码风格以本仓 `_lib/*.sh` 现有约定为准(函数内 `return N` 而非 `exit N`;bash→Python 一律 env-var 传递,禁止字符串插值 heredoc,即 Oracle C1 模式)。

## 0. 决策记录 (2026-07-30,用户决策)

| # | 决策点 | 结论 | 影响 |
|---|--------|------|------|
| D1 | ADR 处理 | **不动 ADR-0003** | ADR-0003 三阶段描述与代码漂移,接受为已知风险;docs 描述四阶段 |
| D2 | 升级策略 | **硬切换** | design-done 门控默认强制;逃生口 = 显式 `SKIP_ARCH_HANDOFF=yes`(同时跳过 arch+design)或 direct-create fallback;README/AGENTS banner 与门控同 commit |
| D3 | scan-state.sh | **纳入本 change** | bash 扫描器与 `guide_cmd.py` 同步升级 4-state,两个入口推荐一致 |
| D4 | 老脚本处理 | **替换** | `guide-arch/scripts/arch_proposal_review.sh` / `approve_proposal.sh` 内容替换为 ~10 行 shim,杜绝双份代码 |

## 1. 架构目标

将当前 `arch` 阶段的 Phase 5.5(提案审批)提取为独立的一级阶段 `design`:

```
arch (Phase 1-6) → design (Phase 1-5) → plan (Phase 1-4) → ship (Phase 1-4)
   "为什么这么建?"    "要改什么?"          "怎么实现?"         "执行了吗?"
   ADR+roadmap       提案生命周期         change artifacts    执行+归档
   +差距分析          +add-improve        +deps              +cleanup
```

## 2. 新增的 design 阶段

### 2.1 状态机:Phase 1-5 (illustrative sketches)

**Phase 1: setup** — 环境检测 + 读 arch-handoff(硬依赖,缺失则拒绝并提示先跑 `guide-arch`)+ rddf-session hook(`stage_design`,parent=stage_arch)+ 展示 arch 上下文(ADR 数、roadmap 阶段、差距分析数)。错误处理用函数 `return 1`,不写 `exit 1`。

**Phase 2: proposal intake** — 双源扫描 `improvements/` + `proposal-suggestions.md`(逻辑从 `arch_proposal_review.sh::scan_pending_proposals` 搬移),交叉排除已批准/已拒绝/已延迟/已归档。

**Phase 3: proposal review** — 逐一交互:y(批准→`approve_proposal.sh`→`proposal-approved.md`)/ n(拒绝→suggestions 状态列标 `已拒绝`)/ d(延迟→标 `延迟`)/ s(跳过);保留现有批量批准(a,作用于全部待审提案,与现行为一致)。**状态字段 = `proposal-suggestions.md` 表格的 `状态` 列**,合法值 `{待讨论, 已批准, 已拒绝, 延迟}`(见 `docs/proposal-suggestions-format.md` §Table columns)。

**Phase 4: design-done gate** — 遍历 `proposal-suggestions.md`,所有条目 `状态` 列 ∈ {已批准, 已拒绝, 延迟} 才通过;否则列出未决策提案并拒绝。

**Phase 5: design-done exit** — 调用 `skills/guide-design/scripts/write_design_handoff.sh`(env-var 模式,内部调 `write_design_handoff.py`)写 `.rddf/state/.design-handoff.json`;关闭 `stage_design` rddf-session。

**重复运行语义**:若 `.design-handoff.json` 已存在且无新增待审提案 → NOOP,提示 "design-done 已完成,无新提案";若有新增待审提案 → 仅审查新增条目,完成后更新 handoff(覆盖写,`design_complete_at` 刷新)。

### 2.2 Handoff schema (`design_handoff_schema.json` v1)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "design-handoff",
  "type": "object",
  "required": ["design_complete_at", "proposals_reviewed", "all_proposals_have_decision", "version"],
  "properties": {
    "design_complete_at": { "type": "string", "format": "date-time" },
    "proposals_reviewed": { "type": "integer", "minimum": 0 },
    "all_proposals_have_decision": { "type": "boolean" },
    "version": { "type": "integer", "const": 1 }
  },
  "additionalProperties": false
}
```

## 3. 修改的 arch 阶段

- 删除 `skills/guide-arch/SKILL.md` Phase 5.5 全节(~100 行)
- 在 frontmatter 之后、`## Phase 1` 之前插入 deprecation notice 框(统一文本见 spec.md deprecation-text Scenario)
- Phase 6 arch-done:输出不含提案计数;末行输出 `💡 Next: skill_use("guide-design")`
- **注意**:`arch-handoff.json` schema 当前**不含** `proposals_reviewed` 字段(已核实 `write_arch_handoff.py`),无需 schema 变更

## 4. 修改的 plan 阶段

### 4.1 design-done 门控位置(关键:在 arch 检查之后,与既有逃生口对齐)

```
run_plan_intake():
    if SKIP_ARCH_HANDOFF=yes:
        提示 "跳过 arch + design handoff 检查"; return 0     # 既有逃生口,同时豁免两门控
    check arch-handoff (既有逻辑,含 direct-create fallback)
    check design-handoff (新增):
        若 .design-handoff.json 存在 → 校验 schema v1 + all_proposals_have_decision=true
        若不存在 → 尝试 check_direct_create_fallback(有归档 change 的存量项目豁免)
        否则拒绝: "❌ design-done 未完成,必须先运行: skill_use(\"guide-design\")"
```

- 新增 `SKIP_DESIGN_HANDOFF=yes` 单独逃生口(仅跳过 design 门控,用于紧急场景),默认**不设**(D2 硬切换)
- `check_design_handoff` 实现遵循 env-var 模式(PROJECT_ROOT 经环境变量传入,无字符串插值),内联于 `plan_intake.sh`(~15 行),与 Round A Task 3 模式一致

### 4.2 同 commit banner(D2 硬切换的缓解措施)

门控启用的**同一个 commit** 必须包含:
- `README.md` 顶部 banner:`⚠️ v2.1+: arch 与 plan 之间新增 design 阶段;存量项目请先运行 skill_use("guide-design"),或设置 SKIP_ARCH_HANDOFF=yes 临时跳过`
- `AGENTS.md` 三阶段架构表更新为四阶段 + 同样的提示

## 5. 双扫描器 4-state 升级(D3)

**两个实现必须同步修改,保证 `rddf guide` 与 `skill_use("guide")` 推荐一致:**
- `skills/_lib/cli/guide_cmd.py::_scan_state()` (Python,`rddf guide` CLI)
- `skills/guide/scripts/scan-state.sh::scan_state()` (bash,`guide` 技能经 `guide_entry.sh` 调用)

### 5.1 完整优先级阶梯(保留全部现有分支)

```
1.  arch-handoff 存在 且 design-handoff 缺失:
    1a. ADR < 1            → guide-arch  (恢复: ADR 数量不足)     [保留现有分支]
    1b. ADR ≥ 1            → guide-design (arch-done 已完成 → 进入设计阶段)  [新增]
2.  design-handoff 存在 且 plan-handoff 缺失
                         → guide-plan   (design-done 已完成 → 进入变更生成) [新增]
3.  plan-handoff 存在:
    3a. active_changes > 0 且 fs 一致   → guide-ship             [保留]
    3b. active_changes == 0             → guide-ship (清理/归档)  [保留]
    3c. stale(handoff N 个,fs 0 个)    → guide-arch             [保留]
4.  worktree 有未完成任务  → guide-ship                          [保留]
5.  worktree 存在(分离/完成)→ guide-ship                        [保留]
6.  HEAD 有已 commit change → guide-ship                         [保留]
7.  无任何 handoff:
    7a. 无 roadmap.md       → guide-arch                         [保留]
    7b. 有未审批提案        → guide-design (原路由 guide-plan 是缺陷,修正)
    7c. 无 changes dir      → guide-plan                         [保留]
    7d. 其他                → guide-ship                         [保留]
```

变更点仅两处:(a) 插入 1b/2 两个 design 相关分支;(b) 7b 未审批提案路由 `guide-plan → guide-design`。其余分支逐字保留。

## 6. rddf-session 变更(修正:真实文件位置)

| 文件 | 改动 |
|------|------|
| `skills/rddf-session/scripts/rddf_session_pkg/_types.py` | `_VALID_KINDS` 追加 `"stage_design"`;`_KIND_ALIAS` 追加 `"guide-design": "stage_design"` |
| `skills/_lib/schemas/sessions_schema.json` | `kind` 枚举追加 `"stage_design"`;`goal.intent` 枚举追加 `"guide-design"`;`version` 保持 `const: 1`(additive 枚举扩展对既有数据兼容,既有 sessions.json 无需迁移) |
| `skills/rddf-session/scripts/rddf_session_hooks.sh` | `parent_kind_map` 追加 `"stage_design": "stage_arch"`;修改 `"stage_plan": "stage_arch"` → `"stage_plan": "stage_design"` |

**parent 变更说明**:`stage_plan` 的 parent 从 `stage_arch` 改为 `stage_design` 是行为变更——新 plan 会话将解析 `stage_design` 父级(若用户跳过 design 直接 plan,parent 解析结果为 None,现有代码 `parents[0] if parents else None` 优雅降级,不报错)。既有会话的 `parent_session_id` 已固化,不受影响。

**design.md 初版错误修正**:初版引用 `skills/_lib/session.py` 的 `SESSION_KINDS`——该文件中不存在此符号,类型验证实际位于 `_types.py`。以本表为准。

## 7. 脚本迁移与 shim(D4 替换)

### 7.1 迁移表

| 旧路径 | 新路径 | 改动 |
|--------|--------|------|
| `guide-arch/scripts/arch_proposal_review.sh` | `guide-design/scripts/design_proposal_review.sh` | 函数 `arch_proposal_review` → `design_proposal_review`;内部 `$SCRIPT_DIR` 解析自然指向新目录(`BASH_SOURCE[0]` 相对解析,`_lib` 相对路径 `../../_lib` 仍成立);逻辑不变 |
| `guide-arch/scripts/approve_proposal.sh` | `guide-design/scripts/approve_proposal.sh` | 纯路径搬移 |

### 7.2 Deprecated shim(包装函数形式,**非立即执行**)

老路径文件内容**整体替换**为:

```bash
#!/usr/bin/env bash
# DEPRECATED (v2.1, removal in v2.2.0): moved to skills/guide-design/scripts/design_proposal_review.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../guide-design/scripts/design_proposal_review.sh"
arch_proposal_review() {
    echo "⚠️ DEPRECATED: guide-arch Phase 5.5 已迁移到 guide-design (v2.1);请使用 skill_use(\"guide-design\")" >&2
    design_proposal_review "$@"
}
# 直接执行(非 source)时保持旧行为
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    arch_proposal_review "$@"
fi
```

关键点(Oracle B1 修复):
- `source` 该文件的调用方获得 `arch_proposal_review` 函数定义(包装),后续 `arch_proposal_review "$PROJECT_ROOT" "$PHASE_5_5_ENTRY"` 正常工作
- 不在文件作用域立即调用,`$@` 为空的问题不存在
- `approve_proposal.sh` 的 shim 同理(函数名不变,仅加警告 + 转发)

**调用方扫描**:实施前用 `grep -rn "arch_proposal_review" skills/ tests/` 枚举全部调用方,确认 shim 覆盖所有调用形式(source 后调用 / 直接执行)。

### 7.3 既有测试同步

`tests/integration/test_proposal_defer.bats` 4 个结构性 grep 指向老路径文件内容(`DEFERRED_COUNT`/`SHOW_ALL`/`view-all`/`已推迟`)。shim 替换后这些 grep 全部失败——**同步更新为 grep 新路径** `guide-design/scripts/design_proposal_review.sh`,并新增 1 个 shim 行为测试(调用老路径函数,断言 stderr 含 DEPRECATED 且功能正常)。

## 8. 测试策略

### 8.1 新增测试(按 tasks.md 分组)

| 组 | 数量 | 类型 |
|----|------|------|
| P1 schema+helper | 4 | Python unit |
| P2 脚本迁移+SKILL.md | 8+1(shim 行为) | bats |
| P3 arch 简化 | 2(deprecation notice + Phase 5 门控回归) | bats(另更新 4 个既有 test_proposal_defer) |
| P4 plan 门控 | 6(arch-only 拒绝 / invalid schema 拒绝 / valid 通过 / SKIP_ARCH_HANDOFF 双跳过 / SKIP_DESIGN_HANDOFF 单跳过 / direct-create fallback 豁免) | bats |
| P5 双扫描器 | 4 Python unit(guide_cmd) + 7 bats(7 种 handoff 组合 × 两个扫描器断言一致) | 混合 |
| P6 session | 1 Python unit + 4 bats(create/resume/abandon + stage_arch→stage_design→stage_plan 完整链) | 混合 |
| P7 add-improve 集成 | 3 bats(e2e: add-improve 创建 → design 扫描到 → y 批准落入 proposal-approved.md) | bats |
| P8 安装/冒烟验证 | 2 bats(INSTALL 子技能列表含 guide-design;smoke.bats glob 覆盖 14 个 SKILL.md) | bats |

合计 ~9 Python unit + ~28 bats ≈ **37 个新增**,另更新 4 个既有。

### 8.2 回归(必须全绿)

```bash
npm test                                        # bats 全量(含 smoke)
python3 -m pytest tests/unit/ -q --tb=short
python3 -m pytest tests/integration/ -q --tb=short
```

### 8.3 硬切换回归测试(D2 必配)

新增 `tests/integration/test_plan_design_gate_legacy_break.bats`:GIVEN 项目仅有 `.arch-handoff.json`(无 `.design-handoff.json`、无归档 change),WHEN 调用 plan intake,THEN 拒绝且错误信息含 `skill_use("guide-design")`——锁定"老流程现在正确失败"这一破坏性变更。

## 9. 实施顺序与安全停止点

按 tasks.md 的 P1→P9 顺序。两个关键风险点:

1. **P2 完成时**:新脚本已就位 + 老路径已替换为 shim(同组任务,无双份代码窗口,D4)。安全。
2. **P4 完成时**:plan 门控启用 + README/AGENTS banner 同 commit。此后存量项目 plan 需先跑 design——这是 D2 的预期行为,banner 已就位。**此点之后不可单独回滚 P4 而不回滚 banner。**

其余每个 P 组完成均为安全停止点(P1 纯新增、P3 仅 arch 简化、P5-P8 不破坏 runtime)。

## 10. Rollback 策略

- **P4 之前**:git revert 即可,无 runtime 状态变更(`.design-handoff.json` 若已写入,删除即可,无消费者)。
- **P4 之后**:revert 需同时还原 plan_intake 门控 + banner;`sessions_schema.json` 枚举扩展是 additive,revert 后既有含 `stage_design` 的 sessions.json 条目会因枚举收缩而校验失败——rollback  rehearsal 必跑:`python3 -m pytest tests/unit/test_rddf_session.py tests/integration/ -k session -q` 确认 session 模块在 revert 后不崩溃(或同时清理 sessions.json 中的 stage_design 条目)。
- **禁止部分回滚 P5**:两个扫描器必须同进同退,否则 `rddf guide` 与 `skill_use("guide")` 推荐分裂。