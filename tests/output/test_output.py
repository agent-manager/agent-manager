"""Tests for output/output.py - Output and logging utilities."""

from agent_manager.output import Color, MessageType, OutputManager, VerbosityLevel, message


class TestVerbosityLevel:
    """Test cases for VerbosityLevel enum."""

    def test_always_level_is_zero(self):
        """Test that ALWAYS level is 0 (always shown)."""
        assert VerbosityLevel.ALWAYS == 0

    def test_verbose_level_is_one(self):
        """Test that VERBOSE level is 1 (-v)."""
        assert VerbosityLevel.VERBOSE == 1

    def test_extra_verbose_level_is_two(self):
        """Test that EXTRA_VERBOSE level is 2 (-vv)."""
        assert VerbosityLevel.EXTRA_VERBOSE == 2

    def test_debug_level_is_three(self):
        """Test that DEBUG level is 3 (-vvv)."""
        assert VerbosityLevel.DEBUG == 3

    def test_levels_are_ordered(self):
        """Test that verbosity levels are properly ordered."""
        assert VerbosityLevel.ALWAYS < VerbosityLevel.VERBOSE
        assert VerbosityLevel.VERBOSE < VerbosityLevel.EXTRA_VERBOSE
        assert VerbosityLevel.EXTRA_VERBOSE < VerbosityLevel.DEBUG


class TestMessageType:
    """Test cases for MessageType enum."""

    def test_normal_type_is_zero(self):
        """Test that NORMAL type is 0."""
        assert MessageType.NORMAL == 0

    def test_success_type_is_one(self):
        """Test that SUCCESS type is 1."""
        assert MessageType.SUCCESS == 1

    def test_error_type_is_two(self):
        """Test that ERROR type is 2."""
        assert MessageType.ERROR == 2


class TestColor:
    """Test cases for Color class."""

    def test_basic_colors_defined(self):
        """Test that basic ANSI color codes are defined."""
        assert Color.RED.startswith("\033[")
        assert Color.GREEN.startswith("\033[")
        assert Color.YELLOW.startswith("\033[")

    def test_semantic_aliases(self):
        """Test that semantic aliases point to correct colors."""
        assert Color.ERROR == Color.RED
        assert Color.WARNING == Color.YELLOW
        assert Color.SUCCESS == Color.GREEN


class TestOutputManager:
    """Test cases for OutputManager."""

    def test_message_with_normal_type(self, capsys):
        """Test message with NORMAL type (no color, no prefix)."""
        manager = OutputManager(verbosity=0, use_color=False)
        manager.message("Test message", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        captured = capsys.readouterr()
        assert "Test message" in captured.out
        assert "Error:" not in captured.out

    def test_message_with_error_type(self):
        """Test message with ERROR type (red, Error: prefix, goes to stderr)."""
        import io
        from unittest.mock import patch

        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            manager = OutputManager(verbosity=0, use_color=False)
            manager.message("Something failed", MessageType.ERROR, VerbosityLevel.ALWAYS)

        # Errors go to stderr
        assert "Error: Something failed" in stderr.getvalue()

    def test_message_with_warning_type(self, capsys):
        """Test message with WARNING type (yellow, Warning: prefix)."""
        manager = OutputManager(verbosity=0, use_color=False)
        manager.message("Be careful", MessageType.WARNING, VerbosityLevel.ALWAYS)

        captured = capsys.readouterr()
        assert "Warning: Be careful" in captured.out

    def test_message_with_success_type(self, capsys):
        """Test message with SUCCESS type (green, no prefix)."""
        manager = OutputManager(verbosity=0, use_color=True, force_color=True)
        manager.message("Done", MessageType.SUCCESS, VerbosityLevel.ALWAYS)

        captured = capsys.readouterr()
        assert "Done" in captured.out
        assert Color.GREEN in captured.out

    def test_message_with_info_type(self, capsys):
        """Test message with INFO type (cyan, no prefix)."""
        manager = OutputManager(verbosity=2, use_color=True, force_color=True)
        manager.message("Information", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)

        captured = capsys.readouterr()
        assert "Information" in captured.out
        assert Color.CYAN in captured.out

    def test_message_with_debug_type(self, capsys):
        """Test message with DEBUG type (dim, DEBUG: prefix)."""
        manager = OutputManager(verbosity=3, use_color=False)
        manager.message("Debug info", MessageType.DEBUG, VerbosityLevel.DEBUG)

        captured = capsys.readouterr()
        assert "DEBUG: Debug info" in captured.out

    def test_message_respects_verbosity(self, capsys):
        """Test that messages respect verbosity requirements."""
        manager = OutputManager(verbosity=0, use_color=False)

        # Should show (ALWAYS)
        manager.message("Always shown", MessageType.NORMAL, VerbosityLevel.ALWAYS)

        # Should not show (requires VERBOSE)
        manager.message("Hidden", MessageType.INFO, VerbosityLevel.VERBOSE)

        captured = capsys.readouterr()
        assert "Always shown" in captured.out
        assert "Hidden" not in captured.out

    def test_verbosity_levels(self, capsys):
        """Test different verbosity levels."""
        # Level 0: Only ALWAYS
        manager = OutputManager(verbosity=0, use_color=False)
        manager.message("Level 0", MessageType.NORMAL, VerbosityLevel.ALWAYS)
        manager.message("Level 1", MessageType.INFO, VerbosityLevel.VERBOSE)

        captured = capsys.readouterr()
        assert "Level 0" in captured.out
        assert "Level 1" not in captured.out

        # Level 2: ALWAYS + VERBOSE + EXTRA_VERBOSE
        manager = OutputManager(verbosity=2, use_color=False)
        manager.message("Level 2a", MessageType.INFO, VerbosityLevel.EXTRA_VERBOSE)
        manager.message("Level 3", MessageType.DEBUG, VerbosityLevel.DEBUG)

        captured = capsys.readouterr()
        assert "Level 2a" in captured.out
        assert "Level 3" not in captured.out


class TestGlobalMessage:
    """Test cases for global message function."""

    def test_global_message_function(self, capsys):
        """Test global message() function."""
        message("Test message")

        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_global_message_with_type(self, capsys):
        """Test global message() with message type."""
        message("Success message", MessageType.SUCCESS)

        captured = capsys.readouterr()
        assert "Success message" in captured.out

    def test_global_message_with_verbosity(self, capsys):
        """Test global message() with verbosity level."""
        from agent_manager.output import get_output

        mgr = get_output()
        original_verbosity = mgr.verbosity
        mgr.verbosity = 0

        # Should not show (requires VERBOSE)
        message("Hidden", MessageType.INFO, VerbosityLevel.VERBOSE)

        captured = capsys.readouterr()
        assert "Hidden" not in captured.out

        mgr.verbosity = original_verbosity
