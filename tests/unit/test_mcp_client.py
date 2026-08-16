"""Unit tests for MCPClient (4 Hub tools + transport + fallback)."""
import os
from unittest.mock import patch, MagicMock
import pytest

from skills.cross_repo_protocol.mcp_client import (
    MCPClient, MCPConfigurationError,
)


def test_missing_github_token_raises_config_error():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("GITHUB_TOKEN", None)
        with pytest.raises(MCPConfigurationError):
            MCPClient()


def test_hub_read_issue_returns_normalized():
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}):
        with patch.object(MCPClient, "_call_mcp_server") as mock:
            mock.return_value = {
                "number": 42, "title": "[RFC] Test", "body": "body",
                "state": "open", "labels": [{"name": "rfc"}],
                "stakeholders": ["org/repo-a"], "contract_impact": "High",
            }
            client = MCPClient()
            result = client.hub_read_issue(42)
            assert result["number"] == 42
            assert result["title"] == "[RFC] Test"
            assert result["status"] == "open"


def test_hub_create_issue_validates_title():
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}):
        client = MCPClient()
        with pytest.raises(ValueError):
            client.hub_create_issue(title="", body="test")


def test_hub_create_issue_success():
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}):
        with patch.object(MCPClient, "_call_mcp_server") as mock:
            mock.return_value = {
                "number": 43, "title": "[RFC] New", "body": "test",
                "state": "open", "created_at": "2026-08-15T16:00:00Z",
                "html_url": "https://github.com/org/rdd-hub/issues/43",
            }
            client = MCPClient()
            result = client.hub_create_issue(title="[RFC] New", body="test")
            assert result["number"] == 43


def test_hub_update_status_without_comment():
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}):
        with patch.object(MCPClient, "_call_mcp_server") as mock:
            mock.return_value = {"number": 42, "status": "in_progress"}
            client = MCPClient()
            result = client.hub_update_status(42, "in_progress")
            assert result["status"] == "in_progress"


def test_hub_sync_contract_returns_receipt():
    with patch.dict(os.environ, {"GITHUB_TOKEN": "fake-token"}):
        with patch.object(MCPClient, "_call_mcp_server") as mock:
            mock.return_value = {
                "contract_id": "auth-v2",
                "synced_at": "2026-08-15T16:00:00Z",
                "hub_confirmed": True,
            }
            client = MCPClient()
            result = client.hub_sync_contract("auth-v2", "synced")
            assert result["hub_confirmed"] is True
