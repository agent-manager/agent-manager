"""Tests for cli_extensions/repo_commands.py - Repository CLI commands."""

from unittest.mock import Mock

from agent_manager.cli_extensions.repo_commands import RepoCommands


class TestRepoCommandsAddCliArguments:
    """Test cases for add_cli_arguments method."""

    def test_adds_update_parser(self):
        """Test that add_cli_arguments adds update parser."""
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_subparsers.add_parser.return_value = mock_parser

        RepoCommands.add_cli_arguments(mock_subparsers)

        mock_subparsers.add_parser.assert_called_once()
        call_args = mock_subparsers.add_parser.call_args
        assert call_args[0][0] == "update"
        assert "Update all repositories" in call_args[1]["help"]

    def test_adds_force_argument(self):
        """Test that update parser includes force argument."""
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_subparsers.add_parser.return_value = mock_parser

        RepoCommands.add_cli_arguments(mock_subparsers)

        # Verify force argument was added
        mock_parser.add_argument.assert_called_once()
        call_args = mock_parser.add_argument.call_args
        assert call_args[0][0] == "--force"
        assert call_args[1]["action"] == "store_true"


class TestRepoCommandsIntegration:
    """Integration tests for repo commands."""

    def test_add_and_process_workflow(self):
        """Test complete workflow of adding arguments and processing."""
        import argparse

        # Create parser
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        # Add arguments
        RepoCommands.add_cli_arguments(subparsers)

        # Parse update command
        args = parser.parse_args(["update"])
        assert args.command == "update"
        assert args.force is False

        # Parse update with force
        args = parser.parse_args(["update", "--force"])
        assert args.command == "update"
        assert args.force is True

    def test_full_command_flow(self):
        """Test full command flow from argparse to parsing."""
        import argparse

        # Set up parser
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        RepoCommands.add_cli_arguments(subparsers)

        # Parse and verify update command with force
        args = parser.parse_args(["update", "--force"])
        assert args.command == "update"
        assert args.force is True
