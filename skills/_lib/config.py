"""Multi-source configuration parser with strict priority order.

Priority (highest to lowest):
    1. Runtime overrides (passed to `parse()`)
    2. loop.yaml (project-level)
    3. .spec-workflow.json (project-level)
    4. Environment variables (SPEC_WORKFLOW_*)
    5. Built-in defaults (skills/_lib/defaults.py)

A higher-priority source COMPLETELY replaces the lower-priority value
(strict order, not deep merge). See `design.md` Decision 5 for rationale.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml

from skills._lib.defaults import get_defaults


class ConfigError(Exception):
    """Raised on invalid config values or unreadable files."""


# Mapping from env var name to dotted config path
_ENV_VAR_MAP = {
    "SPEC_WORKFLOW_MODE": "interaction.mode",
    "SPEC_WORKFLOW_MAX_ITERATIONS": "loop.max_iterations",
    "SPEC_WORKFLOW_MAX_RETRIES": "loop.max_retries",
    "SPEC_WORKFLOW_STATE_PATH": "state.path",
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


class ConfigParser:
    """Multi-source config parser. Use `.parse()` to get a fully-merged config dict."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.spec_workflow_json = self.project_root / ".spec-workflow.json"
        self.loop_yaml = self.project_root / "loop.yaml"

    def parse(self, runtime_overrides: Optional[dict] = None) -> dict:
        """Read all sources, merge in priority order, validate, return config dict.

        Args:
            runtime_overrides: Dict of dotted-path → value. Highest priority.

        Merge order (lowest → highest priority, last write wins):
            defaults < .spec-workflow.json < env vars < loop.yaml < runtime overrides
        This ordering reflects the contract tested in tests/unit/test_config.py:
        env vars override .spec-workflow.json (test_env_var_overrides_file_config),
        loop.yaml overrides .spec-workflow.json (test_priority_loop_yaml_over_spec_workflow_json),
        runtime overrides override loop.yaml (test_priority_runtime_over_loop_yaml).
        """
        config = get_defaults()

        # Lowest: .spec-workflow.json (project-level base)
        if self.spec_workflow_json.is_file():
            try:
                with open(self.spec_workflow_json) as f:
                    file_cfg = json.load(f)
            except json.JSONDecodeError as e:
                raise ConfigError(f"{self.spec_workflow_json} is not valid JSON: {e}") from e
            config = _deep_merge(config, file_cfg)

        # Env vars override .spec-workflow.json
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
        return config
