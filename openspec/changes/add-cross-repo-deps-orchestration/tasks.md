## Implementation Tasks

- [ ] 创建 `skills/_lib/cross_repo_deps.py` 核心模块
  - [ ] 实现 `parse_spoke_iteration(spoke_json)` 函数，提取 `cross_repo_dependencies`
  - [ ] 实现 `build_cross_repo_graph(spokes_data)` 构建跨仓库依赖图
  - [ ] 实现 `detect_cycle(graph)` 使用 DFS 检测循环，返回环成员列表
  - [ ] 实现 `kahn_topological_sort(graph)` 返回 waves 列表
  - [ ] 实现 `calculate_eta_lv1(change, velocity_cache)` 从 tasks.md 计算 ETA
  - [ ] 实现 `calculate_eta_lv2(proposal_path)` 读取 frontmatter `eta` 字段
  - [ ] 实现 `calculate_eta_lv3(manual_eta)` 使用手动设置的 ETA
  - [ ] 实现 `eta_fallback_chain(change)` 三级回退主函数
  - [ ] 实现 `generate_mermaid(graph, etas)` 生成 Mermaid 格式输出
  - [ ] 编写单元测试 `tests/unit/test_cross_repo_deps.py`

- [ ] 创建 `skills/_lib/cross_repo_deps_cache.py` 缓存模块
  - [ ] 实现 `load_cache(spokes_key)` 读取 `.cross-repo-deps-cache.json`
  - [ ] 实现 `save_cache(spokes_key, data)` 写入缓存（TTL 24h）
  - [ ] 实现 `is_cache_valid(cache_entry)` 检查 TTL
  - [ ] 编写单元测试 `tests/unit/test_cross_repo_deps_cache.py`

- [ ] 创建 `rddf hub issue --deps` 命令
  - [ ] 实现 `create_hub_issue(dep_info)` 调用 Hub API 创建 Issue
  - [ ] 实现 `update_hub_issue(issue_id, dep_info)` 更新已存在 Issue
  - [ ] 实现 `find_existing_issue(from_change, depends_on)` 查找重复 Issue
  - [ ] 编写单元测试 `tests/unit/test_hub_issue.py`

- [ ] 升级 `skills/_lib/iteration/` 的 schema 至 v7
  - [ ] 更新 `iteration.json` schema 文件添加 `cross_repo_dependencies` 字段定义
  - [ ] 实现 `load_iteration_v6_compat(json_data)` 向后兼容 v6
  - [ ] 实现 `save_iteration_v7(data)` 写入 v7 格式
  - [ ] 更新 `iteration/render.py` 支持 `cross_repo_dependencies` 展示
  - [ ] 编写单元测试 `tests/unit/test_iteration_v7.py`

- [ ] 升级 `guide-plan` deps 阶段
  - [ ] 修改 `guide-plan.md` Phase 3 添加 `rddf deps cross-repo` 调用
  - [ ] 实现 `check_strict_deps_gate(change)` 检查强依赖状态
  - [ ] 实现 `block_plan_done_on_strong_deps()` 挂起 plan-done 门控
  - [ ] 添加 `STRICT_DEPS_GATE=yes` 环境变量支持
  - [ ] 添加 `SKIP_STRICT_DEPS_GATE=yes` 跳过选项
  - [ ] 编写集成测试 `tests/integration/test_guide_plan_cross_repo_deps.bats`

- [ ] 创建 `rddf deps cross-repo` CLI 入口
  - [ ] 在 `skills/deps/` 下创建 `scripts/cross_repo_cli.py`
  - [ ] 实现 `--spokes` 参数解析（逗号分隔的 org/repo 列表）
  - [ ] 实现 `--force-refresh` 强制刷新缓存
  - [ ] 实现 `--output-format` 支持 mermaid/json/text
  - [ ] 编写集成测试 `tests/integration/test_rddf_cross_repo_cli.bats`

- [ ] 创建 `rddf hub` CLI 入口
  - [ ] 在 `skills/` 下创建 `hub/scripts/hub_cli.py`
  - [ ] 实现 `rddf hub issue --deps` 子命令
  - [ ] 实现 `--from` 和 `--depends-on` 参数
  - [ ] 实现 `--eta` 参数
  - [ ] 编写集成测试 `tests/integration/test_rddf_hub_issue.bats`

- [ ] 更新 velocity cache 机制
  - [ ] 创建 `~/.rddf/state/.velocity-cache.json` 模板
  - [ ] 实现 `read_velocity_cache()` 读取历史速率
  - [ ] 实现 `update_velocity_cache(change_name, actual_days)` 更新速率
  - [ ] 实现 TTL 过期检测（7 天）
  - [ ] 编写单元测试 `tests/unit/test_velocity_cache.py`

- [ ] 集成测试：完整跨仓库依赖流程
  - [ ] 创建 `tests/integration/test_cross_repo_deps_full.bats`
  - [ ] 模拟 3 个 Spoke 仓库的 `iteration.json`
  - [ ] 验证 Mermaid 输出格式正确
  - [ ] 验证 Kahn 拓扑排序产生正确的 waves
  - [ ] 验证循环检测报警正确

- [ ] 更新文档
  - [ ] 更新 `skills/deps/SKILL.md` 添加 cross-repo 相关说明
  - [ ] 更新 `docs/adr/ADR-00XX-cross-repo-deps.md`（新 ADR）
  - [ ] 更新 `CHANGELOG.md` 记录新 feature
