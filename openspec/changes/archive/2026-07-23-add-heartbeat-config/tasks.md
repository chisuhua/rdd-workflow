## 1. Add Heartbeat Config Support
- [x] 1.1 解析 RDDF_HEARTBEAT_TIMEOUT_SECONDS 环境变量（非法值回退默认值）
- [x] 1.2 解析 RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS 环境变量
- [x] 1.3 check_heartbeat_timeouts() 使用实例属性替代模块常量

## 2. Add Tests
- [x] 2.1 测试默认值行为
- [x] 2.2 测试环境变量覆盖
- [x] 2.3 测试非法值回退