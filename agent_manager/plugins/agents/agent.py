"""Abstract base class for AI agent plugins."""

import fnmatch
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.core import MergerRegistry


@dataclass
class ScopeConfig:
    """Configuration for a single scope.

    Attributes:
        directory: The output directory for this scope
        description: Human-readable description of the scope
    """

    directory: Path
    description: str = ""


class AbstractAgent(ABC):
    """Base class for AI agent plugins with hierarchical configuration merging."""

    home_directory: Path = Path.home()
    agent_directory: Path = home_directory

    @property
    @abstractmethod
    def scopes(self) -> dict:
        """Define available scopes for this agent.

        Must be implemented by subclasses. Returns a dictionary mapping
        scope names to ScopeConfig objects.

        Example:
            @property
            def scopes(self) -> dict[str, ScopeConfig]:
                return {
                    "default": ScopeConfig(directory=Path.home() / ".myagent", description="..."),
                    "user": ScopeConfig(directory=Path.home() / ".myagent", description="..."),
                }

        Returns:
            Dictionary mapping scope names to ScopeConfig objects
        """
        pass

    # Default scope name
    DEFAULT_SCOPE = "default"

    def get_scope_names(self) -> list[str]:
        """Get list of available scope names for this agent.

        Returns:
            Sorted list of scope names
        """
        return sorted(self.scopes.keys())

    def get_scope_directory(self, scope: str | None = None) -> Path:
        """Get the output directory for a specific scope.

        Args:
            scope: Scope name. If None, uses DEFAULT_SCOPE.

        Returns:
            Path to the scope's output directory

        Raises:
            ValueError: If the scope is not supported by this agent
        """
        if scope is None:
            scope = self.DEFAULT_SCOPE

        scopes = self.scopes
        if scope not in scopes:
            available = ", ".join(sorted(scopes.keys()))
            raise ValueError(f"Unknown scope '{scope}'. Available scopes: {available}")

        return scopes[scope].directory

    # Default files/directories to exclude when discovering configs
    BASE_EXCLUDE_PATTERNS = [
        ".git",
        ".gitignore",
        "__pycache__",
        "*.pyc",
        ".DS_Store",
        "README.md",
        "LICENSE",
        ".venv",
        "venv",
        "env",
        "node_modules",
        ".pytest_cache",
        ".ruff_cache",
        "*.egg-info",
    ]

    def __init__(self):
        """Initialize the agent with hook registries and merger registry."""
        # Hook registries: file_pattern -> hook_function
        self.pre_merge_hooks: dict[str, Callable] = {}
        self.post_merge_hooks: dict[str, Callable] = {}

        # Build complete exclude patterns (base + agent-specific)
        self.exclude_patterns = self.BASE_EXCLUDE_PATTERNS.copy()
        self.exclude_patterns.extend(self.get_additional_excludes())

        # Initialize merger registry with default mergers
        self.merger_registry = MergerRegistry()
        self.register_default_mergers()

        # Register default hooks, then let agent plugins add custom ones
        self._register_default_hooks()
        self.register_hooks()

    def register_default_mergers(self) -> None:
        """Register built-in mergers for common file types.

        Uses late import to avoid circular dependency with agent_manager.
        """
        # Late import to avoid circular dependency
        from agent_manager.agent_manager import create_default_merger_registry

        # Get a pre-configured registry and copy its registrations
        default_registry = create_default_merger_registry()
        self.merger_registry.filename_mergers = default_registry.filename_mergers.copy()
        self.merger_registry.extension_mergers = default_registry.extension_mergers.copy()
        self.merger_registry.default_merger = default_registry.default_merger

    def get_agent_name(self) -> str:
        """Get the display name for this agent.

        Used in metadata headers and logging. Override to customize.
        Default returns the agent directory name without the leading dot.

        Returns:
            Agent display name (e.g., "claude", "cursor")
        """
        name = self.agent_directory.name
        return name.lstrip(".")

    def _register_default_hooks(self) -> None:
        """Register default hooks common to all agents.

        Sets up markdown cleaning and metadata header generation.
        Called before register_hooks() so plugins can override if needed.
        """
        # Pre-merge: Clean up markdown files
        self.pre_merge_hooks["*.md"] = self._clean_markdown

        # Post-merge: Add metadata header to merged files
        self.post_merge_hooks["*"] = self._add_metadata_header

    def register_hooks(self) -> None:
        """Register agent-specific hooks for pre/post merge processing.

        Override this method to register additional hooks for specific file patterns.
        Default hooks (markdown cleaning, metadata headers) are already registered.

        Example:
            def register_hooks(self) -> None:
                self.pre_merge_hooks[".cursorrules"] = self._validate_cursorrules
                self.post_merge_hooks["*.json"] = self._format_json
        """
        pass

    def _clean_markdown(self, content: str, entry: dict, file_path: Path) -> str:
        """Clean up markdown content before merging.

        Strips trailing whitespace and ensures single newline at end.

        Args:
            content: File content
            entry: Hierarchy entry
            file_path: Path to source file

        Returns:
            Cleaned content
        """
        content = content.rstrip() + "\n"
        message(f"    Cleaned markdown from {entry['name']}", MessageType.DEBUG, VerbosityLevel.DEBUG)
        return content

    def _add_metadata_header(self, content: str, file_name: str, sources: list[str]) -> str:
        """Add metadata header to merged files with appropriate comment syntax.

        Args:
            content: Merged content
            file_name: Output filename
            sources: List of source hierarchy levels

        Returns:
            Content with metadata header
        """
        file_lower = file_name.lower()

        # JSON doesn't support comments, skip header
        if file_lower.endswith(".json"):
            return content

        # Determine comment style based on file extension
        if file_lower.endswith((".yaml", ".yml", ".txt", ".py", ".sh", ".cursorrules", ".clinerules")):
            comment_start = "# "
            comment_end = ""
        elif file_lower.endswith((".md", ".markdown", ".html", ".xml")):
            comment_start = "<!-- "
            comment_end = " -->"
        else:
            comment_start = "# "
            comment_end = ""

        # Build header with appropriate comment syntax
        agent_name = self.get_agent_name()
        header = f"{comment_start}Generated by agent-manager ({agent_name} agent){comment_end}\n"
        header += f"{comment_start}File: {file_name}{comment_end}\n"
        header += f"{comment_start}Sources: {' → '.join(sources)}{comment_end}\n"
        header += (
            f"{comment_start}Hierarchy: {sources[0]} (lowest) to {sources[-1]} (highest priority){comment_end}\n\n"
        )

        return header + content

    def _initialize(self, scope: str | None = None) -> None:
        """Initialize the agent's configuration directory.

        Creates the output directory if it doesn't exist. Override this method
        for agent-specific initialization (e.g., running SDK commands).

        Args:
            scope: Scope to initialize. If None, uses default scope.
        """
        output_dir = self.get_scope_directory(scope)

        if output_dir.exists():
            message(
                f"{self.get_agent_name()} directory already exists: {output_dir}",
                MessageType.DEBUG,
                VerbosityLevel.DEBUG,
            )
            return

        message(
            f"Initializing {self.get_agent_name()} directory: {output_dir}",
            MessageType.INFO,
            VerbosityLevel.EXTRA_VERBOSE,
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        message(f"✓ Created {output_dir}", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

    def update(self, config: dict, scope: str | None = None) -> None:
        """Update agent configuration from hierarchical repositories.

        Default implementation initializes the directory and merges configurations.
        Override for agent-specific update behavior.

        Args:
            config: Configuration data with hierarchy and repo objects
            scope: Configuration scope to use. If None, uses default scope.
        """
        self._initialize(scope)
        self.merge_configurations(config, scope)

    def get_additional_excludes(self) -> list[str]:
        """Get agent-specific exclude patterns.

        Override this method to add additional patterns to exclude when discovering files.
        These will be added to BASE_EXCLUDE_PATTERNS.

        Returns:
            List of additional patterns to exclude (default: empty list)
        """
        return []

    def get_repo_directory_name(self, scope: str | None = None) -> str:
        """Get the directory name to look for in repositories.

        By default, uses the name of the scope's directory (e.g., ".claude" from ~/.claude).
        If _repo_directory_name is set, uses that instead (useful for testing).

        Args:
            scope: Scope name. If None, uses DEFAULT_SCOPE.

        Returns:
            Directory name to search for in repositories
        """
        repo_dir_name = getattr(self, "_repo_directory_name", None)
        if repo_dir_name:
            return repo_dir_name
        return self.get_scope_directory(scope).name

    def _discover_files(self, repo_path: Path, scope: str | None = None) -> list[Path]:
        """Discover configuration files in agent-specific directory within repository.

        Searches for files in <repo_path>/<agent_directory_name>/ recursively.
        For example, if agent_directory is ~/.claude, this searches repo_path/.claude/

        This allows repos to contain configurations for multiple agents:
        - repo/.claude/agents/JIRA.md
        - repo/.cursor/rules.txt
        - repo/.copilot/settings.json

        Each agent only discovers files in its own directory.

        Args:
            repo_path: Path to the repository
            scope: Scope name for determining which directory to look in

        Returns:
            List of configuration file paths found in agent directory
        """
        found_files = []

        # Get the agent directory name to look for in repos
        agent_dir_name = self.get_repo_directory_name(scope)

        # Look for agent-specific directory in the repo
        agent_repo_dir = repo_path / agent_dir_name
        if not agent_repo_dir.exists() or not agent_repo_dir.is_dir():
            return []

        # Recursively find all files in the agent directory
        for item in agent_repo_dir.rglob("*"):
            # Skip directories
            if item.is_dir():
                continue

            # Skip if matches exclude pattern
            should_exclude = False
            for pattern in self.exclude_patterns:
                if fnmatch.fnmatch(item.name, pattern):
                    should_exclude = True
                    break

            if not should_exclude:
                found_files.append(item)

        return sorted(found_files)  # Sort for consistent ordering

    def get_agent_directory(self, scope: str | None = None) -> Path:
        """Get the agent's configuration directory.

        Args:
            scope: Scope name. If None, uses DEFAULT_SCOPE.

        Returns:
            Path to the agent directory for the given scope
        """
        return self.get_scope_directory(scope)

    def _should_include_entry_for_scope(self, entry: dict, scope: str) -> bool:
        """Check if a hierarchy entry should be included for the given scope.

        If the entry has a 'scopes' key, only include it if the scope is in that list.
        If no 'scopes' key is present, include the entry for all scopes.

        Args:
            entry: Hierarchy entry from config
            scope: Current scope being processed

        Returns:
            True if the entry should be included, False otherwise
        """
        entry_scopes = entry.get("scopes")
        if entry_scopes is None:
            # No scopes specified = applies to all scopes
            return True
        return scope in entry_scopes

    def merge_configurations(self, config: dict, scope: str | None = None) -> None:
        """Merge configuration files from hierarchical repositories.

        Traverses the hierarchy (org -> team -> personal) and merges files
        with type-aware strategies and hook support.

        Args:
            config: Configuration data with hierarchy and repo objects
            scope: Scope to merge for. If None, uses DEFAULT_SCOPE.
        """
        if scope is None:
            scope = self.DEFAULT_SCOPE

        # Validate scope
        output_dir = self.get_scope_directory(scope)
        scope_config = self.scopes[scope]

        message(f"\n=== Merging Configurations for scope '{scope}' ===", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        message(f"Output directory: {output_dir}", MessageType.INFO, VerbosityLevel.VERBOSE)
        if scope_config.description:
            message(f"({scope_config.description})\n", MessageType.NORMAL, VerbosityLevel.VERBOSE)

        # Track merged files: filename -> (content, source_info_list)
        merged_files: dict[str, tuple[str, list[str]]] = {}

        # Process hierarchy from lowest to highest priority (org -> team -> personal)
        for entry in config["hierarchy"]:
            # Check if this entry applies to the current scope
            if not self._should_include_entry_for_scope(entry, scope):
                message(
                    f"Skipping '{entry['name']}' (not in scope '{scope}')",
                    MessageType.DEBUG,
                    VerbosityLevel.DEBUG,
                )
                continue

            name = entry["name"]
            repo = entry["repo"]
            repo_path = repo.get_path()

            message(f"Processing '{name}' repository...", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)
            message(f"  Path: {repo_path}", MessageType.DEBUG, VerbosityLevel.DEBUG)

            # Check if repository exists locally
            if not repo_path.exists():
                message(f"  Repository path does not exist: {repo_path}", MessageType.WARNING, VerbosityLevel.ALWAYS)
                continue

            # Discover files in this repository
            files = self._discover_files(repo_path, scope)

            if not files:
                message(f"  No configuration files found in '{name}'", MessageType.NORMAL, VerbosityLevel.ALWAYS)
                continue

            message(f"  Found {len(files)} file(s)", MessageType.DEBUG, VerbosityLevel.DEBUG)

            for file_path in files:
                # Get relative path from agent directory in repo
                # e.g., repo/.claude/agents/JIRA.md -> agents/JIRA.md
                agent_repo_dir = repo_path / self.get_repo_directory_name(scope)
                try:
                    relative_path = file_path.relative_to(agent_repo_dir)
                    file_key = str(relative_path)  # Use relative path as key
                except ValueError:
                    # Fallback to just filename if relative_to fails
                    file_key = file_path.name

                try:
                    content = file_path.read_text()
                    message(f"    Processing: {file_key}", MessageType.DEBUG, VerbosityLevel.DEBUG)

                    # PRE-MERGE HOOK: Allow plugin-specific preprocessing
                    content = self._run_hook(self.pre_merge_hooks, file_key, content, entry, file_path)

                    # Merge with existing content for this file (by relative path)
                    if file_key in merged_files:
                        existing_content, sources = merged_files[file_key]

                        # Get appropriate merger for this file
                        merger_class = self.merger_registry.get_merger(file_path)

                        # Get merger settings from config
                        merger_settings = config.get("mergers", {}).get(merger_class.__name__, {})

                        # Merge using the registered merger
                        merged_content = merger_class.merge(existing_content, content, name, sources, **merger_settings)
                        sources.append(name)
                        merged_files[file_key] = (merged_content, sources)
                    else:
                        # First occurrence of this file
                        merged_files[file_key] = (content, [name])

                except Exception as e:
                    message(f"    Could not process {file_key}: {e}", MessageType.WARNING, VerbosityLevel.ALWAYS)

            message(f"  ✓ Processed '{name}'", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

        # Write merged files with POST-MERGE HOOKS
        if merged_files:
            message(
                f"\nWriting {len(merged_files)} merged file(s) to {output_dir}...",
                MessageType.NORMAL,
                VerbosityLevel.ALWAYS,
            )

            for file_path_str, (content, sources) in merged_files.items():
                # POST-MERGE HOOK: Allow plugin-specific postprocessing
                content = self._run_hook(self.post_merge_hooks, file_path_str, content, None, None, sources)

                # Preserve directory structure: use relative path as-is
                output_path = output_dir / file_path_str
                try:
                    # Ensure parent directories exist
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(content)
                    message(
                        f"  ✓ Wrote {file_path_str} (from {len(sources)} source(s): {', '.join(sources)})",
                        MessageType.SUCCESS,
                        VerbosityLevel.ALWAYS,
                    )
                except Exception as e:
                    message(f"  ✗ Failed to write {file_path_str}: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
        else:
            message("No configuration files found in any hierarchy level", MessageType.WARNING, VerbosityLevel.ALWAYS)

        message("\n✓ Configuration merge complete!", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

    def _run_hook(
        self,
        hooks: dict[str, Callable],
        file_name: str,
        content: str,
        entry: dict | None,
        file_path: Path | None,
        sources: list[str] | None = None,
    ) -> str:
        """Run registered hooks for a file pattern.

        Args:
            hooks: Hook registry to search
            file_name: Name of the file
            content: Current content
            entry: Hierarchy entry (None for post-merge)
            file_path: Path to source file (None for post-merge)
            sources: List of sources (for post-merge hooks)

        Returns:
            Possibly modified content
        """
        for pattern, hook_func in hooks.items():
            if fnmatch.fnmatch(file_name, pattern):
                try:
                    # Call hook with available context
                    if sources is not None:
                        # Post-merge hook signature
                        content = hook_func(content, file_name, sources)
                    else:
                        # Pre-merge hook signature
                        content = hook_func(content, entry, file_path)
                except Exception as e:
                    message(
                        f"  Hook error for {file_name} (pattern: {pattern}): {e}",
                        MessageType.WARNING,
                        VerbosityLevel.ALWAYS,
                    )
        return content
