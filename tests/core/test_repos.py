"""Tests for core/repos.py - Repository discovery and factory functions."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from agent_manager.core.repos import (
    build_repo_type_map,
    create_repo,
    discover_repo_types,
    get_repo_type_map,
    update_repositories,
)
from agent_manager.plugins.repos import AbstractRepo, GitRepo, LocalRepo


class TestDiscoverRepoTypesImportError:
    """Test ImportError handling in discover_repo_types."""

    def test_discover_handles_import_error(self):
        """Test that discover_repo_types handles ImportError gracefully."""
        from agent_manager.core import repos

        # Mock iter_modules to include a module that will fail to import
        with patch("pkgutil.iter_modules") as mock_iter:
            # Create a mock module info that will cause ImportError
            mock_module_info = Mock()
            mock_module_info.name = "broken_repo"
            mock_iter.return_value = [mock_module_info]

            # Mock import_module to raise ImportError for our broken module
            with patch("importlib.import_module", side_effect=ImportError("Module not found")):
                # Should not raise, just skip the broken module
                result = repos.discover_repo_types()

                # Result should be empty since we only had the broken module
                assert result == []


class TestDiscoverRepoTypes:
    """Test cases for discover_repo_types function."""

    def test_discovers_repo_types(self):
        """Test that repository types are discovered."""
        repos = discover_repo_types()

        assert isinstance(repos, list)
        assert len(repos) > 0

    def test_discovers_git_repo(self):
        """Test that GitRepo is discovered."""
        repos = discover_repo_types()
        repo_names = [r.__name__ for r in repos]

        assert "GitRepo" in repo_names

    def test_discovers_local_repo(self):
        """Test that LocalRepo is discovered."""
        repos = discover_repo_types()
        repo_names = [r.__name__ for r in repos]

        assert "LocalRepo" in repo_names

    def test_does_not_discover_abstract_repo(self):
        """Test that AbstractRepo itself is not discovered."""
        repos = discover_repo_types()
        repo_names = [r.__name__ for r in repos]

        assert "AbstractRepo" not in repo_names

    def test_all_discovered_are_repo_subclasses(self):
        """Test that all discovered classes are AbstractRepo subclasses."""
        repos = discover_repo_types()

        for repo in repos:
            assert issubclass(repo, AbstractRepo)

    def test_discovered_repos_have_repo_type(self):
        """Test that discovered repos have REPO_TYPE attribute."""
        repos = discover_repo_types()

        for repo in repos:
            assert hasattr(repo, "REPO_TYPE")
            assert isinstance(repo.REPO_TYPE, str)

    def test_returns_unique_repo_classes(self):
        """Test that no duplicate repo classes are returned."""
        repos = discover_repo_types()
        repo_names = [r.__name__ for r in repos]

        assert len(repo_names) == len(set(repo_names))


class TestBuildRepoTypeMap:
    """Test cases for build_repo_type_map function."""

    def test_returns_dict(self):
        """Test that function returns a dictionary."""
        repo_map = build_repo_type_map()

        assert isinstance(repo_map, dict)

    def test_map_has_git_type(self):
        """Test that map includes 'git' type."""
        repo_map = build_repo_type_map()

        assert "git" in repo_map
        assert repo_map["git"] == GitRepo

    def test_map_has_local_type(self):
        """Test that map includes 'local' or 'file' type."""
        repo_map = build_repo_type_map()

        # LocalRepo might be registered as 'local' or 'file'
        assert "file" in repo_map or "local" in repo_map

    def test_map_values_are_repo_classes(self):
        """Test that all map values are AbstractRepo subclasses."""
        repo_map = build_repo_type_map()

        for repo_class in repo_map.values():
            assert issubclass(repo_class, AbstractRepo)

    def test_map_keys_match_repo_type_attributes(self):
        """Test that keys match the REPO_TYPE attributes."""
        repo_map = build_repo_type_map()

        for repo_type, repo_class in repo_map.items():
            assert repo_type == repo_class.REPO_TYPE


class TestGetRepoTypeMap:
    """Test cases for get_repo_type_map function."""

    def test_returns_dict(self):
        """Test that function returns a dictionary."""
        repo_map = get_repo_type_map()

        assert isinstance(repo_map, dict)

    def test_returns_same_instance_on_multiple_calls(self):
        """Test that function returns cached map (lazy initialization)."""
        # This tests the caching behavior
        repo_map1 = get_repo_type_map()
        repo_map2 = get_repo_type_map()

        # Should return the same dict instance due to caching
        assert repo_map1 is repo_map2

    def test_map_includes_expected_types(self):
        """Test that map includes expected repository types."""
        repo_map = get_repo_type_map()

        assert "git" in repo_map
        assert "file" in repo_map or "local" in repo_map


class TestCreateRepo:
    """Test cases for create_repo factory function."""

    def test_creates_git_repo(self, tmp_path):
        """Test creating a GitRepo instance."""
        repo = create_repo("test", "https://github.com/test/repo", tmp_path, "git")

        assert isinstance(repo, GitRepo)
        assert repo.name == "test"
        assert repo.url == "https://github.com/test/repo"

    def test_creates_local_repo(self, tmp_path):
        """Test creating a LocalRepo instance."""
        repo = create_repo("test", "file:///tmp/test", tmp_path, "file")

        assert isinstance(repo, LocalRepo)
        assert repo.name == "test"
        assert repo.url == "file:///tmp/test"

    def test_creates_repo_with_correct_repos_dir(self, tmp_path):
        """Test that repo is created with correct repos_dir."""
        repo = create_repo("test", "https://github.com/test/repo", tmp_path, "git")

        assert repo.repos_dir == tmp_path

    def test_raises_error_for_invalid_repo_type(self, tmp_path):
        """Test that invalid repo type raises SystemExit."""
        with pytest.raises(SystemExit):
            create_repo("test", "https://example.com", tmp_path, "invalid_type")

    def test_error_message_for_invalid_type(self, tmp_path, capsys):
        """Test that helpful error message is shown for invalid type."""
        with patch("agent_manager.core.repos.message") as mock_message:
            with pytest.raises(SystemExit):
                create_repo("test", "https://example.com", tmp_path, "invalid")

            # Should call output.error with helpful message
            assert mock_message.called


class TestUpdateRepositories:
    """Test cases for update_repositories function."""

    def test_updates_all_repositories(self):
        """Test that all repositories in config are updated."""
        # Create mock repositories
        repo1 = MagicMock()
        repo1.needs_update.return_value = True
        repo2 = MagicMock()
        repo2.needs_update.return_value = True

        config_data = {
            "hierarchy": [
                {"name": "org", "repo": repo1},
                {"name": "team", "repo": repo2},
            ]
        }

        with patch("agent_manager.core.repos.message"):
            update_repositories(config_data)

        repo1.update.assert_called_once()
        repo2.update.assert_called_once()

    def test_skips_update_if_not_needed(self):
        """Test that repositories are skipped if no update needed."""
        repo = MagicMock()
        repo.needs_update.return_value = False

        config_data = {"hierarchy": [{"name": "org", "repo": repo}]}

        with patch("agent_manager.core.repos.message"):
            update_repositories(config_data)

        repo.update.assert_not_called()

    def test_force_update_updates_all(self):
        """Test that force flag updates even when not needed."""
        repo = MagicMock()
        repo.needs_update.return_value = False

        config_data = {"hierarchy": [{"name": "org", "repo": repo}]}

        with patch("agent_manager.core.repos.message"):
            update_repositories(config_data, force=True)

        repo.update.assert_called_once()

    def test_handles_update_errors(self):
        """Test that update errors are handled gracefully."""
        repo = MagicMock()
        repo.needs_update.return_value = True
        repo.update.side_effect = Exception("Update failed")

        config_data = {"hierarchy": [{"name": "org", "repo": repo}]}

        with patch("agent_manager.core.repos.message"), pytest.raises(SystemExit):
            update_repositories(config_data)

    def test_continues_after_single_repo_error(self):
        """Test that other repos are updated even if one fails."""
        repo1 = MagicMock()
        repo1.needs_update.return_value = True
        repo1.update.side_effect = Exception("Repo 1 failed")

        repo2 = MagicMock()
        repo2.needs_update.return_value = True

        config_data = {
            "hierarchy": [
                {"name": "org", "repo": repo1},
                {"name": "team", "repo": repo2},
            ]
        }

        with patch("agent_manager.core.repos.message"), pytest.raises(SystemExit):
            update_repositories(config_data)

        # repo2 should still be attempted
        repo2.update.assert_called_once()

    def test_displays_progress(self):
        """Test that progress is displayed during updates."""
        repo1 = MagicMock()
        repo1.needs_update.return_value = True
        repo2 = MagicMock()
        repo2.needs_update.return_value = True

        config_data = {
            "hierarchy": [
                {"name": "org", "repo": repo1},
                {"name": "team", "repo": repo2},
            ]
        }

        with patch("agent_manager.core.repos.message") as mock_message:
            update_repositories(config_data)

            # Should show progress indicators
            assert mock_message.called

    def test_shows_success_message_on_completion(self):
        """Test that success message is shown when all updates complete."""
        repo = MagicMock()
        repo.needs_update.return_value = True

        config_data = {"hierarchy": [{"name": "org", "repo": repo}]}

        with patch("agent_manager.core.repos.message") as mock_message:
            update_repositories(config_data)

            # Should show success message
            assert mock_message.called


class TestReposIntegration:
    """Integration tests for repo discovery and creation."""

    def test_discovered_repos_can_be_created(self, tmp_path):
        """Test that all discovered repo types can be instantiated."""
        repo_map = get_repo_type_map()

        for repo_type, _repo_class in repo_map.items():
            # Create appropriate URL for each type
            url = "https://github.com/test/repo" if repo_type == "git" else "file:///tmp/test"

            repo = create_repo("test", url, tmp_path, repo_type)

            assert isinstance(repo, AbstractRepo)
            assert repo.name == "test"

    def test_repo_type_map_covers_all_discovered_types(self):
        """Test that repo type map includes all discovered types."""
        discovered = discover_repo_types()
        repo_map = get_repo_type_map()

        # All discovered repos should have their type in the map
        for repo_class in discovered:
            assert repo_class.REPO_TYPE in repo_map
            assert repo_map[repo_class.REPO_TYPE] == repo_class

    def test_factory_creates_correct_repo_type(self, tmp_path):
        """Test that factory creates the correct type based on repo_type."""
        repo_map = get_repo_type_map()

        for repo_type, expected_class in repo_map.items():
            # Create appropriate URL
            url = "https://github.com/test/repo" if repo_type == "git" else "file:///tmp/test"

            repo = create_repo("test", url, tmp_path, repo_type)

            assert type(repo) is expected_class
