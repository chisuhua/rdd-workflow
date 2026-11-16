# 架构审稿：rddf-layout-manifest（critic 第 1 轮）

> 审查者：critic（arch + build 双档）
> 对象：`openspec/rddf-layout-manifest` 的实施 diff（基线 `731f027` → `master`）
> 审稿上下文：`.rddf/reviews/rddf-layout-manifest-builder-review.md` 的 4 BLOCKER + 9 SHOULD_FIX 全部处置后的产物
> 日期：2026-11-16

## 结论

```
profile: arch (docs/adr/ADR-0026, docs/architecture/*) + build (_lib/**, skills/rdd-doctor/**, skills/rdd-builder/scripts/phase*.sh)
结论: APPROVE_WITH_CONDITIONS
mergeable: yes
scope_exceeded: false
BLOCKER: 0
SHOULD_FIX: 3
NITS: 3
```

**0 BLOCKER ⇒ 不触发复审**（按评审预算规则）。以下 3 条 SHOULD_FIX 逐条处置（均为实现层，在 builder 权限内直接修）。

## SHOULD_FIX 处置

### SF-1 `sys.path` 前缀插入把消费方项目根置于工具之前 ⇒ 清单可被 shadow

**critic 指出**：`_lib/cli/layout_cmd.py:28` 的 `sys.path.insert(0, str(project_root))` 把**消费方项目根**置于最前，随后 `from _lib.core.rddf_layout import as_dicts` 导入的可能是**消费方的代码** —— 若第三方项目恰有顶层 `_lib/` 包，清单出口会静默解析到错误模块，违背「payload 是产品声明的布局」这一契约。

**核实与复现**（两条路径都实测）：

| 消费方 `_lib/` 形态 | 实测结果 |
|---|---|
| 无 `__init__.py`（命名空间包） | regular package 优先 ⇒ 命中工具的 `_lib` ⇒ **未被劫持** |
| 有 `__init__.py`（regular package） | `python3 -m _lib.cli` 直接 **`No module named _lib.cli`** ⇒ 整个 CLI 起不来 |

⇒ finding 成立且**比 critic 描述的更严重**：根因是「消费方项目根被放到 `sys.path` 最前」，两种形态分别导致「静默劫持」与「CLI 整体不可用」。

**处置**：**删除 `sys.path.insert`**，`as_dicts` 改为模块级 import —— `skills._lib.cli` 的 identity-merge shim 已把 `_lib` 绑定到工具自身（实测：`from skills._lib.cli import resolve_project_root` 之后 `from _lib.core.rddf_layout import as_dicts` 直接命中工具代码，无需任何 path 注入）。同时清掉因此不再使用的 `os` / `sys` / `resolve_project_root` import。

**回归测试**：`tests/unit/test_layout_cmd.py::test_layout_payload_is_not_shadowed_by_a_consumer_lib` —— 造一个含 `_lib/core/rddf_layout.py`（返回 `HIJACKED`）的消费方目录并置于 `sys.path` 最前，断言 payload 仍是 14 条真实条目。

### SF-2 「永不 CRITICAL」可被聚合器击穿

**critic 指出**：`layout_check.py` 的**模块级** `from _lib.core.rddf_layout import ...` 在 import 失败时（正是 doctor_main.py docstring 描述的「tests 把 `rdd-doctor/` 拷到无 `_lib/` 的临时目录」场景）异常冒泡到 `aggregate_findings`，被转成 **CRITICAL finding** ⇒ acceptance-6「exit 1 不 exit 2」在边缘环境不成立。

**核实**：成立。`doctor_main.py:98-100` 的 `except Exception` 确实把 checker 异常转成 `Severity.CRITICAL`。

**处置**：把 manifest import **移入 `run()` 体内**并 try/except 降级为一条 **WARNING**（`category="layout.unavailable"`）。checker 的其余逻辑不变。

**回归测试**：`tests/unit/test_doctor_layout_checker.py::test_missing_manifest_degrades_to_warning` —— 用 `monkeypatch` 让 `_lib.core.rddf_layout` import 失败，断言返回的 finding **不是 CRITICAL** 且 category 为 `layout.unavailable`。

> 注：原计划的 bats 用例（拷贝 `rdd-doctor/` 到临时目录）在本机**无法复现** —— 全局安装的 `site-packages/rdd-workflow.pth`（`install.sh --global` 生成）把包根永久加进 `sys.path`，`_lib` 恒可达。故降级测试改为精确的单测 mock。

### SF-3 `docs/architecture/rddf-layout.md` 环境变量名写错

**critic 指出**：契约页写的是 `RDFF_STATE_DIR`，代码实况是 `RDDF_STATE_DIR`。

**核实**：**误报** —— 逐字核对 `docs/architecture/rddf-layout.md:87`，写的本来就是 `RDDF_STATE_DIR`（与 `_lib/session_stats.py:24`、`_lib/rfc_interview_state.py:17`、`_lib/subagent_strategy.py:104` 一致），spec delta 的 acceptance-17 也一致。critic 大概率读的是更早的版本。

**处置**：**无需修改**。已复核确认记录在此，避免下次审稿再被提出。

## NITS 处置

| # | critic 指出 | 处置 |
|---|---|---|
| N-1 | `severity` 字段在 JSON 契约里已冻结，但三个判据分支全部硬编码 severity，没有任何消费方读 `e.severity` ⇒ 空转 | **接线**：判据①（`required_when=always` 条目缺失）改用 `Severity[e.severity]`（该字段的语义就是「该条目缺失类判据的定档」）；判据②（未登记）与判据③（class 不符）用固定值（INFO / WARNING），因为它们不是「某个条目的缺失判据」 |
| N-2 | `covers()` 与 `_match_entry()` 是同一清单的两套匹配原语，且 `covers()` 在生产代码零调用方 | **删除 `covers()`** —— 它只服务断言 A（路径常量是否被清单覆盖），属测试实现细节，移入 `tests/unit/test_rddf_layout.py` 本地实现。生产代码只保留清单 + `as_dicts()`，消除「该用哪个」的歧义 |
| N-3 | 判据③对**不存在**的 `never` 条目也做 ignore 判定，通配 `.gitignore` 写法下会为尚不存在的目录报 class-mismatch | **文档写明**：`docs/architecture/rddf-layout.md` 的「读法上的三个约定」新增一条 —— 判据③判定的是 **ignore 规则本身**，与条目是否存在无关；通配 `.gitignore` 下会命中尚不存在的目录，属 advisory WARNING，不阻断 |

## 验证

```
python3 -m pytest tests/unit/test_rddf_layout.py tests/unit/test_layout_cmd.py \
                  tests/unit/test_doctor_layout_checker.py -q      # 19 passed
bats tests/integration/test_doctor_layout.bats                   # 11 passed
python3 -m pytest tests/unit/ -q                                  # 见 archive 前全量回归门
bash skills/rdd-doctor/scripts/doctor.sh --category layout        # 本仓 0 finding
```

## 未采纳的评审意见

无。3 条 SHOULD_FIX 全部采纳（其中 1 条经核实为误报，明确记录）；3 条 NITS 全部采纳。
