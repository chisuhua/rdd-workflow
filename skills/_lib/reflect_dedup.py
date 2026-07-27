# skills/_lib/reflect_dedup.py
"""Fuzzy dedup matching for reflect_engine.

Searches improvements/*.md, proposal-suggestions.md, and proposal-approved.md
for existing proposals that match a given error signature/fingerprint.
"""

import os, json, re
from pathlib import Path

STOP_WORDS = {"the", "a", "an", "is", "at", "on", "in", "of", "to", "for",
              "and", "or", "not", "with", "from", "by", "as", "be", "was", "are"}


class DedupMatcher:
    """Fuzzy matcher for finding existing proposals related to an error signature."""

    def __init__(self, improvements_dir=None, suggestions_file=None,
                 approved_file=None, project_root=None):
        root = project_root or self._find_project_root()
        self.improvements_dir = improvements_dir or os.path.join(root, "improvements")
        self.suggestions_file = suggestions_file or os.path.join(root, "proposal-suggestions.md")
        self.approved_file = approved_file or os.path.join(root, "proposal-approved.md")

    @staticmethod
    def _find_project_root():
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists():
                return str(parent)
        return str(current)

    def _extract_keywords(self, fingerprint):
        """Extract meaningful keywords from a fingerprint like 'plan:plan-done:quality-gate-fail'."""
        parts = fingerprint.replace(":", " ").replace("-", " ").split()
        return [p.lower() for p in parts if p.lower() not in STOP_WORDS]

    def _fuzzy_match(self, keywords, text):
        """Check if at least 1 keyword appears in the text."""
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw in text_lower)
        return matches >= 1

    def _scan_improvements(self, keywords):
        """Scan improvements/*.md for matching proposals."""
        if not os.path.isdir(self.improvements_dir):
            return None
        for fname in sorted(os.listdir(self.improvements_dir)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(self.improvements_dir, fname)
            try:
                with open(fpath) as f:
                    content = f.read()
                if self._fuzzy_match(keywords, content):
                    name = fname[:-3]  # strip .md
                    return {"matched_name": name, "source": "improvements",
                            "file": fpath, "matched_keywords": keywords}
            except (IOError, OSError):
                continue
        return None

    def _scan_suggestions(self, keywords):
        """Scan proposal-suggestions.md JSON for matching proposals."""
        if not os.path.isfile(self.suggestions_file):
            return None
        try:
            with open(self.suggestions_file) as f:
                entries = json.load(f)
            search_text = json.dumps(entries).lower()
            if self._fuzzy_match(keywords, search_text):
                # Find the best matching entry
                for entry in entries:
                    if isinstance(entry, dict):
                        entry_text = json.dumps(entry).lower()
                        if self._fuzzy_match(keywords, entry_text):
                            return {"matched_name": entry.get("name", "unknown"),
                                    "source": "suggestions",
                                    "matched_keywords": keywords}
        except (json.JSONDecodeError, IOError):
            pass
        return None

    def _scan_approved(self, keywords):
        """Scan proposal-approved.md markdown table for matching proposals."""
        if not os.path.isfile(self.approved_file):
            return None
        try:
            with open(self.approved_file) as f:
                content = f.read()
            if self._fuzzy_match(keywords, content):
                # Extract proposal names from markdown table links
                matches = re.findall(r'\[([^\]]+)\]\(improvements/', content)
                for name in matches:
                    if any(kw in name.lower() for kw in keywords):
                        return {"matched_name": name, "source": "approved",
                                "matched_keywords": keywords}
        except (IOError, OSError):
            pass
        return None

    def check_all(self, fingerprint):
        """Check all sources for a matching proposal. Returns first match or None."""
        keywords = self._extract_keywords(fingerprint)
        if len(keywords) < 2:
            return None  # too few keywords for meaningful matching

        for scanner in [self._scan_improvements, self._scan_suggestions, self._scan_approved]:
            result = scanner(keywords)
            if result is not None:
                return result
        return None
