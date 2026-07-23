"""Proxy: maps skills.rddf_session → skills/rddf-session/ for pyright LSP resolution.

Python's import system treats a .py file with __path__ set as a
namespace-like package. This file bridges the underscore-to-hyphen gap
between Python import names and filesystem directory names.

Runtime: conftest.py dash-bridge (Phase 2) maps this via sys.modules
before this file is loaded. This file exists purely for pyright/LSP.
"""

__path__ = [__import__('os').path.join(__import__('os').path.dirname(__file__), 'rddf-session')]
