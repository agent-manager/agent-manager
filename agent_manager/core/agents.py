"""Agent discovery utilities for agent-manager."""

import sys

from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.utils import discover_external_plugins, filter_disabled_plugins, load_plugin_class


# Package prefix for agent plugins
AGENT_PLUGIN_PREFIX = "am_agent_"


def discover_agent_plugins(include_disabled: bool = False) -> dict[str, dict]:
    """Discover all available agent plugins.

    Agent plugins are discovered by searching for installed packages
    that start with 'am_agent_' prefix.

    Args:
        include_disabled: If True, include disabled agent plugins

    Returns:
        Dictionary mapping agent names to plugin info:
        {
            "claude": {
                "package_name": "am_agent_claude",
                "source": "package"
            }
        }
    """
    plugins = discover_external_plugins(
        plugin_type="agent",
        package_prefix=AGENT_PLUGIN_PREFIX,
    )

    # Filter out disabled plugins unless requested
    if not include_disabled:
        plugins = filter_disabled_plugins(plugins, "agents")

    return plugins


def get_agent_names() -> list[str]:
    """Get list of available agent plugin names.

    Returns:
        List of agent names (e.g., ["claude", "copilot"])
    """
    plugins = discover_agent_plugins()
    return sorted(plugins.keys())


def load_agent(agent_name: str, plugins: dict[str, dict] | None = None):
    """Load an agent class by name.

    Args:
        agent_name: Name of the agent (e.g., "claude")
        plugins: Optional pre-discovered plugins dict. If None, will discover.

    Returns:
        Instance of the Agent class

    Raises:
        SystemExit: If the agent cannot be loaded
    """
    if plugins is None:
        plugins = discover_agent_plugins()

    if agent_name not in plugins:
        message(f"Agent '{agent_name}' not found", MessageType.ERROR, VerbosityLevel.ALWAYS)
        available = ", ".join(sorted(plugins.keys())) if plugins else "none"
        message(f"Available agents: {available}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        sys.exit(1)

    plugin_info = plugins[agent_name]
    message(f"Loading agent plugin: {plugin_info['package_name']}", MessageType.DEBUG, VerbosityLevel.DEBUG)

    try:
        agent_class = load_plugin_class(plugin_info, "Agent")
        return agent_class()
    except Exception as e:
        message(f"Failed to load agent '{agent_name}': {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
        sys.exit(1)


def run_agents(agent_names: list[str], config_data: dict, scope: str = "default") -> None:
    """Run one or more agents with the given configuration.

    Args:
        agent_names: List of agent names to run, or ["all"] for all agents
        config_data: Configuration data with repo objects
        scope: Configuration scope to use (default: "default")
    """
    plugins = discover_agent_plugins()

    # Determine which agents to run
    if agent_names == ["all"] or "all" in agent_names:
        agents_to_run = sorted(plugins.keys())
    else:
        agents_to_run = agent_names

    # Check if we have any agents
    if not agents_to_run:
        message("No agent plugins found", MessageType.ERROR, VerbosityLevel.ALWAYS)
        message(
            "Please install an agent plugin (e.g., pip install -e am_agent_claude)",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        sys.exit(1)

    # Run each agent
    for agent_name in agents_to_run:
        message(f"\nInitializing agent: {agent_name}", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        try:
            agent = load_agent(agent_name, plugins)

            # Validate scope for this agent
            available_scopes = agent.get_scope_names()
            if scope not in available_scopes:
                message(
                    f"Scope '{scope}' not supported by agent '{agent_name}'",
                    MessageType.ERROR,
                    VerbosityLevel.ALWAYS,
                )
                message(
                    f"Available scopes: {', '.join(available_scopes)}",
                    MessageType.NORMAL,
                    VerbosityLevel.ALWAYS,
                )
                sys.exit(1)

            message(f"Using scope: {scope}", MessageType.INFO, VerbosityLevel.VERBOSE)
            agent.update(config_data, scope=scope)
        except SystemExit:
            raise
        except Exception as e:
            message(f"Failed to initialize agent '{agent_name}': {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

