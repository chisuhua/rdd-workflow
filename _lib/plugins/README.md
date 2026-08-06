# Gate Mechanism Plugins

Custom gate checks for the rdd-workflow v2 phase-transition gate. Plugins let you
add organization- or project-specific validation without modifying core code.

## Writing a Plugin

A plugin is a Python module that calls `register_gate_check()` with one or more
`Check` namedtuples. Place it anywhere on the Python path, or under
`skills/_lib/plugins/` (this directory).

### Minimal Example

```python
# my_plugin.py
from skills._lib.gate import Check, register_gate_check


def _check_team_owns_change(ctx):
    """Require a CODEOWNERS entry for the active change directory."""
    sv = ctx.get("state_vector")
    if sv is None:
        return (True, None)
    active = sv.get_field("arch_side.current_change")
    if not active:
        return (True, None)
    import os
    return (os.path.isfile(".github/CODEOWNERS"), None)


register_gate_check(Check(
    name="team_owns_change",
    condition=_check_team_owns_change,
    message="No CODEOWNERS file",
    suggestion="Create .github/CODEOWNERS: echo '* @your-team' > .github/CODEOWNERS",
))
```

### Loading Plugins

The gate loads plugins from any `.py` file under `skills/_lib/plugins/`. To use
plugins, ensure they are imported before constructing the `GateMechanism`:

```python
# In your entrypoint
import skills._lib.plugins.my_plugin  # noqa: F401  (triggers registration)

from skills._lib.gate import GateMechanism
gate = GateMechanism(load_defaults=True)
```

## Check Contract

A check is a `Check` namedtuple with five fields:

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Unique identifier (no spaces). Recorded in events. |
| `condition` | `Callable[[dict], tuple[bool, str | None]]` | Returns `(passed, severity)`. `severity` is `"error"` (blocks) or `"warning"` (allows with notice). |
| `message` | `str` | Human-readable explanation shown on failure. |
| `suggestion` | `str` | Concrete next step, ideally with a shell command. |
| `severity` | `str` | Documented default; actual severity returned by `condition`. |

The `condition` callable receives a `context` dict containing:
- `state_vector`: the loaded `StateVector` instance
- Any additional keys passed to `verify_transition(transition, context)`

## Best Practices

- Make check names lowercase with underscores.
- Always return a tuple, never raise from `condition` (caller wraps exceptions).
- Provide actionable suggestions — they appear verbatim in the user's terminal.
- Use `warning` severity for soft checks (advisory); `error` for hard blocks.
- Test your plugin: see `tests/unit/test_gate.py::test_plugin_register_via_public_api`.
