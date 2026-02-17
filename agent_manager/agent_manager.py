#!/usr/bin/env python

"""Hierarchical Manager for AI Agents."""

import argparse
import sys

from agent_manager.cli_extensions import (
    AgentCommands,
    ConfigCommands,
    DirectoryCommands,
    MergerCommands,
    PluginCommands,
    RepoCommands,
    RepoConfigCommands,
)
from agent_manager.config import Config
from agent_manager.core import create_default_merger_registry, update_repositories
from agent_manager.output import MessageType, VerbosityLevel, get_output, message

# Grouped command help text
COMMAND_GROUPS = """
runtime commands:
  run                 Run agent(s) for configured directories
  update              Update all repositories

config entity commands:
  repo                Manage repo entries in the configuration
  directory           Manage target directories in the configuration

configuration file commands:
  config              Manage the configuration file

plugin commands:
  plugins             Manage agent, repo, and merger plugins

legacy aliases (use 'plugins' instead):
  agents              Alias for 'plugins agents'
  repos               Alias for 'plugins repos'
  mergers             Alias for 'plugins mergers'
"""


class GroupedHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom formatter that hides the subparser choices from positional arguments."""

    def _metavar_formatter(self, action, default_metavar):
        if action.choices is not None:
            result = action.metavar if action.metavar is not None else ""

            def format_fn(tuple_size):
                if isinstance(result, tuple):
                    return result
                return (result,) * tuple_size

            return format_fn
        return super()._metavar_formatter(action, default_metavar)

    def _format_action(self, action):
        # Skip formatting subparser actions entirely (we show them in epilog)
        if isinstance(action, argparse._SubParsersAction):
            return ""
        return super()._format_action(action)


def main() -> None:
    """Main entry point for the agent-manager CLI."""
    parser = argparse.ArgumentParser(
        description="Manage your AI agents from a hierarchy of directories",
        formatter_class=GroupedHelpFormatter,
        epilog=COMMAND_GROUPS,
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Increase verbosity (-v, -vv, -vvv)",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable colored output",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # Register all command parsers
    AgentCommands.add_cli_arguments(subparsers)     # run + agents
    RepoCommands.add_cli_arguments(subparsers)      # update + repos (legacy)
    ConfigCommands.add_cli_arguments(subparsers)     # config
    MergerCommands.add_cli_arguments(subparsers)     # mergers (legacy)
    RepoConfigCommands.add_cli_arguments(subparsers)  # repo
    DirectoryCommands.add_cli_arguments(subparsers)   # directory
    PluginCommands.add_cli_arguments(subparsers)      # plugins

    args = parser.parse_args()

    # Configure output system
    output_mgr = get_output()
    output_mgr.verbosity = args.verbose
    output_mgr.use_color = not args.no_color and sys.stdout.isatty()

    message(
        f"Verbosity level: {args.verbose}",
        MessageType.DEBUG,
        VerbosityLevel.DEBUG,
    )
    message(
        f"Command: {args.command}",
        MessageType.DEBUG,
        VerbosityLevel.DEBUG,
    )

    # Initialize configuration manager
    config = Config()
    config.ensure_directories()

    # ------------------------------------------------------------------
    # Commands that return early (no repo update needed)
    # ------------------------------------------------------------------

    # plugins
    if args.command == "plugins":
        merger_registry = create_default_merger_registry()
        pc = PluginCommands(merger_registry)
        pc.process_cli_command(args, config)
        return

    # Legacy aliases -> delegate to same logic
    if args.command == "mergers":
        merger_registry = create_default_merger_registry()
        merger_commands = MergerCommands(merger_registry)
        merger_commands.process_cli_command(args, config)
        return

    if args.command == "agents":
        AgentCommands.process_agents_command(args)
        return

    if args.command == "repos":
        RepoCommands.process_repos_command(args)
        return

    # Config entity commands
    if args.command == "repo":
        RepoConfigCommands.process_cli_command(args, config)
        return

    if args.command == "directory":
        DirectoryCommands.process_cli_command(args, config)
        return

    # Config file commands
    if args.command == "config":
        ConfigCommands.process_cli_command(args, config)
        return

    # No command specified
    if args.command is None:
        parser.print_help()
        return

    # ------------------------------------------------------------------
    # Runtime commands (require config + repo update)
    # ------------------------------------------------------------------

    # Initialize config if needed (skip if already exists)
    config.initialize(skip_if_already_created=True)

    # Load config data
    config_data = config.read()

    # Update the repositories
    update_repositories(
        config_data, force=getattr(args, "force", False),
    )

    if args.command == "update":
        return

    if args.command == "run":
        AgentCommands.process_cli_command(args, config_data)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
