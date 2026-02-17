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
        agent_plugin_names = get_agent_names()

        # Agents command group
        agents_parser = subparsers.add_parser(
            "agents", help="Manage agent plugins",
        )
        agents_subparsers = agents_parser.add_subparsers(
            dest="agents_command", help="Agent commands",
        )

        agents_subparsers.add_parser(
            "list",
            help="List available agent plugins",
            description=(
                "Show all discovered agent plugins, including their "
                "package names and enabled/disabled status."
            ),
        )

        enable_parser = agents_subparsers.add_parser(
            "enable",
            help="Enable an agent plugin",
        )
        enable_parser.add_argument("name", help="Agent name (e.g., claude)")

        disable_parser = agents_subparsers.add_parser(
            "disable",
            help="Disable an agent plugin",
        )
        disable_parser.add_argument("name", help="Agent name (e.g., claude)")

        # Run command
        run_parser = subparsers.add_parser(
            "run",
            help="Run agent(s) for configured directories",
            description=(
                "Merge configurations from repos and apply them to "
                "the specified agent(s) in configured directories."
            ),
        )
        run_parser.add_argument(
            "--agent",
            type=str,
            default="all",
            choices=["all"] + agent_plugin_names,
            help="Agent plugin to use (default: all agents)",
        )

    @classmethod
    def process_agents_command(
        cls, args: argparse.Namespace,
    ) -> None:
        """Process agents-related CLI commands."""
        if (
            not hasattr(args, "agents_command")
            or args.agents_command is None
        ):
            message(
                "Usage: agent-manager agents <command>",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message(
                "Available commands:",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                "  list      List available agent plugins",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                "  enable    Enable an agent plugin",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                "  disable   Disable an agent plugin",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            return

        if args.agents_command == "list":
            cls.list_agents()
        elif args.agents_command == "enable":
            cls.enable_agent(args.name)
        elif args.agents_command == "disable":
            cls.disable_agent(args.name)

    @classmethod
    def list_agents(cls) -> None:
        """List all available agent plugins."""
        message(
            "\n=== Available Agent Plugins ===\n",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )

        disabled = get_disabled_plugins().get("agents", [])
        plugins = discover_agent_plugins()

        if not plugins and not disabled:
            message(
                "No agent plugins found.",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                "\nTo install an agent plugin, use: "
                "pip install <plugin-package>",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                "Agent plugins have package names starting "
                "with 'am_agent_'",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            return

        if plugins:
            message(
                "Installed agents:",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            for agent_name in sorted(plugins.keys()):
                package_name = plugins[agent_name]["package_name"]
                message(
                    f"  {agent_name} ({package_name})",
                    MessageType.NORMAL,
                    VerbosityLevel.ALWAYS,
                )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        if disabled:
            message(
                "Disabled agents:",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            for name in disabled:
                message(
                    f"  {name} (disabled)",
                    MessageType.WARNING,
                    VerbosityLevel.ALWAYS,
                )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message(
                "Use 'agent-manager agents enable <name>' to re-enable",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        message(
            f"Total: {len(plugins)} enabled, {len(disabled)} disabled",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

    @classmethod
    def enable_agent(cls, name: str) -> None:
        """Enable an agent plugin."""
        if not set_plugin_enabled("agents", name, enabled=True):
            sys.exit(1)

    @classmethod
    def disable_agent(cls, name: str) -> None:
        """Disable an agent plugin."""
        if not set_plugin_enabled("agents", name, enabled=False):
            sys.exit(1)

    @classmethod
    def process_cli_command(cls, args, config_data: dict) -> None:
        """Process the run command for agents.

        This is a transitional implementation. The full directory-iteration
        loop will be implemented in PR 7 (main loop rewrite).

        Args:
            args: Parsed command-line arguments
            config_data: V2 configuration data with repos, directories, etc.
        """
        agents_to_run = (
            [args.agent] if args.agent != "all" else ["all"]
        )

        # TODO(PR 7): iterate config_data["directories"], resolve
        # hierarchy per directory, and call run_agents for each.
        # For now, just pass the repos list directly.
        message(
            "Warning: full directory-based run loop not yet implemented "
            "(PR 7). Running agents against all repos.",
            MessageType.WARNING,
            VerbosityLevel.VERBOSE,
        )

        from pathlib import Path

        repos = config_data.get("repos", [])
        merger_settings = config_data.get("mergers", {})
        base_directory = Path.home()

        run_agents(
            agents_to_run, repos, base_directory, merger_settings,
        )
