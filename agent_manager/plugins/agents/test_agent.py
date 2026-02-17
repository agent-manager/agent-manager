"""Test Agent for testing agent-manager functionality (V2 interface)."""

import tempfile
from pathlib import Path
from typing import Any

from agent_manager.plugins.agents import AbstractAgent


class TestAgent(AbstractAgent):
    """A test agent that writes merged configs to a temporary directory."""

    agent_subdirectory = ".testagent"

    def __init__(self, temp_dir: Path | None = None):
        """Initialize the test agent.

        Args:
            temp_dir: Optional temporary directory path.
                     If not provided, a new temporary directory is created.
        """
        if temp_dir:
            self._base_dir = temp_dir
        else:
            self._temp_dir = tempfile.mkdtemp(prefix="agent_manager_test_")
            self._base_dir = Path(self._temp_dir)

        super().__init__()

    def register_hooks(self):
        """No custom hooks for test agent."""

    def update(
        self,
        repos: list[dict[str, Any]],
        base_directory: Path | None = None,
        merger_settings: dict[str, Any] | None = None,
    ) -> None:
        """Update the test agent configuration.

        Args:
            repos: Ordered list of repo entries
            base_directory: Target directory (defaults to internal temp dir)
            merger_settings: Optional merger settings
        """
        if base_directory is None:
            base_directory = self._base_dir
        output_dir = base_directory / self.agent_subdirectory
        self._initialize(output_dir)
        self.merge_configurations(repos, base_directory, merger_settings)

    def get_output_directory(self) -> Path:
        """Get the output directory where merged configs are written."""
        return self._base_dir / self.agent_subdirectory

    def get_base_directory(self) -> Path:
        """Get the base directory."""
        return self._base_dir

    def cleanup(self):
        """Clean up the temporary directory."""
        import shutil

        if hasattr(self, "_temp_dir") and Path(self._temp_dir).exists():
            shutil.rmtree(self._temp_dir)


# Export the Agent class for auto-discovery
Agent = TestAgent
