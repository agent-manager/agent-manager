"""Abstract base class for repository implementations."""

from abc import ABC, abstractmethod
from pathlib import Path


class AbstractRepo(ABC):
    """Abstract base class for repository management."""

    # Subclasses must define this to identify their type
    REPO_TYPE: str = "unknown"

    def __init__(self, name: str, url: str, repos_dir: Path):
        """Initialize a repository.

        Args:
            name: Name of the hierarchy level
            url: Repository URL
            repos_dir: Base directory where repos are stored
        """
        self.name = name
        self.url = url
        self.repos_dir = repos_dir
        self.local_path: Path

    @classmethod
    @abstractmethod
    def can_handle_url(cls, url: str) -> bool:
        """Check if this repository type can handle the given URL.

        Args:
            url: The URL to check

        Returns:
            True if this repo type can handle the URL, False otherwise
        """
        pass

    @classmethod
    @abstractmethod
    def validate_url(cls, url: str) -> bool:
        """Validate that the URL is accessible and valid.

        Args:
            url: The URL to validate

        Returns:
            True if the URL is valid and accessible, False otherwise
        """
        pass

    @abstractmethod
    def update(self) -> None:
        """Update the repository.

        Should fetch/pull latest changes for remote repositories.
        May be a no-op for local repositories.
        """
        pass

    def get_path(self) -> Path:
        """Get the local path to the repository.

        Returns:
            Path to the local repository
        """
        return self.local_path

    def exists(self) -> bool:
        """Check if the repository exists locally.

        Returns:
            True if the repository exists, False otherwise
        """
        return self.local_path.exists()

    @abstractmethod
    def needs_update(self) -> bool:
        """Check if the repository needs to be updated.

        Returns:
            True if update() should be called, False otherwise
        """
        pass

    def get_display_url(self) -> str:
        """Get a human-friendly display version of the URL.

        Returns:
            String representation of the URL for display purposes
        """
        return self.url

    # ------------------------------------------------------------------
    # V2 safety methods
    # ------------------------------------------------------------------
    @classmethod
    def detect_directory(cls, path: Path) -> str | None:
        """Detect the VCS type of a target directory.

        Inspects the directory at *path* and returns a repo type string
        (e.g. ``"git"``, ``"file"``) or ``None`` if the directory does
        not exist or is not recognised.

        The base implementation checks for a ``.git`` directory (returns
        ``"git"``), and falls back to ``"file"`` for any existing
        directory.  Subclasses may override for more specific detection.

        Args:
            path: Directory to inspect

        Returns:
            Repo type string or None
        """
        if not path.exists() or not path.is_dir():
            return None
        if (path / ".git").exists():
            return "git"
        return "file"

    def safe_to_overwrite(self, file_path: Path) -> bool:
        """Determine whether *file_path* can be safely overwritten.

        "Safe" means the overwrite will not cause data loss that the
        user cannot recover.  Subclasses implement the actual logic:

        * **GitRepo**: returns ``True`` if the file is tracked by Git
          and has no uncommitted changes (i.e. it can be recovered via
          ``git checkout``).
        * **LocalRepo**: always returns ``False`` because there is no
          VCS to recover from.

        The default implementation conservatively returns ``False``.

        Args:
            file_path: Absolute path to the file to check

        Returns:
            True if safe to overwrite, False otherwise
        """
        return False

    # ------------------------------------------------------------------
    # String representations
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        """String representation of the repository."""
        repo_type = self.__class__.__name__.replace("Repo", "").lower()
        return (
            f"Repo(name='{self.name}', type={repo_type}, "
            f"path={self.local_path})"
        )

    def __repr__(self) -> str:
        """Developer representation of the repository."""
        return (
            f"{self.__class__.__name__}(name='{self.name}', "
            f"url='{self.url}', local_path={self.local_path})"
        )
