"""CLI commands for managing AI agent plugins."""

import argparse
import sys

from agent_manager.core import discover_agent_plugins, get_agent_names, run_agents
from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.utils import get_disabled_plugins, set_plugin_enabled


class AgentCommands:
    """Manages CLI commands for AI agent plugins."""

    @classmethod
    def add_cli_arguments(cls, subparsers) -> None:
        """Add agent-related CLI arguments.

        Args:
            subparsers: The argparse subparsers to add to
        """
        # Discover available plugins for the choices
        agent_plugin_names = get_agent_names()

        # Agents command group
        agents_parser = subparsers.add_parser("agents", help="Manage agent plugins")
        agents_subparsers = agents_parser.add_subparsers(dest="agents_command", help="Agent commands")

        # agents list
        agents_subparsers.add_parser("list", help="List available agent plugins")

        # agents enable
        enable_parser = agents_subparsers.add_parser("enable", help="Enable an agent plugin")
        enable_parser.add_argument("name", help="Agent name (e.g., claude)")

        # agents disable
        disable_parser = agents_subparsers.add_parser("disable", help="Disable an agent plugin")
        disable_parser.add_argument("name", help="Agent name (e.g., claude)")

        # Run command (default action)
        run_parser = subparsers.add_parser("run", help="Run an agent (default command)")
        run_parser.add_argument(
            "--agent",
            type=str,
            default="all",
            choices=["all"] + agent_plugin_names,
            help="Agent plugin to use (default: all agents)",
        )

    @classmethod
    def process_agents_command(cls, args: argparse.Namespace) -> None:
        """Process agents-related CLI commands.

        Args:
            args: Parsed command-line arguments
        """
        if not hasattr(args, "agents_command") or args.agents_command is None:
            message("No agents subcommand specified", MessageType.ERROR, VerbosityLevel.ALWAYS)
            message("Available commands: list, enable, disable", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            sys.exit(1)

        if args.agents_command == "list":
            cls.list_agents()
        elif args.agents_command == "enable":
            cls.enable_agent(args.name)
        elif args.agents_command == "disable":
            cls.disable_agent(args.name)

    @classmethod
    def list_agents(cls) -> None:
        """List all available agent plugins."""
        message("\n=== Available Agent Plugins ===\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Get disabled agents
        disabled = get_disabled_plugins().get("agents", [])

        plugins = discover_agent_plugins()

        if not plugins and not disabled:
            message("No agent plugins found.", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message(
                "\nTo install an agent plugin, use: pip install <plugin-package>",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message("Agent plugins have package names starting with 'am_agent_'", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            return

        if plugins:
            message("Installed agents:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            for agent_name in sorted(plugins.keys()):
                package_name = plugins[agent_name]["package_name"]
                message(f"  {agent_name} ({package_name})", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Show disabled agents
        if disabled:
            message("Disabled agents:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            for name in disabled:
                message(f"  {name} (disabled)", MessageType.WARNING, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("Use 'agent-manager agents enable <name>' to re-enable", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        total = len(plugins) + len(disabled)
        message(f"Total: {len(plugins)} enabled, {len(disabled)} disabled", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

    @classmethod
    def enable_agent(cls, name: str) -> None:
        """Enable an agent plugin.

        Args:
            name: Name of the agent to enable
        """
        if not set_plugin_enabled("agents", name, enabled=True):
            sys.exit(1)

    @classmethod
    def disable_agent(cls, name: str) -> None:
        """Disable an agent plugin.

        Args:
            name: Name of the agent to disable
        """
        if not set_plugin_enabled("agents", name, enabled=False):
            sys.exit(1)

    @classmethod
    def process_cli_command(cls, args, config_data: dict) -> None:
        """Process the run command for agents.

        Args:
            args: Parsed command-line arguments
            config_data: Configuration data with repo objects
        """
        # Determine which agents to run
        agents_to_run = [args.agent] if args.agent != "all" else ["all"]

        # Use the core module to run agents
        run_agents(agents_to_run, config_data)
