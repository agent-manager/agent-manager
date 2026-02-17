"""Tests for cli_extensions/agent_commands.py - Agent CLI commands (V2)."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agent_manager.cli_extensions.agent_commands import AgentCommands


class TestAgentCommandsAddCliArguments:

    @patch("agent_manager.cli_extensions.agent_commands.get_agent_names")
    def test_adds_agents_and_run_parsers(self, mock_names):
        mock_names.return_value = ["claude"]
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_parser.add_subparsers.return_value = Mock()
        mock_subparsers.add_parser.return_value = mock_parser

        AgentCommands.add_cli_arguments(mock_subparsers)

        calls = [c[0][0] for c in mock_subparsers.add_parser.call_args_list]
        assert "agents" in calls
        assert "run" in calls

    @patch("agent_manager.cli_extensions.agent_commands.get_agent_names")
    def test_adds_agents_subcommands(self, mock_names):
        mock_names.return_value = ["claude"]
        mock_subparsers = Mock()
        mock_agents_parser = Mock()
        mock_agents_sub = Mock()
        mock_agents_parser.add_subparsers.return_value = mock_agents_sub

        def side_effect(name, **kwargs):
            if name == "agents":
                return mock_agents_parser
            return Mock()

        mock_subparsers.add_parser.side_effect = side_effect

        AgentCommands.add_cli_arguments(mock_subparsers)

        calls = [c[0][0] for c in mock_agents_sub.add_parser.call_args_list]
        assert "list" in calls
        assert "enable" in calls
        assert "disable" in calls

    @patch("agent_manager.cli_extensions.agent_commands.get_agent_names")
    def test_run_has_agent_choices(self, mock_names):
        mock_names.return_value = ["claude", "custom"]
        mock_subparsers = Mock()
        mock_run = Mock()

        def side_effect(name, **kwargs):
            if name == "run":
                return mock_run
            m = Mock()
            m.add_subparsers.return_value = Mock()
            return m

        mock_subparsers.add_parser.side_effect = side_effect

        AgentCommands.add_cli_arguments(mock_subparsers)

        for call in mock_run.add_argument.call_args_list:
            if call[0] and call[0][0] == "--agent":
                assert call[1]["choices"] == ["all", "claude", "custom"]
                return
        pytest.fail("--agent argument not found")

    @patch("agent_manager.cli_extensions.agent_commands.get_agent_names")
    def test_no_scope_argument(self, mock_names):
        """--scope was removed in V2."""
        mock_names.return_value = []
        mock_subparsers = Mock()
        mock_run = Mock()

        def side_effect(name, **kwargs):
            if name == "run":
                return mock_run
            m = Mock()
            m.add_subparsers.return_value = Mock()
            return m

        mock_subparsers.add_parser.side_effect = side_effect

        AgentCommands.add_cli_arguments(mock_subparsers)

        for call in mock_run.add_argument.call_args_list:
            if call[0] and call[0][0] == "--scope":
                pytest.fail("--scope should not exist in V2")


class TestAgentCommandsProcessCliCommand:

    @patch("agent_manager.cli_extensions.agent_commands.run_agents")
    @patch("agent_manager.cli_extensions.agent_commands.message")
    def test_calls_run_agents_with_v2_signature(self, mock_msg, mock_run):
        args = Mock()
        args.agent = "claude"
        config_data = {
            "repos": [{"name": "org", "url": "x", "repo_type": "git"}],
            "mergers": {"JsonMerger": {"indent": 2}},
        }

        AgentCommands.process_cli_command(args, config_data)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["claude"]
        assert call_args[0][1] == config_data["repos"]
        assert isinstance(call_args[0][2], Path)
        assert call_args[0][3] == {"JsonMerger": {"indent": 2}}

    @patch("agent_manager.cli_extensions.agent_commands.run_agents")
    @patch("agent_manager.cli_extensions.agent_commands.message")
    def test_all_agents(self, mock_msg, mock_run):
        args = Mock()
        args.agent = "all"
        config_data = {"repos": [], "mergers": {}}

        AgentCommands.process_cli_command(args, config_data)

        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["all"]


class TestAgentCommandsProcessAgentsCommand:

    def test_no_subcommand(self):
        args = Mock()
        args.agents_command = None
        messages = []

        with patch(
            "agent_manager.cli_extensions.agent_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            AgentCommands.process_agents_command(args)

        output = "\n".join(messages)
        assert "Usage: agent-manager agents <command>" in output

    @patch(
        "agent_manager.cli_extensions.agent_commands"
        ".AgentCommands.list_agents",
    )
    def test_list(self, mock_list):
        args = Mock()
        args.agents_command = "list"
        AgentCommands.process_agents_command(args)
        mock_list.assert_called_once()


class TestAgentCommandsListAgents:

    @patch("agent_manager.cli_extensions.agent_commands.get_disabled_plugins")
    @patch("agent_manager.cli_extensions.agent_commands.discover_agent_plugins")
    def test_with_plugins(self, mock_disc, mock_disabled):
        mock_disc.return_value = {
            "claude": {"package_name": "am_agent_claude", "source": "package"},
        }
        mock_disabled.return_value = {"agents": []}
        messages = []

        with patch(
            "agent_manager.cli_extensions.agent_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            AgentCommands.list_agents()

        output = "\n".join(messages)
        assert "claude" in output
        assert "am_agent_claude" in output

    @patch("agent_manager.cli_extensions.agent_commands.get_disabled_plugins")
    @patch("agent_manager.cli_extensions.agent_commands.discover_agent_plugins")
    def test_no_plugins(self, mock_disc, mock_disabled):
        mock_disc.return_value = {}
        mock_disabled.return_value = {"agents": []}
        messages = []

        with patch(
            "agent_manager.cli_extensions.agent_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            AgentCommands.list_agents()

        output = "\n".join(messages)
        assert "No agent plugins found" in output
