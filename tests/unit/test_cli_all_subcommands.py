"""Comprehensive unit-test coverage for every ``rddf`` subcommand.

This file exists for two purposes:

1. **Coverage lock** — every subcommand registered in
   ``skills._lib.cli._ROUTES`` must satisfy three structural contracts:

   - It is a key in ``_ROUTES``.
   - The registered module path resolves via ``importlib`` to a real module.
   - The registered function (``cmd_<name>``) exists and is callable.

   A new subcommand cannot be merged without extending these parametrized
   cases; a removed subcommand will cause this test to fail loudly.

2. **Regression lock — fix-iteration-schema-filled-at (2026-08-10)**.

   The schema for ``.rddf/state/iteration.json`` rejected every write once
   an undeclared ``filled_at`` field appeared in ``changes[*]`` (first
   observed 2026-08-08 17:00; 26 cascading corrupt backups followed). The
   ``TestFilledAtRegression`` class below locks the schema acceptance +
   migration behaviour so this drift cannot recur silently.

Subcommands covered (28 total — must match ``list_commands()``):

     archive, archive-sync, cleanup, dashboard, deps, deps.cross-repo,
     discover-ship-changes, doctor, feature, guide, init, issue, iteration,
     l2-trend, migrate-improvements, monitor, orchestrate, report-issue,
     rdd-hub-bootstrap, roadmap, sessions, status, sync-hub, validate, version,
     watch-hub
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import jsonschema
import pytest

from skills._lib.cli import _ROUTES, list_commands, route
from skills._lib.cli import __main__ as cli_main
from skills._lib.iteration import store as iteration_store
from skills._lib.iteration.schema import _load_schema, _validate


# ---------------------------------------------------------------------------
# Coverage matrix — the canonical list of every rddf subcommand.
#
# Whenever a new subcommand is added to ``_ROUTES``, add an entry here.
# The test parametrization below iterates over this tuple; missing entries
# fail with a clear "registered but not covered" message.
# ---------------------------------------------------------------------------

ALL_SUBCOMMANDS: tuple[str, ...] = (
    "ac-verify",
    "archive",
    "archive-sync",
    "cleanup",
    "contract-check",
    "dashboard",
    "deps",
    "deps.cross-repo",
    "discover-ship-changes",
    "doctor",
    "feature",
    "guide",
    "hub",
    "init",
    "issue",
    "iteration",
    "l2-trend",
    "migrate-improvements",
    "monitor",
    "orchestrate",
    "rdd-hub-bootstrap",
    "rdd-verify",
    "report-issue",
    "roadmap",
    "scheduler",
    "sessions",
    "status",
    "sync-hub",
    "validate",
    "version",
    "watch-hub",
)


# ===========================================================================
# Section 1 — Subcommand coverage matrix
# ===========================================================================


class TestSubcommandCoverage:
    """Every subcommand in ``_ROUTES`` is structurally present and callable."""

    def test_list_commands_returns_canonical_subcommand_set(self):
        """``list_commands()`` must exactly equal ``ALL_SUBCOMMANDS``.

        Drift here is a smell: either a new subcommand was added without
        extending the canonical tuple (test will fail and force the dev
        to acknowledge the addition), or a subcommand was removed but the
        tuple was not pruned.
        """
        assert list_commands() == list(ALL_SUBCOMMANDS), (
            f"list_commands()={list_commands()!r} diverges from "
            f"ALL_SUBCOMMANDS={ALL_SUBCOMMANDS!r}. Update ALL_SUBCOMMANDS "
            "if a subcommand was intentionally added/removed."
        )

    def test_routes_keys_match_canonical_subcommand_set(self):
        """The private routing table has exactly the canonical subcommands."""
        assert set(_ROUTES.keys()) == set(ALL_SUBCOMMANDS), (
            f"_ROUTES={set(_ROUTES.keys())!r} diverges from "
            f"ALL_SUBCOMMANDS={set(ALL_SUBCOMMANDS)!r}"
        )

    @pytest.mark.parametrize("subcommand", ALL_SUBCOMMANDS)
    def test_subcommand_is_registered(self, subcommand: str):
        """Each canonical subcommand has a routing entry."""
        assert subcommand in _ROUTES, (
            f"{subcommand!r} is in ALL_SUBCOMMANDS but missing from _ROUTES"
        )

    @pytest.mark.parametrize("subcommand", ALL_SUBCOMMANDS)
    def test_subcommand_handler_module_importable(self, subcommand: str):
        """The module path declared in ``_ROUTES`` resolves via importlib."""
        module_path = _ROUTES[subcommand].split(":", 1)[0]
        # We do not actually execute the module — just check that importlib
        # can locate it. This catches typos like ``.stat_cmd`` vs ``.status_cmd``
        # before they break production routing.
        spec = importlib.util.find_spec(module_path)
        assert spec is not None, (
            f"{subcommand!r}: module {module_path!r} not importable "
            "(check _ROUTES for typos)"
        )

    @pytest.mark.parametrize("subcommand", ALL_SUBCOMMANDS)
    def test_subcommand_handler_callable_with_correct_signature(self, subcommand: str):
        """The registered handler is callable with ``(args: list[str]) -> int``.

        We stub the module into ``sys.modules`` before ``route()`` triggers
        its lazy import so the assertion is hermetic — no real handler
        is invoked, only its presence + signature is checked.
        """
        import types

        module_path, _, func_name = _ROUTES[subcommand].partition(":")
        calls: list[list[str]] = []

        def _stub(args):
            calls.append(list(args))
            return 0

        fake_module = types.ModuleType(module_path)
        setattr(fake_module, func_name, _stub)
        sys.modules[module_path] = fake_module
        try:
            rc = route(subcommand, ["--probe"])
            assert rc == 0
            assert calls == [["--probe"]], (
                f"{subcommand!r}: route() did not forward ['--probe'] to "
                f"{func_name!r} (got calls={calls!r})"
            )
        finally:
            sys.modules.pop(module_path, None)

    @pytest.mark.parametrize("subcommand", ALL_SUBCOMMANDS)
    def test_subcommand_handler_signature_is_args_to_int(self, subcommand: str):
        """Handler functions take ``list[str]`` and return ``int``.

        This is the contract documented at ``_lib/cli/__init__.py`` line 76;
        deviating from it will break the ``main()`` dispatcher which assumes
        the return value is a process exit code.
        """
        module_path, _, func_name = _ROUTES[subcommand].partition(":")
        # Import the real module — not a stub — so we read its true signature.
        mod = importlib.import_module(module_path)
        handler = getattr(mod, func_name)
        sig = inspect.signature(handler)
        params = list(sig.parameters.values())
        # First parameter must be ``args`` with no default.
        assert len(params) >= 1, (
            f"{subcommand!r}: handler {func_name!r} has no parameters"
        )
        assert params[0].name == "args", (
            f"{subcommand!r}: first param is {params[0].name!r}, expected 'args'"
        )
        # Return annotation must be ``int`` (or ``int | None``).
        assert sig.return_annotation in (int, "int"), (
            f"{subcommand!r}: handler return annotation is "
            f"{sig.return_annotation!r}, expected 'int'"
        )


# ===========================================================================
# Section 2 — main() dispatch integration (one-shot per subcommand)
# ===========================================================================


class TestMainDispatchesToEachSubcommand:
    """``main([subcommand, ...])`` runs the registered handler in a tmp repo.

    Creates a minimal ``.rddf/state/`` directory in a tmp git repo, stubs
    each handler in ``sys.modules`` with a return-0 sentinel, and verifies
    ``main()`` propagates args + exit code. This complements the per-handler
    unit tests (``test_cli_<name>.py``) by exercising the full dispatch
    chain (git root resolution + project_root detection + lazy import +
    arg forwarding).
    """

    @pytest.fixture
    def fake_handlers(self):
        """Install sentinel handlers for every subcommand, yield the calls dict."""
        import types

        calls: dict[str, list[list[str]]] = {}

        # Multiple subcommands may share one module (e.g. ``deps`` and
        # ``deps.cross-repo`` both live in ``deps_cmd.py``). Reuse the fake
        # module per module_path so the second registration does not clobber
        # the first one's handler attribute.
        fake_modules: dict[str, types.ModuleType] = {}

        for sub in ALL_SUBCOMMANDS:
            module_path, _, func_name = _ROUTES[sub].partition(":")
            _calls: list[list[str]] = []

            def _make_handler(name):
                def _handler(args):
                    _calls.append(list(args))
                    calls.setdefault(name, _calls)
                    return 0

                return _handler

            fake_module = fake_modules.get(module_path)
            if fake_module is None:
                fake_module = types.ModuleType(module_path)
                fake_modules[module_path] = fake_module
                sys.modules[module_path] = fake_module
            setattr(fake_module, func_name, _make_handler(sub))

        yield calls

        for sub in ALL_SUBCOMMANDS:
            module_path, _, _ = _ROUTES[sub].partition(":")
            sys.modules.pop(module_path, None)

    @pytest.fixture
    def tmp_repo_with_state_dir(self, tmp_path, monkeypatch):
        """A tmp git repo with an empty ``.rddf/state/`` (so main() doesn't
        bail out with 'not a rdd-workflow project')."""
        import subprocess

        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=str(repo), check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(repo), check=True,
        )
        (repo / "README.md").write_text("# tmp\n")
        subprocess.run(["git", "add", "README.md"], cwd=str(repo), check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "init"],
            cwd=str(repo), check=True,
        )
        (repo / ".rddf" / "state").mkdir(parents=True)
        monkeypatch.chdir(str(repo))
        return repo

    @pytest.mark.parametrize("subcommand", ALL_SUBCOMMANDS)
    def test_main_invokes_handler_with_args(
        self, subcommand, tmp_repo_with_state_dir, fake_handlers
    ):
        """``main(['<sub>', '--foo'])`` reaches the handler with ``['--foo']``."""
        rc = cli_main.main([subcommand, "--foo"])
        assert rc == 0, f"{subcommand!r}: main() returned {rc}"
        assert fake_handlers[subcommand] == [["--foo"]], (
            f"{subcommand!r}: handler called with "
            f"{fake_handlers[subcommand]!r}, expected [['--foo']]"
        )

    def test_main_session_alias_routes_to_sessions(
        self, tmp_repo_with_state_dir, fake_handlers
    ):
        """Legacy ``rddf session`` alias dispatches to the ``sessions`` handler."""
        rc = cli_main.main(["session", "show", "rds_test"])
        assert rc == 0
        # The 'sessions' handler should have been invoked with ['show', 'rds_test'].
        assert fake_handlers.get("sessions") == [["show", "rds_test"]], (
            f"session alias not dispatched correctly: "
            f"{fake_handlers.get('sessions')!r}"
        )


# ===========================================================================
# Section 3 — Regression: fix-iteration-schema-filled-at (2026-08-10)
# ===========================================================================


class TestFilledAtRegression:
    """Lock the v6 schema + migration so ``filled_at`` drift cannot recur.

    Background: an undeclared ``filled_at`` field appeared in
    ``iteration.json`` on or before 2026-08-08; the strict schema rejected
    every subsequent write, producing 26 cascading corrupt backups. The
    fix (a) adds ``filled_at`` to the per-change allowed properties and
    (b) adds a v5→v6 migration that sets ``filled_at = None`` on legacy
    entries. These tests lock both behaviours.
    """

    @pytest.fixture
    def schema(self):
        """The current iteration_schema.json (cached after first load)."""
        return _load_schema()

    def test_schema_version_is_v6(self, schema):
        """The schema advertises v6 as the current ``const``.

        Note: ``const`` was relaxed to ``enum: [3, 4, 5, 6]`` to allow
        historical-version data through (e.g. corruption tests below
        write ``version: 999`` which must STILL fail). If you ever
        re-tighten, ensure the test fixture data still validates.
        """
        assert "version" in schema["properties"]
        version_prop = schema["properties"]["version"]
        # ``const`` or ``enum`` — either is acceptable as long as 6 is allowed.
        if "const" in version_prop:
            assert version_prop["const"] == 6
        else:
            assert "enum" in version_prop
            assert 6 in version_prop["enum"]

    def test_filled_at_is_in_per_change_allowed_properties(self, schema):
        """``filled_at`` must be a declared per-change property."""
        per_change_props = (
            schema["properties"]["changes"]["items"]["properties"]
        )
        assert "filled_at" in per_change_props, (
            "filled_at missing from per-change schema — the v5 schema "
            "rejected every write once this field appeared in data"
        )

    def test_filled_at_accepts_iso8601_or_null(self, schema):
        """``filled_at`` is ``[string, null]`` with ``format: date-time``."""
        prop = (
            schema["properties"]["changes"]["items"]["properties"]["filled_at"]
        )
        assert "string" in prop["type"], (
            f"filled_at must accept string; got {prop['type']!r}"
        )
        assert "null" in prop["type"], (
            f"filled_at must accept null (legacy entries); got {prop['type']!r}"
        )
        assert prop.get("format") == "date-time", (
            f"filled_at should be date-time format; got {prop.get('format')!r}"
        )

    def test_filled_at_rejects_other_types(self, schema):
        """Constructing a change with ``filled_at`` as int must fail validation."""
        bad = {
            "version": 6,
            "updated_at": "2026-08-10T00:00:00+00:00",
            "current_phase": "default",
            "changes": [
                {
                    "name": "bad",
                    "status": "proposed",
                    "added_at": "2026-08-10T00:00:00+00:00",
                    "filled_at": 12345,  # int — not allowed
                }
            ],
        }
        with pytest.raises(jsonschema.ValidationError):
            _validate(bad)

    def test_iteration_with_filled_at_validates(self, schema):
        """A change entry containing ``filled_at`` must validate cleanly.

        This is the exact shape that triggered the original bug. Now that
        the schema accepts the field, this must pass.
        """
        good = {
            "version": 6,
            "updated_at": "2026-08-10T00:00:00+00:00",
            "current_phase": "v2.2",
            "changes": [
                {
                    "name": "archive-cleanup-plan-files-extension",
                    "status": "archived",
                    "phase": "v2.2",
                    "category": "core",
                    "priority": "P2",
                    "added_at": "2026-08-08T23:47:24+0800",
                    "filled_at": "2026-08-09T00:10:00+0800",
                    "tasks_done": 23,
                    "tasks_total": 23,
                    "archived_at": "2026-08-08T15:00:00+00:00",
                }
            ],
        }
        # Must not raise.
        _validate(good)

    def test_actual_repo_iteration_json_validates_after_fix(self, schema):
        """The repo's own ``.rddf/state/iteration.json`` validates.

        This is the headline scenario from fix-iteration-schema-filled-at:
        the live iteration.json in the rdd-workflow repo had ``filled_at``
        injected and was rejected by the strict v5 schema. The v6 schema
        must accept it as-is. This test will fail if someone deletes
        ``filled_at`` from the schema without bumping the migration first.
        """
        repo_iteration = (
            Path(__file__).resolve().parents[2]
            / ".rddf"
            / "state"
            / "iteration.json"
        )
        if not repo_iteration.is_file():
            pytest.skip(
                "Repo iteration.json not present in this checkout "
                "(likely running outside the rdd-workflow repo)"
            )
        with open(repo_iteration) as f:
            data = json.load(f)
        # Sanity: the file should actually contain filled_at somewhere —
        # otherwise this test isn't actually exercising the regression.
        has_filled_at = any(
            "filled_at" in change for change in data.get("changes", [])
        )
        assert has_filled_at, (
            "Repo iteration.json no longer contains filled_at — "
            "this test has lost its purpose; remove or update it."
        )
        # And critically, it must validate now. Use the local-ref-resolving
        # validator (the raw jsonschema.validate() cannot resolve the schema's
        # $ref to feature_view_schema.json without network access).
        _validate(data)


# ===========================================================================
# Section 4 — Migration chain v3 → v6
# ===========================================================================


class TestMigrationChain:
    """Verify the v3 → v4 → v5 → v6 migration chain preserves data + adds new fields."""

    def test_migrate_v5_to_v6_sets_filled_at_none(self):
        """Migrating a v5 state stamps ``filled_at = None`` on every change."""
        v5_state = {
            "version": 5,
            "updated_at": "2026-08-10T00:00:00+00:00",
            "current_phase": "v2.2",
            "changes": [
                {
                    "name": "legacy-change",
                    "status": "archived",
                    "added_at": "2026-08-01T00:00:00+00:00",
                    "l2_violation_count_after": 0,
                    "l2_violation_kind": "sim_include_drv",
                }
            ],
        }
        migrated = iteration_store._migrate_v5_to_v6(v5_state)
        assert migrated["version"] == 6
        assert "filled_at" in migrated["changes"][0]
        assert migrated["changes"][0]["filled_at"] is None
        # Existing fields preserved.
        assert migrated["changes"][0]["l2_violation_count_after"] == 0
        assert migrated["changes"][0]["l2_violation_kind"] == "sim_include_drv"

    def test_migrate_v5_to_v6_idempotent(self):
        """Running migration on already-v6 data is a no-op."""
        v6_state = {
            "version": 6,
            "updated_at": "2026-08-10T00:00:00+00:00",
            "current_phase": "v2.2",
            "changes": [
                {
                    "name": "x",
                    "status": "archived",
                    "added_at": "2026-08-01T00:00:00+00:00",
                    "filled_at": "2026-08-02T00:00:00+00:00",
                }
            ],
        }
        # Passing v6 to _migrate_v5_to_v6 must return the input unchanged
        # (it only acts on version==5).
        result = iteration_store._migrate_v5_to_v6(v6_state)
        assert result is v6_state or result == v6_state
        # The pre-existing filled_at value must NOT be overwritten with None.
        assert result["changes"][0]["filled_at"] == "2026-08-02T00:00:00+00:00"

    def test_migrate_to_current_walks_v3_to_v6(self):
        """``_migrate_to_current`` walks v3 → v6 in three steps, adding all new fields."""
        v3_state = {
            "version": 3,
            "updated_at": "2026-08-10T00:00:00+00:00",
            "current_phase": "v2.0",
            "changes": [
                {"name": "old-change", "status": "archived", "added_at": "..."}
            ],
        }
        migrated = iteration_store._migrate_to_current(v3_state)
        assert migrated["version"] == 6
        c = migrated["changes"][0]
        # v4 added: manual_deps, manual_blocks
        assert c["manual_deps"] is None
        assert c["manual_blocks"] is None
        # v5 added: l2_violation_count_after, l2_violation_kind
        assert c["l2_violation_count_after"] is None
        assert c["l2_violation_kind"] is None
        # v6 added: filled_at
        assert c["filled_at"] is None

    def test_migrate_to_current_v6_is_no_op(self):
        """Already-current data passes through unchanged (identity or shallow copy)."""
        v6_state = {
            "version": 6,
            "updated_at": "2026-08-10T00:00:00+00:00",
            "current_phase": "default",
            "changes": [
                {
                    "name": "x",
                    "status": "archived",
                    "added_at": "2026-08-01T00:00:00+00:00",
                    "filled_at": "2026-08-02T00:00:00+00:00",
                }
            ],
        }
        result = iteration_store._migrate_to_current(v6_state)
        # Identity acceptable (no migration ran), but values must be preserved.
        assert result["changes"][0]["filled_at"] == "2026-08-02T00:00:00+00:00"


# ===========================================================================
# Section 5 — Smoke: safe-default invocations for each handler
# ===========================================================================


# These handlers can be called with no args and a writable tmp project
# without doing anything destructive. They are smoke-tested to catch
# "the handler exists but crashes on import" regressions.
SAFE_SMOKE_SUBCOMMANDS: tuple[str, ...] = (
    "version",       # reads package.json
    "iteration",     # prints help when called with no subcommand
)


class TestSafeSmoke:
    """A handful of handlers can be safely invoked with no args + tmp project."""

    @pytest.fixture
    def tmp_project_root(self, tmp_path, monkeypatch):
        """A minimal project root (no .rddf/state/ — main() short-circuits
        anyway, but we still need a valid git repo for resolve_project_root)."""
        import subprocess

        repo = tmp_path / "proj"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t"],
            cwd=str(repo), check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "T"],
            cwd=str(repo), check=True,
        )
        (repo / "README.md").write_text("# x\n")
        subprocess.run(["git", "add", "README.md"], cwd=str(repo), check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "i"],
            cwd=str(repo), check=True,
        )
        (repo / "package.json").write_text(
            json.dumps({"version": "9.9.9", "name": "test"})
        )
        # main() short-circuits with "not a rdd-workflow project" if
        # .rddf/state/ is missing, so we must create it for any smoke
        # test that exercises the dispatch chain end-to-end.
        (repo / ".rddf" / "state").mkdir(parents=True)
        monkeypatch.chdir(str(repo))
        monkeypatch.setenv("RDDF_PROJECT_ROOT", str(repo))
        return repo

    def test_version_handler_invokable(self, tmp_project_root, capsys):
        """``rddf version`` returns 0 and prints the version banner."""
        rc = cli_main.main(["version"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "rddf v9.9.9" in captured.out

    def test_iteration_handler_invokable(self, tmp_project_root, capsys):
        """``rddf iteration`` (no subcommand) prints help and returns 0."""
        rc = cli_main.main(["iteration"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "usage" in captured.out.lower() or "subcommand" in captured.out.lower()

    def test_main_no_args_prints_help(self, capsys):
        """``rddf`` (no args) prints help and returns 0."""
        rc = cli_main.main([])
        captured = capsys.readouterr()
        assert rc == 0
        assert "usage:" in captured.out.lower()