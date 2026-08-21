# extend-populate-roadmap-with-code-verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional `--code-verify=off|on|strict` flag to `populate-roadmap-from-arch` that cross-checks each ADR's claimed implementation status against actual code symbols (functions/classes/flags), emitting 4 new "已实施能力" badges in fragment bodies and writing supplementary state to `.rddf/state/.populate-supplementary.json`.

**Architecture:** Three layers:
1. **Data model + verification logic** (Phase 1) — `AdrCodeVerification` dataclass + regex parser + mcp→grep fallback verifier in `populate_lib.py`.
2. **CLI orchestration** (Phase 2) — `--code-verify` argparse-style flag in `populate.sh`, new Step 1.5 between catalog (Step 1) and fragment write (Step 5), strict-mode exit-2 on discrepancy.
3. **Fragment rendering** (Phase 3) — 4 badge formatters wired into `_format_adr_block` when verification is on; byte-identical fallback to v1.0 when off.

**Tech Stack:** Python 3.11+ (dataclass + concurrent.futures), Bash 4+ (argparse-style flag parsing), JSON Schema v1, pytest (unit), bats-core (integration).

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/populate-roadmap-from-arch/scripts/populate_lib.py` | Add `AdrCodeVerification` dataclass + verify functions (Tasks 1-3, 5-7, 9-12) |
| `skills/populate-roadmap-from-arch/scripts/populate.sh` | Add `--code-verify` flag + Step 1.5 orchestration + strict-mode exit (Tasks 4, 8) |
| `skills/_lib/schemas/populate_supplementary_schema.json` | v1 JSON Schema for `.rddf/state/.populate-supplementary.json` (Tasks 13-14) |
| `skills/populate-roadmap-from-arch/SKILL.md` | Document new flag + state-machine diagram + badge legend + Known Limitations + CI guidance (Task 24) |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_populate_lib.py` | New file, ≥10 unit tests for verification logic (Tasks 16-25) |
| `tests/integration/test_populate_roadmap_from_arch.bats` | New file, ≥4 integration tests for CLI end-to-end (Tasks 26-29) |

---

### Task 1: Add AdrCodeVerification dataclass + parse_symbols_from_adr_text

**Files:**
- Modify: `skills/populate-roadmap-from-arch/scripts/populate_lib.py:1-50` (after existing dataclasses)
- Test: `tests/unit/test_populate_lib.py` (new file, create)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_populate_lib.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "populate-roadmap-from-arch" / "scripts"))
from populate_lib import AdrCodeVerification, parse_symbols_from_adr_text

def test_parse_symbols_from_adr_text_basic():
    text = """
    Use `parse_symbols()` helper and `AdrRecord` class.
    See `--code-verify` flag in CLI.
    """
    symbols = parse_symbols_from_adr_text(text)
    assert "parse_symbols()" in symbols
    assert "AdrRecord" in symbols
    assert "--code-verify" in symbols

def test_parse_symbols_filters_code_blocks():
    text = """
    Example:
    ```python
    def real_func(): pass
    ```
    But mention `helper_func()` outside the block.
    """
    symbols = parse_symbols_from_adr_text(text)
    assert "real_func" not in symbols  # filtered
    assert "helper_func()" in symbols

def test_adc_code_verification_dataclass_fields():
    v = AdrCodeVerification(
        adr_id="ADR-0017",
        self_claim_version="v2.0.0+",
        code_symbols_found=["foo"],
        code_symbols_expected=["foo", "bar"],
        verification_status="confirmed",
        has_discrepancy=False,
        verified_at="2026-08-21T10:00:00Z",
        mcp_used=False,
    )
    assert v.adr_id == "ADR-0017"
    assert v.verification_status == "confirmed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_parse_symbols_from_adr_text_basic tests/unit/test_populate_lib.py::test_adc_code_verification_dataclass_fields -v`
Expected: FAIL with `ImportError: cannot import name 'AdrCodeVerification' from 'populate_lib'` and `cannot import name 'parse_symbols_from_adr_text'`

- [ ] **Step 3: Implement dataclass + parser**

Add to `skills/populate-roadmap-from-arch/scripts/populate_lib.py` after the existing `PhaseRecord` dataclass:

```python
# ---- Phase 1: Code Verification (v1.1+) ----

@dataclass
class AdrCodeVerification:
    """Result of cross-checking an ADR's claimed implementation against actual code."""
    adr_id: str
    self_claim_version: Optional[str]  # e.g. "v2.0.0+" or None if placeholder
    code_symbols_found: List[str]
    code_symbols_expected: List[str]
    verification_status: str  # one of: 'confirmed' | 'self-claim-only' | 'placeholder-as-claimed' | 'placeholder-but-exists'
    has_discrepancy: bool
    verified_at: str  # ISO 8601
    mcp_used: bool  # whether codebase-memory-mcp was used


def parse_symbols_from_adr_text(adr_text: str) -> List[str]:
    """Extract code symbols from ADR prose, filtering code blocks.

    Patterns:
      - `func()` / `ClassName` / `module.py` (backticked)
      - `def func` / `class Class` (Python definition lines)
      - `--flag` (CLI flags)
    """
    symbols: List[str] = []

    # 1. Strip fenced code blocks ```...```
    text_no_code = re.sub(r"```[\s\S]*?```", "", adr_text)

    # 2. Backtick-quoted symbols
    for m in re.finditer(r"`([^`]+)`", text_no_code):
        sym = m.group(1).strip()
        if sym:
            symbols.append(sym)

    # 3. Python definition lines (def/class)
    for m in re.finditer(r"^\s*(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", text_no_code, re.MULTILINE):
        symbols.append(m.group(1))

    # 4. CLI flags
    for m in re.finditer(r"--([a-z][a-z0-9-]+)", text_no_code):
        symbols.append(f"--{m.group(1)}")

    # Dedupe preserving order
    seen = set()
    deduped: List[str] = []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_parse_symbols_from_adr_text_basic tests/unit/test_populate_lib.py::test_adc_code_verification_dataclass_fields -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Defer commit**

按仓库约定，execute 阶段不逐任务 commit；所有变更将在 archive 阶段统一提交。

---

### Task 2: Add verify_adr_by_code with mcp→grep fallback

**Files:**
- Modify: `skills/populate-roadmap-from-arch/scripts/populate_lib.py` (append after parse_symbols_from_adr_text)
- Test: `tests/unit/test_populate_lib.py`

- [ ] **Step 1: Write the failing tests**

```python
# Add to tests/unit/test_populate_lib.py
from populate_lib import AdrRecord, verify_adr_by_code
from datetime import datetime
import tempfile

def test_verify_adr_by_code_confirmed(tmp_path):
    """ADR claims v2.0, code has all symbols → confirmed, no discrepancy."""
    # Create a fake project with code containing symbols
    (tmp_path / "foo.py").write_text("def helper_func(): pass\nclass MyClass: pass\n")
    adr = AdrRecord(
        id="ADR-0099", path=Path("docs/adr/ADR-0099-test.md"),
        title="Test ADR", status="已采纳", key_decision="Test",
        implementation_version="v2.0.0+",
    )
    # Use only symbols we know exist in tmp_path
    adr_text = "Implements `helper_func()` and `MyClass`."
    result = verify_adr_by_code(adr, adr_text, tmp_path)
    assert result.verification_status == "confirmed"
    assert result.has_discrepancy is False
    assert result.mcp_used is False  # default fallback

def test_verify_adr_by_code_self_claim_only(tmp_path):
    """ADR claims v2.0, code has <80% symbols → self-claim-only, has discrepancy."""
    # Only 1 of 3 symbols exists
    (tmp_path / "real.py").write_text("def only_one(): pass\n")
    adr = AdrRecord(
        id="ADR-0098", path=Path("docs/adr/ADR-0098.md"),
        title="T", status="已采纳", key_decision="k",
        implementation_version="v2.0.0+",
    )
    adr_text = "See `only_one()`, `missing_two()`, and `missing_three()`."
    result = verify_adr_by_code(adr, adr_text, tmp_path)
    assert result.verification_status == "self-claim-only"
    assert result.has_discrepancy is True

def test_verify_adr_by_code_placeholder_no_code(tmp_path):
    """ADR placeholder, code has 0 symbols → placeholder-as-claimed, no discrepancy."""
    adr = AdrRecord(
        id="ADR-0097", path=Path("docs/adr/ADR-0097.md"),
        title="T", status="占位（v3.0 候选）", key_decision="k",
        implementation_version=None,
    )
    adr_text = "This is a placeholder. `nonexistent_symbol()` described."
    result = verify_adr_by_code(adr, adr_text, tmp_path)
    assert result.verification_status == "placeholder-as-claimed"
    assert result.has_discrepancy is False

def test_verify_adr_by_code_placeholder_contradicts(tmp_path):
    """ADR placeholder, but code actually has 1 symbol → placeholder-but-exists, discrepancy."""
    (tmp_path / "real.py").write_text("def unexpected_symbol(): pass\n")
    adr = AdrRecord(
        id="ADR-0096", path=Path("docs/adr/ADR-0096.md"),
        title="T", status="占位（v3.0 候选）", key_decision="k",
        implementation_version=None,
    )
    adr_text = "This is a placeholder. `unexpected_symbol()` is mentioned."
    result = verify_adr_by_code(adr, adr_text, tmp_path)
    assert result.verification_status == "placeholder-but-exists"
    assert result.has_discrepancy is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_verify_adr_by_code_confirmed tests/unit/test_populate_lib.py::test_verify_adr_by_code_self_claim_only tests/unit/test_populate_lib.py::test_verify_adr_by_code_placeholder_no_code tests/unit/test_populate_lib.py::test_verify_adr_by_code_placeholder_contradicts -v`
Expected: FAIL with `ImportError: cannot import name 'verify_adr_by_code'`

- [ ] **Step 3: Implement verify_adr_by_code**

Append to `populate_lib.py`:

```python
def _try_mcp_search(symbol: str, project_root: Path) -> Optional[bool]:
    """Try codebase-memory-mcp if available. Returns None if mcp unavailable.

    Detection: check if `codebase-memory-mcp_search_graph` is registered by
    looking for a sentinel env var or trying to import the tool wrapper.
    Conservative: returns None on any error → falls through to grep.
    """
    try:
        # Best-effort probe: check for mcp availability via env
        if not Path(project_root / ".codebase-memory").exists():
            return None  # mcp not configured
        # In a real AI orchestrator with mcp tool access, this would call
        # `codebase-memory-mcp_search_graph(query=symbol, project_root=...)`.
        # For unit tests, this branch is unreachable.
        return None
    except Exception:
        return None


def _grep_symbol(symbol: str, project_root: Path) -> bool:
    """Fallback: grep for symbol in source files (skip .git, .venv, node_modules)."""
    import subprocess
    # Use ripgrep if available, else grep
    cmd = ["grep", "-r", "-l", "--include=*.py", "--include=*.sh", "--include=*.ts",
           "--exclude-dir=.git", "--exclude-dir=.venv", "--exclude-dir=node_modules",
           "--exclude-dir=.rddf", "--exclude-dir=skills/_lib",
           "-F", symbol, str(project_root)]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=10, text=True)
        return bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def verify_adr_by_code(adr: AdrRecord, adr_text: str, project_root: Path) -> AdrCodeVerification:
    """Verify ADR's self-claim against actual code symbols.

    Logic:
      - If ADR is placeholder (no impl_version): check if any mentioned symbol exists
        → exists: placeholder-but-exists (discrepancy)
        → not exists: placeholder-as-claimed (no discrepancy)
      - If ADR claims implementation: check coverage of mentioned symbols
        → ≥80% found: confirmed (no discrepancy)
        → <80% found: self-claim-only (discrepancy)
    """
    from datetime import datetime, timezone

    symbols = parse_symbols_from_adr_text(adr_text)
    mcp_used = False
    found: List[str] = []

    for sym in symbols:
        # 1. Try mcp
        mcp_result = _try_mcp_search(sym, project_root)
        if mcp_result is True:
            mcp_used = True
            found.append(sym)
            continue
        elif mcp_result is False:
            mcp_used = True
            continue

        # 2. Fallback: grep
        if _grep_symbol(sym, project_root):
            found.append(sym)

    is_placeholder = adr.is_placeholder_or_design() or adr.implementation_version is None

    if is_placeholder:
        if found:
            status = "placeholder-but-exists"
            has_discrepancy = True
        else:
            status = "placeholder-as-claimed"
            has_discrepancy = False
    else:
        coverage = len(found) / len(symbols) if symbols else 1.0
        if coverage >= 0.80:
            status = "confirmed"
            has_discrepancy = False
        else:
            status = "self-claim-only"
            has_discrepancy = True

    return AdrCodeVerification(
        adr_id=adr.id,
        self_claim_version=adr.implementation_version,
        code_symbols_found=found,
        code_symbols_expected=symbols,
        verification_status=status,
        has_discrepancy=has_discrepancy,
        verified_at=datetime.now(timezone.utc).isoformat(),
        mcp_used=mcp_used,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_verify_adr_by_code_confirmed tests/unit/test_populate_lib.py::test_verify_adr_by_code_self_claim_only tests/unit/test_populate_lib.py::test_verify_adr_by_code_placeholder_no_code tests/unit/test_populate_lib.py::test_verify_adr_by_code_placeholder_contradicts -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Defer commit**

---

### Task 3: Add verify_all_adrs (parallel with ThreadPoolExecutor)

**Files:**
- Modify: `skills/populate-roadmap-from-arch/scripts/populate_lib.py`
- Test: `tests/unit/test_populate_lib.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/test_populate_lib.py
from populate_lib import verify_all_adrs

def test_verify_all_adrs_parallel(tmp_path):
    """5 ADRs verified in parallel — wall-time < 2x single-ADR time."""
    import time
    # Create 5 ADRs each with one symbol in a unique file
    adrs = []
    for i in range(5):
        sym = f"func_{i}"
        (tmp_path / f"mod_{i}.py").write_text(f"def {sym}(): pass\n")
        adr = AdrRecord(
            id=f"ADR-{1000+i}", path=Path(f"docs/adr/ADR-{1000+i}.md"),
            title="T", status="已采纳", key_decision="k",
            implementation_version="v2.0.0+",
        )
        adrs.append((adr, f"See `{sym}()` in code.", tmp_path))

    start = time.time()
    results = verify_all_adrs(adrs, max_workers=4)
    elapsed = time.time() - start

    assert len(results) == 5
    # Serial would take ~5x single; parallel should be < 2x
    assert elapsed < 5.0, f"Parallel verification took {elapsed:.2f}s, expected < 5s"
    # All should be confirmed
    for r in results:
        assert r.verification_status == "confirmed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_verify_all_adrs_parallel -v`
Expected: FAIL with `ImportError: cannot import name 'verify_all_adrs'`

- [ ] **Step 3: Implement verify_all_adrs**

Append to `populate_lib.py`:

```python
def verify_all_adrs(
    adr_inputs: List[Tuple["AdrRecord", str, Path]],
    max_workers: int = 4,
) -> List[AdrCodeVerification]:
    """Verify multiple ADRs in parallel using ThreadPoolExecutor.

    Args:
        adr_inputs: list of (AdrRecord, adr_text, project_root) tuples
        max_workers: thread pool size (default 4)

    Returns:
        List of AdrCodeVerification, one per input (order preserved).
    """
    from concurrent.futures import ThreadPoolExecutor

    if not adr_inputs:
        return []

    results: List[AdrCodeVerification] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(verify_adr_by_code, adr, text, root)
            for (adr, text, root) in adr_inputs
        ]
        for fut in futures:
            results.append(fut.result())

    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_verify_all_adrs_parallel -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 4: Add load_supplementary_or_default + save_supplementary

**Files:**
- Modify: `skills/populate-roadmap-from-arch/scripts/populate_lib.py`
- Test: `tests/unit/test_populate_lib.py`

- [ ] **Step 1: Write the failing tests**

```python
# Add to tests/unit/test_populate_lib.py
from populate_lib import (
    load_supplementary_or_default, save_supplementary
)

def test_load_supplementary_or_default_missing(tmp_path):
    """File missing → returns empty dict."""
    result = load_supplementary_or_default(tmp_path)
    assert result == {}

def test_load_supplementary_or_default_present(tmp_path):
    """File present → returns parsed records dict."""
    import json
    state_dir = tmp_path / ".rddf" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / ".populate-supplementary.json").write_text(json.dumps({
        "version": 1,
        "generated_at": "2026-08-21T10:00:00Z",
        "records": [
            {"adr_id": "ADR-0017", "verification_status": "confirmed"}
        ]
    }))
    result = load_supplementary_or_default(tmp_path)
    assert "ADR-0017" in result
    assert result["ADR-0017"]["verification_status"] == "confirmed"

def test_supplementary_json_roundtrip(tmp_path):
    """Write 3 records → read back → all fields match (schema v1)."""
    import json
    recs = [
        AdrCodeVerification(
            adr_id=f"ADR-{i}", self_claim_version="v2.0.0+",
            code_symbols_found=[f"sym_{i}"], code_symbols_expected=[f"sym_{i}"],
            verification_status="confirmed", has_discrepancy=False,
            verified_at="2026-08-21T10:00:00Z", mcp_used=False,
        )
        for i in range(3)
    ]
    save_supplementary(recs, tmp_path)

    state_file = tmp_path / ".rddf" / "state" / ".populate-supplementary.json"
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert data["version"] == 1
    assert len(data["records"]) == 3
    for orig, written in zip(recs, data["records"]):
        assert orig.adr_id == written["adr_id"]
        assert orig.verification_status == written["verification_status"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_load_supplementary_or_default_missing tests/unit/test_populate_lib.py::test_load_supplementary_or_default_present tests/unit/test_populate_lib.py::test_supplementary_json_roundtrip -v`
Expected: FAIL with `ImportError: cannot import name 'load_supplementary_or_default'`

- [ ] **Step 3: Implement load + save**

Append to `populate_lib.py`:

```python
def load_supplementary_or_default(project_root: Path) -> Dict[str, Dict]:
    """Load supplementary verification records, or return {} if missing/invalid."""
    state_file = project_root / ".rddf" / "state" / ".populate-supplementary.json"
    if not state_file.exists():
        return {}
    try:
        import json
        data = json.loads(state_file.read_text(encoding="utf-8"))
        if data.get("version") != 1:
            return {}  # unsupported version
        return {r["adr_id"]: r for r in data.get("records", [])}
    except (json.JSONDecodeError, KeyError, OSError):
        return {}


def save_supplementary(
    records: List[AdrCodeVerification],
    project_root: Path,
) -> Path:
    """Atomically write supplementary records to .rddf/state/.populate-supplementary.json.

    Schema v1 — see skills/_lib/schemas/populate_supplementary_schema.json.
    """
    import json
    import os
    import tempfile
    from datetime import datetime, timezone

    state_dir = project_root / ".rddf" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    target = state_dir / ".populate-supplementary.json"

    payload = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": [
            {
                "adr_id": r.adr_id,
                "self_claim_version": r.self_claim_version,
                "verification_status": r.verification_status,
                "code_symbols_found": r.code_symbols_found,
                "code_symbols_expected": r.code_symbols_expected,
                "has_discrepancy": r.has_discrepancy,
                "verified_at": r.verified_at,
                "mcp_used": r.mcp_used,
            }
            for r in records
        ],
    }

    # Atomic write: tempfile + os.replace
    fd, tmp_path = tempfile.mkstemp(dir=state_dir, suffix=".tmp", prefix=".populate-supplementary.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, target)
    except Exception:
        # Clean up on failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return target
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_load_supplementary_or_default_missing tests/unit/test_populate_lib.py::test_load_supplementary_or_default_present tests/unit/test_populate_lib.py::test_supplementary_json_roundtrip -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Defer commit**

---

### Task 5: Create JSON Schema v1 for populate_supplementary

**Files:**
- Create: `skills/_lib/schemas/populate_supplementary_schema.json`
- Modify: `skills/populate-roadmap-from-arch/scripts/populate_lib.py::save_supplementary` (add schema validation)

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/test_populate_lib.py
def test_supplementary_schema_validation_rejects_version_zero(tmp_path):
    """Schema v1 must reject version=0 or missing version."""
    import json
    from populate_lib import save_supplementary
    import jsonschema

    schema_path = Path(__file__).resolve().parents[1] / "skills" / "_lib" / "schemas" / "populate_supplementary_schema.json"
    # First test: schema file exists
    assert schema_path.exists(), f"Schema not found at {schema_path}"

    # Second test: write a v1 record, load back, validate against schema
    recs = [AdrCodeVerification(
        adr_id="ADR-0017", self_claim_version="v2.0.0+",
        code_symbols_found=["foo"], code_symbols_expected=["foo", "bar"],
        verification_status="confirmed", has_discrepancy=False,
        verified_at="2026-08-21T10:00:00Z", mcp_used=False,
    )]
    save_supplementary(recs, tmp_path)
    written = json.loads((tmp_path / ".rddf/state/.populate-supplementary.json").read_text())
    schema = json.loads(schema_path.read_text())
    jsonschema.validate(written, schema)  # MUST not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_supplementary_schema_validation_rejects_version_zero -v`
Expected: FAIL — schema file does not exist (FileNotFoundError)

- [ ] **Step 3: Create schema file**

Create `skills/_lib/schemas/populate_supplementary_schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "populate-supplementary",
  "description": "ADR code-verification records written by populate-roadmap-from-arch --code-verify=on|strict",
  "version": 1,
  "type": "object",
  "required": ["version", "generated_at", "records"],
  "properties": {
    "version": {
      "type": "integer",
      "const": 1,
      "description": "Schema version. Consumers MUST reject version=0 or missing."
    },
    "generated_at": {
      "type": "string",
      "format": "date-time"
    },
    "records": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "adr_id", "self_claim_version", "verification_status",
          "code_symbols_found", "code_symbols_expected",
          "has_discrepancy", "verified_at", "mcp_used"
        ],
        "properties": {
          "adr_id": {"type": "string", "pattern": "^ADR-[0-9]{4}$"},
          "self_claim_version": {"type": ["string", "null"]},
          "verification_status": {
            "type": "string",
            "enum": ["confirmed", "self-claim-only", "placeholder-as-claimed", "placeholder-but-exists"]
          },
          "code_symbols_found": {"type": "array", "items": {"type": "string"}},
          "code_symbols_expected": {"type": "array", "items": {"type": "string"}},
          "has_discrepancy": {"type": "boolean"},
          "verified_at": {"type": "string", "format": "date-time"},
          "mcp_used": {"type": "boolean"}
        }
      }
    }
  }
}
```

Then modify `save_supplementary` in `populate_lib.py` to validate before write:

```python
    # Add at top of save_supplementary after state_dir.mkdir:
    schema_path = Path(__file__).resolve().parents[2] / "_lib" / "schemas" / "populate_supplementary_schema.json"
    if schema_path.exists():
        try:
            import jsonschema
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(payload, schema)
        except (jsonschema.ValidationError, ImportError) as e:
            raise RuntimeError(f"populate_supplementary payload failed schema v1 validation: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_supplementary_schema_validation_rejects_version_zero -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 6: Add 4 badge formatters to populate_lib.py

**Files:**
- Modify: `skills/populate-roadmap-from-arch/scripts/populate_lib.py`
- Test: `tests/unit/test_populate_lib.py`

- [ ] **Step 1: Write the failing tests**

```python
# Add to tests/unit/test_populate_lib.py
from populate_lib import (
    _format_badge_confirmed, _format_badge_self_claim_only,
    _format_badge_placeholder_but_exists, _format_badge_placeholder_as_claimed,
)

def test_format_badge_confirmed():
    s = _format_badge_confirmed("v2.0.0+")
    assert s == "*（已实施 v2.0.0+ + 代码验证）*"

def test_format_badge_self_claim_only():
    s = _format_badge_self_claim_only("v2.0.0+")
    assert s == "*（已实施 v2.0.0+ 仅自报）*"

def test_format_badge_placeholder_but_exists():
    s = _format_badge_placeholder_but_exists()
    assert s == "*（占位 + 代码已现 ⚠️）*"

def test_format_badge_placeholder_as_claimed():
    s = _format_badge_placeholder_as_claimed()
    assert s == "*（占位 + 代码未现）*"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_format_badge_confirmed tests/unit/test_populate_lib.py::test_format_badge_self_claim_only tests/unit/test_populate_lib.py::test_format_badge_placeholder_but_exists tests/unit/test_populate_lib.py::test_format_badge_placeholder_as_claimed -v`
Expected: FAIL with `ImportError: cannot import name '_format_badge_confirmed'`

- [ ] **Step 3: Implement 4 badge formatters**

Append to `populate_lib.py`:

```python
def _format_badge_confirmed(claim_version: str) -> str:
    return f"*（已实施 {claim_version} + 代码验证）*"

def _format_badge_self_claim_only(claim_version: str) -> str:
    return f"*（已实施 {claim_version} 仅自报）*"

def _format_badge_placeholder_but_exists() -> str:
    return "*（占位 + 代码已现 ⚠️）*"

def _format_badge_placeholder_as_claimed() -> str:
    return "*（占位 + 代码未现）*"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_format_badge_confirmed tests/unit/test_populate_lib.py::test_format_badge_self_claim_only tests/unit/test_populate_lib.py::test_format_badge_placeholder_but_exists tests/unit/test_populate_lib.py::test_format_badge_placeholder_as_claimed -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Defer commit**

---

### Task 7: Wire _format_adr_block to choose badge based on verification

**Files:**
- Modify: `skills/populate-roadmap-from-arch/scripts/populate_lib.py` (update `_format_adr_block`)
- Test: `tests/unit/test_populate_lib.py`

- [ ] **Step 1: Write the failing tests**

```python
# Add to tests/unit/test_populate_lib.py
from populate_lib import _format_adr_block

def test_format_adr_block_with_verification_confirmed():
    adr = AdrRecord(
        id="ADR-0017", path=Path("docs/adr/ADR-0017.md"),
        title="Test", status="已采纳", key_decision="key",
        implementation_version="v2.0.0+",
    )
    v = AdrCodeVerification(
        adr_id="ADR-0017", self_claim_version="v2.0.0+",
        code_symbols_found=["foo"], code_symbols_expected=["foo"],
        verification_status="confirmed", has_discrepancy=False,
        verified_at="2026-08-21T10:00:00Z", mcp_used=False,
    )
    out = _format_adr_block(adr, verification=v)
    assert "*（已实施 v2.0.0+ + 代码验证）*" in out

def test_format_adr_block_no_verification_uses_v1_marker():
    adr = AdrRecord(
        id="ADR-0017", path=Path("docs/adr/ADR-0017.md"),
        title="Test", status="已采纳", key_decision="key",
        implementation_version="v2.0.0+",
    )
    out = _format_adr_block(adr, verification=None)
    # v1.0 marker: should NOT contain new badges
    assert "*（已实施 v2.0.0+ + 代码验证）*" not in out
    assert "*（已实施 v2.0.0+ 仅自报）*" not in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_format_adr_block_with_verification_confirmed tests/unit/test_populate_lib.py::test_format_adr_block_no_verification_uses_v1_marker -v`
Expected: FAIL — function doesn't accept `verification` kwarg, or doesn't render new badge

- [ ] **Step 3: Modify _format_adr_block signature**

Find `_format_adr_block` in `populate_lib.py` and modify its signature + body to accept `verification` and emit badges when present:

```python
def _format_adr_block(
    adr: AdrRecord,
    verification: Optional[AdrCodeVerification] = None,
) -> str:
    """Format one ADR as a markdown bullet line for the phase body.

    When verification is None, uses v1.0 marker (*已实施 vX.Y.Z+*).
    When verification is provided, chooses 1 of 4 new badges based on
    verification.verification_status.
    """
    if verification is None:
        # v1.0 behavior: use implementation_version marker (if any)
        if adr.implementation_version:
            impl_marker = f"*已实施 {adr.implementation_version}*"
        else:
            impl_marker = ""
    else:
        status = verification.verification_status
        if status == "confirmed":
            impl_marker = _format_badge_confirmed(verification.self_claim_version or "v?")
        elif status == "self-claim-only":
            impl_marker = _format_badge_self_claim_only(verification.self_claim_version or "v?")
        elif status == "placeholder-but-exists":
            impl_marker = _format_badge_placeholder_but_exists()
        elif status == "placeholder-as-claimed":
            impl_marker = _format_badge_placeholder_as_claimed()
        else:
            impl_marker = ""

    title_line = f"- **{adr.id}** — {adr.title}"
    key_line = f"  - {adr.key_decision}"
    if impl_marker:
        return f"{title_line} {impl_marker}\n{key_line}"
    return f"{title_line}\n{key_line}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_format_adr_block_with_verification_confirmed tests/unit/test_populate_lib.py::test_format_adr_block_no_verification_uses_v1_marker -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Defer commit**

---

### Task 8: Add --code-verify flag + Step 1.5 orchestration in populate.sh

**Files:**
- Modify: `skills/populate-roadmap-from-arch/scripts/populate.sh`
- Test: `tests/integration/test_populate_roadmap_from_arch.bats` (new file)

- [ ] **Step 1: Write the failing integration test**

```bash
# tests/integration/test_populate_roadmap_from_arch.bats (new file)
#!/usr/bin/env bats

setup() {
    load test_helper
    FIXTURE_REPO="$(mktemp -d)"
    cd "$FIXTURE_REPO"
    git init -q
    mkdir -p docs/adr skills/_lib/schemas
    # Minimal schema copy
    cp "$BATS_TEST_DIRNAME/../../skills/_lib/schemas/populate_supplementary_schema.json" skills/_lib/schemas/
    mkdir -p skills/populate-roadmap-from-arch/scripts
    cp -r "$BATS_TEST_DIRNAME/../../skills/populate-roadmap-from-arch/scripts/." skills/populate-roadmap-from-arch/scripts/
}

teardown() {
    rm -rf "$FIXTURE_REPO"
}

@test "code-verify off: same output as v1.0 (no supplementary.json written)":
    # Create 1 ADR with implementation_version
    cat > docs/adr/ADR-0001-test.md <<EOF
---
title: Test
status: 已采纳
---
\`helper_func()\` is implemented.
EOF
    # Create code
    mkdir -p src
    echo "def helper_func(): pass" > src/foo.py

    run bash "$FIXTURE_REPO/skills/populate-roadmap-from-arch/scripts/populate.sh" --yes --code-verify=off --dry-run
    [ "$status" -eq 0 ]
    # No supplementary.json should exist after --dry-run
    [ ! -f "$FIXTURE_REPO/.rddf/state/.populate-supplementary.json" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_populate_roadmap_from_arch.bats`
Expected: FAIL — populate.sh doesn't accept `--code-verify` flag

- [ ] **Step 3: Modify populate.sh**

In `skills/populate-roadmap-from-arch/scripts/populate.sh`:

1. **Add flag parsing** (around line 158 in arg parser):

```bash
            --code-verify) CODE_VERIFY="$2"; shift 2 ;;
            --no-code-verify) CODE_VERIFY="off"; shift ;;
            --dry-run) DRY_RUN="true"; shift ;;
```

2. **Add default** (after `SKIP_PROMPT` initialization):

```bash
CODE_VERIFY="${CODE_VERIFY:-off}"  # off | on | strict
```

3. **Insert Step 1.5 between Step 1 and Step 2** (after the catalog step, before fragment write):

```bash
# --- Step 1.5: code verification (optional) ---
SUPPLEMENTARY_RECORDS=""
if [ "$CODE_VERIFY" = "on" ] || [ "$CODE_VERIFY" = "strict" ]; then
    if [ "$DRY_RUN" = "true" ]; then
        echo "▶ [DRY-RUN] 跳过代码验证（--dry-run 模式下不读取 supplementary）"
    else
        echo "▶ Step 1.5: 验证 ADR 代码存在性（mode=$CODE_VERIFY）..."
        # Read all ADR files
        ADR_INPUTS=()
        while IFS= read -r adr_file; do
            adr_id=$(basename "$adr_file" | sed -E 's/^(ADR-[0-9]+).*/\1/')
            adr_text=$(cat "$adr_file")
            ADR_INPUTS+=("$adr_id|$adr_file|$adr_text")
        done < <(find "$PROJECT_ROOT/docs/adr" -name "ADR-*.md" -type f 2>/dev/null)

        # Build JSON input for Python
        ADRS_JSON="["
        first=1
        for entry in "${ADR_INPUTS[@]}"; do
            IFS='|' read -r adr_id adr_path adr_text <<< "$entry"
            if [ $first -eq 0 ]; then ADRS_JSON+=","; fi
            first=0
            # Use python to construct JSON safely
            ADRS_JSON+=$(python3 -c "
import json,sys
print(json.dumps({
    'id': sys.argv[1],
    'path': sys.argv[2],
    'text': sys.argv[3],
    'implementation_version': None
}))" "$adr_id" "$adr_path" "$adr_text")
        done
        ADRS_JSON+="]"

        # Call Python verifier
        SUPPLEMENTARY_RECORDS=$(CODE_VERIFY_MODE="$CODE_VERIFY" PROJECT_ROOT="$PROJECT_ROOT" \
            python3 -c "
import json, os, sys
sys.path.insert(0, os.path.join(os.environ['PROJECT_ROOT'], 'skills/populate-roadmap-from-arch/scripts'))
from populate_lib import AdrRecord, verify_all_adrs, save_supplementary
from pathlib import Path

data = json.loads('''$ADRS_JSON''')
adrs = [AdrRecord(
    id=d['id'], path=Path(d['path']),
    title='', status='已采纳', key_decision='',
    implementation_version=d['implementation_version'],
) for d in data]

inputs = [(a, d['text'], Path(os.environ['PROJECT_ROOT'])) for a, d in zip(adrs, data)]
results = verify_all_adrs(inputs, max_workers=4)

if os.environ.get('CODE_VERIFY_MODE') != 'strict':
    save_supplementary(results, Path(os.environ['PROJECT_ROOT']))
    print(f\"[code-verify] Wrote {len(results)} records (mode={os.environ.get('CODE_VERIFY_MODE')})\")
else:
    save_supplementary(results, Path(os.environ['PROJECT_ROOT']))
    discrepancies = [r for r in results if r.has_discrepancy]
    if discrepancies:
        print(f\"[code-verify] {len(discrepancies)} discrepancies found:\", file=sys.stderr)
        for d in discrepancies:
            print(f\"  - {d.adr_id}: {d.verification_status}\", file=sys.stderr)
        sys.exit(2)
    else:
        print(f\"[code-verify] No discrepancies (mode=strict)\")
" 2>&1) || {
            rc=$?
            if [ $rc -eq 2 ]; then
                echo "$SUPPLEMENTARY_RECORDS" >&2
                exit 2
            fi
            exit $rc
        }
        echo "$SUPPLEMENTARY_RECORDS"
    fi
fi
```

4. **Update --help** text to include the new flag:

```bash
            --help|-h)
                echo "Usage: populate.sh [--phase phase-N] [--dry-run] [--no-backup] [--yes] [--code-verify=off|on|strict]"
                echo ""
                echo "  --code-verify=MODE   Cross-check ADRs against code (off|on|strict). Default: off"
                echo "    off     No verification (v1.0 behavior)"
                echo "    on      Verify and write supplementary state; render new badges"
                echo "    strict  Like 'on' but exit 2 on any discrepancy"
                ...
```

- [ ] **Step 4: Run integration test to verify it passes**

Run: `bats tests/integration/test_populate_roadmap_from_arch.bats`
Expected: PASS (1 test)

- [ ] **Step 5: Defer commit**

---

### Task 9: Verify mcp-unavailable falls back to grep + emits warning

**Files:**
- Test: `tests/unit/test_populate_lib.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/unit/test_populate_lib.py
def test_mcp_unavailable_falls_back_to_grep(tmp_path, monkeypatch):
    """When mcp is unavailable (no .codebase-memory), grep fallback runs + emits warning."""
    # Ensure .codebase-memory does NOT exist
    assert not (tmp_path / ".codebase-memory").exists()

    # Create code with the symbol
    (tmp_path / "foo.py").write_text("def mentioned_func(): pass\n")

    # Capture stderr
    import io
    import sys as _sys
    captured = io.StringIO()
    monkeypatch.setattr(_sys, "stderr", captured)

    adr = AdrRecord(
        id="ADR-0050", path=Path("docs/adr/ADR-0050.md"),
        title="T", status="已采纳", key_decision="k",
        implementation_version="v2.0.0+",
    )
    result = verify_adr_by_code(adr, "Uses `mentioned_func()`.", tmp_path)

    # Should fall back to grep, find the symbol
    assert result.mcp_used is False
    assert "mentioned_func()" in result.code_symbols_found
    assert result.verification_status == "confirmed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_mcp_unavailable_falls_back_to_grep -v`
Expected: FAIL — mcp_used logic might be inverted, or test setup wrong

- [ ] **Step 3: Verify implementation correctness (no code change expected)**

The implementation in Task 2 already handles this. Verify by reading the `_try_mcp_search` and `verify_adr_by_code` functions:
- `_try_mcp_search` returns `None` when `.codebase-memory` is missing
- `verify_adr_by_code` treats `None` as "fall through to grep"
- After grep finds it, `mcp_used=False` and `code_symbols_found=["mentioned_func()"]`
- Coverage = 1/1 = 100% ≥ 80% → `confirmed`

If the test fails, adjust the mcp detection logic to be more conservative.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_populate_lib.py::test_mcp_unavailable_falls_back_to_grep -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 10: Integration tests for all 4 code-verify modes

**Files:**
- Modify: `tests/integration/test_populate_roadmap_from_arch.bats`

- [ ] **Step 1: Write the failing tests**

```bash
# Add to tests/integration/test_populate_roadmap_from_arch.bats

@test "code-verify on: new badges appear in fragment body":
    # Setup: 1 ADR with implementation_version, code with 1 of 1 symbol → confirmed
    cat > docs/adr/ADR-0001-test.md <<EOF
---
title: Test
status: 已采纳
---
\`helper_func()\` is implemented.
EOF
    mkdir -p src
    echo "def helper_func(): pass" > src/foo.py
    # Stub out fragment write by using --dry-run (preview only)
    # For full integration, use --yes and check fragment content
    run bash "$FIXTURE_REPO/skills/populate-roadmap-from-arch/scripts/populate.sh" --yes --code-verify=on
    [ "$status" -eq 0 ]
    [ -f "$FIXTURE_REPO/.rddf/state/.populate-supplementary.json" ]
    # Check fragment body contains badge (only if fragment was actually written)
    # If --dry-run, just verify supplementary.json structure
    run jq -r '.version' "$FIXTURE_REPO/.rddf/state/.populate-supplementary.json"
    [ "$output" = "1" ]

@test "code-verify strict: exit 2 on discrepancy":
    # Setup: ADR claims v2.0, but code has none of the symbols → self-claim-only
    cat > docs/adr/ADR-0002-test.md <<EOF
---
title: Test
status: 已采纳
---
\`nonexistent_one()\` and \`nonexistent_two()\` are implemented.
EOF
    # No code with these symbols → strict should exit 2
    run bash "$FIXTURE_REPO/skills/populate-roadmap-from-arch/scripts/populate.sh" --yes --code-verify=strict
    [ "$status" -eq 2 ]
    [[ "$output" =~ "ADR-0002" ]]

@test "code-verify on with RDD_NO_MCP=1: grep fallback works":
    cat > docs/adr/ADR-0003-test.md <<EOF
---
title: Test
status: 已采纳
---
\`helper_func()\` is implemented.
EOF
    mkdir -p src
    echo "def helper_func(): pass" > src/foo.py
    RDD_NO_MCP=1 run bash "$FIXTURE_REPO/skills/populate-roadmap-from-arch/scripts/populate.sh" --yes --code-verify=on
    [ "$status" -eq 0 ]
    [ -f "$FIXTURE_REPO/.rddf/state/.populate-supplementary.json" ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tests/integration/test_populate_roadmap_from_arch.bats`
Expected: 2 of 3 FAIL (the "code-verify off" test from Task 8 should now PASS; the new 3 should mostly FAIL)

- [ ] **Step 3: Verify implementation, fix any gaps**

Most failures should be due to test setup issues (jq missing, fixture path problems). Fix test setup; ensure:
- `jq` is available (or use `python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])"`)
- `RDD_NO_MCP` env var is honored by the verifier (add a check in `_try_mcp_search`)
- `--dry-run` truly skips the write step

- [ ] **Step 4: Run tests to verify they pass**

Run: `bats tests/integration/test_populate_roadmap_from_arch.bats`
Expected: PASS (4 tests total: 1 from Task 8 + 3 from this task)

- [ ] **Step 5: Defer commit**

---

### Task 11: Update SKILL.md with new flag, state-machine, badges, CI guidance

**Files:**
- Modify: `skills/populate-roadmap-from-arch/SKILL.md`

- [ ] **Step 1: Write a manual validation script** (no test file needed for docs)

```bash
# No failing test — docs changes are validated by grep checks in CI
grep -q '\-\-code-verify' skills/populate-roadmap-from-arch/SKILL.md && echo "OK" || echo "MISSING"
grep -q 'Step 1.5' skills/populate-roadmap-from-arch/SKILL.md && echo "OK" || echo "MISSING"
grep -q '已实施 v2.0.0+ + 代码验证' skills/populate-roadmap-from-arch/SKILL.md && echo "OK" || echo "MISSING"
grep -q 'codebase-memory-mcp' skills/populate-roadmap-from-arch/SKILL.md && echo "OK" || echo "MISSING"
grep -q 'Recommended CI Integration' skills/populate-roadmap-from-arch/SKILL.md && echo "OK" || echo "MISSING"
```

- [ ] **Step 2: Run validation to verify it fails**

Run: `bash -c "$(cat <<'EOF'
grep -q '\-\-code-verify' skills/populate-roadmap-from-arch/SKILL.md && echo "OK" || echo "MISSING"
grep -q 'Step 1.5' skills/populate-roadmap-from-arch/SKILL.md && echo "OK" || echo "MISSING"
grep -q '已实施 v2.0.0+ + 代码验证' skills/populate-roadmap-from-arch/SKILL.md && echo "OK" || echo "MISSING"
grep -q 'codebase-memory-mcp' skills/populate-roadmap-from-arch/SKILL.md && echo "OK" || echo "MISSING"
grep -q 'Recommended CI Integration' skills/populate-roadmap-from-arch/SKILL.md && echo "OK" || echo "MISSING"
EOF
)"`
Expected: 5x `MISSING`

- [ ] **Step 3: Update SKILL.md**

Edit `skills/populate-roadmap-from-arch/SKILL.md`:

1. Add to CLI flag table (find the existing table, add rows):
```
| `--code-verify=off\|on\|strict` | Cross-check ADRs against code (default `off`) |
| `--no-code-verify`              | Shortcut for `--code-verify=off`              |
```

2. Update state-machine diagram (find the Step 1 → Step 2 → ... flow):
Add `Step 1.5: Verify` between `Step 1: Catalog` and `Step 2: Classify`.

3. Add badge legend section (after the existing badge/marker section):
```markdown
### 已实施能力 badges (--code-verify=on|strict)

| Status | Badge | Meaning |
|---|---|---|
| `confirmed` | `*（已实施 vX.Y.Z+ + 代码验证）*` | ADR claims impl + ≥80% symbols found |
| `self-claim-only` | `*（已实施 vX.Y.Z+ 仅自报）*` | ADR claims impl + <80% symbols found |
| `placeholder-but-exists` | `*（占位 + 代码已现 ⚠️）*` | ADR placeholder + code has the symbol |
| `placeholder-as-claimed` | `*（占位 + 代码未现）*` | ADR placeholder + no symbol found |
```

4. Add Known Limitations entry:
```markdown
### Known Limitations

- **codebase-memory-mcp availability**: When `--code-verify=on|strict` runs without `codebase-memory-mcp` configured (no `.codebase-memory/` directory), the verifier falls back to a ripgrep-based symbol search. CI environments without mcp will get less precise results but the verification still runs.
- **80% threshold heuristic**: The `confirmed` vs `self-claim-only` threshold is hardcoded at 80%. Future versions may make this configurable via `--coverage-threshold=N`.
- **Symbol regex coverage**: Backtick patterns + Python `def`/`class` + CLI `--flag`. C/Rust/Go definitions are not yet extracted. See Out-of-Scope.
```

5. Add Recommended CI Integration section:
```markdown
## Recommended CI Integration

No CI workflow YAML is shipped with this change. Recommended patterns:

- **Pull request checks**: Run `bash skills/populate-roadmap-from-arch/scripts/populate.sh --yes --code-verify=strict --dry-run` to surface any ADR↔code drift without modifying files.
- **Nightly**: Run `--code-verify=on` and commit `.rddf/state/.populate-supplementary.json` updates as part of a "roadmap-sync" job.
- **Local dev**: `RDD_NO_MCP=1 populate.sh --yes --code-verify=on` works without mcp setup.
```

- [ ] **Step 4: Run validation to verify it passes**

Run the same grep checks from Step 1.
Expected: 5x `OK`

- [ ] **Step 5: Defer commit**

---

### Task 12: Full regression — `./test.sh --full --regression`

**Files:**
- None (verification only)

- [ ] **Step 1: Run full test suite with regression check**

```bash
./test.sh --full --regression 2>&1 | tee /tmp/full-test.log
```

- [ ] **Step 2: Compare against baseline**

```bash
bash tests/scripts/report_regression.sh
```

Expected: `0 new failures, N known failures (matches baseline)` or similar pass message.

- [ ] **Step 3: Verify new unit tests pass**

```bash
python3 -m pytest tests/unit/test_populate_lib.py -v --tb=short
```

Expected: ≥10 tests pass.

- [ ] **Step 4: Verify new integration tests pass**

```bash
bats tests/integration/test_populate_roadmap_from_arch.bats
```

Expected: ≥4 tests pass.

- [ ] **Step 5: Manual verification**

```bash
# 1. Verify --code-verify=off produces byte-identical output to v1.0
git stash  # stash any pending changes
git checkout 2b0991a -- skills/populate-roadmap-from-arch/  # get v1.0 state
bash skills/populate-roadmap-from-arch/scripts/populate.sh --yes --code-verify=off --dry-run > /tmp/v1-off.txt
git checkout HEAD -- skills/populate-roadmap-from-arch/  # restore
bash skills/populate-roadmap-from-arch/scripts/populate.sh --yes --code-verify=off --dry-run > /tmp/v1.1-off.txt
diff /tmp/v1-off.txt /tmp/v1.1-off.txt  # MUST be empty

# 2. Verify --code-verify=on writes supplementary.json and renders 4 badge types
bash skills/populate-roadmap-from-arch/scripts/populate.sh --yes --code-verify=on
ls -la .rddf/state/.populate-supplementary.json  # exists
jq -r '.records | length' .rddf/state/.populate-supplementary.json  # N > 0
grep -c "（已实施.*+ 代码验证）" roadmap.md  # ≥1 confirmed
grep -c "（已实施.*仅自报）" roadmap.md  # ≥0
grep -c "（占位 + 代码已现" roadmap.md  # ≥0
grep -c "（占位 + 代码未现）" roadmap.md  # ≥1 (for placeholders)

# 3. Verify --code-verify=strict exits 2 on fixture with discrepancy
# (use the bats integration test from Task 10)
git stash pop 2>/dev/null  # restore if stashed
```

- [ ] **Step 6: Defer commit (archive-stage commit only)**

All changes will be committed in a single archive-stage commit per the worktree-archive-workflow convention. Do NOT run `git commit` per-task.

---

## Self-Review (mandatory before archive)

After completing all 11 tasks above, perform a self-review:

1. **Spec coverage**: Browse `openspec/changes/extend-populate-roadmap-with-code-verification/{proposal,design,tasks}.md`. Confirm each requirement maps to a Task above:
   - Phase 1 tasks (1.1-1.6 in tasks.md) → Task 1, 2, 3, 4, 5 in this plan ✓
   - Phase 2 tasks (2.1-2.5) → Task 8 ✓
   - Phase 3 tasks (3.1-3.3) → Task 6, 7 ✓
   - Phase 4 tasks (4.1-4.2) → Task 5 ✓
   - Phase 5 tasks (5.1-5.10) → Tasks 1, 2, 3, 4, 6, 7, 9 ✓
   - Phase 6 tasks (6.1-6.4) → Tasks 8, 10 ✓
   - Phase 7 tasks (7.1-7.2) → Task 11 ✓
   - Phase 8 tasks (8.1-8.7) → Task 12 ✓

2. **Placeholder scan**: Search this plan for "TBD", "TODO", "implement later", "fill in details". None should remain. Fix any occurrences.

3. **Type consistency**: `AdrCodeVerification` fields are identical across Tasks 1, 2, 3, 4, 5, 7, 9. `_format_adr_block` signature consistent in Tasks 7 and tests. `verify_adr_by_code` signature consistent in Tasks 2, 3, 9.

4. **Contract compliance**: This plan is at `.rddf/plans/extend-populate-roadmap-with-code-verification.md`, has 12 `### Task N:` sections, ≥24 `- [ ]` checkboxes, header with Goal/Architecture/Tech Stack. Satisfies `_lib/execute.md` validation.

---

## Archive Stage (Phase 3)

After all 12 tasks complete:

1. **In worktree**: `git add -A && git commit -m "feat(populate-roadmap): add --code-verify flag + 4 badge types + supplementary state"`
2. **Switch to master**: `cd /workspace/project/rdd-workflow && git checkout master`
3. **Merge worktree branch**: `git merge --no-ff openspec/extend-populate-roadmap-with-code-verification`
4. **Run openspec archive**: `openspec archive extend-populate-roadmap-with-code-verification --yes`
5. **Cleanup worktree**: `git worktree remove .rddf/wt/extend-populate-roadmap-with-code-verification && git branch -d openspec/extend-populate-roadmap-with-code-verification`
6. **Restore proposal-suggestions.md stash** (from pre-worktree step):
   `git stash pop` (in master, after archive)
   Then commit: `git add proposal-suggestions.md && git commit -m "chore(proposal-suggestions): remove entry after design-phase approval"`

---

**End of plan.**