"""Consolidated CLI commands for plugin management.

Groups all plugin enable/disable/list/show/configure commands under
``agent-manager plugins [agents|repos|mergers] <action>``.
"""

import argparse
import sys

from agent_manager.config import Config
from agent_manager.core import (
    MergerRegistry,
    discover_agent_plugins,
    discover_repo_types,
)
from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.utils import get_disabled_plugins, set_plugin_enabled


class PluginCommands:
    """Manages all plugin-related CLI commands."""

    def __init__(self, merger_registry: MergerRegistry | None = None):
        self.merger_registry = merger_registry

    @staticmethod
    def add_cli_arguments(subparsers) -> None:
        """Register the ``plugins`` command group."""
        plugins_parser = subparsers.add_parser(
            "plugins",
            help="Manage agent, repo, and merger plugins",
        )
        plugins_sub = plugins_parser.add_subparsers(
            dest="plugins_category",
            help="Plugin category",
        )

        # --- plugins agents ---
        agents_parser = plugins_sub.add_parser(
            "agents", help="Manage agent plugins",
        )
        agents_sub = agents_parser.add_subparsers(
            dest="plugins_action", help="Agent plugin actions",
        )
        agents_sub.add_parser("list", help="List agent plugins")
        p = agents_sub.add_parser("enable", help="Enable an agent plugin")
        p.add_argument("name", help="Agent name")
        p = agents_sub.add_parser("disable", help="Disable an agent plugin")
        p.add_argument("name", help="Agent name")

        # --- plugins repos ---
        repos_parser = plugins_sub.add_parser(
            "repos", help="Manage repo type plugins",
        )
        repos_sub = repos_parser.add_subparsers(
            dest="plugins_action", help="Repo plugin actions",
        )
        repos_sub.add_parser("list", help="List repo type plugins")
        p = repos_sub.add_parser("enable", help="Enable a repo plugin")
        p.add_argument("name", help="Repo type name")
        p = repos_sub.add_parser("disable", help="Disable a repo plugin")
        p.add_argument("name", help="Repo type name")

        # --- plugins mergers ---
        mergers_parser = plugins_sub.add_parser(
            "mergers", help="Manage merger plugins",
        )
        mergers_sub = mergers_parser.add_subparsers(
            dest="plugins_action", help="Merger plugin actions",
        )
        mergers_sub.add_parser("list", help="List merger plugins")
        p = mergers_sub.add_parser("show", help="Show merger preferences")
        p.add_argument("name", help="Merger class name")
        p = mergers_sub.add_parser(
            "configure", help="Configure merger preferences",
        )
        p.add_argument(
            "--merger", help="Configure a specific merger only",
        )
        p = mergers_sub.add_parser("enable", help="Enable a merger plugin")
        p.add_argument("name", help="Merger name")
        p = mergers_sub.add_parser("disable", help="Disable a merger plugin")
        p.add_argument("name", help="Merger name")

    def process_cli_command(
        self,
        args: argparse.Namespace,
        config: Config | None = None,
    ) -> None:
        """Dispatch to the correct plugin category handler."""
        category = getattr(args, "plugins_category", None)
        if category is None:
            self._show_usage()
            return

        action = getattr(args, "plugins_action", None)

        if category == "agents":
            self._handle_agents(action, args)
        elif category == "repos":
            self._handle_repos(action, args)
        elif category == "mergers":
            self._handle_mergers(action, args, config)

    @staticmethod
    def _show_usage() -> None:
        message(
            "Usage: agent-manager plugins <category> <action>",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        message(
            "Categories:",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        message(
            "  agents    Manage agent plugins",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        message(
            "  repos     Manage repo type plugins",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        message(
            "  mergers   Manage merger plugins",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------
    @staticmethod
    def _handle_agents(action: str | None, args: argparse.Namespace) -> None:
        if action is None:
            message(
                "Usage: agent-manager plugins agents "
                "[list|enable|disable]",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            return

        if action == "list":
            PluginCommands._list_agents()
        elif action in ("enable", "disable"):
            enabled = action == "enable"
            if not set_plugin_enabled("agents", args.name, enabled=enabled):
                sys.exit(1)

    @staticmethod
    def _list_agents() -> None:
        disabled = get_disabled_plugins().get("agents", [])
        plugins = discover_agent_plugins()

        message(
            "\n=== Agent Plugins ===\n",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )

        if not plugins and not disabled:
            message(
                "No agent plugins found.",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            return

        if plugins:
            message(
                "Installed:", MessageType.NORMAL, VerbosityLevel.ALWAYS,
            )
            for name in sorted(plugins.keys()):
                pkg = plugins[name]["package_name"]
                message(
                    f"  {name} ({pkg})",
                    MessageType.NORMAL,
                    VerbosityLevel.ALWAYS,
                )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        if disabled:
            message(
                "Disabled:", MessageType.NORMAL, VerbosityLevel.ALWAYS,
            )
            for name in disabled:
                message(
                    f"  {name}",
                    MessageType.WARNING,
                    VerbosityLevel.ALWAYS,
                )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        message(
            f"Total: {len(plugins)} enabled, {len(disabled)} disabled",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )

    # ------------------------------------------------------------------
    # Repos
    # ------------------------------------------------------------------
    @staticmethod
    def _handle_repos(action: str | None, args: argparse.Namespace) -> None:
        if action is None:
            message(
                "Usage: agent-manager plugins repos "
                "[list|enable|disable]",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            return

        if action == "list":
            PluginCommands._list_repos()
        elif action in ("enable", "disable"):
            enabled = action == "enable"
            if not set_plugin_enabled("repos", args.name, enabled=enabled):
                sys.exit(1)

    @staticmethod
    def _list_repos() -> None:
        disabled = get_disabled_plugins().get("repos", [])
        repo_types = discover_repo_types()

        message(
            "\n=== Repo Type Plugins ===\n",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )

        if not repo_types and not disabled:
            message(
                "No repo type plugins found.",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            return

        if repo_types:
            message(
                "Installed:", MessageType.NORMAL, VerbosityLevel.ALWAYS,
            )
            for repo_class in repo_types:
                message(
                    f"  {repo_class.REPO_TYPE} ({repo_class.__module__})",
                    MessageType.NORMAL,
                    VerbosityLevel.ALWAYS,
                )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        if disabled:
            message(
                "Disabled:", MessageType.NORMAL, VerbosityLevel.ALWAYS,
            )
            for name in disabled:
                message(
                    f"  {name}",
                    MessageType.WARNING,
                    VerbosityLevel.ALWAYS,
                )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        message(
            f"Total: {len(repo_types)} enabled, {len(disabled)} disabled",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )

    # ------------------------------------------------------------------
    # Mergers
    # ------------------------------------------------------------------
    def _handle_mergers(
        self,
        action: str | None,
        args: argparse.Namespace,
        config: Config | None = None,
    ) -> None:
        if action is None:
            message(
                "Usage: agent-manager plugins mergers "
                "[list|show|configure|enable|disable]",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            return

        if action == "list":
            self._list_mergers()
        elif action == "show":
            self._show_merger(args.name)
        elif action == "configure":
            merger_name = getattr(args, "merger", None)
            self._configure_mergers(config, merger_name)
        elif action in ("enable", "disable"):
            enabled = action == "enable"
            if not set_plugin_enabled("mergers", args.name, enabled=enabled):
                sys.exit(1)

    def _list_mergers(self) -> None:
        from agent_manager.core.mergers import discover_merger_classes

        if self.merger_registry is None:
            message(
                "Merger registry not available.",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            return

        disabled = get_disabled_plugins().get("mergers", [])
        registered = self.merger_registry.list_registered_mergers()

        message(
            "\n=== Merger Plugins ===\n",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )

        if registered["extensions"]:
            message(
                "Extension-based:",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            for ext in sorted(registered["extensions"]):
                merger = self.merger_registry.extension_mergers[ext]
                message(
                    f"  {ext} -> {merger.__name__}",
                    MessageType.NORMAL,
                    VerbosityLevel.ALWAYS,
                )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        message(
            f"Default: {registered['default']}",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Unregistered
        all_discovered = discover_merger_classes()
        registered_classes = set(
            self.merger_registry.extension_mergers.values()
        )
        registered_classes.update(
            self.merger_registry.filename_mergers.values()
        )
        registered_classes.add(self.merger_registry.default_merger)
        unregistered = [m for m in all_discovered if m not in registered_classes]

        if unregistered:
            message(
                "Available but unregistered:",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            for cls in sorted(unregistered, key=lambda c: c.__name__):
                exts = getattr(cls, "FILE_EXTENSIONS", [])
                ext_str = f" ({', '.join(exts)})" if exts else ""
                message(
                    f"  {cls.__name__}{ext_str}",
                    MessageType.NORMAL,
                    VerbosityLevel.ALWAYS,
                )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        if disabled:
            message(
                "Disabled:", MessageType.NORMAL, VerbosityLevel.ALWAYS,
            )
            for name in disabled:
                message(
                    f"  {name}",
                    MessageType.WARNING,
                    VerbosityLevel.ALWAYS,
                )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

    def _show_merger(self, merger_name: str) -> None:
        merger_class = self._find_merger_class(merger_name)
        if not merger_class:
            message(
                f"Merger '{merger_name}' not found",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(1)

        prefs = merger_class.merge_preferences()
        if not prefs:
            message(
                f"\n{merger_name} has no configurable preferences.\n",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            return

        message(
            f"\n=== {merger_name} Preferences ===\n",
            MessageType.NORMAL,
            VerbosityLevel.ALWAYS,
        )
        for pref_name, schema in prefs.items():
            message(
                f"{pref_name}:",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                f"  Type: {schema.get('type', 'unknown')}",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message(
                f"  Default: {schema.get('default')}",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            desc = schema.get("description", "")
            if desc:
                message(
                    f"  Description: {desc}",
                    MessageType.NORMAL,
                    VerbosityLevel.ALWAYS,
                )
            message("", MessageType.NORMAL, VerbosityLevel.ALWAYS)

    def _configure_mergers(
        self,
        config: Config | None,
        specific_merger: str | None = None,
    ) -> None:
        if config is None:
            message(
                "Config required for merger configuration.",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(1)

        # Delegate to the existing MergerCommands logic
        from agent_manager.cli_extensions.merger_commands import (
            MergerCommands,
        )

        if self.merger_registry is None:
            message(
                "Merger registry not available.",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(1)

        mc = MergerCommands(self.merger_registry)
        mc.configure_mergers(config, specific_merger)

    def _find_merger_class(self, merger_name: str) -> type | None:
        from agent_manager.core.mergers import discover_merger_classes

        if self.merger_registry is None:
            return None

        all_classes: set[type] = set()
        all_classes.update(self.merger_registry.extension_mergers.values())
        all_classes.update(self.merger_registry.filename_mergers.values())
        all_classes.add(self.merger_registry.default_merger)
        for cls in discover_merger_classes():
            all_classes.add(cls)

        for cls in all_classes:
            if cls.__name__ == merger_name:
                return cls
        return None
