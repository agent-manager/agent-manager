"""Tests for cli_extensions/plugin_commands.py."""

from unittest.mock import Mock, patch

import pytest

from agent_manager.cli_extensions.plugin_commands import PluginCommands


class TestPluginCommandsAddCliArguments:

    def test_adds_plugins_parser(self):
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_sub = Mock()
        mock_parser.add_subparsers.return_value = mock_sub

        # Each category parser also needs add_subparsers
        cat_parser = Mock()
        cat_sub = Mock()
        cat_parser.add_subparsers.return_value = cat_sub
        mock_sub.add_parser.return_value = cat_parser

        mock_subparsers.add_parser.return_value = mock_parser

        PluginCommands.add_cli_arguments(mock_subparsers)

        calls = [c[0][0] for c in mock_subparsers.add_parser.call_args_list]
        assert "plugins" in calls

    def test_adds_category_parsers(self):
        mock_subparsers = Mock()
        mock_plugins_parser = Mock()
        mock_plugins_sub = Mock()
        mock_plugins_parser.add_subparsers.return_value = mock_plugins_sub

        # Category parsers
        mock_cat = Mock()
        mock_cat.add_subparsers.return_value = Mock()
        mock_plugins_sub.add_parser.return_value = mock_cat

        mock_subparsers.add_parser.return_value = mock_plugins_parser

        PluginCommands.add_cli_arguments(mock_subparsers)

        calls = [
            c[0][0]
            for c in mock_plugins_sub.add_parser.call_args_list
        ]
        assert "agents" in calls
        assert "repos" in calls
        assert "mergers" in calls


class TestPluginCommandsProcess:

    def test_no_category_shows_usage(self):
        pc = PluginCommands()
        args = Mock()
        args.plugins_category = None
        messages = []

        with patch(
            "agent_manager.cli_extensions.plugin_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            pc.process_cli_command(args)

        output = "\n".join(messages)
        assert "Usage: agent-manager plugins" in output

    def test_agents_category_dispatches(self):
        pc = PluginCommands()
        args = Mock()
        args.plugins_category = "agents"
        args.plugins_action = "list"

        with patch.object(
            PluginCommands, "_handle_agents",
        ) as mock_h:
            pc.process_cli_command(args)
            mock_h.assert_called_once_with("list", args)

    def test_repos_category_dispatches(self):
        pc = PluginCommands()
        args = Mock()
        args.plugins_category = "repos"
        args.plugins_action = "list"

        with patch.object(
            PluginCommands, "_handle_repos",
        ) as mock_h:
            pc.process_cli_command(args)
            mock_h.assert_called_once_with("list", args)

    def test_mergers_category_dispatches(self):
        pc = PluginCommands()
        args = Mock()
        args.plugins_category = "mergers"
        args.plugins_action = "list"

        with patch.object(
            PluginCommands, "_handle_mergers",
        ) as mock_h:
            pc.process_cli_command(args, config=Mock())
            mock_h.assert_called_once()


class TestPluginCommandsAgents:

    def test_no_action_shows_usage(self):
        messages = []

        with patch(
            "agent_manager.cli_extensions.plugin_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            PluginCommands._handle_agents(None, Mock())

        output = "\n".join(messages)
        assert "plugins agents" in output

    @patch("agent_manager.cli_extensions.plugin_commands.get_disabled_plugins")
    @patch("agent_manager.cli_extensions.plugin_commands.discover_agent_plugins")
    def test_list_agents(self, mock_disc, mock_disabled):
        mock_disc.return_value = {
            "claude": {"package_name": "am_agent_claude"},
        }
        mock_disabled.return_value = {"agents": []}
        messages = []

        with patch(
            "agent_manager.cli_extensions.plugin_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            PluginCommands._handle_agents("list", Mock())

        output = "\n".join(messages)
        assert "claude" in output

    @patch("agent_manager.cli_extensions.plugin_commands.set_plugin_enabled")
    def test_enable_agent(self, mock_enable):
        mock_enable.return_value = True
        args = Mock()
        args.name = "claude"

        PluginCommands._handle_agents("enable", args)

        mock_enable.assert_called_once_with(
            "agents", "claude", enabled=True,
        )


class TestPluginCommandsRepos:

    @patch("agent_manager.cli_extensions.plugin_commands.get_disabled_plugins")
    @patch("agent_manager.cli_extensions.plugin_commands.discover_repo_types")
    def test_list_repos(self, mock_disc, mock_disabled):
        mock_repo = Mock()
        mock_repo.REPO_TYPE = "git"
        mock_repo.__module__ = "agent_manager.plugins.repos.git_repo"
        mock_disc.return_value = [mock_repo]
        mock_disabled.return_value = {"repos": []}
        messages = []

        with patch(
            "agent_manager.cli_extensions.plugin_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            PluginCommands._handle_repos("list", Mock())

        output = "\n".join(messages)
        assert "git" in output

    @patch("agent_manager.cli_extensions.plugin_commands.set_plugin_enabled")
    def test_disable_repo(self, mock_enable):
        mock_enable.return_value = True
        args = Mock()
        args.name = "git"

        PluginCommands._handle_repos("disable", args)

        mock_enable.assert_called_once_with(
            "repos", "git", enabled=False,
        )


class TestPluginCommandsMergers:

    def test_no_action_shows_usage(self):
        pc = PluginCommands()
        messages = []

        with patch(
            "agent_manager.cli_extensions.plugin_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            pc._handle_mergers(None, Mock())

        output = "\n".join(messages)
        assert "plugins mergers" in output

    def test_show_merger_not_found(self):
        pc = PluginCommands(merger_registry=Mock())
        with patch.object(pc, "_find_merger_class", return_value=None):
            with pytest.raises(SystemExit):
                with patch(
                    "agent_manager.cli_extensions.plugin_commands.message",
                ):
                    pc._handle_mergers("show", Mock(name="NoSuch"))
