# fix-rddf-status-corrupt-message

**优先级**: P1 | **来源**: session 2026-08-05 `rddf status` — `.rddf/state/iteration.json` 存在且为合法 JSON, 但 schema 校验失败, CLI 误报 "📭 iteration.json not found" 并建议 `skill_use("propose", ...)` (该建议无法修复 corruption)
**阶段**: default | **分类**: infra-setup
**类型**: bug

## 架构依据

- **ADR-0017** (已采纳): rddf-session / iteration.json 是工作流核心状态文件; 状态文件的诊断准确性直接影响用户恢复决策
- **ADR-0018** (已采纳): arch-quality-gate 强调 "正确性优先于覆盖率" — 错误消息 (missing 误报 corrupt) 比漏报更具误导性
- **`iteration.store` 已有 corrupt 处理先例**: `skills/_lib/iteration/store.py::_backup_corrupt_file()` 在 `load()` 路径上对 schema-invalid 文件写 `.corrupt.<ts>` 备份并降级为空 state。本改进的目标是把同一诊断能力暴露到 **read 路径** (`_read_unlocked`), 目前该路径静默吞掉 `ValidationError`
- **`state_reader.py` 模块 docstring (L1-21) 明确承认该设计**: "All return `None` for missing or corrupt files and never raise" — 契约本身正确 (read-only, 不写备份), 问题出在 CLI 层把两种失败折叠成同一条 "not found" 消息

## 根因

三层折叠导致诊断信息丢失:

1. `skills/_lib/iteration/store.py:77-93` `_read_unlocked()` 对 **三种失败** (文件缺失 / `JSONDecodeError` / `jsonschema.ValidationError`) 统一返回 `None`, ValidationError 被裸 `except` 吞掉:

   ```python
   try:
       _validate(data)
   except jsonschema.ValidationError:
       return None  # ← 诊断信息在此丢失
   ```

2. `skills/_lib/state_reader.py:115-129` `read_iteration()` 有意调用 `_read_unlocked` (而非 `load`) 以保持 read-only — 这层无需改动语义, 只缺一个"带回错误"的兄弟函数

3. `skills/_lib/cli/status_cmd.py` 两个消费点把 `None` 一律渲染为 "not found":
   - `_mode_b` (L171-174): `📭 iteration.json not found` + `initialize via: skill_use("propose", "<change-name>")`
   - `_mode_a` (L303-306): 同上

   `skills/feature/scripts/feature_cli.py:31` 有同款问题: `❌ iteration.json not found (run guide-plan first)`

**误导性提示的严重性**: `skill_use("propose", ...)` 走 `iteration.store.load()`/`save()` 路径, 对 schema-invalid 文件会写 `.corrupt.<ts>` 备份并重建空 state — 用户 68 条 change 的迭代数据被静默清空。错误提示把用户推向**数据丢失式"修复"**。

### 本仓库实际复现 (2026-08-05 已验证)

`iter_data['changes'][68]` (change `fix-rddf-init-broken-layout`) 携带 per-change 级 `updated_at` 字段, 被 per-change item schema 的 `additionalProperties: false` 拒绝:

```
$ rddf status
📭 iteration.json not found
   initialize via: skill_use("propose", "<change-name>")

$ python3 -c "from skills._lib.state_reader import read_iteration; print(read_iteration('.'))"
None

$ python3 - <<'EOF'
import json, jsonschema
from skills._lib.iteration.schema import _load_schema, _load_registry
data = json.load(open('.rddf/state/iteration.json'))
v = jsonschema.Draft7Validator(_load_schema(), registry=_load_registry())
for e in list(v.iter_errors(data))[:1]:
    print('path:', list(e.absolute_path)); print('msg:', e.message)
EOF
path: ['changes', 68]
msg: Additional properties are not allowed ('updated_at' was unexpected)
```

注: 顶层 schema (`skills/_lib/schemas/iteration_schema.json`) 在 properties 中列出 `updated_at` 故顶层允许; per-change item schema 的 `additionalProperties: false` 未列出该字段。**修复 schema (允许 per-change `updated_at`) 不在本改进 scope** — 本改进修的是诊断消息; schema 漂移是否合法需单独提案决策。

## 方案选型 (三选一并记录决策)

| 方案 | 描述 | 评估 |
|------|------|------|
| (a) 改 `read_iteration` 返回 tri-state (`MISSING`/`CORRUPT` 枚举或异常) | 修改现有函数返回契约 | ❌ 拒绝 — `read_iteration` 调用方众多 (guide / feature / guide-arch·plan·ship intake), 改契约需要全量审计; 违反最小爆炸半径原则 |
| (b) **新增** `read_iteration_or_corrupt(project_root) -> tuple[Optional[dict], Optional[str]]` | 加性 API, 返回 `(data, error_message)`; `error_message is None` 表示成功或文件缺失 (靠 `os.path.isfile` 区分) | ✅ **采纳** — 旧函数不动, 旧调用方零影响; read-only 契约保留 |
| (c) `_read_unlocked` 内部打 stderr/structured warning | 日志式旁路 | ❌ 拒绝 — 与 `state_reader` "never raise, silent None" 契约冲突; 且 warning 无法被 CLI 结构化渲染成用户可操作的修复指引 |

决策: **(b) 加性 helper**。配合 `store.py` 新增一个 verbose 读取函数, 两个 CLI 消费点切换到新 helper。

## 范围

**In Scope**:

1. `skills/_lib/iteration/store.py` — 新增 `_read_unlocked_verbose(path) -> tuple[Optional[dict], Optional[str]]`:
   - 文件缺失 → `(None, None)`
   - `JSONDecodeError`/`OSError` → `(None, f"invalid JSON: {e}")`
   - `ValidationError` → `(None, f"schema validation failed at {list(e.absolute_path)}: {e.message}")`
   - 成功 → `(data, None)`
   - `_read_unlocked` 改为委托 `_read_unlocked_verbose` 并丢弃 error (一行改动, 零行为变化)

2. `skills/_lib/state_reader.py` — 新增 `read_iteration_or_corrupt(project_root)` (薄封装, 走 `_read_unlocked_verbose`); `read_iteration` 保持原样; 模块 docstring "Return contract" 段增补一行

3. `skills/_lib/cli/status_cmd.py`:
   - `_mode_a` (L303-306) 和 `_mode_b` (L171-174) 切换到 `read_iteration_or_corrupt`
   - 文件缺失 (`error is None` 且文件不存在) → 保留现有 "not found" 消息, 并附加文件路径 `.rddf/state/iteration.json`
   - 文件存在但损坏 → 新消息 (见"关键场景"), **不显示** `skill_use("propose", ...)` 提示
   - 返回码: corrupt 时 `_mode_a` 返回 1 (与 `_mode_b` 现状对齐; 当前 corrupt 走 "not found" 分支 `_mode_a` 返回 0 是隐藏 bug — CLI 静默成功)

4. `skills/feature/scripts/feature_cli.py:31` — 同款区分, 保持消息风格 (`❌`) 一致

5. 测试:
   - `tests/unit/test_state_reader_corrupt.py`: 4 case (missing / invalid JSON / schema-invalid / valid) — tmpdir 构造 iteration.json
   - `tests/unit/test_iteration_store_verbose.py`: 3 case 锁定 `_read_unlocked_verbose` 返回形状
   - `tests/integration/test_status_corrupt_message.bats`: 端到端 `rddf status` 在 corrupt iteration.json 下的输出断言 (含 "不得出现 propose 提示" 反向断言)

**Out Scope**:

- 不修改 `iteration_schema.json` (per-change `updated_at` 是否合法是独立决策, 需单独提案)
- 不修改 `read_iteration` 返回契约 / 其他 7 个 state_reader 函数
- 不让 read 路径写 `.corrupt.<ts>` 备份 (read-only 契约, `state_reader.py` L14-19 明确禁止)
- 不扫描/修复其他 state 文件 (sessions.json / handoffs) 的同款问题 — 若后续发现, 照本模式另起提案
- 不改动 `iteration.store.load()` 的既有 corrupt 备份行为

## 关键场景

**场景 1** (文件缺失 — 回归保持):
- GIVEN `.rddf/state/iteration.json` 不存在
- WHEN 运行 `rddf status`
- THEN 输出 `📭 iteration.json not found (expected at .rddf/state/iteration.json)` + 现有 `initialize via: skill_use("propose", ...)` 提示 (缺失时该提示是正确的)

**场景 2** (schema-invalid — 新行为):
- GIVEN iteration.json 存在, 合法 JSON, 但 `changes[68]` 有多余 `updated_at` 字段
- WHEN 运行 `rddf status` 或 `rddf status <name>`
- THEN 输出:
  ```
  ❌ iteration.json fails schema validation
     path: .rddf/state/iteration.json
     error: ['changes', 68]: Additional properties are not allowed ('updated_at' was unexpected)
     fix: restore from a iteration.json.corrupt.<ts> backup in .rddf/state/, or edit the file manually
  ```
- AND 输出中**不含** `skill_use("propose"`
- AND 退出码为 1 (两种 mode)

**场景 3** (invalid JSON — 新行为):
- GIVEN iteration.json 存在但含语法错误 (如尾逗号)
- WHEN 运行 `rddf status`
- THEN 输出 `❌ iteration.json is not valid JSON: <error>` + 同样的 fix 指引, 无 propose 提示

**场景 4** (feature CLI 一致性):
- GIVEN 同场景 2 的 corrupt 文件
- WHEN 运行 `rddf feature summary` (或任意 `feature` 子命令)
- THEN 显示同款 corrupt 诊断, 而非 "not found (run guide-plan first)"

**场景 5** (向后兼容):
- GIVEN 现有 `read_iteration` 的全部调用方 (guide recommender / intake phases / 其他 CLI)
- WHEN 本改进落地
- THEN 这些调用方零修改, 行为与修复前**完全一致** (corrupt 仍返回 `None` — 它们渲染什么消息不在本 scope)

## 技术约束

**MUST**:
- `_read_unlocked` 委托 `_read_unlocked_verbose` 后保持**字节级行为兼容** (现有 unit tests `test_iteration*.py` 零修改 PASS)
- 新 helper 全程 read-only: 不写文件、不调 `_backup_corrupt_file`、不获取文件锁
- corrupt 分支的 CLI 输出**不得包含** `skill_use("propose"` 子串 (bats 反向断言锁死)
- corrupt 时 `_mode_a`/`_mode_b` 退出码均为 1
- error message 中必须含 `list(e.absolute_path)` 渲染的 JSON path (用户能直接定位到 `changes[68]`)
- 测试用 `tmp_path`/`BATS_TMPDIR` 构造 fixture, 不依赖仓库当前真实 corrupt 状态 (该状态会被人工修复, 测试必须自给自足)

**MUST NOT**:
- 不得修改 `read_iteration` 的返回类型或抛异常
- 不得在 `store.py` 新增模块级状态 (沿用现有纯函数风格)
- 不得引入新第三方依赖 (`jsonschema` 已在依赖中)
- 不得改动 `WT_ISSUES_JSON` / `iteration.json` 的 schema 版本字段
- 不得顺手"修复"当前仓库的 corrupt iteration.json — 留给用户按新消息指引操作, 也是验收的活样本

**SHOULD**:
- `_mode_b` 与 `_mode_a` 复用同一个 `_render_iteration_read_error(data, error, path)` 内部函数, 避免两处消息文案漂移
- `feature_cli.py` 与 `status_cmd.py` 消息文案保持同一句式 (仅 emoji 前缀差异)
- 在 `state_reader.py` docstring 增补一行: "需要区分 missing/corrupt 的调用方使用 `read_iteration_or_corrupt`"

## 验收标准

1. **新 unit tests 全 PASS**: `tests/unit/test_state_reader_corrupt.py` (4 case) + `tests/unit/test_iteration_store_verbose.py` (3 case), 其中 schema-invalid case 的 fixture 精确复刻本仓库场景 (per-change entry 携带 `updated_at`), 断言返回的 error message 含 `"changes', 68"` 或等价 path 渲染
2. **bats 端到端 PASS**: `tests/integration/test_status_corrupt_message.bats`:
   - corrupt fixture 下 `rddf status` 输出含 `fails schema validation` 且**不含** `propose`
   - corrupt fixture 下退出码 = 1
   - missing fixture 下输出含 `not found` 且含 `propose` (回归锁)
3. **现有测试零修改 PASS**: `python3 -m pytest tests/unit/ -q` + `tests/integration/` 全绿; `npm test` (bats) 全绿
4. **read-only 契约验证**: 测试中 assert 调用 `read_iteration_or_corrupt` 后 `.rddf/state/` 目录无新增文件 (无 `.corrupt.<ts>` 生成)
5. **向后兼容**: `grep -rn "read_iteration(" skills/ tests/` 全部既有调用点零修改; `_read_unlocked` 的既有调用方 (`save()` 等) 行为不变
6. **活样本人工验证**: 在当前仓库 (iteration.json 仍 corrupt) 直接运行 `rddf status`, 输出为场景 2 的新消息; 手工修复/移除文件后再次运行, 输出回退到场景 1
7. **行数约束**: 实现 ≤60 行新增 + ≤15 行改动 (不含测试)

## 关联

- 与 `iteration.store._backup_corrupt_file()` (load 路径) 互补: 本改进把同一诊断暴露到 read 路径, 两者共享 "schema-invalid ≠ missing" 的语义模型
- ADR-0017 §3 (rddf-session 绑定): iteration.json 是 session 恢复的关键输入, 错误的 "not found" 会误导用户放弃恢复而去 re-propose
- 后续可考虑: 若 sessions.json / handoff JSON 出现同款误报, 按本模式为对应 reader 加 `_or_corrupt` 变体 (独立提案)
- 独立的后续决策: per-change `updated_at` 是否应加入 `iteration_schema.json` item properties (若合法, 本仓库当前的 corrupt 文件即自愈; 若非法, 需查是哪个 writer 写入的 — 疑似 iteration sync hook)