# deferral 登记约定（另案立项）

> **单一真源**：措辞清单与两种豁免格式定义在 `_lib/deferral_registration.py`
> （`DEFERRAL_PHRASES` / `REGISTERED_FORM` / `BACKLOG_FORM`）。本文是它的**展开** ——
> 代码加词时本文没跟上，`tests/unit/test_deferral_registration.py` 会红。

## 为什么需要它

「本次不做 / 另案立项」是**合法**的收口方式。但没有登记载体时，被推迟的缺陷**没有欠账条目**：

- `fix-spec-v3-naming-sync.md:192` 记「第三次撞上同一堵墙…**另案立项**」—— 至今没有对应的
  improvement 文件 ⇒ 该缺陷在 2026-11-26 第 4 次复发；
- `fix-bats-per-file-timeout.md:411` 同样以「工具缺陷另案」收口 ⇒ 2026-11-26 第 2 次出现。

⇒ 「另案」没有登记载体 = 缺陷没有欠账条目 = 复发不可见、优先级不可排。

## 约定

任何 deferral 措辞处，**必须紧跟目标标识**：

| 形式 | 含义 |
|---|---|
| `另案（已登记：<improvement-slug>）` | 欠账已是一个 improvement（如 `fix-foo`） |
| `另案（backlog：<topic>）` | 欠账是一条 backlog 占位（还没有 slug） |

二者都没有 ⇒ **视为未登记**，由 `rddf doctor --category deferral-registration` 报出来
（WARNING，给出文件 + 行号）。

## 措辞清单（受管辖的 deferral 措辞）

- `另案`
- `另立`
- `另行立项`
- `后续另案`

> 与**提案推迟状态字段**（`已推迟` / `deferred`）**不共用措辞集** —— 那是「提案本身被推迟」，
> 本约定管的是「缺陷被欠着」。两套检测面互斥，不会重复报告。

## 存量噪音

存量文档里的历史无标识 deferral **一次性登记**在 `.rddf/deferral-exemptions.txt`
（可审计的账本，不是静默忽略）。清单条目**不再命中**时 doctor 会提示「可清理」——
清单不会静默腐坏。

## 谁来执行

- **作者**（planner / builder 收口时）：写「另案」就带上目标标识；
- **doctor**：`rddf doctor --category deferral-registration`（WARNING，不阻断）；
- **绝不自动代写**：doctor 只报警，不替作者创建 improvement 文件。
