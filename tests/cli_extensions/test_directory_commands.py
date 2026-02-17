"""Tests for cli_extensions/directory_commands.py."""

from unittest.mock import Mock, patch

from agent_manager.cli_extensions.directory_commands import DirectoryCommands


class TestDirectoryAddCliArguments:

    def test_adds_directory_parser(self):
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_parser.add_subparsers.return_value = Mock()
        mock_subparsers.add_parser.return_value = mock_parser

        DirectoryCommands.add_cli_arguments(mock_subparsers)

        calls = [c[0][0] for c in mock_subparsers.add_parser.call_args_list]
        assert "directory" in calls

    def test_adds_subcommands(self):
        mock_subparsers = Mock()
        mock_dir_parser = Mock()
        mock_dir_sub = Mock()
        mock_dir_parser.add_subparsers.return_value = mock_dir_sub
        mock_subparsers.add_parser.return_value = mock_dir_parser

        DirectoryCommands.add_cli_arguments(mock_subparsers)

        calls = [c[0][0] for c in mock_dir_sub.add_parser.call_args_list]
        assert "list" in calls
        assert "add" in calls
        assert "remove" in calls


class TestDirectoryProcessCliCommand:

    def test_no_subcommand_shows_usage(self):
        args = Mock()
        args.directory_command = None
        config = Mock()
        messages = []

        with patch(
            "agent_manager.cli_extensions.directory_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            DirectoryCommands.process_cli_command(args, config)

        output = "\n".join(messages)
        assert "Usage: agent-manager directory" in output

    def test_list_delegates(self):
        args = Mock()
        args.directory_command = "list"
        config = Mock()

        with patch.object(
            DirectoryCommands, "list_directories",
        ) as mock_list:
            DirectoryCommands.process_cli_command(args, config)
            mock_list.assert_called_once_with(config)

    def test_add_delegates(self):
        args = Mock()
        args.directory_command = "add"
        args.path = "HOME/GIT/project"
        args.dir_type = "git"
        args.agents = ["cursor"]
        args.hierarchy = ["personal"]

        config = Mock()

        with patch.object(
            DirectoryCommands, "add_directory",
        ) as mock_add:
            DirectoryCommands.process_cli_command(args, config)
            mock_add.assert_called_once_with(args, config)

    def test_remove_delegates(self):
        args = Mock()
        args.directory_command = "remove"
        args.path = "HOME/GIT/project"

        config = Mock()

        DirectoryCommands.process_cli_command(args, config)
        config.remove_directory.assert_called_once_with(
            "HOME/GIT/project",
        )


class TestDirectoryListDirectories:

    def test_no_config(self):
        config = Mock()
        config.exists.return_value = False
        messages = []

        with patch(
            "agent_manager.cli_extensions.directory_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            DirectoryCommands.list_directories(config)

        output = "\n".join(messages)
        assert "No configuration found" in output

    def test_empty_directories(self):
        config = Mock()
        config.exists.return_value = True
        config.read.return_value = {"repos": [], "directories": {}}
        messages = []

        with patch(
            "agent_manager.cli_extensions.directory_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            DirectoryCommands.list_directories(config)

        output = "\n".join(messages)
        assert "No directories configured" in output

    @patch(
        "agent_manager.cli_extensions.directory_commands.read_manifest",
    )
    @patch(
        "agent_manager.cli_extensions.directory_commands"
        ".AbstractRepo.detect_directory",
    )
    def test_lists_directories_with_manifest(
        self, mock_detect, mock_manifest,
    ):
        mock_detect.return_value = "git"
        mock_manifest.return_value = {
            "last_synced": "2026-02-13T15:30:00",
            "files": [
                {"name": ".cursor/rules/test.md", "agents": ["cursor"]},
            ],
        }

        config = Mock()
        config.exists.return_value = True
        config.read.return_value = {
            "repos": [],
            "directories": {
                "HOME/GIT/project": {
                    "type": "git",
                    "agents": ["cursor"],
                    "hierarchy": ["org", "personal"],
                },
            },
        }
        messages = []

        with patch(
            "agent_manager.cli_extensions.directory_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            DirectoryCommands.list_directories(config)

        output = "\n".join(messages)
        assert "HOME/GIT/project" in output
        assert "git" in output
        assert "cursor" in output
        assert "org -> personal" in output
        assert "1 managed files" in output

    @patch(
        "agent_manager.cli_extensions.directory_commands.read_manifest",
    )
    @patch(
        "agent_manager.cli_extensions.directory_commands"
        ".AbstractRepo.detect_directory",
    )
    def test_handles_none_dir_config(
        self, mock_detect, mock_manifest,
    ):
        """Directories with None config should display defaults."""
        mock_detect.return_value = "file"
        mock_manifest.return_value = {"files": []}

        config = Mock()
        config.exists.return_value = True
        config.read.return_value = {
            "repos": [],
            "directories": {"HOME": None},
        }
        messages = []

        with patch(
            "agent_manager.cli_extensions.directory_commands.message",
            side_effect=lambda t, *a, **kw: messages.append(t),
        ):
            DirectoryCommands.list_directories(config)

        output = "\n".join(messages)
        assert "HOME" in output
        assert "(defaults)" in output


class TestDirectoryAddDirectory:

    @patch(
        "agent_manager.cli_extensions.directory_commands"
        ".AbstractRepo.detect_directory",
    )
    def test_add_with_auto_detect(self, mock_detect):
        mock_detect.return_value = "git"

        args = Mock()
        args.path = "HOME/GIT/project"
        args.dir_type = None
        args.agents = None
        args.hierarchy = None

        config = Mock()

        with patch(
            "agent_manager.cli_extensions.directory_commands.message",
        ):
            DirectoryCommands.add_directory(args, config)

        config.add_directory.assert_called_once_with(
            "HOME/GIT/project",
            dir_type="git",
            agents=None,
            hierarchy=None,
        )

    def test_add_with_explicit_type(self):
        args = Mock()
        args.path = "HOME"
        args.dir_type = "local"
        args.agents = ["cursor", "claude"]
        args.hierarchy = None

        config = Mock()

        DirectoryCommands.add_directory(args, config)

        config.add_directory.assert_called_once_with(
            "HOME",
            dir_type="local",
            agents=["cursor", "claude"],
            hierarchy=None,
        )
