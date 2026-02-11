"""Tests for plugins/repos/local_repo.py - Local directory repository implementation."""

from pathlib import Path
from unittest.mock import patch

import pytest

from agent_manager.plugins.repos.local_repo import LocalRepo


class TestLocalRepoCanHandleUrl:
    """Test cases for LocalRepo.can_handle_url()."""

    def test_handles_file_protocol(self):
        """Test that file:// URLs are handled."""
        assert LocalRepo.can_handle_url("file:///tmp/repo")

    def test_handles_file_protocol_with_tilde(self):
        """Test that file:// URLs with tilde are handled."""
        assert LocalRepo.can_handle_url("file://~/Documents/repo")

    def test_handles_file_protocol_with_relative_path(self):
        """Test that file:// URLs with relative paths are handled."""
        assert LocalRepo.can_handle_url("file://./local/repo")

    def test_handles_file_protocol_windows_paths(self):
        """Test that file:// URLs with Windows paths are handled."""
        assert LocalRepo.can_handle_url("file://C:/Users/name/repo")

    def test_rejects_http_urls(self):
        """Test that HTTP URLs are not handled."""
        assert not LocalRepo.can_handle_url("http://example.com/repo")

    def test_rejects_https_urls(self):
        """Test that HTTPS URLs are not handled."""
        assert not LocalRepo.can_handle_url("https://example.com/repo")

    def test_rejects_git_urls(self):
        """Test that git:// URLs are not handled."""
        assert not LocalRepo.can_handle_url("git://github.com/user/repo")

    def test_rejects_ssh_urls(self):
        """Test that SSH URLs are not handled."""
        assert not LocalRepo.can_handle_url("ssh://git@github.com/user/repo")

    def test_accepts_plain_paths(self):
        """Test that plain paths are now handled (auto-converted to file://)."""
        assert LocalRepo.can_handle_url("/tmp/repo")
        assert LocalRepo.can_handle_url("~/config")
        assert LocalRepo.can_handle_url("./relative")
        assert LocalRepo.can_handle_url("../parent")
        assert LocalRepo.can_handle_url(".")

    def test_rejects_bare_relative_paths(self):
        """Test that bare relative paths (no ./) are still rejected."""
        assert not LocalRepo.can_handle_url("relative/path")
        assert not LocalRepo.can_handle_url("subdir")


class TestLocalRepoValidateUrl:
    """Test cases for LocalRepo.validate_url()."""

    def test_validate_existing_directory(self, tmp_path):
        """Test validation succeeds for existing directories."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            result = LocalRepo.validate_url(f"file://{test_dir}")

        assert result is True

    def test_validate_non_existing_path(self):
        """Test validation fails for non-existing paths."""
        with patch("agent_manager.plugins.repos.local_repo.message"):
            result = LocalRepo.validate_url("file:///nonexistent/path")

        assert result is False

    def test_validate_file_not_directory(self, tmp_path):
        """Test validation fails when path is a file, not a directory."""
        test_file = tmp_path / "test.txt"
        test_file.touch()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            result = LocalRepo.validate_url(f"file://{test_file}")

        assert result is False

    def test_validate_with_tilde_expansion(self, tmp_path):
        """Test validation with tilde expansion."""
        with patch("agent_manager.plugins.repos.local_repo.resolve_file_path") as mock_resolve:
            mock_resolve.return_value = tmp_path
            tmp_path.mkdir(exist_ok=True)

            with patch("agent_manager.plugins.repos.local_repo.message"):
                result = LocalRepo.validate_url("file://~/test")

            assert mock_resolve.called

    def test_validate_handles_exception(self):
        """Test validation handles exceptions gracefully."""
        with patch("agent_manager.plugins.repos.local_repo.resolve_file_path") as mock_resolve:
            mock_resolve.side_effect = Exception("Invalid path")

            with patch("agent_manager.plugins.repos.local_repo.message"):
                result = LocalRepo.validate_url("file://invalid")

        assert result is False


class TestLocalRepoInitialization:
    """Test cases for LocalRepo initialization."""

    def test_initialization_sets_attributes(self, tmp_path):
        """Test that initialization sets correct attributes."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        assert repo.name == "test"
        assert repo.url == f"file://{test_dir}"
        assert repo.repos_dir == tmp_path

    def test_local_path_is_resolved_path(self, tmp_path):
        """Test that local_path is the resolved file path, not under repos_dir."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        # LocalRepo uses the file path directly, not repos_dir/name
        assert repo.local_path == test_dir

    def test_repo_type_is_file(self, tmp_path):
        """Test that REPO_TYPE is 'file'."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        assert repo.REPO_TYPE == "file"

    def test_initialization_with_tilde(self, tmp_path):
        """Test initialization with tilde expansion."""
        with patch("agent_manager.plugins.repos.local_repo.resolve_file_path") as mock_resolve:
            mock_resolve.return_value = tmp_path

            with patch("agent_manager.plugins.repos.local_repo.message"):
                repo = LocalRepo("test", "file://~/test", tmp_path)

            assert repo.local_path == tmp_path
            mock_resolve.assert_called_once_with("file://~/test")


class TestLocalRepoNeedsUpdate:
    """Test cases for LocalRepo.needs_update()."""

    def test_needs_update_always_false(self, tmp_path):
        """Test that needs_update always returns False for local repos."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        assert repo.needs_update() is False

    def test_needs_update_false_even_if_not_exists(self, tmp_path):
        """Test that needs_update returns False even if directory doesn't exist."""
        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", "file:///nonexistent", tmp_path)

        # Local repos never need updates
        assert repo.needs_update() is False


class TestLocalRepoUpdate:
    """Test cases for LocalRepo.update()."""

    def test_update_is_noop(self, tmp_path):
        """Test that update is a no-op for local repos."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message") as mock_message:
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)
            repo.update()

            # Should log a debug message
            mock_message.assert_called()

    def test_update_does_not_modify_directory(self, tmp_path):
        """Test that update doesn't modify the directory."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        test_file = test_dir / "file.txt"
        test_file.write_text("content")

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)
            repo.update()

        # File should still exist with same content
        assert test_file.exists()
        assert test_file.read_text() == "content"


class TestLocalRepoGetDisplayUrl:
    """Test cases for LocalRepo.get_display_url()."""

    def test_get_display_url_returns_resolved_path(self, tmp_path):
        """Test that get_display_url returns the resolved absolute path."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        display_url = repo.get_display_url()

        assert display_url == str(test_dir)
        assert not display_url.startswith("file://")

    def test_get_display_url_with_tilde(self, tmp_path):
        """Test that get_display_url shows resolved path even with tilde."""
        with patch("agent_manager.plugins.repos.local_repo.resolve_file_path") as mock_resolve:
            mock_resolve.return_value = tmp_path

            with patch("agent_manager.plugins.repos.local_repo.message"):
                repo = LocalRepo("test", "file://~/test", tmp_path)

            display_url = repo.get_display_url()

            # Should show resolved path, not the tilde version
            assert display_url == str(tmp_path)


class TestLocalRepoIntegration:
    """Integration tests for LocalRepo."""

    def test_repo_lifecycle(self, tmp_path):
        """Test basic repository lifecycle."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        # Exists immediately
        assert repo.exists()

        # Never needs updates
        assert not repo.needs_update()

        # Update is a no-op
        repo.update()

        # Still exists
        assert repo.exists()

    def test_get_path_returns_correct_path(self, tmp_path):
        """Test that get_path returns the correct local path."""
        test_dir = tmp_path / "myrepo"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("myrepo", f"file://{test_dir}", tmp_path)

        path = repo.get_path()

        assert path == test_dir

    def test_string_representation(self, tmp_path):
        """Test string representation of LocalRepo."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        str_repr = str(repo)

        assert "test" in str_repr
        assert "local" in str_repr.lower()

    def test_repr_representation(self, tmp_path):
        """Test repr representation of LocalRepo."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        repr_str = repr(repo)

        assert "LocalRepo" in repr_str
        assert "test" in repr_str
        assert str(test_dir) in repr_str


class TestLocalRepoEdgeCases:
    """Test cases for edge cases and special scenarios."""

    def test_handle_paths_with_spaces(self, tmp_path):
        """Test handling paths with spaces."""
        test_dir = tmp_path / "path with spaces"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        assert repo.local_path == test_dir
        assert repo.exists()

    def test_handle_paths_with_unicode(self, tmp_path):
        """Test handling paths with Unicode characters."""
        test_dir = tmp_path / "测试目录"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        assert repo.local_path == test_dir
        assert repo.exists()

    def test_handle_nested_paths(self, tmp_path):
        """Test handling deeply nested paths."""
        test_dir = tmp_path / "level1" / "level2" / "level3" / "repo"
        test_dir.mkdir(parents=True)

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        assert repo.local_path == test_dir
        assert repo.exists()

    def test_handle_symlinks(self, tmp_path):
        """Test handling symbolic links."""
        real_dir = tmp_path / "real"
        real_dir.mkdir()

        link_dir = tmp_path / "link"
        link_dir.symlink_to(real_dir)

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{link_dir}", tmp_path)

        # Should follow symlink
        assert repo.exists()

    def test_handle_relative_path(self, tmp_path):
        """Test handling relative paths."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.resolve_file_path") as mock_resolve:
            mock_resolve.return_value = test_dir

            with patch("agent_manager.plugins.repos.local_repo.message"):
                repo = LocalRepo("test", "file://./relative/path", tmp_path)

            # Should resolve to absolute path
            assert repo.local_path == test_dir

    def test_validate_with_special_characters(self, tmp_path):
        """Test validation with special characters in path."""
        test_dir = tmp_path / "special-chars_123"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            result = LocalRepo.validate_url(f"file://{test_dir}")

        assert result is True

    def test_exists_with_empty_directory(self, tmp_path):
        """Test exists() with an empty directory."""
        test_dir = tmp_path / "empty"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        # Should exist even if empty
        assert repo.exists()

    def test_exists_with_populated_directory(self, tmp_path):
        """Test exists() with a populated directory."""
        test_dir = tmp_path / "populated"
        test_dir.mkdir()
        (test_dir / "file1.txt").touch()
        (test_dir / "file2.txt").touch()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        assert repo.exists()


class TestLocalRepoVsGitRepo:
    """Comparison tests between LocalRepo and potential Git usage."""

    def test_local_repo_ignores_repos_dir(self, tmp_path):
        """Test that LocalRepo ignores repos_dir parameter."""
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()

        actual_dir = tmp_path / "actual"
        actual_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{actual_dir}", repos_dir)

        # local_path should be actual_dir, NOT repos_dir/test
        assert repo.local_path == actual_dir
        assert repo.local_path != repos_dir / "test"

    def test_local_repo_url_format_different_from_git(self):
        """Test that LocalRepo uses file:// protocol."""
        assert LocalRepo.can_handle_url("file:///tmp/repo")
        assert not LocalRepo.can_handle_url("https://github.com/user/repo")

    def test_local_repo_never_needs_network(self, tmp_path):
        """Test that LocalRepo never needs network access."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch("agent_manager.plugins.repos.local_repo.message"):
            repo = LocalRepo("test", f"file://{test_dir}", tmp_path)

        # Should work completely offline
        assert repo.exists()
        assert not repo.needs_update()
        repo.update()  # Should not throw
