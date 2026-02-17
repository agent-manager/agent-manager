"""Core infrastructure for agent-manager plugin system."""

from .agents import discover_agent_plugins, get_agent_names, load_agent, run_agents
from .manifest import (
    add_or_update_entry,
    cleanup_stale_files,
    get_manifest_entry,
    is_managed,
    read_manifest,
    remove_agent_from_entry,
    write_manifest,
)
from .merger_registry import MergerRegistry
from .mergers import create_default_merger_registry, discover_merger_classes
from .repos import create_repo, discover_repo_types, get_repo_type_map, update_repositories
from .safety import (
    ClobberAction,
    TypeValidation,
    check_clobber,
    should_proceed_on_type_mismatch,
    should_write_file,
    validate_directory_type,
)

__all__ = [
    "ClobberAction",
    "MergerRegistry",
    "TypeValidation",
    "add_or_update_entry",
    "check_clobber",
    "cleanup_stale_files",
    "create_default_merger_registry",
    "create_repo",
    "discover_agent_plugins",
    "discover_merger_classes",
    "discover_repo_types",
    "get_agent_names",
    "get_manifest_entry",
    "get_repo_type_map",
    "is_managed",
    "load_agent",
    "read_manifest",
    "remove_agent_from_entry",
    "run_agents",
    "should_proceed_on_type_mismatch",
    "should_write_file",
    "update_repositories",
    "validate_directory_type",
    "write_manifest",
]
