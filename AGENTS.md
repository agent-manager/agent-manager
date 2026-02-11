# Agent Manager - AI Assistant Guide

## Project Overview

**Agent Manager** is a hierarchical configuration management framework for AI agents with a pluggable architecture. It enables organizations to maintain AI agent configurations at multiple levels (organizational, team, personal) with intelligent merging and type-aware content strategies.

### Core Concept
Configurations cascade from lowest to highest priority: Organization → Team → Personal, with intelligent merging based on file types (JSON, YAML, Markdown, etc.).

## Architecture

### Design Principles
1. **Pluggable Everything**: Agents, repositories, and mergers are all pluggable
2. **Type-Aware Merging**: Different merge strategies for different file types
3. **Hook System**: Pre/post-merge processing for custom logic
4. **Clean Separation**: Output (UI), config (data), core (logic), plugins (extensions)

### Directory Structure

```
agent_manager/
├── agent_manager/           # Main package
│   ├── output/             # Output system (logging with colors/verbosity)
│   ├── config/             # Configuration management
│   ├── core/               # Core functionality (repos, mergers, registry)
│   ├── cli_extensions/     # CLI commands (config, mergers, repos, agents)
│   ├── plugins/            # Plugin system
│   │   ├── agents/        # Agent implementations (AbstractAgent base)
│   │   ├── repos/         # Repository types (git, local, etc.)
│   │   └── mergers/       # Content mergers (json, yaml, markdown, etc.)
│   └── utils/             # Utilities (URL handling, etc.)
└── tests/                  # Comprehensive test suite (7,476 lines)
```

## Recent Major Changes

### Output System Refactor (November 2025)
**Complete refactor of output/logging system** - This is the most recent and significant change:

#### What Changed
- **Removed**: Multiple convenience functions (`error()`, `warning()`, `success()`, `info()`, `debug()`)
- **Added**: Single `message(text, msg_type, verbosity)` function
- **Separated**: Visual style (MessageType) from verbosity requirements (VerbosityLevel)

#### New Output API

```python
from agent_manager.output import MessageType, VerbosityLevel, message

# Always shown, no color, no prefix
message("Configuration initialized")

# Error (red, "Error: " prefix, stderr, always shown)
message("File not found", MessageType.ERROR)

# Warning (yellow, "Warning: " prefix, always shown)
message("This will overwrite!", MessageType.WARNING)

# Success (green, always shown)
message("✓ Configuration saved", MessageType.SUCCESS)

# Info at -vv level (cyan, no prefix)
message("Processing repository...", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)

# Debug at -vvv level (dim, "DEBUG: " prefix)
message("Loaded plugin: JsonMerger", MessageType.DEBUG, VerbosityLevel.DEBUG)
```

#### MessageType Guidelines

| Type | Use For | Color | Prefix | Output |
|------|---------|-------|--------|--------|
| `NORMAL` | User prompts, instructions | None | None | stdout |
| `SUCCESS` | Confirmations, completions | Green | None | stdout |
| `ERROR` | Failures, validation errors | Red | "Error: " | stderr |
| `WARNING` | Non-fatal issues | Yellow | "Warning: " | stdout |
| `INFO` | Progress, status updates | Cyan | None | stdout |
| `DEBUG` | Internal diagnostics | Dim | "DEBUG: " | stdout |

#### VerbosityLevel Guidelines

| Level | Flag | Value | Use For |
|-------|------|-------|---------|
| `ALWAYS` | (none) | 0 | User prompts, errors, success confirmations |
| `VERBOSE` | `-v` | 1 | Operation summaries, non-critical warnings |
| `EXTRA_VERBOSE` | `-vv` | 2 | Progress indicators, detailed steps |
| `DEBUG` | `-vvv` | 3 | Internal state, plugin discovery |

**See**: `OUTPUT_REFACTOR_SUMMARY.md` and `MESSAGE_CORRECTIONS.md` for complete details.

## Key Components

### 1. Configuration Management (`config/config.py`)
- **Purpose**: Manage hierarchical configuration file
- **Key Methods**:
  - `initialize()` - Interactive config creation
  - `read()` - Load and validate config
  - `add_level()`, `remove_level()`, `update_level()`, `move_level()` - Hierarchy management
- **File Location**: `~/.agent-manager/config.yaml`

### 2. Output System (`output/output.py`)
- **Purpose**: Unified logging with colors and verbosity control
- **Key Class**: `OutputManager`
- **Singleton**: Use `get_output()` to access global instance
- **Key Method**: `message(text, msg_type, verbosity)` - Single entry point for all output

### 3. Repository System (`core/repos.py`)
- **Purpose**: Abstract repository access (Git, local files, etc.)
- **Plugin-based**: Discover repo types via `AbstractRepo` subclasses
- **Key Functions**:
  - `discover_repo_types()` - Auto-discover repo plugins
  - `create_repo()` - Factory for repo instances
  - `update_repositories()` - Update all repos in config

### 4. Merger System (`core/mergers.py`, `core/merger_registry.py`)
- **Purpose**: Type-aware content merging
- **Plugin-based**: Mergers for JSON, YAML, Markdown, Text, Dict, etc.
- **Registry**: `MergerRegistry` maps file types to merger classes
- **Key Methods**:
  - `register_extension()` - Map file extension to merger
  - `register_filename()` - Map specific filename to merger
  - `get_merger()` - Get appropriate merger for a file

### 5. Agent System (`plugins/agents/agent.py`)
- **Purpose**: Abstract base for AI agent plugins
- **Key Method**: `merge_configurations()` - Merge hierarchy and run hooks
- **Hook System**: `pre_merge_hooks`, `post_merge_hooks` for custom logic

### 6. CLI Extensions (`cli_extensions/`)
- **AgentCommands**: `run` command, agent discovery
- **ConfigCommands**: `init`, `show`, `add`, `remove`, `update`, `move`, `validate`
- **MergerCommands**: `list`, `show`, `configure` mergers
- **RepoCommands**: Update repositories

## Development Guidelines

### Code Style
- **Formatter**: `ruff format`
- **Type Hints**: Use type annotations
- **Docstrings**: Google-style docstrings for all public methods
- **Line Length**: 120 characters (ruff default)

### Testing Requirements

**MANDATORY**: Every code change MUST include corresponding test updates.

#### Test Policy
1. **New features**: Add tests covering the new functionality
2. **Bug fixes**: Add a test that would have caught the bug
3. **Refactors**: Update existing tests if behavior changes
4. **No exceptions**: Even "trivial" changes need test verification

#### Before Completing Any Code Change
- [ ] Run affected tests to verify they pass
- [ ] Add new tests for new functionality
- [ ] Update existing tests if behavior changed
- [ ] Run `pytest tests/ -v` to ensure no regressions

#### Test Framework
- **Framework**: pytest
- **Location**: `tests/` directory mirrors `agent_manager/` structure
- **Coverage**: 99% (547/553 tests passing)
- **Run Tests**: `pytest tests/ -v`
- **Fast Tests**: `pytest tests/ -q --tb=no`

#### Test File Locations
| Source File | Test File |
|-------------|-----------|
| `agent_manager/config/config.py` | `tests/config/test_config.py` |
| `agent_manager/utils/url.py` | `tests/utils/test_url.py` |
| `agent_manager/plugins/repos/local_repo.py` | `tests/plugins/repos/test_local_repo.py` |
| `agent_manager/cli_extensions/config_commands.py` | `tests/cli_extensions/test_config_commands.py` |

### Plugin Development

#### Creating a New Agent Plugin

```python
from agent_manager.plugins.agents import AbstractAgent

class MyAgent(AbstractAgent):
    """My custom AI agent."""
    
    def run(self, config_data: dict, merged_dir: Path) -> None:
        """Run the agent with merged configuration."""
        # Your agent logic here
        pass
```

**Installation**: Plugins are auto-discovered via entry points in `pyproject.toml`:

```toml
[project.entry-points."agent_manager.agents"]
my_agent = "my_package.my_agent:MyAgent"
```

#### Creating a New Merger

```python
from agent_manager.plugins.mergers import AbstractMerger

class MyMerger(AbstractMerger):
    """Merger for my custom format."""
    
    def merge(self, base_content: str, override_content: str) -> str:
        """Merge two files of this type."""
        # Your merge logic here
        return merged_content
```

**Registration**: Register in merger registry or via entry points.

#### Creating a New Repository Type

```python
from agent_manager.plugins.repos import AbstractRepo

class MyRepo(AbstractRepo):
    """Repository implementation for my source."""
    
    @staticmethod
    def can_handle_url(url: str) -> bool:
        """Check if this repo can handle the URL."""
        return url.startswith("myrepo://")
    
    def update(self) -> None:
        """Update the repository."""
        pass
```

## Common Tasks

### Adding Output Messages

```python
from agent_manager.output import MessageType, VerbosityLevel, message

# User-facing prompts (always visible)
message("Please enter your choice:", MessageType.NORMAL, VerbosityLevel.ALWAYS)

# Validation errors (always visible)
message("Invalid input", MessageType.ERROR, VerbosityLevel.ALWAYS)

# Success confirmations (always visible)
message("✓ Configuration saved", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

# Progress indicators (only at -vv)
message("Processing files...", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)

# Debug information (only at -vvv)
message("Loaded plugin: X", MessageType.DEBUG, VerbosityLevel.DEBUG)
```

### Accessing Configuration

```python
from agent_manager.config import Config

config = Config()
config.ensure_directories()  # Ensure ~/.agent-manager/ exists
config_data = config.read()  # Load config

# Access hierarchy
for entry in config_data['hierarchy']:
    name = entry['name']
    url = entry['url']
    repo = entry['repo']  # AbstractRepo instance
```

### Using the Merger Registry

```python
from agent_manager.core import create_default_merger_registry

registry = create_default_merger_registry()

# Get merger for a file
merger = registry.get_merger("config.json")  # Returns JsonMerger
merger = registry.get_merger("README.md")    # Returns MarkdownMerger

# Merge two files
merged_content = merger.merge(base_content, override_content)
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/config/test_config.py -v

# Specific test
pytest tests/config/test_config.py::TestConfig::test_read -v

# Fast run (no verbose, no traceback)
pytest tests/ -q --tb=no

# With coverage
pytest tests/ --cov=agent_manager --cov-report=html
```

## Important Files

### Core Implementation
- `agent_manager/output/output.py` - Output system (191 lines)
- `agent_manager/config/config.py` - Config management (692 lines)
- `agent_manager/core/repos.py` - Repository system (172 lines)
- `agent_manager/core/mergers.py` - Merger system (55 lines)
- `agent_manager/core/merger_registry.py` - Merger registry (127 lines)

### Plugin Base Classes
- `agent_manager/plugins/agents/agent.py` - AbstractAgent (264 lines)
- `agent_manager/plugins/repos/abstract_repo.py` - AbstractRepo (105 lines)
- `agent_manager/plugins/mergers/abstract_merger.py` - AbstractMerger (92 lines)

### CLI
- `agent_manager/agent_manager.py` - Main entry point (84 lines)
- `agent_manager/cli_extensions/` - CLI commands (4 files, ~400 lines)

### Documentation
- `docs/` - Comprehensive documentation
  - `GETTING_STARTED.md` - Setup guide
  - `ARCHITECTURE.md` - System design
  - `CUSTOM_AGENTS.md` - Plugin development
  - `CLI_REFERENCE.md` - Command reference
- `OUTPUT_REFACTOR_SUMMARY.md` - Recent refactor details
- `MESSAGE_CORRECTIONS.md` - Output guidelines
- `REFACTOR_COMPLETE.md` - Refactor summary

## Configuration File Format

```yaml
hierarchy:
  - name: organization
    url: https://github.com/org/config.git
    repo_type: git
  - name: team
    url: https://github.com/team/config.git
    repo_type: git
  - name: personal
    url: file:///home/user/config
    repo_type: local

repos_dir: ~/.agent-manager/repos
output_dir: ~/.agent-manager/output

merger_preferences:
  json:
    indent: 2
    sort_keys: false
  yaml:
    indent: 2
  markdown:
    separator_style: "heading"
```

## Testing Philosophy

### Test Structure
- **Unit Tests**: Test individual functions/methods
- **Integration Tests**: Test component interactions
- **Mock Extensively**: Use `unittest.mock` for external dependencies
- **Fixtures**: Use pytest fixtures for common setup

### Test Patterns

```python
from unittest.mock import Mock, patch, MagicMock
import pytest

def test_example():
    """Test description."""
    # Arrange
    mock_config = Mock()
    mock_config.read.return_value = {"hierarchy": []}
    
    # Act
    with patch("agent_manager.config.Config", return_value=mock_config):
        result = some_function()
    
    # Assert
    assert result == expected
    mock_config.read.assert_called_once()
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure package is installed in development mode: `pip install -e .`
2. **Test Failures**: Check if Mock attributes are properly initialized (see `tests/test_agent_manager.py`)
3. **Output Not Showing**: Check verbosity level - use `ALWAYS` for user-facing messages
4. **Plugin Not Found**: Verify entry point in `pyproject.toml` and reinstall package

### Debug Mode

```bash
# Run with debug output (-vvv)
agent-manager -vvv run

# See all debug messages
agent-manager -vvv config show
```

## Statistics

- **Core Code**: 3,370 lines in 32 files
- **Tests**: 7,476 lines in 32 files
- **Test Coverage**: 99% (547/553 passing)
- **Plugin Types**: 3 (agents, repos, mergers)
- **Built-in Mergers**: 7 (JSON, YAML, Markdown, Text, Dict, XML, Copy)
- **Built-in Repos**: 2 (Git, Local)

## Key Design Decisions

1. **Single Message Function**: All output goes through one function with explicit type and verbosity
2. **Plugin Discovery**: Auto-discovery via entry points, no manual registration
3. **Immutable Base Content**: Mergers never modify original files
4. **YAML Configuration**: Human-readable, version-controllable config format
5. **Hook System**: Extensibility without modifying core code
6. **Type-Aware Merging**: Different strategies for different content types

## Plugin Ecosystem

### Naming Convention
All plugins follow the `am_<type>_<name>` pattern:
- **Agents**: `am_agent_<name>` (discovered by package prefix)
- **Mergers**: `am_merger_<name>` (discovered via entry points)
- **Repos**: `am_repo_<name>` (future)

### Official Companion Plugins

| Plugin | GitHub | Description |
|--------|--------|-------------|
| **am-agent-claude** | [john-westcott-iv/am-agent-claude](https://github.com/john-westcott-iv/am-agent-claude) | Claude/Cursor AI agent integration |
| **am-merger-smart-markdown** | [john-westcott-iv/am_merger_smart_markdown](https://github.com/john-westcott-iv/am_merger_smart_markdown) | Section-aware Markdown merging using mistletoe |

### Plugin Discovery

**Agents** are discovered by package prefix:
```python
# Packages starting with 'am_agent_' are auto-discovered
# e.g., am_agent_claude -> agent name: "claude"
agent-manager agents list
agent-manager run --agent claude
```

**Mergers** are discovered via entry points:
```toml
# In pyproject.toml
[project.entry-points."agent_manager.mergers"]
smart_markdown = "am_merger_smart_markdown.smart_markdown_merger:SmartMarkdownMerger"
```

```bash
agent-manager mergers list  # Shows registered and available mergers
```

## Future Considerations

- Consider fixing 6 failing integration tests (Mock attribute assignment issues)
- Document update needed for `docs/CUSTOM_*.md` files with new output API
- Potential new merger types (TOML, INI, etc.)
- Cloud-based repository types (S3, Azure Blob, etc.)

---

**Last Updated**: December 2025  
**Version**: 1.0.0  
**Python**: 3.12+  
**Key Dependencies**: Click, PyYAML, GitPython
**License**: Apache 2.0

