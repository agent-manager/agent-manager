"""Tests for plugins/agents/agent.py - Abstract agent base class."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agent_manager.plugins.agents.agent import AbstractAgent


class ConcreteAgent(AbstractAgent):
    """Concrete implementation for testing AbstractAgent."""

    # Use a test agent directory name
    agent_directory: Path = Path.home() / ".testagent"

    # Set the repo directory name explicitly so it doesn't change if agent_directory is overridden
    _repo_directory_name: str = ".testagent"

    @property
    def scopes(self) -> dict:
        """Define test scopes."""
        from agent_manager.plugins.agents import ScopeConfig

        return {
            "default": ScopeConfig(
                directory=self.agent_directory,
                description="Test scope",
            ),
        }

    def register_hooks(self) -> None:
        """Concrete implementation of register_hooks."""
        # For testing, register some sample hooks
        self.pre_merge_hooks["test.txt"] = self._test_pre_hook
        self.post_merge_hooks["*.md"] = self._test_post_hook

    def _test_pre_hook(self, content: str, entry: dict, file_path: Path) -> str:
        """Sample pre-merge hook for testing."""
        return content + "\n# Pre-hook applied"

    def _test_post_hook(self, content: str, file_name: str, sources: list[str]) -> str:
        """Sample post-merge hook for testing."""
        return content + f"\n# Post-hook applied from {len(sources)} sources"


class TestAbstractAgentInitialization:
    """Test cases for AbstractAgent initialization."""

    def test_initialization(self):
        """Test basic agent initialization."""
        agent = ConcreteAgent()

        assert agent.pre_merge_hooks is not None
        assert agent.post_merge_hooks is not None
        assert agent.exclude_patterns is not None
        assert agent.merger_registry is not None

    def test_exclude_patterns_include_base(self):
        """Test that exclude patterns include BASE_EXCLUDE_PATTERNS."""
        agent = ConcreteAgent()

        # Should include base patterns
        assert ".git" in agent.exclude_patterns
        assert "__pycache__" in agent.exclude_patterns
        assert "*.pyc" in agent.exclude_patterns

    def test_register_hooks_called(self):
        """Test that register_hooks is called during initialization."""
        agent = ConcreteAgent()

        # ConcreteAgent registers hooks in register_hooks()
        assert "test.txt" in agent.pre_merge_hooks
        assert "*.md" in agent.post_merge_hooks

    def test_home_directory_set(self):
        """Test that home_directory is set."""
        agent = ConcreteAgent()

        assert agent.home_directory == Path.home()

    def test_agent_directory_set(self):
        """Test that agent_directory is set."""
        agent = ConcreteAgent()

        assert agent.agent_directory == Path.home() / ".testagent"


class TestAbstractAgentExcludePatterns:
    """Test cases for exclude pattern management."""

    def test_base_exclude_patterns(self):
        """Test that BASE_EXCLUDE_PATTERNS contains expected patterns."""
        patterns = AbstractAgent.BASE_EXCLUDE_PATTERNS

        assert ".git" in patterns
        assert ".gitignore" in patterns
        assert "__pycache__" in patterns
        assert "*.pyc" in patterns
        assert ".DS_Store" in patterns
        assert "README.md" in patterns
        assert ".venv" in patterns

    def test_get_additional_excludes_default(self):
        """Test that get_additional_excludes returns empty list by default."""
        agent = ConcreteAgent()

        additional = agent.get_additional_excludes()

        assert additional == []

    def test_exclude_patterns_are_combined(self):
        """Test that exclude patterns combine base and additional."""

        class AgentWithExcludes(AbstractAgent):
            @property
            def scopes(self):
                from agent_manager.plugins.agents import ScopeConfig

                return {"default": ScopeConfig(directory=Path.home() / ".test", description="Test")}

            def get_additional_excludes(self):
                return ["custom.txt", "*.log"]

        agent = AgentWithExcludes()

        # Should have both base and custom patterns
        assert ".git" in agent.exclude_patterns
        assert "custom.txt" in agent.exclude_patterns
        assert "*.log" in agent.exclude_patterns


class TestAbstractAgentRootLevelFiles:
    """Test cases for root-level file discovery configuration."""

    def test_base_root_level_files_exists(self):
        """Test that BASE_ROOT_LEVEL_FILES class attribute exists."""
        assert hasattr(AbstractAgent, 'BASE_ROOT_LEVEL_FILES')
        assert isinstance(AbstractAgent.BASE_ROOT_LEVEL_FILES, list)

    def test_base_root_level_files_contains_agents_md(self):
        """Test that BASE_ROOT_LEVEL_FILES contains AGENTS.md."""
        assert "AGENTS.md" in AbstractAgent.BASE_ROOT_LEVEL_FILES


class TestAbstractAgentFileDiscovery:
    """Test cases for file discovery."""

    def test_discover_files_finds_root_files(self, tmp_path):
        """Test that _discover_files finds files in agent directory."""
        # Create agent directory and test files
        agent_dir = tmp_path / ".testagent"
        agent_dir.mkdir()
        (agent_dir / "config.yaml").touch()
        (agent_dir / "settings.json").touch()
        (agent_dir / ".cursorrules").touch()

        agent = ConcreteAgent()
        files = agent._discover_files(tmp_path)

        file_names = [f.name for f in files]
        assert "config.yaml" in file_names
        assert "settings.json" in file_names
        # Dot files like .cursorrules are legitimate config files and should be found
        assert ".cursorrules" in file_names

    def test_discover_files_excludes_directories(self, tmp_path):
        """Test that _discover_files recursively finds files but excludes directories."""
        agent_dir = tmp_path / ".testagent"
        agent_dir.mkdir()
        (agent_dir / "config.yaml").touch()
        (agent_dir / "subdir").mkdir()
        (agent_dir / "subdir" / "nested.txt").touch()

        agent = ConcreteAgent()
        files = agent._discover_files(tmp_path)

        # Should include both config.yaml and nested.txt (recursive search)
        file_names = [f.name for f in files]
        assert "config.yaml" in file_names
        assert "nested.txt" in file_names
        assert len(files) == 2

    def test_discover_files_excludes_patterns(self, tmp_path):
        """Test that _discover_files excludes files matching exclude patterns."""
        agent_dir = tmp_path / ".testagent"
        agent_dir.mkdir()
        (agent_dir / "config.yaml").touch()
        (agent_dir / "README.md").touch()  # Excluded by BASE_EXCLUDE_PATTERNS
        (agent_dir / ".DS_Store").touch()  # Excluded (hidden file)

        agent = ConcreteAgent()
        files = agent._discover_files(tmp_path)

        file_names = [f.name for f in files]
        assert "config.yaml" in file_names
        assert "README.md" not in file_names
        assert ".DS_Store" not in file_names

    def test_discover_files_excludes_wildcard_patterns(self, tmp_path):
        """Test that _discover_files handles wildcard patterns."""
        agent_dir = tmp_path / ".testagent"
        agent_dir.mkdir()
        (agent_dir / "config.yaml").touch()
        (agent_dir / "test.pyc").touch()  # Excluded by *.pyc

        agent = ConcreteAgent()
        files = agent._discover_files(tmp_path)

        file_names = [f.name for f in files]
        assert "config.yaml" in file_names
        assert "test.pyc" not in file_names

    def test_discover_files_returns_sorted(self, tmp_path):
        """Test that _discover_files returns files in sorted order."""
        agent_dir = tmp_path / ".testagent"
        agent_dir.mkdir()
        (agent_dir / "zebra.txt").touch()
        (agent_dir / "alpha.txt").touch()
        (agent_dir / "middle.txt").touch()

        agent = ConcreteAgent()
        files = agent._discover_files(tmp_path)

        file_names = [f.name for f in files]
        assert file_names == ["alpha.txt", "middle.txt", "zebra.txt"]

    def test_discover_files_handles_empty_directory(self, tmp_path):
        """Test that _discover_files handles repos without agent directory."""
        agent = ConcreteAgent()
        files = agent._discover_files(tmp_path)

        # No .testagent directory exists, should return empty
        assert files == []

    def test_discover_files_handles_empty_agent_directory(self, tmp_path):
        """Test that _discover_files handles empty agent directories."""
        agent_dir = tmp_path / ".testagent"
        agent_dir.mkdir()

        agent = ConcreteAgent()
        files = agent._discover_files(tmp_path)

        assert files == []

    def test_discover_files_finds_nested_files(self, tmp_path):
        """Test that _discover_files recursively finds nested files."""
        agent_dir = tmp_path / ".testagent"
        (agent_dir / "agents").mkdir(parents=True)
        (agent_dir / "commands").mkdir(parents=True)
        (agent_dir / "agents" / "JIRA.md").touch()
        (agent_dir / "commands" / "test.txt").touch()
        (agent_dir / "root.yaml").touch()

        agent = ConcreteAgent()
        files = agent._discover_files(tmp_path)

        file_names = [f.name for f in files]
        assert "JIRA.md" in file_names
        assert "test.txt" in file_names
        assert "root.yaml" in file_names
        assert len(files) == 3

    def test_discover_files_ignores_other_agent_directories(self, tmp_path):
        """Test that _discover_files only finds files in its own agent directory."""
        # Create files for .testagent (our agent)
        testagent_dir = tmp_path / ".testagent"
        testagent_dir.mkdir()
        (testagent_dir / "my-config.yaml").touch()
        (testagent_dir / "my-rules.txt").touch()

        # Create files for .otherapp (different agent)
        otherapp_dir = tmp_path / ".otherapp"
        otherapp_dir.mkdir()
        (otherapp_dir / "other-config.yaml").touch()
        (otherapp_dir / "other-rules.txt").touch()

        # Create files at repo root (should be ignored)
        (tmp_path / "root-config.yaml").touch()

        agent = ConcreteAgent()
        files = agent._discover_files(tmp_path)

        file_names = [f.name for f in files]
        # Should only find files from .testagent
        assert "my-config.yaml" in file_names
        assert "my-rules.txt" in file_names
        # Should NOT find files from .otherapp or root
        assert "other-config.yaml" not in file_names
        assert "other-rules.txt" not in file_names
        assert "root-config.yaml" not in file_names
        assert len(files) == 2

    def test_merge_configurations_preserves_directory_structure(self, tmp_path):
        """Test that merge_configurations preserves subdirectory structure."""
        # Create repo with nested directory structure
        org_path = tmp_path / "org"
        org_path.mkdir()

        # Create nested structure in .testagent
        (org_path / ".testagent" / "agents").mkdir(parents=True)
        (org_path / ".testagent" / "commands").mkdir(parents=True)
        (org_path / ".testagent" / "agents" / "JIRA.md").write_text("# JIRA Agent")
        (org_path / ".testagent" / "commands" / "test.md").write_text("# Test Command")
        (org_path / ".testagent" / "root.yaml").write_text("root: true")

        org_repo = Mock()
        org_repo.get_path.return_value = org_path

        config = {"hierarchy": [{"name": "org", "repo": org_repo}]}

        agent = ConcreteAgent()
        agent.agent_directory = tmp_path / "output"
        agent.agent_directory.mkdir()

        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(config)

        # Verify directory structure is preserved
        assert (agent.agent_directory / "agents" / "JIRA.md").exists()
        assert (agent.agent_directory / "commands" / "test.md").exists()
        assert (agent.agent_directory / "root.yaml").exists()

        # Verify content
        jira_content = (agent.agent_directory / "agents" / "JIRA.md").read_text()
        assert "# JIRA Agent" in jira_content


class TestAbstractAgentGetAgentDirectory:
    """Test cases for get_agent_directory method."""

    def test_get_agent_directory_returns_path(self):
        """Test that get_agent_directory returns the agent_directory."""
        agent = ConcreteAgent()

        directory = agent.get_agent_directory()

        assert directory == agent.agent_directory
        assert isinstance(directory, Path)


class TestAbstractAgentRunHook:
    """Test cases for hook execution."""

    def test_run_hook_executes_matching_hook(self, tmp_path):
        """Test that _run_hook executes hooks for matching patterns."""
        agent = ConcreteAgent()

        content = "Original content"
        entry = {"name": "test"}
        file_path = tmp_path / "test.txt"

        # Run hook (test.txt matches registered pre-hook)
        result = agent._run_hook(agent.pre_merge_hooks, "test.txt", content, entry, file_path)

        assert "# Pre-hook applied" in result

    def test_run_hook_executes_wildcard_pattern(self, tmp_path):
        """Test that _run_hook handles wildcard patterns."""
        agent = ConcreteAgent()

        content = "Original content"
        sources = ["org", "team"]

        # Run hook (*.md matches registered post-hook)
        result = agent._run_hook(agent.post_merge_hooks, "README.md", content, None, None, sources)

        assert "# Post-hook applied from 2 sources" in result

    def test_run_hook_no_match(self, tmp_path):
        """Test that _run_hook returns content unchanged when no hook matches."""
        agent = ConcreteAgent()

        content = "Original content"
        entry = {"name": "test"}
        file_path = tmp_path / "no-match.xyz"

        result = agent._run_hook(agent.pre_merge_hooks, "no-match.xyz", content, entry, file_path)

        assert result == content

    def test_run_hook_handles_exception(self, tmp_path):
        """Test that _run_hook handles hook exceptions gracefully."""

        class FaultyAgent(AbstractAgent):
            @property
            def scopes(self):
                from agent_manager.plugins.agents import ScopeConfig

                return {"default": ScopeConfig(directory=Path.home() / ".test", description="Test")}

            def register_hooks(self):
                self.pre_merge_hooks["*.txt"] = self._faulty_hook

            def _faulty_hook(self, content, entry, file_path):
                raise Exception("Hook error")

        agent = FaultyAgent()

        content = "Original content"
        entry = {"name": "test"}
        file_path = tmp_path / "test.txt"

        with patch("agent_manager.plugins.agents.agent.message"):
            result = agent._run_hook(agent.pre_merge_hooks, "test.txt", content, entry, file_path)

            # Should return original content despite error
            assert result == content


class TestAbstractAgentMergeConfigurations:
    """Test cases for configuration merging."""

    def test_merge_configurations_processes_hierarchy(self, tmp_path):
        """Test that merge_configurations processes all hierarchy levels."""
        # Create mock repositories with agent-specific directories
        org_path = tmp_path / "org"
        team_path = tmp_path / "team"
        org_path.mkdir()
        team_path.mkdir()

        # Create agent directories and files
        (org_path / ".testagent").mkdir()
        (team_path / ".testagent").mkdir()
        (org_path / ".testagent" / "config.yaml").write_text("org: true")
        (team_path / ".testagent" / "config.yaml").write_text("team: true")

        org_repo = Mock()
        org_repo.get_path.return_value = org_path

        team_repo = Mock()
        team_repo.get_path.return_value = team_path

        config = {
            "hierarchy": [
                {"name": "org", "repo": org_repo},
                {"name": "team", "repo": team_repo},
            ]
        }

        agent = ConcreteAgent()
        agent.agent_directory = tmp_path / "output"
        agent.agent_directory.mkdir()

        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(config)

        # Should have merged and written config.yaml
        output_file = agent.agent_directory / "config.yaml"
        assert output_file.exists()

    def test_merge_configurations_handles_missing_repo_path(self, tmp_path):
        """Test that merge_configurations handles missing repository paths."""
        missing_repo = Mock()
        missing_repo.get_path.return_value = tmp_path / "nonexistent"

        config = {"hierarchy": [{"name": "missing", "repo": missing_repo}]}

        agent = ConcreteAgent()
        agent.agent_directory = tmp_path / "output"
        agent.agent_directory.mkdir()

        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(config)

        # Should not crash, just skip missing repo
        output_files = list(agent.agent_directory.iterdir())
        assert len(output_files) == 0

    def test_merge_configurations_handles_empty_repo(self, tmp_path):
        """Test that merge_configurations handles repos with no files."""
        empty_path = tmp_path / "empty"
        empty_path.mkdir()

        empty_repo = Mock()
        empty_repo.get_path.return_value = empty_path

        config = {"hierarchy": [{"name": "empty", "repo": empty_repo}]}

        agent = ConcreteAgent()
        agent.agent_directory = tmp_path / "output"
        agent.agent_directory.mkdir()

        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(config)

        # Should not crash
        output_files = list(agent.agent_directory.iterdir())
        assert len(output_files) == 0

    def test_merge_configurations_uses_merger_registry(self, tmp_path):
        """Test that merge_configurations uses the merger registry."""
        org_path = tmp_path / "org"
        team_path = tmp_path / "team"
        org_path.mkdir()
        team_path.mkdir()

        # Create agent directories and files
        (org_path / ".testagent").mkdir()
        (team_path / ".testagent").mkdir()
        (org_path / ".testagent" / "config.json").write_text('{"org": true}')
        (team_path / ".testagent" / "config.json").write_text('{"team": true}')

        org_repo = Mock()
        org_repo.get_path.return_value = org_path

        team_repo = Mock()
        team_repo.get_path.return_value = team_path

        config = {
            "hierarchy": [
                {"name": "org", "repo": org_repo},
                {"name": "team", "repo": team_repo},
            ]
        }

        agent = ConcreteAgent()
        agent.agent_directory = tmp_path / "output"
        agent.agent_directory.mkdir()

        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(config)

        # Should have merged JSON and written output
        output_file = agent.agent_directory / "config.json"
        assert output_file.exists()

        # Content should be merged (both keys present)
        import json

        content = json.loads(output_file.read_text())
        assert "org" in content
        assert "team" in content

    def test_merge_configurations_applies_pre_merge_hooks(self, tmp_path):
        """Test that merge_configurations applies pre-merge hooks."""
        org_path = tmp_path / "org"
        org_path.mkdir()

        # Create agent directory and files
        (org_path / ".testagent").mkdir()
        (org_path / ".testagent" / "test.txt").write_text("Content")

        org_repo = Mock()
        org_repo.get_path.return_value = org_path

        config = {"hierarchy": [{"name": "org", "repo": org_repo}]}

        agent = ConcreteAgent()
        agent.agent_directory = tmp_path / "output"
        agent.agent_directory.mkdir()

        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(config)

        output_file = agent.agent_directory / "test.txt"
        assert output_file.exists()

        content = output_file.read_text()
        assert "# Pre-hook applied" in content

    def test_merge_configurations_applies_post_merge_hooks(self, tmp_path):
        """Test that merge_configurations applies post-merge hooks."""
        org_path = tmp_path / "org"
        org_path.mkdir()

        # Create agent directory and files
        (org_path / ".testagent").mkdir()
        (org_path / ".testagent" / "config.md").write_text("# Content")

        org_repo = Mock()
        org_repo.get_path.return_value = org_path

        config = {"hierarchy": [{"name": "org", "repo": org_repo}]}

        agent = ConcreteAgent()
        agent.agent_directory = tmp_path / "output"
        agent.agent_directory.mkdir()

        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(config)

        output_file = agent.agent_directory / "config.md"
        assert output_file.exists()

        content = output_file.read_text()
        assert "# Post-hook applied from 1 sources" in content

    def test_merge_configurations_handles_file_read_error(self, tmp_path):
        """Test that merge_configurations handles file read errors gracefully."""
        org_path = tmp_path / "org"
        org_path.mkdir()

        # Create a file that will cause an error when read
        # (by making it a directory instead of a file)
        (org_path / "bad.txt").mkdir()

        org_repo = Mock()
        org_repo.get_path.return_value = org_path

        config = {"hierarchy": [{"name": "org", "repo": org_repo}]}

        agent = ConcreteAgent()
        agent.agent_directory = tmp_path / "output"
        agent.agent_directory.mkdir()

        with patch("agent_manager.plugins.agents.agent.message"):
            # Should not crash
            agent.merge_configurations(config)

    def test_merge_configurations_handles_file_write_error(self, tmp_path):
        """Test that merge_configurations handles file write errors gracefully."""
        org_path = tmp_path / "org"
        org_path.mkdir()

        # Create agent directory and files
        (org_path / ".testagent").mkdir()
        (org_path / ".testagent" / "config.yaml").write_text("test: true")

        org_repo = Mock()
        org_repo.get_path.return_value = org_path

        config = {"hierarchy": [{"name": "org", "repo": org_repo}]}

        agent = ConcreteAgent()
        # Set agent_directory to a file (not a directory) to cause write error
        bad_output = tmp_path / "bad_output"
        bad_output.touch()
        agent.agent_directory = bad_output

        with patch("agent_manager.plugins.agents.agent.message"):
            # Should not crash
            agent.merge_configurations(config)


class TestAbstractAgentAbstractMethods:
    """Test cases for abstract method enforcement."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that AbstractAgent cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AbstractAgent()

    def test_must_implement_scopes(self):
        """Test that subclasses must implement scopes property."""

        class IncompleteAgent(AbstractAgent):
            # Missing scopes property
            pass

        with pytest.raises(TypeError):
            IncompleteAgent()


class TestAbstractAgentExceptionHandling:
    """Test exception handling during file processing."""

    def test_merge_configurations_handles_file_processing_exception(self, tmp_path):
        """Test that merge_configurations handles exceptions when processing files."""
        org_path = tmp_path / "org"
        org_path.mkdir()

        # Create a file that will cause an exception
        test_file = org_path / "test.json"
        test_file.write_text("not valid json")

        org_repo = Mock()
        org_repo.get_path.return_value = org_path

        config = {"hierarchy": [{"name": "org", "repo": org_repo}]}

        agent = ConcreteAgent()
        agent.agent_directory = tmp_path / "output"
        agent.agent_directory.mkdir()

        # Make the merger raise an exception
        with (
            patch("agent_manager.plugins.agents.agent.message"),
            patch.object(agent.merger_registry, "get_merger") as mock_get_merger,
        ):
            mock_merger = Mock()
            mock_merger.merge.side_effect = ValueError("Test error")
            mock_get_merger.return_value = mock_merger

            # Should not raise, just log warning
            agent.merge_configurations(config)


class TestAbstractAgentEdgeCases:
    """Test cases for edge cases and special scenarios."""

    def test_merge_configurations_with_merger_settings(self, tmp_path):
        """Test that merge_configurations passes merger settings."""
        org_path = tmp_path / "org"
        team_path = tmp_path / "team"
        org_path.mkdir()
        team_path.mkdir()

        # Create agent directories and files
        (org_path / ".testagent").mkdir()
        (team_path / ".testagent").mkdir()
        (org_path / ".testagent" / "config.json").write_text('{"key": "value1"}')
        (team_path / ".testagent" / "config.json").write_text('{"key": "value2"}')

        org_repo = Mock()
        org_repo.get_path.return_value = org_path

        team_repo = Mock()
        team_repo.get_path.return_value = team_path

        config = {
            "hierarchy": [
                {"name": "org", "repo": org_repo},
                {"name": "team", "repo": team_repo},
            ],
            "mergers": {"JsonMerger": {"indent": 2}},
        }

        agent = ConcreteAgent()
        agent.agent_directory = tmp_path / "output"
        agent.agent_directory.mkdir()

        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(config)

        # Should have applied merger settings
        output_file = agent.agent_directory / "config.json"
        assert output_file.exists()

    def test_discover_files_with_unicode_filenames(self, tmp_path):
        """Test that _discover_files handles Unicode filenames."""
        # Create agent directory and files
        agent_dir = tmp_path / ".testagent"
        agent_dir.mkdir()
        (agent_dir / "配置.yaml").touch()
        (agent_dir / "Конфигурация.json").touch()

        agent = ConcreteAgent()
        files = agent._discover_files(tmp_path)

        assert len(files) == 2

    def test_merge_configurations_with_unicode_content(self, tmp_path):
        """Test that merge_configurations handles Unicode content."""
        org_path = tmp_path / "org"
        org_path.mkdir()

        # Create agent directory and files
        (org_path / ".testagent").mkdir()
        (org_path / ".testagent" / "config.txt").write_text("你好世界 🌍", encoding="utf-8")

        org_repo = Mock()
        org_repo.get_path.return_value = org_path

        config = {"hierarchy": [{"name": "org", "repo": org_repo}]}

        agent = ConcreteAgent()
        agent.agent_directory = tmp_path / "output"
        agent.agent_directory.mkdir()

        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(config)

        output_file = agent.agent_directory / "config.txt"
        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        assert "你好世界" in content
        assert "🌍" in content
