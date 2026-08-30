"""Plugin manifest validator (per phase-3-general-20260829063801)."""
import re
from pathlib import Path


class ManifestError(ValueError):
    """Raised when a plugin manifest fails validation."""


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ENTRY_RE = re.compile(r"^[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+$")
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")


def validate_manifest(path):
    """Validate a plugin.yaml manifest. Returns parsed dict on success;
    raises ManifestError on any field violation."""
    import yaml
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a YAML mapping")
    for req in ("name", "version", "entry_point"):
        if req not in data:
            raise ManifestError(f"missing required field: {req}")
    if not NAME_RE.match(data["name"]):
        raise ManifestError(f"invalid name (must match kebab-case): {data['name']}")
    if not SEMVER_RE.match(data["version"]):
        raise ManifestError(f"invalid semver: {data['version']}")
    if not ENTRY_RE.match(data["entry_point"]):
        raise ManifestError(f"invalid entry_point (expected module:function): {data['entry_point']}")
    if "network" in data and not isinstance(data["network"], bool):
        raise ManifestError("network must be bool")
    return data