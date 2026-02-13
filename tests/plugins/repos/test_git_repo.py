"""Tests for plugins/repos/git_repo.py - Git repository implementation."""

from unittest.mock import Mock, patch

import git
import pytest

from agent_manager.plugins.repos.git_repo import GitRepo


class TestGitRepoCanHandleUrl:
    """Test cases for GitRepo.can_handle_url()."""

    def test_handles_git_protocol(self):
        """Test that git:// URLs are handled."""
        assert GitRepo.can_handle_url("git://github.com/user/repo.git")

    def test_handles_git_at_ssh(self):
        """Test that git@ SSH URLs are handled."""
        assert GitRepo.can_handle_url("git@github.com:user/repo.git")

    def test_handles_ssh_protocol(self):
        """Test that ssh:// URLs are handled."""
        assert GitRepo.can_handle_url("ssh://git@github.com/user/repo.git")

    def test_handles_https_with_git_suffix(self):
        """Test that HTTPS URLs with .git are handled."""
        assert GitRepo.can_handle_url("https://github.com/user/repo.git")

    def test_handles_http_with_git_suffix(self):
        """Test that HTTP URLs with .git are handled."""
        assert GitRepo.can_handle_url("http://example.com/repo.git")

    def test_handles_github_urls(self):
        """Test that GitHub URLs are handled."""
        assert GitRepo.can_handle_url("https://github.com/user/repo")

    def test_handles_gitlab_urls(self):
        """Test that GitLab URLs are handled."""
        assert GitRepo.can_handle_url("https://gitlab.com/user/repo")

    def test_handles_bitbucket_urls(self):
        """Test that Bitbucket URLs are handled."""
        assert GitRepo.can_handle_url("https://bitbucket.org/user/repo")

    def test_rejects_file_urls(self):
        """Test that file:// URLs are not handled."""
        assert not GitRepo.can_handle_url("file:///tmp/repo")

    def test_rejects_plain_http_without_git(self):
        """Test that plain HTTP URLs without git indicators are not handled."""
        assert not GitRepo.can_handle_url("https://example.com/page")

    def test_rejects_non_url_strings(self):
        """Test that non-URL strings are not handled."""
        assert not GitRepo.can_handle_url("/local/path/to/repo")


class TestGitRepoValidateUrl:
    """Test cases for GitRepo.validate_url()."""

    @patch("agent_manager.plugins.repos.git_repo.git.cmd.Git")
    def test_validate_successful_ls_remote(self, mock_git_cmd):
        """Test that validation succeeds with successful ls-remote."""
        mock_git_instance = Mock()
        mock_git_cmd.return_value = mock_git_instance
        mock_git_instance.ls_remote.return_value = "refs/heads/main"

        result = GitRepo.validate_url("https://github.com/user/repo.git")

        assert result is True
        mock_git_instance.ls_remote.assert_called_once()

    @patch("agent_manager.plugins.repos.git_repo.git.cmd.Git")
    def test_validate_failed_ls_remote(self, mock_git_cmd):
        """Test that validation fails with failed ls-remote."""
        mock_git_instance = Mock()
        mock_git_cmd.return_value = mock_git_instance
        mock_git_instance.ls_remote.side_effect = git.exc.GitCommandError("ls-remote", 128)

        with patch("agent_manager.plugins.repos.git_repo.message"):
            result = GitRepo.validate_url("https://github.com/user/invalid.git")

        assert result is False

    @patch("agent_manager.plugins.repos.git_repo.git.cmd.Git")
    def test_validate_handles_generic_exception(self, mock_git_cmd):
        """Test that validation handles generic exceptions."""
        mock_git_instance = Mock()
        mock_git_cmd.return_value = mock_git_instance
        mock_git_instance.ls_remote.side_effect = Exception("Network error")

        with patch("agent_manager.plugins.repos.git_repo.message"):
            result = GitRepo.validate_url("https://github.com/user/repo.git")

        assert result is False


class TestGitRepoInitialization:
    """Test cases for GitRepo initialization."""

    def test_initialization_sets_attributes(self, tmp_path):
        """Test that initialization sets correct attributes."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)

        assert repo.name == "test"
        assert repo.url == "https://github.com/user/repo.git"
        assert repo.repos_dir == tmp_path

    def test_local_path_is_under_repos_dir(self, tmp_path):
        """Test that local_path is under repos_dir."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)

        assert repo.local_path == tmp_path / "test"

    def test_repo_type_is_git(self, tmp_path):
        """Test that REPO_TYPE is 'git'."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)

        assert repo.REPO_TYPE == "git"

    def test_initialization_does_not_clone(self, tmp_path):
        """Test that initialization doesn't clone the repository."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)

        assert not repo.local_path.exists()


class TestGitRepoNeedsUpdate:
    """Test cases for GitRepo.needs_update()."""

    def test_needs_update_when_not_cloned(self, tmp_path):
        """Test that needs_update returns True when repo doesn't exist."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)

        assert repo.needs_update() is True

    @patch("agent_manager.plugins.repos.git_repo.git.Repo")
    def test_needs_update_when_already_cloned(self, mock_repo_class, tmp_path):
        """Test that needs_update returns True even when repo exists."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)
        repo.local_path.mkdir(parents=True)

        # Mock git.Repo to return a valid repository
        mock_repo_instance = Mock()
        mock_repo_instance.remotes.origin.url = "https://github.com/user/repo.git"
        mock_repo_class.return_value = mock_repo_instance

        with patch("agent_manager.plugins.repos.git_repo.message"):
            result = repo.needs_update()

        # Always returns True to check for remote updates
        assert result is True

    @patch("agent_manager.plugins.repos.git_repo.git.Repo")
    def test_needs_update_warns_on_url_mismatch(self, mock_repo_class, tmp_path):
        """Test that needs_update warns when remote URL doesn't match."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)
        repo.local_path.mkdir(parents=True)

        # Mock git.Repo with different URL
        mock_repo_instance = Mock()
        mock_repo_instance.remotes.origin.url = "https://github.com/other/repo.git"
        mock_repo_class.return_value = mock_repo_instance

        with patch("agent_manager.plugins.repos.git_repo.message") as mock_message:
            repo.needs_update()

            # Should log a warning
            mock_message.assert_called()

    @patch("agent_manager.plugins.repos.git_repo.git.Repo")
    def test_needs_update_exits_on_invalid_repo(self, mock_repo_class, tmp_path):
        """Test that needs_update exits when directory is not a valid git repo."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)
        repo.local_path.mkdir(parents=True)

        # Mock git.Repo to raise InvalidGitRepositoryError
        mock_repo_class.side_effect = git.exc.InvalidGitRepositoryError

        with patch("agent_manager.plugins.repos.git_repo.message"), pytest.raises(SystemExit):
            repo.needs_update()


class TestGitRepoUpdate:
    """Test cases for GitRepo.update()."""

    @patch("agent_manager.plugins.repos.git_repo.git.Repo")
    def test_update_clones_when_not_exists(self, mock_repo_class, tmp_path):
        """Test that update clones the repository when it doesn't exist."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)

        mock_cloned_repo = Mock()
        mock_repo_class.clone_from.return_value = mock_cloned_repo

        with patch("agent_manager.plugins.repos.git_repo.message"):
            repo.update()

        mock_repo_class.clone_from.assert_called_once_with("https://github.com/user/repo.git", tmp_path / "test")

    @patch("agent_manager.plugins.repos.git_repo.git.Repo")
    def test_update_exits_on_clone_failure(self, mock_repo_class, tmp_path):
        """Test that update exits when cloning fails."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)

        mock_repo_class.clone_from.side_effect = git.exc.GitCommandError("clone", 128)

        with patch("agent_manager.plugins.repos.git_repo.message"), pytest.raises(SystemExit):
            repo.update()

    @patch("agent_manager.plugins.repos.git_repo.git.Repo")
    def test_update_pulls_when_exists(self, mock_repo_class, tmp_path):
        """Test that update pulls changes when repo exists."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)
        repo.local_path.mkdir(parents=True)

        # Mock existing repository
        mock_repo_instance = Mock()
        mock_repo_instance.active_branch.name = "main"
        mock_repo_instance.remotes.origin.fetch.return_value = None
        mock_repo_instance.remotes.origin.pull.return_value = None
        mock_repo_class.return_value = mock_repo_instance

        with patch("agent_manager.plugins.repos.git_repo.message"):
            repo.update()

        mock_repo_instance.remotes.origin.fetch.assert_called_once()
        mock_repo_instance.remotes.origin.pull.assert_called_once_with("main")

    @patch("agent_manager.plugins.repos.git_repo.git.Repo")
    def test_update_handles_different_branch(self, mock_repo_class, tmp_path):
        """Test that update handles non-main branches."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)
        repo.local_path.mkdir(parents=True)

        # Mock repository on 'develop' branch
        mock_repo_instance = Mock()
        mock_repo_instance.active_branch.name = "develop"
        mock_repo_instance.remotes.origin.fetch.return_value = None
        mock_repo_instance.remotes.origin.pull.return_value = None
        mock_repo_class.return_value = mock_repo_instance

        with patch("agent_manager.plugins.repos.git_repo.message"):
            repo.update()

        mock_repo_instance.remotes.origin.pull.assert_called_once_with("develop")

    @patch("agent_manager.plugins.repos.git_repo.git.Repo")
    def test_update_exits_on_pull_failure(self, mock_repo_class, tmp_path):
        """Test that update exits when pull fails."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)
        repo.local_path.mkdir(parents=True)

        # Mock repository that fails on pull
        mock_repo_instance = Mock()
        mock_repo_instance.active_branch.name = "main"
        mock_repo_instance.remotes.origin.fetch.return_value = None
        mock_repo_instance.remotes.origin.pull.side_effect = git.exc.GitCommandError("pull", 1)
        mock_repo_class.return_value = mock_repo_instance

        with patch("agent_manager.plugins.repos.git_repo.message"), pytest.raises(SystemExit):
            repo.update()

    @patch("agent_manager.plugins.repos.git_repo.git.Repo")
    def test_update_exits_on_invalid_repo(self, mock_repo_class, tmp_path):
        """Test that update exits when local path is not a valid git repo."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)
        repo.local_path.mkdir(parents=True)

        # Mock git.Repo to raise InvalidGitRepositoryError
        mock_repo_class.side_effect = git.exc.InvalidGitRepositoryError

        with patch("agent_manager.plugins.repos.git_repo.message"), pytest.raises(SystemExit):
            repo.update()


class TestGitRepoIntegration:
    """Integration tests for GitRepo."""

    def test_repo_lifecycle(self, tmp_path):
        """Test basic repository lifecycle."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)

        # Initially doesn't exist
        assert not repo.exists()
        assert repo.needs_update()

        # After creating directory (simulating clone)
        repo.local_path.mkdir()
        assert repo.exists()

    def test_get_path_returns_correct_path(self, tmp_path):
        """Test that get_path returns the correct local path."""
        repo = GitRepo("myrepo", "https://github.com/user/repo.git", tmp_path)

        path = repo.get_path()

        assert path == tmp_path / "myrepo"

    def test_get_display_url_returns_original_url(self, tmp_path):
        """Test that get_display_url returns the original URL."""
        url = "https://github.com/user/repo.git"
        repo = GitRepo("test", url, tmp_path)

        assert repo.get_display_url() == url

    def test_string_representation(self, tmp_path):
        """Test string representation of GitRepo."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)

        str_repr = str(repo)

        assert "test" in str_repr
        assert "git" in str_repr.lower()

    def test_repr_representation(self, tmp_path):
        """Test repr representation of GitRepo."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)

        repr_str = repr(repo)

        assert "GitRepo" in repr_str
        assert "test" in repr_str
        assert "github" in repr_str


class TestGitRepoEdgeCases:
    """Test cases for edge cases and special scenarios."""

    def test_handle_very_long_urls(self, tmp_path):
        """Test handling very long repository URLs."""
        long_url = "https://github.com/user/" + "a" * 200 + ".git"
        repo = GitRepo("test", long_url, tmp_path)

        assert repo.url == long_url

    def test_handle_urls_with_credentials(self):
        """Test handling URLs with embedded credentials."""
        url = "https://user:pass@github.com/user/repo.git"

        assert GitRepo.can_handle_url(url)

    def test_handle_urls_with_ports(self):
        """Test handling URLs with custom ports."""
        url = "ssh://git@github.com:2222/user/repo.git"

        assert GitRepo.can_handle_url(url)

    def test_handle_repos_with_special_characters(self, tmp_path):
        """Test handling repository names with special characters."""
        repo = GitRepo("test-repo_v2.0", "https://github.com/user/repo.git", tmp_path)

        assert repo.name == "test-repo_v2.0"
        assert repo.local_path.name == "test-repo_v2.0"

    @patch("agent_manager.plugins.repos.git_repo.git.Repo")
    def test_update_handles_generic_exception(self, mock_repo_class, tmp_path):
        """Test that update handles unexpected exceptions."""
        repo = GitRepo("test", "https://github.com/user/repo.git", tmp_path)

        mock_repo_class.clone_from.side_effect = Exception("Unexpected error")

        with patch("agent_manager.plugins.repos.git_repo.message"), pytest.raises(SystemExit):
            repo.update()
