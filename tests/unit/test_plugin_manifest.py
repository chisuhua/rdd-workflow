"""Plugin manifest schema validation (per phase-3-general-20260829063801 acceptance)."""
import pytest
from _lib.plugin_manifest import validate_manifest, ManifestError


def _write(tmp_path, data):
    import yaml
    p = tmp_path / "plugin.yaml"
    p.write_text(yaml.safe_dump(data))
    return p


def test_valid_manifest_passes(tmp_path):
    m = {"name": "my-plugin", "version": "1.0.0", "entry_point": "plugin:main", "network": False}
    validate_manifest(_write(tmp_path, m))


@pytest.mark.parametrize("missing", ["name", "version", "entry_point"])
def test_missing_required_field_rejects(tmp_path, missing):
    m = {"name": "p", "version": "1.0.0", "entry_point": "p:m"}
    del m[missing]
    with pytest.raises(ManifestError):
        validate_manifest(_write(tmp_path, m))


def test_invalid_network_type_rejects(tmp_path):
    m = {"name": "p", "version": "1.0.0", "entry_point": "p:m", "network": "yes"}
    with pytest.raises(ManifestError):
        validate_manifest(_write(tmp_path, m))


def test_invalid_entry_point_format_rejects(tmp_path):
    m = {"name": "p", "version": "1.0.0", "entry_point": "no-colon"}
    with pytest.raises(ManifestError):
        validate_manifest(_write(tmp_path, m))


def test_invalid_version_format_rejects(tmp_path):
    m = {"name": "p", "version": "not-semver", "entry_point": "p:m"}
    with pytest.raises(ManifestError):
        validate_manifest(_write(tmp_path, m))


def test_invalid_name_format_rejects(tmp_path):
    m = {"name": "P-CAPITAL", "version": "1.0.0", "entry_point": "p:m"}
    with pytest.raises(ManifestError):
        validate_manifest(_write(tmp_path, m))