"""Generic plugin discovery utilities for agent-manager."""

import importlib
import importlib.metadata
from pathlib import Path
from typing import Any

import yaml

from agent_manager.output import MessageType, VerbosityLevel, message


# =============================================================================
# Plugin Enable/Disable Utilities
# =============================================================================


def get_disabled_plugins(config_file: Path | None = None) -> dict[str, list[str]]:
    """Get the list of disabled plugins from config.

    Args:
        config_file: Path to config file. Defaults to ~/.agent-manager/config.yaml

    Returns:
        Dictionary mapping plugin types to lists of disabled plugin names:
        {
            "mergers": ["smart_markdown"],
            "agents": ["claude"],
            "repos": []
        }
    """
    if config_file is None:
        config_file = Path.home() / ".agent-manager" / "config.yaml"

    result = {"mergers": [], "agents": [], "repos": []}

    if not config_file.exists():
        return result

    try:
        with open(config_file) as f:
            config = yaml.safe_load(f) or {}

        plugins_config = config.get("plugins", {})
        disabled = plugins_config.get("disabled", {})

        for plugin_type in result:
            result[plugin_type] = disabled.get(plugin_type, [])

    except Exception as e:
        message(f"Failed to read disabled plugins from config: {e}", MessageType.DEBUG, VerbosityLevel.DEBUG)

    return result


def is_plugin_disabled(plugin_type: str, plugin_name: str, config_file: Path | None = None) -> bool:
    """Check if a plugin is disabled.

    Args:
        plugin_type: Type of plugin ("mergers", "agents", "repos")
        plugin_name: Name of the plugin
        config_file: Path to config file. Defaults to ~/.agent-manager/config.yaml

    Returns:
        True if the plugin is disabled, False otherwise
    """
    disabled = get_disabled_plugins(config_file)
    return plugin_name in disabled.get(plugin_type, [])


def set_plugin_enabled(
    plugin_type: str,
    plugin_name: str,
    enabled: bool,
    config_file: Path | None = None,
) -> bool:
    """Enable or disable a plugin in config.

    Args:
        plugin_type: Type of plugin ("mergers", "agents", "repos")
        plugin_name: Name of the plugin
        enabled: True to enable, False to disable
        config_file: Path to config file. Defaults to ~/.agent-manager/config.yaml

    Returns:
        True if the operation succeeded, False otherwise
    """
    if config_file is None:
        config_file = Path.home() / ".agent-manager" / "config.yaml"

    try:
        # Read existing config
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Ensure plugins.disabled structure exists
        if "plugins" not in config:
            config["plugins"] = {}
        if "disabled" not in config["plugins"]:
            config["plugins"]["disabled"] = {}
        if plugin_type not in config["plugins"]["disabled"]:
            config["plugins"]["disabled"][plugin_type] = []

        disabled_list = config["plugins"]["disabled"][plugin_type]

        if enabled:
            # Remove from disabled list
            if plugin_name in disabled_list:
                disabled_list.remove(plugin_name)
                message(f"Enabled {plugin_type[:-1]} plugin: {plugin_name}", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
            else:
                message(f"Plugin '{plugin_name}' is already enabled", MessageType.INFO, VerbosityLevel.ALWAYS)
        else:
            # Add to disabled list
            if plugin_name not in disabled_list:
                disabled_list.append(plugin_name)
                message(
                    f"Disabled {plugin_type[:-1]} plugin: {plugin_name}", MessageType.SUCCESS, VerbosityLevel.ALWAYS
                )
            else:
                message(f"Plugin '{plugin_name}' is already disabled", MessageType.INFO, VerbosityLevel.ALWAYS)

        # Clean up empty lists
        if not disabled_list:
            del config["plugins"]["disabled"][plugin_type]
        if not config["plugins"]["disabled"]:
            del config["plugins"]["disabled"]
        if not config["plugins"]:
            del config["plugins"]

        # Write back to config
        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        return True

    except Exception as e:
        message(f"Failed to update plugin state: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
        return False


def filter_disabled_plugins(
    plugins: dict[str, Any],
    plugin_type: str,
    config_file: Path | None = None,
) -> dict[str, Any]:
    """Filter out disabled plugins from a plugin dictionary.

    Args:
        plugins: Dictionary of discovered plugins
        plugin_type: Type of plugin ("mergers", "agents", "repos")
        config_file: Path to config file

    Returns:
        Filtered dictionary with disabled plugins removed
    """
    disabled = get_disabled_plugins(config_file)
    disabled_names = disabled.get(plugin_type, [])

    filtered = {}
    for name, info in plugins.items():
        if name in disabled_names:
            message(f"Skipping disabled {plugin_type[:-1]}: {name}", MessageType.DEBUG, VerbosityLevel.DEBUG)
        else:
            filtered[name] = info

    return filtered


# =============================================================================
# Plugin Discovery Utilities
# =============================================================================


def discover_external_plugins(
    plugin_type: str,
    package_prefix: str | None = None,
    entry_point_group: str | None = None,
    base_class: type | None = None,
) -> dict[str, dict]:
    """Discover external plugins via package prefix and/or entry points.

    This is a generic utility that can discover plugins using two methods:
    1. Package prefix: Finds installed packages starting with a specific prefix
       (e.g., 'am_agent_' for agent plugins)
    2. Entry points: Finds plugins registered under a specific entry point group
       (e.g., 'agent_manager.mergers' for merger plugins)

    Args:
        plugin_type: Human-readable name for logging (e.g., "agent", "merger")
        package_prefix: Package name prefix to search for (e.g., "am_agent_")
        entry_point_group: Entry point group name (e.g., "agent_manager.mergers")
        base_class: Optional base class to validate loaded classes against

    Returns:
        Dictionary mapping plugin names to plugin info dicts:
        {
            "plugin_name": {
                "package_name": "full_package_name",
                "class": <class object> (if entry point),
                "source": "package" | "entry_point"
            }
        }
    """
    plugins = {}

    # === Method 1: Discover by package prefix ===
    if package_prefix:
        plugins.update(
            _discover_by_package_prefix(
                plugin_type=plugin_type,
                package_prefix=package_prefix,
            )
        )

    # === Method 2: Discover by entry points ===
    if entry_point_group:
        plugins.update(
            _discover_by_entry_points(
                plugin_type=plugin_type,
                entry_point_group=entry_point_group,
                base_class=base_class,
            )
        )

    return plugins


def _discover_by_package_prefix(
    plugin_type: str,
    package_prefix: str,
) -> dict[str, dict]:
    """Discover plugins by scanning installed packages with a specific prefix.

    Args:
        plugin_type: Human-readable name for logging
        package_prefix: Package name prefix to search for

    Returns:
        Dictionary mapping plugin names to plugin info
    """
    plugins = {}

    try:
        for dist in importlib.metadata.distributions():
            # Normalize package name (hyphens to underscores)
            package_name = dist.name.replace("-", "_")

            if package_name.startswith(package_prefix):
                # Extract plugin name by removing the prefix
                plugin_name = package_name[len(package_prefix) :]

                plugins[plugin_name] = {
                    "package_name": package_name,
                    "source": "package",
                }

                message(
                    f"Discovered {plugin_type} plugin: {plugin_name} ({package_name})",
                    MessageType.DEBUG,
                    VerbosityLevel.DEBUG,
                )

    except Exception as e:
        message(
            f"Failed to discover {plugin_type} plugins by package prefix: {e}",
            MessageType.DEBUG,
            VerbosityLevel.DEBUG,
        )

    return plugins


def _discover_by_entry_points(
    plugin_type: str,
    entry_point_group: str,
    base_class: type | None = None,
) -> dict[str, dict]:
    """Discover plugins via entry points.

    Args:
        plugin_type: Human-readable name for logging
        entry_point_group: Entry point group name
        base_class: Optional base class to validate against

    Returns:
        Dictionary mapping plugin names to plugin info
    """
    plugins = {}

    try:
        entry_points = importlib.metadata.entry_points()

        # Get entry points for the specified group
        # Python 3.10+ uses select(), older versions use get()
        if hasattr(entry_points, "select"):
            eps = entry_points.select(group=entry_point_group)
        else:
            eps = entry_points.get(entry_point_group, [])

        for ep in eps:
            try:
                # Load the class from the entry point
                loaded_class = ep.load()

                # Validate against base class if provided
                if base_class is not None:
                    if not (isinstance(loaded_class, type) and issubclass(loaded_class, base_class)):
                        message(
                            f"Entry point '{ep.name}' does not point to a valid {plugin_type} class",
                            MessageType.WARNING,
                            VerbosityLevel.VERBOSE,
                        )
                        continue

                plugins[ep.name] = {
                    "package_name": ep.value.split(":")[0] if ":" in ep.value else ep.value,
                    "class": loaded_class,
                    "source": "entry_point",
                }

                message(
                    f"Discovered external {plugin_type} plugin: {ep.name}",
                    MessageType.DEBUG,
                    VerbosityLevel.DEBUG,
                )

            except Exception as e:
                message(
                    f"Failed to load {plugin_type} plugin '{ep.name}': {e}",
                    MessageType.WARNING,
                    VerbosityLevel.VERBOSE,
                )

    except Exception as e:
        message(
            f"Failed to discover {plugin_type} plugins via entry points: {e}",
            MessageType.DEBUG,
            VerbosityLevel.DEBUG,
        )

    return plugins


def load_plugin_class(plugin_info: dict, class_name: str = "Agent"):
    """Load a class from a plugin.

    Args:
        plugin_info: Plugin info dict from discover_external_plugins
        class_name: Name of the class to load from the module

    Returns:
        The loaded class

    Raises:
        ImportError: If the module or class cannot be loaded
    """
    # If class was already loaded via entry point, return it
    if "class" in plugin_info:
        return plugin_info["class"]

    # Otherwise, import the module and get the class
    module = importlib.import_module(plugin_info["package_name"])
    return getattr(module, class_name)
