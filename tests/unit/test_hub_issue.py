"""Tests for hub_issue (CRUD)."""
from unittest.mock import patch
from skills._lib.hub_issue import create_hub_issue, find_existing_issue, update_hub_issue


def test_create_hub_issue_calls_client():
    with patch("skills._lib.hub_issue._get_client") as mock:
        mock.return_value.create_issue.return_value = {
            "number": 42, "html_url": "https://github.com/org/rdd-hub/issues/42"
        }
        result = create_hub_issue({
            "title": "[RFC] test",
            "body": "test",
            "stakeholders": [],
        })
        assert result["number"] == 42


def test_find_existing_issue_matches():
    issues = [
        {"title": "[RFC] test"},
        {"title": "[RFC] other"},
    ]
    assert find_existing_issue(issues, "test") is not None
    assert find_existing_issue(issues, "missing") is None


def test_update_hub_issue_calls_client():
    with patch("skills._lib.hub_issue._get_client") as mock:
        mock.return_value.hub_update_status.return_value = {"number": 42, "status": "in_progress"}
        result = update_hub_issue(42, {"status": "in_progress"})
        assert result["status"] == "in_progress"
