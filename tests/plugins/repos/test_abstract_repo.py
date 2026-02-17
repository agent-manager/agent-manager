"""Tests for plugins/repos/abstract_repo.py - Base repository class."""

from pathlib import Path

import pytest

from agent_manager.plugins.repos.abstract_repo import AbstractRepo


class ConcreteRepo(AbstractRepo):
    """Concrete implementation for testing AbstractRepo."""

    REPO_TYPE = "test"

    @classmethod
    def can_handle_url(cls, url: str) -> bool:
        return url.startswith("test://")

    @classmethod
    def validate_url(cls, url: str) -> bool:
        return url.startswith("test://valid")

    def __init__(self, name: str, url: str, repos_dir: Path):
        super().__init__(name, url, repos_dir)
        self.local_path = repos_dir / name

    def update(self) -> None:
        """Concrete implementation for testing."""
        pass

    def needs_update(self) -> bool:
        """Concrete implementation for testing."""
        return not self.exists()


class TestAbstractRepoInitialization:
    """Test cases for AbstractRepo initialization."""

    def test_initialization(self, tmp_path):
        """Test basic repository initialization."""
        repo = ConcreteRepo("test", "test://valid/repo", tmp_path)

        assert repo.name == "test"
        assert repo.url == "test://valid/repo"
        assert repo.repos_dir == tmp_path

    def test_has_repo_type_attribute(self, tmp_path):
        """Test that REPO_TYPE attribute is set."""
        repo = ConcreteRepo("test", "test://valid/repo", tmp_path)

        assert hasattr(repo, "REPO_TYPE")
        assert repo.REPO_TYPE == "test"

    def test_local_path_is_path_object(self, tmp_path):
        """Test that local_path is a Path object."""
        repo = ConcreteRepo("test", "test://valid/repo", tmp_path)

        assert isinstance(repo.local_path, Path)


class TestAbstractRepoCanHandleUrl:
    """Test cases for can_handle_url class method."""

    def test_can_handle_returns_bool(self):
        """Test that can_handle_url returns a boolean."""
        result = ConcreteRepo.can_handle_url("test://valid/repo")

        assert isinstance(result, bool)

    def test_can_handle_matching_url(self):
        """Test that can_handle_url returns True for matching URLs."""
        result = ConcreteRepo.can_handle_url("test://valid/repo")

        assert result is True

    def test_can_handle_non_matching_url(self):
        """Test that can_handle_url returns False for non-matching URLs."""
        result = ConcreteRepo.can_handle_url("https://example.com")

        assert result is False


class TestAbstractRepoValidateUrl:
    """Test cases for validate_url class method."""

    def test_validate_returns_bool(self):
        """Test that validate_url returns a boolean."""
        result = ConcreteRepo.validate_url("test://valid/repo")

        assert isinstance(result, bool)

    def test_validate_valid_url(self):
        """Test that validate_url returns True for valid URLs."""
        result = ConcreteRepo.validate_url("test://valid/repo")

        assert result is True

    def test_validate_invalid_url(self):
        """Test that validate_url returns False for invalid URLs."""
        result = ConcreteRepo.validate_url("test://invalid/repo")

        assert result is False


class TestAbstractRepoGetPath:
    """Test cases for get_path method."""

    def test_get_path_returns_local_path(self, tmp_path):
        """Test that get_path returns the local_path."""
        repo = ConcreteRepo("test", "test://valid/repo", tmp_path)

        path = repo.get_path()

        assert path == repo.local_path
        assert isinstance(path, Path)

    def test_get_path_matches_repos_dir(self, tmp_path):
        """Test that get_path is under repos_dir."""
        repo = ConcreteRepo("test", "test://valid/repo", tmp_path)

        path = repo.get_path()

        assert path == tmp_path / "test"


class TestAbstractRepoExists:
    """Test cases for exists method."""

    def test_exists_returns_false_when_not_created(self, tmp_path):
        """Test that exists returns False when directory doesn't exist."""
        repo = ConcreteRepo("test", "test://valid/repo", tmp_path)

        assert repo.exists() is False

    def test_exists_returns_true_when_created(self, tmp_path):
        """Test that exists returns True when directory exists."""
        repo = ConcreteRepo("test", "test://valid/repo", tmp_path)
        repo.local_path.mkdir(parents=True)

        assert repo.exists() is True

    def test_exists_with_nested_directory(self, tmp_path):
        """Test exists with nested directory structure."""
        nested_dir = tmp_path / "nested" / "dir"
        repo = ConcreteRepo("test", "test://valid/repo", nested_dir)

        assert repo.exists() is False

        nested_dir.mkdir(parents=True)
        (nested_dir / "test").mkdir()

        assert repo.exists() is True


class TestAbstractRepoGetDisplayUrl:
    """Test cases for get_display_url method."""

    def test_get_display_url_returns_original_url(self, tmp_path):
        """Test that get_display_url returns the original URL by default."""
        url = "test://valid/repo"
        repo = ConcreteRepo("test", url, tmp_path)

        display_url = repo.get_display_url()

        assert display_url == url

    def test_get_display_url_returns_string(self, tmp_path):
        """Test that get_display_url returns a string."""
        repo = ConcreteRepo("test", "test://valid/repo", tmp_path)

        display_url = repo.get_display_url()

        assert isinstance(display_url, str)


class TestAbstractRepoStringRepresentations:
    """Test cases for string representations."""

    def test_str_representation(self, tmp_path):
        """Test __str__ representation."""
        repo = ConcreteRepo("test", "test://valid/repo", tmp_path)

        str_repr = str(repo)

        assert "test" in str_repr
        assert "Repo" in str_repr

    def test_repr_representation(self, tmp_path):
        """Test __repr__ representation."""
        repo = ConcreteRepo("test", "test://valid/repo", tmp_path)

        repr_str = repr(repo)

        assert "ConcreteRepo" in repr_str
        assert "test" in repr_str
        assert "test://valid/repo" in repr_str

    def test_str_includes_local_path(self, tmp_path):
        """Test that __str__ includes local path."""
        repo = ConcreteRepo("myrepo", "test://valid/repo", tmp_path)

        str_repr = str(repo)

        assert str(repo.local_path) in str_repr


class TestAbstractRepoAbstractMethods:
    """Test cases for abstract method requirements."""

    def test_cannot_instantiate_abstract_class(self, tmp_path):
        """Test that AbstractRepo cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AbstractRepo("test", "test://valid/repo", tmp_path)

    def test_must_implement_can_handle_url(self, tmp_path):
        """Test that subclasses must implement can_handle_url."""

        class IncompleteRepo(AbstractRepo):
            REPO_TYPE = "incomplete"

            @classmethod
            def validate_url(cls, url: str) -> bool:
                return True

            def update(self) -> None:
                pass

            def needs_update(self) -> bool:
                return False

        with pytest.raises(TypeError):
            IncompleteRepo("test", "test://valid/repo", tmp_path)

    def test_must_implement_validate_url(self, tmp_path):
        """Test that subclasses must implement validate_url."""

        class IncompleteRepo(AbstractRepo):
            REPO_TYPE = "incomplete"

            @classmethod
            def can_handle_url(cls, url: str) -> bool:
                return True

            def update(self) -> None:
                pass

            def needs_update(self) -> bool:
                return False

        with pytest.raises(TypeError):
            IncompleteRepo("test", "test://valid/repo", tmp_path)

    def test_must_implement_update(self, tmp_path):
        """Test that subclasses must implement update."""

        class IncompleteRepo(AbstractRepo):
            REPO_TYPE = "incomplete"

            @classmethod
            def can_handle_url(cls, url: str) -> bool:
                return True

            @classmethod
            def validate_url(cls, url: str) -> bool:
                return True

            def needs_update(self) -> bool:
                return False

        with pytest.raises(TypeError):
            IncompleteRepo("test", "test://valid/repo", tmp_path)

    def test_must_implement_needs_update(self, tmp_path):
        """Test that subclasses must implement needs_update."""

        class IncompleteRepo(AbstractRepo):
            REPO_TYPE = "incomplete"

            @classmethod
            def can_handle_url(cls, url: str) -> bool:
                return True

            @classmethod
            def validate_url(cls, url: str) -> bool:
                return True

            def update(self) -> None:
                pass

        with pytest.raises(TypeError):
            IncompleteRepo("test", "test://valid/repo", tmp_path)


class TestAbstractRepoEdgeCases:
    """Test cases for edge cases and special scenarios."""

    def test_initialization_with_special_characters_in_name(self, tmp_path):
        """Test initialization with special characters in name."""
        repo = ConcreteRepo("test-repo_v2", "test://valid/repo", tmp_path)

        assert repo.name == "test-repo_v2"

    def test_initialization_with_long_url(self, tmp_path):
        """Test initialization with very long URL."""
        long_url = "test://valid/" + "a" * 500
        repo = ConcreteRepo("test", long_url, tmp_path)

        assert repo.url == long_url

    def test_get_path_with_unicode_characters(self, tmp_path):
        """Test get_path with Unicode characters in name."""
        repo = ConcreteRepo("测试", "test://valid/repo", tmp_path)

        path = repo.get_path()

        assert "测试" in str(path)

    def test_exists_with_symlink(self, tmp_path):
        """Test exists method with symbolic link."""
        real_dir = tmp_path / "real"
        real_dir.mkdir()

        symlink_dir = tmp_path / "link"
        symlink_dir.symlink_to(real_dir)

        repo = ConcreteRepo("test", "test://valid/repo", symlink_dir)

        # Symlink should be followed
        assert repo.exists() is False

        (symlink_dir / "test").mkdir()
        assert repo.exists() is True


class TestDetectDirectory:
    """Test cases for detect_directory classmethod."""

    def test_nonexistent_directory(self, tmp_path):
        assert AbstractRepo.detect_directory(tmp_path / "nope") is None

    def test_file_not_directory(self, tmp_path):
        f = tmp_path / "file.txt"
        f.touch()
        assert AbstractRepo.detect_directory(f) is None

    def test_plain_directory_returns_file(self, tmp_path):
        d = tmp_path / "plain"
        d.mkdir()
        assert AbstractRepo.detect_directory(d) == "file"

    def test_git_directory_returns_git(self, tmp_path):
        d = tmp_path / "gitrepo"
        d.mkdir()
        (d / ".git").mkdir()
        assert AbstractRepo.detect_directory(d) == "git"


class TestSafeToOverwrite:
    """Test cases for safe_to_overwrite on base class."""

    def test_base_always_returns_false(self, tmp_path):
        repo = ConcreteRepo("test", "test://valid/repo", tmp_path)
        some_file = tmp_path / "any_file.txt"
        some_file.touch()
        assert repo.safe_to_overwrite(some_file) is False
