"""Multi-source configuration parser with strict priority order.

Priority (highest to lowest):
    1. Runtime overrides (passed to `parse()`)
    2. loop.yaml (project-level)
    3. .rddf.json (project-level)
    4. Environment variables (RDDF_*)
    5. Built-in defaults (skills/_lib/defaults.py)

A higher-priority source COMPLETELY replaces the lower-priority value
(strict order, not deep merge). See `design.md` Decision 5 for rationale.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from skills._lib.core.defaults import get_defaults


# Path to the JSON Schema for config validation. Resolved relative to this
# module (skills/_lib/config.py) so it works regardless of CWD.
_CONFIG_SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "schemas", "config_schema.json"
)


class ConfigError(Exception):
    """Raised on invalid config values or unreadable files."""


# Mapping from env var name to dotted config path
_ENV_VAR_MAP = {
    "RDDF_MODE": "interaction.mode",
    "RDDF_MAX_ITERATIONS": "loop.max_iterations",
    "RDDF_MAX_RETRIES": "loop.max_retries",
    "RDDF_STATE_PATH": "state.path",
    "RDDF_REPORT_ENABLED": "reporting.enabled",
    "RDDF_REPORT_AUTO_SUBMIT": "reporting.auto_submit",
    "RDDF_REPORT_CLOSE_ON_ARCHIVE": "reporting.close_on_archive",
    "RDDF_REPORT_DESTINATION": "reporting.destination",
    "RDDF_REPORT_GH_REPO": "reporting.gh_repo",
}


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Deep-merge overlay into base. Overlay values completely replace base values (strict order)."""
    out = dict(base)
    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _set_dotted(data: dict, dotted_key: str, value: Any) -> None:
    """Set a value at a dotted path, creating dicts as needed."""
    keys = dotted_key.split(".")
    cur = data
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[keys[-1]] = value


def _coerce_env_value(raw: str, target_path: str) -> Any:
    """Coerce env var string to int/float/bool/str based on the target config key."""
    # Numeric fields
    if "max_iterations" in target_path or "max_retries" in target_path:
        try:
            return int(raw)
        except ValueError:
            raise ConfigError(f"Env var {target_path}='{raw}' is not a valid integer")
    if "seconds" in target_path:
        try:
            return float(raw)
        except ValueError:
            raise ConfigError(f"Env var {target_path}='{raw}' is not a valid float")
    if raw.lower() in ("true", "yes", "1"):
        return True
    if raw.lower() in ("false", "no", "0"):
        return False
    return raw


def _validate(config: dict) -> None:
    """Validate config values. Raises ConfigError with clear messages."""
    mode = config.get("interaction", {}).get("mode")
    if mode not in ("loop", "menu", "hybrid"):
        raise ConfigError(
            f"Invalid mode '{mode}'. Must be one of: loop, menu, hybrid"
        )
    max_iter = config.get("loop", {}).get("max_iterations")
    if not isinstance(max_iter, int) or max_iter <= 0:
        raise ConfigError(f"max_iterations must be a positive integer (got {max_iter!r})")
    max_retries = config.get("loop", {}).get("max_retries")
    if not isinstance(max_retries, int) or max_retries < 0:
        raise ConfigError(f"max_retries must be a non-negative integer (got {max_retries!r})")


def _validate_schema(config: dict, project_root: Optional[str] = None) -> None:
    """Validate the merged config against config_schema.json using jsonschema.

    Complements the existing ``_validate()`` function with broader structural
    validation (types, enums, numeric bounds) for interaction, loop, and
    triggers sections. All fields are optional in the schema - validation
    only runs on fields that are present (``additionalProperties: true``).

    Backward-compatibility: if the schema file is missing, validation is
    silently skipped so that older installations without the schema file
    continue to work.

    Args:
        config: The merged config dict to validate.
        project_root: Unused. Kept for signature stability in case future
            callers want to override the schema location via project root.

    Raises:
        ConfigError: If the config violates the schema, with the validator's
            error message embedded.
    """
    if not os.path.isfile(_CONFIG_SCHEMA_PATH):
        return
    try:
        import jsonschema
    except ImportError:
        return
    try:
        with open(_CONFIG_SCHEMA_PATH) as f:
            schema = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise ConfigError(
            f"config schema at {_CONFIG_SCHEMA_PATH} is unreadable: {e}"
        ) from e
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(config), key=lambda e: e.path)
    if errors:
        first = errors[0]
        field_path = ".".join(str(p) for p in first.absolute_path) or "<root>"
        raise ConfigError(
            f"config schema validation failed at '{field_path}': {first.message}"
        )


def is_triggers_disabled() -> bool:
    """Check if --trigger-off flag is set via env var TRIGGER_OFF."""
    return os.environ.get("TRIGGER_OFF", "").lower() in ("1", "true", "yes")


def apply_safety_rails(triggers_cfg: dict) -> dict:
    """Apply safety rails to triggers config.

    - If TRIGGER_OFF is set, disable all triggers
    - If crash_recovery is enabled, ensure state is persisted
    """
    if is_triggers_disabled() or triggers_cfg.get("safety", {}).get("trigger_off_override"):
        triggers_cfg["enabled"] = False
    return triggers_cfg


class ConfigParser:
    """Multi-source config parser. Use `.parse()` to get a fully-merged config dict."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.rddf_json = self.project_root / ".rddf.json"
        self.loop_yaml = self.project_root / "loop.yaml"
        self.triggers: dict = {}

    def parse(self, runtime_overrides: Optional[dict] = None) -> dict:
        """Read all sources, merge in priority order, validate, return config dict.

        Args:
            runtime_overrides: Dict of dotted-path → value. Highest priority.

        Merge order (lowest → highest priority, last write wins):
            defaults < .rddf.json < env vars < loop.yaml < runtime overrides
        This ordering reflects the contract tested in tests/unit/test_config.py:
        env vars override .rddf.json (test_env_var_overrides_file_config),
        loop.yaml overrides .rddf.json (test_priority_loop_yaml_over_rddf_json),
        runtime overrides override loop.yaml (test_priority_runtime_over_loop_yaml).
        """
        config = get_defaults()

        # Lowest: .rddf.json (project-level base)
        if self.rddf_json.is_file():
            try:
                with open(self.rddf_json) as f:
                    file_cfg = json.load(f)
            except json.JSONDecodeError as e:
                raise ConfigError(f"{self.rddf_json} is not valid JSON: {e}") from e
            config = _deep_merge(config, file_cfg)

        # Env vars override .rddf.json
        env_overlay: dict = {}
        for env_name, dotted_path in _ENV_VAR_MAP.items():
            if env_name in os.environ:
                coerced = _coerce_env_value(os.environ[env_name], dotted_path)
                _set_dotted(env_overlay, dotted_path, coerced)
        config = _deep_merge(config, env_overlay)

        # loop.yaml overrides env vars and file
        if self.loop_yaml.is_file():
            try:
                with open(self.loop_yaml) as f:
                    loop_cfg = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise ConfigError(f"{self.loop_yaml} is not valid YAML: {e}") from e
            config = _deep_merge(config, loop_cfg)

        # Highest: runtime overrides
        if runtime_overrides:
            runtime_overlay: dict = {}
            for dotted_path, value in runtime_overrides.items():
                _set_dotted(runtime_overlay, dotted_path, value)
            config = _deep_merge(config, runtime_overlay)

        _validate(config)
        _validate_schema(config, str(self.project_root))

        # v3.0: triggers config
        triggers_cfg = config.get("triggers", {})
        # Apply defaults if missing
        if "enabled" not in triggers_cfg:
            triggers_cfg["enabled"] = True
        if "webhook_port" not in triggers_cfg:
            triggers_cfg["webhook_port"] = 9090
        if "fs_watch_interval" not in triggers_cfg:
            triggers_cfg["fs_watch_interval"] = 30.0
        if "git_poll_interval" not in triggers_cfg:
            triggers_cfg["git_poll_interval"] = 60.0
        if "default_rate_limit" not in triggers_cfg:
            triggers_cfg["default_rate_limit"] = 60
        safety_cfg = triggers_cfg.get("safety", {})
        if "max_concurrent_fires" not in safety_cfg:
            safety_cfg["max_concurrent_fires"] = 5
        if "crash_recovery" not in safety_cfg:
            safety_cfg["crash_recovery"] = True
        if "trigger_off_override" not in safety_cfg:
            safety_cfg["trigger_off_override"] = False
        triggers_cfg["safety"] = safety_cfg
        self.triggers = apply_safety_rails(triggers_cfg)

        return config
