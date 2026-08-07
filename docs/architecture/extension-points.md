# Extension Points

This doc is for contributors. It captures the **how** for the most common extension operations: adding a skill, a detector/action, a CLI subcommand, or an ADR. Each operation has a checklist.

## Adding a New Skill

Skills are first-class extensions — the project ships 17 and grows over time.

**Checklist**:

1. **Pick a name** that is unique, kebab-case, descriptive (`guide-arch`, `add-improve`, `rdd-env-check`).
2. **Copy the frontmatter** from a similar skill (e.g. `skills/<existing-skill>/SKILL.md`). Fill in `name`, `description`, `license`, `compatibility`, and `metadata.{author, version, evolved-from, user-invocable}`. Set `version: 1.0` for new skills.
3. **Write the body** following the "state machine" pattern: numbered phases, each with a clear gate. Match the style of `skills/guide-arch/SKILL.md`.
4. **Add `scripts/`** under the skill dir if any block exceeds ~50 lines (ADR-0021). Bash + Python mixed, with `*.sh` orchestrators and `*.py` business logic. Each script is wrapped in a `main()` function.
5. **Write tests** in `tests/integration/test_<skill>.bats` (bats for shell) or `tests/unit/test_<module>.py` (pytest for Python).
6. **Register in install.sh** if the skill needs project-wide discovery (mostly for skills that aren't auto-discovered).
7. **Update this doc** — add a row to the module map in [overview.md](overview.md) and link to the new SKILL.md in [skills-and-handoff.md](skills-and-handoff.md).
8. **Add an ADR** if the new skill introduces a structural change (new contract, new handoff file, new gate).

**Don't**:
- Don't edit frontmatter after first commit to "rebrand" — bump `version`.
- Don't add `depends_on` between skills — keep skills independent; coordination is via handoff files.
- Don't reach into another skill's `scripts/` — call the skill instead, or use `_lib/`.

## Adding a New Detector / Action (Loop Engine Plugin)

Detectors and actions are pluggable units in the Loop engine. They live in `_lib/loop/` or `_lib/plugins/`.

**Detector** — observes state, returns a signal (e.g. "tasks are stale", "config drifted").

```python
# _lib/loop/detectors/my_detector.py
from .base import Detector

class MyDetector(Detector):
    name = "my-detector"

    def detect(self, state) -> Signal:
        if state.get("foo") > 10:
            return Signal(level="warning", message="foo too high")
        return Signal(level="ok")
```

**Action** — performs a side-effect in response to a signal (e.g. "open issue", "send notification").

```python
# _lib/loop/actions/my_action.py
from .base import Action

class MyAction(Action):
    name = "my-action"

    def run(self, signal, state) -> Result:
        # do work
        return Result(ok=True, message="did the thing")
```

**Checklist**:

1. Subclass the appropriate base (`Detector` / `Action`).
2. Set a unique `name`.
3. Register in the plugin loader (`_lib/loop/plugin_loader.py`).
4. Add a unit test in `tests/unit/test_<name>.py` (TDD).
5. Document the signal contract (what level, what payload).

## Adding a New `rddf` CLI Subcommand

The CLI is a thin wrapper: each subcommand maps to one function in `_lib/cli/`. The available command modules are dispatched through `_lib/cli/__init__.py` and `_lib/cli/__main__.py`.

**Checklist**:

1. Add a new file `_lib/cli/<subcommand>_cmd.py` exposing `def main(argv: list[str]) -> int`, matching the existing `*_cmd.py` modules.
2. Register the subcommand in `_lib/cli/__init__.py` dispatch and expose it from `_lib/cli/__main__.py` when required.
3. Update the installed `rddf` entry point only if the command requires packaging or launcher changes; ordinary subcommands are routed by the existing CLI entry point.
4. Add a smoke test in `tests/integration/test_rddf_<subcommand>.bats`.
5. Update [overview.md](overview.md) module map.

**Don't**:
- Don't put business logic in the CLI layer — call into `_lib/`.

## Adding a New ADR

ADRs are immutable historical records. They are the most-leverage docs in the project because every other doc references them.

**Checklist**:

1. **Find the next number**: `ls docs/adr/ADR-*.md | sort | tail -1` — increment by 1 (e.g. `ADR-0026`).
2. **Copy `docs/adr/ADR-0000-template.md`** to `docs/adr/ADR-NNNN-<kebab-slug>.md`.
3. **Fill in**: Context, Decision, Status (set to `待定`), Consequences.
4. **Add a row** to `docs/adr/README.md` ADR list table (status = 待定).
5. **Reference it** from any other doc that should cite the decision.
6. **Commit** with message `docs(adr): propose ADR-NNNN <slug>`.
7. **After review**, edit status to `已采纳` or `已替代为 ADR-NNN` and update the row in `docs/adr/README.md`.

**Don't**:
- Don't renumber an existing ADR — links break across the whole repo.
- Don't edit an ADR's body to reflect new code — write a new ADR that supersedes it.

## Adding a New Handoff File

Rare; only when a new phase boundary emerges.

**Checklist**:

1. Define a JSON schema in `_lib/schemas/<name>_schema.json`.
2. Add a writer function in the phase that produces the handoff.
3. Add a reader + version-check in the phase that consumes it.
4. Add a migration entry if any existing data needs to be back-filled.
5. Document the schema in [skills-and-handoff.md](skills-and-handoff.md).
6. Add an ADR (per "Adding a New ADR" above).

## Cross-references

- Skills protocol: [skills-and-handoff.md](skills-and-handoff.md)
- Loop engine: [loop-engine.md](loop-engine.md) — for detector/action context.
- ADR index: `../adr/README.md`.
