"""Tests for config/config.py - Configuration management."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from agent_manager.config.config import Config, ConfigError


class TestConfigError:
    """Test cases for ConfigError exception."""

    def test_single_error_message(self):
        """Test ConfigError with single error message."""
        error = ConfigError("Single error")

        assert len(error.errors) == 1
        assert str(error) == "Single error"

    def test_multiple_error_messages(self):
        """Test ConfigError with multiple error messages."""
        errors = ["Error 1", "Error 2", "Error 3"]
        error = ConfigError(errors)

        assert len(error.errors) == 3
        assert "Configuration has 3 errors" in str(error)
        assert "Error 1" in str(error)
        assert "Error 2" in str(error)

    def test_format_errors_with_list(self):
        """Test error formatting with list of errors."""
        error = ConfigError(["First", "Second"])

        formatted = str(error)
        assert "2 errors" in formatted
        assert "  - First" in formatted
        assert "  - Second" in formatted


class TestConfigInitialization:
    """Test cases for Config initialization."""

    def test_default_initialization(self):
        """Test Config initialization with default directory."""
        config = Config()

        assert config.config_directory == Path.home() / ".agent-manager"
        assert config.config_file == Path.home() / ".agent-manager" / "config.yaml"
        assert config.repos_directory == Path.home() / ".agent-manager" / "repos"

    def test_custom_config_directory(self, tmp_path):
        """Test Config initialization with custom directory."""
        custom_dir = tmp_path / "custom"
        config = Config(config_dir=custom_dir)

        assert config.config_directory == custom_dir
        assert config.config_file == custom_dir / "config.yaml"
        assert config.repos_directory == custom_dir / "repos"


class TestConfigEnsureDirectories:
    """Test cases for ensure_directories method."""

    def test_creates_config_directory(self, tmp_path):
        """Test that ensure_directories creates config directory."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)

        with patch("agent_manager.config.config.message"):
            config.ensure_directories()

        assert config_dir.exists()
        assert config_dir.is_dir()

    def test_creates_repos_directory(self, tmp_path):
        """Test that ensure_directories creates repos directory."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)

        with patch("agent_manager.config.config.message"):
            config.ensure_directories()

        repos_dir = config_dir / "repos"
        assert repos_dir.exists()
        assert repos_dir.is_dir()

    def test_idempotent_creation(self, tmp_path):
        """Test that ensure_directories is idempotent."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)

        with patch("agent_manager.config.config.message"):
            config.ensure_directories()
            config.ensure_directories()  # Call again

        # Should not raise error
        assert config_dir.exists()

    def test_handles_permission_error(self, tmp_path):
        """Test that ensure_directories handles permission errors."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)

        with (
            patch("pathlib.Path.mkdir", side_effect=PermissionError),
            patch("agent_manager.config.config.message"),
            pytest.raises(SystemExit),
        ):
            config.ensure_directories()

    def test_handles_os_error(self, tmp_path):
        """Test that ensure_directories handles OS errors."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)

        with (
            patch("pathlib.Path.mkdir", side_effect=OSError("Disk full")),
            patch("agent_manager.config.config.message"),
            pytest.raises(SystemExit),
        ):
            config.ensure_directories()

    def test_handles_generic_exception(self, tmp_path):
        """Test that ensure_directories handles unexpected exceptions."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)

        with (
            patch("pathlib.Path.mkdir", side_effect=RuntimeError("Unexpected error")),
            patch("agent_manager.config.config.message"),
            pytest.raises(SystemExit),
        ):
            config.ensure_directories()


class TestConfigValidateRepoUrl:
    """Test cases for validate_repo_url static method."""

    @patch("agent_manager.config.config.discover_repo_types")
    def test_validates_git_url(self, mock_discover):
        """Test validation of git URL."""
        from agent_manager.plugins.repos.git_repo import GitRepo

        mock_git_repo = Mock(spec=GitRepo)
        mock_git_repo.REPO_TYPE = "git"
        mock_git_repo.can_handle_url.return_value = True
        mock_git_repo.validate_url.return_value = True

        mock_discover.return_value = [mock_git_repo]

        with patch("agent_manager.config.config.message"):
            result = Config.validate_repo_url("https://github.com/user/repo")

        assert result is True

    @patch("agent_manager.config.config.discover_repo_types")
    def test_validates_file_url(self, mock_discover):
        """Test validation of file URL."""
        from agent_manager.plugins.repos.local_repo import LocalRepo

        mock_local_repo = Mock(spec=LocalRepo)
        mock_local_repo.REPO_TYPE = "file"
        mock_local_repo.can_handle_url.return_value = True
        mock_local_repo.validate_url.return_value = True

        mock_discover.return_value = [mock_local_repo]

        with patch("agent_manager.config.config.message"):
            result = Config.validate_repo_url("file:///tmp/repo")

        assert result is True

    @patch("agent_manager.config.config.Config.detect_repo_types")
    def test_rejects_invalid_url(self, mock_detect):
        """Test rejection of invalid URL."""
        mock_detect.return_value = []

        with patch("agent_manager.config.config.message"):
            result = Config.validate_repo_url("invalid://url")

        assert result is False


class TestConfigValidateRepoUrlEdgeCases:
    """Test edge cases for validate_repo_url."""

    def test_validate_url_with_missing_repo_class(self):
        """Test validate_url when repo class is not found after detection."""
        url = "https://github.com/test/repo"

        # Mock detect_repo_types to return a type, but discover_repo_types to return empty
        with (
            patch("agent_manager.config.config.Config.detect_repo_types", return_value=["nonexistent"]),
            patch("agent_manager.config.config.discover_repo_types", return_value=[]),
            patch("agent_manager.config.config.message"),
        ):
            result = Config.validate_repo_url(url)

            # Should return False and log internal error
            assert result is False


class TestConfigDetectRepoTypes:
    """Test cases for detect_repo_types static method."""

    @patch("agent_manager.config.config.discover_repo_types")
    def test_detects_single_type(self, mock_discover):
        """Test detection of single matching repo type."""
        mock_repo = Mock()
        mock_repo.REPO_TYPE = "git"
        mock_repo.can_handle_url.return_value = True

        mock_discover.return_value = [mock_repo]

        types = Config.detect_repo_types("https://github.com/user/repo")

        assert types == ["git"]

    @patch("agent_manager.config.config.discover_repo_types")
    def test_detects_multiple_types(self, mock_discover):
        """Test detection of multiple matching repo types."""
        mock_repo1 = Mock()
        mock_repo1.REPO_TYPE = "type1"
        mock_repo1.can_handle_url.return_value = True

        mock_repo2 = Mock()
        mock_repo2.REPO_TYPE = "type2"
        mock_repo2.can_handle_url.return_value = True

        mock_discover.return_value = [mock_repo1, mock_repo2]

        types = Config.detect_repo_types("https://example.com")

        assert "type1" in types
        assert "type2" in types

    @patch("agent_manager.config.config.discover_repo_types")
    def test_detects_no_types(self, mock_discover):
        """Test detection when no types match."""
        mock_repo = Mock()
        mock_repo.can_handle_url.return_value = False

        mock_discover.return_value = [mock_repo]

        types = Config.detect_repo_types("invalid://url")

        assert types == []


class TestConfigPromptForRepoType:
    """Test cases for prompt_for_repo_type static method."""

    @patch("builtins.input", return_value="1")
    def test_prompts_and_returns_selection(self, mock_input):
        """Test that prompt returns selected repo type."""
        url = "https://example.com"
        available = ["git", "file"]

        with patch("agent_manager.config.config.message"):
            selected = Config.prompt_for_repo_type(url, available)

        assert selected == "git"

    @patch("builtins.input", return_value="2")
    def test_prompts_returns_second_option(self, mock_input):
        """Test selection of second option."""
        available = ["type1", "type2", "type3"]

        with patch("agent_manager.config.config.message"):
            selected = Config.prompt_for_repo_type("url", available)

        assert selected == "type2"

    @patch("builtins.input", side_effect=["invalid", "0", "5", "2"])
    def test_prompts_retries_on_invalid_input(self, mock_input):
        """Test that prompt retries on invalid input."""
        available = ["type1", "type2"]

        with patch("agent_manager.config.config.message"):
            selected = Config.prompt_for_repo_type("url", available)

        # Should eventually select type2
        assert selected == "type2"
        assert mock_input.call_count == 4


class TestConfigValidate:
    """Test cases for validate static method."""

    def test_validates_valid_config(self):
        """Test validation of valid configuration."""
        config = {
            "hierarchy": [
                {"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"},
                {"name": "team", "url": "file:///tmp/team", "repo_type": "file"},
            ]
        }

        # Should not raise exception
        Config.validate(config)

    def test_rejects_missing_hierarchy(self):
        """Test rejection of config without hierarchy key."""
        config = {}

        with pytest.raises(ConfigError) as exc_info:
            Config.validate(config)

        assert "must contain 'hierarchy' key" in str(exc_info.value)

    def test_rejects_non_list_hierarchy(self):
        """Test rejection of hierarchy that's not a list."""
        config = {"hierarchy": "not a list"}

        with pytest.raises(ConfigError) as exc_info:
            Config.validate(config)

        assert "'hierarchy' must be a list" in str(exc_info.value)

    def test_rejects_empty_hierarchy(self):
        """Test rejection of empty hierarchy."""
        config = {"hierarchy": []}

        with pytest.raises(ConfigError) as exc_info:
            Config.validate(config)

        assert "'hierarchy' cannot be empty" in str(exc_info.value)

    def test_rejects_non_dict_entry(self):
        """Test rejection of non-dictionary hierarchy entry."""
        config = {"hierarchy": ["not a dict"]}

        with pytest.raises(ConfigError) as exc_info:
            Config.validate(config)

        assert "must be a dictionary" in str(exc_info.value)

    def test_rejects_missing_required_keys(self):
        """Test rejection of entry missing required keys."""
        config = {"hierarchy": [{"name": "org"}]}  # Missing url and repo_type

        with pytest.raises(ConfigError) as exc_info:
            Config.validate(config)

        error_str = str(exc_info.value)
        assert "missing required keys" in error_str
        assert "url" in error_str
        assert "repo_type" in error_str

    def test_rejects_non_string_name(self):
        """Test rejection of non-string name field."""
        config = {"hierarchy": [{"name": 123, "url": "url", "repo_type": "git"}]}

        with pytest.raises(ConfigError) as exc_info:
            Config.validate(config)

        assert "'name' must be a string" in str(exc_info.value)

    def test_rejects_empty_name(self):
        """Test rejection of empty name field."""
        config = {"hierarchy": [{"name": "", "url": "url", "repo_type": "git"}]}

        with pytest.raises(ConfigError) as exc_info:
            Config.validate(config)

        assert "'name' cannot be empty" in str(exc_info.value)

    def test_rejects_non_string_url(self):
        """Test rejection of non-string url field."""
        config = {"hierarchy": [{"name": "org", "url": 456, "repo_type": "git"}]}

        with pytest.raises(ConfigError) as exc_info:
            Config.validate(config)

        assert "'url' must be a string" in str(exc_info.value)

    def test_rejects_empty_url(self):
        """Test rejection of empty url field."""
        config = {"hierarchy": [{"name": "org", "url": "", "repo_type": "git"}]}

        with pytest.raises(ConfigError) as exc_info:
            Config.validate(config)

        assert "'url' cannot be empty" in str(exc_info.value)

    def test_rejects_non_string_repo_type(self):
        """Test rejection of non-string repo_type field."""
        config = {"hierarchy": [{"name": "org", "url": "url", "repo_type": 789}]}

        with pytest.raises(ConfigError) as exc_info:
            Config.validate(config)

        assert "'repo_type' must be a string" in str(exc_info.value)

    def test_rejects_empty_repo_type(self):
        """Test rejection of empty repo_type field."""
        config = {"hierarchy": [{"name": "org", "url": "url", "repo_type": ""}]}

        with pytest.raises(ConfigError) as exc_info:
            Config.validate(config)

        assert "'repo_type' cannot be empty" in str(exc_info.value)

    def test_collects_multiple_errors(self):
        """Test that validation collects multiple errors."""
        config = {
            "hierarchy": [
                {"name": "", "url": "", "repo_type": ""},  # 3 errors
                {"name": 123, "url": 456, "repo_type": 789},  # 3 errors
            ]
        }

        with pytest.raises(ConfigError) as exc_info:
            Config.validate(config)

        error_str = str(exc_info.value)
        assert "6 errors" in error_str or "cannot be empty" in error_str


class TestConfigWrite:
    """Test cases for write method."""

    def test_writes_valid_config(self, tmp_path):
        """Test writing valid configuration."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config_dir.mkdir()

        config_data = {"hierarchy": [{"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"}]}

        with patch("agent_manager.config.config.message"):
            config.write(config_data)

        assert config.config_file.exists()

        # Verify contents
        with open(config.config_file) as f:
            written = yaml.safe_load(f)

        assert written["hierarchy"][0]["name"] == "org"

    def test_write_rejects_invalid_config(self, tmp_path):
        """Test that write rejects invalid configuration."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config_dir.mkdir()

        invalid_config = {"hierarchy": []}  # Empty hierarchy

        with pytest.raises(SystemExit):
            config.write(invalid_config)

    def test_write_handles_os_error(self, tmp_path):
        """Test that write handles file system errors."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        # Don't create directory to cause error

        config_data = {"hierarchy": [{"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"}]}

        with pytest.raises(SystemExit):
            config.write(config_data)

    def test_write_handles_generic_exception(self, tmp_path):
        """Test that write handles unexpected exceptions."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config_dir.mkdir()

        config_data = {"hierarchy": [{"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"}]}

        # Simulate unexpected exception during YAML dump
        with patch("yaml.dump", side_effect=RuntimeError("Unexpected error")), pytest.raises(SystemExit):
            config.write(config_data)


class TestConfigRead:
    """Test cases for read method."""

    def test_reads_valid_config(self, tmp_path):
        """Test reading valid configuration file."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        config_file = config_dir / "config.yaml"
        config_data = {"hierarchy": [{"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"}]}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = Config(config_dir=config_dir)

        with (
            patch("agent_manager.config.config.message"),
            patch("agent_manager.config.config.create_repo") as mock_create,
        ):
            mock_create.return_value = Mock()
            loaded = config.read()

        assert loaded["hierarchy"][0]["name"] == "org"
        assert "repo" in loaded["hierarchy"][0]

    def test_read_handles_missing_file(self, tmp_path):
        """Test that read handles missing configuration file."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)

        with patch("agent_manager.config.config.message"), pytest.raises(SystemExit):
            config.read()

    def test_read_handles_empty_file(self, tmp_path):
        """Test that read handles empty configuration file."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        config_file = config_dir / "config.yaml"
        config_file.touch()  # Create empty file

        config = Config(config_dir=config_dir)

        with patch("agent_manager.config.config.message"), pytest.raises(SystemExit):
            config.read()

    def test_read_handles_invalid_config(self, tmp_path):
        """Test that read handles invalid configuration."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        config_file = config_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump({"hierarchy": []}, f)  # Invalid (empty)

        config = Config(config_dir=config_dir)

        with patch("agent_manager.config.config.message"), pytest.raises(SystemExit):
            config.read()


class TestConfigExists:
    """Test cases for exists method."""

    def test_exists_returns_true_when_file_exists(self, tmp_path):
        """Test that exists returns True when config file exists."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        config_file = config_dir / "config.yaml"
        config_file.touch()

        config = Config(config_dir=config_dir)

        assert config.exists() is True

    def test_exists_returns_false_when_file_missing(self, tmp_path):
        """Test that exists returns False when config file doesn't exist."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)

        assert config.exists() is False


class TestConfigInitialize:
    """Test cases for initialize method."""

    def test_initialize_creates_config(self, tmp_path):
        """Test that initialize creates configuration."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)

        # Ensure directories exist
        config.ensure_directories()

        with (
            patch("agent_manager.config.config.message"),
            patch("builtins.input", side_effect=['["org"]', "https://github.com/org/repo"]),
            patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
            patch("agent_manager.config.config.Config.detect_repo_types", return_value=["git"]),
        ):
            config.initialize()

        assert config_dir.exists()
        assert config.config_file.exists()

    def test_initialize_skips_if_exists(self, tmp_path):
        """Test that initialize skips if config already exists."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        config_file = config_dir / "config.yaml"
        config_file.touch()

        config = Config(config_dir=config_dir)

        with patch("agent_manager.config.config.message"):
            config.initialize(skip_if_already_created=True)

        # Should not prompt for input

    def test_initialize_cancelled_on_overwrite_no(self, tmp_path):
        """Test that initialize can be cancelled when overwriting."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config.ensure_directories()
        config.config_file.touch()  # Create existing file

        with (
            patch("agent_manager.config.config.message"),
            patch("builtins.input", return_value="no"),  # Say no to overwrite
        ):
            config.initialize(skip_if_already_created=False)

        # File should still exist but not be modified (just touched, so empty)
        assert config.config_file.exists()
        assert config.config_file.stat().st_size == 0

    def test_initialize_continues_on_overwrite_yes(self, tmp_path):
        """Test that initialize continues when user confirms overwrite."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config.ensure_directories()
        config.config_file.touch()  # Create existing file

        with (
            patch("agent_manager.config.config.message"),
            patch("builtins.input", side_effect=["yes", '["org"]', "https://github.com/org/repo"]),
            patch("agent_manager.config.config.Config.detect_repo_types", return_value=["git"]),
            patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
        ):
            config.initialize(skip_if_already_created=False)

        # Config file should be updated with content
        assert config.config_file.exists()
        assert config.config_file.stat().st_size > 0

    def test_initialize_hierarchy_not_a_list_retry(self, tmp_path):
        """Test that initialize retries when hierarchy is not a list."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config.ensure_directories()

        with (
            patch("agent_manager.config.config.message"),
            patch(
                "builtins.input",
                side_effect=['{"key": "value"}', '["org"]', "https://github.com/org/repo"],
            ),
            patch("agent_manager.config.config.Config.detect_repo_types", return_value=["git"]),
            patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
        ):
            config.initialize()

        assert config.config_file.exists()

    def test_initialize_hierarchy_syntax_error_retry(self, tmp_path):
        """Test that initialize retries on syntax error in hierarchy."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config.ensure_directories()

        with (
            patch("agent_manager.config.config.message"),
            patch(
                "builtins.input",
                side_effect=["[invalid", '["org"]', "https://github.com/org/repo"],
            ),
            patch("agent_manager.config.config.Config.detect_repo_types", return_value=["git"]),
            patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
        ):
            config.initialize()

        assert config.config_file.exists()

    def test_initialize_empty_url_retry(self, tmp_path):
        """Test that initialize retries when URL is empty."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config.ensure_directories()

        with (
            patch("agent_manager.config.config.message"),
            patch(
                "builtins.input",
                side_effect=['["org"]', "", "https://github.com/org/repo"],
            ),
            patch("agent_manager.config.config.Config.detect_repo_types", return_value=["git"]),
            patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
        ):
            config.initialize()

        assert config.config_file.exists()

    def test_initialize_no_matching_repo_type_retry(self, tmp_path):
        """Test that initialize retries when no repo type matches URL."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config.ensure_directories()

        with (
            patch("agent_manager.config.config.message"),
            patch(
                "builtins.input",
                side_effect=['["org"]', "invalid://bad", "https://github.com/org/repo"],
            ),
            # First call returns empty, second returns git, then one more for validation
            patch(
                "agent_manager.config.config.Config.detect_repo_types",
                side_effect=[[], ["git"]],
            ),
            patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
        ):
            config.initialize()

        assert config.config_file.exists()

    def test_initialize_accepts_comma_separated_hierarchy(self, tmp_path):
        """Test that initialize accepts comma-separated hierarchy levels."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config.ensure_directories()

        with (
            patch("agent_manager.config.config.message"),
            patch(
                "builtins.input",
                side_effect=["org, team, personal", "url1", "url2", "url3"],
            ),
            patch("agent_manager.config.config.Config.detect_repo_types", return_value=["git"]),
            patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
        ):
            config.initialize()

        # Verify the hierarchy was parsed correctly
        data = config.read()
        assert len(data["hierarchy"]) == 3
        assert data["hierarchy"][0]["name"] == "org"
        assert data["hierarchy"][1]["name"] == "team"
        assert data["hierarchy"][2]["name"] == "personal"

    def test_initialize_strips_whitespace_from_hierarchy(self, tmp_path):
        """Test that initialize strips whitespace from comma-separated levels."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config.ensure_directories()

        with (
            patch("agent_manager.config.config.message"),
            patch(
                "builtins.input",
                side_effect=["  org  ,  team  ", "url1", "url2"],
            ),
            patch("agent_manager.config.config.Config.detect_repo_types", return_value=["git"]),
            patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
        ):
            config.initialize()

        data = config.read()
        assert data["hierarchy"][0]["name"] == "org"
        assert data["hierarchy"][1]["name"] == "team"

    def test_initialize_accepts_python_list_syntax(self, tmp_path):
        """Test that initialize still accepts Python list syntax for backward compatibility."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config.ensure_directories()

        with (
            patch("agent_manager.config.config.message"),
            patch("builtins.input", side_effect=['["org", "team"]', "url1", "url2"]),
            patch("agent_manager.config.config.Config.detect_repo_types", return_value=["git"]),
            patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
        ):
            config.initialize()

        data = config.read()
        assert len(data["hierarchy"]) == 2
        assert data["hierarchy"][0]["name"] == "org"
        assert data["hierarchy"][1]["name"] == "team"

    def test_initialize_rejects_empty_hierarchy_entries(self, tmp_path):
        """Test that initialize rejects empty hierarchy entries."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config.ensure_directories()

        with (
            patch("agent_manager.config.config.message"),
            patch(
                "builtins.input",
                side_effect=["org, , team", "org, team", "url1", "url2"],
            ),
            patch("agent_manager.config.config.Config.detect_repo_types", return_value=["git"]),
            patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
        ):
            config.initialize()

        # Should have retried and accepted the valid input
        data = config.read()
        assert len(data["hierarchy"]) == 2


class TestConfigNormalizeUrl:
    """Test cases for normalize_url static method."""

    def test_normalizes_relative_file_url(self, tmp_path):
        """Test that relative file:// URLs are resolved to absolute paths."""
        # Create a test directory
        test_dir = tmp_path / "test_repo"
        test_dir.mkdir()

        # Change to tmp_path directory
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Test with relative path
            url = "file://./test_repo"
            normalized = Config.normalize_url(url)

            # Should be absolute
            assert normalized.startswith("file://")
            assert str(test_dir) in normalized
            assert "./" not in normalized
        finally:
            os.chdir(original_cwd)

    def test_normalizes_relative_file_url_with_parent_dir(self, tmp_path):
        """Test that relative file:// URLs with parent directory are resolved."""
        # Create nested structure
        parent = tmp_path / "parent"
        parent.mkdir()
        child = parent / "child"
        child.mkdir()
        target = tmp_path / "target"
        target.mkdir()

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(child)

            # Test with parent directory reference
            url = "file://../../target"
            normalized = Config.normalize_url(url)

            # Should be absolute
            assert normalized.startswith("file://")
            assert str(target) in normalized
            assert ".." not in normalized
        finally:
            os.chdir(original_cwd)

    def test_normalizes_tilde_in_file_url(self):
        """Test that tilde (~) in file:// URLs is expanded."""
        url = "file://~/repos/org"
        normalized = Config.normalize_url(url)

        # Should expand ~
        assert "~" not in normalized
        assert normalized.startswith("file://")
        assert str(Path.home()) in normalized

    def test_absolute_file_url_remains_unchanged(self, tmp_path):
        """Test that absolute file:// URLs remain absolute."""
        test_dir = tmp_path / "test_repo"
        test_dir.mkdir()

        url = f"file://{test_dir}"
        normalized = Config.normalize_url(url)

        # Should still be absolute and unchanged (except for potential path normalization)
        assert normalized.startswith("file://")
        assert str(test_dir) in normalized

    def test_git_url_unchanged(self):
        """Test that git URLs are not modified."""
        url = "https://github.com/user/repo.git"
        normalized = Config.normalize_url(url)

        # Should be unchanged
        assert normalized == url

    def test_ssh_git_url_unchanged(self):
        """Test that SSH git URLs are not modified."""
        url = "git@github.com:user/repo.git"
        normalized = Config.normalize_url(url)

        # Should be unchanged
        assert normalized == url

    def test_other_protocols_unchanged(self):
        """Test that other protocol URLs are not modified."""
        url = "s3://bucket/path/to/repo"
        normalized = Config.normalize_url(url)

        # Should be unchanged
        assert normalized == url


class TestConfigFileUrlResolution:
    """Integration tests for file:// URL resolution in config operations."""

    def test_initialize_resolves_relative_file_urls(self, tmp_path):
        """Test that initialize resolves relative file:// URLs to absolute paths."""
        config_dir = tmp_path / "config"
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()

        config = Config(config_dir=config_dir)
        config.ensure_directories()

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            with (
                patch("agent_manager.config.config.message"),
                patch("builtins.input", side_effect=['["org"]', "file://./repos"]),
                patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
                patch(
                    "agent_manager.config.config.Config.detect_repo_types",
                    return_value=["file"],
                ),
            ):
                config.initialize()

            # Read back the config
            with open(config.config_file) as f:
                written_config = yaml.safe_load(f)

            # URL should be absolute
            url = written_config["hierarchy"][0]["url"]
            assert url.startswith("file://")
            assert "./" not in url
            assert str(repos_dir) in url
        finally:
            os.chdir(original_cwd)

    def test_add_level_resolves_relative_file_urls(self, tmp_path):
        """Test that add_level resolves relative file:// URLs to absolute paths."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config.ensure_directories()

        # Create initial config with git URL
        initial_config = {"hierarchy": [{"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"}]}
        with open(config.config_file, "w") as f:
            yaml.dump(initial_config, f)

        # Create a local repo directory
        local_repo = tmp_path / "local"
        local_repo.mkdir()

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            with (
                patch("agent_manager.config.config.message"),
                patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
                patch(
                    "agent_manager.config.config.Config.detect_repo_types",
                    return_value=["file"],
                ),
                patch("agent_manager.config.config.create_repo"),
            ):
                config.add_level("personal", "file://./local")

            # Read back the config
            with open(config.config_file) as f:
                written_config = yaml.safe_load(f)

            # New URL should be absolute
            personal_entry = [e for e in written_config["hierarchy"] if e["name"] == "personal"][0]
            url = personal_entry["url"]
            assert url.startswith("file://")
            assert "./" not in url
            assert str(local_repo) in url
        finally:
            os.chdir(original_cwd)

    def test_update_level_resolves_relative_file_urls(self, tmp_path):
        """Test that update_level resolves relative file:// URLs to absolute paths."""
        config_dir = tmp_path / "config"
        config = Config(config_dir=config_dir)
        config.ensure_directories()

        # Create initial config
        initial_config = {"hierarchy": [{"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"}]}
        with open(config.config_file, "w") as f:
            yaml.dump(initial_config, f)

        # Create a new local repo directory
        new_local = tmp_path / "new_local"
        new_local.mkdir()

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            with (
                patch("agent_manager.config.config.message"),
                patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
                patch(
                    "agent_manager.config.config.Config.detect_repo_types",
                    return_value=["file"],
                ),
                patch("agent_manager.config.config.create_repo"),
            ):
                config.update_level("org", new_url="file://./new_local")

            # Read back the config
            with open(config.config_file) as f:
                written_config = yaml.safe_load(f)

            # Updated URL should be absolute
            url = written_config["hierarchy"][0]["url"]
            assert url.startswith("file://")
            assert "./" not in url
            assert str(new_local) in url
        finally:
            os.chdir(original_cwd)


class TestConfigEdgeCases:
    """Test cases for edge cases and special scenarios."""

    def test_config_with_unicode_paths(self, tmp_path):
        """Test Config with Unicode characters in paths."""
        config_dir = tmp_path / "配置"
        config = Config(config_dir=config_dir)

        with patch("agent_manager.config.config.message"):
            config.ensure_directories()

        assert config_dir.exists()

    def test_validates_config_with_additional_fields(self):
        """Test that validation allows additional fields."""
        config = {
            "hierarchy": [
                {
                    "name": "org",
                    "url": "https://github.com/org/repo",
                    "repo_type": "git",
                    "extra_field": "extra_value",
                }
            ],
            "mergers": {"JsonMerger": {"indent": 2}},
        }

        # Should not raise exception
        Config.validate(config)
