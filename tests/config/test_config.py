"""Tests for config/config.py - V2 Configuration management."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from agent_manager.config.config import Config, ConfigError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _minimal_config(**overrides):
    """Return a minimal valid V2 config dict, with optional overrides."""
    base = {
        "repos": [
            {"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"},
        ],
    }
    base.update(overrides)
    return base


def _write_config(config_obj: Config, data: dict) -> None:
    """Write raw YAML data to the config file without validation."""
    config_obj.config_directory.mkdir(parents=True, exist_ok=True)
    with open(config_obj.config_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


# ===========================================================================
# ConfigError
# ===========================================================================
class TestConfigError:
    """Test cases for ConfigError exception."""

    def test_single_error_message(self):
        error = ConfigError("Single error")
        assert len(error.errors) == 1
        assert str(error) == "Single error"

    def test_multiple_error_messages(self):
        errors = ["Error 1", "Error 2", "Error 3"]
        error = ConfigError(errors)
        assert len(error.errors) == 3
        assert "Configuration has 3 errors" in str(error)

    def test_format_errors_with_list(self):
        error = ConfigError(["First", "Second"])
        formatted = str(error)
        assert "2 errors" in formatted
        assert "  - First" in formatted
        assert "  - Second" in formatted


# ===========================================================================
# Config.__init__
# ===========================================================================
class TestConfigInitialization:

    def test_default_initialization(self):
        config = Config()
        assert config.config_directory == Path.home() / ".agent-manager"
        assert config.config_file == Path.home() / ".agent-manager" / "config.yaml"
        assert config.repos_directory == Path.home() / ".agent-manager" / "repos"

    def test_custom_config_directory(self, tmp_path):
        custom_dir = tmp_path / "custom"
        config = Config(config_dir=custom_dir)
        assert config.config_directory == custom_dir
        assert config.config_file == custom_dir / "config.yaml"


# ===========================================================================
# ensure_directories
# ===========================================================================
class TestConfigEnsureDirectories:

    def test_creates_config_and_repos_dirs(self, tmp_path):
        config = Config(config_dir=tmp_path / "cfg")
        with patch("agent_manager.config.config.message"):
            config.ensure_directories()
        assert config.config_directory.exists()
        assert config.repos_directory.exists()

    def test_idempotent(self, tmp_path):
        config = Config(config_dir=tmp_path / "cfg")
        with patch("agent_manager.config.config.message"):
            config.ensure_directories()
            config.ensure_directories()
        assert config.config_directory.exists()

    def test_handles_permission_error(self, tmp_path):
        config = Config(config_dir=tmp_path / "cfg")
        with (
            patch("pathlib.Path.mkdir", side_effect=PermissionError),
            patch("agent_manager.config.config.message"),
            pytest.raises(SystemExit),
        ):
            config.ensure_directories()

    def test_handles_os_error(self, tmp_path):
        config = Config(config_dir=tmp_path / "cfg")
        with (
            patch("pathlib.Path.mkdir", side_effect=OSError("Disk full")),
            patch("agent_manager.config.config.message"),
            pytest.raises(SystemExit),
        ):
            config.ensure_directories()

    def test_handles_generic_exception(self, tmp_path):
        config = Config(config_dir=tmp_path / "cfg")
        with (
            patch("pathlib.Path.mkdir", side_effect=RuntimeError("oops")),
            patch("agent_manager.config.config.message"),
            pytest.raises(SystemExit),
        ):
            config.ensure_directories()


# ===========================================================================
# validate – repos
# ===========================================================================
class TestValidateRepos:

    def test_valid_minimal_config(self):
        Config.validate(_minimal_config())

    def test_missing_repos_key(self):
        with pytest.raises(ConfigError, match="must contain 'repos' key"):
            Config.validate({})

    def test_repos_not_a_list(self):
        with pytest.raises(ConfigError, match="'repos' must be a list"):
            Config.validate({"repos": "bad"})

    def test_repo_entry_not_dict(self):
        with pytest.raises(ConfigError, match="must be a dictionary"):
            Config.validate({"repos": ["bad"]})

    def test_repo_missing_required_keys(self):
        with pytest.raises(ConfigError, match="missing required keys"):
            Config.validate({"repos": [{"name": "x"}]})

    def test_repo_name_not_string(self):
        with pytest.raises(ConfigError, match="'name' must be a string"):
            Config.validate({"repos": [{"name": 123, "url": "u", "repo_type": "git"}]})

    def test_repo_name_empty(self):
        with pytest.raises(ConfigError, match="'name' cannot be empty"):
            Config.validate({"repos": [{"name": "", "url": "u", "repo_type": "git"}]})

    def test_repo_duplicate_name(self):
        with pytest.raises(ConfigError, match="duplicate name"):
            Config.validate({
                "repos": [
                    {"name": "dup", "url": "u1", "repo_type": "git"},
                    {"name": "dup", "url": "u2", "repo_type": "git"},
                ]
            })

    def test_repo_url_not_string(self):
        with pytest.raises(ConfigError, match="'url' must be a string"):
            Config.validate({"repos": [{"name": "x", "url": 123, "repo_type": "git"}]})

    def test_repo_url_empty(self):
        with pytest.raises(ConfigError, match="'url' cannot be empty"):
            Config.validate({"repos": [{"name": "x", "url": "", "repo_type": "git"}]})

    def test_repo_type_not_string(self):
        with pytest.raises(ConfigError, match="'repo_type' must be a string"):
            Config.validate({"repos": [{"name": "x", "url": "u", "repo_type": 9}]})

    def test_repo_type_empty(self):
        with pytest.raises(ConfigError, match="'repo_type' cannot be empty"):
            Config.validate({"repos": [{"name": "x", "url": "u", "repo_type": ""}]})

    def test_collects_multiple_errors(self):
        with pytest.raises(ConfigError) as exc:
            Config.validate({
                "repos": [
                    {"name": "", "url": "", "repo_type": ""},
                    {"name": 1, "url": 2, "repo_type": 3},
                ]
            })
        assert len(exc.value.errors) >= 4


# ===========================================================================
# validate – default_hierarchy
# ===========================================================================
class TestValidateDefaultHierarchy:

    def test_valid_default_hierarchy(self):
        Config.validate(_minimal_config(default_hierarchy=["org"]))

    def test_default_hierarchy_not_list(self):
        with pytest.raises(ConfigError, match="'default_hierarchy' must be a list"):
            Config.validate(_minimal_config(default_hierarchy="bad"))

    def test_default_hierarchy_entry_not_string(self):
        with pytest.raises(ConfigError, match="default_hierarchy entry 0 must be a string"):
            Config.validate(_minimal_config(default_hierarchy=[123]))

    def test_default_hierarchy_references_unknown_repo(self):
        with pytest.raises(ConfigError, match="does not match any repo name"):
            Config.validate(_minimal_config(default_hierarchy=["nonexistent"]))


# ===========================================================================
# validate – default_agents
# ===========================================================================
class TestValidateDefaultAgents:

    def test_valid_default_agents(self):
        Config.validate(_minimal_config(default_agents=["cursor", "claude"]))

    def test_default_agents_not_list(self):
        with pytest.raises(ConfigError, match="'default_agents' must be a list"):
            Config.validate(_minimal_config(default_agents="bad"))

    def test_default_agents_entry_not_string(self):
        with pytest.raises(ConfigError, match="default_agents entry 0 must be a string"):
            Config.validate(_minimal_config(default_agents=[99]))

    def test_default_agents_entry_empty(self):
        with pytest.raises(ConfigError, match="default_agents entry 0 cannot be empty"):
            Config.validate(_minimal_config(default_agents=[""]))


# ===========================================================================
# validate – directories
# ===========================================================================
class TestValidateDirectories:

    def test_valid_directories(self):
        Config.validate(_minimal_config(
            default_hierarchy=["org"],
            directories={"HOME": {"type": "local", "agents": ["cursor"], "hierarchy": ["org"]}},
        ))

    def test_directories_not_dict(self):
        with pytest.raises(ConfigError, match="'directories' must be a dictionary"):
            Config.validate(_minimal_config(directories="bad"))

    def test_directory_config_not_dict(self):
        with pytest.raises(ConfigError, match="config must be a dictionary"):
            Config.validate(_minimal_config(directories={"HOME": "bad"}))

    def test_directory_none_value_accepted(self):
        """A directory with None (bare key in YAML) is valid."""
        Config.validate(_minimal_config(
            default_hierarchy=["org"],
            directories={"HOME": None},
        ))

    def test_directory_type_not_string(self):
        with pytest.raises(ConfigError, match="'type' must be a string"):
            Config.validate(_minimal_config(directories={"HOME": {"type": 123}}))

    def test_directory_type_empty(self):
        with pytest.raises(ConfigError, match="'type' cannot be empty"):
            Config.validate(_minimal_config(directories={"HOME": {"type": ""}}))

    def test_directory_agents_not_list(self):
        with pytest.raises(ConfigError, match="'agents' must be a list"):
            Config.validate(_minimal_config(directories={"HOME": {"agents": "bad"}}))

    def test_directory_agents_entry_not_string(self):
        with pytest.raises(ConfigError, match="agents entry 0 must be a string"):
            Config.validate(_minimal_config(directories={"HOME": {"agents": [42]}}))

    def test_directory_hierarchy_not_list(self):
        with pytest.raises(ConfigError, match="'hierarchy' must be a list"):
            Config.validate(_minimal_config(directories={"HOME": {"hierarchy": "bad"}}))

    def test_directory_hierarchy_entry_not_string(self):
        with pytest.raises(ConfigError, match="hierarchy entry 0 must be a string"):
            Config.validate(_minimal_config(directories={"HOME": {"hierarchy": [42]}}))

    def test_directory_hierarchy_references_unknown_repo(self):
        with pytest.raises(ConfigError, match="does not match any repo name"):
            Config.validate(_minimal_config(directories={"HOME": {"hierarchy": ["ghost"]}}))

    def test_warns_when_no_hierarchy_and_no_default(self):
        """Should warn when directory omits hierarchy and no default_hierarchy."""
        warnings = Config.validate(_minimal_config(directories={"HOME": {}}))
        assert any("no repos will be merged" in w for w in warnings)

    def test_no_warning_when_directory_has_hierarchy(self):
        warnings = Config.validate(_minimal_config(directories={"HOME": {"hierarchy": ["org"]}}))
        assert len(warnings) == 0

    def test_no_warning_when_default_hierarchy_set(self):
        warnings = Config.validate(_minimal_config(
            default_hierarchy=["org"],
            directories={"HOME": {}},
        ))
        assert len(warnings) == 0


# ===========================================================================
# validate – extra fields
# ===========================================================================
class TestValidateExtraFields:

    def test_allows_additional_top_level_keys(self):
        cfg = _minimal_config()
        cfg["mergers"] = {"JsonMerger": {"indent": 2}}
        Config.validate(cfg)

    def test_allows_extra_keys_in_repo_entry(self):
        cfg = _minimal_config()
        cfg["repos"][0]["extra"] = "val"
        Config.validate(cfg)


# ===========================================================================
# write / read round-trip
# ===========================================================================
class TestConfigWriteRead:

    def test_write_and_read_minimal(self, tmp_path):
        config = Config(config_dir=tmp_path / "cfg")
        config.config_directory.mkdir(parents=True)

        data = _minimal_config()
        with patch("agent_manager.config.config.message"):
            config.write(data)

        assert config.config_file.exists()

        with (
            patch("agent_manager.config.config.message"),
            patch("agent_manager.config.config.create_repo", return_value=Mock()),
        ):
            loaded = config.read()

        assert loaded["repos"][0]["name"] == "org"

    def test_write_full_config(self, tmp_path):
        config = Config(config_dir=tmp_path / "cfg")
        config.config_directory.mkdir(parents=True)

        data = _minimal_config(
            default_hierarchy=["org"],
            default_agents=["cursor"],
            directories={"HOME": {"type": "local", "agents": ["cursor"], "hierarchy": ["org"]}},
        )

        with patch("agent_manager.config.config.message"):
            config.write(data)

        with open(config.config_file) as f:
            raw = yaml.safe_load(f)

        assert raw["default_hierarchy"] == ["org"]
        assert raw["default_agents"] == ["cursor"]
        assert raw["directories"]["HOME"]["type"] == "local"

    def test_write_rejects_invalid_config(self, tmp_path):
        config = Config(config_dir=tmp_path / "cfg")
        config.config_directory.mkdir(parents=True)

        with pytest.raises(SystemExit):
            config.write({})  # Missing repos key entirely

    def test_write_handles_os_error(self, tmp_path):
        config = Config(config_dir=tmp_path / "nonexistent")
        with pytest.raises(SystemExit):
            config.write(_minimal_config())

    def test_read_handles_missing_file(self, tmp_path):
        config = Config(config_dir=tmp_path / "cfg")
        with patch("agent_manager.config.config.message"), pytest.raises(SystemExit):
            config.read()

    def test_read_handles_empty_file(self, tmp_path):
        config = Config(config_dir=tmp_path / "cfg")
        config.config_directory.mkdir(parents=True)
        config.config_file.touch()
        with patch("agent_manager.config.config.message"), pytest.raises(SystemExit):
            config.read()

    def test_read_handles_invalid_yaml(self, tmp_path):
        config = Config(config_dir=tmp_path / "cfg")
        config.config_directory.mkdir(parents=True)
        config.config_file.write_text("invalid: yaml: content: [")
        with patch("agent_manager.config.config.message"), pytest.raises(SystemExit):
            config.read()


# ===========================================================================
# exists
# ===========================================================================
class TestConfigExists:

    def test_returns_true_when_exists(self, tmp_path):
        config = Config(config_dir=tmp_path)
        (tmp_path / "config.yaml").touch()
        assert config.exists() is True

    def test_returns_false_when_missing(self, tmp_path):
        config = Config(config_dir=tmp_path / "nonexistent")
        assert config.exists() is False


# ===========================================================================
# get_repo_names / get_directory_paths
# ===========================================================================
class TestConfigGetters:

    def test_get_repo_names(self, tmp_path):
        config = Config(config_dir=tmp_path)
        _write_config(config, _minimal_config())
        assert config.get_repo_names() == ["org"]

    def test_get_repo_names_empty(self, tmp_path):
        config = Config(config_dir=tmp_path / "x")
        assert config.get_repo_names() == []

    def test_get_directory_paths(self, tmp_path):
        config = Config(config_dir=tmp_path)
        _write_config(config, _minimal_config(directories={"HOME": None, "/x": {}}))
        paths = config.get_directory_paths()
        assert "HOME" in paths
        assert "/x" in paths

    def test_get_directory_paths_empty(self, tmp_path):
        config = Config(config_dir=tmp_path / "x")
        assert config.get_directory_paths() == []


# ===========================================================================
# add_repo
# ===========================================================================
class TestAddRepo:

    def test_adds_repo(self, tmp_path):
        config = Config(config_dir=tmp_path)
        _write_config(config, _minimal_config())

        with (
            patch("agent_manager.config.config.message"),
            patch("agent_manager.config.config.create_repo", return_value=Mock()),
            patch("agent_manager.config.config.Config.detect_repo_types", return_value=["file"]),
            patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
        ):
            config.add_repo("personal", "file:///tmp/personal")

        with open(config.config_file) as f:
            raw = yaml.safe_load(f)
        names = [r["name"] for r in raw["repos"]]
        assert "personal" in names

    def test_rejects_duplicate_name(self, tmp_path):
        config = Config(config_dir=tmp_path)
        _write_config(config, _minimal_config())

        with (
            patch("agent_manager.config.config.message"),
            patch("agent_manager.config.config.create_repo", return_value=Mock()),
            patch("agent_manager.config.config.Config.detect_repo_types", return_value=["git"]),
            patch("agent_manager.config.config.Config.validate_repo_url", return_value=True),
            pytest.raises(SystemExit),
        ):
            config.add_repo("org", "https://other.com")

    def test_rejects_when_no_config(self, tmp_path):
        config = Config(config_dir=tmp_path / "x")
        with patch("agent_manager.config.config.message"), pytest.raises(SystemExit):
            config.add_repo("a", "u")


# ===========================================================================
# remove_repo
# ===========================================================================
class TestRemoveRepo:

    def test_removes_repo(self, tmp_path):
        config = Config(config_dir=tmp_path)
        data = _minimal_config()
        data["repos"].append({"name": "extra", "url": "u", "repo_type": "git"})
        _write_config(config, data)

        with (
            patch("agent_manager.config.config.message"),
            patch("agent_manager.config.config.create_repo", return_value=Mock()),
        ):
            config.remove_repo("extra")

        with open(config.config_file) as f:
            raw = yaml.safe_load(f)
        names = [r["name"] for r in raw["repos"]]
        assert "extra" not in names

    def test_refuses_if_referenced_without_force(self, tmp_path):
        config = Config(config_dir=tmp_path)
        _write_config(config, _minimal_config(default_hierarchy=["org"]))

        with (
            patch("agent_manager.config.config.message"),
            patch("agent_manager.config.config.create_repo", return_value=Mock()),
            pytest.raises(SystemExit),
        ):
            config.remove_repo("org", force=False)

    def test_cascades_with_force(self, tmp_path):
        config = Config(config_dir=tmp_path)
        _write_config(config, _minimal_config(
            default_hierarchy=["org"],
            directories={"HOME": {"hierarchy": ["org"]}},
        ))

        with (
            patch("agent_manager.config.config.message"),
            patch("agent_manager.config.config.create_repo", return_value=Mock()),
        ):
            config.remove_repo("org", force=True)

        with open(config.config_file) as f:
            raw = yaml.safe_load(f)
        assert raw["repos"] == []
        assert raw["default_hierarchy"] == []

    def test_not_found(self, tmp_path):
        config = Config(config_dir=tmp_path)
        _write_config(config, _minimal_config())
        with (
            patch("agent_manager.config.config.message"),
            patch("agent_manager.config.config.create_repo", return_value=Mock()),
            pytest.raises(SystemExit),
        ):
            config.remove_repo("ghost")


# ===========================================================================
# add_directory / remove_directory
# ===========================================================================
class TestDirectoryManagement:

    def test_add_directory(self, tmp_path):
        config = Config(config_dir=tmp_path)
        _write_config(config, _minimal_config(default_hierarchy=["org"]))

        with (
            patch("agent_manager.config.config.message"),
            patch("agent_manager.config.config.create_repo", return_value=Mock()),
        ):
            config.add_directory("HOME", dir_type="local", agents=["cursor"])

        with open(config.config_file) as f:
            raw = yaml.safe_load(f)
        assert "HOME" in raw["directories"]
        assert raw["directories"]["HOME"]["type"] == "local"

    def test_add_directory_duplicate(self, tmp_path):
        config = Config(config_dir=tmp_path)
        _write_config(config, _minimal_config(directories={"HOME": None}))
        with (
            patch("agent_manager.config.config.message"),
            patch("agent_manager.config.config.create_repo", return_value=Mock()),
            pytest.raises(SystemExit),
        ):
            config.add_directory("HOME")

    def test_remove_directory(self, tmp_path):
        config = Config(config_dir=tmp_path)
        _write_config(config, _minimal_config(
            default_hierarchy=["org"],
            directories={"HOME": None, "/x": None},
        ))

        with (
            patch("agent_manager.config.config.message"),
            patch("agent_manager.config.config.create_repo", return_value=Mock()),
        ):
            config.remove_directory("HOME")

        with open(config.config_file) as f:
            raw = yaml.safe_load(f)
        assert "HOME" not in raw["directories"]

    def test_remove_directory_not_found(self, tmp_path):
        config = Config(config_dir=tmp_path)
        _write_config(config, _minimal_config())
        with (
            patch("agent_manager.config.config.message"),
            patch("agent_manager.config.config.create_repo", return_value=Mock()),
            pytest.raises(SystemExit),
        ):
            config.remove_directory("ghost")


# ===========================================================================
# set_defaults / get_defaults
# ===========================================================================
class TestDefaults:

    def test_set_and_get_defaults(self, tmp_path):
        config = Config(config_dir=tmp_path)
        _write_config(config, _minimal_config())

        with (
            patch("agent_manager.config.config.message"),
            patch("agent_manager.config.config.create_repo", return_value=Mock()),
        ):
            config.set_defaults(repos=["org"], agents=["cursor"])

        defaults = config.get_defaults()
        assert defaults["default_hierarchy"] == ["org"]
        assert defaults["default_agents"] == ["cursor"]

    def test_get_defaults_no_file(self, tmp_path):
        config = Config(config_dir=tmp_path / "x")
        defaults = config.get_defaults()
        assert defaults == {"default_hierarchy": [], "default_agents": []}


# ===========================================================================
# generate_template
# ===========================================================================
class TestGenerateTemplate:

    def test_template_is_valid_yaml(self):
        template = Config.generate_template()
        parsed = yaml.safe_load(template)
        assert "repos" in parsed
        assert "default_hierarchy" in parsed
        assert "directories" in parsed


# ===========================================================================
# URL utilities (unchanged from V1)
# ===========================================================================
class TestNormalizeUrl:

    def test_git_url_unchanged(self):
        url = "https://github.com/user/repo.git"
        assert Config.normalize_url(url) == url

    def test_ssh_url_unchanged(self):
        url = "git@github.com:user/repo.git"
        assert Config.normalize_url(url) == url

    def test_tilde_expanded(self):
        url = "file://~/repos/org"
        normalized = Config.normalize_url(url)
        assert "~" not in normalized
        assert str(Path.home()) in normalized


class TestDetectRepoTypes:

    @patch("agent_manager.config.config.discover_repo_types")
    def test_single_match(self, mock_discover):
        mock_repo = Mock()
        mock_repo.REPO_TYPE = "git"
        mock_repo.can_handle_url.return_value = True
        mock_discover.return_value = [mock_repo]
        assert Config.detect_repo_types("https://github.com/x") == ["git"]

    @patch("agent_manager.config.config.discover_repo_types")
    def test_no_match(self, mock_discover):
        mock_repo = Mock()
        mock_repo.can_handle_url.return_value = False
        mock_discover.return_value = [mock_repo]
        assert Config.detect_repo_types("bad://x") == []


class TestPromptForRepoType:

    @patch("builtins.input", return_value="1")
    def test_returns_selection(self, _mock_input):
        with patch("agent_manager.config.config.message"):
            selected = Config.prompt_for_repo_type("url", ["git", "file"])
        assert selected == "git"

    @patch("builtins.input", side_effect=["bad", "0", "2"])
    def test_retries_on_bad_input(self, mock_input):
        with patch("agent_manager.config.config.message"):
            selected = Config.prompt_for_repo_type("url", ["a", "b"])
        assert selected == "b"
        assert mock_input.call_count == 3
