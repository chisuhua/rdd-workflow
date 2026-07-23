# add-heartbeat-config Implementation Plan

**Goal:** Make `DEFAULT_HEARTBEAT_TIMEOUT_SECONDS` and `HEARTBEAT_REFRESH_THRESHOLD_SECONDS` configurable via environment variables.

**Architecture:** Thread config values from `RddfSessionCoordinator.__init__` → `RddfSessionCommands` instance attributes → used in `check_heartbeat_timeouts()`.

**Tech Stack:** Python 3.11+, os.environ

---

### Task 1: Add env var parsing to `_types.py` + thread through facade

**Files:**
- Modify: `skills/rddf-session/scripts/rddf_session_pkg/_types.py:12-13`
- Test: existing tests

- [ ] **Step 1: Read current code** — confirm `DEFAULT_HEARTBEAT_TIMEOUT_SECONDS` and `HEARTBEAT_REFRESH_THRESHOLD_SECONDS` are module-level constants in `_types.py`

- [ ] **Step 2: Add `heartbeat_config` dataclass + env var parsing + test**

In `_types.py`, add:

```python
import os

@dataclass
class HeartbeatConfig:
    """Configurable heartbeat threshold, parsed from env vars."""
    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS
    refresh_threshold_seconds: int = HEARTBEAT_REFRESH_THRESHOLD_SECONDS

    @staticmethod
    def from_env() -> "HeartbeatConfig":
        timeout = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS
        threshold = HEARTBEAT_REFRESH_THRESHOLD_SECONDS

        raw = os.environ.get("RDDF_HEARTBEAT_TIMEOUT_SECONDS", "")
        if raw:
            try:
                parsed = int(raw)
                if parsed > 0:
                    timeout = parsed
            except ValueError:
                pass  # illegal value → fall back to default

        raw = os.environ.get("RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS", "")
        if raw:
            try:
                parsed = int(raw)
                if parsed > 0:
                    threshold = parsed
            except ValueError:
                pass

        return HeartbeatConfig(timeout_seconds=timeout, refresh_threshold_seconds=threshold)
```

- [ ] **Step 3: Thread config through facade + commands**

In `rddf_session.py` (facade):
```python
def __init__(self, sessions_file: str, config: Optional[HeartbeatConfig] = None):
    self._store = RddfSessionStore(sessions_file)
    self._commands = RddfSessionCommands(self._store, config or HeartbeatConfig())
    self._binding = RddfSessionBinding(self._store)
```

In `_commands.py`:
```python
def __init__(self, store: RddfSessionStore, config: HeartbeatConfig):
    self._store = store
    self._config = config

# In check_heartbeat_timeouts, replace:
#   DEFAULT_HEARTBEAT_TIMEOUT_SECONDS
# with:
#   self._config.timeout_seconds
```

- [ ] **Step 4: Run tests to verify**

Run: `python3 -m pytest tests/ -x -q --tb=short -k "rddf" 2>&1 | tail -5`
Expected: all rddf tests pass

- [ ] **Step 5: Commit**

```bash
git add skills/rddf-session/scripts/rddf_session.py skills/rddf-session/scripts/rddf_session_pkg/_commands.py skills/rddf-session/scripts/rddf_session_pkg/_types.py
git commit -m "feat(rddf-session): add configurable heartbeat timeout via env vars"
```

---

### Task 2: Add tests for env var config

**Files:**
- Modify: `tests/unit/test_rddf_session.py` — add new test methods

- [ ] **Step 1: Add test_default_config**

```python
def test_default_config(self):
    """Default HeartbeatConfig values match module constants."""
    config = HeartbeatConfig()
    assert config.timeout_seconds == 1800
    assert config.refresh_threshold_seconds == 300
```

- [ ] **Step 2: Add test_env_var_override**

```python
@mock.patch.dict(os.environ, {"RDDF_HEARTBEAT_TIMEOUT_SECONDS": "3600", "RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS": "600"})
def test_env_var_override(self):
    config = HeartbeatConfig.from_env()
    assert config.timeout_seconds == 3600
    assert config.refresh_threshold_seconds == 600
```

- [ ] **Step 3: Add test_illegal_env_fallback**

```python
@mock.patch.dict(os.environ, {"RDDF_HEARTBEAT_TIMEOUT_SECONDS": "invalid", "RDDF_HEARTBEAT_REFRESH_THRESHOLD_SECONDS": "0"})
def test_illegal_env_fallback(self):
    config = HeartbeatConfig.from_env()
    assert config.timeout_seconds == 1800  # fell back to default
    assert config.refresh_threshold_seconds == 300  # fell back to default
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/unit/test_rddf_session.py -x -q --tb=short 2>&1 | tail -5`
Expected: 27 passed (24 original + 3 new)

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_rddf_session.py
git commit -m "test(rddf-session): add 3 tests for HeartbeatConfig env var parsing"
```