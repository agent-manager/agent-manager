"""CLI commands for managing configuration (V2 schema)."""

import argparse
import sys

from agent_manager.config import Config
from agent_manager.output import MessageType, VerbosityLevel, message


class ConfigCommands:
    """Manages configuration-related CLI commands."""

    @staticmethod
    def add_cli_arguments(subparsers) -> None:
        """Add config subcommands to the argument parser.

        Args:
            subparsers: The subparsers object to add commands to
        """
        config_parser = subparsers.add_parser("config", help="Manage configuration")
        config_subparsers = config_parser.add_subparsers(dest="config_command", help="Configuration commands")

        # config show
        config_subparsers.add_parser(
            "show",
            help="Display current configuration",
            description="Display the current configuration including repos, defaults, and directories.",
        )

        # config validate
        config_subparsers.add_parser(
            "validate",
            help="Validate configuration",
            description="Validate the configuration file structure and check that all repository URLs are accessible.",
        )

        # config template
        config_subparsers.add_parser(
            "template",
            help="Dump a starter configuration template to stdout",
            description="Print a commented YAML template to stdout that can be redirected to a config file.",
        )

        # config defaults
        defaults_parser = config_subparsers.add_parser(
            "defaults",
            help="Show or set default hierarchy and agents",
            description="Show or set the default_hierarchy and default_agents. "
            "When called with flags, the lists are replaced entirely (declarative).",
        )
        defaults_parser.add_argument(
            "--repos", nargs="+", metavar="NAME",
            help="Set default_hierarchy (declarative, full replace)",
        )
        defaults_parser.add_argument(
            "--agents", nargs="+", metavar="NAME",
            help="Set default_agents (declarative, full replace)",
        )

        # config where
        config_subparsers.add_parser(
            "where",
            help="Show configuration file location",
            description="Show the file paths for the configuration file, config directory, and repos directory.",
        )

        # config init (placeholder for future wizard, currently creates from template)
        config_subparsers.add_parser(
            "init",
            help="Initialize configuration (interactive wizard)",
            description="Create a new configuration file through an interactive setup wizard.",
        )

        # config edit (placeholder for future editor integration)
        config_subparsers.add_parser(
            "edit",
            help="Edit configuration in $EDITOR",
            description="Open the configuration file in your default editor, validate on save.",
        )

    @staticmethod
    def process_cli_command(args: argparse.Namespace, config: Config) -> None:
        """Process config CLI commands.

        Args:
            args: Parsed command-line arguments
            config: Config instance to operate on
        """
        if args.config_command is None:
            message("Usage: agent-manager config <command>", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("Available commands:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  show       Display current configuration", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  validate   Validate configuration", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  template   Dump starter template to stdout", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  defaults   Show or set default hierarchy/agents", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  where      Show configuration file location", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  init       Initialize configuration (wizard)", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  edit       Edit configuration in $EDITOR", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            return
        elif args.config_command == "show":
            ConfigCommands.display(config)
        elif args.config_command == "validate":
            ConfigCommands.validate_all(config)
        elif args.config_command == "template":
            ConfigCommands.template()
        elif args.config_command == "defaults":
            repos = getattr(args, "repos", None)
            agents = getattr(args, "agents", None)
            ConfigCommands.defaults(config, repos, agents)
        elif args.config_command == "where":
            ConfigCommands.show_location(config)
        elif args.config_command == "init":
            message("Interactive wizard not yet implemented. Use 'config template' to generate a starter config.",
                    MessageType.WARNING, VerbosityLevel.ALWAYS)
        elif args.config_command == "edit":
            message("Editor integration not yet implemented. Use 'config where' to find the file path.",
                    MessageType.WARNING, VerbosityLevel.ALWAYS)
        else:
            message("Unknown config command", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

    @staticmethod
    def display(config: Config) -> None:
        """Display the current configuration.

        Args:
            config: Config instance
        """
        if not config.exists():
            message("No configuration file found. Run 'agent-manager config init' to create one.",
                    MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        config_data = config.read()

        # Repos
        repos = config_data.get("repos", [])
        message("\n=== Repos ===\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        if repos:
            for entry in repos:
                message(f"  {entry['name']} ({entry.get('repo_type', 'unknown')})",
                        MessageType.NORMAL, VerbosityLevel.ALWAYS)
                message(f"    URL: {entry['url']}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        else:
            message("  (none)", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Default hierarchy
        default_hierarchy = config_data.get("default_hierarchy", [])
        message("\n=== Default Hierarchy ===\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        if default_hierarchy:
            for idx, name in enumerate(default_hierarchy, 1):
                message(f"  {idx}. {name}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        else:
            message("  (not set)", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Default agents
        default_agents = config_data.get("default_agents", [])
        message("\n=== Default Agents ===\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        if default_agents:
            for name in default_agents:
                message(f"  - {name}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        else:
            message("  (not set -- falls back to all enabled agents)", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Directories
        directories = config_data.get("directories", {})
        message("\n=== Directories ===\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        if directories:
            for dir_path, dir_config in directories.items():
                if dir_config is None:
                    dir_config = {}
                dir_type = dir_config.get("type", "unset")
                agents = dir_config.get("agents")
                hierarchy = dir_config.get("hierarchy")

                message(f"  {dir_path}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
                message(f"    type: {dir_type}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
                if agents:
                    message(f"    agents: {', '.join(agents)}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
                else:
                    message("    agents: (inherits default)", MessageType.NORMAL, VerbosityLevel.ALWAYS)
                if hierarchy:
                    message(f"    hierarchy: {' -> '.join(hierarchy)}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
                else:
                    message("    hierarchy: (inherits default)", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        else:
            message("  (none)", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

    @staticmethod
    def validate_all(config: Config) -> None:
        """Validate configuration structure and repository URLs.

        Args:
            config: Config instance
        """
        if not config.exists():
            message("No configuration file found. Run 'agent-manager config init' to create one.",
                    MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        # First validate structure (read does this)
        config_data = config.read()

        repos = config_data.get("repos", [])
        message("\nValidating repository URLs...\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        all_valid = True
        for idx, entry in enumerate(repos):
            name = entry["name"]
            url = entry["url"]
            total = len(repos)

            message(f"[{idx + 1}/{total}] {name}: {url}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            if config.validate_repo_url(url):
                message("  Valid", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
            else:
                message("  Invalid or inaccessible", MessageType.ERROR, VerbosityLevel.ALWAYS)
                all_valid = False

        message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        if all_valid:
            message("All repositories are valid and accessible!", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
        else:
            message("Some repositories failed validation.", MessageType.WARNING, VerbosityLevel.ALWAYS)
            sys.exit(1)

    @staticmethod
    def template() -> None:
        """Dump a starter configuration template to stdout."""
        print(Config.generate_template())

    @staticmethod
    def defaults(config: Config, repos: list[str] | None = None, agents: list[str] | None = None) -> None:
        """Show or set default_hierarchy and default_agents.

        Args:
            config: Config instance
            repos: If provided, set default_hierarchy (full replace)
            agents: If provided, set default_agents (full replace)
        """
        if repos is None and agents is None:
            # Show current defaults
            defaults = config.get_defaults()
            message("\nDefault hierarchy:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            if defaults["default_hierarchy"]:
                for idx, name in enumerate(defaults["default_hierarchy"], 1):
                    message(f"  {idx}. {name}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            else:
                message("  (not set)", MessageType.NORMAL, VerbosityLevel.ALWAYS)

            message("\nDefault agents:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            if defaults["default_agents"]:
                for name in defaults["default_agents"]:
                    message(f"  - {name}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            else:
                message("  (not set -- falls back to all enabled agents)", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        else:
            config.set_defaults(repos=repos, agents=agents)

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

        message("\nStatus:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        if config.config_file.exists():
            message("  Config file exists", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
        else:
            message("  Config file does not exist", MessageType.WARNING, VerbosityLevel.ALWAYS)

        if config.config_directory.exists():
            message("  Config directory exists", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
        else:
            message("  Config directory does not exist", MessageType.WARNING, VerbosityLevel.ALWAYS)

        if config.repos_directory.exists():
            message("  Repos directory exists", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
        else:
            message("  Repos directory does not exist", MessageType.WARNING, VerbosityLevel.ALWAYS)

        message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
