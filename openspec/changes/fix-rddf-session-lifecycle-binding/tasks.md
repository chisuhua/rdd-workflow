## 1. guide-design SKILL.md hook 修复

- [ ] 1.1 在 `guide-design/SKILL.md` Phase 1 `rddf_session_hook_entry` 调用前添加 skill_root.sh fallback source 逻辑
- [ ] 1.2 在 `guide-design/SKILL.md` Phase 5 `rddf_session_hook_close` 调用前添加同样的 source 逻辑

## 2. guide-plan SKILL.md hook 修复

- [ ] 2.1 在 `guide-plan/SKILL.md` Phase 1 `rddf_session_hook_entry` 调用前添加 skill_root.sh fallback source 逻辑
- [ ] 2.2 在 `guide-plan/SKILL.md` Phase 4 `rddf_session_hook_close` 调用前添加同样的 source 逻辑

## 3. guide-ship SKILL.md hook 修复

- [ ] 3.1 在 `guide-ship/SKILL.md` Phase 1 `rddf_session_hook_entry` 调用前添加 skill_root.sh fallback source 逻辑
- [ ] 3.2 在 `guide-ship/SKILL.md` Phase 5 `rddf_session_hook_close` 调用前添加同样的 source 逻辑

## 4. 优雅降级验证

- [ ] 4.1 验证 `skill_root.sh` 缺失时 hook 打印 warning 且不阻塞工作流
- [ ] 4.2 运行 `skill_use("guide-plan")` 后确认 `sessions.json` 出现 `kind=stage_plan` 且 parent 指向 stage_design
- [ ] 4.3 运行 `python3 -m pytest tests/unit/ -q` 全量回归，确认无破坏
