# tests/unit/test_config_openspec_gate.py
import json
import os

import jsonschema
import yaml


def test_config_openspec_gate_section():
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
    assert "openspec_gate" in cfg
    assert "paths" in cfg["openspec_gate"]
    assert "extensions" in cfg["openspec_gate"]
    assert "exclude" in cfg["openspec_gate"]
    assert "mode" in cfg["openspec_gate"]
    assert cfg["openspec_gate"]["mode"] in ("warn", "block")


def test_config_openspec_gate_schema():
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
    schema_path = os.path.join("skills", "_lib", "schemas", "config_schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    jsonschema.validate(cfg, schema)
