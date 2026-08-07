## 1. Schema Extension

- [ ] 1.1 修改 `.rddf/state/.env-cache.json` schema 从 10 字段扩展到 13 字段,追加 `discovered_adr_dir` / `discovered_roadmap_path` / `discovered_architecture_dir` / `discovered_adr_pattern` 4 个字段
- [ ] 1.2 确认 `rdd-env-check/scripts/env_check.sh` 已有的 10 字段顺序与语义保持不变(纯增量)

## 2. Auto-Discovery Wiring

- [ ] 2.1 在 `skills/rdd-env-check/scripts/env_check.sh` 中新增 `_discover_arch_artifacts_and_persist` 函数
- [ ] 2.2 该函数调用 `discover-arch-artifacts.sh::discover_all()`,把 4 个 `DISCOVERED_*` 全局变量通过 **env-var pattern** 传给 Python(Oracle C1 security,禁止 bash `$VAR` 字符串插值)
- [ ] 2.3 接入 cache miss 路径:cache 文件缺失或 `cache.branch != git branch --show-current` 时自动触发

## 3. Read-Side Fallback Chain

- [ ] 3.1 修改 `_lib/gate.py::_read_arch_handoff_paths()` 优先级为 **env-cache > handoff > 默认** fallback
- [ ] 3.2 用 `dict.get(field, default)` 模式保证旧 `.env-cache.json`(10 字段,缺 discovered_*)向后兼容
- [ ] 3.3 验证 `_lib/loop/detectors.py::detect_adr_status` 通过 `_read_arch_handoff_paths()` 间接读取到新字段(零额外改动)

## 4. Opt-Out Path

- [ ] 4.1 在 `_discover_arch_artifacts_and_persist` 中检查 `SKIP_AUTO_DISCOVERY=yes` env var;为 yes 时跳过 `discover_all` 调用,完全不改 cache 字段
- [ ] 4.2 当 SKIP_AUTO_DISCOVERY=yes 时,在 env-check 输出中打印 `✅ Skip discovery (SKIP_AUTO_DISCOVERY=yes)` 显眼提示,防止误设

## 5. Documentation Sync

- [ ] 5.1 更新 `skills/rdd-env-check/SKILL.md` 第 25 行:10 字段列表 → 13 字段
- [ ] 5.2 更新 SKILL.md 第 40 行边界段:"不缓存 ADR-0016 工件发现" → "自动缓存 ADR-0016 发现(opt-out via `SKIP_AUTO_DISCOVERY=yes`)"

## 6. Test Coverage

- [ ] 6.1 新建 `tests/integration/test_env_check_arch_discovery.bats`,覆盖 5 个场景:
  - [ ] 6.1.1 Scenario 1:第三方项目首次 env-check → cache miss → discover → 落盘 → 下游命中
  - [ ] 6.1.2 Scenario 2:env-check cache hit(TTL 内 + 同 branch)→ 零重扫
  - [ ] 6.1.3 Scenario 3:branch 切换 → cache.branch 不匹配 → 重发现
  - [ ] 6.1.4 Scenario 4:SKIP_AUTO_DISCOVERY=yes → 行为完全等同现状
  - [ ] 6.1.5 Scenario 6:旧 cache 文件(10 字段) → `dict.get` fallback 不抛异常
- [ ] 6.2 在 `tests/unit/test_gate.py`(或新建 `test_gate_arch_handoff_paths.py`)加 3 个 case 锁定 `_read_arch_handoff_paths()` 三级 fallback 优先级

## 7. Verification

- [ ] 7.1 跑 `./test.sh --quick` 确认 60s pytest unit + 30s bats smoke baseline 全绿,无回归
- [ ] 7.2 跑 `./test.sh --bats --regression` 验证无新增失败(对比 `KNOWN_FAILURES.txt` baseline)
- [ ] 7.3 手动跑一次第三方仿真:`mkdir -p /tmp/third-party-doc/decision && echo "RFC-0001-foo" > /tmp/third-party-doc/decision/RFC-0001-foo.md && cd /tmp/third-party-doc && SPEC_WORKFLOW_ADR_DIR=decision SPEC_WORKFLOW_ADR_PATTERN='RFC-*.md' rdd-env-check` → 验证 discovered_adr_dir / discovered_adr_pattern 被正确捕获
- [ ] 7.4 git worktree 内 1 个聚合 commit:`feat(env-check): cache arch-discovery on first run (P2)` 匹配仓库 convention
- [ ] 7.5 archive change: `openspec archive add-env-cache-arch-discovery --yes` + `git commit` archive moves
