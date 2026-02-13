"""Tests for core/agents.py - Agent discovery and loading."""

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
    """Test cases for discover_agent_plugins function."""

    @patch("agent_manager.core.agents.discover_external_plugins")
    def test_calls_discover_external_plugins(self, mock_discover):
        """Test that discover_agent_plugins uses the utility correctly."""
        mock_discover.return_value = {"claude": {"package_name": "am_agent_claude", "source": "package"}}

        result = discover_agent_plugins()

        mock_discover.assert_called_once_with(
            plugin_type="agent",
            package_prefix=AGENT_PLUGIN_PREFIX,
        )
        assert result == {"claude": {"package_name": "am_agent_claude", "source": "package"}}

    @patch("agent_manager.core.agents.discover_external_plugins")
    def test_returns_empty_dict_when_no_plugins(self, mock_discover):
        """Test that empty dict is returned when no plugins found."""
        mock_discover.return_value = {}

        result = discover_agent_plugins()

        assert result == {}


class TestGetAgentNames:
    """Test cases for get_agent_names function."""

    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_returns_sorted_names(self, mock_discover):
        """Test that agent names are returned sorted."""
        mock_discover.return_value = {
            "zebra": {"package_name": "am_agent_zebra"},
            "alpha": {"package_name": "am_agent_alpha"},
            "middle": {"package_name": "am_agent_middle"},
        }

        result = get_agent_names()

        assert result == ["alpha", "middle", "zebra"]

    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_returns_empty_list_when_no_plugins(self, mock_discover):
        """Test that empty list is returned when no plugins found."""
        mock_discover.return_value = {}

        result = get_agent_names()

        assert result == []


class TestLoadAgent:
    """Test cases for load_agent function."""

    @patch("agent_manager.core.agents.load_plugin_class")
    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_loads_agent_successfully(self, mock_discover, mock_load_class):
        """Test successful agent loading."""
        mock_discover.return_value = {"claude": {"package_name": "am_agent_claude", "source": "package"}}
        mock_agent_class = Mock()
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance
        mock_load_class.return_value = mock_agent_class

        result = load_agent("claude")

        mock_load_class.assert_called_once_with({"package_name": "am_agent_claude", "source": "package"}, "Agent")
        assert result == mock_agent_instance

    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_exits_when_agent_not_found(self, mock_discover):
        """Test that SystemExit is raised when agent not found."""
        mock_discover.return_value = {"claude": {"package_name": "am_agent_claude"}}

        with patch("agent_manager.core.agents.message"):
            with pytest.raises(SystemExit):
                load_agent("nonexistent")

    @patch("agent_manager.core.agents.load_plugin_class")
    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_exits_on_load_error(self, mock_discover, mock_load_class):
        """Test that SystemExit is raised on load error."""
        mock_discover.return_value = {"claude": {"package_name": "am_agent_claude"}}
        mock_load_class.side_effect = Exception("Load failed")

        with patch("agent_manager.core.agents.message"):
            with pytest.raises(SystemExit):
                load_agent("claude")

    @patch("agent_manager.core.agents.load_plugin_class")
    def test_uses_provided_plugins_dict(self, mock_load_class):
        """Test that provided plugins dict is used instead of discovering."""
        plugins = {"claude": {"package_name": "am_agent_claude", "source": "package"}}
        mock_agent_class = Mock()
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance
        mock_load_class.return_value = mock_agent_class

        result = load_agent("claude", plugins)

        mock_load_class.assert_called_once_with({"package_name": "am_agent_claude", "source": "package"}, "Agent")
        assert result == mock_agent_instance


class TestRunAgents:
    """Test cases for run_agents function."""

    @patch("agent_manager.core.agents.load_agent")
    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_runs_single_agent(self, mock_discover, mock_load_agent):
        """Test running a single specified agent."""
        mock_discover.return_value = {
            "claude": {"package_name": "am_agent_claude"},
            "other": {"package_name": "am_agent_other"},
        }
        mock_agent_instance = Mock()
        mock_agent_instance.get_scope_names.return_value = ["default"]
        mock_load_agent.return_value = mock_agent_instance

        config_data = {"hierarchy": []}

        with patch("agent_manager.core.agents.message"):
            run_agents(["claude"], config_data)

        mock_load_agent.assert_called_once()
        mock_agent_instance.update.assert_called_once_with(config_data, scope="default")

    @patch("agent_manager.core.agents.load_agent")
    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_runs_all_agents(self, mock_discover, mock_load_agent):
        """Test running all agents when 'all' is specified."""
        mock_discover.return_value = {
            "agent1": {"package_name": "am_agent_agent1"},
            "agent2": {"package_name": "am_agent_agent2"},
        }
        mock_agent_instance = Mock()
        mock_agent_instance.get_scope_names.return_value = ["default"]
        mock_load_agent.return_value = mock_agent_instance

        config_data = {"hierarchy": []}

        with patch("agent_manager.core.agents.message"):
            run_agents(["all"], config_data)

        # Should run both agents
        assert mock_load_agent.call_count == 2
        assert mock_agent_instance.update.call_count == 2

    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_exits_when_no_agents_found(self, mock_discover):
        """Test that SystemExit is raised when no agents found."""
        mock_discover.return_value = {}

        with patch("agent_manager.core.agents.message"):
            with pytest.raises(SystemExit):
                run_agents(["all"], {})

    @patch("agent_manager.core.agents.load_agent")
    @patch("agent_manager.core.agents.discover_agent_plugins")
    def test_exits_on_agent_error(self, mock_discover, mock_load_agent):
        """Test that SystemExit is raised when agent fails."""
        mock_discover.return_value = {"claude": {"package_name": "am_agent_claude"}}
        mock_agent_instance = Mock()
        mock_agent_instance.get_scope_names.return_value = ["default"]
        mock_agent_instance.update.side_effect = Exception("Update failed")
        mock_load_agent.return_value = mock_agent_instance

        with patch("agent_manager.core.agents.message"):
            with pytest.raises(SystemExit):
                run_agents(["claude"], {})


class TestAgentPluginPrefix:
    """Test cases for AGENT_PLUGIN_PREFIX constant."""

    def test_prefix_is_am_agent(self):
        """Test that the plugin prefix is 'am_agent_'."""
        assert AGENT_PLUGIN_PREFIX == "am_agent_"
