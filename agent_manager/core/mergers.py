"""Merger utilities for agent-manager."""

import importlib
import inspect
import pkgutil
from pathlib import Path

from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.utils import discover_external_plugins, filter_disabled_plugins


def discover_merger_classes(include_disabled: bool = False):
    """Dynamically discover all merger classes.

    Discovers mergers from two sources:
    1. Built-in: Scans the plugins.mergers package for AbstractMerger subclasses
    2. External: Discovers plugins via entry points under 'agent_manager.mergers'

    Args:
        include_disabled: If True, include disabled merger plugins

    Returns:
        List of merger classes
    """
    from agent_manager.plugins.mergers import AbstractMerger

    merger_classes = []

    # === Part 1: Discover built-in mergers ===
    merger_classes.extend(_discover_builtin_mergers(AbstractMerger))

    # === Part 2: Discover external merger plugins via entry points ===
    external_plugins = discover_external_plugins(
        plugin_type="merger",
        entry_point_group="agent_manager.mergers",
        base_class=AbstractMerger,
    )

    # Filter out disabled plugins unless requested
    if not include_disabled:
        external_plugins = filter_disabled_plugins(external_plugins, "mergers")

    for plugin_info in external_plugins.values():
        if "class" in plugin_info:
            merger_class = plugin_info["class"]
            if merger_class not in merger_classes:
                merger_classes.append(merger_class)

    return merger_classes


def _discover_builtin_mergers(abstract_merger_class: type) -> list[type]:
    """Discover built-in merger classes from the plugins.mergers package.

    Args:
        abstract_merger_class: The AbstractMerger base class

    Returns:
        List of built-in merger classes
    """
    merger_classes = []

    import agent_manager.plugins.mergers as mergers_package

    mergers_package_path = Path(mergers_package.__file__).parent

    # Iterate through all Python files in the mergers directory
    for module_info in pkgutil.iter_modules([str(mergers_package_path)]):
        module_name = module_info.name

        # Skip private modules, __init__, abstract_merger, dict_merger (base class), copy_merger, and manager
        if module_name.startswith("_") or module_name in [
            "abstract_merger",
            "dict_merger",  # Base class for JSON/YAML mergers
            "copy_merger",
            "manager",
            "merger_registry",
        ]:
            continue

        try:
            # Import the module
            module = importlib.import_module(f"agent_manager.plugins.mergers.{module_name}")

            # Find all classes in the module
            for _name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a subclass of AbstractMerger
                # (but not AbstractMerger itself)
                if (
                    issubclass(obj, abstract_merger_class)
                    and obj is not abstract_merger_class
                    and obj.__module__ == module.__name__
                ):
                    merger_classes.append(obj)

        except ImportError:
            # Skip modules that can't be imported (e.g., missing dependencies)
            continue

    return merger_classes


def create_default_merger_registry():
    """Create a merger registry with auto-discovered built-in mergers.

    Automatically discovers and registers all merger classes in the
    agent_manager.plugins.mergers package based on their FILE_EXTENSIONS attribute.

    Returns:
        MergerRegistry with default mergers registered
    """
    from .merger_registry import MergerRegistry

    registry = MergerRegistry()

    # Auto-discover merger classes
    merger_classes = discover_merger_classes()

    # Register each merger for its declared file extensions
    for merger_class in merger_classes:
        if hasattr(merger_class, "FILE_EXTENSIONS") and merger_class.FILE_EXTENSIONS:
            for extension in merger_class.FILE_EXTENSIONS:
                registry.register_extension(extension, merger_class)
                message(
                    f"Auto-registered {merger_class.__name__} for extension: {extension}",
                    MessageType.DEBUG,
                    VerbosityLevel.DEBUG,
                )

    return registry
