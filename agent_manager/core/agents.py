"""Agent discovery utilities for agent-manager."""

import sys
from pathlib import Path
from typing import Any

from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.utils import (
    discover_external_plugins,
    filter_disabled_plugins,
    load_plugin_class,
)

# Package prefix for agent plugins
AGENT_PLUGIN_PREFIX = "am_agent_"


def discover_agent_plugins(
    include_disabled: bool = False,
) -> dict[str, dict]:
    """Discover all available agent plugins.

    Agent plugins are discovered by searching for installed packages
    that start with 'am_agent_' prefix.

    Args:
        include_disabled: If True, include disabled agent plugins

    Returns:
        Dictionary mapping agent names to plugin info
    """
    plugins = discover_external_plugins(
        plugin_type="agent",
        package_prefix=AGENT_PLUGIN_PREFIX,
    )

    if not include_disabled:
        plugins = filter_disabled_plugins(plugins, "agents")

    return plugins


def get_agent_names() -> list[str]:
    """Get list of available agent plugin names.

    Returns:
        List of agent names (e.g., ["claude", "cursor"])
    """
    plugins = discover_agent_plugins()
    return sorted(plugins.keys())


def load_agent(
    agent_name: str, plugins: dict[str, dict] | None = None
):
    """Load an agent class by name.

    Args:
        agent_name: Name of the agent (e.g., "claude")
        plugins: Optional pre-discovered plugins dict.

    Returns:
        Instance of the Agent class

    Raises:
        SystemExit: If the agent cannot be loaded
    """
    if plugins is None:
        plugins = discover_agent_plugins()

    if agent_name not in plugins:
        message(
            f"Agent '{agent_name}' not found",
            MessageType.ERROR,
            VerbosityLevel.ALWAYS,
        )
        available = (
            ", ".join(sorted(plugins.keys())) if plugins else "none"
        )
        message(
            f"Available agents: {available}",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        sys.exit(1)

    plugin_info = plugins[agent_name]
    message(
        f"Loading agent plugin: {plugin_info['package_name']}",
        MessageType.DEBUG,
        VerbosityLevel.DEBUG,
    )

    try:
        agent_class = load_plugin_class(plugin_info, "Agent")
        return agent_class()
    except Exception as e:
        message(
            f"Failed to load agent '{agent_name}': {e}",
            MessageType.ERROR,
            VerbosityLevel.ALWAYS,
        )
        sys.exit(1)


def run_agents(
    agent_names: list[str],
    repos: list[dict[str, Any]],
    base_directory: Path,
    merger_settings: dict[str, Any] | None = None,
) -> None:
    """Run one or more agents with the given configuration.

    Args:
        agent_names: List of agent names to run, or ["all"] for all
        repos: Ordered list of repo entries (lowest to highest priority)
        base_directory: Resolved target directory
        merger_settings: Optional per-merger settings from config
    """
    plugins = discover_agent_plugins()

    agents_to_run = (
        sorted(plugins.keys())
        if agent_names == ["all"] or "all" in agent_names
        else agent_names
    )

    if not agents_to_run:
        message(
            "No agent plugins found",
            MessageType.ERROR,
            VerbosityLevel.ALWAYS,
        )
        message(
            "Install an agent plugin (e.g., pip install -e am_agent_claude)",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        sys.exit(1)

    for agent_name in agents_to_run:
        message(
            f"\nInitializing agent: {agent_name}",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )

        try:
            agent = load_agent(agent_name, plugins)
            agent.update(repos, base_directory, merger_settings)
        except SystemExit:
            raise
        except Exception as e:
            message(
                f"Failed to run agent '{agent_name}': {e}",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(1)
