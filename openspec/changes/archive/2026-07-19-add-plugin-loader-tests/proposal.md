## Why

`plugin_loader.py` 114 行做动态插件加载，是 loop 引擎的可扩展性入口。现有 `except Exception:` 块无 logging，且无 dedicated unit test 锁定预期行为。需要 3 个核心场景的单元测试。

## What Changes

- 创建 `tests/unit/test_plugin_loader.py`
- 3 个测试函数：load 成功 / load 失败 / 重复 load
- 使用 pytest `tmp_path` fixture，不依赖外部插件文件
- 不改动 plugin_loader.py 源码

## Capabilities

### New Capabilities
- `plugin-loader-test-suite`: plugin_loader.py 核心场景单元测试

### Modified Capabilities
- （无）

## Impact

- **Affected code**: 仅 `tests/unit/test_plugin_loader.py`（新增文件）
- **Scope**: 测试覆盖，不改源码
- **Risk**: 极低
- **Effort**: 1-2 小时