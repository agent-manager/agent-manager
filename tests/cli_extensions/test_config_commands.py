"""Tests for cli_extensions/config_commands.py - V2 Config CLI commands."""

import argparse
from unittest.mock import Mock, patch

import pytest
import yaml

from agent_manager.cli_extensions.config_commands import ConfigCommands
from agent_manager.config.config import Config


class TestConfigCommandsAddCliArguments:
    """Test that all V2 subcommands are registered."""

    def test_adds_config_parser(self):
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_subparsers.add_parser.return_value = mock_parser
        ConfigCommands.add_cli_arguments(mock_subparsers)
        assert mock_subparsers.add_parser.called

    def test_adds_expected_subcommands(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        ConfigCommands.add_cli_arguments(subparsers)

        # Commands that don't require positional args
        for cmd in ["show", "validate", "template", "where", "init", "edit"]:
            args = parser.parse_args(["config", cmd])
            assert args.config_command == cmd


class TestConfigCommandsProcessCliCommand:

    @patch("agent_manager.cli_extensions.config_commands.ConfigCommands.display")
    def test_show(self, mock_display):
        args = Mock(config_command="show")
        config = Mock(spec=Config)
        ConfigCommands.process_cli_command(args, config)
        mock_display.assert_called_once_with(config)

    @patch("agent_manager.cli_extensions.config_commands.ConfigCommands.validate_all")
    def test_validate(self, mock_validate):
        args = Mock(config_command="validate")
        config = Mock(spec=Config)
        ConfigCommands.process_cli_command(args, config)
        mock_validate.assert_called_once_with(config)

    @patch("agent_manager.cli_extensions.config_commands.ConfigCommands.template")
    def test_template(self, mock_template):
        args = Mock(config_command="template")
        config = Mock(spec=Config)
        ConfigCommands.process_cli_command(args, config)
        mock_template.assert_called_once()

    @patch("agent_manager.cli_extensions.config_commands.ConfigCommands.defaults")
    def test_defaults_show(self, mock_defaults):
        args = Mock(config_command="defaults", repos=None, agents=None)
        config = Mock(spec=Config)
        ConfigCommands.process_cli_command(args, config)
        mock_defaults.assert_called_once_with(config, None, None)

    @patch("agent_manager.cli_extensions.config_commands.ConfigCommands.defaults")
    def test_defaults_set(self, mock_defaults):
        args = Mock(config_command="defaults", repos=["a", "b"], agents=["cursor"])
        config = Mock(spec=Config)
        ConfigCommands.process_cli_command(args, config)
        mock_defaults.assert_called_once_with(config, ["a", "b"], ["cursor"])

    @patch("agent_manager.cli_extensions.config_commands.ConfigCommands.show_location")
    def test_where(self, mock_show):
        args = Mock(config_command="where")
        config = Mock(spec=Config)
        ConfigCommands.process_cli_command(args, config)
        mock_show.assert_called_once_with(config)

    def test_unknown_command(self):
        args = Mock(config_command="unknown")
        config = Mock(spec=Config)
        with patch("agent_manager.cli_extensions.config_commands.message"), pytest.raises(SystemExit):
            ConfigCommands.process_cli_command(args, config)

    def test_no_subcommand_shows_help(self):
        args = Mock(config_command=None)
        config = Mock(spec=Config)
        messages = []

        def capture(msg, *a, **kw):
            messages.append(msg)

        with patch("agent_manager.cli_extensions.config_commands.message", side_effect=capture):
            ConfigCommands.process_cli_command(args, config)

        assert any("Available" in str(m) for m in messages)


class TestConfigCommandsDisplay:

    def test_display_shows_repos_and_directories(self):
        config = Mock(spec=Config)
        config.exists.return_value = True
        config.read.return_value = {
            "repos": [
                {"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"},
            ],
            "default_hierarchy": ["org"],
            "default_agents": ["cursor"],
            "directories": {
                "HOME": {"type": "local", "agents": ["cursor"], "hierarchy": ["org"]},
            },
        }

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.display(config)

    def test_display_errors_when_no_config(self):
        config = Mock(spec=Config)
        config.exists.return_value = False

        with patch("agent_manager.cli_extensions.config_commands.message"), pytest.raises(SystemExit):
            ConfigCommands.display(config)

    def test_display_handles_none_directory(self):
        config = Mock(spec=Config)
        config.exists.return_value = True
        config.read.return_value = {
            "repos": [],
            "directories": {"HOME": None},
        }

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.display(config)

    def test_display_handles_no_directories(self):
        config = Mock(spec=Config)
        config.exists.return_value = True
        config.read.return_value = {"repos": []}

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.display(config)


class TestConfigCommandsValidateAll:

    def test_validates_all_repos(self):
        config = Mock(spec=Config)
        config.exists.return_value = True
        config.read.return_value = {
            "repos": [
                {"name": "org", "url": "https://github.com/org/repo", "repo_type": "git"},
                {"name": "team", "url": "file:///tmp/team", "repo_type": "file"},
            ],
        }
        config.validate_repo_url.return_value = True

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.validate_all(config)

        assert config.validate_repo_url.call_count == 2

    def test_exits_on_failure(self):
        config = Mock(spec=Config)
        config.exists.return_value = True
        config.read.return_value = {
            "repos": [{"name": "bad", "url": "bad", "repo_type": "x"}],
        }
        config.validate_repo_url.return_value = False

        with patch("agent_manager.cli_extensions.config_commands.message"), pytest.raises(SystemExit):
            ConfigCommands.validate_all(config)

    def test_errors_when_no_config(self):
        config = Mock(spec=Config)
        config.exists.return_value = False

        with patch("agent_manager.cli_extensions.config_commands.message"), pytest.raises(SystemExit):
            ConfigCommands.validate_all(config)


class TestConfigCommandsTemplate:

    def test_prints_template(self, capsys):
        ConfigCommands.template()
        out = capsys.readouterr().out
        assert "repos:" in out
        assert "directories:" in out


class TestConfigCommandsDefaults:

    def test_shows_defaults(self):
        config = Mock(spec=Config)
        config.get_defaults.return_value = {
            "default_hierarchy": ["org"],
            "default_agents": ["cursor"],
        }
        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.defaults(config)

    def test_sets_defaults(self):
        config = Mock(spec=Config)
        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.defaults(config, repos=["a", "b"], agents=["c"])
        config.set_defaults.assert_called_once_with(repos=["a", "b"], agents=["c"])


class TestConfigCommandsShowLocation:

    def test_shows_paths(self, tmp_path):
        config = Mock(spec=Config)
        config.config_directory = tmp_path
        config.config_file = tmp_path / "config.yaml"
        config.repos_directory = tmp_path / "repos"

        with patch("agent_manager.cli_extensions.config_commands.message"):
            ConfigCommands.show_location(config)
