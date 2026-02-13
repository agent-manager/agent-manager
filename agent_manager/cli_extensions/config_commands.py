"""CLI commands for managing configuration."""

import argparse
import sys

import yaml

from agent_manager.config import Config
from agent_manager.core import create_repo
from agent_manager.output import MessageType, VerbosityLevel, message


class ConfigCommands:
    """Manages configuration-related CLI commands."""

    @staticmethod
    def add_cli_arguments(subparsers) -> None:
        """Add config subcommands to the argument parser.

        Args:
            subparsers: The subparsers object to add commands to
        """
        # Config command group
        config_parser = subparsers.add_parser("config", help="Manage configuration")
        config_subparsers = config_parser.add_subparsers(dest="config_command", help="Configuration commands")

        # config init
        config_subparsers.add_parser(
            "init",
            help="Initialize or reinitialize configuration",
            description="Create a new configuration file at ~/.agent-manager/config.yaml through an interactive setup wizard. If a configuration already exists, it will be re-initialized.",
        )

        # config show
        show_parser = config_subparsers.add_parser(
            "show",
            help="Display current hierarchy",
            description="Display the current configuration hierarchy, showing each level's name, repository type, and URL in priority order (lowest to highest).",
        )
        show_parser.add_argument("--resolve-paths", action="store_true", help="Resolve file:// URLs to absolute paths")

        # config add
        add_parser = config_subparsers.add_parser(
            "add",
            help="Add a new hierarchy level",
            description="Add a new hierarchy level with a name and repository URL. The level is appended to the end (highest priority) unless --position is specified.",
        )
        add_parser.add_argument("name", help="Name of the hierarchy level")
        add_parser.add_argument("url", help="Repository URL (git URL or file:// path)")
        add_parser.add_argument("--position", type=int, help="Position to insert (0-based, default: append to end)")

        # config remove
        remove_parser = config_subparsers.add_parser(
            "remove",
            help="Remove a hierarchy level",
            description="Remove a hierarchy level by name from the configuration. This does not delete any cached repository data on disk.",
        )
        remove_parser.add_argument("name", help="Name of the hierarchy level to remove")

        # config update
        update_parser = config_subparsers.add_parser(
            "update",
            help="Update an existing hierarchy level",
            description="Change the URL or name of an existing hierarchy level. At least one of --url or --rename must be provided.",
        )
        update_parser.add_argument("name", help="Name of the hierarchy level to update")
        update_parser.add_argument("--url", help="New repository URL (git URL or file:// path)")
        update_parser.add_argument("--rename", help="New name for the hierarchy level")

        # config move
        move_parser = config_subparsers.add_parser(
            "move",
            help="Move a hierarchy level to a new position",
            description="Change the position of a hierarchy level within the priority order. Levels later in the list have higher priority and their values take precedence during merging.",
        )
        move_parser.add_argument("name", help="Name of the hierarchy level to move")
        move_group = move_parser.add_mutually_exclusive_group(required=True)
        move_group.add_argument("--position", type=int, help="New position (0-based)")
        move_group.add_argument("--up", action="store_true", help="Move up one position")
        move_group.add_argument("--down", action="store_true", help="Move down one position")

        # config validate
        config_subparsers.add_parser(
            "validate",
            help="Validate all repository URLs",
            description="Check that all repository URLs in the hierarchy are valid and accessible. Reports which repositories pass or fail validation.",
        )

        # config export
        export_parser = config_subparsers.add_parser(
            "export",
            help="Export configuration to a file or stdout",
            description="Export the current configuration as YAML to a file or to stdout. Useful for backing up or sharing configurations.",
        )
        export_parser.add_argument("file", nargs="?", help="Output file (default: stdout)")

        # config import
        import_parser = config_subparsers.add_parser(
            "import",
            help="Import configuration from a file",
            description="Import a configuration from a YAML file, replacing the current configuration. You will be prompted before overwriting an existing configuration.",
        )
        import_parser.add_argument("file", help="Input file to import")

        # config where
        config_subparsers.add_parser(
            "where",
            help="Show configuration file location",
            description="Show the file paths for the configuration file, config directory, and repos directory, along with whether each exists on disk.",
        )

    @staticmethod
    def process_cli_command(args: argparse.Namespace, config: Config) -> None:
        """Process config CLI commands.

        Args:
            args: Parsed command-line arguments
            config: Config instance to operate on
        """
        if args.config_command is None:
            # No subcommand provided, show available commands
            message("Usage: agent-manager config <command>", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("Available commands:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  init      Initialize or reinitialize configuration", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  show      Display current hierarchy", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  add       Add a new hierarchy level", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  remove    Remove a hierarchy level", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  update    Update an existing hierarchy level", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  move      Move a hierarchy level to a new position", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  validate  Validate all repository URLs", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  export    Export configuration to a file or stdout", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  import    Import configuration from a file", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  where     Show configuration file location", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            return
        elif args.config_command == "init":
            config.initialize(skip_if_already_created=False)
        elif args.config_command == "show":
            resolve = getattr(args, "resolve_paths", False)
            ConfigCommands.display(config, resolve_paths=resolve)
        elif args.config_command == "add":
            config.add_level(args.name, args.url, args.position)
        elif args.config_command == "remove":
            config.remove_level(args.name)
        elif args.config_command == "update":
            config.update_level(args.name, args.url, args.rename)
        elif args.config_command == "move":
            direction = None
            if getattr(args, "up", False):
                direction = "up"
            elif getattr(args, "down", False):
                direction = "down"
            config.move_level(args.name, args.position, direction)
        elif args.config_command == "validate":
            ConfigCommands.validate_all(config)
        elif args.config_command == "export":
            output_file = getattr(args, "file", None)
            ConfigCommands.export_config(config, output_file)
        elif args.config_command == "import":
            ConfigCommands.import_config(config, args.file)
        elif args.config_command == "where":
            ConfigCommands.show_location(config)
        else:
            # This shouldn't happen if argparse is set up correctly
            message("Unknown config command", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

    @staticmethod
    def display(config: Config, resolve_paths: bool = False) -> None:
        """Display the current hierarchy configuration.

        Args:
            config: Config instance
            resolve_paths: If True, show resolved paths for repositories
        """
        if not config.exists():
            message(
                "No configuration file found. Run without arguments to create one.",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(1)

        config_data = config.read()
        message("\nCurrent Hierarchy (lowest to highest priority):\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        for idx, entry in enumerate(config_data["hierarchy"], 1):
            priority = "→" * idx
            message(f"  {priority} {entry['name']}", MessageType.NORMAL, VerbosityLevel.ALWAYS)

            message(f"      Type: {entry.get('repo_type', 'unknown')}", MessageType.NORMAL, VerbosityLevel.ALWAYS)

            url = entry["url"]
            message(f"      URL: {url}", MessageType.NORMAL, VerbosityLevel.ALWAYS)

            # Use pluggable repo architecture for resolved display
            if resolve_paths:
                try:
                    # Create temporary repo instance for display
                    repo = create_repo(entry["name"], entry["url"], config.repos_directory, entry["repo_type"])
                    resolved = repo.get_display_url()
                    # Only show if different from original URL
                    if resolved != url:
                        message(f"      Resolved: {resolved}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
                except Exception as e:
                    message(f"Failed to resolve path for {entry['name']}: {e}", MessageType.DEBUG, VerbosityLevel.DEBUG)

            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

    @staticmethod
    def validate_all(config: Config) -> None:
        """Validate all repository URLs in the configuration.

        Args:
            config: Config instance
        """
        if not config.exists():
            message(
                "No configuration file found. Run without arguments to create one.",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(1)

        config_data = config.read()
        message("\nValidating all repositories...\n", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)

        all_valid = True
        for idx, entry in enumerate(config_data["hierarchy"]):
            name = entry["name"]
            url = entry["url"]

            total = len(config_data["hierarchy"])
            message(f"[{idx + 1}/{total}] {name}: {url}", MessageType.NORMAL, VerbosityLevel.ALWAYS)

            if config.validate_repo_url(url):
                message("  ✓ Valid", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
            else:
                message("  ✗ Invalid or inaccessible", MessageType.ERROR, VerbosityLevel.ALWAYS)
                all_valid = False

        message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        if all_valid:
            message("✓ All repositories are valid and accessible!", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
        else:
            message(
                "Some repositories failed validation. Please check the errors above.",
                MessageType.WARNING,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(1)

    @staticmethod
    def export_config(config: Config, output_file: str | None = None) -> None:
        """Export configuration to a file or stdout.

        Args:
            config: Config instance
            output_file: Optional output file path. If None, write to stdout.
        """
        if not config.exists():
            message("No configuration file found. Nothing to export.", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        config_data = config.read()

        # Remove repo objects before exporting (they're not serializable)
        export_data = {"hierarchy": []}
        for entry in config_data["hierarchy"]:
            export_entry = {"name": entry["name"], "url": entry["url"], "repo_type": entry["repo_type"]}
            export_data["hierarchy"].append(export_entry)

        # Include mergers section if present
        if "mergers" in config_data:
            export_data["mergers"] = config_data["mergers"]

        if output_file:
            try:
                with open(output_file, "w") as f:
                    yaml.dump(export_data, f, default_flow_style=False, sort_keys=False)
                message(f"Configuration exported to {output_file}", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
            except Exception as e:
                message(f"Failed to export configuration: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
                sys.exit(1)
        else:
            # Write to stdout
            print(yaml.dump(export_data, default_flow_style=False, sort_keys=False))

    @staticmethod
    def import_config(config: Config, input_file: str) -> None:
        """Import configuration from a file.

        Args:
            config: Config instance
            input_file: Input file path to import from
        """
        try:
            with open(input_file) as f:
                imported_data = yaml.safe_load(f)
        except FileNotFoundError:
            message(f"File not found: {input_file}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)
        except yaml.YAMLError as e:
            message(f"Invalid YAML file: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)
        except Exception as e:
            message(f"Failed to read file: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        # Validate imported data
        if not isinstance(imported_data, dict) or "hierarchy" not in imported_data:
            message("Invalid configuration file: missing 'hierarchy' key", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        # Warn if overwriting existing config
        if config.exists():
            response = input(f"Configuration file already exists at {config.config_file}. Overwrite? (yes/no): ")
            if response.lower() not in ["yes", "y"]:
                message("Import cancelled.", MessageType.NORMAL, VerbosityLevel.ALWAYS)
                return

        # Write imported config
        try:
            config.write(imported_data)
            message(f"✓ Configuration imported from {input_file}", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
        except Exception as e:
            message(f"Failed to import configuration: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

    @staticmethod
    def show_location(config: Config) -> None:
        """Show the location of the configuration file and directories.

        Args:
            config: Config instance
        """
        message("\nConfiguration Locations:\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        message(f"  Config directory: {config.config_directory}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        message(f"  Config file:      {config.config_file}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        message(f"  Repos directory:  {config.repos_directory}", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Show status
        message("\nStatus:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        if config.config_file.exists():
            message("  ✓ Configuration file exists", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
        else:
            message("  ✗ Configuration file does not exist", MessageType.WARNING, VerbosityLevel.ALWAYS)

        if config.config_directory.exists():
            message("  ✓ Config directory exists", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
        else:
            message("  ✗ Config directory does not exist", MessageType.WARNING, VerbosityLevel.ALWAYS)

        if config.repos_directory.exists():
            message("  ✓ Repos directory exists", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
        else:
            message("  ✗ Repos directory does not exist", MessageType.WARNING, VerbosityLevel.ALWAYS)

        message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
