# 验收报告 — remove-dead-dup-layer

- **日期**：2026-11-04
- **验收角色**：`verifier`（source: user）
- **被验对象**：`openspec/changes/remove-dead-dup-layer`（in-place 实施，未 commit）
- **已用轮次**：1 / 3

## 判据来源

1. 用户本次验收条件：无单独声明
2. `proposal.md` 的 `## 验收标准`（**18 条 AC**，其中 AC-17 / AC-18 为实施中基于实证新增）
3. `tasks.md`：10 Task / **32 个 Step 全部勾选**

## 分流判定

| 条件 | 结果 |
|---|---|
| change 有 `## 验收标准` 段 | ✅ |
| P3 archive gate（`discover_eligible()` 口径） | ❌ 未登记 `iteration.json`；`rddf rdd-verify --dry-run` = 空队列 |
| `rdd-verifier` 可加载 | ✅ |

→ **本地验收 1–5 步**；额外门由 `tasks.md` 取证（未勾选 Step = 0）。

## 逐条判定

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 `skills/_lib/iteration/` 只剩 `__init__.py` | ✅ | `ls` → `__init__.py` + `__pycache__` |
| AC-2 `skills/_lib/schemas/` 不存在；canonical 34 个 | ✅ | 目录 No such file；`ls _lib/schemas/*.json \| wc -l` = 34 |
| AC-3 3 个活契约内容与原副本逐字节相同 | ✅（附注） | `populate_state` / `populate_supplementary`：`cmp` 逐字节一致；`rfc_draft` 唯一差异是 **`$id` 同步到 canonical 路径**（`diff` 只有 1 行），搬移本身一致 |
| AC-4 README ↔ 磁盘双向一致 | ✅ | 脚本比对 `refs == disk` → True（34 个）；`doctor --category docs-consistency` → All OK |
| AC-5 populate schema 路径存在于磁盘 | ✅ | `test_populate_schema_path.py::test_state_schema_path_resolves_to_real_file` pass；`parents[2]`→`parents[1]` 共 3 处 |
| AC-6 校验路径**实际执行** | ✅ | 同文件 `test_jsonschema_branch_actually_runs`：构造「过手工兜底、违 jsonschema」的 payload → 返回错误串（证明走 jsonschema 分支）。另：读路径本就「记录不抛错」（返回错误串 + stderr + 回退全量模式），唯一会 raise 的写路径 `save_populate_state` **无生产调用方** → 零行为风险 |
| AC-7 3 个失效代理已删；`rdd_arch` 保留可 import | ✅ | 3 个文件均不存在；`import skills.rdd_arch` → `__path__` = `skills/rdd-arch` |
| AC-8 dash 注册无旧名 | ✅ | `_lib/cli/__init__.py` 与 `tests/conftest.py` 的 `_DASH_SKILLS` 均无 `guide-*` / `ac-verifier`；剩余 3 条目标目录均存在 |
| AC-9 `skills._lib.iteration.store` 解析到 canonical | ✅ | `→ <repo>/_lib/iteration/store.py`；`proposal_source_fields` True；公共 API（load/save/create_empty/add_or_update_change）可用 |
| AC-10 schema 版本测试扫 canonical、动态发现、无硬编码数量 | ✅ | `test_schema_version_field.py` 改指 `_lib/schemas`，`assert len(SCHEMAS) == 20` 已删；47 项相关测试 pass |
| AC-11 `verifier_audit_schema.json` 可 `json.load` | ✅ | 首行 Python docstring 已改为 JSON `description`；34 个 schema 全部可解析 |
| AC-12 新守卫通过（6 项） | ✅ | `test_no_stale_dup_layer.py` **11 passed**（含 shim 层无 JSON / 超 50 行须命中豁免且豁免清单规模 ≤ 3 / 无旧路径引用 / 无失效代理 / `skills._lib.schemas` 隔离后不可 import / canonical 全部可解析） |
| AC-13 pytest unit 无新增失败 | ✅ | 全量 `3267 passed, 2 skipped`（基线 `3206 passed + 1 failed`；+61 新测试全 pass，基线那 1 个失败已修） |
| AC-14 回归新增失败 0 + smoke 全绿 | ✅ | `已知失败: 11 / 新增失败: 0 / 已修复 (zombie): 0`；`bats tests/smoke.bats` 9/9 ok |
| AC-15 `openspec validate` | ✅ | `Change 'remove-dead-dup-layer' is valid` |
| AC-16 `doctor --category roadmap-feature` | ✅ | `✅ All 1 categories OK` |
| AC-17 canonical 是副本的超集 | ⚠️ **部分（2 处已判定无影响）** | 逐键比对 20 个 schema：契约字段缺失仅 2 处 —— `arch_handoff_schema.json::discovered.roadmap_path`（canonical 的 `discovered` 是 `additionalProperties: true` → **不校验该字段**）与 `skill_role_schema.json::$comment`（纯注解）。两者均已登记 Known Residual |
| AC-18 顶层 `version` 记法归一 + 零重复键 | ✅ | 34 个 schema 全部 `{"const":"vN"}`（`v ∈ {v1,v2,v3}`）；`object_pairs_hook` 重复键扫描 → 无 |

**合计：17 ✅ / 1 ⚠️ / 0 ❌**

## 实施中修掉的 3 个真问题（AC 之外的发现）

1. **canonical `iteration_schema.json` 缺 `cross_repo_dependencies`** —— 该字段只有陈旧副本里有；canonical 是 `additionalProperties: false`，而运行时 `_lib/iteration/__init__.py:174`（v6→v7 迁移）每个 change 都写它 → **运行时写出的 iteration.json 校验必失败**。已把定义搬进 canonical，并由 `test_canonical_declares_fields_the_runtime_writes` 锁住。
2. **canonical `sessions_schema.json` 缺 `$defs.Session.properties.metrics`** —— 副本与 canonical **朝不同方向分叉**（副本有 metrics，canonical 有 `goal.last_seen_offset`），两侧都是活字段 → canonical 取**并集**。
3. **顶层 `version` 两种记法冲突** —— 5 个 schema 用遗留 int 记法 `1`，4 处既有测试硬断言该形式。统一为 `{"const":"vN"}`（`sessions` 用 `v3`），测试同步。

> **方法论教训（已写入 design.md Decision 5）**：`json.loads` 通过**不足以**证明 JSON 改对 —— 顶层已有 `version` 时再插同名 key 形成**重复键**（后写覆盖先写，解析器不报错但语义已丢）。必须用 `object_pairs_hook` 显式查重复键。

## 遗留清扫复核

| 项 | 结果 |
|---|---|
| TODO / FIXME / XXX / HACK / 临时标记 | 无（本 change 触及的文件） |
| 注释掉的代码 / 调试打印 / `breakpoint()` | 无 |
| 被 skip / xfail 的测试 | 无（4 个新测试文件共 20 个用例无 skip） |
| 未替换的 mock | 无（`monkeypatch` 均为 pytest 标准 fixture） |
| 临时 fallback | 无。`_SELF_REL_PATH` 之类豁免均为**显式登记**且有单测锁住 |
| `tasks.md` 未完成 Step | 0 |

## 观察项（不阻断，供后续决策）

1. **doctor 的 schema `version` 检查是 no-op（既有 bug，非本次引入）** —— `state_schema_check.py::_check_schema_version_metadata` 调 `resolve_real_lib_path("schemas")`，而该函数用 `is_file()` 判**目录** → 恒抛 `LibPathNotFoundError` → 检查整体提前返回。**这解释了为什么 24 个缺顶层 `version` 的 schema 从未被 doctor 报出来**。本 change 已手工补齐 34 个 schema 的 `version`，但**门禁本身仍不生效**。修它需要：`is_file()` → `is_dir()` + 为 4 个「payload 契约版本」schema 加显式豁免。建议独立立项。
2. `arch_handoff_schema.json::discovered.roadmap_path` 与 `skill_role_schema.json::$comment` —— 相对副本的 2 处差异，均无契约影响（前者靠 `additionalProperties: true`，后者是纯注解）。
3. **`skills/_lib/gh_repo_detect.py`（138 行完整实现住在 shim 层）** —— 守卫豁免清单已显式登记，理由写在清单里；迁移方案同 resolver（本次不做）。
4. **`iteration.json` 仍未登记这 3 个 change** → `rdd-verifier` 的 `discover_eligible()` 永远返回空，skill 无法接管验收。这是流程层缺口（治理规则明令禁止为凑前置条件而伪造 handoff），故本报告不做补登记。
5. **工作区仍混着另一条在途工作线**（`docs/adr/ADR-0060-*`、`skills/rdd-arch/scripts/adr_shape_check.sh` 等）。提交时必须选择性 stage。

## 结论

**PASS（实现层）**，附 AC-17 的 2 处已判定无影响的差异。

三个 change 全部实施完毕并各自通过验收：

| change | 验收 | 报告 |
|---|---|---|
| fix-test-isolation-and-hygiene | PASS（1 条 proposal_drift 已闭合：AC-1 文本收窄） | `.rddf/reviews/fix-test-isolation-and-hygiene-verify.md` |
| fix-v4-residue-contract | PASS（15 ✅ / 0 ⚠️） | `.rddf/reviews/fix-v4-residue-contract-verify.md` |
| remove-dead-dup-layer | PASS（17 ✅ / 1 ⚠️，无影响） | 本文件 |

最终回归门：`./test.sh --full --regression` → **ALL PASSED**（bats 新增失败 0 / unit 3267 passed / integration 201 passed）。
