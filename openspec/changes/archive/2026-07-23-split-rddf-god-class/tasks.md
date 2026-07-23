## 1. Split RddfSessionCoordinator
- [x] 1.1 提取 `_types.py`（SessionData/SessionState 类型定义、dataclass、常量）
- [x] 1.2 提取 `_store.py`（sessions.json 读写、原子文件操作、状态验证）
- [x] 1.3 提取 `_commands.py`（CRUD、生命周期转换、冲突检测、session 选择）
- [x] 1.4 提取 `_binding.py`（owner_opencode_session_id 管理、跨 session 冲突解决）
- [x] 1.5 `facade.py` 保留全部公共方法签名并 re-export

## 2. Verify Regression
- [x] 2.1 运行全部 24+10 测试通过
- [x] 2.2 lsp_find_references 验证无遗漏调用点