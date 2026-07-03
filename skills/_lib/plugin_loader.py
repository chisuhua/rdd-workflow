"""Generic plugin loader for the v2-loop-engine spec-workflow modules.

Provides a reusable `PluginLoader[BaseClass]` that scans a directory of
`.py` files, imports them via `importlib`, discovers subclasses of the
given base class, and returns instantiated plugin objects.

This eliminates the duplicated plugin-loading logic that previously
lived independently in `detectors.py` and `actions.py`.

Type parameter `T` is the base class — e.g. `PluginLoader[Detector]`
or `PluginLoader[Action]`.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Generic, Optional, Type, TypeVar, List

T = TypeVar("T")


class PluginLoader(Generic[T]):
    """Generic loader that discovers and instantiates subclasses of a base class.

    Scans a plugin directory for `.py` files, imports each module, and
    returns any classes that subclass `base_class` (excluding
    `base_class` itself). Files starting with `_` are skipped, as are
    files that fail to import or whose subclasses fail to instantiate.

    Usage:
        loader = PluginLoader(Detector, ".spec-workflow/detectors")
        plugins = loader.load_plugins()                # plugins only
        all_of_them = loader.all_plugins(builtins)     # builtins + plugins
    """

    def __init__(self, base_class: Type[T], default_plugin_dir: str) -> None:
        """Initialize the loader.

        Args:
            base_class: The base class whose subclasses are treated as plugins.
            default_plugin_dir: Default directory to scan for plugin files;
                used when `load_plugins` / `all_plugins` is called without
                an explicit `plugin_dir`.
        """
        self.base_class = base_class
        self.default_plugin_dir = default_plugin_dir

    def load_plugins(self, plugin_dir: Optional[str] = None) -> list[T]:
        """Scan `plugin_dir` for .py files and return instantiated subclasses.

        Scan order is sorted to produce deterministic results regardless
        of filesystem ordering.

        - If `plugin_dir` does not exist, returns ``[]`` (no exception).
        - Skips files whose names start with ``_`` (private helpers).
        - Files that fail to import are silently skipped.
        - Subclasses that fail to instantiate are silently skipped.
        - Returns each discovered subclass instance as a member of
          ``list[T]``.

        Args:
            plugin_dir: Directory to scan.  Falls back to
                ``self.default_plugin_dir`` when ``None``.

        Returns:
            Instances of classes that subclass ``self.base_class`` but
            are not ``self.base_class`` itself, in sorted file order.
        """
        pdir = Path(plugin_dir or self.default_plugin_dir)
        if not pdir.exists():
            return []

        plugins: list[T] = []
        for py_file in sorted(pdir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception:
                continue
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, self.base_class)
                    and attr is not self.base_class
                ):
                    try:
                        plugins.append(attr())
                    except Exception:
                        continue
        return plugins

    def all_plugins(self, builtins: list, plugin_dir: Optional[str] = None) -> list:
        """Return built-in list followed by plugin-loaded instances.

        Built-in entries come first (deterministic order preserved from
        the caller), followed by any plugins discovered via
        ``load_plugins``.  Callers can de-duplicate by ``.name`` or other
        identifiers if needed.

        Args:
            builtins: Pre-built list of built-in instances (caller
                constructs wrappers / ordering as appropriate).
            plugin_dir: Directory to scan.  Falls back to
                ``self.default_plugin_dir`` when ``None``.

        Returns:
            Combined list: ``builtins + load_plugins(plugin_dir)``.
        """
        return list(builtins) + self.load_plugins(plugin_dir)