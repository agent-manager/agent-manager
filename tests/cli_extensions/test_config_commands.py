"""Tests for cli_extensions/config_commands.py - Config CLI commands."""

import sys
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
import yaml

from agent_manager.cli_extensions.config_commands import ConfigCommands
from agent_manager.config.config import Config


class TestConfigCommandsAddCliArguments:
    """Test cases for add_cli_arguments method."""

    def test_adds_config_parser(self):
        """Test that config parser is added."""
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_subparsers.add_parser.return_value = mock_parser

        ConfigCommands.add_cli_arguments(mock_subparsers)

        # Should add config parser
        assert mock_subparsers.add_parser.called

    def test_adds_all_subcommands(self):
        """Test that all config subcommands are added."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        ConfigCommands.add_cli_arguments(subparsers)

        # Parse each subcommand to verify they exist
        commands = ["init", "show", "add", "remove", "update", "move", "validate", "export", "import", "where"]

        for cmd in commands:
            if cmd in ["add", "remove", "update", "move", "import"]:
                # These require additional arguments
                continue
            args = parser.parse_args(["config", cmd])
            assert args.command == "config"
            assert args.config_command == cmd


class TestConfigCommandsProcessCliCommand:
    """Test cases for process_cli_command method."""

    def test_processes_init_command(self):
        """Test processing of init command."""
        args = Mock()
        args.config_command = "init"

        config = Mock(spec=Config)

        ConfigCommands.process_cli_command(args, config)

        config.initialize.assert_called_once_with(skip_if_already_created=False)

    @patch("agent_manager.cli_extensions.config_commands.ConfigCommands.display")
    def test_processes_show_command(self, mock_display):
        """Test processing of show command."""
        args = Mock()
        args.config_command = "show"
        args.resolve_paths = False

        config = Mock(spec=Config)

        ConfigCommands.process_cli_command(args, config)

        mock_display.assert_called_once_with(config, resolve_paths=False)

    @patch("agent_manager.cli_extensions.config_commands.ConfigCommands.display")
    def test_processes_show_command_with_resolve(self, mock_display):
        """Test processing of show command with resolve_paths."""
        args = Mock()
        args.config_command = "show"
        args.resolve_paths = True

        config = Mock(spec=Config)

        ConfigCommands.process_cli_command(args, config)

        mock_display.assert_called_once_with(config, resolve_paths=True)

    def test_processes_add_command(self):
        """Test processing of add command."""
        args = Mock()
        args.config_command = "add"
        args.name = "team"
        args.url = "https://github.com/team/repo"
        args.position = None

        config = Mock(spec=Config)

        ConfigCommands.process_cli_command(args, config)

        config.add_level.assert_called_once_with("team", "https://github.com/team/repo", None)

    def test_processes_remove_command(self):
        """Test processing of remove command."""
        args = Mock()
        args.config_command = "remove"
        args.name = "team"

        config = Mock(spec=Config)

        ConfigCommands.process_cli_command(args, config)

        config.remove_level.assert_called_once_with("team")

    def test_processes_update_command(self):
        """Test processing of update command."""
        args = Mock()
        args.config_command = "update"
        args.name = "team"
        args.url = "https://github.com/team/new-repo"
        args.rename = "new-team"

        config = Mock(spec=Config)

        ConfigCommands.process_cli_command(args, config)

        config.update_level.assert_called_once_with("team", "https://github.com/team/new-repo", "new-team")

    def test_processes_move_command_with_position(self):
        """Test processing of move command with position."""
        args = Mock()
        args.config_command = "move"
        args.name = "team"
        args.position = 2
        args.up = False
        args.down = False

        config = Mock(spec=Config)

        ConfigCommands.process_cli_command(args, config)

        config.move_level.assert_called_once_with("team", 2, None)

    def test_processes_move_command_with_up(self):
        """Test processing of move command with up direction."""
        args = Mock()
        args.config_command = "move"
        args.name = "team"
        args.position = None
        args.up = True
        args.down = False

        config = Mock(spec=Config)

        ConfigCommands.process_cli_command(args, config)

        config.move_level.assert_called_once_with("team", None, "up")

    def test_processes_move_command_with_down(self):
        """Test processing of move command with down direction."""
        args = Mock()
        args.config_command = "move"
        args.name = "team"
        args.position = None
        args.up = False
        args.down = True

        config = Mock(spec=Config)

        ConfigCommands.process_cli_command(args, config)

        config.move_level.assert_called_once_with("team", None, "down")

    @patch("agent_manager.cli_extensions.config_commands.ConfigCommands.validate_all")
    def test_processes_validate_command(self, mock_validate):
        """Test processing of validate command."""
        args = Mock()
        args.config_command = "validate"

        config = Mock(spec=Config)

        ConfigCommands.process_cli_command(args, config)

        mock_validate.assert_called_once_with(config)

    @patch("agent_manager.cli_extensions.config_commands.ConfigCommands.export_config")
    def test_processes_export_command(self, mock_export):
        """Test processing of export command."""
        args = Mock()
        args.config_command = "export"
        args.file = "output.yaml"

        config = Mock(spec=Config)

        ConfigCommands.process_cli_command(args, config)

        mock_export.assert_called_once_with(config, "output.yaml")

    @patch("agent_manager.cli_extensions.config_commands.ConfigCommands.import_config")
    def test_processes_import_command(self, mock_import):
        """Test processing of import command."""
        args = Mock()
        args.config_command = "import"
        args.file = "input.yaml"

        config = Mock(spec=Config)

        ConfigCommands.process_cli_command(args, config)

        mock_import.assert_called_once_with(config, "input.yaml")

    @patch("agent_manager.cli_extensions.config_commands.ConfigCommands.show_location")
    def test_processes_where_command(self, mock_show):
        """Test processing of where command."""
        args = Mock()
        args.config_command = "where"

        config = Mock(spec=Config)

        ConfigCommands.process_cli_command(args, config)

        mock_show.assert_called_once_with(config)

    def test_processes_unknown_command(self):
        """Test processing of unknown command."""
        args = Mock()
        args.config_command = "unknown"

        config = Mock(spec=Config)

        with patch("agent_manager.cli_extensions.config_commands.message"):
            with pytest.raises(SystemExit):
                ConfigCommands.process_cli_command(args, config)

    def test_shows_help_when_no_subcommand(self):
        """Test that no subcommand shows available commands instead of error."""
        args = Mock()
        args.config_command = None

        config = Mock(spec=Config)
        messages = []

        def capture_message(msg, *args, **kwargs):
            messages.append(msg)

        with patch("agent_manager.cli_extensions.config_commands.message", side_effect=capture_message):
            # Should return without error, not raise SystemExit
            ConfigCommands.process_cli_command(args, config)

        # Should have printed available subcommands
        assert any("Available" in str(m) or "subcommand" in str(m).lower() for m in messages)


class TestConfigCommandsDisplay:
    """Test cases for display method."""

    def test_display_shows_hierarchy(self, tmp_path):
        """Test that display shows hierarchy configuration."""
        config = Mock(spec=Config)
        config.exists.return_value = True
        config.read.return_value = {
            "hierarchy": [
                {"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"},
                {"name": "team", "url": "file:///tmp/team", "repo_type": "file"},
            ]
        }

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.display(config)

        config.exists.assert_called_once()
        config.read.assert_called_once()

    def test_display_errors_when_no_config(self):
        """Test that display errors when config doesn't exist."""
        config = Mock(spec=Config)
        config.exists.return_value = False

        with patch("agent_manager.cli_extensions.config_commands.message"):
            with pytest.raises(SystemExit):
                ConfigCommands.display(config)

    @patch("agent_manager.cli_extensions.config_commands.create_repo")
    def test_display_resolves_paths(self, mock_create, tmp_path):
        """Test that display resolves file paths when requested."""
        mock_repo = Mock()
        mock_repo.get_display_url.return_value = "/resolved/path"
        mock_create.return_value = mock_repo

        config = Mock(spec=Config)
        config.exists.return_value = True
        config.repos_directory = tmp_path
        config.read.return_value = {"hierarchy": [{"name": "team", "url": "file:///tmp/team", "repo_type": "file"}]}

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.display(config, resolve_paths=True)

        mock_create.assert_called_once()


class TestConfigCommandsValidateAll:
    """Test cases for validate_all method."""

    def test_validates_all_repositories(self, tmp_path):
        """Test validation of all repositories."""
        config = Mock(spec=Config)
        config.exists.return_value = True
        config.read.return_value = {
            "hierarchy": [
                {"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"},
                {"name": "team", "url": "file:///tmp/team", "repo_type": "file"},
            ]
        }
        config.validate_repo_url.return_value = True

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.validate_all(config)

        assert config.validate_repo_url.call_count == 2

    def test_validates_all_reports_failures(self):
        """Test that validate_all reports validation failures."""
        config = Mock(spec=Config)
        config.exists.return_value = True
        config.read.return_value = {
            "hierarchy": [
                {"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"},
                {"name": "bad", "url": "invalid://url", "repo_type": "unknown"},
            ]
        }
        config.validate_repo_url.side_effect = [True, False]

        with patch("agent_manager.cli_extensions.config_commands.message"):
            with pytest.raises(SystemExit):
                ConfigCommands.validate_all(config)

    def test_validates_all_errors_when_no_config(self):
        """Test that validate_all errors when config doesn't exist."""
        config = Mock(spec=Config)
        config.exists.return_value = False

        with patch("agent_manager.cli_extensions.config_commands.message"):
            with pytest.raises(SystemExit):
                ConfigCommands.validate_all(config)


class TestConfigCommandsExportConfig:
    """Test cases for export_config method."""

    def test_exports_to_file(self, tmp_path):
        """Test exporting configuration to file."""
        output_file = tmp_path / "export.yaml"

        config = Mock(spec=Config)
        config.exists.return_value = True
        config.read.return_value = {
            "hierarchy": [{"name": "org", "url": "https://github.com/org/repo", "repo_type": "git", "repo": Mock()}]
        }

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.export_config(config, str(output_file))

        assert output_file.exists()

        # Verify exported content
        with open(output_file) as f:
            exported = yaml.safe_load(f)

        assert "hierarchy" in exported
        assert exported["hierarchy"][0]["name"] == "org"
        assert "repo" not in exported["hierarchy"][0]  # Should be removed

    def test_exports_to_stdout(self, capsys):
        """Test exporting configuration to stdout."""
        config = Mock(spec=Config)
        config.exists.return_value = True
        config.read.return_value = {
            "hierarchy": [{"name": "org", "url": "https://github.com/org/repo", "repo_type": "git", "repo": Mock()}]
        }

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.export_config(config, None)

        captured = capsys.readouterr()
        assert "org" in captured.out
        assert "hierarchy" in captured.out

    def test_exports_with_mergers_section(self, tmp_path):
        """Test that export includes mergers section if present."""
        output_file = tmp_path / "export.yaml"

        config = Mock(spec=Config)
        config.exists.return_value = True
        config.read.return_value = {
            "hierarchy": [{"name": "org", "url": "url", "repo_type": "git", "repo": Mock()}],
            "mergers": {"JsonMerger": {"indent": 2}},
        }

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.export_config(config, str(output_file))

        with open(output_file) as f:
            exported = yaml.safe_load(f)

        assert "mergers" in exported
        assert exported["mergers"]["JsonMerger"]["indent"] == 2

    def test_export_errors_when_no_config(self):
        """Test that export errors when config doesn't exist."""
        config = Mock(spec=Config)
        config.exists.return_value = False

        with patch("agent_manager.cli_extensions.config_commands.message"):
            with pytest.raises(SystemExit):
                ConfigCommands.export_config(config, "output.yaml")


class TestConfigCommandsImportConfig:
    """Test cases for import_config method."""

    def test_imports_from_file(self, tmp_path):
        """Test importing configuration from file."""
        input_file = tmp_path / "import.yaml"
        import_data = {"hierarchy": [{"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"}]}

        with open(input_file, "w") as f:
            yaml.dump(import_data, f)

        config = Mock(spec=Config)
        config.exists.return_value = False
        config.config_file = tmp_path / "config.yaml"

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.import_config(config, str(input_file))

        config.write.assert_called_once()

    def test_import_prompts_before_overwrite(self, tmp_path):
        """Test that import prompts before overwriting existing config."""
        input_file = tmp_path / "import.yaml"
        import_data = {"hierarchy": [{"name": "org", "url": "url", "repo_type": "git"}]}

        with open(input_file, "w") as f:
            yaml.dump(import_data, f)

        config = Mock(spec=Config)
        config.exists.return_value = True
        config.config_file = tmp_path / "config.yaml"

        with patch("agent_manager.cli_extensions.config_commands.message"):
            with patch("builtins.input", return_value="no"):
                ConfigCommands.import_config(config, str(input_file))

        # Should not write if user says no
        config.write.assert_not_called()

    def test_import_handles_missing_file(self):
        """Test that import handles missing input file."""
        config = Mock(spec=Config)

        with patch("agent_manager.cli_extensions.config_commands.message"):
            with pytest.raises(SystemExit):
                ConfigCommands.import_config(config, "nonexistent.yaml")

    def test_import_handles_invalid_yaml(self, tmp_path):
        """Test that import handles invalid YAML."""
        input_file = tmp_path / "invalid.yaml"
        input_file.write_text("invalid: yaml: content:")

        config = Mock(spec=Config)

        with patch("agent_manager.cli_extensions.config_commands.message"):
            with pytest.raises(SystemExit):
                ConfigCommands.import_config(config, str(input_file))

    def test_import_validates_structure(self, tmp_path):
        """Test that import validates configuration structure."""
        input_file = tmp_path / "invalid.yaml"
        with open(input_file, "w") as f:
            yaml.dump({"not_hierarchy": []}, f)

        config = Mock(spec=Config)

        with patch("agent_manager.cli_extensions.config_commands.message"):
            with pytest.raises(SystemExit):
                ConfigCommands.import_config(config, str(input_file))


class TestConfigCommandsShowLocation:
    """Test cases for show_location method."""

    def test_shows_configuration_locations(self, tmp_path):
        """Test that show_location displays config file locations."""
        config = Mock(spec=Config)

        # Mock the path attributes and their exists() methods
        config.config_directory = Mock()
        config.config_directory.__str__ = Mock(return_value=str(tmp_path / "config"))
        config.config_directory.exists = Mock(return_value=False)

        config.config_file = Mock()
        config.config_file.__str__ = Mock(return_value=str(tmp_path / "config" / "config.yaml"))
        config.config_file.exists = Mock(return_value=False)

        config.repos_directory = Mock()
        config.repos_directory.__str__ = Mock(return_value=str(tmp_path / "config" / "repos"))
        config.repos_directory.exists = Mock(return_value=False)

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.show_location(config)

        # Should not raise any errors

    def test_shows_existence_status(self, tmp_path):
        """Test that show_location shows existence status."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.touch()

        config = Mock(spec=Config)
        config.config_directory = config_dir
        config.config_file = config_file
        config.repos_directory = config_dir / "repos"

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.show_location(config)


class TestConfigCommandsEdgeCases:
    """Test cases for edge cases and special scenarios."""

    def test_display_handles_unicode_names(self):
        """Test that display handles Unicode in hierarchy names."""
        config = Mock(spec=Config)
        config.exists.return_value = True
        config.read.return_value = {"hierarchy": [{"name": "组织", "url": "https://example.com", "repo_type": "git"}]}

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.display(config)

    def test_export_handles_write_error(self, tmp_path):
        """Test that export handles write errors."""
        output_file = tmp_path / "readonly"
        output_file.mkdir()  # Make it a directory to cause error

        config = Mock(spec=Config)
        config.exists.return_value = True
        config.read.return_value = {"hierarchy": [{"name": "org", "url": "url", "repo_type": "git", "repo": Mock()}]}

        with patch("agent_manager.cli_extensions.config_commands.message"):
            with pytest.raises(SystemExit):
                ConfigCommands.export_config(config, str(output_file))

    def test_import_accepts_yes_variations(self, tmp_path):
        """Test that import accepts various yes responses."""
        input_file = tmp_path / "import.yaml"
        import_data = {"hierarchy": [{"name": "org", "url": "url", "repo_type": "git"}]}

        with open(input_file, "w") as f:
            yaml.dump(import_data, f)

        config = Mock(spec=Config)
        config.exists.return_value = True
        config.config_file = tmp_path / "config.yaml"

        for yes_response in ["yes", "y", "YES", "Y"]:
            with patch("agent_manager.cli_extensions.config_commands.message"):
                with patch("builtins.input", return_value=yes_response):
                    ConfigCommands.import_config(config, str(input_file))

            config.write.assert_called()
            config.write.reset_mock()
