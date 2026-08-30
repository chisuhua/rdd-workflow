"""RFC interview checkpoint state (resume support, per phase-2-general-20260829063814 acceptance).

State file: .rddf/state/.rfc-interview-<name>.json (gitignored).
Override path via RDDF_STATE_DIR (for tests).
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Optional

DEFAULT_STATE_DIR = ".rddf/state"
STATE_PATH_TEMPLATE = "{state_dir}/.rfc-interview-{name}.json"


def _state_path(name):
    state_dir = os.environ.get("RDDF_STATE_DIR", DEFAULT_STATE_DIR)
    return Path(STATE_PATH_TEMPLATE.format(state_dir=state_dir, name=name))


def load_state(name):
    path = _state_path(name)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def save_state(name, state):
    path = _state_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def clear_state(name):
    path = _state_path(name)
    if path.exists():
        path.unlink()