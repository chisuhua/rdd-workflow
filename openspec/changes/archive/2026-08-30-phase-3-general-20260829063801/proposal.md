# phase-3-general-20260829063801

## Why

`ADR-0012` (flow customization layer) + `ADR-0020` (incremental skeleton planning) 已定义 plugin loader,但 `_lib/loop/plugin_loader.py` 仅有 stub,无 manifest schema、无 lifecycle hooks、无 reference plugins。**Why now**: 用户为多项目部署 rdd-workflow,每个项目需定制 detector/action。

## What Changes

**In Scope**:

- **Out Scope**: plugin marketplace;plugin 签名

### 关键场景

- GIVEN 3rd party 发布 plugin 包含 `plugin.yaml` + `detectors/*.py`
  WHEN rddf 启动
  THEN plugin 被自动加载,detector 注册到 detectors registry
- GIVEN plugin manifest 缺 required field
  WHEN load  THEN 拒绝加载,日志记录但不 crash

**Out of Scope**:

- (no items specified)

## Capabilities

- MUST: plugin 在独立进程/线程运行,主进程不被污染

## Impact

- MUST NOT: plugin 自动执行网络请求 (除非 manifest 显式声明 `network: true`)

## Acceptance

- 3 reference plugins 端到端测试通过
- plugin manifest schema 测试 (5 个 invalid case reject)
- plugin 隔离性测试 (mock plugin 抛异常不影响主流程)

