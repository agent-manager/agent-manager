"""Configuration management class for agent-manager.

V2 schema: repos + default_hierarchy + default_agents + directories
"""

import sys
from pathlib import Path
from typing import Any, TypedDict

import yaml

from agent_manager.core import create_repo, discover_repo_types
from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.utils import is_file_url, resolve_file_path


class RepoEntry(TypedDict):
    """Type definition for a repo entry."""

    name: str
    url: str
    repo_type: str


class DirectoryEntry(TypedDict, total=False):
    """Type definition for a directory entry."""

    type: str
    agents: list[str]
    hierarchy: list[str]


class ConfigData(TypedDict, total=False):
    """Type definition for the V2 configuration structure."""

    repos: list[RepoEntry]
    default_hierarchy: list[str]
    default_agents: list[str]
    directories: dict[str, DirectoryEntry]
    mergers: dict[str, Any]


class ConfigError(Exception):
    """Exception raised for configuration validation errors.

    Can contain multiple error messages.
    """

    def __init__(self, errors: str | list[str]):
        """Initialize ConfigError.

        Args:
            errors: Single error message or list of error messages
        """
        if isinstance(errors, str):
            self.errors = [errors]
        else:
            self.errors = errors
        super().__init__(self._format_errors())

    def _format_errors(self) -> str:
        """Format errors for display."""
        if len(self.errors) == 1:
            return self.errors[0]
        else:
            error_list = "\n".join(f"  - {err}" for err in self.errors)
            return f"Configuration has {len(self.errors)} errors:\n{error_list}"


class Config:
    """Manages configuration for agent-manager."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize the Config manager.

        Args:
            config_dir: Optional custom config directory.
                       Defaults to ~/.agent-manager
        """
        if config_dir is None:
            config_dir = Path.home() / ".agent-manager"

        self.config_directory = config_dir
        self.config_file = self.config_directory / "config.yaml"
        self.repos_directory = self.config_directory / "repos"

    def ensure_directories(self) -> None:
        """Create config directories if they don't exist.

        Raises:
            SystemExit: If directories cannot be created
        """
        directories = {
            "config": self.config_directory,
            "repos": self.repos_directory,
        }

        for dir_name, dir_path in directories.items():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                message(f"Ensured {dir_name} directory exists: {dir_path}", MessageType.DEBUG, VerbosityLevel.DEBUG)
            except PermissionError:
                message(
                    f"Permission denied creating {dir_name} directory: {dir_path}",
                    MessageType.ERROR,
                    VerbosityLevel.ALWAYS,
                )
                sys.exit(1)
            except OSError as e:
                message(f"Failed to create {dir_name} directory: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
                sys.exit(1)
            except Exception as e:
                message(
                    f"Unexpected error creating {dir_name} directory: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS
                )
                sys.exit(1)

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize a URL by resolving file:// URLs to absolute paths.

        Args:
            url: The URL to normalize

        Returns:
            Normalized URL with absolute paths for file:// URLs
        """
        if is_file_url(url):
            resolved_path = resolve_file_path(url)
            return f"file://{resolved_path}"
        return url

    @staticmethod
    def validate_repo_url(url: str) -> bool:
        """Validate a repository URL using the pluggable repo system.

        Args:
            url: The URL to validate

        Returns:
            True if the URL is valid and accessible, False otherwise
        """
        matching_type_names = Config.detect_repo_types(url)

        if len(matching_type_names) == 0:
            message(f"No repository type can handle URL: {url}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            return False

        for repo_class in discover_repo_types():
            if matching_type_names[0] == repo_class.REPO_TYPE:
                return repo_class.validate_url(url)

        message("Internal error: Could not find repo class", MessageType.ERROR, VerbosityLevel.ALWAYS)
        return False

    @staticmethod
    def detect_repo_types(url: str) -> list[str]:
        """Detect which repository types can handle the given URL.

        Args:
            url: The URL to check

        Returns:
            List of repo type names that can handle this URL
        """
        matching_types = []
        for repo_class in discover_repo_types():
            if repo_class.can_handle_url(url):
                matching_types.append(repo_class.REPO_TYPE)
        return matching_types

    @staticmethod
    def prompt_for_repo_type(url: str, available_types: list[str]) -> str:
        """Prompt the user to select a repository type when multiple match.

        Args:
            url: The URL being configured
            available_types: List of repo types that can handle this URL

        Returns:
            The selected repo type
        """
        message(f"\nMultiple repository types can handle this URL: {url}", MessageType.WARNING, VerbosityLevel.ALWAYS)
        message("Available types:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        for idx, repo_type in enumerate(available_types, 1):
            message(f"  {idx}. {repo_type}", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        while True:
            choice = input(f"\nSelect type (1-{len(available_types)}): ").strip()
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(available_types):
                    selected_type = available_types[choice_idx]
                    message(f"Selected: {selected_type}", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
                    return selected_type
                else:
                    message("Invalid selection. Please try again.", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            except ValueError:
                message("Please enter a number.", MessageType.NORMAL, VerbosityLevel.ALWAYS)

    @staticmethod
    def validate(config: dict[str, Any]) -> list[str]:
        """Validate the V2 configuration structure.

        Collects all validation errors before raising an exception.

        Args:
            config: The configuration dictionary to validate

        Returns:
            List of warnings (non-fatal issues)

        Raises:
            ConfigError: If the configuration is invalid, with all errors
        """
        errors: list[str] = []
        warnings: list[str] = []

        # --- repos ---
        if "repos" not in config:
            errors.append("Configuration must contain 'repos' key")
        elif not isinstance(config["repos"], list):
            errors.append("'repos' must be a list")
        else:
            repo_names: set[str] = set()
            for idx, entry in enumerate(config["repos"]):
                if not isinstance(entry, dict):
                    errors.append(f"Repo entry {idx} must be a dictionary")
                    continue

                required_keys = ["name", "url", "repo_type"]
                missing_keys = [key for key in required_keys if key not in entry]
                if missing_keys:
                    errors.append(f"Repo entry {idx} is missing required keys: {', '.join(missing_keys)}")

                if "name" in entry:
                    if not isinstance(entry["name"], str):
                        errors.append(
                            f"Repo entry {idx} 'name' must be a string, got {type(entry['name']).__name__}"
                        )
                    elif not entry["name"]:
                        errors.append(f"Repo entry {idx} 'name' cannot be empty")
                    elif entry["name"] in repo_names:
                        errors.append(f"Repo entry {idx} has duplicate name '{entry['name']}'")
                    else:
                        repo_names.add(entry["name"])

                if "url" in entry:
                    if not isinstance(entry["url"], str):
                        errors.append(
                            f"Repo entry {idx} 'url' must be a string, got {type(entry['url']).__name__}"
                        )
                    elif not entry["url"]:
                        errors.append(f"Repo entry {idx} 'url' cannot be empty")

                if "repo_type" in entry:
                    if not isinstance(entry["repo_type"], str):
                        errors.append(
                            f"Repo entry {idx} 'repo_type' must be a string, "
                            f"got {type(entry['repo_type']).__name__}"
                        )
                    elif not entry["repo_type"]:
                        errors.append(f"Repo entry {idx} 'repo_type' cannot be empty")

            # --- default_hierarchy ---
            if "default_hierarchy" in config:
                if not isinstance(config["default_hierarchy"], list):
                    errors.append("'default_hierarchy' must be a list")
                else:
                    for idx, name in enumerate(config["default_hierarchy"]):
                        if not isinstance(name, str):
                            errors.append(f"default_hierarchy entry {idx} must be a string")
                        elif name not in repo_names:
                            errors.append(
                                f"default_hierarchy entry '{name}' does not match any repo name"
                            )

            # --- default_agents ---
            if "default_agents" in config:
                if not isinstance(config["default_agents"], list):
                    errors.append("'default_agents' must be a list")
                else:
                    for idx, name in enumerate(config["default_agents"]):
                        if not isinstance(name, str):
                            errors.append(f"default_agents entry {idx} must be a string")
                        elif not name:
                            errors.append(f"default_agents entry {idx} cannot be empty")

            # --- directories ---
            if "directories" in config:
                if not isinstance(config["directories"], dict):
                    errors.append("'directories' must be a dictionary")
                else:
                    has_default_hierarchy = (
                        "default_hierarchy" in config
                        and isinstance(config.get("default_hierarchy"), list)
                        and len(config.get("default_hierarchy", [])) > 0
                    )

                    for dir_path, dir_config in config["directories"].items():
                        if not isinstance(dir_path, str):
                            errors.append(f"Directory key must be a string, got {type(dir_path).__name__}")
                            continue

                        if dir_config is None:
                            dir_config = {}

                        if not isinstance(dir_config, dict):
                            errors.append(f"Directory '{dir_path}' config must be a dictionary")
                            continue

                        # Validate type
                        if "type" in dir_config:
                            if not isinstance(dir_config["type"], str):
                                errors.append(
                                    f"Directory '{dir_path}' 'type' must be a string"
                                )
                            elif not dir_config["type"]:
                                errors.append(f"Directory '{dir_path}' 'type' cannot be empty")

                        # Validate agents list
                        if "agents" in dir_config:
                            if not isinstance(dir_config["agents"], list):
                                errors.append(f"Directory '{dir_path}' 'agents' must be a list")
                            else:
                                for idx, agent in enumerate(dir_config["agents"]):
                                    if not isinstance(agent, str):
                                        errors.append(
                                            f"Directory '{dir_path}' agents entry {idx} must be a string"
                                        )

                        # Validate hierarchy list
                        if "hierarchy" in dir_config:
                            if not isinstance(dir_config["hierarchy"], list):
                                errors.append(f"Directory '{dir_path}' 'hierarchy' must be a list")
                            else:
                                for idx, name in enumerate(dir_config["hierarchy"]):
                                    if not isinstance(name, str):
                                        errors.append(
                                            f"Directory '{dir_path}' hierarchy entry {idx} must be a string"
                                        )
                                    elif name not in repo_names:
                                        errors.append(
                                            f"Directory '{dir_path}' hierarchy entry '{name}' "
                                            f"does not match any repo name"
                                        )

                        # Warn if directory omits hierarchy and no default_hierarchy
                        if "hierarchy" not in dir_config and not has_default_hierarchy:
                            warnings.append(
                                f"Directory '{dir_path}' has no 'hierarchy' and no "
                                f"'default_hierarchy' is defined; no repos will be merged"
                            )

        if errors:
            raise ConfigError(errors)

        return warnings

    def write(self, config: ConfigData) -> None:
        """Write the configuration to the config file with validation.

        Args:
            config: The configuration dictionary to write

        Raises:
            SystemExit: If validation fails or file cannot be written
        """
        try:
            self.validate(config)

            clean_config: dict[str, Any] = {}

            # repos
            clean_config["repos"] = []
            for entry in config.get("repos", []):
                clean_config["repos"].append({
                    "name": entry["name"],
                    "url": entry["url"],
                    "repo_type": entry["repo_type"],
                })

            # default_hierarchy
            if "default_hierarchy" in config:
                clean_config["default_hierarchy"] = list(config["default_hierarchy"])

            # default_agents
            if "default_agents" in config:
                clean_config["default_agents"] = list(config["default_agents"])

            # directories
            if "directories" in config:
                clean_config["directories"] = {}
                for dir_path, dir_config in config["directories"].items():
                    if dir_config is None:
                        clean_config["directories"][dir_path] = None
                    else:
                        clean_entry: dict[str, Any] = {}
                        if "type" in dir_config:
                            clean_entry["type"] = dir_config["type"]
                        if "agents" in dir_config:
                            clean_entry["agents"] = list(dir_config["agents"])
                        if "hierarchy" in dir_config:
                            clean_entry["hierarchy"] = list(dir_config["hierarchy"])
                        clean_config["directories"][dir_path] = clean_entry if clean_entry else None

            # Copy additional top-level keys (like mergers)
            for key, value in config.items():
                if key not in ("repos", "default_hierarchy", "default_agents", "directories"):
                    clean_config[key] = value

            with open(self.config_file, "w") as f:
                yaml.dump(clean_config, f, default_flow_style=False, sort_keys=False)
            message(f"Configuration saved to {self.config_file}", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
        except ConfigError as e:
            message(f"Invalid configuration - {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)
        except OSError as e:
            message(f"Failed to write configuration file: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)
        except Exception as e:
            message(f"Unexpected error writing configuration: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

    def read(self) -> ConfigData:
        """Load the configuration file with error handling.

        Returns:
            The loaded and validated configuration dictionary with repo objects

        Raises:
            SystemExit: If file cannot be read or config is invalid
        """
        try:
            with open(self.config_file) as f:
                config = yaml.safe_load(f)
                if config is None:
                    message(f"Configuration file {self.config_file} is empty", MessageType.ERROR, VerbosityLevel.ALWAYS)
                    sys.exit(1)

                warnings = self.validate(config)
                for warning in warnings:
                    message(f"Warning: {warning}", MessageType.WARNING, VerbosityLevel.ALWAYS)

                message(f"Configuration loaded from {self.config_file}", MessageType.DEBUG, VerbosityLevel.DEBUG)

                # Create repo objects for each repo entry
                for entry in config.get("repos", []):
                    repo = create_repo(entry["name"], entry["url"], self.repos_directory, entry["repo_type"])
                    entry["repo"] = repo

                return config
        except ConfigError as e:
            message(f"Invalid configuration - {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)
        except FileNotFoundError:
            message(f"Configuration file not found: {self.config_file}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)
        except yaml.YAMLError as e:
            message(f"Failed to parse configuration file: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)
        except OSError as e:
            message(f"Failed to read configuration file: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)
        except Exception as e:
            message(f"Unexpected error loading configuration: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

    def exists(self) -> bool:
        """Check if the configuration file exists.

        Returns:
            True if config file exists, False otherwise
        """
        return self.config_file.exists()

    def get_repo_names(self) -> list[str]:
        """Get list of repo names from the config file.

        Returns:
            List of repo names, or empty list if config doesn't exist
        """
        if not self.exists():
            return []
        try:
            with open(self.config_file) as f:
                config = yaml.safe_load(f)
                if config and "repos" in config:
                    return [entry["name"] for entry in config["repos"] if isinstance(entry, dict) and "name" in entry]
        except Exception:
            pass
        return []

    def get_directory_paths(self) -> list[str]:
        """Get list of directory paths from the config file.

        Returns:
            List of directory path keys, or empty list if config doesn't exist
        """
        if not self.exists():
            return []
        try:
            with open(self.config_file) as f:
                config = yaml.safe_load(f)
                if config and "directories" in config and isinstance(config["directories"], dict):
                    return list(config["directories"].keys())
        except Exception:
            pass
        return []

    def add_repo(self, name: str, url: str, repo_type: str | None = None) -> None:
        """Add a new repo to the configuration.

        Args:
            name: Name of the repo
            url: Repository URL
            repo_type: Optional repo type (auto-detected if not provided)
        """
        if not self.exists():
            message("No configuration file found. Run 'agent-manager config init' first.",
                    MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        if repo_type is None:
            matching_types = self.detect_repo_types(url)
            if len(matching_types) == 0:
                message("No repository type can handle this URL", MessageType.ERROR, VerbosityLevel.ALWAYS)
                sys.exit(1)
            elif len(matching_types) == 1:
                repo_type = matching_types[0]
            else:
                repo_type = self.prompt_for_repo_type(url, matching_types)

        message("Validating repository...", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)
        if not self.validate_repo_url(url):
            message("Invalid or inaccessible repository URL", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        url = self.normalize_url(url)
        config = self.read()

        if any(entry["name"] == name for entry in config.get("repos", [])):
            message(f"Repo '{name}' already exists", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        config.setdefault("repos", []).append({"name": name, "url": url, "repo_type": repo_type})
        self.write(config)

        message(f"Repo '{name}' added.", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
        message(
            f"To include it in the default hierarchy, run:\n"
            f"  agent-manager config defaults --repos {name}",
            MessageType.INFO, VerbosityLevel.ALWAYS,
        )

    def remove_repo(self, name: str, force: bool = False) -> None:
        """Remove a repo from the configuration.

        Args:
            name: Name of the repo to remove
            force: If True, cascade-remove from default_hierarchy and directory hierarchies
        """
        if not self.exists():
            message("No configuration file found.", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        config = self.read()

        repos = config.get("repos", [])
        if not any(entry["name"] == name for entry in repos):
            message(f"Repo '{name}' not found", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        # Check references
        references: list[str] = []
        if name in config.get("default_hierarchy", []):
            references.append("default_hierarchy")
        for dir_path, dir_config in config.get("directories", {}).items():
            if dir_config and name in dir_config.get("hierarchy", []):
                references.append(f"directory '{dir_path}' hierarchy")

        if references and not force:
            ref_list = "\n  - ".join(references)
            message(
                f"Error: '{name}' is referenced in:\n  - {ref_list}\n"
                f"Use --force to remove it from all references, or update those first.",
                MessageType.ERROR, VerbosityLevel.ALWAYS,
            )
            sys.exit(1)

        # Remove from repos
        config["repos"] = [entry for entry in repos if entry["name"] != name]

        # Cascade if forced
        if force and references:
            if "default_hierarchy" in config:
                config["default_hierarchy"] = [n for n in config["default_hierarchy"] if n != name]
            for dir_config in config.get("directories", {}).values():
                if dir_config and "hierarchy" in dir_config:
                    dir_config["hierarchy"] = [n for n in dir_config["hierarchy"] if n != name]

        self.write(config)
        message(f"Repo '{name}' removed.", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

    def add_directory(self, path: str, dir_type: str | None = None,
                      agents: list[str] | None = None,
                      hierarchy: list[str] | None = None) -> None:
        """Add a directory to the configuration.

        Args:
            path: Directory path (can use HOME keyword)
            dir_type: Directory type (e.g., 'git', 'local')
            agents: Optional list of agent names
            hierarchy: Optional list of repo names for hierarchy
        """
        if not self.exists():
            message("No configuration file found. Run 'agent-manager config init' first.",
                    MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        config = self.read()

        directories = config.setdefault("directories", {})
        if path in directories:
            message(f"Directory '{path}' already exists in config", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        dir_entry: dict[str, Any] = {}
        if dir_type:
            dir_entry["type"] = dir_type
        if agents:
            dir_entry["agents"] = agents
        if hierarchy:
            dir_entry["hierarchy"] = hierarchy

        directories[path] = dir_entry if dir_entry else None
        self.write(config)
        message(f"Directory '{path}' added.", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

    def remove_directory(self, path: str) -> None:
        """Remove a directory from the configuration.

        Args:
            path: Directory path to remove
        """
        if not self.exists():
            message("No configuration file found.", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        config = self.read()
        directories = config.get("directories", {})

        if path not in directories:
            message(f"Directory '{path}' not found in config", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        del directories[path]
        self.write(config)
        message(f"Directory '{path}' removed.", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

    def set_defaults(self, repos: list[str] | None = None, agents: list[str] | None = None) -> None:
        """Set default_hierarchy and/or default_agents.

        Declarative: replaces the entire list.

        Args:
            repos: Full list of repo names for default_hierarchy
            agents: Full list of agent names for default_agents
        """
        if not self.exists():
            message("No configuration file found.", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        config = self.read()

        if repos is not None:
            config["default_hierarchy"] = repos
        if agents is not None:
            config["default_agents"] = agents

        self.write(config)
        message("Defaults updated.", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

    def get_defaults(self) -> dict[str, list[str]]:
        """Get current default_hierarchy and default_agents.

        Returns:
            Dictionary with 'default_hierarchy' and 'default_agents' keys
        """
        if not self.exists():
            return {"default_hierarchy": [], "default_agents": []}

        try:
            with open(self.config_file) as f:
                config = yaml.safe_load(f)
                if config is None:
                    return {"default_hierarchy": [], "default_agents": []}
                return {
                    "default_hierarchy": config.get("default_hierarchy", []),
                    "default_agents": config.get("default_agents", []),
                }
        except Exception:
            return {"default_hierarchy": [], "default_agents": []}

    @staticmethod
    def generate_template() -> str:
        """Generate a commented YAML template for a new configuration.

        Returns:
            Template string suitable for writing to stdout or a file
        """
        return """# agent-manager configuration
# See docs/CONFIGURATION.md for full reference

repos:
  - name: example-org
    url: https://github.com/org/ai-configs.git
    repo_type: git
  - name: personal
    url: file:///path/to/your/personal_ai
    repo_type: file

default_hierarchy:
  - example-org
  - personal

default_agents:
  - cursor
  - claude

directories:
  HOME:
    type: local
    # inherits default_hierarchy and default_agents
  # HOME/GIT/your-project:
  #   type: git
  #   agents: [cursor]
  #   hierarchy: [personal]
"""
