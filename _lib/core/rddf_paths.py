"""Canonical locations of the two proposal index files.

`improvement-suggestions.md` and `improvement-approved.md` are rdd-workflow
internal metadata, so ADR-0026 puts them under `.rddf/` — the same rule that
moved `.rddf/improvements/` and `.rddf/roadmap.md`. Projects created before the
move still keep them at the project root; those copies stay valid.

Resolution rule (one function, so the answer cannot drift between callers):

- read / write target = `<root>/.rddf/<name>` when it exists, else the legacy
  `<root>/<name>` when that exists, else the canonical `<root>/.rddf/<name>`
  (new projects get the new location).

Rows in a `.rddf/`-hosted index link to `improvements/<name>.md` (relative to
the index file); rows in a legacy root-hosted index link to
`.rddf/improvements/<name>.md` (relative to the project root). `link_prefix()`
answers which form a given index file needs.

Pure path arithmetic: no IO beyond `os.path.isfile`, no imports from `_lib`.
"""
from __future__ import annotations

import os
from typing import List

RDFF_DIR = ".rddf"
SUGGESTIONS_NAME = "improvement-suggestions.md"
APPROVED_NAME = "improvement-approved.md"
INDEX_NAMES = (SUGGESTIONS_NAME, APPROVED_NAME)


def candidates(project_root: str, name: str) -> List[str]:
    """Both legal locations, canonical first."""
    return [
        os.path.join(project_root, RDFF_DIR, name),
        os.path.join(project_root, name),
    ]


def resolve(project_root: str, name: str) -> str:
    """Path to read/write for `name`: existing file first, canonical as default."""
    paths = candidates(project_root, name)
    for path in paths:
        if os.path.isfile(path):
            return path
    return paths[0]


def suggestions_file(project_root: str) -> str:
    return resolve(project_root, SUGGESTIONS_NAME)


def approved_file(project_root: str) -> str:
    return resolve(project_root, APPROVED_NAME)


def is_rddf_hosted(path: str) -> bool:
    """True when `path` lives directly under a `.rddf/` directory."""
    return os.path.basename(os.path.dirname(os.path.abspath(path))) == RDFF_DIR


def link_prefix(index_path: str) -> str:
    """Markdown link prefix for table rows written into `index_path`."""
    return "improvements/" if is_rddf_hosted(index_path) else f"{RDFF_DIR}/improvements/"
