---
name: contract-check
description: |
  Spoke local implementation vs Hub OpenAPI contract validator (Breaking-Change blocks CI).

  Invoke when BOTH:
    1. Contract drift suspected OR CI integration needed
    2. Hub contract path + local implementation path provided

  Default: breaking-change exits 1; push warns (SKIP_CONTRACT_GATE); PR blocks (STRICT_CONTRACT_GATE).

  Boundary ownership: see role.boundaries.owns / not_owns.
license: MIT
compatibility: Python 3.11+
metadata:
  version: "1.0"
  author: sisyphus
  evolved-from: "W1-1 rdd-hub-bootstrap contract templates"
  user-invocable: true
---

# Contract Check

CI gate 校验 Spoke 仓库实现是否符合 Hub 端 OpenAPI contract。

## 调用

```bash
skill_use("contract-check")
# 等价于:
python3 skills/contract-check/scripts/contract_check.py \
  --hub rdd-hub/contracts/auth-v2.yaml \
  --local src/auth_impl.py
```

## 退出码

- `0` — compliant(无 diff 或仅 Low/Medium)
- `1` — Breaking-Change(必须 fix 才能合并)

## 输出

- JSON (CI-friendly): `--format json`
- Markdown (人类): `--format markdown`

## 依赖

- `openapi-diff`(可选)— 提供更精确的 OpenAPI schema diff
- 否则 fallback 到 simple YAML+grep(基线检测)

## 相关

- ADR-0030 Hub-and-Spoke 联邦架构
- W1-1 `add-rdd-hub-bootstrap`(Hub 仓库创建)
- W2-2 `add-cross-repo-state-schemas`(`contract_cache_schema.json` SSOT)
