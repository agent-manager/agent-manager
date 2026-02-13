"""Configuration management class for agent-manager."""

import ast
import sys
from pathlib import Path
from typing import Any, TypedDict

import yaml

from agent_manager.core import create_repo, discover_repo_types
from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.utils import is_file_url, resolve_file_path


class HierarchyEntry(TypedDict):
    """Type definition for a hierarchy entry."""

    name: str
    url: str
    repo_type: str


class ConfigData(TypedDict):
    """Type definition for the configuration structure."""

    hierarchy: list[HierarchyEntry]


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
            # Resolve to absolute path and convert back to file:// URL
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
        # Use detect_repo_types to find matching types
        matching_type_names = Config.detect_repo_types(url)

        if len(matching_type_names) == 0:
            message(f"No repository type can handle URL: {url}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            return False

        # Get the first matching repo class
        # (if multiple types match, the user will choose during config)
        for repo_class in discover_repo_types():
            if matching_type_names[0] == repo_class.REPO_TYPE:
                # Delegate validation to the repo class
                return repo_class.validate_url(url)

        # Should never reach here if detect_repo_types works correctly
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
    def validate(config: dict[str, Any]) -> None:
        """Validate the configuration structure.

        Collects all validation errors before raising an exception.

        Args:
            config: The configuration dictionary to validate

        Raises:
            ConfigError: If the configuration is invalid, with all errors
        """
        errors = []

        # Check for hierarchy key
        if "hierarchy" not in config:
            errors.append("Configuration must contain 'hierarchy' key")
            # Can't continue without hierarchy
            raise ConfigError(errors)

        # Check hierarchy is a list
        if not isinstance(config["hierarchy"], list):
            errors.append("'hierarchy' must be a list")
            # Can't continue if not a list
            raise ConfigError(errors)

        # Check hierarchy is not empty
        if len(config["hierarchy"]) == 0:
            errors.append("'hierarchy' cannot be empty")
            raise ConfigError(errors)

        # Validate each hierarchy entry
        for idx, entry in enumerate(config["hierarchy"]):
            # Check entry is a dictionary
            if not isinstance(entry, dict):
                errors.append(f"Hierarchy entry {idx} must be a dictionary")
                # Skip further validation of this entry
                continue

            # Check for required keys
            required_keys = ["name", "url", "repo_type"]
            missing_keys = [key for key in required_keys if key not in entry]
            if missing_keys:
                errors.append(f"Hierarchy entry {idx} is missing required keys: {', '.join(missing_keys)}")

            # Validate 'name' field
            if "name" in entry:
                if not isinstance(entry["name"], str):
                    errors.append(f"Hierarchy entry {idx} 'name' must be a string, got {type(entry['name']).__name__}")
                elif not entry["name"]:
                    errors.append(f"Hierarchy entry {idx} 'name' cannot be empty")

            # Validate 'url' field
            if "url" in entry:
                if not isinstance(entry["url"], str):
                    errors.append(f"Hierarchy entry {idx} 'url' must be a string, got {type(entry['url']).__name__}")
                elif not entry["url"]:
                    errors.append(f"Hierarchy entry {idx} 'url' cannot be empty")

            # Validate 'repo_type' field
            if "repo_type" in entry:
                if not isinstance(entry["repo_type"], str):
                    errors.append(
                        f"Hierarchy entry {idx} 'repo_type' must be a string, got {type(entry['repo_type']).__name__}"
                    )
                elif not entry["repo_type"]:
                    errors.append(f"Hierarchy entry {idx} 'repo_type' cannot be empty")

        # Raise exception with all errors if any were found
        if errors:
            raise ConfigError(errors)

    def write(self, config: ConfigData) -> None:
        """Write the configuration to the config file with validation.

        Args:
            config: The configuration dictionary to write

        Raises:
            SystemExit: If validation fails or file cannot be written
        """
        try:
            # Validate before writing
            self.validate(config)

            # Create a clean copy without repo objects (which can't be serialized)
            clean_config = {"hierarchy": []}
            for entry in config["hierarchy"]:
                clean_entry = {
                    "name": entry["name"],
                    "url": entry["url"],
                    "repo_type": entry["repo_type"],
                }
                clean_config["hierarchy"].append(clean_entry)

            # Copy over any additional top-level keys (like merger settings)
            for key, value in config.items():
                if key != "hierarchy":
                    clean_config[key] = value

            # Write to file
            with open(self.config_file, "w") as f:
                yaml.dump(clean_config, f, default_flow_style=False, sort_keys=False)
            print(f"\n✓ Configuration saved to {self.config_file}")
        except ConfigError as e:
            print(f"Error: Invalid configuration - {e}")
            sys.exit(1)
        except OSError as e:
            print(f"Error: Failed to write configuration file: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error: Unexpected error writing configuration: {e}")
            sys.exit(1)

    def read(self) -> ConfigData:
        """Load the configuration file with error handling.

        Returns:
            The loaded and validated configuration dictionary

        Raises:
            SystemExit: If file cannot be read or config is invalid
        """
        try:
            with open(self.config_file) as f:
                # Read the config file
                config = yaml.safe_load(f)
                if config is None:
                    message(f"Configuration file {self.config_file} is empty", MessageType.ERROR, VerbosityLevel.ALWAYS)
                    sys.exit(1)

                # Validate config structure after loading
                self.validate(config)
                message(f"Configuration loaded from {self.config_file}", MessageType.DEBUG, VerbosityLevel.DEBUG)

                # Crate repo objects for each hierarchy entry
                for entry in config["hierarchy"]:
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

    def initialize(self, skip_if_already_created: bool = True) -> None:
        """Interactively create the config file.

        Args:
            skip_if_already_created: If True, skip initialization if config
                                    already exists. If False, prompt user
                                    to confirm overwrite.
        """
        if self.config_file.exists():
            if skip_if_already_created:
                message("Configuration file already exists, skipping", MessageType.DEBUG, VerbosityLevel.DEBUG)
                return

            # Confirm overwrite
            message(
                f"\nConfiguration file already exists: {self.config_file}", MessageType.WARNING, VerbosityLevel.ALWAYS
            )
            message("This will overwrite your existing configuration!", MessageType.WARNING, VerbosityLevel.ALWAYS)
            response = input("\nContinue? (yes/no): ").strip().lower()

            if response not in ["yes", "y"]:
                message("Initialization cancelled.", MessageType.NORMAL, VerbosityLevel.ALWAYS)
                return

            message("\nReinitializing configuration...\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        else:
            message("No configuration file found. Let's create one!", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            message("(Press Ctrl+C at any time to exit)\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Prompt for hierarchy with retry loop
        hierarchy_list = None
        while hierarchy_list is None:
            message(
                "Enter your hierarchy levels, from LOWEST to HIGHEST priority.",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )
            message("(first = base, last = overrides all)", MessageType.NORMAL, VerbosityLevel.ALWAYS)
            example = "(e.g., organization, team, personal): "
            hierarchy_input = input(example).strip()

            if not hierarchy_input:
                message("Hierarchy cannot be empty. Please try again.\n", MessageType.ERROR, VerbosityLevel.ALWAYS)
                continue

            # Try parsing as Python list first (for backward compatibility)
            if hierarchy_input.startswith("["):
                try:
                    hierarchy_list = ast.literal_eval(hierarchy_input)
                    if not isinstance(hierarchy_list, list):
                        message("Invalid list format. Please try again.\n", MessageType.ERROR, VerbosityLevel.ALWAYS)
                        hierarchy_list = None
                        continue
                except (ValueError, SyntaxError):
                    message("Invalid list format. Please try again.\n", MessageType.ERROR, VerbosityLevel.ALWAYS)
                    continue
            else:
                # Parse as comma-separated values
                hierarchy_list = [level.strip() for level in hierarchy_input.split(",") if level.strip()]

            # Validate we got at least one level
            if not hierarchy_list:
                message(
                    "Hierarchy must have at least one level. Please try again.\n",
                    MessageType.ERROR,
                    VerbosityLevel.ALWAYS,
                )
                hierarchy_list = None
                continue

            # Validate level names (no special characters that would cause issues)
            invalid_names = [name for name in hierarchy_list if not name or "/" in name or "\\" in name]
            if invalid_names:
                message(
                    f"Invalid level name(s): {invalid_names}. Names cannot be empty or contain slashes.",
                    MessageType.ERROR,
                    VerbosityLevel.ALWAYS,
                )
                message("Please try again.\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)
                hierarchy_list = None

        # Prompt for repository URL for each hierarchy level
        hierarchy_config: list[HierarchyEntry] = []
        message("\nNow, provide the repository URL for each level:", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        message("(Git URL or file:// path, e.g., file:///path/to/dir)\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        for level in hierarchy_list:
            repo_url = ""
            repo_type = ""
            valid = False
            while not valid:
                repo_url = input(f"  URL for '{level}': ").strip()
                if not repo_url:
                    message("URL cannot be empty. Please try again.", MessageType.ERROR, VerbosityLevel.ALWAYS)
                    continue

                # Detect which repo types can handle this URL
                matching_types = self.detect_repo_types(repo_url)

                if len(matching_types) == 0:
                    message(
                        "No repository type can handle this URL. Please try again.",
                        MessageType.ERROR,
                        VerbosityLevel.ALWAYS,
                    )
                    continue
                elif len(matching_types) == 1:
                    # Only one match - use it
                    repo_type = matching_types[0]
                    message(f"Detected repository type: {repo_type}", MessageType.DEBUG, VerbosityLevel.DEBUG)
                else:
                    # Multiple matches - prompt user
                    repo_type = self.prompt_for_repo_type(repo_url, matching_types)

                # Validate the repository is accessible
                message("Validating repository...", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)
                if self.validate_repo_url(repo_url):
                    message("✓ Valid repository", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
                    # Normalize the URL to ensure file:// URLs are absolute
                    repo_url = self.normalize_url(repo_url)
                    valid = True
                else:
                    message("Please try again with a valid URL.", MessageType.NORMAL, VerbosityLevel.ALWAYS)
                    repo_url = ""
                    repo_type = ""

            hierarchy_config.append({"name": level, "url": repo_url, "repo_type": repo_type})

        # Create config structure and write it
        config: ConfigData = {"hierarchy": hierarchy_config}
        self.write(config)

    def exists(self) -> bool:
        """Check if the configuration file exists.

        Returns:
            True if config file exists, False otherwise
        """
        return self.config_file.exists()

    def add_level(self, name: str, url: str, position: int | None = None) -> None:
        """Add a new level to the hierarchy.

        Args:
            name: Name of the new hierarchy level
            url: Repository URL (git URL or file:// path)
            position: Optional position to insert (0-based).
                     If None, appends to end.
        """
        if not self.exists():
            message(
                "No configuration file found. Run without arguments to create one.",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(1)

        # Detect repo type
        matching_types = self.detect_repo_types(url)
        if len(matching_types) == 0:
            message("No repository type can handle this URL", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)
        elif len(matching_types) == 1:
            repo_type = matching_types[0]
            message(f"Detected repository type: {repo_type}", MessageType.DEBUG, VerbosityLevel.DEBUG)
        else:
            repo_type = self.prompt_for_repo_type(url, matching_types)

        # Validate repository URL
        message("Validating repository...", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)
        if not self.validate_repo_url(url):
            message("Invalid or inaccessible repository URL", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        # Normalize the URL to ensure file:// URLs are absolute
        url = self.normalize_url(url)

        config = self.read()

        # Check if name already exists
        if any(entry["name"] == name for entry in config["hierarchy"]):
            message(f"Hierarchy level '{name}' already exists", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        # Add the new entry
        new_entry: HierarchyEntry = {"name": name, "url": url, "repo_type": repo_type}

        if position is not None:
            if position < 0 or position > len(config["hierarchy"]):
                message(
                    f"Invalid position. Must be between 0 and {len(config['hierarchy'])}",
                    MessageType.ERROR,
                    VerbosityLevel.ALWAYS,
                )
                sys.exit(1)
            config["hierarchy"].insert(position, new_entry)
            message(f"✓ Added '{name}' at position {position}", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
        else:
            config["hierarchy"].append(new_entry)
            message(f"✓ Added '{name}' as highest priority level", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

        self.write(config)

    def remove_level(self, name: str) -> None:
        """Remove a level from the hierarchy.

        Args:
            name: Name of the hierarchy level to remove
        """
        if not self.exists():
            message(
                "No configuration file found. Run without arguments to create one.",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(1)

        config = self.read()

        # Find and remove the entry
        original_length = len(config["hierarchy"])
        config["hierarchy"] = [entry for entry in config["hierarchy"] if entry["name"] != name]

        if len(config["hierarchy"]) == original_length:
            message(f"Hierarchy level '{name}' not found", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        if len(config["hierarchy"]) == 0:
            message("Cannot remove the last hierarchy level", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        message(f"✓ Removed hierarchy level '{name}'", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
        self.write(config)

    def update_level(self, name: str, new_url: str | None = None, new_name: str | None = None) -> None:
        """Update an existing hierarchy level.

        Args:
            name: Current name of the hierarchy level
            new_url: Optional new repository URL (git URL or file:// path)
            new_name: Optional new name for the level
        """
        if not self.exists():
            message(
                "No configuration file found. Run without arguments to create one.",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(1)

        if not new_url and not new_name:
            message("Must specify either --url or --rename", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        config = self.read()

        # Find the entry
        entry_found = False
        for entry in config["hierarchy"]:
            if entry["name"] == name:
                entry_found = True

                # Validate new URL if provided
                if new_url:
                    # Detect repo type for new URL
                    matching_types = self.detect_repo_types(new_url)
                    if len(matching_types) == 0:
                        message("No repository type can handle this URL", MessageType.ERROR, VerbosityLevel.ALWAYS)
                        sys.exit(1)
                    elif len(matching_types) == 1:
                        new_repo_type = matching_types[0]
                        message(f"Detected repository type: {new_repo_type}", MessageType.DEBUG, VerbosityLevel.DEBUG)
                    else:
                        new_repo_type = self.prompt_for_repo_type(new_url, matching_types)

                    message("Validating repository...", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)
                    if not self.validate_repo_url(new_url):
                        message("Invalid or inaccessible repository URL", MessageType.ERROR, VerbosityLevel.ALWAYS)
                        sys.exit(1)
                    # Normalize the URL to ensure file:// URLs are absolute
                    new_url = self.normalize_url(new_url)
                    entry["url"] = new_url
                    entry["repo_type"] = new_repo_type
                    message(f"✓ Updated URL for '{name}'", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

                # Check if new name already exists
                if new_name:
                    name_exists = any(e["name"] == new_name for e in config["hierarchy"] if e["name"] != name)
                    if name_exists:
                        message(
                            f"Hierarchy level '{new_name}' already exists", MessageType.ERROR, VerbosityLevel.ALWAYS
                        )
                        sys.exit(1)
                    entry["name"] = new_name
                    message(f"✓ Renamed '{name}' to '{new_name}'", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

                break

        if not entry_found:
            message(f"Hierarchy level '{name}' not found", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        self.write(config)

    def move_level(self, name: str, position: int | None = None, direction: str | None = None) -> None:
        """Move a hierarchy level to a new position.

        Args:
            name: Name of the hierarchy level to move
            position: New position (0-based), or None if using direction
            direction: 'up' or 'down' to move relative, or None if using
                       position
        """
        if not self.exists():
            message(
                "No configuration file found. Run without arguments to create one.",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(1)

        if position is None and direction is None:
            message("Must specify either --position or --up/--down", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        if position is not None and direction is not None:
            message("Cannot specify both --position and --up/--down", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        config = self.read()

        # Find the entry
        current_idx = None
        for idx, entry in enumerate(config["hierarchy"]):
            if entry["name"] == name:
                current_idx = idx
                break

        if current_idx is None:
            message(f"Hierarchy level '{name}' not found", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

        # Calculate new position
        if direction:
            if direction == "up":
                new_pos = current_idx - 1
            elif direction == "down":
                new_pos = current_idx + 1
            else:
                message("Direction must be 'up' or 'down'", MessageType.ERROR, VerbosityLevel.ALWAYS)
                sys.exit(1)
        else:
            new_pos = position

        # Validate new position
        if new_pos < 0 or new_pos >= len(config["hierarchy"]):
            message(
                f"Invalid position. Must be between 0 and {len(config['hierarchy']) - 1}",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(1)

        if new_pos == current_idx:
            message(f"'{name}' is already at position {current_idx}", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)
            return

        # Move the entry
        entry = config["hierarchy"].pop(current_idx)
        config["hierarchy"].insert(new_pos, entry)

        message(
            f"✓ Moved '{name}' from position {current_idx} to {new_pos}", MessageType.SUCCESS, VerbosityLevel.ALWAYS
        )
        self.write(config)
