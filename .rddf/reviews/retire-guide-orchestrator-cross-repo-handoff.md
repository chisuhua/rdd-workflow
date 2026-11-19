# retire-guide-orchestrator — 跨仓交接单（需 architect 角色）

> **状态**: 本仓侧全部完成；archive 被 2 项跨仓治理面改动阻塞。
> **依据**: ADR-0063 Decision 5「治理面未合入前本仓不 archive」。
> **本仓已提交**: `d7a7b2d0`（A / B / C 本仓侧合并为一个原子提交 —— `test_stage_consumers_agreement.py`
> 等文件被 C 与 B 连续改写，拆分会产出不可运行的中间态 commit）。

## 本仓侧完成情况（已 commit + 全量门绿）

| AC | 状态 | 证据 |
|---|---|---|
| AC-1 归档 | pass | `skills/guide` 不存在；`docs/legacy/skills/guide/SKILL.md` 存在；`docs/legacy/README.md` 含「考古保留」 |
| AC-2 契约面 | pass | `package.json::skills[]` 28 项无 `guide`；`pyrightconfig.json` 无 `skills/guide` |
| AC-3 跨仓证据 | **blocked** | `.rddf/state/.cross-repo-evidence.json` `status=unverified`（见下） |
| AC-4 `rddf guide` 可用 | pass | `recommender.scan_state('.')` ⇒ `('rdd-builder', '变更生成已完成 → 进入变更执行', 'high')` |
| AC-5 stage_guide 代码路径退役 | pass | 命中项全为 **legacy 枚举保留**（`_types.py:32/41/55`、`sessions_schema.json:14/47/48/69`）+ 1 处 docstring —— 与 `iteration_schema.json` / `verifier_loop_schema.json` 的既有政策一致 |
| AC-6 events 总线未退化 | pass | `phase_started` / `rddf monitor` / `child_progress` 均保留（ADR-0063 Decision 7） |
| AC-7 测试无新增失败 | pass | `pytest unit` 3433 passed / `integration` 196 passed / bats 回归门 0 新增失败 |
| AC-8 架构快照归档 | pass | `docs/architecture/README.md` 无 guide-orchestrator-flow；文件在 `docs/legacy/` |
| AC-9 ADR 状态标注 | pass | ADR-0055 / ADR-0056 含 `Superseded by ADR-0063`；ADR-0051 References 含 `ADR-0063` |
| AC-10 跨仓 D7 | **blocked** | 见下 |
| AC-11 全量门 | pass | `./test.sh --full --regression` ⇒ rc=0 / `✅ ALL PASSED` |

## 待办的 2 项跨仓治理面改动

两者均在 `~/.config/opencode` 仓 —— 属**治理面**（`~/.config/opencode/**`），按角色矩阵由 **architect** 角色持有写集
（`§审查配对 治理面归属行`），builder 无权写。

### T7.1 `~/.config/opencode/scripts/rdd-skills.sh` — 内置清单移除 `guide`

- **位置**: 第 38 行起的 `RDD_SKILLS_BUILTIN=(...)` 数组，第 **45** 行 `  guide`
- **改动**: 删除该行（数组其余成员不动）
- **影响**: 该数组仅在「一个安装都没找到」时作为最后兜底（脚本 L105 注释）。删除后
  `available[]` 不再含 `guide`
- **判据**: `~/.config/opencode/scripts/rdd-skills.sh --json` 的 `available[]` 不含 `guide`
- **审查要求**: 该文件是「被治理面规则行为依赖的脚本」（§治理面作用域表末行）⇒ 改其**落盘行为 / 报错文案 / 退出码**时
  按治理面审；本改动只删数组成员 ⇒ 属**表格行变更**（触发条件：增删/修改表格行）⇒ **oracle → critic 必审**

### T7.2 `~/.config/opencode/.rddf/state/adr-front-agent-redesign.md` — D7 段修订

- **位置**: D7 段（`### D7 \`guide\` 的归宿：只并入交互，不并入执行`），末句 **「`guide` skill 不删。」**
- **改动建议**: 改为
  > `guide` skill 已归档（ADR-0063，2026-11-19）；其交互职责由 front 承担，推荐能力由 `rddf guide` CLI 承担。
- **保留**: D7 前半段的决策（front 吸收交互部分 / 不吸收执行部分）与「新鲜度标注（强制）」段**不动**
- **判据**: 该文本不再含「`guide` skill 不删」的未修订表述，且保留「front 吸收交互部分」的决策
- **审查要求**: 改 ADR 正文（治理面文档）⇒ 按 §治理面作用域表走 **oracle → critic**；
  若判定为「纯措辞修订」可走 ADR 行的只 oracle 豁免，但**不得**单方面改决策内容

## 两侧的顺序约束

ADR-0063 Decision 5 规定「**治理面先行、本仓 archive 后置**」：

```
[跨仓] T7.1 + T7.2 落地（architect 角色 + oracle→critic）
        ↓
[本仓] 复跑证据探针 → .cross-repo-evidence.json 的 status 变 verified
        ↓
[本仓] verifier 验收 C（AC-3 / AC-10 转为 pass）
        ↓
[本仓] openspec archive retire-guide-orchestrator
```

## 本仓侧的复跑命令

```bash
# 证据探针（两项都应为 0）
grep -c '\bguide\b' ~/.config/opencode/scripts/rdd-skills.sh || true
grep -c 'guide. skill 不删' ~/.config/opencode/.rddf/state/adr-front-agent-redesign.md || true
```

探针归零后，按 `.rddf/state/.cross-repo-evidence.json` 的 schema 重建工件（`status` 字段随之改为 `verified`），
再切 verifier 跑 C 的 AC-3 / AC-10，最后 `openspec archive retire-guide-orchestrator --yes`。

## 一并可做的 architect 侧收口（不阻塞，但同属 architect 写集）

两条 ADR 的元数据仍是占位符，需在 architect 侧回填（§architect 产出形态契约 的「ADR 完成的标志」第 4 条）：

| 文件 | 当前 | 应改为 |
|---|---|---|
| `docs/adr/ADR-0062-recommender-single-implementation.md` L7-8 | `backlog: consolidate-recommender-implementation`（待 planner 立项） | `openspec/changes/archive/2026-11-19-consolidate-recommender-implementation/` + AC 映射（proposal AC-1 ~ AC-9） |
| `docs/adr/ADR-0063-retire-guide-orchestrator.md` L7-8 | `backlog: retire-guide-orchestrator`（待 planner 立项） | `openspec/changes/retire-guide-orchestrator/`（C 尚未归档）+ AC 映射（proposal AC-1 ~ AC-12） |

> 回填属「关联 change 落库」动作，**不改 ADR 的决策内容** ⇒ 按 §审查配对 的 ADR 行可走只 oracle 豁免
> （或只改指针不动任何表格行 / 决策条目）。
