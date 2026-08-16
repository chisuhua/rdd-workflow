# Cross-Project Contracts

本目录存放跨项目接口契约(OpenAPI / Protobuf / JSON Schema)。

## 命名约定

- `<service>-<version>.yaml` — 例如 `auth-v2.yaml`
- 版本号遵循 [SemVer](https://semver.org/)

## 修改流程

1. 在 Hub 仓库创建 PR
2. 关联 RFC Issue(RDD Cross-Repo Sync 看板)
3. 等待所有 Spoke 仓库 ack
4. merge 后通过 `rddf sync-hub` 拉取到本地
