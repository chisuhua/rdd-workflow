#!/usr/bin/env python3
"""Infer change type from description content.

Change types:
- test-only: Pure test additions/modifications
- doc-only: Documentation changes only
- refactor-only: Code restructuring without behavior changes
- feature: New functionality
"""
import re
from typing import Literal

ChangeType = Literal["test-only", "doc-only", "refactor-only", "feature", "debt"]


def infer_change_type(description: str, name: str = "") -> ChangeType:
    """Infer change type from description and name.
    
    Heuristics:
    - name contains 'test' or description mentions 'test coverage' → test-only
    - name contains 'doc' or description mentions 'documentation' → doc-only
    - description mentions 'refactor' or 'restructure' → refactor-only
    - description mentions 'new feature' or 'implement' → feature
    - default: feature
    """
    desc_lower = description.lower()
    name_lower = name.lower()
    
    # Test-only detection
    if "test" in name_lower or any(k in desc_lower for k in [
        "test coverage", "test-only", "testing", "单元测试", "测试覆盖"
    ]):
        return "test-only"
    
    # Doc-only detection
    if "doc" in name_lower or any(k in desc_lower for k in [
        "documentation", "doc-only", "文档", "readme", "adr"
    ]):
        return "doc-only"
    
    # Refactor-only detection
    if any(k in desc_lower for k in [
        "refactor", "restructure", "重组", "拆分", "重构"
    ]):
        return "refactor-only"
    
    # Debt detection
    if any(k in desc_lower for k in [
        "debt", "技术债务", "清理", "cleanup"
    ]):
        return "debt"
    
    return "feature"


if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("add unit tests for auth module", "test-auth"),
        ("update README.md with installation guide", "update-readme"),
        ("refactor RddfSessionCoordinator into modules", "split-rddf-god-class"),
        ("implement JWT authentication", "add-jwt-auth"),
        ("fix circular dependencies", "fix-circular-deps"),
    ]
    
    for desc, name in test_cases:
        ct = infer_change_type(desc, name)
        print(f"{name}: {ct}")
