"""CLI commands for managing merger configurations."""

import argparse
import sys

from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.config import Config
from agent_manager.core import MergerRegistry
from agent_manager.utils import get_disabled_plugins, set_plugin_enabled


class MergerCommands:
    """Manager for merger-related CLI commands."""

    def __init__(self, merger_registry: MergerRegistry):
        """Initialize the merger commands handler.

        Args:
            merger_registry: The merger registry to manage
        """
        self.merger_registry = merger_registry

    @staticmethod
    def add_cli_arguments(subparsers) -> None:
        """Add merger-related CLI arguments.

        Args:
            subparsers: The argparse subparsers to add to
        """
        # Mergers command group
        mergers_parser = subparsers.add_parser("mergers", help="Manage content mergers")
        mergers_subparsers = mergers_parser.add_subparsers(dest="mergers_command", help="Merger commands")

        # mergers list
        mergers_subparsers.add_parser(
            "list",
            help="List available merger plugins",
            description="Show all registered mergers and their file extension mappings, the default fallback merger, and any available but unregistered merger plugins.",
        )

        # mergers show
        show_parser = mergers_subparsers.add_parser(
            "show",
            help="Show preferences for a specific merger",
            description="Display the configurable preferences for a specific merger, including their types, default values, and valid ranges or choices.",
        )
        show_parser.add_argument("name", help="Merger class name (e.g., JsonMerger)")

        # mergers configure
        configure_parser = mergers_subparsers.add_parser(
            "configure",
            help="Interactively configure merger preferences",
            description="Interactively prompt for preference values for each configurable merger (e.g., JSON indent level, YAML width) and save the results to the configuration file.",
        )
        configure_parser.add_argument("--merger", help="Configure only a specific merger (e.g., JsonMerger)")

        # mergers enable
        enable_parser = mergers_subparsers.add_parser(
            "enable",
            help="Enable a merger plugin",
            description="Re-enable a previously disabled merger plugin so it will be available for file merging.",
        )
        enable_parser.add_argument("name", help="Merger name (e.g., smart_markdown)")

        # mergers disable
        disable_parser = mergers_subparsers.add_parser(
            "disable",
            help="Disable a merger plugin",
            description="Disable a merger plugin. Disabled mergers will not be available for file merging; files that would use them will fall back to the default merger.",
        )
        disable_parser.add_argument("name", help="Merger name (e.g., smart_markdown)")

    def process_cli_command(self, args: argparse.Namespace, config: Config) -> None:
        """Process merger-related CLI commands.

        Args:
            args: Parsed command-line arguments
            config: Configuration manager instance
        """
        if not hasattr(args, "mergers_command") or args.mergers_command is None:
            message("Usage: agent-manager mergers <command>", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("Available commands:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  list        List available merger plugins", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  show        Show preferences for a specific merger", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message(
                "  configure   Interactively configure merger preferences", MessageType.NORMAL, VerbosityLevel.ALWAYS
            )
            message("  enable      Enable a merger plugin", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("  disable     Disable a merger plugin", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            return

        if args.mergers_command == "list":
            self.list_mergers()
        elif args.mergers_command == "show":
            self.show_merger(args.name)
        elif args.mergers_command == "configure":
            self.configure_mergers(config, args.merger)
        elif args.mergers_command == "enable":
            self.enable_merger(args.name)
        elif args.mergers_command == "disable":
            self.disable_merger(args.name)

    def list_mergers(self) -> None:
        """List all registered and available mergers."""
        from agent_manager.core.mergers import discover_merger_classes

        message("\n=== Registered Mergers ===\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Get disabled mergers
        disabled = get_disabled_plugins().get("mergers", [])

        registered = self.merger_registry.list_registered_mergers()

        # Show filename-specific mergers
        if registered["filenames"]:
            message("Filename-specific mergers:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            for filename in registered["filenames"]:
                merger = self.merger_registry.filename_mergers[filename]
                message(f"  {filename} → {merger.__name__}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Show extension-based mergers
        if registered["extensions"]:
            message("Extension-based mergers:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            for ext in sorted(registered["extensions"]):
                merger = self.merger_registry.extension_mergers[ext]
                message(f"  {ext} → {merger.__name__}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Show default merger
        message("Default fallback merger:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        message(f"  {registered['default']}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Show available but unregistered mergers
        all_discovered = discover_merger_classes()
        registered_classes = set(self.merger_registry.filename_mergers.values())
        registered_classes.update(self.merger_registry.extension_mergers.values())
        registered_classes.add(self.merger_registry.default_merger)

        unregistered = [m for m in all_discovered if m not in registered_classes]

        if unregistered:
            message("Available but not registered:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            for merger_class in sorted(unregistered, key=lambda c: c.__name__):
                extensions = getattr(merger_class, "FILE_EXTENSIONS", [])
                ext_str = f" (handles: {', '.join(extensions)})" if extensions else ""
                message(f"  {merger_class.__name__}{ext_str}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Show disabled plugins
        if disabled:
            message("Disabled mergers:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            for name in disabled:
                message(f"  {name} (disabled)", MessageType.WARNING, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("Use 'agent-manager mergers enable <name>' to re-enable", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

    def enable_merger(self, name: str) -> None:
        """Enable a merger plugin.

        Args:
            name: Name of the merger to enable
        """
        if not set_plugin_enabled("mergers", name, enabled=True):
            sys.exit(1)

    def disable_merger(self, name: str) -> None:
        """Disable a merger plugin.

        Args:
            name: Name of the merger to disable
        """
        if not set_plugin_enabled("mergers", name, enabled=False):
            sys.exit(1)

    def show_merger(self, merger_name: str) -> None:
        """Show preferences for a specific merger.

        Args:
            merger_name: Name of the merger class
        """
        # Find the merger class
        merger_class = self._find_merger_class(merger_name)
        if not merger_class:
            message(f"Merger '{merger_name}' not found", MessageType.ERROR, VerbosityLevel.ALWAYS)
            message(
                "Use 'agent-manager mergers list' to see available mergers", MessageType.NORMAL, VerbosityLevel.ALWAYS
            )
            sys.exit(1)

        # Get preferences
        prefs = merger_class.merge_preferences()

        if not prefs:
            message(f"\n{merger_name} has no configurable preferences.\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            return

        message(f"\n=== {merger_name} Preferences ===\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        for pref_name, pref_schema in prefs.items():
            pref_type = pref_schema.get("type", "unknown")
            default = pref_schema.get("default")
            description = pref_schema.get("description", "No description")

            message(f"{pref_name}:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message(f"  Type: {pref_type}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message(f"  Default: {default}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message(f"  Description: {description}", MessageType.NORMAL, VerbosityLevel.ALWAYS)

            # Show additional constraints
            if "min" in pref_schema:
                message(f"  Min: {pref_schema['min']}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            if "max" in pref_schema:
                message(f"  Max: {pref_schema['max']}", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            if "choices" in pref_schema:
                message(f"  Choices: {', '.join(pref_schema['choices'])}", MessageType.NORMAL, VerbosityLevel.ALWAYS)

            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

    def configure_mergers(self, config: Config, specific_merger: str | None = None) -> None:
        """Interactively configure merger preferences.

        Args:
            config: Configuration manager instance
            specific_merger: Optional specific merger to configure
        """
        message("\n=== Configure Merger Preferences ===\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Get all merger classes
        merger_classes = self._get_all_merger_classes()

        # Filter to specific merger if requested
        if specific_merger:
            merger_class = self._find_merger_class(specific_merger)
            if not merger_class:
                message(f"Merger '{specific_merger}' not found", MessageType.ERROR, VerbosityLevel.ALWAYS)
                sys.exit(1)
            merger_classes = [merger_class]

        # Load existing config
        try:
            config_data = config.read()
        except SystemExit:
            # Config doesn't exist yet, create empty structure
            config_data = {"hierarchy": [], "mergers": {}}

        # Ensure mergers section exists
        if "mergers" not in config_data:
            config_data["mergers"] = {}

        # Configure each merger
        for merger_class in merger_classes:
            prefs = merger_class.merge_preferences()
            if not prefs:
                continue  # Skip mergers with no preferences

            message(f"\n{merger_class.__name__}:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("=" * (len(merger_class.__name__) + 1), MessageType.NORMAL, VerbosityLevel.ALWAYS)

            # Get existing settings or create empty dict
            merger_name = merger_class.__name__
            if merger_name not in config_data["mergers"]:
                config_data["mergers"][merger_name] = {}

            current_settings = config_data["mergers"][merger_name]

            # Prompt for each preference
            for pref_name, pref_schema in prefs.items():
                pref_type = pref_schema.get("type")
                default = pref_schema.get("default")
                description = pref_schema.get("description", "")
                current_value = current_settings.get(pref_name, default)

                # Build prompt
                prompt = f"\n  {pref_name}"
                if description:
                    prompt += f" ({description})"

                # Add type-specific info
                if pref_type == "int":
                    min_val = pref_schema.get("min")
                    max_val = pref_schema.get("max")
                    if min_val is not None and max_val is not None:
                        prompt += f" [{min_val}-{max_val}]"
                elif pref_type == "str" and "choices" in pref_schema:
                    choices = pref_schema["choices"]
                    prompt += f" (choices: {', '.join(choices)})"
                elif pref_type == "bool":
                    prompt += " (y/n)"

                prompt += f" [current: {current_value}]: "

                # Get user input
                user_input = input(prompt).strip()

                # Use current value if empty
                if not user_input:
                    continue

                # Parse and validate input
                try:
                    if pref_type == "int":
                        value = int(user_input)
                        min_val = pref_schema.get("min")
                        max_val = pref_schema.get("max")
                        if min_val is not None and value < min_val:
                            message(
                                f"Value too small, using minimum: {min_val}", MessageType.WARNING, VerbosityLevel.ALWAYS
                            )
                            value = min_val
                        if max_val is not None and value > max_val:
                            message(
                                f"Value too large, using maximum: {max_val}", MessageType.WARNING, VerbosityLevel.ALWAYS
                            )
                            value = max_val
                        current_settings[pref_name] = value
                    elif pref_type == "bool":
                        value = user_input.lower() in ["y", "yes", "true", "1"]
                        current_settings[pref_name] = value
                    elif pref_type == "str":
                        if "choices" in pref_schema:
                            if user_input in pref_schema["choices"]:
                                current_settings[pref_name] = user_input
                            else:
                                message(
                                    f"Invalid choice. Valid options: {', '.join(pref_schema['choices'])}",
                                    MessageType.WARNING,
                                    VerbosityLevel.ALWAYS,
                                )
                        else:
                            current_settings[pref_name] = user_input
                    else:
                        current_settings[pref_name] = user_input
                except ValueError:
                    message(f"Invalid {pref_type} value, skipping", MessageType.ERROR, VerbosityLevel.ALWAYS)

            config_data["mergers"][merger_name] = current_settings

        # Save configuration
        message("\nSaving configuration...", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        config.write(config_data)
        message(f"✓ Merger preferences saved to {config.config_file}\n", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

    def _get_all_merger_classes(self) -> list[type]:
        """Get all unique merger classes (registered and discovered).

        Returns:
            List of merger classes
        """
        from agent_manager.core.mergers import discover_merger_classes

        merger_classes = set()

        # Add filename mergers
        for merger_class in self.merger_registry.filename_mergers.values():
            merger_classes.add(merger_class)

        # Add extension mergers
        for merger_class in self.merger_registry.extension_mergers.values():
            merger_classes.add(merger_class)

        # Add default merger
        merger_classes.add(self.merger_registry.default_merger)

        # Add all discovered mergers (including unregistered ones)
        for merger_class in discover_merger_classes():
            merger_classes.add(merger_class)

        return sorted(merger_classes, key=lambda c: c.__name__)

    def _find_merger_class(self, merger_name: str) -> type | None:
        """Find a merger class by name.

        Searches both registered and discovered mergers.

        Args:
            merger_name: Name of the merger class

        Returns:
            Merger class or None if not found
        """
        all_mergers = self._get_all_merger_classes()
        for merger_class in all_mergers:
            if merger_class.__name__ == merger_name:
                return merger_class
        return None
