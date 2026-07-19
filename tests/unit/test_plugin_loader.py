"""Tests for skills._lib.loop.plugin_loader.PluginLoader.

Covers the generic plugin loader contract:
- load_plugins discovers subclasses of base_class from .py files in a directory
- Files starting with ``_`` are skipped (private helpers)
- Files that fail to import or whose subclasses fail to instantiate are
  silently skipped (no exception propagates)
- all_plugins returns builtins first, then plugin-loaded instances
- Non-existent plugin directory returns an empty list
"""
from skills._lib.loop.plugin_loader import PluginLoader


class _BasePlugin:
    """Base class for test plugins.

    Defined at module scope so plugin files can import it via
    ``from test_plugin_loader import _BasePlugin`` (pytest's default
    prepend import mode puts ``tests/unit/`` on ``sys.path``).
    """

    name = "base"


def test_load_plugins_discovers_subclasses_and_skips_underscore_and_broken(tmp_path):
    """load_plugins returns valid subclass instances; skips ``_``-prefixed
    files and files that fail to import."""
    # Valid plugin: subclass of _BasePlugin
    (tmp_path / "alpha.py").write_text(
        "from test_plugin_loader import _BasePlugin\n"
        "class Alpha(_BasePlugin):\n"
        "    name = 'alpha'\n"
    )
    # Underscore-prefixed file: must be skipped even though it defines a valid subclass
    (tmp_path / "_private.py").write_text(
        "from test_plugin_loader import _BasePlugin\n"
        "class Private(_BasePlugin):\n"
        "    name = 'private'\n"
    )
    # Broken file: invalid Python syntax, must be silently skipped
    (tmp_path / "broken.py").write_text("this is not valid python {{{\n")

    loader = PluginLoader(_BasePlugin, str(tmp_path))
    plugins = loader.load_plugins()
    names = [p.name for p in plugins]

    # The valid plugin was discovered and instantiated
    assert "alpha" in names
    # Underscore-prefixed file was skipped
    assert "private" not in names
    # Broken file did not crash the loader
    assert "broken" not in names
    # Only the one valid plugin was loaded
    assert len(plugins) == 1
    # The returned object is an instance of the subclass, not the base class
    assert isinstance(plugins[0], _BasePlugin)
    assert type(plugins[0]) is not _BasePlugin


def test_load_plugins_handles_missing_dir_and_failed_instantiation(tmp_path):
    """load_plugins returns [] for non-existent dir and silently skips
    subclasses whose ``__init__`` raises."""
    # Non-existent directory: returns empty list, no exception
    missing_dir = tmp_path / "does_not_exist"
    loader = PluginLoader(_BasePlugin, str(missing_dir))
    assert loader.load_plugins() == []

    # Empty directory: also returns empty list
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    loader_empty = PluginLoader(_BasePlugin, str(empty_dir))
    assert loader_empty.load_plugins() == []

    # Subclass whose __init__ raises must be silently skipped, while a
    # sibling valid plugin still loads
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    (plugin_dir / "bad_init.py").write_text(
        "from test_plugin_loader import _BasePlugin\n"
        "class BadInit(_BasePlugin):\n"
        "    name = 'bad_init'\n"
        "    def __init__(self):\n"
        "        raise RuntimeError('intentional init failure')\n"
    )
    (plugin_dir / "good.py").write_text(
        "from test_plugin_loader import _BasePlugin\n"
        "class Good(_BasePlugin):\n"
        "    name = 'good'\n"
    )
    loader_mixed = PluginLoader(_BasePlugin, str(plugin_dir))
    plugins = loader_mixed.load_plugins()
    names = [p.name for p in plugins]
    assert "good" in names
    assert "bad_init" not in names
    assert len(plugins) == 1


def test_all_plugins_combines_builtins_first_then_loaded_plugins(tmp_path):
    """all_plugins returns builtins (in order) followed by plugin-loaded
    instances."""
    (tmp_path / "extra.py").write_text(
        "from test_plugin_loader import _BasePlugin\n"
        "class Extra(_BasePlugin):\n"
        "    name = 'extra'\n"
    )

    # Construct two builtin instances with distinct names
    builtin_a = _BasePlugin()
    builtin_a.name = "builtin_a"
    builtin_b = _BasePlugin()
    builtin_b.name = "builtin_b"
    builtins = [builtin_a, builtin_b]

    loader = PluginLoader(_BasePlugin, str(tmp_path))
    combined = loader.all_plugins(builtins)
    names = [p.name for p in combined]

    # Builtins appear first, in their original order
    assert names[:2] == ["builtin_a", "builtin_b"]
    # Plugin-loaded instance appears after builtins
    assert "extra" in names
    assert names.index("extra") >= 2
    # Total = 2 builtins + 1 plugin
    assert len(combined) == 3
    # all_plugins must not mutate the caller's builtins list
    assert builtins == [builtin_a, builtin_b]
