"""Safety checks for file overwrites and directory type validation.

This module implements the clobber-detection and overwrite-protection
logic used by the main loop when writing merged files to target
directories.  It also validates the configured directory type against
the detected type at runtime.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_manager.core.manifest import is_managed
from agent_manager.output import MessageType, VerbosityLevel, message
from agent_manager.plugins.repos.abstract_repo import AbstractRepo


# ------------------------------------------------------------------
# Clobber detection
# ------------------------------------------------------------------
class ClobberAction:
    """Result of a clobber check for a single file."""

    SAFE = "safe"
    CLOBBER_RECOVERABLE = "clobber_recoverable"
    CLOBBER_RISKY = "clobber_risky"
    NEW_FILE = "new_file"

    def __init__(
        self,
        action: str,
        file_name: str,
        reason: str = "",
    ):
        self.action = action
        self.file_name = file_name
        self.reason = reason

    @property
    def is_safe(self) -> bool:
        return self.action in (self.SAFE, self.NEW_FILE)

    def __repr__(self) -> str:
        return (
            f"ClobberAction({self.action!r}, {self.file_name!r}, "
            f"{self.reason!r})"
        )


def check_clobber(
    file_name: str,
    base_directory: Path,
    manifest: dict[str, Any],
    repo: AbstractRepo | None = None,
) -> ClobberAction:
    """Determine the safety of writing a file.

    Decision tree:

    1. File in manifest? -> Safe (we wrote it last time)
    2. File doesn't exist on disk? -> New file (safe to create)
    3. File exists but NOT in manifest -> Clobber case:
       a. ``repo.safe_to_overwrite()`` True -> recoverable clobber
       b. Otherwise -> risky clobber

    Args:
        file_name: Relative path of the file to write
        base_directory: Target directory
        manifest: Current manifest data
        repo: Repo plugin for safe_to_overwrite check (optional)

    Returns:
        ClobberAction describing the result
    """
    if is_managed(manifest, file_name):
        return ClobberAction(
            ClobberAction.SAFE, file_name, "file tracked in manifest",
        )

    file_path = base_directory / file_name
    if not file_path.exists():
        return ClobberAction(
            ClobberAction.NEW_FILE, file_name, "file does not exist yet",
        )

    # File exists on disk but is NOT in the manifest
    if repo is not None and repo.safe_to_overwrite(file_path):
        return ClobberAction(
            ClobberAction.CLOBBER_RECOVERABLE,
            file_name,
            "file exists (unmanaged) but is recoverable via VCS",
        )

    return ClobberAction(
        ClobberAction.CLOBBER_RISKY,
        file_name,
        "file exists (unmanaged) and cannot be recovered",
    )


def should_write_file(
    clobber: ClobberAction,
    *,
    force: bool = False,
    non_interactive: bool = False,
) -> bool:
    """Decide whether to proceed with writing a file.

    Safe and new files are always written. For clobber cases:

    - ``--force``: always write, log warning
    - ``--non-interactive`` (without force): skip, log warning
    - Interactive (default): skip with warning (prompt planned for PR 7)

    Every clobber action is logged regardless of the decision.

    Args:
        clobber: ClobberAction from check_clobber
        force: Whether --force flag is active
        non_interactive: Whether --non-interactive flag is active

    Returns:
        True if the file should be written
    """
    if clobber.is_safe:
        return True

    # Always log the clobber event
    if clobber.action == ClobberAction.CLOBBER_RECOVERABLE:
        if force:
            message(
                f"WARNING: Overwriting unmanaged file: "
                f"{clobber.file_name} (--force, recoverable)",
                MessageType.WARNING,
                VerbosityLevel.ALWAYS,
            )
            return True

        message(
            f"WARNING: Skipped unmanaged file: "
            f"{clobber.file_name} (recoverable via VCS, "
            f"use --force to overwrite)",
            MessageType.WARNING,
            VerbosityLevel.ALWAYS,
        )
        return False

    # Risky clobber
    if force:
        message(
            f"WARNING: Overwriting unmanaged file: "
            f"{clobber.file_name} (--force, NOT recoverable)",
            MessageType.WARNING,
            VerbosityLevel.ALWAYS,
        )
        return True

    if non_interactive:
        message(
            f"WARNING: Skipped unmanaged file: "
            f"{clobber.file_name} (not recoverable, "
            f"use --force to overwrite)",
            MessageType.WARNING,
            VerbosityLevel.ALWAYS,
        )
        return False

    # Interactive mode: skip with warning (prompt will be added later)
    message(
        f"WARNING: Skipped unmanaged file: "
        f"{clobber.file_name} (not recoverable, "
        f"use --force to overwrite)",
        MessageType.WARNING,
        VerbosityLevel.ALWAYS,
    )
    return False


# ------------------------------------------------------------------
# Directory type validation
# ------------------------------------------------------------------
class TypeValidation:
    """Result of a directory type validation."""

    MATCH = "match"
    MISMATCH = "mismatch"
    NO_CONFIG = "no_config"
    NOT_EXISTS = "not_exists"

    def __init__(
        self,
        result: str,
        configured: str | None = None,
        detected: str | None = None,
        message_text: str = "",
    ):
        self.result = result
        self.configured = configured
        self.detected = detected
        self.message_text = message_text

    @property
    def ok(self) -> bool:
        return self.result in (self.MATCH, self.NO_CONFIG)

    def __repr__(self) -> str:
        return (
            f"TypeValidation({self.result!r}, "
            f"configured={self.configured!r}, "
            f"detected={self.detected!r})"
        )


def validate_directory_type(
    path: Path,
    configured_type: str | None,
) -> TypeValidation:
    """Compare configured directory type with what's on disk.

    Args:
        path: Directory to inspect
        configured_type: Type from config (e.g. ``"git"``, ``"file"``),
                        or None if not configured

    Returns:
        TypeValidation result
    """
    if not path.exists():
        return TypeValidation(
            TypeValidation.NOT_EXISTS,
            configured=configured_type,
            message_text=f"Directory does not exist: {path}",
        )

    detected = AbstractRepo.detect_directory(path)

    if configured_type is None:
        return TypeValidation(
            TypeValidation.NO_CONFIG,
            detected=detected,
            message_text="No type configured; detected as "
            f"'{detected}'",
        )

    if configured_type == detected:
        return TypeValidation(
            TypeValidation.MATCH,
            configured=configured_type,
            detected=detected,
        )

    return TypeValidation(
        TypeValidation.MISMATCH,
        configured=configured_type,
        detected=detected,
        message_text=(
            f"Directory '{path}' type mismatch: "
            f"configured as '{configured_type}', "
            f"detected as '{detected}'"
        ),
    )


def should_proceed_on_type_mismatch(
    validation: TypeValidation,
    *,
    force: bool = False,
    non_interactive: bool = False,
) -> bool:
    """Decide whether to proceed when directory type doesn't match.

    - Match or no config: always proceed
    - Mismatch + ``--force``: proceed, log warning
    - Mismatch + ``--non-interactive``: skip, log warning
    - Mismatch interactive: skip with warning (prompt planned for PR 7)

    Args:
        validation: TypeValidation result
        force: Whether --force is active
        non_interactive: Whether --non-interactive is active

    Returns:
        True if processing should continue
    """
    if validation.ok:
        return True

    if validation.result == TypeValidation.NOT_EXISTS:
        message(
            f"WARNING: {validation.message_text}",
            MessageType.WARNING,
            VerbosityLevel.ALWAYS,
        )
        return False

    # Mismatch
    if force:
        message(
            f"WARNING: {validation.message_text} (--force, proceeding)",
            MessageType.WARNING,
            VerbosityLevel.ALWAYS,
        )
        return True

    if non_interactive:
        message(
            f"WARNING: {validation.message_text} (skipping)",
            MessageType.WARNING,
            VerbosityLevel.ALWAYS,
        )
        return False

    # Interactive: skip (prompt planned)
    message(
        f"WARNING: {validation.message_text} (skipping, "
        f"use --force to override)",
        MessageType.WARNING,
        VerbosityLevel.ALWAYS,
    )
    return False
