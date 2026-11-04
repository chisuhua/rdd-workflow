"""Skills package - provides module aliases for dash-bridge compatibility.

This file exists primarily for LSP (pyright) to recognize module paths.
The actual dash-bridge logic for test execution is in tests/conftest.py.

Module aliases (each target directory must exist):
  - skills.rddf_session → skills/rddf-session/
  - skills.rdd_arch → skills/rdd-arch/
  - skills.rdd_workflow_writing_plans → skills/rdd-workflow-writing-plans/
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # These imports tell pyright where to find the modules
    # They only run during type checking, not at runtime
    import sys
    import os
    from pathlib import Path

    # The dash-bridge directories
    _dash_map = {
        'rddf_session': 'rddf-session',
        'rdd_arch': 'rdd-arch',
        'rdd_workflow_writing_plans': 'rdd-workflow-writing-plans',
    }
