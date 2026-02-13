"""Test Agent for testing agent-manager functionality."""

import tempfile
from pathlib import Path

from agent_manager.plugins.agents import AbstractAgent


class TestAgent(AbstractAgent):
    """A test agent that writes merged configs to a temporary directory.

    This agent is used for testing the agent-manager functionality without
    affecting any real agent configurations. It creates a temporary directory
    and writes all merged configurations there.
    """

    def __init__(self, temp_dir: Path | None = None):
        """Initialize the test agent.

        Args:
            temp_dir: Optional temporary directory path. If not provided,
                     a new temporary directory will be created.
        """
        # Set agent directory before calling super().__init__()
        if temp_dir:
            self.agent_directory = temp_dir
        else:
            # Create a temporary directory
            self._temp_dir = tempfile.mkdtemp(prefix="agent_manager_test_")
            self.agent_directory = Path(self._temp_dir)

        # Call parent constructor to set up hooks and mergers
        super().__init__()

    # Set the repo directory name to ".testagent"
    _repo_directory_name: str = ".testagent"

    @property
    def scopes(self):
        """Define available scopes for the test agent.

        Returns:
            Dictionary mapping scope names to ScopeConfig objects
        """
        from agent_manager.plugins.agents import ScopeConfig

        return {"default": ScopeConfig(directory=self.agent_directory, description="Test agent directory")}

    def register_hooks(self):
        """Register any custom hooks for the test agent.

        Test agent doesn't need custom hooks, so this is a no-op.
        """
        pass

    def register_mergers(self):
        """Register any custom mergers for the test agent.

        Test agent uses default mergers, so this is a no-op.
        """
        pass

    def update(self, config: dict):
        """Update the test agent configuration.

        This writes all merged configurations to the temporary directory.

        Args:
            config: Configuration dictionary with hierarchy information
        """
        self._initialize()
        self.merge_configurations(config)

    def _initialize(self):
        """Initialize the test agent directory."""
        self.agent_directory.mkdir(parents=True, exist_ok=True)

    def get_output_directory(self) -> Path:
        """Get the output directory where merged configs are written.

        Returns:
            Path to the output directory
        """
        return self.agent_directory

    def cleanup(self):
        """Clean up the temporary directory.

        This should be called after tests are done to clean up resources.
        """
        import shutil

        if hasattr(self, "_temp_dir") and Path(self._temp_dir).exists():
            shutil.rmtree(self._temp_dir)


# Export the Agent class for auto-discovery
Agent = TestAgent
