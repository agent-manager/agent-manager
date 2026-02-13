#!/usr/bin/env python

"""Hierarchical Manager for AI Agents."""

import argparse
import sys

from agent_manager.cli_extensions import AgentCommands, ConfigCommands, MergerCommands, RepoCommands
from agent_manager.config import Config
from agent_manager.core import create_default_merger_registry, update_repositories
from agent_manager.output import MessageType, VerbosityLevel, get_output, message

# Grouped command help text
COMMAND_GROUPS = """
runtime commands:
  run                 Run an agent (default command)
  update              Update all repositories in the hierarchy

plugin commands:
  agents              Manage agent plugins
  repos               Manage repository types
  mergers             Manage content mergers

configuration commands:
  config              Manage configuration
"""


class GroupedHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom formatter that hides the subparser choices from positional arguments."""

    def _metavar_formatter(self, action, default_metavar):
        if action.choices is not None:
            # For subparser actions, just show the metavar without listing choices
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
    # Parse arguments with subcommands
    parser = argparse.ArgumentParser(
        description="Manage your AI agents from a hierarchy of directories",
        formatter_class=GroupedHelpFormatter,
        epilog=COMMAND_GROUPS,
    )
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity (-v, -vv, -vvv)")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")

    # Use metavar='' to hide the default {cmd1,cmd2,...} display
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # Add CLI arguments from all command extensions
    AgentCommands.add_cli_arguments(subparsers)
    RepoCommands.add_cli_arguments(subparsers)
    ConfigCommands.add_cli_arguments(subparsers)
    MergerCommands.add_cli_arguments(subparsers)

    args = parser.parse_args()

    # Configure output system
    output_mgr = get_output()
    output_mgr.verbosity = args.verbose
    output_mgr.use_color = not args.no_color and sys.stdout.isatty()

    message(f"Verbosity level: {args.verbose}", MessageType.DEBUG, VerbosityLevel.DEBUG)
    message(f"Command: {args.command}", MessageType.DEBUG, VerbosityLevel.DEBUG)

    # Initialize configuration manager
    config = Config()
    config.ensure_directories()

    # Handle mergers subcommands
    if args.command == "mergers":
        # Create a default merger registry for CLI commands
        merger_registry = create_default_merger_registry()
        merger_commands = MergerCommands(merger_registry)
        merger_commands.process_cli_command(args, config)
        return

    # Handle agents subcommands
    if args.command == "agents":
        AgentCommands.process_agents_command(args)
        return

    # Handle repos subcommands
    if args.command == "repos":
        RepoCommands.process_repos_command(args)
        return

    # Handle config subcommands
    if args.command == "config":
        ConfigCommands.process_cli_command(args, config)
        return

    # If no command specified, show help
    if args.command is None:
        parser.print_help()
        return

    # Initialize config if needed (skip if already exists)
    config.initialize(skip_if_already_created=True)

    # Load config data (this instantiates all repo objects)
    config_data = config.read()

    # Update the repositories (for both 'update' and 'run' commands)
    update_repositories(config_data, force=getattr(args, "force", False))

    # If this was just an update command, we're done
    if args.command == "update":
        return

    # Default to run command
    if args.command == "run":
        AgentCommands.process_cli_command(args, config_data)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
