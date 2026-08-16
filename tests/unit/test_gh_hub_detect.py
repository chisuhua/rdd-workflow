"""Unit tests for gh_repo_detect.detect_hub_repo (cross-repo Hub detection)."""
import os
from unittest.mock import patch

from skills._lib.gh_repo_detect import detect_hub_repo


def test_detect_hub_repo_from_env_var():
    with patch.dict(os.environ, {"RDDF_REPORT_GH_REPO": "my-org/rdd-hub"}):
        result = detect_hub_repo()
        assert result == "my-org/rdd-hub"


def test_detect_hub_repo_default_fallback():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("RDDF_REPORT_GH_REPO", None)
        result = detect_hub_repo()
        assert result == "rdd-hub"
