# add-env-cache-arch-discovery

**优先级**: P2 | **来源**: 第三方项目集成实务 — ADR 路径 / 命名差异处理
**阶段**: default | **分类**: general
**类型**: feature

## 架构依据

- **ADR-0016 Arch Discovery Contract** 已存在（`_lib/discover-arch-artifacts.sh`,三层 fallback: env var > handoff > 约定 default），自动扫描默认候选 + `SPEC_WORKFLOW_ADR_DIR`/`SPEC_WORKFLOW_ROADMAP_PATH`/`SPEC_WORKFLOW_ARCHITECTURE_DIR`/`SPEC_WORKFLOW_ADR_PATTERN` 四个环境变量强制覆盖。
- **当前 gap**（`skills/rdd-env-check/SKILL.md:40` 显式声明边界）：rdd-env-check **不缓存** ADR-0016 工件发现。10 字段 `.env-cache.json` 只记 `adr_count: int`，不记路径/glob。
- **下游消费者**（`_read_arch_handoff_paths()` in `_lib/gate.py:76-104`、`_lib/loop/detectors.py:181`）读 `.arch-handoff.json`，但 handoff 只在 `guide-arch` Phase 5 arch-done 落盘 → **arch-done 之前的全部 phase 都用硬编码默认**（`docs/adr` / `roadmap.md` / `docs/architecture` / `ADR-*.md`）。
- **症状**：第三方项目若 ADR 路径与默认不一致（如 `documentation/decisions/RFC-*.md`），phase 1-4（env-check / design / plan / ship）全部走错路径，每次 phase entry 都触发 `discover-arch-artifacts.sh` 重新扫一遍文件系统——直到 `guide-arch` Phase 5 落盘 handoff，下游才"看到"真实配置。**重复扫描 ~4 phase × N 启动**。
- **Oracle C1 security**: 已存在的 env-var 模式禁止 bash `$VAR` 字符串插值；本提案新增的 cache writer 必须沿用该模式。

## 范围

### In Scope

- **`.rddf/state/.env-cache.json` schema 增量扩展**：10 → 14 字段，追加 `discovered_adr_dir` / `discovered_roadmap_path` / `discovered_architecture_dir` / `discovered_adr_pattern` 4 字段（注：原 10 字段保留顺序与语义）。
- **`rdd-env-check` cache miss 路径**调用 `discover-arch-artifacts.sh::discover_all()`，把 4 个 `DISCOVERED_*` 全局变量写入 cache 已扩展的字段。
- **`_read_arch_handoff_paths()` 优先级改为三级 fallback**：
  1. `.env-cache.json` 中 `discovered_*` 字段（首次运行 / branch 切换后即写入）
  2. `.arch-handoff.json` 中 `adr_dir` / `roadmap_path` / `architecture_dir` / `adr_pattern`（arch-phase 落盘后）
  3. 硬编码默认（`docs/adr` / `roadmap.md` / `docs/architecture` / `ADR-*.md`）
- **branch 失效机制复用**：`.env-cache.json` 已有的 `branch` 字段比对 `git branch --show-current`，本提案无需新增失效逻辑。
- **`SKIP_AUTO_DISCOVERY=yes` opt-out 环境变量**：禁写 discovered 字段（向后兼容现有行为）。
- **consumer 同步改造**：`gate.py:_read_arch_handoff_paths` + `detectors.py:detect_adr_status` 已通过 `_read_arch_handoff_paths` 间接读取，零额外改动。

### Out Scope

- 不改 `.arch-handoff.json` schema（v1 const=1，ADR-0016 锁版本）。
- 不让 env-check 反向写 handoff（单一职责：env-check 管 cache，arch-phase 管 handoff）。
- 不修改 `_lib/discover-arch-artifacts.sh` 本身（脚本已含 4 个公开函数 `discover_adr_dir` / `discover_roadmap` / `discover_architecture_dir` / `discover_adr_pattern`，调用即可）。
- 不修改 Loop 引擎 / detectors / gate 的注册逻辑（只改单一读取函数即可传导）。
- 不引入新依赖（Pure bash + Python stdlib `json`）。

## 关键场景

### 场景 1：第三方项目 + 首次 env-check
- GIVEN 第三方项目 ADR 在 `documentation/decisions/`,roadmap 在 `planning/roadmap.md`,命名 `RFC-*.md`
- AND `.env-cache.json` 不存在（首次运行）
- AND 当前 branch = `main`
- WHEN `skill_use("rdd-env-check")` 触发 `_run_env_full_check`
- THEN `discover_arch_artifacts::discover_all` 扫到 `documentation/decisions` + `planning/roadmap.md` + `RFC-*.md`
- AND `.env-cache.json` 落盘 14 字段，其中 `discovered_adr_dir="documentation/decisions"`、`discovered_roadmap_path="planning/roadmap.md"`、`discovered_adr_pattern="RFC-*.md"`
- AND 后续同 session 的 `gate.py:_check_adr_exists` 通过 `_read_arch_handoff_paths()` 直接命中 cache 字段，**不再走硬编码默认**。

### 场景 2：env-check cache hit
- GIVEN `.env-cache.json` 已存在且在 TTL 内（3600s）且 `branch` 匹配
- WHEN 任意 phase 启动并调用 `_read_arch_handoff_paths`
- THEN 跳过 `discover-arch-artifacts.sh` 调用，直接从 cache 取 `discovered_*` 字段。

### 场景 3：branch 切换
- GIVEN `.env-cache.json` 存在，`cache.branch = "main"`
- AND 用户 `git checkout feature/add-foo`
- WHEN `rdd-env-check` 触发
- THEN `cache.branch != "feature/add-foo"` → cache 失效 → 重发现新 branch 的当前状态 → 重新落盘。

### 场景 4：opt-out（向后兼容）
- GIVEN `SKIP_AUTO_DISCOVERY=yes` 环境变量
- WHEN `rdd-env-check` 触发
- THEN `discover_all` 不被调用 → `discovered_*` 字段不写入 cache（或写空字符串）→ `_read_arch_handoff_paths` 跳过 cache，回退到下一级（handoff → 默认）。

### 场景 5：handoff 优先于默认（保持旧行为）
- GIVEN `.arch-handoff.json` 存在（`guide-arch` Phase 5 已落盘）
- AND `.env-cache.json` **不存在或尚未发现**（如用户跳过 env-check 直接进 arch-phase）
- WHEN 下游 phase 读 `_read_arch_handoff_paths`
- THEN 自动跳过 cache → 读 handoff → 命中。

### 场景 6：旧 cache 文件兼容
- GIVEN 升级前生成的 `.env-cache.json`（只有 10 字段，缺 `discovered_*`）
- WHEN 新版 `_read_arch_handoff_paths` 读 cache
- THEN `dict.get("discovered_adr_dir", default)` 拿不到时回退到下一级（handoff → 默认），**不抛异常**。

## 技术约束

- **MUST** env-check 的 Python cache writer 沿用 **env-var passing 模式**（`os.environ.get("DISCOVERED_ADR_DIR")`），禁止 bash `$VAR` 字符串插值 — Oracle C1。
- **MUST** `.env-cache.json` **追加** 4 个新字段，不删不改现有 10 字段顺序 — 避免破坏已发布格式消费者。
- **MUST** 原子写 cache（`.tmp` → `mv`，env-check 现有 `_atomic_write_cache` 模式）。
- **MUST NOT** 触发 env-check 失败 → 阻断 phase 进入（即使 `discover-arch-artifacts.sh` 报错，必须降级到默认约定并 emit warning，不抛非零 exit）。
- **MUST NOT** 在 env-check 路径中跑 `git`/`openspec` subprocess（保持纯 filesystem walk，< 200ms 预算）。
- **SHOULD** 加 1 个 bats 集成测试在 `tests/integration/test_env_check_arch_discovery.bats`：
  - Scenario 1 + 6 覆盖
  - SKIP_AUTO_DISCOVERY opt-out 覆盖
- **SHOULD** 加 1 个 Python unit test 在 `tests/unit/test_gate_arch_handoff_paths.py`（或既有 `test_gate.py`），锁定 `_read_arch_handoff_paths()` 三级 fallback 顺序。
- **SHOULD** `discover_adr_pattern` 已存在的小写探测（`adr-*.md`）行为保持，作为 fallback path 自动延伸。

## 验收标准

- [ ] `.env-cache.json` schema：**10 → 14 字段**（增量），现有消费者零修改。
- [ ] env-check cache miss 路径耗时：**< 200ms**（pure filesystem walk + 1-2 find 调用，no subprocess）。
- [ ] 新增测试通过：
  - [ ] `tests/integration/test_env_check_arch_discovery.bats`：5 个 @test 用例（scenario 1+2+3+4+6）。
  - [ ] `tests/unit/test_gate.py::test_read_arch_handoff_paths_priority`：3 个 case（env-cache 命中 / handoff 命中 / default 命中）。
- [ ] 现有测试零回归：`./test.sh --quick` 全绿（保留现有 60s pytest unit + 30s bats smoke baseline）。
- [ ] 文档同步：`skills/rdd-env-check/SKILL.md` 第 25 行（10 字段列表）→ 14 字段 + 边界行（第 40 行）改为"自动缓存 ADR-0016 发现（opt-out via `SKIP_AUTO_DISCOVERY=yes`）"。
- [ ] 无新增外部依赖；新增 LOC 估算：**~40 行**（cache writer 扩展 15 行 + `_read_arch_handoff_paths` 优先级链 15 行 + tests 10 行）。
