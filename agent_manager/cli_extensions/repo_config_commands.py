"""CLI commands for managing repo entries in the configuration.

This manages *config entries* (``repo add/remove/list``), not repo
*plugins* (which live under ``plugins repos``).
"""

import argparse

from agent_manager.config import Config
from agent_manager.output import MessageType, VerbosityLevel, message


class RepoConfigCommands:
    """Manages CLI commands for repo entries in the config."""

    @staticmethod
    def add_cli_arguments(subparsers) -> None:
        """Add repo config commands to the argument parser."""
        repo_parser = subparsers.add_parser(
            "repo",
            help="Manage repository entries in the configuration",
        )
        repo_sub = repo_parser.add_subparsers(
            dest="repo_command",
            help="Repo commands",
        )

        # repo list
        repo_sub.add_parser(
            "list",
            help="List configured repos",
        )

        # repo add
        add_parser = repo_sub.add_parser(
            "add",
            help="Add a repo to the configuration",
        )
        add_parser.add_argument("name", help="Repo name")
        add_parser.add_argument("url", help="Repository URL")
        add_parser.add_argument(
            "--type",
            dest="repo_type",
            help="Repository type (auto-detected if omitted)",
        )

        # repo remove
        rm_parser = repo_sub.add_parser(
            "remove",
            help="Remove a repo from the configuration",
        )
        rm_parser.add_argument("name", help="Repo name to remove")
        rm_parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Remove even if referenced in default_hierarchy or "
                "directory hierarchies (cascade-removes references)"
            ),
        )

    @classmethod
    def process_cli_command(
        cls,
        args: argparse.Namespace,
        config: Config,
    ) -> None:
        """Process repo config commands."""
        cmd = getattr(args, "repo_command", None)
        if cmd is None:
            cls._show_usage()
            return

        if cmd == "list":
            cls.list_repos(config)
        elif cmd == "add":
            config.add_repo(
                args.name,
                args.url,
                repo_type=getattr(args, "repo_type", None),
            )
        elif cmd == "remove":
            config.remove_repo(
                args.name,
                force=getattr(args, "force", False),
            )

    @staticmethod
    def _show_usage() -> None:
        message(
            "Usage: agent-manager repo <command>",
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
            "  list      List configured repos",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        message(
            "  add       Add a repo to the configuration",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        message(
            "  remove    Remove a repo from the configuration",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )

    @staticmethod
    def list_repos(config: Config) -> None:
        """List configured repos."""
        if not config.exists():
            message(
                "No configuration found. Run 'agent-manager config init'.",
                MessageType.WARNING,
                VerbosityLevel.ALWAYS,
            )
            return

        config_data = config.read()
        repos = config_data.get("repos", [])

        if not repos:
            message(
                "No repos configured.",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                "Use 'agent-manager repo add <name> <url>' to add one.",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            return

        message(
            "\n=== Configured Repos ===\n",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        for entry in repos:
            name = entry.get("name", "?")
            url = entry.get("url", "?")
            repo_type = entry.get("repo_type", "unknown")
            message(
                f"  {name} ({repo_type})",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                f"    URL: {url}",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )

        message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        message(
            f"Total: {len(repos)} repo(s)",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
