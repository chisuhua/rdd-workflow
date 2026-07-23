"""Skills package - provides module aliases for dash-bridge compatibility.

This file exists primarily for LSP (pyright) to recognize module paths.
The actual dash-bridge logic for test execution is in tests/conftest.py.

Module aliases:
  - skills.rddf_session → skills/rddf-session/
  - skills.guide_arch → skills/guide-arch/
  - skills.guide_plan → skills/guide-plan/
  - skills.guide_ship → skills/guide-ship/
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
        'guide_arch': 'guide-arch',
        'guide_plan': 'guide-plan',
        'guide_ship': 'guide-ship',
        'rdd_workflow_writing_plans': 'rdd-workflow-writing-plans',
    }
