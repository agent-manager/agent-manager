"""Comprehensive integration tests for agent_manager.py - Main CLI entry point."""

from unittest.mock import Mock, patch

import pytest

from agent_manager.agent_manager import main


class TestCLIArgumentParsing:
    """Test CLI argument parsing and routing."""

    def test_help_argument(self, capsys):
        """Test --help displays usage information."""
        with pytest.raises(SystemExit) as exc_info, patch("sys.argv", ["agent-manager", "--help"]):
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Manage your AI agents from a hierarchy of directories" in captured.out
        assert "runtime commands" in captured.out
        assert "plugin commands" in captured.out
        assert "config" in captured.out

    def test_version_verbosity_levels(self):
        """Test verbosity levels are correctly parsed."""
        test_cases = [
            ([], 0),  # No -v flag
            (["-v"], 1),  # Single -v
            (["-vv"], 2),  # Double -v
            (["-vvv"], 3),  # Triple -v
            (["--verbose"], 1),  # Long form
        ]

        for args, expected_level in test_cases:
            with patch("sys.argv", ["agent-manager"] + args + ["config", "where"]):
                with patch("agent_manager.agent_manager.Config") as mock_config:
                    with patch("agent_manager.agent_manager.ConfigCommands.process_cli_command"):
                        with patch("agent_manager.agent_manager.get_output") as mock_output:
                            mock_output_instance = Mock(verbosity=0, use_color=True)
                            mock_output.return_value = mock_output_instance
                            mock_config.return_value.ensure_directories = Mock()

                            main()

                            assert mock_output_instance.verbosity == expected_level

    def test_no_color_option(self):
        """Test --no-color disables colored output."""
        with patch("sys.argv", ["agent-manager", "--no-color", "config", "where"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.ConfigCommands.process_cli_command"):
                    with patch("agent_manager.agent_manager.get_output") as mock_output:
                        with patch("sys.stdout.isatty", return_value=True):
                            mock_output_instance = Mock(verbosity=0, use_color=True)
                            mock_output.return_value = mock_output_instance
                            mock_config.return_value.ensure_directories = Mock()

                            main()

                            assert mock_output_instance.use_color is False

    def test_color_enabled_when_tty(self):
        """Test color is enabled when stdout is a TTY."""
        with patch("sys.argv", ["agent-manager", "config", "where"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.ConfigCommands.process_cli_command"):
                    with patch("agent_manager.agent_manager.get_output") as mock_output:
                        with patch("sys.stdout.isatty", return_value=True):
                            mock_output_instance = Mock(verbosity=0, use_color=False)
                            mock_output.return_value = mock_output_instance
                            mock_config.return_value.ensure_directories = Mock()

                            main()

                            assert mock_output_instance.use_color is True

    def test_color_disabled_when_not_tty(self):
        """Test color is disabled when stdout is not a TTY."""
        with patch("sys.argv", ["agent-manager", "config", "where"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.ConfigCommands.process_cli_command"):
                    with patch("agent_manager.agent_manager.get_output") as mock_output:
                        with patch("sys.stdout.isatty", return_value=False):
                            mock_output_instance = Mock(verbosity=0, use_color=True)
                            mock_output.return_value = mock_output_instance
                            mock_config.return_value.ensure_directories = Mock()

                            main()

                            assert mock_output_instance.use_color is False


class TestConfigCommand:
    """Test config command routing and execution."""

    def test_config_command_calls_config_commands(self):
        """Test that 'config' command routes to ConfigCommands."""
        with patch("sys.argv", ["agent-manager", "config", "where"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.ConfigCommands.process_cli_command") as mock_process:
                    with patch("agent_manager.agent_manager.get_output"):
                        mock_config.return_value.ensure_directories = Mock()

                        main()

                        mock_process.assert_called_once()
                        args, config = mock_process.call_args[0]
                        assert args.command == "config"
                        assert args.config_command == "where"

    def test_config_init_command(self):
        """Test config init command."""
        with patch("sys.argv", ["agent-manager", "config", "init"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.ConfigCommands.process_cli_command") as mock_process:
                    with patch("agent_manager.agent_manager.get_output"):
                        mock_config.return_value.ensure_directories = Mock()

                        main()

                        assert mock_process.called
                        args = mock_process.call_args[0][0]
                        assert args.config_command == "init"

    def test_config_show_command(self):
        """Test config show command."""
        with patch("sys.argv", ["agent-manager", "config", "show"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.ConfigCommands.process_cli_command") as mock_process:
                    with patch("agent_manager.agent_manager.get_output"):
                        mock_config.return_value.ensure_directories = Mock()

                        main()

                        assert mock_process.called
                        args = mock_process.call_args[0][0]
                        assert args.config_command == "show"

    def test_config_defaults_command(self):
        """Test config defaults command with parameters."""
        with patch("sys.argv", ["agent-manager", "config", "defaults", "--repos", "org", "personal"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.ConfigCommands.process_cli_command") as mock_process:
                    with patch("agent_manager.agent_manager.get_output"):
                        mock_config.return_value.ensure_directories = Mock()

                        main()

                        assert mock_process.called
                        args = mock_process.call_args[0][0]
                        assert args.config_command == "defaults"
                        assert args.repos == ["org", "personal"]

    def test_config_command_early_return(self):
        """Test that config command returns early without initializing repos."""
        with patch("sys.argv", ["agent-manager", "config", "where"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.ConfigCommands.process_cli_command"):
                    with patch("agent_manager.agent_manager.get_output"):
                        mock_config_instance = Mock()
                        mock_config.return_value = mock_config_instance

                        main()

                        # Should not call initialize or read
                        mock_config_instance.initialize.assert_not_called()
                        mock_config_instance.read.assert_not_called()


class TestMergersCommand:
    """Test mergers command routing and execution."""

    def test_mergers_list_command(self):
        """Test mergers list command."""
        with patch("sys.argv", ["agent-manager", "mergers", "list"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.create_default_merger_registry") as mock_registry:
                    with patch(
                        "agent_manager.cli_extensions.merger_commands.MergerCommands.process_cli_command"
                    ) as mock_process:
                        with patch("agent_manager.agent_manager.get_output"):
                            mock_config.return_value.ensure_directories = Mock()

                            main()

                            mock_registry.assert_called_once()
                            mock_process.assert_called_once()
                            args = mock_process.call_args[0][0]
                            assert args.mergers_command == "list"

    def test_mergers_show_command(self):
        """Test mergers show command."""
        with patch("sys.argv", ["agent-manager", "mergers", "show", "JsonMerger"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.create_default_merger_registry"):
                    with patch(
                        "agent_manager.cli_extensions.merger_commands.MergerCommands.process_cli_command"
                    ) as mock_process:
                        with patch("agent_manager.agent_manager.get_output"):
                            mock_config.return_value.ensure_directories = Mock()

                            main()

                            args = mock_process.call_args[0][0]
                            assert args.mergers_command == "show"
                            assert args.name == "JsonMerger"

    def test_mergers_command_early_return(self):
        """Test that mergers command returns early without repo operations."""
        with patch("sys.argv", ["agent-manager", "mergers", "list"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.create_default_merger_registry"):
                    with patch("agent_manager.cli_extensions.merger_commands.MergerCommands.process_cli_command"):
                        with patch("agent_manager.agent_manager.get_output"):
                            with patch("agent_manager.agent_manager.update_repositories") as mock_update:
                                mock_config.return_value.ensure_directories = Mock()

                                main()

                                # Should not call update_repositories
                                mock_update.assert_not_called()


class TestUpdateCommand:
    """Test update command execution."""

    def test_update_command_updates_repositories(self):
        """Test update command updates all repositories."""
        mock_config_data = {
            "hierarchy": [
                {
                    "name": "org",
                    "url": "https://github.com/org/repo",
                    "repo_type": "git",
                    "repo": Mock(),
                }
            ]
        }

        with patch("sys.argv", ["agent-manager", "update"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.update_repositories") as mock_update:
                    with patch("agent_manager.agent_manager.get_output"):
                        mock_config_instance = Mock()
                        mock_config.return_value = mock_config_instance
                        mock_config_instance.initialize = Mock()
                        mock_config_instance.read.return_value = mock_config_data

                        main()

                        mock_update.assert_called_once()
                        assert mock_update.call_args[0][0] == mock_config_data
                        assert mock_update.call_args[1]["force"] is False

    def test_update_command_with_force_flag(self):
        """Test update command with --force flag."""
        mock_config_data = {"hierarchy": []}

        with patch("sys.argv", ["agent-manager", "update", "--force"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.update_repositories") as mock_update:
                    with patch("agent_manager.agent_manager.get_output"):
                        mock_config_instance = Mock()
                        mock_config.return_value = mock_config_instance
                        mock_config_instance.read.return_value = mock_config_data

                        main()

                        assert mock_update.call_args[1]["force"] is True

    def test_update_command_returns_after_update(self):
        """Test that update command returns after updating repos."""
        with patch("sys.argv", ["agent-manager", "update"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.update_repositories"):
                    with patch("agent_manager.agent_manager.AgentCommands.process_cli_command") as mock_agent:
                        with patch("agent_manager.agent_manager.get_output"):
                            mock_config.return_value.read.return_value = {"hierarchy": []}

                            main()

                            # Should not call agent commands
                            mock_agent.assert_not_called()


class TestNoCommand:
    """Test cases for running with no command."""

    def test_no_command_shows_help(self, capsys):
        """Test that running with no command shows help and exits cleanly."""
        with patch("sys.argv", ["agent-manager"]), patch("agent_manager.agent_manager.Config") as mock_config:
            with patch("agent_manager.agent_manager.get_output"):
                mock_config.return_value.ensure_directories = Mock()

                main()

                # Should show help message
                captured = capsys.readouterr()
                assert "usage:" in captured.out or "agent-manager" in captured.out

    def test_no_command_does_not_call_process_cli(self):
        """Test that running with no command doesn't call agent processing."""
        with patch("sys.argv", ["agent-manager"]), patch("agent_manager.agent_manager.Config") as mock_config:
            with patch("agent_manager.agent_manager.AgentCommands.process_cli_command") as mock_process:
                with patch("agent_manager.agent_manager.get_output"):
                    mock_config.return_value.ensure_directories = Mock()

                    main()

                    # Should NOT call process_cli_command
                    mock_process.assert_not_called()


class TestRunCommand:
    """Test run command execution."""

    def test_run_command_explicit(self):
        """Test that run command must be explicitly specified."""
        mock_config_data = {"hierarchy": []}

        with patch("sys.argv", ["agent-manager", "run"]), patch("agent_manager.agent_manager.Config") as mock_config:
            with patch("agent_manager.agent_manager.update_repositories"):
                with patch("agent_manager.cli_extensions.agent_commands.get_agent_names", return_value=[]):
                    with patch("agent_manager.agent_manager.AgentCommands.process_cli_command") as mock_agent:
                        with patch("agent_manager.agent_manager.get_output"):
                            mock_config_instance = Mock()
                            mock_config.return_value = mock_config_instance
                            mock_config_instance.read.return_value = mock_config_data
                            # Mock initialize to avoid interactive prompts
                            mock_config_instance.initialize = Mock()

                            main()

                            mock_agent.assert_called_once()

    def test_run_command_with_all_flag(self):
        """Test run command with --all flag."""
        mock_config_data = {"hierarchy": []}

        with patch("sys.argv", ["agent-manager", "run", "--all"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.update_repositories"):
                    with patch("agent_manager.agent_manager.AgentCommands.process_cli_command") as mock_agent:
                        with patch("agent_manager.cli_extensions.agent_commands.get_agent_names", return_value=[]):
                            with patch("agent_manager.agent_manager.get_output"):
                                mock_config.return_value.read.return_value = mock_config_data

                                main()

                                args = mock_agent.call_args[0][0]
                                assert args.run_all is True

    def test_run_updates_repos_before_running_agents(self):
        """Test that repositories are updated before running agents."""
        mock_config_data = {"hierarchy": []}
        call_order = []

        def track_update(*args, **kwargs):
            call_order.append("update")

        def track_agent(*args, **kwargs):
            call_order.append("agent")

        with patch("sys.argv", ["agent-manager", "run"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.update_repositories", side_effect=track_update):
                    with patch(
                        "agent_manager.agent_manager.AgentCommands.process_cli_command", side_effect=track_agent
                    ):
                        with patch("agent_manager.agent_manager.get_output"):
                            mock_config.return_value.read.return_value = mock_config_data

                            main()

                            assert call_order == ["update", "agent"]


class TestConfigInitialization:
    """Test configuration initialization workflow."""

    def test_config_directories_ensured(self):
        """Test that config directories are ensured on startup."""
        with patch("sys.argv", ["agent-manager", "config", "where"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.ConfigCommands.process_cli_command"):
                    with patch("agent_manager.agent_manager.get_output"):
                        mock_config_instance = Mock()
                        mock_config.return_value = mock_config_instance

                        main()

                        mock_config_instance.ensure_directories.assert_called_once()

    def test_config_initialize_skipped_if_exists(self):
        """Test that initialization is skipped if config already exists."""
        mock_config_data = {"hierarchy": []}

        with patch("sys.argv", ["agent-manager", "run"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.update_repositories"):
                    with patch("agent_manager.agent_manager.AgentCommands.process_cli_command"):
                        with patch("agent_manager.agent_manager.get_output"):
                            mock_config_instance = Mock()
                            mock_config.return_value = mock_config_instance
                            mock_config_instance.read.return_value = mock_config_data

                            main()

                            # initialize should be called with skip_if_already_created=True
                            mock_config_instance.initialize.assert_called_once_with(skip_if_already_created=True)

    def test_config_read_called_for_run_command(self):
        """Test that config.read() is called for run/update commands."""
        mock_config_data = {"hierarchy": []}

        with patch("sys.argv", ["agent-manager", "run"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.update_repositories"):
                    with patch("agent_manager.agent_manager.AgentCommands.process_cli_command"):
                        with patch("agent_manager.agent_manager.get_output"):
                            mock_config_instance = Mock()
                            mock_config.return_value = mock_config_instance
                            mock_config_instance.read.return_value = mock_config_data

                            main()

                            mock_config_instance.read.assert_called_once()


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_unknown_command_shows_help(self, capsys):
        """Test that unknown commands display help and exit."""
        with patch("sys.argv", ["agent-manager", "unknown-command"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.update_repositories"):
                    with patch("agent_manager.cli_extensions.agent_commands.get_agent_names", return_value=[]):
                        with patch("agent_manager.agent_manager.get_output"):
                            mock_config.return_value.read.return_value = {"hierarchy": []}

                            with pytest.raises(SystemExit) as exc_info:
                                main()

                            assert exc_info.value.code == 2  # argparse returns 2 for invalid arguments

    def test_config_read_failure_propagates(self):
        """Test that config read failures propagate correctly."""
        with patch("sys.argv", ["agent-manager", "run"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.get_output"):
                    mock_config_instance = Mock()
                    mock_config.return_value = mock_config_instance
                    mock_config_instance.read.side_effect = SystemExit(1)

                    with pytest.raises(SystemExit) as exc_info:
                        main()

                    assert exc_info.value.code == 1


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_run_workflow(self):
        """Test complete run workflow from start to finish."""
        mock_config_data = {
            "hierarchy": [
                {
                    "name": "org",
                    "url": "https://github.com/test/org",
                    "repo_type": "git",
                    "repo": Mock(),
                },
                {
                    "name": "personal",
                    "url": "file:///home/user/config",
                    "repo_type": "local",
                    "repo": Mock(),
                },
            ]
        }

        with patch("sys.argv", ["agent-manager", "-vv", "run", "--all"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.update_repositories") as mock_update:
                    with patch("agent_manager.agent_manager.AgentCommands.process_cli_command") as mock_agent:
                        with patch("agent_manager.cli_extensions.agent_commands.get_agent_names", return_value=[]):
                            with patch("agent_manager.agent_manager.get_output") as mock_output:
                                mock_output_instance = Mock(verbosity=0, use_color=True)
                                mock_output.return_value = mock_output_instance

                                mock_config_instance = Mock()
                                mock_config.return_value = mock_config_instance
                                mock_config_instance.read.return_value = mock_config_data

                                main()

                                # Verify full workflow
                                assert mock_output_instance.verbosity == 2
                                mock_config_instance.ensure_directories.assert_called_once()
                                mock_config_instance.initialize.assert_called_once_with(skip_if_already_created=True)
                                mock_config_instance.read.assert_called_once()
                                mock_update.assert_called_once_with(mock_config_data, force=False)
                                mock_agent.assert_called_once()

                            # Verify agent command args
                            args, config_data = mock_agent.call_args[0]
                            assert args.command == "run"
                            assert args.run_all is True
                            assert config_data == mock_config_data

    def test_config_command_workflow(self):
        """Test complete config management workflow."""
        with patch("sys.argv", ["agent-manager", "-v", "config", "show"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.ConfigCommands.process_cli_command") as mock_process:
                    with patch("agent_manager.agent_manager.get_output") as mock_output:
                        mock_output_instance = Mock(verbosity=0, use_color=True)
                        mock_output.return_value = mock_output_instance

                        mock_config_instance = Mock()
                        mock_config.return_value = mock_config_instance

                        main()

                        # Verify workflow
                        assert mock_output_instance.verbosity == 1
                        mock_config_instance.ensure_directories.assert_called_once()
                        mock_process.assert_called_once()

                        # Verify no repo operations
                        mock_config_instance.initialize.assert_not_called()
                        mock_config_instance.read.assert_not_called()

    def test_mergers_configuration_workflow(self):
        """Test complete mergers configuration workflow."""
        with patch("sys.argv", ["agent-manager", "mergers", "configure", "--merger", "JsonMerger"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.create_default_merger_registry") as mock_registry:
                    with patch(
                        "agent_manager.cli_extensions.merger_commands.MergerCommands.process_cli_command"
                    ) as mock_process:
                        with patch("agent_manager.agent_manager.get_output"):
                            mock_config_instance = Mock()
                            mock_config.return_value = mock_config_instance

                            main()

                            # Verify workflow
                            mock_config_instance.ensure_directories.assert_called_once()
                            mock_registry.assert_called_once()
                            mock_process.assert_called_once()

                            # Verify args
                            args = mock_process.call_args[0][0]
                            assert args.mergers_command == "configure"
                            assert args.merger == "JsonMerger"


class TestFullIntegration:
    """Full integration tests using test data and TestAgent."""

    @pytest.fixture
    def test_data_path(self):
        """Get the path to test data directory."""
        from pathlib import Path

        return Path(__file__).parent / "data"

    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """Create a temporary output directory for test agent."""
        return tmp_path / "test_agent_output"

    @pytest.fixture
    def mock_config_data(self, test_data_path, tmp_path):
        """Create mock configuration data using test data directories."""
        from agent_manager.plugins.repos.local_repo import LocalRepo

        # Create a temp repos directory
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir(parents=True, exist_ok=True)

        return {
            "repos": [
                {
                    "name": "organization",
                    "url": f"file://{test_data_path / 'org'}",
                    "repo_type": "local",
                    "repo": LocalRepo("organization", f"file://{test_data_path / 'org'}", repos_dir),
                },
                {
                    "name": "team",
                    "url": f"file://{test_data_path / 'team'}",
                    "repo_type": "local",
                    "repo": LocalRepo("team", f"file://{test_data_path / 'team'}", repos_dir),
                },
                {
                    "name": "personal",
                    "url": f"file://{test_data_path / 'personal'}",
                    "repo_type": "local",
                    "repo": LocalRepo("personal", f"file://{test_data_path / 'personal'}", repos_dir),
                },
            ]
        }

    def test_full_merge_integration(self, mock_config_data, temp_output_dir, test_data_path):
        """Test full integration: read config, merge files, write to TestAgent."""
        import json

        import yaml

        from agent_manager.plugins.agents.test_agent import TestAgent

        # Create TestAgent with temp directory as the base
        test_agent = TestAgent(temp_dir=temp_output_dir)

        # V2: pass repos list and base_directory
        test_agent.update(mock_config_data["repos"], base_directory=temp_output_dir)

        # Verify the output directory was created
        output_dir = temp_output_dir / ".testagent"
        assert output_dir.exists()

        # Verify merged files exist (under .testagent subdirectory)
        merged_cursorrules = output_dir / ".cursorrules"
        merged_mcp = output_dir / "mcp.json"
        merged_settings = output_dir / "settings.yaml"

        assert merged_cursorrules.exists(), "Merged .cursorrules should exist"
        assert merged_mcp.exists(), "Merged mcp.json should exist"
        assert merged_settings.exists(), "Merged settings.yaml should exist"

        # Verify .cursorrules content (text merger should concatenate)
        cursorrules_content = merged_cursorrules.read_text()
        assert "Personal Preferences - John's Setup" in cursorrules_content

        # Verify mcp.json deep merge (JSON merger)
        mcp_data = json.loads(merged_mcp.read_text())
        assert "company-docs" in mcp_data["mcpServers"]
        assert "jira" in mcp_data["mcpServers"]
        assert "postgres" in mcp_data["mcpServers"]
        assert "redis" in mcp_data["mcpServers"]
        assert "aws" in mcp_data["mcpServers"]
        assert "filesystem" in mcp_data["mcpServers"]
        assert "git" in mcp_data["mcpServers"]
        assert "localhost" in mcp_data["mcpServers"]
        assert "postgres-local" in mcp_data["mcpServers"]

        # Verify settings.yaml deep merge with overrides (YAML merger)
        settings_data = yaml.safe_load(merged_settings.read_text())
        assert settings_data["python"]["testing"]["min_coverage"] == 90
        assert "team" in settings_data
        assert settings_data["team"]["name"] == "Backend Engineering"
        assert "organization" in settings_data
        assert settings_data["organization"]["name"] == "ACME Corp"

        # Clean up
        test_agent.cleanup()

    def test_run_command_flow(self, mock_config_data, temp_output_dir):
        """Test the run command flow through the CLI."""

        with patch("sys.argv", ["agent-manager", "run"]):
            with patch("agent_manager.agent_manager.Config") as mock_config:
                with patch("agent_manager.agent_manager.AgentCommands.process_cli_command") as mock_agent_cmd:
                    with patch("agent_manager.agent_manager.update_repositories") as mock_update:
                        # Setup mocks
                        mock_config_instance = Mock()
                        mock_config.return_value = mock_config_instance
                        mock_config_instance.ensure_directories = Mock()
                        mock_config_instance.initialize = Mock()
                        mock_config_instance.read.return_value = mock_config_data

                        # Run main
                        main()

                        # Verify the flow
                        mock_config_instance.ensure_directories.assert_called_once()
                        mock_config_instance.initialize.assert_called_once_with(skip_if_already_created=True)
                        mock_config_instance.read.assert_called_once()
                        mock_update.assert_called_once()
                        mock_agent_cmd.assert_called_once()

    def test_agent_import(self):
        """Test that TestAgent can be imported and instantiated."""
        from agent_manager.plugins.agents.test_agent import TestAgent

        agent = TestAgent()
        assert agent is not None
        assert hasattr(agent, "update")
        assert hasattr(agent, "agent_subdirectory")

        agent.cleanup()

    def test_test_agent_initialization(self):
        """Test TestAgent initialization and cleanup."""
        from pathlib import Path

        from agent_manager.plugins.agents.test_agent import TestAgent

        # Test with auto-generated temp dir
        agent = TestAgent()
        base = agent.get_base_directory()
        assert base.exists()

        agent.cleanup()
        assert not base.exists()

        # Test with provided temp dir
        from tempfile import mkdtemp

        custom_temp = Path(mkdtemp())
        agent2 = TestAgent(temp_dir=custom_temp)
        assert agent2.get_base_directory() == custom_temp

        import shutil

        shutil.rmtree(custom_temp)
