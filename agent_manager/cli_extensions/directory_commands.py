"""CLI commands for managing target directories in the configuration."""

import argparse
from pathlib import Path

from agent_manager.config import Config
from agent_manager.core.manifest import read_manifest
from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.plugins.repos.abstract_repo import AbstractRepo


class DirectoryCommands:
    """Manages CLI commands for target directories in the config."""

    @staticmethod
    def add_cli_arguments(subparsers) -> None:
        """Add directory-related CLI arguments."""
        dir_parser = subparsers.add_parser(
            "directory",
            help="Manage target directories in the configuration",
        )
        dir_sub = dir_parser.add_subparsers(
            dest="directory_command",
            help="Directory commands",
        )

        # directory list
        dir_sub.add_parser(
            "list",
            help="List configured target directories",
        )

        # directory add
        add_parser = dir_sub.add_parser(
            "add",
            help="Add a target directory to the configuration",
        )
        add_parser.add_argument(
            "path",
            help="Directory path (use HOME for home directory)",
        )
        add_parser.add_argument(
            "--type",
            dest="dir_type",
            help="Directory VCS type (auto-detected if omitted)",
        )
        add_parser.add_argument(
            "--agents",
            nargs="+",
            metavar="NAME",
            help="Agent list for this directory",
        )
        add_parser.add_argument(
            "--hierarchy",
            nargs="+",
            metavar="REPO",
            help="Repo hierarchy for this directory",
        )

        # directory remove
        rm_parser = dir_sub.add_parser(
            "remove",
            help="Remove a target directory from the configuration",
        )
        rm_parser.add_argument("path", help="Directory path to remove")

    @classmethod
    def process_cli_command(
        cls,
        args: argparse.Namespace,
        config: Config,
    ) -> None:
        """Process directory commands."""
        cmd = getattr(args, "directory_command", None)
        if cmd is None:
            cls._show_usage()
            return

        if cmd == "list":
            cls.list_directories(config)
        elif cmd == "add":
            cls.add_directory(args, config)
        elif cmd == "remove":
            config.remove_directory(args.path)

    @staticmethod
    def _show_usage() -> None:
        message(
            "Usage: agent-manager directory <command>",
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
            "  list      List configured target directories",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        message(
            "  add       Add a target directory",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        message(
            "  remove    Remove a target directory",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )

    @staticmethod
    def list_directories(config: Config) -> None:
        """List configured directories with manifest info."""
        if not config.exists():
            message(
                "No configuration found. "
                "Run 'agent-manager config init'.",
                MessageType.WARNING,
                VerbosityLevel.ALWAYS,
            )
            return

        config_data = config.read()
        directories = config_data.get("directories", {})

        if not directories:
            message(
                "No directories configured.",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                "Use 'agent-manager directory add <path>' to add one.",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            return

        message(
            "\n=== Configured Directories ===\n",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )

        for path_str, dir_config in sorted(directories.items()):
            if dir_config is None:
                dir_config = {}

            # Resolve path for detection
            resolved = Path(
                path_str.replace("HOME", str(Path.home()))
            ).expanduser()

            dir_type = dir_config.get("type", "auto")
            detected = AbstractRepo.detect_directory(resolved)
            agents = dir_config.get("agents")
            hierarchy = dir_config.get("hierarchy")

            agents_str = ", ".join(agents) if agents else "(defaults)"
            hierarchy_str = (
                " -> ".join(hierarchy) if hierarchy else "(defaults)"
            )

            # Read manifest for last_synced
            manifest = read_manifest(resolved)
            last_synced = manifest.get("last_synced", "never")
            file_count = len(manifest.get("files", []))

            message(
                f"  {path_str}",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                f"    Type: {dir_type} (detected: {detected})",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                f"    Agents: {agents_str}",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                f"    Hierarchy: {hierarchy_str}",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                f"    Last synced: {last_synced} "
                f"({file_count} managed files)",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

    @staticmethod
    def add_directory(args: argparse.Namespace, config: Config) -> None:
        """Add a directory to the config with optional auto-detection."""
        dir_type = getattr(args, "dir_type", None)

        if dir_type is None:
            resolved = Path(
                args.path.replace("HOME", str(Path.home()))
            ).expanduser()
            detected = AbstractRepo.detect_directory(resolved)
            if detected:
                dir_type = detected
                message(
                    f"Auto-detected type: {detected}",
                    MessageType.INFO,
                    VerbosityLevel.VERBOSE,
                )

        config.add_directory(
            args.path,
            dir_type=dir_type,
            agents=getattr(args, "agents", None),
            hierarchy=getattr(args, "hierarchy", None),
        )
