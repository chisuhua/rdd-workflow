---
优先级: P2
来源: 实施「本地门镜像 CI」时实测（2026-11-19 ruff 0.17.5 vs 0.15.22）
阶段: v4
分类: core-impl
类型: debt
主题: 静态检查口径
---

## 架构依据

- 本仓的 lint 门口径写在 `pyproject.toml` 的 `[tool.ruff.lint]`（2026-11-19 起显式 `select = ["E4","E7","E9","F"]`）。
- ruff 0.16+ 把 I/S/UP 加进了**默认**规则集 ⇒ `requirements.txt` 里的 `ruff>=0.1` 让 CI 每次装到新默认，
  于 2026-08-17 起 `ruff check skills/_lib/` 报 36 个 error（CI 的 Ruff step 一直红）。
  口径显式化（`select`）之后这 37 个发现在**当前口径下不参与判定**，但它们是真实存在的代码问题，
  记在本仓的机读债务位（`.rddf/improvements/`）而不是烂在某个 PR 评论里。
- 分层事实（实测）：`skills/_lib/**` 绝大多数是 **identity-merge shim**（`sys.path.insert(...)` →
  `import _lib.x as _real` → `sys.modules[__name__] = _real`）；`skills/_lib/core/*.py` 三个文件全是
  0-def shim（真实实现是 `_lib/core/*.py`）⇒ **I001 在 shim 上自动重排 import 有破坏 shim 语义的风险**
  （`sys.path` / `sys.modules` 必须先于 import 生效）。

## 范围

### In Scope

1. **I001（25 处）** —— import 排序。**不自动修**：identity-merge 的语句顺序是契约的一部分
   （`sys.path.insert` / `sys.modules[...]` 必须先于 import）。若要修，必须逐文件人工确认顺序，
   改完跑全量门（`tests/unit/test_p1_1_identity_merge.py` 是它的护栏）。
2. **S102（8 处）** —— `exec(compile(...))`。**这是 shim 机制本身**（把真身模块加载成 `__main__` 之外的
   名字）。两个选项：(a) 每处 `# noqa: S102` + 一行理由注释；(b) 抽一个共用 helper
   （如 `_exec_real_module()`）消掉 7 处重复。
3. **S603（1 处）** —— `subprocess` 调用未显式声明 `shell=False`（默认即是 False，属提示性规则）。
4. **UP035 / UP006（2 处，`skills/_lib/gh_repo_detect.py`）** —— `typing.Tuple` → `tuple`。
5. **UP007（1 处，`skills/_lib/iteration/__init__.py`）** —— `Union[str, Path]` → `str | Path`。
   ⚠ 该文件没有 `from __future__ import annotations`，模块级赋值 `PathLike = ...` 在 import 时求值
   ⇒ 需要 Python ≥ 3.10（本仓 target py311 ✓，但若要支持更老的运行时要改成字符串注解）。

### Out of Scope

- **不改 `[tool.ruff.lint] select`** —— 口径是「显式化的窄集」，收窄/放宽是另一件事、另一个提案。
- **不扩大 lint 覆盖面** —— `ruff check skills/_lib/` 只查 shim 层，真实实现层 `_lib/` 目前**不在任何 lint 门内**
  （`pyrightconfig.json` 的 `include` 含 `_lib`，但 pyright 不在 CI 里跑 ⇒ 另一处死配置）。
  同理 `mypy --strict skills/_lib/core/` 只看到 0-def shim ⇒ **mypy 门目前近乎空转**。
  这两条覆盖漏洞单独立项，不在本提案偷偷扩大 CI 范围。
- **不改 `pyproject.toml` 里 `[[tool.mypy.overrides]] module = "_lib.core.*"`** —— 该 override 指向的是
  真实实现 `_lib/core/*`，而 CI 的 mypy 命令查的是 `skills/_lib/core/` ⇒ override 与被查路径对不上；
  是死配置还是有意为之需要单独判断（连带 `pyrightconfig.json` 里 `skills/guide-arch` / `skills/guide-plan`
  两个已随 v4 改名、不存在的目录）。

## 关键场景

- **GIVEN** `ruff check skills/_lib/ --select I,S,UP` 报 37 个发现，**WHEN** 有人用 `ruff --fix` 批量修，
  **THEN** identity-merge shim 的 import 顺序可能被改坏 ⇒ `skills._lib.X` 与 `_lib.X` 不再是同一个对象
  ⇒ `tests/unit/test_p1_1_identity_merge.py` 必须变红（这是本提案要求**逐文件人工确认**的原因）。

## 技术约束

- MUST NOT 用 `ruff --fix` 批量处理 shim 层的 I001；MUST 逐文件确认 import 顺序。
- MUST 修完之后跑全量门（`./test.sh --full --regression`），不能只看 ruff 变绿。
- MAY 为 S102 采用 per-file-ignores 或共用 helper，二选一，但必须**写明理由**（不得静默关闭规则）。
- MUST NOT 通过放宽 `select` 来「清掉」这批发现（那是把债藏起来，不是还债）。

## 验收标准

1. **可复现的清单**：记录 37 个发现的逐规则计数（I001 25 / S102 8 / S603 1 / UP035 1 / UP006 1 / UP007 1）
   与文件清单；`ruff check skills/_lib/ --select I,S,UP --output-format concise` 可复现。
2. **处置完备**：37 个发现每个都有明确处置（修 / 逐条 `# noqa` + 理由 / 记为正当豁免），
   不允许「沉默消失」。
3. **回归**：处置完成后 `ruff check skills/_lib/`（当前口径）仍绿，且
   `./test.sh --full --regression` ⇒ 未评估 0 / 新增失败 0 / ALL PASSED。
4. **口径不变**：`pyproject.toml` 的 `select` 不因本提案而变宽或变窄。
