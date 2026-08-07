## Context

**Background**: rdd-workflow 当前已部署 ADR-0016 Arch Discovery Contract(`_lib/discover-arch-artifacts.sh`)。该契约提供三层 fallback:
1. 环境变量强制覆盖(`SPEC_WORKFLOW_ADR_DIR`/`SPEC_WORKFLOW_ROADMAP_PATH`/`SPEC_WORKFLOW_ARCHITECTURE_DIR`/`SPEC_WORKFLOW_ADR_PATTERN`)
2. 默认候选自动扫描(`docs/adr` / `doc/adr` / `documentation/adrs` / `adrs` 等)
3. 硬编码 fallback(`docs/adr` / `roadmap.md` / `docs/architecture` / `ADR-*.md`)

**Current state**: 第三方项目若 ADR 路径/命名不匹配默认,phase 1-4(env-check / design / plan / ship)每次启动都重新运行 `discover-arch-artifacts.sh::discover_all()`(~50-150ms 文件系统 walk)。直到 `guide-arch` Phase 5 落盘 `.arch-handoff.json`,下游消费者(`_read_arch_handoff_paths()` in `gate.py:76-104`、`detectors.py:181`)才看到正确路径。

**Constraint — 硬阻断**: 项目自己昨天(2026-08-06)的 `rds_95b183ee73e6` (stage_arch) 和 `rds_11eee8e42b01` (stage_design) rddf-session 都是 abandoned 状态,`.arch-handoff.json` 和 `.design-handoff.json` 都不存在。guide-design / guide-plan 跑前必须 `SKIP_ARCH_HANDOFF=yes` 显式跳过两个硬门控——这是项目惯例。

**Stakeholders**:
- 第三方项目集成者:用 rdd-workflow 但 ADR 风格各异
- `guide-arch` / `guide-design` / `guide-plan` / `guide-ship` 的用户:受 phase entry 重复扫描影响
- CI / monorepo:TTL cache 行为需可预测

## Goals / Non-Goals

**Goals:**
- 把 `.env-cache.json` 从 10 字段扩展到 14 字段,记录 `discovered_adr_dir` / `discovered_roadmap_path` / `discovered_architecture_dir` / `discovered_adr_pattern`
- 让 env-check cache miss 时自动跑 `discover-arch-artifacts.sh::discover_all()` 并持久化发现结果
- 让 `_read_arch_handoff_paths()` 优先级变为 **env-cache > handoff > 默认**(三级 fallback)
- 让 `SKIP_AUTO_DISCOVERY=yes` 提供 opt-out 向后兼容
- 已有 `branch` 失效机制覆盖新字段(branch 切换自动失效)
- 不破坏现有 10 个字段顺序 / 格式(纯增量)

**Non-Goals:**
- 不改 `.arch-handoff.json` schema(ADR-0016 v1 const=1 锁版本)
- 不让 env-check 反向写 handoff(单一职责分离)
- 不修改 `_lib/discover-arch-artifacts.sh` 脚本本身
- 不引入新依赖(Pure bash + Python stdlib `json`)
- 不为 guide-design / guide-arch 添加新 env vars(全部沿用现有)

## Decisions

### Decision 1: cache 字段名用 `discovered_*` 前缀而非 `arch_*`

**Rationale**: 避免与 `.arch-handoff.json` 的字段名(`adr_dir`/`roadmap_path`/`architecture_dir`/`adr_pattern`)混淆。前缀 `discovered_` 明确表示"这是从 env-check 发现阶段来的结果",与 handoff 的"已落盘契约结果"语义分层。

**Alternatives considered**:
- 命名 = `arch_handoff_*`: 与 handoff 同名前缀,容易让消费者误以为是 handoff 字段
- 命名 = `cache_adr_dir` 等:通用 cache 前缀,但 `.env-cache.json` 已有 10 字段都没有 `cache_` 前缀,会破坏一致性

### Decision 2: 字段数 10 → 14 纯增量,不改既有字段顺序

**Rationale**: 现有消费者可能硬编码 `jq '.adr_count'` 这类位置字段依赖(虽然项目里没有,但保险起见)。增量扩展保证 `.env-cache.json` v10 schema 仍然能解析。

**Alternatives considered**:
- 重排 14 字段为更合理顺序:需要遍历全部消费者并修正,工作量大
- 用嵌套 `discovered: {adr_dir, ...}` 子对象:嵌套 JSON 比 flat 多 30 行 parser code

### Decision 3: `_read_arch_handoff_paths()` 优先级 = env-cache > handoff > 默认

**Rationale**: env-cache 是 phase entry 的"早期信号",handoff 是 "arch-done 后期固化信号"。下游消费者拿到的应该是"最早可用"的真实路径。Phase 1 之前根本没有 handoff(env-cache 是唯一持久化的发现结果);Phase 5 之后 handoff 落盘,但 env-cache 通常更新更快(branch 切换等场景)。

**Alternatives considered**:
- 优先级 = handoff > env-cache:逻辑上更"正式优先",但 arch-done 之前没有 handoff,前 4 个 phase 全走默认,等于零改进
- 优先级 = env-cache > handoff,但 handoff 显式覆盖:需要新增 `arch_handoff_forces=true` flag,复杂化

### Decision 4: SKIP_AUTO_DISCOVERY=yes 完全停止 discovery 写入(不是跳过函数调用)

**Rationale**: 让用户在 CI / monorepo 等场景强制保持现有行为。不调用 `discover_all` 比"调用但不写结果"更省 CPU(~5-50ms 节省)。

**Alternatives considered**:
- SKIP_AUTO_DISCOVERY=write(只跳过写,不跳过算):用户改 env var 名字多记一个 flag,且性能无优势

### Decision 5: 测试覆盖边界而非单元

**Rationale**: cache miss / cache hit / branch 切换 / SKIP env var / 旧 cache 文件兼容这 5 个边界用 bats 一刀切测更真实(集成测试),单元测试 `_read_arch_handoff_paths()` 优先级只有 3 case 不如集成测试反映真实场景。

**Alternatives considered**:
- 完整覆盖: 5 个 bats + 3 个 unit test = 8 个测试,工作量翻倍且维护成本高

## Risks / Trade-offs

- [Risk] 第三方项目升级 rdd-workflow 后遇到旧 `.env-cache.json`(缺 `discovered_*`)→ [Mitigation] `dict.get(discovered_adr_dir, default)` fallback 已写在 `_read_arch_handoff_paths()` 设计中,grep `tests/unit/test_gate.py::test_read_arch_handoff_paths_priority` 锁定
- [Risk] branch 切换瞬间 `.rddf/state/.env-cache.json` 因 1-2 个并行 phase 抢占失效,但有人读到中间空状态 → [Mitigation] 既有 `.tmp` → `mv` 原子写已经过验证,继续沿用
- [Risk] `discover-arch-artifacts.sh::discover_all` 单次调用 > 200ms 预算(P1 项目用 M1 Mac,第三方项目可能在 ARM CI 上跑)→ [Mitigation] MUST NOT 5 + 验收标准 `< 200ms` 在 bats 测试中实测,失败则回归
- [Risk] `SKIP_AUTO_DISCOVERY` env var 被某 ops 误设,导致发现机制静默失效 → [Mitigation] env-check 启动时打印 `✅ Skip discovery (SKIP_AUTO_DISCOVERY=yes)` 一行显眼提示
- [Trade-off] `.env-cache.json` 字段从 10 → 14 涨 30%,gitignored 文件大小可接受(从 ~200B 到 ~280B)— 选择增量而非新文件,避免 state 文件碎片化
- [Trade-off] `_read_arch_handoff_paths()` 增加 1 层 fallback 检查 +1-2 处 dict.get — 选择 vs 默认 fallback 收益对比(~50% first-run time saved),trade-off 净正

## Migration Plan

**Pre-deploy** (此提案实施前):
1. 备份现有 `.env-cache.json`(如果存在)为 `.env-cache.json.bak`
2. grep 现有对 `.env-cache.json` 字段名硬编码的测试,确认无破坏

**Deploy steps** (按 ship-phase execute 顺序):
1. `skills/rdd-env-check/scripts/env_check.sh` 增加 `_discover_arch_artifacts_and_persist` 函数,cache miss 路径触发
2. `_lib/gate.py::_read_arch_handoff_paths()` 改造为 read env-cache first
3. `skills/rdd-env-check/SKILL.md` 文档同步(10 字段列表 → 14 字段 + 边界行改文案)
4. 新增 `tests/integration/test_env_check_arch_discovery.bats` + `tests/unit/test_gate.py` 的 3 个 case

**Rollback**:
- 任何一阶段回退 = `git revert` 该阶段 commit
- 用户层 rollback: `SKIP_AUTO_DISCOVERY=yes` 立刻关掉自动写入(降级到现有 default 行为)
- 数据层 rollback: 14 字段 cache → 删 4 个 discovered 字段 → 回退到 10 字段兼容模式(消费者 `dict.get` 自动 fallback)

**Backwards compat**:
- 旧 `.env-cache.json` 文件(10 字段)在升级后:env-check 读 `dict.get(discovered_adr_dir, default)` 拿不到时回退到下一级,无异常
- 旧消费者(只读 10 字段):升级后仍能解析 14 字段,因为新字段名不会冲突

## Open Questions

- [Q1] 第三阶段 webecho `design.skill_root.sh` fallback 行为——`resolve_rdd_skill_dir` 找不到时是 silent 跳过还是 warn 后继续?
  当前设计:silent skip。优先级很低,留作 follow-up improvement。
- [Q2] `discover_adr_pattern` 已支持 `adr-*.md` lowercase 自动探测(`_lib/discover-arch-artifacts.sh:163-189`),新 cache 字段 `discovered_adr_pattern` 是否需要二次扫描其他变体(如 `MADR-*` / `RFD-*`)?
  当前设计:不二次扫描,沿用已有大小写探测即可。新变体可在 follow-up improvement 加。
- [Q3] 升级迁移路径:旧 `.env-cache.json`(10 字段)升级到 14 字段,首次 `rdd-env-check` 触发 discover 后,旧 branch 上的 cache 是否会被覆盖?——branch 失效机制已保证这是预期行为。
