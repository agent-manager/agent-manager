"""Repository utilities for agent-manager."""

import importlib
import inspect
import pkgutil
import sys
from pathlib import Path

from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.utils import get_disabled_plugins


def discover_repo_types(include_disabled: bool = False):
    """Dynamically discover all repository type classes.

    Scans the plugins.repos package for all classes that inherit from AbstractRepo
    (excluding AbstractRepo itself).

    Args:
        include_disabled: If True, include disabled repo type plugins

    Returns:
        List of repository class types
    """
    from agent_manager.plugins.repos import AbstractRepo

    repo_types = []

    # Get disabled repos if filtering
    disabled_repos = get_disabled_plugins().get("repos", []) if not include_disabled else []

    # Get the repos package path
    import agent_manager.plugins.repos as repos_package

    repo_package_path = Path(repos_package.__file__).parent

    # Iterate through all Python files in the repos directory
    for module_info in pkgutil.iter_modules([str(repo_package_path)]):
        module_name = module_info.name

        # Skip private modules, __init__, and abstract_repo
        if module_name.startswith("_") or module_name == "abstract_repo":
            continue

        try:
            # Import the module
            module = importlib.import_module(f"agent_manager.plugins.repos.{module_name}")

            # Find all classes in the module
            for _name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a subclass of AbstractRepo
                # (but not AbstractRepo itself)
                if issubclass(obj, AbstractRepo) and obj is not AbstractRepo and obj.__module__ == module.__name__:
                    # Check if this repo type is disabled
                    if hasattr(obj, "REPO_TYPE") and obj.REPO_TYPE in disabled_repos:
                        message(f"Skipping disabled repo type: {obj.REPO_TYPE}", MessageType.DEBUG, VerbosityLevel.DEBUG)
                        continue
                    repo_types.append(obj)

        except ImportError:
            # Skip modules that can't be imported (e.g., missing dependencies)
            continue

    return repo_types


def build_repo_type_map():
    """Build a map of repo type strings to their classes.

    Returns:
        Dictionary mapping repo type names to their classes
    """
    repo_types = discover_repo_types()
    return {repo_class.REPO_TYPE: repo_class for repo_class in repo_types}


# Lazily initialized map of repo type strings to their classes
_REPO_TYPE_MAP = None


def get_repo_type_map():
    """Get the repo type map, building it if necessary.

    Returns:
        Dictionary mapping repo type names to their classes
    """
    global _REPO_TYPE_MAP
    if _REPO_TYPE_MAP is None:
        _REPO_TYPE_MAP = build_repo_type_map()
    return _REPO_TYPE_MAP


def create_repo(name: str, url: str, repos_dir: Path, repo_type: str):
    """Factory function to create the appropriate repository type.

    Args:
        name: Name of the hierarchy level
        url: Repository URL
        repos_dir: Base directory where repos are stored
        repo_type: Type of repository (e.g., 'git', 'local', 's3')

    Returns:
        An instance of AbstractRepo (GitRepo, LocalRepo, etc.)

    Raises:
        SystemExit: If the repo type is not supported
    """
    repo_type_map = get_repo_type_map()
    repo_class = repo_type_map.get(repo_type)

    if repo_class is None:
        message(f"Unsupported repository type for '{name}': {repo_type}", MessageType.ERROR, VerbosityLevel.ALWAYS)
        message(f"URL: {url}", MessageType.ERROR, VerbosityLevel.ALWAYS)
        available_types = ", ".join(repo_type_map.keys())
        message(f"Available types: {available_types}", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)
        sys.exit(1)

    return repo_class(name, url, repos_dir)


def update_repositories(config_data: dict, force: bool = False) -> None:
    """Update all repositories in the hierarchy.

    Args:
        config_data: The configuration data with repo objects
        force: If True, update even if repo appears up to date
    """
    message("\nUpdating repositories...\n", MessageType.NORMAL, VerbosityLevel.ALWAYS)

    errors = False
    for idx, entry in enumerate(config_data["hierarchy"], 1):
        name = entry["name"]
        repo = entry["repo"]  # Use the repo object from config

        message(f"[{idx}/{len(config_data['hierarchy'])}] {name}", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        try:
            # Check if update is needed
            if force or repo.needs_update():
                repo.update()
            else:
                message(f"  {name} is up to date, skipping", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        except Exception as e:
            message(f"Failed to update '{name}': {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            errors = True

    if errors:
        message("\n✗ Some repositories failed to update", MessageType.ERROR, VerbosityLevel.ALWAYS)
        sys.exit(1)

    message("\n✓ All repositories updated successfully!", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
