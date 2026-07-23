## 1. Add rddf_session_hook_attach
- [ ] 1.1 在 rddf_session_hooks.sh 中实现 rddf_session_hook_attach 函数
- [ ] 1.2 签名与 detach 镜像对齐（接受 session_id 和 change_name 参数）
- [ ] 1.3 写入 idempotent（重复调用不报错）

## 2. Integrate Attach Hooks
- [ ] 2.1 guide-plan Phase 2（propose 完成后）调用 attach
- [ ] 2.2 guide-ship Phase 1（plan 生成后）调用 attach
- [ ] 2.3 4 个测试（正常/idempotent/detach 兼容/hook 集成）