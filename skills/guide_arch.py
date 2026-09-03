"""DEPRECATED shim: maps skills.guide_arch → skills/rdd-arch/ (Stage 3 rename).

Per Stage 3 / ADR-0042, the canonical skill is `rdd-arch`. Legacy `guide_arch`
imports are forwarded to `rdd-arch` for the deprecation window (v3.x + 2 minor).
"""
__path__ = [__import__('os').path.join(__import__('os').path.dirname(__file__), 'rdd-arch')]
