import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "skills" / "_lib" / "schemas" / "feature_view_schema.json"


@pytest.fixture
def schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


@pytest.fixture
def valid_payload() -> dict:
    return {
        "schema_version": 1,
        "updated_at": "2026-07-09T12:00:00+00:00",
        "features": {
            "feature-stream": {
                "name": "feature-stream",
                "status": "in_progress",
                "change_names": ["refactor-stream-base", "add-m2sPipe"],
                "change_count": 2,
                "archived_count": 0,
                "rollup_basis": "explicit",
                "depends_on": [],
                "blocks": ["feature-pipes"],
                "parallel_group": 0,
                "conflicts_with": [],
            }
        },
        "execution_order": [["feature-stream"], ["feature-pipes"]],
    }


class TestFeatureViewSchema:
    def test_valid_payload_accepted(self, schema, valid_payload):
        jsonschema.validate(valid_payload, schema)  # should not raise

    def test_missing_schema_version_rejected(self, schema, valid_payload):
        del valid_payload["schema_version"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)

    def test_wrong_status_rejected(self, schema, valid_payload):
        valid_payload["features"]["feature-stream"]["status"] = "bogus"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)

    def test_wrong_schema_version_rejected(self, schema, valid_payload):
        valid_payload["schema_version"] = 99
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)

    def test_execution_order_must_be_list_of_lists(self, schema, valid_payload):
        valid_payload["execution_order"] = ["feature-stream", "feature-pipes"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)

    def test_features_must_be_object(self, schema, valid_payload):
        valid_payload["features"] = ["feature-stream", "feature-pipes"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(valid_payload, schema)