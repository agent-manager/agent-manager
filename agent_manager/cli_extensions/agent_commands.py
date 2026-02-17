"""CLI commands for managing AI agent plugins."""

import argparse
import sys
from pathlib import Path

from agent_manager.core import discover_agent_plugins, get_agent_names, run_agents
from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.utils import get_disabled_plugins, set_plugin_enabled


def resolve_directory_path(raw: str) -> Path:
    """Resolve a directory path from CLI input.

    Handles the ``HOME`` keyword, ``~`` prefix, and resolves to an
    absolute path so it can be matched against config entries.

    Args:
        raw: Raw path string from CLI (e.g. ``HOME``, ``~/GIT/...``,
             ``/absolute/path``)

    Returns:
        Resolved absolute Path
    """
    if raw == "HOME" or raw.startswith("HOME/"):
        raw = raw.replace("HOME", str(Path.home()), 1)
    return Path(raw).expanduser().resolve()


class AgentCommands:
    """Manages CLI commands for AI agent plugins."""

    @classmethod
    def add_cli_arguments(cls, subparsers) -> None:
        """Add agent-related CLI arguments.

        Args:
            subparsers: The argparse subparsers to add to
        """
        agent_plugin_names = get_agent_names()

        # Agents command group (plugin management)
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
                "the specified agent(s) in configured directories. "
                "Either --all or at least one --directory is required."
            ),
        )

        target_group = run_parser.add_mutually_exclusive_group()
        target_group.add_argument(
            "--all",
            action="store_true",
            dest="run_all",
            help="Run against all configured directories",
        )
        target_group.add_argument(
            "--directory",
            action="append",
            dest="directories",
            metavar="PATH",
            help=(
                "Target directory to run against (repeatable). "
                "Use HOME for home directory."
            ),
        )

        run_parser.add_argument(
            "--agent",
            action="append",
            dest="agents",
            metavar="NAME",
            choices=agent_plugin_names or None,
            help=(
                "Agent plugin to use (repeatable). "
                "Omit for all agents."
            ),
        )
        run_parser.add_argument(
            "--force",
            action="store_true",
            help="Override safety checks (clobber warnings, type mismatches)",
        )
        run_parser.add_argument(
            "--non-interactive",
            action="store_true",
            help=(
                "Suppress all prompts; skip anything questionable. "
                "Non-zero exit if anything was skipped (for cron/CI)."
            ),
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

        This is a transitional implementation.  The full directory-iteration
        loop will be implemented in PR 7 (main loop rewrite).

        Args:
            args: Parsed command-line arguments
            config_data: V2 configuration data with repos, directories, etc.
        """
        # Validate that --all or --directory was provided
        run_all = getattr(args, "run_all", False)
        directories = getattr(args, "directories", None)

        if not run_all and not directories:
            message(
                "Error: specify --all or at least one --directory",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(2)

        # Determine which agents to run
        agents = getattr(args, "agents", None)
        agents_to_run = agents if agents else ["all"]

        force = getattr(args, "force", False)
        non_interactive = getattr(args, "non_interactive", False)

        # Resolve requested directories
        resolved_dirs = (
            None if run_all
            else [resolve_directory_path(d) for d in directories]
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

        if force:
            message(
                "Force mode enabled.",
                MessageType.DEBUG,
                VerbosityLevel.DEBUG,
            )
        if non_interactive:
            message(
                "Non-interactive mode enabled.",
                MessageType.DEBUG,
                VerbosityLevel.DEBUG,
            )
        if resolved_dirs:
            for d in resolved_dirs:
                message(
                    f"Target directory: {d}",
                    MessageType.DEBUG,
                    VerbosityLevel.DEBUG,
                )

        repos = config_data.get("repos", [])
        merger_settings = config_data.get("mergers", {})
        base_directory = Path.home()

        run_agents(
            agents_to_run, repos, base_directory, merger_settings,
        )
