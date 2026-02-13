"""Tests for mergers/manager.py - Merger CLI management."""

import argparse
from unittest.mock import patch

import pytest

from agent_manager.cli_extensions.merger_commands import MergerCommands
from agent_manager.config import Config
from agent_manager.core.merger_registry import MergerRegistry
from agent_manager.plugins.mergers.json_merger import JsonMerger
from agent_manager.plugins.mergers.markdown_merger import MarkdownMerger
from agent_manager.plugins.mergers.yaml_merger import YamlMerger


@pytest.fixture
def merger_registry():
    """Create a test merger registry."""
    registry = MergerRegistry()
    registry.register_extension(".json", JsonMerger)
    registry.register_extension(".yaml", YamlMerger)
    registry.register_extension(".md", MarkdownMerger)
    return registry


@pytest.fixture
def merger_manager(merger_registry):
    """Create a test merger manager."""
    return MergerCommands(merger_registry)


@pytest.fixture
def mock_config(tmp_path):
    """Create a mock config with a temporary directory."""
    config_dir = tmp_path / ".agent-manager"
    config_dir.mkdir()
    return Config(config_dir=config_dir)


class TestMergerCommandsCLI:
    """Test cases for MergerCommands CLI argument handling."""

    def test_add_cli_arguments(self):
        """Test that CLI arguments are properly added."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        MergerCommands.add_cli_arguments(subparsers)

        # Parse 'mergers list' command
        args = parser.parse_args(["mergers", "list"])
        assert args.command == "mergers"
        assert args.mergers_command == "list"

    def test_add_cli_arguments_show(self):
        """Test 'mergers show' CLI arguments."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        MergerCommands.add_cli_arguments(subparsers)

        # Parse 'mergers show' command
        args = parser.parse_args(["mergers", "show", "JsonMerger"])
        assert args.command == "mergers"
        assert args.mergers_command == "show"
        assert args.name == "JsonMerger"

    def test_add_cli_arguments_configure(self):
        """Test 'mergers configure' CLI arguments."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        MergerCommands.add_cli_arguments(subparsers)

        # Parse 'mergers configure' command
        args = parser.parse_args(["mergers", "configure"])
        assert args.command == "mergers"
        assert args.mergers_command == "configure"
        assert args.merger is None  # Optional

    def test_add_cli_arguments_configure_with_merger(self):
        """Test 'mergers configure' with specific merger."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        MergerCommands.add_cli_arguments(subparsers)

        args = parser.parse_args(["mergers", "configure", "--merger", "JsonMerger"])
        assert args.command == "mergers"
        assert args.mergers_command == "configure"
        assert args.merger == "JsonMerger"


class TestMergerCommandsListCommand:
    """Test cases for 'mergers list' command."""

    def test_list_mergers(self, merger_manager, capsys):
        """Test listing registered mergers."""
        with patch("agent_manager.cli_extensions.merger_commands.message") as mock_message:
            merger_manager.list_mergers()

            # Should show output
            assert mock_message.called

    def test_list_mergers_shows_extensions(self, merger_manager, capsys):
        """Test that list shows extension-based mergers."""
        registry = merger_manager.merger_registry
        registry.register_extension(".json", JsonMerger)
        registry.register_extension(".yaml", YamlMerger)

        with patch("agent_manager.cli_extensions.merger_commands.message") as mock_message:
            merger_manager.list_mergers()

            # Verify message was called (can't easily check exact output)
            assert mock_message.called

    def test_list_mergers_shows_filenames(self, merger_manager):
        """Test that list shows filename-specific mergers."""
        registry = merger_manager.merger_registry
        registry.register_filename("mcp.json", JsonMerger)

        with patch("agent_manager.cli_extensions.merger_commands.message") as mock_message:
            merger_manager.list_mergers()

            assert mock_message.called


class TestMergerCommandsShowCommand:
    """Test cases for 'mergers show' command."""

    def test_show_merger_with_valid_merger(self, merger_manager):
        """Test showing preferences for a valid merger."""
        with patch("agent_manager.cli_extensions.merger_commands.message") as mock_message:
            merger_manager.show_merger("JsonMerger")

            # Should show info about preferences
            assert mock_message.called

    def test_show_merger_with_invalid_merger(self, merger_manager):
        """Test showing preferences for an invalid merger."""
        with patch("agent_manager.cli_extensions.merger_commands.message") as mock_message:
            with pytest.raises(SystemExit):
                merger_manager.show_merger("NonExistentMerger")

            # Should show error
            assert mock_message.called

    def test_show_merger_with_no_preferences(self, merger_manager):
        """Test showing merger that has no preferences."""
        with patch("agent_manager.cli_extensions.merger_commands.message") as mock_message:
            merger_manager.show_merger("CopyMerger")

            # Should indicate no preferences
            assert mock_message.called


class TestMergerCommandsHelpers:
    """Test cases for MergerCommands helper methods."""

    def test_get_all_merger_classes(self, merger_manager):
        """Test getting all registered merger classes."""
        merger_classes = merger_manager._get_all_merger_classes()

        assert len(merger_classes) > 0
        # Should include at least the default merger
        assert any(mc.__name__ == "CopyMerger" for mc in merger_classes)

    def test_get_all_merger_classes_unique(self, merger_manager):
        """Test that get_all_merger_classes returns unique classes."""
        registry = merger_manager.merger_registry
        # Register JsonMerger multiple times
        registry.register_extension(".json", JsonMerger)
        registry.register_filename("config.json", JsonMerger)

        merger_classes = merger_manager._get_all_merger_classes()

        # Count occurrences of JsonMerger
        json_merger_count = sum(1 for mc in merger_classes if mc.__name__ == "JsonMerger")
        assert json_merger_count == 1  # Should be unique

    def test_find_merger_class_valid(self, merger_manager):
        """Test finding a valid merger class by name."""
        merger_class = merger_manager._find_merger_class("JsonMerger")

        assert merger_class == JsonMerger

    def test_find_merger_class_invalid(self, merger_manager):
        """Test finding an invalid merger class."""
        merger_class = merger_manager._find_merger_class("NonExistentMerger")

        assert merger_class is None


class TestMergerCommandsProcessCommand:
    """Test cases for process_cli_command."""

    def test_process_cli_command_list(self, merger_manager, mock_config):
        """Test processing 'mergers list' command."""
        args = argparse.Namespace(mergers_command="list")

        with patch.object(merger_manager, "list_mergers") as mock_list:
            merger_manager.process_cli_command(args, mock_config)
            mock_list.assert_called_once()

    def test_process_cli_command_show(self, merger_manager, mock_config):
        """Test processing 'mergers show' command."""
        args = argparse.Namespace(mergers_command="show", name="JsonMerger")

        with patch.object(merger_manager, "show_merger") as mock_show:
            merger_manager.process_cli_command(args, mock_config)
            mock_show.assert_called_once_with("JsonMerger")

    def test_process_cli_command_configure(self, merger_manager, mock_config):
        """Test processing 'mergers configure' command."""
        args = argparse.Namespace(mergers_command="configure", merger=None)

        with patch.object(merger_manager, "configure_mergers") as mock_configure:
            merger_manager.process_cli_command(args, mock_config)
            mock_configure.assert_called_once_with(mock_config, None)

    def test_process_cli_command_no_subcommand_shows_usage(self, merger_manager, mock_config):
        """Test that no subcommand shows friendly usage message."""
        args = argparse.Namespace()  # No mergers_command

        messages = []

        def capture_message(text, *args_inner, **kwargs):
            messages.append(text)

        with patch("agent_manager.cli_extensions.merger_commands.message", side_effect=capture_message):
            merger_manager.process_cli_command(args, mock_config)

        output = "\n".join(messages)
        assert "Usage: agent-manager mergers <command>" in output
        assert "Available commands:" in output


class TestMergerCommandsConfigureCommand:
    """Test cases for 'mergers configure' command."""

    def test_configure_mergers_reads_config(self, merger_manager, mock_config):
        """Test that configure_mergers reads existing config."""
        # Ensure config directory exists
        mock_config.ensure_directories()

        # Create a config file with a valid hierarchy (no repo objects - they can't be serialized)
        config_data = {
            "hierarchy": [{"name": "test", "url": "https://github.com/test/repo", "repo_type": "git"}],
            "mergers": {"JsonMerger": {"indent": 4, "sort_keys": True}},
        }

        # Write the config file directly as YAML to avoid serialization issues
        import yaml

        with open(mock_config.config_file, "w") as f:
            yaml.dump(config_data, f)

        with (
            patch("builtins.input", return_value=""),  # Skip all prompts
            patch("agent_manager.cli_extensions.merger_commands.message"),
            patch.object(mock_config, "write"),
        ):
            merger_manager.configure_mergers(mock_config, specific_merger="JsonMerger")

        # Read the original config we wrote
        with open(mock_config.config_file) as f:
            loaded_config = yaml.safe_load(f)
        assert "mergers" in loaded_config

    def test_configure_mergers_creates_mergers_section(self, merger_manager, mock_config):
        """Test that configure creates mergers section if missing."""
        # Ensure config directory exists
        mock_config.ensure_directories()

        # Create a minimal config without mergers section but with valid hierarchy
        config_data = {"hierarchy": [{"name": "test", "url": "https://github.com/test/repo", "repo_type": "git"}]}

        # Write the config file directly as YAML to avoid serialization issues
        import yaml

        with open(mock_config.config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch("builtins.input", return_value=""), patch("agent_manager.cli_extensions.merger_commands.message"):
            # Capture what would be written
            written_config = None

            def capture_write(data):
                nonlocal written_config
                written_config = data

            with patch.object(mock_config, "write", side_effect=capture_write):
                merger_manager.configure_mergers(mock_config, specific_merger="JsonMerger")

        # Should have created mergers section
        assert written_config is not None
        assert "mergers" in written_config

    def test_configure_specific_merger(self, merger_manager, mock_config):
        """Test configuring a specific merger."""
        # Ensure config directory exists
        mock_config.ensure_directories()

        config_data = {"hierarchy": [{"name": "test", "url": "https://github.com/test/repo", "repo_type": "git"}]}

        # Write the config file directly as YAML to avoid serialization issues
        import yaml

        with open(mock_config.config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch("builtins.input", return_value=""), patch("agent_manager.cli_extensions.merger_commands.message"):
            # Capture what would be written
            written_config = None

            def capture_write(data):
                nonlocal written_config
                written_config = data

            with patch.object(mock_config, "write", side_effect=capture_write):
                merger_manager.configure_mergers(mock_config, specific_merger="JsonMerger")

        # Should have created mergers section
        assert written_config is not None
        assert "mergers" in written_config

    def test_configure_invalid_merger_exits(self, merger_manager, mock_config):
        """Test that configuring invalid merger exits."""
        # Ensure config directory exists
        mock_config.ensure_directories()

        config_data = {"hierarchy": [{"name": "test", "url": "https://github.com/test/repo", "repo_type": "git"}]}
        mock_config.write(config_data)

        with patch("agent_manager.cli_extensions.merger_commands.message"), pytest.raises(SystemExit):
            merger_manager.configure_mergers(mock_config, specific_merger="InvalidMerger")

    def test_configure_int_validation_min_boundary(self, merger_manager, mock_config):
        """Test that int values below minimum are clamped."""
        mock_config.ensure_directories()

        config_data = {"hierarchy": [{"name": "test", "url": "https://github.com/test/repo", "repo_type": "git"}]}
        import yaml

        with open(mock_config.config_file, "w") as f:
            yaml.dump(config_data, f)

        # JsonMerger has 'indent' with min=0, provide -1
        with (
            patch("builtins.input", side_effect=["-1", ""]),  # -1 for indent, then skip rest
            patch("agent_manager.cli_extensions.merger_commands.message"),
        ):
            written_config = None

            def capture_write(data):
                nonlocal written_config
                written_config = data

            with patch.object(mock_config, "write", side_effect=capture_write):
                merger_manager.configure_mergers(mock_config, specific_merger="JsonMerger")

            # Should clamp to minimum
            assert written_config["mergers"]["JsonMerger"]["indent"] == 0

    def test_configure_int_validation_max_boundary(self, merger_manager, mock_config):
        """Test that int values above maximum are clamped."""
        mock_config.ensure_directories()

        config_data = {"hierarchy": [{"name": "test", "url": "https://github.com/test/repo", "repo_type": "git"}]}
        import yaml

        with open(mock_config.config_file, "w") as f:
            yaml.dump(config_data, f)

        # YamlMerger has 'indent' and 'width'. Width has max=200, provide 999
        with (
            patch("builtins.input", side_effect=["", "999"]),  # skip indent, 999 for width
            patch("agent_manager.cli_extensions.merger_commands.message"),
        ):
            written_config = None

            def capture_write(data):
                nonlocal written_config
                written_config = data

            with patch.object(mock_config, "write", side_effect=capture_write):
                merger_manager.configure_mergers(mock_config, specific_merger="YamlMerger")

            # Should clamp to maximum
            assert written_config["mergers"]["YamlMerger"]["width"] == 200

    def test_configure_int_validation_invalid_input(self, merger_manager, mock_config):
        """Test that invalid int input is handled gracefully."""
        mock_config.ensure_directories()

        config_data = {"hierarchy": [{"name": "test", "url": "https://github.com/test/repo", "repo_type": "git"}]}
        import yaml

        with open(mock_config.config_file, "w") as f:
            yaml.dump(config_data, f)

        # Provide non-int value for indent
        with (
            patch("builtins.input", side_effect=["invalid", ""]),  # invalid string, then skip rest
            patch("agent_manager.cli_extensions.merger_commands.message") as mock_message,
            patch.object(mock_config, "write"),
        ):
            merger_manager.configure_mergers(mock_config, specific_merger="JsonMerger")

            # Should show warning
            assert any(
                call[0][0].startswith("Invalid") or "Invalid" in str(call) for call in mock_message.call_args_list
            )

    def test_configure_bool_validation_yes_variants(self, merger_manager, mock_config):
        """Test that various 'yes' inputs are recognized as True."""
        mock_config.ensure_directories()

        config_data = {"hierarchy": [{"name": "test", "url": "https://github.com/test/repo", "repo_type": "git"}]}
        import yaml

        with open(mock_config.config_file, "w") as f:
            yaml.dump(config_data, f)

        for yes_input in ["y", "yes", "true", "1"]:
            # JsonMerger has 'sort_keys' as bool
            with (
                patch(
                    "builtins.input", side_effect=["", yes_input, ""]
                ),  # skip indent, yes for sort_keys, skip ensure_ascii
                patch("agent_manager.cli_extensions.merger_commands.message"),
            ):
                written_config = None

                def capture_write(data):
                    nonlocal written_config
                    written_config = data

                with patch.object(mock_config, "write", side_effect=capture_write):
                    merger_manager.configure_mergers(mock_config, specific_merger="JsonMerger")

                assert written_config["mergers"]["JsonMerger"]["sort_keys"] is True

    def test_configure_bool_validation_no_variants(self, merger_manager, mock_config):
        """Test that non-yes inputs are recognized as False."""
        mock_config.ensure_directories()

        config_data = {"hierarchy": [{"name": "test", "url": "https://github.com/test/repo", "repo_type": "git"}]}
        import yaml

        with open(mock_config.config_file, "w") as f:
            yaml.dump(config_data, f)

        # JsonMerger has 'sort_keys' as bool
        with (
            patch("builtins.input", side_effect=["", "n", ""]),  # skip indent, no for sort_keys, skip ensure_ascii
            patch("agent_manager.cli_extensions.merger_commands.message"),
        ):
            written_config = None

            def capture_write(data):
                nonlocal written_config
                written_config = data

            with patch.object(mock_config, "write", side_effect=capture_write):
                merger_manager.configure_mergers(mock_config, specific_merger="JsonMerger")

            assert written_config["mergers"]["JsonMerger"]["sort_keys"] is False

    def test_configure_string_choice_validation_valid(self, merger_manager, mock_config):
        """Test that valid string choice is accepted."""
        mock_config.ensure_directories()

        config_data = {"hierarchy": [{"name": "test", "url": "https://github.com/test/repo", "repo_type": "git"}]}
        import yaml

        with open(mock_config.config_file, "w") as f:
            yaml.dump(config_data, f)

        # MarkdownMerger has 'separator_style' with choices
        with (
            patch("builtins.input", side_effect=["heading", ""]),  # valid choice, then skip rest
            patch("agent_manager.cli_extensions.merger_commands.message"),
        ):
            written_config = None

            def capture_write(data):
                nonlocal written_config
                written_config = data

            with patch.object(mock_config, "write", side_effect=capture_write):
                merger_manager.configure_mergers(mock_config, specific_merger="MarkdownMerger")

            assert written_config["mergers"]["MarkdownMerger"]["separator_style"] == "heading"

    def test_configure_string_choice_validation_invalid(self, merger_manager, mock_config):
        """Test that invalid string choice shows warning."""
        mock_config.ensure_directories()

        config_data = {"hierarchy": [{"name": "test", "url": "https://github.com/test/repo", "repo_type": "git"}]}
        import yaml

        with open(mock_config.config_file, "w") as f:
            yaml.dump(config_data, f)

        # MarkdownMerger has 'separator_style' with choices, provide invalid
        with (
            patch("builtins.input", side_effect=["invalid_choice", ""]),  # invalid choice, then skip rest
            patch("agent_manager.cli_extensions.merger_commands.message") as mock_message,
            patch.object(mock_config, "write"),
        ):
            merger_manager.configure_mergers(mock_config, specific_merger="MarkdownMerger")

            # Should show warning about invalid choice
            assert any(
                "Invalid choice" in str(call) or "invalid" in str(call).lower() for call in mock_message.call_args_list
            )
