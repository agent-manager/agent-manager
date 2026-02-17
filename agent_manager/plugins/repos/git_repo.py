"""Git repository implementation."""

import subprocess
import sys
from pathlib import Path

import git

from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.plugins.repos.abstract_repo import AbstractRepo


class GitRepo(AbstractRepo):
    """Manages a git repository."""

    REPO_TYPE = "git"

    @classmethod
    def can_handle_url(cls, url: str) -> bool:
        """Check if this is a git repository URL.

        Args:
            url: The URL to check

        Returns:
            True if this looks like a git URL
        """
        # Check for common git URL patterns
        git_patterns = [
            url.startswith("git@"),
            url.startswith("git://"),
            url.startswith("ssh://"),
            url.startswith("http://") and ".git" in url,
            url.startswith("https://") and ".git" in url,
            # Also check for common git hosting services
            "github.com" in url,
            "gitlab.com" in url,
            "bitbucket.org" in url,
        ]
        return any(git_patterns)

    @classmethod
    def validate_url(cls, url: str) -> bool:
        """Validate that the git URL is accessible.

        Args:
            url: The git URL to validate

        Returns:
            True if the repository is accessible, False otherwise
        """
        try:
            # Use ls-remote to check if the repository is accessible
            git.cmd.Git().ls_remote(url)
            message(f"Git URL validated: {url}", MessageType.DEBUG, VerbosityLevel.DEBUG)
            return True
        except git.exc.GitCommandError as e:
            message(f"Cannot access git repository: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            return False
        except Exception as e:
            message(f"Invalid git URL: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            return False

    def __init__(self, name: str, url: str, repos_dir: Path):
        """Initialize a git repository.

        Args:
            name: Name of the hierarchy level
            url: Git repository URL
            repos_dir: Base directory where repos are stored

        Note: Does not clone or validate the repository.
        Call needs_update() and update() to sync the repository.
        """
        super().__init__(name, url, repos_dir)
        self.local_path = repos_dir / name

    def needs_update(self) -> bool:
        """Check if the repository needs to be cloned or updated.

        Returns:
            True if the repository needs to be cloned or pulled
        """
        # If it doesn't exist locally, it needs to be cloned
        if not self.local_path.exists():
            message(f"Repository '{self.name}' needs cloning", MessageType.DEBUG, VerbosityLevel.DEBUG)
            return True

        # Check if it's a valid git repository
        try:
            repo = git.Repo(self.local_path)

            # Verify remote URL matches
            if repo.remotes.origin.url != self.url:
                message(
                    f"Repository '{self.name}' remote URL mismatch. "
                    f"Expected: {self.url}, "
                    f"Got: {repo.remotes.origin.url}",
                    MessageType.WARNING,
                    VerbosityLevel.ALWAYS,
                )

            # Check if there are remote updates available
            # (Note: This requires a fetch, so we'll just return True
            # and let update() decide if pull is needed)
            message(f"Repository '{self.name}' may have updates", MessageType.DEBUG, VerbosityLevel.DEBUG)
            return True

        except (git.exc.InvalidGitRepositoryError, git.exc.GitCommandError) as e:
            message(
                f"Directory exists but is not a valid git repository: {self.local_path}",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            message(f"Error: {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)

    def update(self) -> None:
        """Update the git repository.

        If the repository doesn't exist, clones it.
        If it exists, performs a fetch and pull to get the latest changes.
        """
        # If repository doesn't exist, clone it
        if not self.local_path.exists():
            message(f"Cloning '{self.name}' from {self.url}...", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)
            try:
                git.Repo.clone_from(self.url, self.local_path)
                message(f"Successfully cloned '{self.name}'", MessageType.SUCCESS, VerbosityLevel.ALWAYS)
            except git.exc.GitCommandError as e:
                message(f"Failed to clone repository '{self.name}': {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
                sys.exit(1)
            except Exception as e:
                message(
                    f"Unexpected error cloning repository '{self.name}': {e}", MessageType.ERROR, VerbosityLevel.ALWAYS
                )
                sys.exit(1)
            return

        # Repository exists, update it
        message(f"Updating '{self.name}'...", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)

        try:
            repo = git.Repo(self.local_path)

            # Fetch latest changes
            message(f"Fetching changes for '{self.name}'...", MessageType.DEBUG, VerbosityLevel.DEBUG)
            repo.remotes.origin.fetch()

            # Get current branch
            current_branch = repo.active_branch.name

            # Pull changes
            message(
                f"Pulling changes for '{self.name}' (branch: {current_branch})...",
                MessageType.DEBUG,
                VerbosityLevel.DEBUG,
            )
            repo.remotes.origin.pull(current_branch)

            message(f"Successfully updated '{self.name}'", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

        except git.exc.InvalidGitRepositoryError:
            message(
                f"'{self.name}' at {self.local_path} is not a valid git repository",
                MessageType.ERROR,
                VerbosityLevel.ALWAYS,
            )
            sys.exit(1)
        except git.exc.GitCommandError as e:
            message(f"Failed to update repository '{self.name}': {e}", MessageType.ERROR, VerbosityLevel.ALWAYS)
            sys.exit(1)
        except Exception as e:
            message(
                f"Unexpected error updating repository '{self.name}': {e}", MessageType.ERROR, VerbosityLevel.ALWAYS
            )
            sys.exit(1)

    def safe_to_overwrite(self, file_path: Path) -> bool:
        """Check if a file inside this git repository is safe to overwrite.

        A file is safe to overwrite if it is tracked by Git and has no
        uncommitted changes (staged or unstaged).  In that state the
        user can always recover the previous content via ``git checkout``.

        Args:
            file_path: Absolute path to the file to check

        Returns:
            True if tracked + clean, False otherwise
        """
        try:
            repo = git.Repo(self.local_path)
        except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError):
            return False

        try:
            rel = file_path.resolve().relative_to(
                Path(repo.working_dir).resolve()
            )
        except ValueError:
            return False

        rel_str = str(rel)

        # Check if file is tracked
        try:
            result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", rel_str],
                cwd=repo.working_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return False
        except OSError:
            return False

        # Check for uncommitted changes (staged or unstaged)
        if repo.is_dirty(path=rel_str):
            return False

        # Also check for staged changes
        staged = [
            d.a_path for d in repo.index.diff("HEAD")
        ] if repo.head.is_valid() else []
        return rel_str not in staged
