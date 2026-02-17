"""Tests for core/agents.py - Agent discovery and loading (V2)."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agent_manager.core.agents import (
    AGENT_PLUGIN_PREFIX,
    discover_agent_plugins,
    get_agent_names,
    load_agent,
    run_agents,
)


class TestDiscoverAgentPlugins:

    @patch("agent_manager.core.agents.discover_external_plugins")
    def test_calls_discover_external_plugins(self, mock_discover):
        mock_discover.return_value = {
            "claude": {"package_name": "am_agent_claude", "source": "package"}
        }
        result = discover_agent_plugins()
        mock_discover.assert_called_once_with(
            plugin_type="agent",
            package_prefix=AGENT_PLUGIN_PREFIX,
        )
        assert "claude" in result

    @patch("agent_manager.core.agents.discover_external_plugins")
    def test_returns_empty_dict_when_no_plugins(self, mock_discover):
        mock_discover.return_value = {}
        assert discover_agent_plugins() == {}


class TestGetAgentNames:

    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_returns_sorted_names(self, mock_discover):
        mock_discover.return_value = {
            "zebra": {},
            "alpha": {},
            "middle": {},
        }
        assert get_agent_names() == ["alpha", "middle", "zebra"]

    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_returns_empty_list_when_no_plugins(self, mock_discover):
        mock_discover.return_value = {}
        assert get_agent_names() == []


class TestLoadAgent:

    @patch("agent_manager.core.agents.load_plugin_class")
    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_loads_agent_successfully(self, mock_discover, mock_load):
        mock_discover.return_value = {
            "claude": {"package_name": "am_agent_claude", "source": "package"}
        }
        mock_agent = Mock()
        mock_load.return_value = Mock(return_value=mock_agent)

        result = load_agent("claude")
        assert result == mock_agent

    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_exits_when_not_found(self, mock_discover):
        mock_discover.return_value = {"claude": {}}
        with (
            patch("agent_manager.core.agents.message"),
            pytest.raises(SystemExit),
        ):
            load_agent("nonexistent")

    @patch("agent_manager.core.agents.load_plugin_class")
    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_exits_on_load_error(self, mock_discover, mock_load):
        mock_discover.return_value = {"claude": {"package_name": "x"}}
        mock_load.side_effect = Exception("fail")
        with (
            patch("agent_manager.core.agents.message"),
            pytest.raises(SystemExit),
        ):
            load_agent("claude")

    @patch("agent_manager.core.agents.load_plugin_class")
    def test_uses_provided_plugins(self, mock_load):
        plugins = {"claude": {"package_name": "am_agent_claude", "source": "package"}}
        mock_agent = Mock()
        mock_load.return_value = Mock(return_value=mock_agent)
        result = load_agent("claude", plugins)
        assert result == mock_agent


class TestRunAgents:

    @patch("agent_manager.core.agents.load_agent")
    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_runs_single_agent(self, mock_discover, mock_load):
        mock_discover.return_value = {
            "claude": {"package_name": "am_agent_claude"},
            "other": {"package_name": "am_agent_other"},
        }
        mock_agent = Mock()
        mock_load.return_value = mock_agent

        repos = [{"name": "org", "repo": Mock()}]
        base_dir = Path("/tmp/test")

        with patch("agent_manager.core.agents.message"):
            run_agents(["claude"], repos, base_dir)

        mock_load.assert_called_once()
        mock_agent.update.assert_called_once_with(repos, base_dir, None)

    @patch("agent_manager.core.agents.load_agent")
    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_runs_all_agents(self, mock_discover, mock_load):
        mock_discover.return_value = {
            "agent1": {"package_name": "x"},
            "agent2": {"package_name": "y"},
        }
        mock_agent = Mock()
        mock_load.return_value = mock_agent

        repos = []
        base_dir = Path("/tmp/test")

        with patch("agent_manager.core.agents.message"):
            run_agents(["all"], repos, base_dir)

        assert mock_load.call_count == 2
        assert mock_agent.update.call_count == 2

    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_exits_when_no_agents(self, mock_discover):
        mock_discover.return_value = {}
        with (
            patch("agent_manager.core.agents.message"),
            pytest.raises(SystemExit),
        ):
            run_agents(["all"], [], Path("/tmp"))

    @patch("agent_manager.core.agents.load_agent")
    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_exits_on_agent_error(self, mock_discover, mock_load):
        mock_discover.return_value = {"claude": {"package_name": "x"}}
        mock_agent = Mock()
        mock_agent.update.side_effect = Exception("boom")
        mock_load.return_value = mock_agent

        with (
            patch("agent_manager.core.agents.message"),
            pytest.raises(SystemExit),
        ):
            run_agents(["claude"], [], Path("/tmp"))

    @patch("agent_manager.core.agents.load_agent")
    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_passes_merger_settings(self, mock_discover, mock_load):
        mock_discover.return_value = {"claude": {"package_name": "x"}}
        mock_agent = Mock()
        mock_load.return_value = mock_agent

        repos = []
        base_dir = Path("/tmp")
        settings = {"JsonMerger": {"indent": 2}}

        with patch("agent_manager.core.agents.message"):
            run_agents(["claude"], repos, base_dir, settings)

        mock_agent.update.assert_called_once_with(repos, base_dir, settings)


class TestAgentPluginPrefix:

    def test_prefix_is_am_agent(self):
        assert AGENT_PLUGIN_PREFIX == "am_agent_"
