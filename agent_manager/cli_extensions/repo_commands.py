"""CLI commands for managing repositories."""

import argparse
import sys

from agent_manager.core import discover_repo_types
from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.utils import get_disabled_plugins, set_plugin_enabled


class RepoCommands:
    """Manages CLI commands for repository operations."""

    @staticmethod
    def add_cli_arguments(subparsers) -> None:
        """Add repository-related CLI arguments.

        Args:
            subparsers: The argparse subparsers to add to
        """
        # Repos command group
        repos_parser = subparsers.add_parser("repos", help="Manage repository types")
        repos_subparsers = repos_parser.add_subparsers(dest="repos_command", help="Repository commands")

        # repos list
        repos_subparsers.add_parser("list", help="List available repository types")

        # repos enable
        enable_parser = repos_subparsers.add_parser("enable", help="Enable a repository type plugin")
        enable_parser.add_argument("name", help="Repository type name (e.g., git)")

        # repos disable
        disable_parser = repos_subparsers.add_parser("disable", help="Disable a repository type plugin")
        disable_parser.add_argument("name", help="Repository type name (e.g., git)")

        # Update command (keep as separate command for backwards compatibility)
        update_parser = subparsers.add_parser(
            "update", help="Update all repositories in the hierarchy (does not update agent configs)"
        )
        update_parser.add_argument(
            "--force", action="store_true", help="Force update even if repository appears up to date"
        )

    @staticmethod
    def process_repos_command(args: argparse.Namespace) -> None:
        """Process repos-related CLI commands.

        Args:
            args: Parsed command-line arguments
        """
        if not hasattr(args, "repos_command") or args.repos_command is None:
            message("No repos subcommand specified", MessageType.ERROR, VerbosityLevel.ALWAYS)
            message("Available commands: list, enable, disable", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            sys.exit(1)

        if args.repos_command == "list":
            RepoCommands.list_repos()
        elif args.repos_command == "enable":
            RepoCommands.enable_repo(args.name)
        elif args.repos_command == "disable":
            RepoCommands.disable_repo(args.name)

    @staticmethod
    def list_repos() -> None:
        """List all available repository types."""
        message("\n=== Available Repository Types ===\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Get disabled repos
        disabled = get_disabled_plugins().get("repos", [])

        repo_types = discover_repo_types()

        if not repo_types and not disabled:
            message("No repository type plugins found.", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            return

        if repo_types:
            message("Installed repository types:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            for repo_class in repo_types:
                repo_type = repo_class.REPO_TYPE
                module = repo_class.__module__
                message(f"  {repo_type} ({module})", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Show disabled repo types
        if disabled:
            message("Disabled repository types:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            for name in disabled:
                message(f"  {name} (disabled)", MessageType.WARNING, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("Use 'agent-manager repos enable <name>' to re-enable", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        message(f"Total: {len(repo_types)} enabled, {len(disabled)} disabled", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

    @staticmethod
    def enable_repo(name: str) -> None:
        """Enable a repository type plugin.

        Args:
            name: Name of the repository type to enable
        """
        if not set_plugin_enabled("repos", name, enabled=True):
            sys.exit(1)

    @staticmethod
    def disable_repo(name: str) -> None:
        """Disable a repository type plugin.

        Args:
            name: Name of the repository type to disable
        """
        if not set_plugin_enabled("repos", name, enabled=False):
            sys.exit(1)

