"""Tests for plugins/agents/agent.py - V2 Abstract agent base class."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agent_manager.plugins.agents.agent import AbstractAgent


class ConcreteAgent(AbstractAgent):
    """Concrete implementation for testing AbstractAgent."""

    agent_subdirectory = ".testagent"

    def register_hooks(self) -> None:
        self.pre_merge_hooks["*test.txt"] = self._test_pre_hook
        self.post_merge_hooks["*.md"] = self._test_post_hook

    def _test_pre_hook(
        self, content: str, repo_name: str, file_path: Path
    ) -> str:
        return content + "\n# Pre-hook applied"

    def _test_post_hook(
        self, content: str, file_name: str, sources: list[str]
    ) -> str:
        return content + f"\n# Post-hook applied from {len(sources)} sources"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_repo(tmp_path: Path, name: str, files: dict[str, str]) -> Mock:
    """Create a mock repo with files on disk.

    Args:
        tmp_path: Base temp directory
        name: Repo directory name
        files: Mapping of relative paths to contents
    """
    repo_path = tmp_path / name
    repo_path.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        fpath = repo_path / rel
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content)
    repo = Mock()
    repo.get_path.return_value = repo_path
    return repo


# ===========================================================================
# Initialization
# ===========================================================================
class TestAbstractAgentInit:

    def test_initialization(self):
        agent = ConcreteAgent()
        assert agent.pre_merge_hooks is not None
        assert agent.post_merge_hooks is not None
        assert agent.exclude_patterns is not None
        assert agent.merger_registry is not None

    def test_exclude_patterns_include_base(self):
        agent = ConcreteAgent()
        assert ".git" in agent.exclude_patterns
        assert "__pycache__" in agent.exclude_patterns

    def test_register_hooks_called(self):
        agent = ConcreteAgent()
        assert "*test.txt" in agent.pre_merge_hooks
        assert "*.md" in agent.post_merge_hooks

    def test_get_agent_name(self):
        agent = ConcreteAgent()
        assert agent.get_agent_name() == "testagent"

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            AbstractAgent()

    def test_must_implement_agent_subdirectory(self):
        class Incomplete(AbstractAgent):
            pass

        with pytest.raises(TypeError):
            Incomplete()


# ===========================================================================
# Exclude patterns
# ===========================================================================
class TestExcludePatterns:

    def test_base_patterns(self):
        patterns = AbstractAgent.BASE_EXCLUDE_PATTERNS
        assert ".git" in patterns
        assert "*.pyc" in patterns

    def test_additional_excludes(self):
        class CustomAgent(AbstractAgent):
            agent_subdirectory = ".custom"

            def get_additional_excludes(self):
                return ["custom.txt", "*.log"]

        agent = CustomAgent()
        assert "custom.txt" in agent.exclude_patterns
        assert "*.log" in agent.exclude_patterns
        assert ".git" in agent.exclude_patterns


# ===========================================================================
# Root-level files
# ===========================================================================
class TestRootLevelFiles:

    def test_base_root_level_files(self):
        assert "AGENTS.md" in AbstractAgent.BASE_ROOT_LEVEL_FILES

    def test_default_additional_empty(self):
        agent = ConcreteAgent()
        assert agent.get_additional_root_level_files() == []

    def test_combined(self):
        agent = ConcreteAgent()
        files = agent._get_root_level_files()
        assert "AGENTS.md" in files

    def test_custom_root_files(self):
        class CustomAgent(AbstractAgent):
            agent_subdirectory = ".custom"

            def get_additional_root_level_files(self):
                return ["CUSTOM.md"]

        agent = CustomAgent()
        files = agent._get_root_level_files()
        assert "AGENTS.md" in files
        assert "CUSTOM.md" in files


# ===========================================================================
# File discovery
# ===========================================================================
class TestFileDiscovery:

    def test_finds_agent_dir_files(self, tmp_path):
        agent_dir = tmp_path / ".testagent"
        agent_dir.mkdir()
        (agent_dir / "config.yaml").touch()
        (agent_dir / "settings.json").touch()

        agent = ConcreteAgent()
        names = [f.name for f in agent._discover_files(tmp_path)]
        assert "config.yaml" in names
        assert "settings.json" in names

    def test_excludes_patterns(self, tmp_path):
        agent_dir = tmp_path / ".testagent"
        agent_dir.mkdir()
        (agent_dir / "config.yaml").touch()
        (agent_dir / "README.md").touch()
        (agent_dir / ".DS_Store").touch()

        agent = ConcreteAgent()
        names = [f.name for f in agent._discover_files(tmp_path)]
        assert "config.yaml" in names
        assert "README.md" not in names
        assert ".DS_Store" not in names

    def test_recursive_discovery(self, tmp_path):
        agent_dir = tmp_path / ".testagent"
        (agent_dir / "sub").mkdir(parents=True)
        (agent_dir / "root.txt").touch()
        (agent_dir / "sub" / "nested.txt").touch()

        agent = ConcreteAgent()
        names = [f.name for f in agent._discover_files(tmp_path)]
        assert "root.txt" in names
        assert "nested.txt" in names

    def test_empty_repo(self, tmp_path):
        agent = ConcreteAgent()
        assert agent._discover_files(tmp_path) == []

    def test_empty_agent_dir(self, tmp_path):
        (tmp_path / ".testagent").mkdir()
        agent = ConcreteAgent()
        assert agent._discover_files(tmp_path) == []

    def test_ignores_other_agent_dirs(self, tmp_path):
        our = tmp_path / ".testagent"
        our.mkdir()
        (our / "ours.txt").touch()

        other = tmp_path / ".other"
        other.mkdir()
        (other / "theirs.txt").touch()

        agent = ConcreteAgent()
        names = [f.name for f in agent._discover_files(tmp_path)]
        assert "ours.txt" in names
        assert "theirs.txt" not in names

    def test_root_level_agents_md(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# Agents")

        agent = ConcreteAgent()
        names = [f.name for f in agent._discover_files(tmp_path)]
        assert "AGENTS.md" in names

    def test_root_level_before_subdir(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("root")
        agent_dir = tmp_path / ".testagent"
        agent_dir.mkdir()
        (agent_dir / "AGENTS.md").write_text("subdir")

        agent = ConcreteAgent()
        files = agent._discover_files(tmp_path)
        agents_files = [f for f in files if f.name == "AGENTS.md"]
        assert len(agents_files) == 2
        # Root-level should be first
        assert agents_files[0].parent == tmp_path

    def test_sorted_results(self, tmp_path):
        agent_dir = tmp_path / ".testagent"
        agent_dir.mkdir()
        (agent_dir / "z.txt").touch()
        (agent_dir / "a.txt").touch()

        agent = ConcreteAgent()
        names = [f.name for f in agent._discover_files(tmp_path)]
        assert names == ["a.txt", "z.txt"]


# ===========================================================================
# Merge configurations (V2 interface)
# ===========================================================================
class TestMergeConfigurations:

    def test_merges_from_repos(self, tmp_path):
        org_repo = _make_repo(
            tmp_path, "org", {".testagent/config.yaml": "org: true"}
        )
        team_repo = _make_repo(
            tmp_path, "team", {".testagent/config.yaml": "team: true"}
        )

        repos = [
            {"name": "org", "repo": org_repo},
            {"name": "team", "repo": team_repo},
        ]

        base_dir = tmp_path / "target"
        base_dir.mkdir()

        agent = ConcreteAgent()
        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(repos, base_dir)

        output = base_dir / ".testagent" / "config.yaml"
        assert output.exists()

    def test_root_level_files_written_to_base(self, tmp_path):
        repo = _make_repo(
            tmp_path, "org",
            {"AGENTS.md": "# Agents from org"},
        )

        base_dir = tmp_path / "target"
        base_dir.mkdir()

        agent = ConcreteAgent()
        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(
                [{"name": "org", "repo": repo}], base_dir,
            )

        assert (base_dir / "AGENTS.md").exists()
        content = (base_dir / "AGENTS.md").read_text()
        assert "Agents from org" in content

    def test_preserves_directory_structure(self, tmp_path):
        repo = _make_repo(tmp_path, "org", {
            ".testagent/agents/JIRA.md": "# JIRA",
            ".testagent/commands/test.md": "# Test",
            ".testagent/root.yaml": "root: true",
        })

        base_dir = tmp_path / "target"
        base_dir.mkdir()

        agent = ConcreteAgent()
        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(
                [{"name": "org", "repo": repo}], base_dir,
            )

        assert (base_dir / ".testagent" / "agents" / "JIRA.md").exists()
        assert (base_dir / ".testagent" / "commands" / "test.md").exists()
        assert (base_dir / ".testagent" / "root.yaml").exists()

    def test_missing_repo_path_skipped(self, tmp_path):
        repo = Mock()
        repo.get_path.return_value = tmp_path / "nonexistent"

        base_dir = tmp_path / "target"
        base_dir.mkdir()

        agent = ConcreteAgent()
        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(
                [{"name": "bad", "repo": repo}], base_dir,
            )

    def test_empty_repo_skipped(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        repo = Mock()
        repo.get_path.return_value = empty

        base_dir = tmp_path / "target"
        base_dir.mkdir()

        agent = ConcreteAgent()
        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(
                [{"name": "empty", "repo": repo}], base_dir,
            )

    def test_uses_merger_registry(self, tmp_path):
        org_repo = _make_repo(
            tmp_path, "org", {".testagent/config.json": '{"org": true}'}
        )
        team_repo = _make_repo(
            tmp_path, "team", {".testagent/config.json": '{"team": true}'}
        )

        base_dir = tmp_path / "target"
        base_dir.mkdir()

        agent = ConcreteAgent()
        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(
                [
                    {"name": "org", "repo": org_repo},
                    {"name": "team", "repo": team_repo},
                ],
                base_dir,
            )

        import json

        out = base_dir / ".testagent" / "config.json"
        assert out.exists()
        data = json.loads(out.read_text())
        assert "org" in data
        assert "team" in data

    def test_applies_pre_merge_hooks(self, tmp_path):
        repo = _make_repo(
            tmp_path, "org", {".testagent/test.txt": "Content"}
        )

        base_dir = tmp_path / "target"
        base_dir.mkdir()

        agent = ConcreteAgent()
        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(
                [{"name": "org", "repo": repo}], base_dir,
            )

        content = (base_dir / ".testagent" / "test.txt").read_text()
        assert "# Pre-hook applied" in content

    def test_applies_post_merge_hooks(self, tmp_path):
        repo = _make_repo(
            tmp_path, "org", {".testagent/config.md": "# Content"}
        )

        base_dir = tmp_path / "target"
        base_dir.mkdir()

        agent = ConcreteAgent()
        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(
                [{"name": "org", "repo": repo}], base_dir,
            )

        content = (base_dir / ".testagent" / "config.md").read_text()
        assert "# Post-hook applied from 1 sources" in content

    def test_merger_settings_passed(self, tmp_path):
        org_repo = _make_repo(
            tmp_path, "org",
            {".testagent/config.json": '{"key": "v1"}'},
        )
        team_repo = _make_repo(
            tmp_path, "team",
            {".testagent/config.json": '{"key": "v2"}'},
        )

        base_dir = tmp_path / "target"
        base_dir.mkdir()

        agent = ConcreteAgent()
        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(
                [
                    {"name": "org", "repo": org_repo},
                    {"name": "team", "repo": team_repo},
                ],
                base_dir,
                merger_settings={"JsonMerger": {"indent": 2}},
            )

        out = base_dir / ".testagent" / "config.json"
        assert out.exists()


# ===========================================================================
# Update (V2 interface)
# ===========================================================================
class TestUpdate:

    def test_update_creates_dir_and_merges(self, tmp_path):
        repo = _make_repo(
            tmp_path, "org", {".testagent/config.yaml": "org: true"}
        )

        base_dir = tmp_path / "target"
        base_dir.mkdir()

        agent = ConcreteAgent()
        with patch("agent_manager.plugins.agents.agent.message"):
            agent.update(
                [{"name": "org", "repo": repo}], base_dir,
            )

        assert (base_dir / ".testagent").exists()
        assert (base_dir / ".testagent" / "config.yaml").exists()


# ===========================================================================
# Hook execution
# ===========================================================================
class TestRunHook:

    def test_matching_pre_hook(self, tmp_path):
        agent = ConcreteAgent()
        result = agent._run_hook(
            agent.pre_merge_hooks, ".testagent/test.txt",
            "content", "org", tmp_path / "test.txt",
        )
        assert "# Pre-hook applied" in result

    def test_matching_post_hook(self):
        agent = ConcreteAgent()
        result = agent._run_hook(
            agent.post_merge_hooks, "README.md",
            "content", None, None, ["org", "team"],
        )
        assert "# Post-hook applied from 2 sources" in result

    def test_no_match(self, tmp_path):
        agent = ConcreteAgent()
        result = agent._run_hook(
            agent.pre_merge_hooks, "no-match.xyz",
            "content", "org", tmp_path / "x",
        )
        assert result == "content"

    def test_handles_exception(self, tmp_path):
        class FaultyAgent(AbstractAgent):
            agent_subdirectory = ".faulty"

            def register_hooks(self):
                self.pre_merge_hooks["*.txt"] = self._bad

            def _bad(self, content, name, path):
                raise RuntimeError("boom")

        agent = FaultyAgent()
        with patch("agent_manager.plugins.agents.agent.message"):
            result = agent._run_hook(
                agent.pre_merge_hooks, "test.txt",
                "original", "org", tmp_path / "test.txt",
            )
        assert result == "original"


# ===========================================================================
# Edge cases
# ===========================================================================
class TestEdgeCases:

    def test_unicode_filenames(self, tmp_path):
        agent_dir = tmp_path / ".testagent"
        agent_dir.mkdir()
        (agent_dir / "配置.yaml").touch()

        agent = ConcreteAgent()
        files = agent._discover_files(tmp_path)
        assert len(files) == 1

    def test_unicode_content(self, tmp_path):
        repo = _make_repo(
            tmp_path, "org",
            {".testagent/config.txt": "你好世界 🌍"},
        )

        base_dir = tmp_path / "target"
        base_dir.mkdir()

        agent = ConcreteAgent()
        with patch("agent_manager.plugins.agents.agent.message"):
            agent.merge_configurations(
                [{"name": "org", "repo": repo}], base_dir,
            )

        content = (base_dir / ".testagent" / "config.txt").read_text()
        assert "你好世界" in content
