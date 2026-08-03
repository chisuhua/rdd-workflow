## Context

**背景**: `guide-arch` Phase 1 setup 当前同时承担 ADR-0016 Layer 1 工件发现与 openspec/git/build 环境健康检查。前者必须在每次 phase 进入时重新运行，后者是可复用、可缓存的静态检查；两类职责混合导致 arch 菜单首屏约 15 行、约 600 tokens 的环境噪音。

**当前状态**: `skills/guide-arch/scripts/arch_env_check.sh` 直接检测 openspec CLI、git 工作区、当前 branch、build 目录，并在同一函数中调用 `discover-arch-artifacts.sh` 后统计 ADR、roadmap、gap analysis 与 active changes。arch/design/plan/ship 的 Phase 1 均需要保持现有环境安全网，但当前没有独立的 `rdd-env-check` skill，也没有可按 TTL 和 branch 失效的环境快照。

**约束**:
- MUST 保留 ADR-0016 Layer 1 工件发现于 `guide-arch`，每次进入 phase 都重新运行，不得缓存或修改 `discover-arch-artifacts.sh`
- MUST 保持 `arch_env_check.sh` 现有 JSON 字段集合不变：`timestamp`, `ttl_s`, `branch`, `openspec_ver`, `git_clean`, `build_dir`, `adr_count`, `roadmap_exists`, `gap_count`, `active_changes`
- MUST 使用固定 cache 路径 `.rddf/state/.env-cache.json`，默认 TTL 3600 秒，并支持 `RDD_ENV_CACHE_TTL` 覆盖
- MUST 不引入新运行时依赖；运行路径仅依赖 bash、git、openspec，jq/python3 在测试环境中可缺席
- MUST 不修改 rddf-session 协议、其他 Phase 2-6 行为及 proposal 明确列出的 gate/handoff 脚本
- SHOULD 使用 atomic rename 写入 cache，且 cache 不保存 token、绝对路径或 git remote 等敏感信息

## Goals / Non-Goals

**Goals**:
- 新建独立 `skills/rdd-env-check/` skill，由 `scripts/env_check.sh` 执行完整环境检查并维护环境快照
- 将可复用 `_check_*` 函数提取到 `skills/_lib/env_checks.sh`，供新 skill 与 `arch_env_check.sh` 共享
- 通过 `.rddf/state/.env-cache.json` 实现 cache hit、1 小时 TTL 过期与 branch 切换失效，并保留 cache 缺失时现场全量检查的透明降级路径
- 让 guide-arch Phase 1 保留实时工件发现，同时将菜单首屏压缩为含 Env、ADR 计数与 roadmap 状态的单行输出
- 将相同环境检查模式接入 arch/design/plan/ship Phase 1，保持阻断行为、JSON 字段和现有测试兼容
- 用 3 个 bats 用例覆盖 cache 命中、TTL 过期和 branch 变化失效，并验证 openspec 缺失、无 jq/python3、性能与 DRY 契约

**Non-Goals**:
- 不缓存、替换或修改 ADR-0016 Layer 1 工件发现
- 不修改 `arch_done_gate.sh`、`arch_quality_report.sh`、`write_arch_handoff.sh`
- 不修改 rddf-session state schema 或协议；`.env-cache.json` 仅作为同目录伴随状态
- 不引入 CI 自动运行 env-check
- 不修改四个 phase 技能的 Phase 2-6 行为
- 本次 fill 不创建 `specs/` capability delta

## Decisions

### 决策 1: 将环境健康检查定义为独立 skill，工件发现继续归 guide-arch

新增 `skills/rdd-env-check/SKILL.md` 与 `skills/rdd-env-check/scripts/env_check.sh`，负责 openspec、git、branch、build 及环境快照输出。`guide-arch` 仍在 Phase 1 每次调用 ADR-0016 discovery 并计算 ADR/roadmap 等架构工件状态，避免 branch 切换或目录重命名后读取陈旧发现结果。

### 决策 2: 使用共享 shell 函数保持检查逻辑单一来源

把现有可复用的 `_check_openspec`、`_check_git`、`_check_build_dir` 等 `_check_*` 逻辑提取到 `skills/_lib/env_checks.sh`。`rdd-env-check` 与重构后的 `arch_env_check.sh` 均 source 该库，至少形成 4 处 `_check_*` 引用，避免两个脚本复制环境判定与修复指引。

### 决策 3: 以 TTL + branch 双条件判定 cache 有效性

cache 固定写入 `.rddf/state/.env-cache.json`，默认 `ttl_s=3600`，允许 `RDD_ENV_CACHE_TTL` 覆盖；值为 0 时始终失效。仅当 cache 存在、mtime 未超过 TTL 且 `cache.branch` 等于当前 `git rev-parse --abbrev-ref HEAD` 时命中，否则执行完整检查并以 `.tmp` → final 的 atomic rename 覆盖快照。

### 决策 4: 保持 JSON 契约与失败语义，显示层只做压缩

新 skill 与兼容入口输出相同字段集合，不改变 openspec 缺失等错误的非零退出码和修复指引。cache hit 只跳过可缓存的完整环境检查，不跳过必要的硬门；guide-arch 首屏将详细静态信息折叠为 `✅ Env OK (cached Xm ago) | ADR:N | Roadmap:✓` 单行，cache miss 对直接调用 guide-arch 的用户透明。

### 决策 5: 四阶段接入采用最小替换并以现有回归测试锁定兼容性

仅替换 arch/design/plan/ship Phase 1 的环境检查调用，不触碰后续 phase。新增 bats 先锁定 cache 三场景和 JSON 字段，再运行现有 49 个相关测试与手工 walkthrough，验证行为兼容；同时以无 jq/python3 的 PATH 场景证明没有新增运行时依赖。

## Risks

- **cache 陈旧导致错误放行**: 同时检查 mtime TTL 与 branch，并允许 `RDD_ENV_CACHE_TTL=0` 强制失效；任何无效或缺失 cache 都回退到全量检查
- **工件发现被误缓存**: 明确保留 `discover-arch-artifacts.sh` 在 guide-arch Phase 1 每次运行，cache 仅覆盖环境健康快照
- **JSON 向后兼容破坏**: 用 bats 对新旧脚本字段集合做 diff，并保持 10 个既有字段名称不变
- **共享函数提取改变错误语义**: 先以失败测试锁定 openspec 缺失、git 状态与 build 判定，再做最小提取并运行现有 49 个测试
- **cache 半写或敏感信息泄漏**: 使用同目录临时文件 atomic rename，字段白名单不包含 token、绝对路径或 git remote
- **可选工具被误变为运行时依赖**: 在 jq/python3 不可用的测试 PATH 下执行核心路径，所有 JSON/cache 操作保持纯 bash 实现
- **首屏压缩隐藏修复信息**: 正常或 cache-hit 路径仅显示单行；失败路径仍输出完整修复指引并返回非零

## Open Questions

- 无；TTL、branch 失效、JSON 字段、cache 路径与职责边界均由 proposal 和 improvement source 明确约束。
