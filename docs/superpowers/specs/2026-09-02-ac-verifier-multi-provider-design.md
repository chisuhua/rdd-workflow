# AC Verifier Multi-Provider — Design

**Date**: 2026-09-02
**Status**: Draft (awaiting user review)
**Author**: brainstorming session output
**Related**: `ac_verifier.py` 当前实现为 stub-only(真实 provider 抛错,仅 mock 可用);rdd-verifier 阶段(ADR-0034)在生产路径上必须能调用真实 LLM。

## 1. Problem & Motivation

### Observed failure mode

当前 `skills/ac-verifier/scripts/ac_verifier.py:123-148` 的 `invoke_ai_agent()` 函数是 **stub**:

```python
provider = os.environ.get("AC_LLM_PROVIDER", "").lower()
if not provider:
    raise AcVerifierError("AC_LLM_PROVIDER not set and AC_LLM_MOCK != yes. ...")
# Real LLM invocation is delegated to a future implementation.
# v1 ships mock-first; real provider implementation in Task 9.
raise AcVerifierError(
    f"Real LLM provider '{provider}' not yet wired in v1. "
    f"Use AC_LLM_MOCK=yes for testing."
)
```

任何 `AC_LLM_PROVIDER=openai|anthropic|local-ollama` 的设置**都会抛错**。rdd-verifier 阶段(ADR-0034)在 archive 前批量跑 ac-verifier,生产路径上**只有 mock 可用**,无法验证真实实现是否满足 proposal ACs。

### Root cause

v1 采用 mock-first 策略(参见 `ac_verifier.py` 顶部注释 "v1 ships mock-first; real provider implementation in Task 9"),但 Task 9 未在 v1 实现周期内完成。当前 PR/rdd-verifier 上线时,真实 LLM 调用尚未实现,导致 rdd-verifier 在生产路径上只能跑 mock,**失去语义验证能力**(mock 返回固定 verdict,无法判断 AC 是否真的实现)。

### Goal

把 `invoke_ai_agent()` 从 stub 替换为可工作的多 provider 实现,支持至少 4 个 provider(openai / anthropic / ollama / MiniMax),并在保持向后兼容(AC_LLM_MOCK、STRICT_AC_GATE、SKIP_AC_VERIFICATION)的前提下让 rdd-verifier 能在生产路径上调真实 LLM。

## 2. Design Decisions (from brainstorming)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| 改进目标 | 完全多 provider 化 + 重构 | 用户在 brainstorming Q1 选择;mock + 4 provider 全部支持;扩展性最好 |
| MiniMax 协议 | 假设 OpenAI 兼容,placeholder 实现 | 用户在 Q2 选择;无官方文档时不阻塞,MiniMax 默认 base_url 留空强制用户配置 |
| 能力范围 | 单轮 JSON 调用(无 tool use) | 用户在 Q3 选择;最小可用,所有 provider 都能支持;未来可独立升级 JSON mode/tool use |
| 依赖管理 | 纯 HTTP requests(0 SDK) | 方案 A;仓库已用 requests (cross_repo_protocol),无需引入 anthropic/openai SDK |
| 抽象层 | 共享 `BaseHTTPProvider` 基类 + 5 子类 | 新 provider = 50 行子类;HTTP/重试/超时/错误分类统一处理 |
| 测试策略 | mock `requests.post` + 现有 AC_LLM_MOCK 回归 | CI 默认无需 API key;live test 显式 opt-in |
| 依赖添加 | `requests>=2.28` 进 requirements.txt | 仓库已声明 (cross_repo_protocol 使用);确认无冲突 |

## 3. Architecture

### Component diagram

```
ac_verifier.py:verify_change(change_name)
       │
       ├─ parse_acs(proposal_path)                  # extract AC bullets
       ├─ build_agent_prompt(acs, change_name)      # (system, user)
       │
       ▼
ac_verifier.py:invoke_ai_agent(system, user)        # MODIFIED: dispatcher
       │
       ├─ if AC_LLM_MOCK=yes → ac_verifier_mocks.py # 现有 mock 路径,不变
       │
       └─ else:
              name = os.environ["AC_LLM_PROVIDER"]
                  │
                  ▼
              llm_providers.get_provider(name)      # registry dispatch
                  │
                  ▼
              BaseHTTPProvider.invoke(system, user)
                  ├─ _build_payload()               # provider-specific
                  ├─ _build_headers()               # provider-specific
                  ├─ requests.post(url, ...)        # shared HTTP
                  ├─ retry: 1s/2s/4s 指数退避         # shared
                  ├─ error classification:           # shared
                  │     401/403 → AuthError(no retry)
                  │     429 → RateLimitError(retry)
                  │     5xx → ProviderError(retry)
                  │     network → NetworkError(retry)
                  └─ _parse_response(data)          # provider-specific
       │
       ▼
parse_verdict(raw, len(acs))                        # JSON 验证(不变)
       │
       ▼
.rddf/state/.ac-verifier-report.json               # 输出(不变)
```

### New file layout

```
skills/ac-verifier/
├── SKILL.md                                  # 更新: 新增 Provider 配置节
└── scripts/
    ├── ac_verifier.py                        # MODIFIED: invoke_ai_agent 委托给 registry
    ├── ac_verifier.sh                        # MODIFIED: header 注释新增 env vars 文档
    ├── ac_verifier_mocks.py                  # UNCHANGED
    └── llm_providers/                        # NEW
        ├── __init__.py                       # PROVIDERS registry + get_provider()
        ├── base.py                           # BaseHTTPProvider + LLMError 层级
        ├── openai.py                         # OpenAIProvider (OpenAI 协议)
        ├── anthropic.py                      # AnthropicProvider (原生协议, 不同 payload)
        ├── ollama.py                         # OllamaProvider (OpenAI 兼容, 无 auth)
        └── minimax.py                        # MiniMaxProvider (OpenAI 兼容 placeholder)
```

### Key design constraints

1. **AC_LLM_MOCK 第一优先级**: dispatcher 第一行检查 mock,绝不进 provider 注册表 — 保证现有 12 个 mock 测试零回归。
2. **Provider 通过 env var 全配置化**: provider name + base_url + api_key + model + timeout + max_retries 全部 env var,无配置文件依赖(`.rddf/project.yaml` 的 `verification.provider: hook` 机制保留,本 change 不动)。
3. **MiniMax 不静默调错地方**: `default_base_url=""` 启动即报错 "AC_LLM_BASE_URL not set",强制用户配置;无 fallback endpoint。
4. **Anthropic 协议隔离**: payload/headers/response parsing 全部 override,与 OpenAI 协议解耦;未来加 Gemini/Cohere 同理。
5. **失败可观测**: 所有错误带 provider name 前缀(stderr: `❌ {provider}: ...`),便于运维定位。

## 4. Components

### 4.1 `BaseHTTPProvider` (base.py)

```python
class LLMError(Exception): ...
class AuthError(LLMError): ...        # 401/403 — fatal, no retry
class RateLimitError(LLMError): ...   # 429 — retryable
class NetworkError(LLMError): ...     # connection/timeout — retryable
class ProviderError(LLMError): ...    # 5xx / bad payload

class BaseHTTPProvider(ABC):
    name: str = "base"
    default_base_url: str = ""
    default_model: str = ""

    def __init__(self):
        self.base_url = os.environ.get("AC_LLM_BASE_URL", "").rstrip("/") or self.default_base_url
        self.api_key = os.environ.get("AC_LLM_API_KEY", "")
        self.model = os.environ.get("AC_LLM_MODEL", "") or self.default_model
        self.timeout = int(os.environ.get("AC_LLM_TIMEOUT", "60"))
        self.max_retries = int(os.environ.get("AC_LLM_MAX_RETRIES", "3"))
        if not self.api_key:
            raise AuthError(f"{self.name}: AC_LLM_API_KEY not set")
        if not self.base_url:
            raise ProviderError(f"{self.name}: AC_LLM_BASE_URL not set and no default")

    def invoke(self, system: str, user: str) -> str:
        payload = self._build_payload(system, user)
        headers = self._build_headers()
        url = f"{self.base_url}/v1/chat/completions"
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
                if resp.status_code in (401, 403):
                    raise AuthError(f"{self.name}: HTTP {resp.status_code}")
                if resp.status_code == 429:
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt); continue
                    raise RateLimitError(f"{self.name}: HTTP 429 (max retries)")
                if resp.status_code >= 500:
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt); continue
                    raise ProviderError(f"{self.name}: HTTP {resp.status_code}")
                if resp.status_code != 200:
                    raise ProviderError(f"{self.name}: HTTP {resp.status_code} body={resp.text[:200]}")
                return self._parse_response(resp.json())
            except (requests.ConnectionError, requests.Timeout) as e:
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt); continue
                raise NetworkError(f"{self.name}: {type(e).__name__}: {e}")
        raise ProviderError(f"{self.name}: max retries exceeded: {last_err}")

    @abstractmethod
    def _build_payload(self, system: str, user: str) -> dict: ...
    @abstractmethod
    def _build_headers(self) -> dict: ...
    def _parse_response(self, data: dict) -> str:
        """Default: OpenAI format. Override for Anthropic."""
        return data["choices"][0]["message"]["content"]
```

### 4.2 5 个 Provider 子类

| Provider | 默认 base_url | 默认 model | 协议 | 备注 |
|----------|---------------|------------|------|------|
| `openai` | `https://api.openai.com` | `gpt-4o-mini` | OpenAI native | 标头 `Authorization: Bearer {key}` |
| `anthropic` | `https://api.anthropic.com` | `claude-3-5-haiku-20241022` | Anthropic native | payload/headers/parsing 全部 override |
| `ollama` | `http://localhost:11434` | `llama3.1` | OpenAI 兼容 | 无 auth,api_key 填 "ollama" 占位 |
| `minimax` | `""` (强制 env 配置) | `MiniMax-M3` | OpenAI 兼容 | placeholder,真实端点由用户配 |

### 4.3 Dispatcher (modify `ac_verifier.py:123-148`)

```python
def invoke_ai_agent(system: str, user: str) -> str:
    if os.environ.get("AC_LLM_MOCK", "").lower() == "yes":
        # 现有 mock 路径,不变
        import importlib.util
        _mock_path = Path(__file__).resolve().parent / "ac_verifier_mocks.py"
        _spec = importlib.util.spec_from_file_location("ac_verifier_mocks", _mock_path)
        _mod = importlib.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        return _mod.mock_invoke(system, user)

    from skills.ac_verifier.scripts.llm_providers import get_provider
    name = os.environ.get("AC_LLM_PROVIDER", "").lower()
    if not name:
        raise AcVerifierError(
            "AC_LLM_PROVIDER not set and AC_LLM_MOCK != yes. "
            "Set AC_LLM_PROVIDER=openai|anthropic|ollama|minimax or AC_LLM_MOCK=yes."
        )
    provider = get_provider(name)  # raises ProviderError if unknown
    return provider.invoke(system, user)
```

> **⚠️ SECURITY**: 真实 API key **永不**写入代码或文档。env var `AC_LLM_API_KEY` 由用户/部署环境注入。本设计文档不包含任何 key 示例。
>
> **注**: 现有 `skills/cross-repo-protocol/mcp_client.py` 已 lazy `import requests`,但**未在 `requirements.txt` 显式声明**(依赖隐式存在)。本 change 将 `requests>=2.28` 显式声明,既满足本 skill,也修复 cross-repo-protocol 的隐性依赖。

## 5. Data Flow

```
ac_verifier.sh
  ↓ (resolve PROJECT_ROOT, parse args, env checks)
ac_verifier.py:verify_change(name)
  ↓
  proposal.md → parse_acs() → [AC-1, AC-2, ...]
  ↓
  build_agent_prompt(acs, name) → (system, user)
  ↓
  invoke_ai_agent(system, user)
    ├─ mock 分支: AC_LLM_MOCK=yes → mock_invoke()
    └─ 真实分支: AC_LLM_PROVIDER=X → get_provider(X).invoke()
        ↓
        requests.post → HTTP 200/4xx/5xx
        ↓
        _parse_response → text
  ↓
  parse_verdict(text, n_acs) → verdict list (JSON schema validated)
  ↓
  write .rddf/state/.ac-verifier-report.json
  ↓
  exit 0 (all pass) / 1 (any fail) / 2 (skip) / 3 (error)
```

### Error → exit code mapping

| 错误 | 重试 | 最终 exit | stderr 示例 |
|------|------|-----------|-------------|
| `AuthError` | ❌ | 3 | `❌ openai: HTTP 401 — check AC_LLM_API_KEY` |
| `RateLimitError` (max retries) | ✅ 3x | 3 | `❌ openai: HTTP 429 rate limited — try later` |
| `NetworkError` (max retries) | ✅ 3x | 3 | `❌ openai: ConnectionError: ...` |
| `ProviderError` 5xx (max retries) | ✅ 3x | 3 | `❌ openai: HTTP 500` |
| `ProviderError` 4xx bad payload | ❌ | 3 | `❌ openai: HTTP 400 body=...` |
| `ProviderError` unknown provider | ❌ | 3 | `❌ Unknown provider 'X'. Valid: [...]` |
| `AcVerifierError` (JSON parse) | ❌ | 3 | `❌ verdict parse failed` |

**指数退避**: 1s / 2s / 4s(attempt 0/1/2)。

## 6. Testing

### 6.1 单元测试 (`tests/unit/test_ac_verifier_providers.py`, 新文件)

~30 cases,全部 mock `requests.post`,无真实 HTTP/无 API key:

- `BaseHTTPProvider` 行为:
  - 401 → `AuthError`,无重试
  - 403 → `AuthError`,无重试
  - 429 → 重试 3 次后 `RateLimitError`
  - 500 → 重试 3 次后 `ProviderError`
  - `requests.ConnectionError` → 重试 3 次后 `NetworkError`
  - `requests.Timeout` → 重试 3 次后 `NetworkError`
  - 指数退避时间正确(可 mock `time.sleep`)
  - max_retries=0 边界(不重试)
  - 200 + OpenAI 格式 → `_parse_response` 提取 `choices[0].message.content`
- env var 解析:
  - 默认值生效
  - override 生效
  - `AC_LLM_API_KEY=""` → `AuthError` 立即抛
  - MiniMax `AC_LLM_BASE_URL=""` → `ProviderError` 立即抛
- 5 个 provider 子类:
  - `_build_payload` 输出结构(无 HTTP)
  - `_build_headers` 输出结构
  - Anthropic `_parse_response` 提取 `content[0].text`
- Dispatcher:
  - 未知 provider name → `ProviderError`
  - `AC_LLM_MOCK=yes` 优先级高于 `AC_LLM_PROVIDER`(回归)

### 6.2 集成测试 (`tests/integration/test_ac_verifier_http_live.bats`, 新文件)

启动本地 mock HTTP server(用 `python3 -m http.server` 或 `nc -l`),真实 `requests.post`:

- mock server 返回 200 + OpenAI 格式 → 全链路通
- mock server 返回 401 → 立即 exit 3
- mock server 返回 500 → 重试 3 次后 exit 3
- mock server close 连接 → 重试 3 次后 exit 3

### 6.3 回归测试 (现有, 必须保持全绿)

- `tests/unit/test_ac_verifier.py` (~12 cases) — `AC_LLM_MOCK` 路径
- `tests/integration/test_ac_verifier.bats` (~7 cases) — `--skip` 路径
- `tests/integration/test_global_install_external_project.bats` (ac-verifier 相关 case) — 安装路径

### 6.4 CI 行为

- 默认跑 unit + integration,**不需要任何 API key**
- 真实 provider live test 用 `AC_LLM_LIVE_TESTS=yes` 显式开启(默认 OFF)
- 真实 key 通过 CI secret 注入,**永不**写入代码或日志

## 7. Migration Path

### Phase 1 (本 change)

1. 新建 `skills/ac-verifier/scripts/llm_providers/` 5 个文件 + `__init__.py`
2. 修改 `ac_verifier.py::invoke_ai_agent` 委托给 `llm_providers.get_provider().invoke()`
3. 新增 `tests/unit/test_ac_verifier_providers.py`
4. 新增 `tests/integration/test_ac_verifier_http_live.bats`
5. 更新 `skills/ac-verifier/SKILL.md` 新增 "Provider 配置" 节
6. 更新 `skills/ac-verifier/scripts/ac_verifier.sh` 头部注释(新增 env vars 文档)
7. 跑 `./test.sh --full --regression` — 必须全绿

### Phase 2 (后续 change, 可选)

- OpenAI/Anthropic 原生 JSON mode (`response_format` / tool use 模拟)
- `.rddf/project.yaml` `verification.provider: hook` 集成
- per-error-code 退避(401 不重试已实现,但 408/503 细分待加)
- 流式响应 / token 用量计费

## 8. Risks & Mitigations

| 风险 | 影响 | 缓解 |
|------|------|------|
| 现有 mock 测试被破坏 | 高 — 12 个 unit + 7 个 integration | `AC_LLM_MOCK` 分支放在 dispatcher 第一行,绝不进 provider;运行 `./test.sh --full --regression` |
| 引入 requests 改变环境 | 低 — 仓库已用 requests | 确认 `cross_repo_protocol` 已声明;若冲突,仅追加 version |
| MiniMax 无真实端点 | 中 — 用户配错会调错地方 | `default_base_url=""` 启动即报错,强制用户配置;无 fallback |
| Anthropic 协议不同 | 中 — 解析错误 | 独立 `_build_payload` + `_parse_response` override,已隔离 |
| 真实 API key 泄露到 git | 高 — 安全事故 | **永不**硬编码;env var 注入;CI 默认不走真实 provider;本设计文档不含 key 示例 |
| 单元测试 mock 不准确 | 中 — 测试通过但生产失败 | mock HTTP 行为贴近真实(provider 各自有 integration test);CI 跑 mock + live 两种 |

## 9. Dependencies

`requirements.txt` 变更:

```diff
 PyYAML>=6.0
 jsonschema>=4.0
 pytest>=7.0
 croniter>=2.0
+requests>=2.28
 ruff>=0.1
 mypy>=1.8
```

(若 `requests` 已声明,跳过;实施前先 grep `requirements.txt` 确认)

## 10. Out of Scope (explicit)

- ❌ 真实 MiniMax API 文档/端点 — placeholder 等用户提供
- ❌ Tool use / 多轮对话 — 单轮 JSON only(per brainstorming Q3)
- ❌ OpenAI/Anthropic JSON mode — Phase 2
- ❌ `.rddf/project.yaml` `verification.provider: hook` 集成 — Phase 2
- ❌ 真实 provider live CI — 仅本地 opt-in
- ❌ 流式响应 / token 计费 — Phase 2

## 11. Acceptance Criteria

- [ ] `AC_LLM_MOCK=yes` 行为完全不变(12 unit + 7 integration 全绿)
- [ ] `AC_LLM_PROVIDER=openai` 真实调用成功(用 test key 手动验证)
- [ ] `AC_LLM_PROVIDER=anthropic` 真实调用成功
- [ ] `AC_LLM_PROVIDER=ollama` 真实调用成功(本地 ollama server)
- [ ] `AC_LLM_PROVIDER=minimax` 启动时报错指引用户配置(无静默)
- [ ] `AC_LLM_PROVIDER=unknown` 报错并列出 valid providers
- [ ] 401 → exit 3,无重试
- [ ] 429 → 重试 3 次后 exit 3
- [ ] 5xx → 重试 3 次后 exit 3
- [ ] 网络断开 → 重试 3 次后 exit 3
- [ ] STRICT_AC_GATE / SKIP_AC_VERIFICATION / AC_LLM_TIMEOUT 行为不变
- [ ] `requests>=2.28` 已加入 requirements.txt(或确认已存在)
- [ ] SKILL.md 更新 Provider 配置节
- [ ] ac_verifier.sh header 注释更新 env vars
- [ ] `./test.sh --full --regression` 全绿(零新增失败)
- [ ] 单元测试覆盖率 ≥ 80% (`llm_providers/` 包)

## 12. References

- `ac_verifier.py:123-148` — 当前 stub
- `ac_verifier.py:170-220` — `parse_verdict` 不变
- `ac_verifier_mocks.py` — 现有 mock 行为参考
- `skills/ac-verifier/SKILL.md` — 用户文档
- ADR-0034 — rdd-verifier 5th phase
- ADR-0036 — `.rddf/project.yaml` 配置(本 change 不动,但涉及 verification.provider)
- `docs/change-quality-guide.md` — change 质量等级(本 change 至少 Silver)
