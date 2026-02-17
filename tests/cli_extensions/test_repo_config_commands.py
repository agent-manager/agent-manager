"""Tests for cli_extensions/repo_config_commands.py."""

from unittest.mock import Mock, patch

from agent_manager.cli_extensions.repo_config_commands import RepoConfigCommands


class TestRepoConfigAddCliArguments:

    def test_adds_repo_parser(self):
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_parser.add_subparsers.return_value = Mock()
        mock_subparsers.add_parser.return_value = mock_parser

        RepoConfigCommands.add_cli_arguments(mock_subparsers)

        calls = [c[0][0] for c in mock_subparsers.add_parser.call_args_list]
        assert "repo" in calls

    def test_adds_subcommands(self):
        mock_subparsers = Mock()
        mock_repo_parser = Mock()
        mock_repo_sub = Mock()
        mock_repo_parser.add_subparsers.return_value = mock_repo_sub

        mock_subparsers.add_parser.return_value = mock_repo_parser

        RepoConfigCommands.add_cli_arguments(mock_subparsers)

        calls = [c[0][0] for c in mock_repo_sub.add_parser.call_args_list]
        assert "list" in calls
        assert "add" in calls
        assert "remove" in calls


class TestRepoConfigProcessCliCommand:

    def test_no_subcommand_shows_usage(self):
        args = Mock()
        args.repo_command = None
        config = Mock()
        messages = []

        with patch(
            "agent_manager.cli_extensions.repo_config_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            RepoConfigCommands.process_cli_command(args, config)

        output = "\n".join(messages)
        assert "Usage: agent-manager repo" in output

    def test_list_delegates(self):
        args = Mock()
        args.repo_command = "list"
        config = Mock()

        with patch.object(
            RepoConfigCommands, "list_repos",
        ) as mock_list:
            RepoConfigCommands.process_cli_command(args, config)
            mock_list.assert_called_once_with(config)

    def test_add_delegates(self):
        args = Mock()
        args.repo_command = "add"
        args.name = "personal"
        args.url = "file:///tmp/personal"
        args.repo_type = "file"

        config = Mock()

        RepoConfigCommands.process_cli_command(args, config)

        config.add_repo.assert_called_once_with(
            "personal", "file:///tmp/personal", repo_type="file",
        )

    def test_add_auto_detect_type(self):
        args = Mock()
        args.repo_command = "add"
        args.name = "org"
        args.url = "https://github.com/org/repo.git"
        args.repo_type = None

        config = Mock()

        RepoConfigCommands.process_cli_command(args, config)

        config.add_repo.assert_called_once_with(
            "org", "https://github.com/org/repo.git", repo_type=None,
        )

    def test_remove_delegates(self):
        args = Mock()
        args.repo_command = "remove"
        args.name = "personal"
        args.force = False

        config = Mock()

        RepoConfigCommands.process_cli_command(args, config)

        config.remove_repo.assert_called_once_with("personal", force=False)

    def test_remove_with_force(self):
        args = Mock()
        args.repo_command = "remove"
        args.name = "personal"
        args.force = True

        config = Mock()

        RepoConfigCommands.process_cli_command(args, config)

        config.remove_repo.assert_called_once_with("personal", force=True)


class TestRepoConfigListRepos:

    def test_no_config(self):
        config = Mock()
        config.exists.return_value = False
        messages = []

        with patch(
            "agent_manager.cli_extensions.repo_config_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            RepoConfigCommands.list_repos(config)

        output = "\n".join(messages)
        assert "No configuration found" in output

    def test_empty_repos(self):
        config = Mock()
        config.exists.return_value = True
        config.read.return_value = {"repos": []}
        messages = []

        with patch(
            "agent_manager.cli_extensions.repo_config_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            RepoConfigCommands.list_repos(config)

        output = "\n".join(messages)
        assert "No repos configured" in output

    def test_lists_repos(self):
        config = Mock()
        config.exists.return_value = True
        config.read.return_value = {
            "repos": [
                {
                    "name": "org",
                    "url": "https://github.com/org/repo.git",
                    "repo_type": "git",
                },
                {
                    "name": "personal",
                    "url": "file:///tmp/personal",
                    "repo_type": "file",
                },
            ],
        }
        messages = []

        with patch(
            "agent_manager.cli_extensions.repo_config_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            RepoConfigCommands.list_repos(config)

        output = "\n".join(messages)
        assert "org (git)" in output
        assert "personal (file)" in output
        assert "Total: 2 repo(s)" in output
