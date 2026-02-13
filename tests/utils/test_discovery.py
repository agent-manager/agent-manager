"""Tests for utils/discovery.py - Generic plugin discovery utilities."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from agent_manager.utils.discovery import (
    _discover_by_entry_points,
    _discover_by_package_prefix,
    discover_external_plugins,
    filter_disabled_plugins,
    get_disabled_plugins,
    is_plugin_disabled,
    load_plugin_class,
    set_plugin_enabled,
)


class TestDiscoverByPackagePrefix:
    """Test cases for _discover_by_package_prefix function."""

    @patch("agent_manager.utils.discovery.importlib.metadata.distributions")
    def test_discovers_single_plugin(self, mock_distributions):
        """Test discovery of single plugin by prefix."""
        mock_dist = Mock()
        mock_dist.name = "am-agent-claude"
        mock_distributions.return_value = [mock_dist]

        result = _discover_by_package_prefix("agent", "am_agent_")

        assert "claude" in result
        assert result["claude"]["package_name"] == "am_agent_claude"
        assert result["claude"]["source"] == "package"

    @patch("agent_manager.utils.discovery.importlib.metadata.distributions")
    def test_discovers_multiple_plugins(self, mock_distributions):
        """Test discovery of multiple plugins."""
        mock_dist1 = Mock()
        mock_dist1.name = "am-agent-claude"
        mock_dist2 = Mock()
        mock_dist2.name = "am-agent-custom"
        mock_dist3 = Mock()
        mock_dist3.name = "other-module"  # Should be ignored

        mock_distributions.return_value = [mock_dist1, mock_dist2, mock_dist3]

        result = _discover_by_package_prefix("agent", "am_agent_")

        assert len(result) == 2
        assert "claude" in result
        assert "custom" in result

    @patch("agent_manager.utils.discovery.importlib.metadata.distributions")
    def test_discovers_no_plugins(self, mock_distributions):
        """Test discovery when no matching plugins."""
        mock_dist = Mock()
        mock_dist.name = "other-module"
        mock_distributions.return_value = [mock_dist]

        result = _discover_by_package_prefix("agent", "am_agent_")

        assert result == {}

    @patch("agent_manager.utils.discovery.importlib.metadata.distributions")
    def test_normalizes_package_names(self, mock_distributions):
        """Test that hyphens are converted to underscores."""
        mock_dist = Mock()
        mock_dist.name = "am-agent-my-custom-plugin"
        mock_distributions.return_value = [mock_dist]

        result = _discover_by_package_prefix("agent", "am_agent_")

        assert "my_custom_plugin" in result
        assert result["my_custom_plugin"]["package_name"] == "am_agent_my_custom_plugin"

    @patch("agent_manager.utils.discovery.importlib.metadata.distributions")
    def test_handles_exception(self, mock_distributions):
        """Test that exceptions are handled gracefully."""
        mock_distributions.side_effect = Exception("Discovery failed")

        with patch("agent_manager.utils.discovery.message"):
            result = _discover_by_package_prefix("agent", "am_agent_")

        assert result == {}


class TestDiscoverByEntryPoints:
    """Test cases for _discover_by_entry_points function."""

    @patch("agent_manager.utils.discovery.importlib.metadata.entry_points")
    def test_discovers_via_entry_points(self, mock_entry_points):
        """Test discovery via entry points."""

        # Create a real class hierarchy for issubclass check
        class BaseClass:
            pass

        class MockClass(BaseClass):
            pass

        mock_ep = Mock()
        mock_ep.name = "smart_markdown"
        mock_ep.value = "am_merger_smart_markdown:SmartMarkdownMerger"
        mock_ep.load.return_value = MockClass

        mock_eps = Mock()
        mock_eps.select.return_value = [mock_ep]
        mock_entry_points.return_value = mock_eps

        with patch("agent_manager.utils.discovery.message"):
            result = _discover_by_entry_points("merger", "agent_manager.mergers", BaseClass)

        assert "smart_markdown" in result
        assert result["smart_markdown"]["class"] == MockClass
        assert result["smart_markdown"]["source"] == "entry_point"

    @patch("agent_manager.utils.discovery.importlib.metadata.entry_points")
    def test_handles_invalid_class(self, mock_entry_points):
        """Test handling of entry point that doesn't point to valid class."""
        mock_ep = Mock()
        mock_ep.name = "invalid"
        mock_ep.load.return_value = "not a class"

        mock_eps = Mock()
        mock_eps.select.return_value = [mock_ep]
        mock_entry_points.return_value = mock_eps

        base_class = type("BaseClass", (), {})

        with patch("agent_manager.utils.discovery.message"):
            result = _discover_by_entry_points("merger", "agent_manager.mergers", base_class)

        assert result == {}

    @patch("agent_manager.utils.discovery.importlib.metadata.entry_points")
    def test_handles_load_error(self, mock_entry_points):
        """Test handling of entry point load error."""
        mock_ep = Mock()
        mock_ep.name = "broken"
        mock_ep.load.side_effect = Exception("Load failed")

        mock_eps = Mock()
        mock_eps.select.return_value = [mock_ep]
        mock_entry_points.return_value = mock_eps

        with patch("agent_manager.utils.discovery.message"):
            result = _discover_by_entry_points("merger", "agent_manager.mergers", None)

        assert result == {}


class TestDiscoverExternalPlugins:
    """Test cases for discover_external_plugins function."""

    @patch("agent_manager.utils.discovery._discover_by_entry_points")
    @patch("agent_manager.utils.discovery._discover_by_package_prefix")
    def test_combines_both_methods(self, mock_prefix, mock_entry_points):
        """Test that both discovery methods are used."""
        mock_prefix.return_value = {"agent1": {"package_name": "am_agent_agent1", "source": "package"}}
        mock_entry_points.return_value = {"merger1": {"package_name": "am_merger_merger1", "source": "entry_point"}}

        result = discover_external_plugins(
            plugin_type="test",
            package_prefix="am_test_",
            entry_point_group="agent_manager.test",
        )

        assert "agent1" in result
        assert "merger1" in result

    @patch("agent_manager.utils.discovery._discover_by_entry_points")
    @patch("agent_manager.utils.discovery._discover_by_package_prefix")
    def test_only_package_prefix(self, mock_prefix, mock_entry_points):
        """Test with only package prefix method."""
        mock_prefix.return_value = {"agent1": {"package_name": "am_agent_agent1", "source": "package"}}

        result = discover_external_plugins(
            plugin_type="test",
            package_prefix="am_test_",
        )

        mock_prefix.assert_called_once()
        mock_entry_points.assert_not_called()
        assert "agent1" in result

    @patch("agent_manager.utils.discovery._discover_by_entry_points")
    @patch("agent_manager.utils.discovery._discover_by_package_prefix")
    def test_only_entry_points(self, mock_prefix, mock_entry_points):
        """Test with only entry points method."""
        mock_entry_points.return_value = {"merger1": {"package_name": "am_merger_merger1", "source": "entry_point"}}

        result = discover_external_plugins(
            plugin_type="test",
            entry_point_group="agent_manager.test",
        )

        mock_prefix.assert_not_called()
        mock_entry_points.assert_called_once()
        assert "merger1" in result


class TestLoadPluginClass:
    """Test cases for load_plugin_class function."""

    def test_returns_preloaded_class(self):
        """Test that preloaded class is returned directly."""
        mock_class = Mock()
        plugin_info = {"package_name": "some_package", "class": mock_class, "source": "entry_point"}

        result = load_plugin_class(plugin_info)

        assert result == mock_class

    @patch("agent_manager.utils.discovery.importlib.import_module")
    def test_imports_and_returns_class(self, mock_import):
        """Test that module is imported and class is retrieved."""
        mock_agent_class = Mock()
        mock_module = Mock()
        mock_module.Agent = mock_agent_class
        mock_import.return_value = mock_module

        plugin_info = {"package_name": "am_agent_claude", "source": "package"}

        result = load_plugin_class(plugin_info, "Agent")

        mock_import.assert_called_once_with("am_agent_claude")
        assert result == mock_agent_class

    @patch("agent_manager.utils.discovery.importlib.import_module")
    def test_raises_on_import_error(self, mock_import):
        """Test that ImportError is raised on failure."""
        mock_import.side_effect = ImportError("Module not found")

        plugin_info = {"package_name": "nonexistent", "source": "package"}

        with pytest.raises(ImportError):
            load_plugin_class(plugin_info, "Agent")


class TestGetDisabledPlugins:
    """Test cases for get_disabled_plugins function."""

    def test_returns_empty_when_no_config(self):
        """Test returns empty lists when config doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            result = get_disabled_plugins(config_file)

            assert result == {"mergers": [], "agents": [], "repos": []}

    def test_returns_disabled_from_config(self):
        """Test returns disabled plugins from config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config = {
                "hierarchy": [],
                "plugins": {
                    "disabled": {
                        "mergers": ["smart_markdown"],
                        "agents": ["claude"],
                    }
                },
            }
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            result = get_disabled_plugins(config_file)

            assert result["mergers"] == ["smart_markdown"]
            assert result["agents"] == ["claude"]
            assert result["repos"] == []

    def test_handles_partial_config(self):
        """Test handles config with partial disabled section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config = {"hierarchy": [], "plugins": {"disabled": {"mergers": ["test"]}}}
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            result = get_disabled_plugins(config_file)

            assert result["mergers"] == ["test"]
            assert result["agents"] == []
            assert result["repos"] == []


class TestIsPluginDisabled:
    """Test cases for is_plugin_disabled function."""

    def test_returns_true_for_disabled(self):
        """Test returns True for disabled plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config = {"plugins": {"disabled": {"mergers": ["smart_markdown"]}}}
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            result = is_plugin_disabled("mergers", "smart_markdown", config_file)

            assert result is True

    def test_returns_false_for_enabled(self):
        """Test returns False for enabled plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config = {"plugins": {"disabled": {"mergers": ["other"]}}}
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            result = is_plugin_disabled("mergers", "smart_markdown", config_file)

            assert result is False


class TestSetPluginEnabled:
    """Test cases for set_plugin_enabled function."""

    def test_disables_plugin(self):
        """Test disabling a plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config = {"hierarchy": []}
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            with patch("agent_manager.utils.discovery.message"):
                result = set_plugin_enabled("mergers", "smart_markdown", False, config_file)

            assert result is True

            with open(config_file) as f:
                updated_config = yaml.safe_load(f)

            assert "smart_markdown" in updated_config["plugins"]["disabled"]["mergers"]

    def test_enables_plugin(self):
        """Test enabling a disabled plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config = {"hierarchy": [], "plugins": {"disabled": {"mergers": ["smart_markdown"]}}}
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            with patch("agent_manager.utils.discovery.message"):
                result = set_plugin_enabled("mergers", "smart_markdown", True, config_file)

            assert result is True

            with open(config_file) as f:
                updated_config = yaml.safe_load(f)

            # Should not have plugins section anymore since it's empty
            assert "plugins" not in updated_config or "disabled" not in updated_config.get("plugins", {})

    def test_cleans_up_empty_sections(self):
        """Test that empty sections are cleaned up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config = {"hierarchy": [], "plugins": {"disabled": {"mergers": ["only_one"]}}}
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            with patch("agent_manager.utils.discovery.message"):
                set_plugin_enabled("mergers", "only_one", True, config_file)

            with open(config_file) as f:
                updated_config = yaml.safe_load(f)

            # Plugins section should be removed entirely
            assert "plugins" not in updated_config


class TestFilterDisabledPlugins:
    """Test cases for filter_disabled_plugins function."""

    def test_filters_disabled_plugins(self):
        """Test that disabled plugins are filtered out."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config = {"plugins": {"disabled": {"mergers": ["disabled_one"]}}}
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            plugins = {
                "enabled_one": {"package": "test1"},
                "disabled_one": {"package": "test2"},
                "enabled_two": {"package": "test3"},
            }

            with patch("agent_manager.utils.discovery.message"):
                result = filter_disabled_plugins(plugins, "mergers", config_file)

            assert "enabled_one" in result
            assert "enabled_two" in result
            assert "disabled_one" not in result

    def test_returns_all_when_none_disabled(self):
        """Test returns all plugins when none are disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config = {"hierarchy": []}
            with open(config_file, "w") as f:
                yaml.dump(config, f)

            plugins = {"one": {"package": "test1"}, "two": {"package": "test2"}}

            result = filter_disabled_plugins(plugins, "mergers", config_file)

            assert len(result) == 2
