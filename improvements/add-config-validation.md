# add-config-validation

**优先级**: P0 | **来源**: Oracle 代码审查 2026-07-19 #8
**阶段**: default | **分类**: general
**类型**: feature

## 架构依据
- Oracle 结论：root config.yaml 是用户可编辑入口，config.py::ConfigParser 消费方。一旦用户改了 yaml key（如 max_iterations → maxIterations），ConfigParser 静默返回 None，Loop 引擎用默认值 100 — 静默降级而非报错。这是用户侧可触达的真问题。
- ADR-0004 §3: Loop 引擎安全机制配置

## 范围
- **In Scope**:
  - config.py::ConfigParser.load() 末尾加 validate() 方法
  - skills/_lib/schemas/config_schema.json（jsonschema，项目已用）
  - schema 校验 required keys + 类型（max_iterations, max_retries 等）
  - 失败时 raise ConfigError(...) 而非静默 fallback
  - 对应单元测试
- **Out Scope**:
  - 不修改 config.yaml 格式
  - 不修改 LoopEngine 的配置消费逻辑
  - 不校验 phase_templates.yaml

## 关键场景
- GIVEN config.yaml 中 max_iterations 拼写为 maxIterations, WHEN ConfigParser.load(), THEN 抛出 ConfigError 而非静默使用默认值
- GIVEN config.yaml 合法完整, WHEN ConfigParser.load(), THEN validate() 通过, 行为不变

## 技术约束
- MUST 使用现有 skills/_lib/schemas/ 下的 jsonschema 模式（项目已有依赖）
- MUST 保持向后兼容：缺失 schema 文件时跳过验证
- SHOULD 验证逻辑放入 ConfigParser 的方法，而非独立函数

## 验收标准
- config_schema.json 约 50 行
- validate() 方法在 load() 末尾被调用
- 2-3 个单元测试覆盖合法/非法/缺失 schema 场景
- 所有现有测试通过
