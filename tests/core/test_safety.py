"""Tests for core/safety.py - Clobber detection and type validation."""

from pathlib import Path
from unittest.mock import Mock, patch

from agent_manager.core.safety import (
    ClobberAction,
    TypeValidation,
    check_clobber,
    should_proceed_on_type_mismatch,
    should_write_file,
    validate_directory_type,
)


# ===========================================================================
# ClobberAction
# ===========================================================================
class TestClobberAction:

    def test_safe_is_safe(self):
        a = ClobberAction(ClobberAction.SAFE, "f.txt")
        assert a.is_safe

    def test_new_file_is_safe(self):
        a = ClobberAction(ClobberAction.NEW_FILE, "f.txt")
        assert a.is_safe

    def test_clobber_recoverable_not_safe(self):
        a = ClobberAction(ClobberAction.CLOBBER_RECOVERABLE, "f.txt")
        assert not a.is_safe

    def test_clobber_risky_not_safe(self):
        a = ClobberAction(ClobberAction.CLOBBER_RISKY, "f.txt")
        assert not a.is_safe

    def test_repr(self):
        a = ClobberAction(ClobberAction.SAFE, "f.txt", "reason")
        assert "SAFE" not in repr(a) or "safe" in repr(a)


# ===========================================================================
# check_clobber
# ===========================================================================
class TestCheckClobber:

    def test_managed_file_is_safe(self, tmp_path):
        manifest = {"files": [{"name": "x.txt", "agents": ["a"], "hash": "h"}]}
        result = check_clobber("x.txt", tmp_path, manifest)
        assert result.action == ClobberAction.SAFE

    def test_new_file_is_new(self, tmp_path):
        manifest = {"files": []}
        result = check_clobber("new.txt", tmp_path, manifest)
        assert result.action == ClobberAction.NEW_FILE

    def test_unmanaged_existing_recoverable(self, tmp_path):
        (tmp_path / "exist.txt").write_text("x")
        manifest = {"files": []}
        repo = Mock()
        repo.safe_to_overwrite.return_value = True

        result = check_clobber("exist.txt", tmp_path, manifest, repo)
        assert result.action == ClobberAction.CLOBBER_RECOVERABLE

    def test_unmanaged_existing_risky(self, tmp_path):
        (tmp_path / "exist.txt").write_text("x")
        manifest = {"files": []}
        repo = Mock()
        repo.safe_to_overwrite.return_value = False

        result = check_clobber("exist.txt", tmp_path, manifest, repo)
        assert result.action == ClobberAction.CLOBBER_RISKY

    def test_unmanaged_existing_no_repo(self, tmp_path):
        (tmp_path / "exist.txt").write_text("x")
        manifest = {"files": []}

        result = check_clobber("exist.txt", tmp_path, manifest)
        assert result.action == ClobberAction.CLOBBER_RISKY


# ===========================================================================
# should_write_file
# ===========================================================================
class TestShouldWriteFile:

    def test_safe_always_writes(self):
        c = ClobberAction(ClobberAction.SAFE, "f.txt")
        assert should_write_file(c) is True
        assert should_write_file(c, force=True) is True
        assert should_write_file(c, non_interactive=True) is True

    def test_new_always_writes(self):
        c = ClobberAction(ClobberAction.NEW_FILE, "f.txt")
        assert should_write_file(c) is True

    def test_recoverable_with_force(self):
        c = ClobberAction(ClobberAction.CLOBBER_RECOVERABLE, "f.txt")
        with patch("agent_manager.core.safety.message"):
            assert should_write_file(c, force=True) is True

    def test_recoverable_without_force(self):
        c = ClobberAction(ClobberAction.CLOBBER_RECOVERABLE, "f.txt")
        with patch("agent_manager.core.safety.message"):
            assert should_write_file(c) is False

    def test_risky_with_force(self):
        c = ClobberAction(ClobberAction.CLOBBER_RISKY, "f.txt")
        with patch("agent_manager.core.safety.message"):
            assert should_write_file(c, force=True) is True

    def test_risky_without_force(self):
        c = ClobberAction(ClobberAction.CLOBBER_RISKY, "f.txt")
        with patch("agent_manager.core.safety.message"):
            assert should_write_file(c) is False

    def test_risky_non_interactive_without_force(self):
        c = ClobberAction(ClobberAction.CLOBBER_RISKY, "f.txt")
        with patch("agent_manager.core.safety.message"):
            assert should_write_file(c, non_interactive=True) is False

    def test_risky_force_and_non_interactive(self):
        c = ClobberAction(ClobberAction.CLOBBER_RISKY, "f.txt")
        with patch("agent_manager.core.safety.message"):
            assert should_write_file(
                c, force=True, non_interactive=True,
            ) is True

    def test_clobber_always_logs(self):
        c = ClobberAction(ClobberAction.CLOBBER_RISKY, "f.txt")
        with patch("agent_manager.core.safety.message") as mock_msg:
            should_write_file(c)
            mock_msg.assert_called()

    def test_force_clobber_logs(self):
        c = ClobberAction(ClobberAction.CLOBBER_RISKY, "f.txt")
        with patch("agent_manager.core.safety.message") as mock_msg:
            should_write_file(c, force=True)
            mock_msg.assert_called()


# ===========================================================================
# TypeValidation
# ===========================================================================
class TestTypeValidation:

    def test_match_is_ok(self):
        v = TypeValidation(TypeValidation.MATCH, "git", "git")
        assert v.ok

    def test_no_config_is_ok(self):
        v = TypeValidation(TypeValidation.NO_CONFIG, detected="git")
        assert v.ok

    def test_mismatch_not_ok(self):
        v = TypeValidation(TypeValidation.MISMATCH, "git", "file")
        assert not v.ok

    def test_not_exists_not_ok(self):
        v = TypeValidation(TypeValidation.NOT_EXISTS)
        assert not v.ok


# ===========================================================================
# validate_directory_type
# ===========================================================================
class TestValidateDirectoryType:

    def test_directory_not_exists(self, tmp_path):
        result = validate_directory_type(tmp_path / "nope", "git")
        assert result.result == TypeValidation.NOT_EXISTS

    def test_no_configured_type(self, tmp_path):
        d = tmp_path / "dir"
        d.mkdir()
        result = validate_directory_type(d, None)
        assert result.result == TypeValidation.NO_CONFIG
        assert result.detected == "file"

    def test_matching_type(self, tmp_path):
        d = tmp_path / "dir"
        d.mkdir()
        (d / ".git").mkdir()
        result = validate_directory_type(d, "git")
        assert result.result == TypeValidation.MATCH

    def test_mismatched_type(self, tmp_path):
        d = tmp_path / "dir"
        d.mkdir()
        result = validate_directory_type(d, "git")
        assert result.result == TypeValidation.MISMATCH
        assert result.configured == "git"
        assert result.detected == "file"


# ===========================================================================
# should_proceed_on_type_mismatch
# ===========================================================================
class TestShouldProceedOnTypeMismatch:

    def test_match_proceeds(self):
        v = TypeValidation(TypeValidation.MATCH, "git", "git")
        assert should_proceed_on_type_mismatch(v) is True

    def test_no_config_proceeds(self):
        v = TypeValidation(TypeValidation.NO_CONFIG)
        assert should_proceed_on_type_mismatch(v) is True

    def test_not_exists_skips(self):
        v = TypeValidation(
            TypeValidation.NOT_EXISTS,
            message_text="gone",
        )
        with patch("agent_manager.core.safety.message"):
            assert should_proceed_on_type_mismatch(v) is False

    def test_mismatch_default_skips(self):
        v = TypeValidation(
            TypeValidation.MISMATCH, "git", "file",
            message_text="mismatch",
        )
        with patch("agent_manager.core.safety.message"):
            assert should_proceed_on_type_mismatch(v) is False

    def test_mismatch_force_proceeds(self):
        v = TypeValidation(
            TypeValidation.MISMATCH, "git", "file",
            message_text="mismatch",
        )
        with patch("agent_manager.core.safety.message"):
            assert should_proceed_on_type_mismatch(v, force=True) is True

    def test_mismatch_non_interactive_skips(self):
        v = TypeValidation(
            TypeValidation.MISMATCH, "git", "file",
            message_text="mismatch",
        )
        with patch("agent_manager.core.safety.message"):
            assert should_proceed_on_type_mismatch(
                v, non_interactive=True,
            ) is False

    def test_mismatch_force_and_non_interactive(self):
        v = TypeValidation(
            TypeValidation.MISMATCH, "git", "file",
            message_text="mismatch",
        )
        with patch("agent_manager.core.safety.message"):
            assert should_proceed_on_type_mismatch(
                v, force=True, non_interactive=True,
            ) is True
