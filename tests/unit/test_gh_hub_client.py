"""Unit tests for gh_hub_client (GitHub Hub API client)."""
import pytest
from unittest.mock import patch, MagicMock
from skills._lib.gh_hub_client import GhHubClient, RateLimitError


def test_create_issue_builds_correct_payload():
    client = GhHubClient(owner="org", repo="rdd-hub")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout='{"number": 42, "html_url": "https://github.com/org/rdd-hub/issues/42"}'
        )
        result = client.create_issue(
            title="[RFC] Test",
            body="Test body",
            labels=["rfc", "cross-repo"],
        )
        assert result["number"] == 42
        assert "issues/42" in result["html_url"]
        # 检查 gh CLI 调用参数
        call_args = mock_run.call_args[0][0]
        assert "issue" in call_args
        assert "create" in call_args
        assert "--title" in call_args
        assert "[RFC] Test" in call_args
        assert "--label" in call_args


def test_get_issue_status_parses_response():
    client = GhHubClient(owner="org", repo="rdd-hub")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 42, "state": "open", "state_reason": null, "title": "[RFC] Test"}',
        )
        status = client.get_issue_status(42)
        assert status["state"] == "open"
        assert status["number"] == 42


def test_rate_limit_error_raised_on_403():
    client = GhHubClient(owner="org", repo="rdd-hub")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stderr="403 rate limit exceeded"
        )
        with pytest.raises(RateLimitError):
            client.create_issue(title="Test", body="Test")
