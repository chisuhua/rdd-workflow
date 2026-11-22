# fix-rddf-status-icon-coverage 验收报告

**change**: `fix-rddf-status-icon-coverage`
**判据来源**: `openspec/changes/fix-rddf-status-icon-coverage/proposal.md` 的 `## Acceptance`（AC-1 ~ AC-8）
**已用轮次**: 2（critic 2 轮 + 本验收；**评审预算已满**，第 3 轮须用户明确批准）

## 逐条判定

| AC | 判定 | 证据 |
|---|---|---|
| **AC-1** 两个词汇域各自完整（①~⑦） | **PASS** | `pytest tests/unit/test_iteration_status_coverage.py -q` ⇒ **6 passed**（7 条判据分布在 6 个测试函数；⑥ 含「豁免仍然存在」的配套测试）。逐条：① `_VALID_STATUSES` == schema enum；②③ `renderer` 两表 ⊇ enum 且非空；④ `status_cmd._STATUS_ICON` key 集 **恰好 6 值**；⑤ 两域交集 emoji 相同；⑥ 全仓 archived 字面比较点**未对齐 = 0**（3 条显式豁免带理由） |
| **AC-2** `store.set_status(..., "archived_partial")` 不再抛错 | **PASS** | 实测：`set_status({"changes": []}, "chg-x", "archived_partial")` ⇒ 返回的 data 里 `status == "archived_partial"`，**无异常**（改前抛 `ValueError: invalid status 'archived_partial'; must be one of (...)`） |
| **AC-3** dashboard 把 `archived_partial` 归入 archived 区（**terminal + plain 两条路径**） | **PASS** | 实测：① `store.list_archived()` 对含 `archived`/`archived_partial`/`planned` 的 data 返回 `['a','b']`（partial 被收进 archived）；② `store.feature_progress()` 返回 `{'a': (1,1), 'b': (1,1), 'c': (0,1)}`（partial 计 done）；③ `renderer._STATUS_ICON["archived_partial"] == "📦"`、`_STATUS_ICON_PLAIN["archived_partial"] == "-"`（**不再 `?`**）；④ 两处分类点（`:455-456` emoji 路径 / `:806-807` plain 路径）均改为 `in ("archived","archived_partial")` ⇒ **两条渲染路径都覆盖** |
| **AC-4** 新守卫全绿 + 负向验证 | **PASS** | 6 passed。**负向验证 5 变体逐个注入并复测**：删 `_VALID_STATUSES` 的一个值 ✅抓到 / 给 `status_cmd._STATUS_ICON` 加死键 `proposed` ✅抓到（**这正是本批初版的错误做法**）/ 把 renderer 的 archived 过滤退回 `== "archived"` ✅抓到 / 删 renderer 图标表的 `archived_partial` ✅抓到 / 改坏跨表 emoji 一致性 ✅抓到。恢复正常后全绿 |
| **AC-5** `pytest tests/unit/` 全绿；`ruff check skills/_lib/` 全绿 | **PASS** | `pytest tests/unit/ -q` ⇒ **3529 passed, 3 skipped**（3523 + 6 守卫）；相关既有测试（`test_status_disk_derived` / `test_dashboard_renderer` / `test_iteration` / `test_workflow_synthesizer` / `test_roadmap_sprint`）⇒ **240 passed** 无回归；`ruff check skills/_lib/`（CI 范围）⇒ **All checks passed!**；我改的 11 个文件 ruff 错误数 **改前 3 → 改后 3**（全是既有问题：无新增） |
| **AC-6** `openspec validate --all` issue 数不变 | **PASS** | 本批**不改 spec** ⇒ `openspec validate --all` ERROR 仍为 **11** |
| **AC-7** 残留扫描器命中数不变 | **PASS** | `scan_specs(Path('.'))` ⇒ `未豁免 0/0/0`、`含已豁免 303/159/41`（本批不涉及 spec） |
| **AC-8** `./test.sh --full --regression` 全绿 | **见下** | 见「全量门」 |

## 全量门

`BATS_TIMEOUT=120 BATS_TIMEOUT_RETRY=240 ./test.sh --full --regression`

结果：见「全量门」段。

## 遗留清扫

| 项 | 结果 |
|---|---|
| 本次范围内的 TODO / 半截实现 | 无 |
| 注释掉的代码 | 无新增 |
| 临时调试日志 | 无（实施脚本在 `/tmp/opencode/`，不入仓） |
| 被 skip 的测试 | 无新增 skip |
| 未替换的 mock | 不涉及 |
| 临时 fallback 分支 | 无 |
| 刻意保留的 3 处 `== "archived"` | **不是遗留** —— 3 条各有理由，且写进守卫的**豁免清单**并有配套测试断言「豁免仍然存在」 |
| 未采纳的 finding | 无（2 轮共 3 BLOCKER + 5 SF + 3 NIT 全部采纳并实施） |

## 实施期教训

1. **「能渲染成 `?`」不等于「这个状态会走到渲染点」。** 我第一版断言「`rddf status` 把
   `proposed`/`review` 渲染成 `?`」—— 但 `rddf status` **不读 iteration.json**
   （`status_cmd.py:26-30` docstring）⇒ 那三个状态**永远到不了**渲染点 ⇒ 我的 AC
   **平凡满足**、实测路径**不可能通过**。⇒ 写 AC 前先问「这个状态真的会被产生并流到这里吗」。
2. **一个域不等于一张表，也不等于一个真源。** 我把 schema enum 当唯一真源、要求所有表 ⊇ enum
   —— 但 `status_cmd` 的表服务 **disk-derived 词汇**（含 enum 外的 `committed`）。
   ⇒ 「同一概念在几处出现」≠「它们该有同一个值域」。
3. **死键也是错。** 我原计划给 `status_cmd._STATUS_ICON` 补 3 个 enum 值 —— 那些键
   **永远不会被 `.get()` 命中** ⇒ 写进 spec 就是造死契约。⇒ 守卫判据 ④ 用「**恰好等于**」
   ⇒ 死键变成可机判的违规（负向验证已实测会抓）。
4. **同构代码要成对改。** `renderer.py` 的 emoji 路径与 plain 路径**逐行同构** ⇒ 只改一处
   ⇒ 另一处缺陷存活，且若 AC 只断言一处就会**平凡满足**。⇒ 守卫判据 ⑥ 用**全仓扫描**。
5. **豁免本身也要被守卫。** 3 处「不改」的理由写进守卫的豁免清单 + 配套测试断言其仍然存在
   ⇒ 豁免不会悄悄过期。

## 路由建议

无需返工。本批可归档。tail 的 `rddf archive` 确认门（行为变更，需用户拍板）与
`acceptance-N` 的 218 条（需方向决策）独立立项。
