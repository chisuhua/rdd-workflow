# 验收报告 — fix-v4-residue-contract

- **日期**：2026-11-04
- **验收角色**：`verifier`（source: user）
- **被验对象**：`openspec/changes/fix-v4-residue-contract`（in-place 实施，未 commit）
- **已用轮次**：1 / 3

## 判据来源

1. 用户本次验收条件：无单独声明
2. `proposal.md` 的 `## 验收标准`（**15 条 AC**）
3. `tasks.md`：6 Task / **44 个 Step 全部勾选**

## 分流判定

| 条件 | 结果 |
|---|---|
| change 有 `## 验收标准` 段 | ✅ |
| P3 archive gate（`discover_eligible()` 口径） | ❌ 该 change 未登记 `iteration.json`；`rddf rdd-verify --dry-run` = 空队列 |
| `rdd-verifier` 可加载 | ✅ |

→ **本地验收 1–5 步**。「额外门」由 `tasks.md` 取证（未勾选 Step = 0），`iteration.json` 缺条目记为观察项。

## 逐条判定

| AC | 判定 | 证据 |
|---|---|---|
| AC-1 两种分类都写 `rdd-builder`，打印行标 P2/P1 | ✅ | `implementation_gap` → `→ Route: rdd-builder (P2 fix implementation, loop 1/3)`，state = `rdd-builder`；`proposal_drift` → `(P1 rewrite proposal)`，state = `rdd-builder`；输出无 `guide-` |
| AC-2 分类驱动失败路径 route == `rdd-builder` | ✅ | `pytest tests/unit/test_rdd_verify_cmd.py -k failed` → 3 passed（含 `assert result["route"] == "rdd-builder"`）。integrity 分支写 `archive-ready` 已按 AC 排除 |
| AC-3 两个 enum 同时含 v4 值与 legacy | ✅ | 两文件 `rdd-builder: True` / `guide-ship: True`；`json.loads` 均合法 |
| AC-4 `feedback show-schema` ⊇ 8 值且与运行时一致 | ✅ | superset True；`enum == VALID_SOURCES` True |
| AC-5 arch-done 提示指 `rdd-arch` 不含 `guide-arch` | ✅（**验证方法修正**，见下） | `_DEFAULT_CHECKS['plan_done']` 的 `arch_handoff_exists.suggestion` = `请先运行 skill_use('rdd-arch') 完成架构定义` |
| AC-6 `rddf --help` 无旧名 | ✅ | `grep -c 'guide-'` → 0 |
| AC-7 `rddf sessions` 提示指 v4 | ✅ | `sessions_cmd.py` 三处均为 `("rdd-arch"|"rdd-planner"|"rdd-builder")`；`grep guide-` 无输出 |
| AC-8 路由 enum 缺 v4 值 → CRITICAL；含 legacy + v4 → 不报 | ✅ | `test_v4_residue_check.py` 10 passed（R1 两个方向各 1 例） |
| AC-9 不扫 `docs/**` `.rddf/**` `tests/**` `openspec/**` | ✅ | 实跑守卫，扫描面外命中 = `[]` |
| AC-10 代码目录旧路径 → WARNING（tmp 夹具） | ✅ | `test_docs_consistency.py -k 'scans_code or skips_itself or no_false_positive'` → 5 passed |
| AC-11 pytest unit 无新增失败 | ✅ | 全量跑：`pytest unit OK`（217 s）。基线唯一失败 `test_no_hardcoded_workspace_paths` 已修（我自己的验收报告写了 3 处绝对路径） |
| AC-12 `report_regression.sh` 新增失败 0 | ✅（**基线被外部破坏，已用 HEAD 基线重算**，见下） | 实施后实际失败集 = 10 条，**全部在 `git show HEAD:tests/KNOWN_FAILURES.txt` 的 11 条既有基线内** → 新增 0 |
| AC-13 `openspec validate` | ✅ | `Change 'fix-v4-residue-contract' is valid` |
| AC-14 `doctor --category v4-residue` 本仓 0 CRITICAL | ✅ | `✅ All 1 categories OK`（0 CRITICAL / 0 WARNING） |
| AC-15 `doctor --category roadmap-feature` 无 CRITICAL | ✅ | `✅ All 1 categories OK` |

**合计：15 ✅ / 0 ⚠️ / 0 ❌**

## 两处判据口径修正（必须记录）

### 1 · AC-5 的验证方法不可行

`proposal.md` 要求「用无 arch-handoff 的临时项目**触发错误路径**」。**该错误路径运行时不存在**：

```
grep GateMechanism 全仓（.py/.sh/.md）→  只命中 _lib/gate.py:399 的定义 + .rddf/plans/*.md 历史文档
```

`GateMechanism` **无任何生产代码实例化**，`_DEFAULT_CHECKS` 的 `arch_handoff_exists` 检查永不执行。
→ 改用**直接取 `Check.suggestion`** 取证（这是用户真正会看到的那句字符串）。
→ **`_lib/gate.py` 的 GateMechanism 是死代码**，登记为观察项（不在本 change 范围）。

### 2 · AC-12 的基线文件被外部进程破坏

| 时间 | `tests/KNOWN_FAILURES.txt` 状态 |
|---|---|
| 首轮回归结束（18:43） | 87 行 / **11 条**有效基线 |
| **19:03** | 被截断为 **32 字节**占位行 `known failure # existing reason` |
| 次轮回归（19:26） | 基线只剩 1 条占位 → 11 条既有失败全被算成「新增 10 条」 |

- **不是本 change 造成的**：本次会话从未写入该文件；`test.sh` / `collect_bats_failures.sh` / `report_regression.sh` 也无写它的代码路径。
- 同仓存在**另一条在途工作线**（`docs/adr/ADR-0060-*`、`skills/rdd-arch/scripts/adr_shape_check.sh` 等，自会话开始即存在），`tests/KNOWN_FAILURES.txt` 处于 ` M` 状态 → 高度疑似并发会话改写。
- **重算方法**：把次轮回归的 10 条实际失败逐条比对 `git show HEAD:tests/KNOWN_FAILURES.txt`，**10/10 命中既有基线** → 真实新增失败 = 0。首轮我引入的 5 条已逐个复验转绿。

## 遗留清扫复核

| 项 | 结果 |
|---|---|
| TODO / FIXME / XXX / HACK | 无（`review-debt` 分类未报本 change 触及的文件） |
| 注释掉的代码 / 调试打印 | 无 |
| 被 skip / xfail 的测试 | 无 |
| 未替换的 mock | 无（`monkeypatch` 全为 pytest 标准 fixture） |
| 临时 fallback | 无。`_R2_PATTERN` 的 4 个 idiom 均有单测覆盖 |
| `tasks.md` 未完成 Step | 0 |

## 观察项（不阻断）

1. **`_lib/gate.py::GateMechanism` 是死代码** —— `_DEFAULT_CHECKS` 全套检查无人调用。AC-5 的文案修改因此只是「修正一句看不着的字符串」。建议独立立项：要么接线，要么删。
2. **`iteration.json` 未登记本 change** → `rdd-verifier` 无法接管（同 Change C 的同一缺口，属流程层）。
3. **`tests/KNOWN_FAILURES.txt` 被并发截断** → 后续任何 `--regression` 跑都会误报。需先恢复（`git checkout -- tests/KNOWN_FAILURES.txt` 或 `refresh_known_failures.sh`），但该文件属另一工作线，**未擅自处置**。
4. **`_lib/cli/__init__.py::_DASH_SKILLS` 仍有 3 条死注册**（`guide-arch` / `guide-plan` / `guide-ship` 目录均不存在）——归 `remove-dead-dup-layer`。
5. `tests/integration/test_rdd_doctor_skills_md_sync.bats:62` 硬编码 `table_rows -eq 23`，本次因新增分类改为 24 —— 脆弱断言，建议改为「与 `_CHECKERS` 条数一致」。

## 守卫实效（本 change 最有价值的部分）

| 来源 | 找到的残留 |
|---|---|
| 设计阶段人工 grep `_lib/` | 10 处 |
| `v4-residue` R2（首跑） | **+2**（`execute_step7.py`、`feature_view.py`） |
| R2 扩 `run guide-` idiom 后 | **+4**（`state_schema_check.py` ×3、`tasks_checkbox_check.py`） |
| 实施中人工补 | **+1**（`feature_cli.py:31`） |
| 回归门抓到的人工清单遗漏 | **+5 处测试断言钉住旧值**（feature_skill ×2、verifier_loop ×1、self_contained ×2） |

→ **人工清单 10 处之外，共 12 处**。结论：靠人列清单必漏，守卫 + 回归门是必要组合。

## 结论

**PASS**。契约面已收敛到 v4 词汇并有守卫防复发；`doctor --category v4-residue` 对本仓 0/0。
可进入 Change B（`remove-dead-dup-layer`），但**需先处置 `KNOWN_FAILURES.txt` 否则回归门不可用**。
