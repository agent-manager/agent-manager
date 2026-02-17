"""Tests for core/manifest.py - Manifest system."""

from pathlib import Path
from unittest.mock import patch

import yaml

from agent_manager.core.manifest import (
    _file_hash,
    _manifest_path,
    add_or_update_entry,
    cleanup_stale_files,
    get_manifest_entry,
    is_managed,
    read_manifest,
    remove_agent_from_entry,
    write_manifest,
)


# ===========================================================================
# Helpers
# ===========================================================================
class TestFileHash:

    def test_hashes_file(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("hello")
        h = _file_hash(f)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex

    def test_same_content_same_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("same")
        f2.write_text("same")
        assert _file_hash(f1) == _file_hash(f2)

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("one")
        f2.write_text("two")
        assert _file_hash(f1) != _file_hash(f2)

    def test_missing_file_returns_empty(self, tmp_path):
        assert _file_hash(tmp_path / "missing.txt") == ""


class TestManifestPath:

    def test_returns_correct_path(self, tmp_path):
        p = _manifest_path(tmp_path)
        assert p == tmp_path / ".agent-manager" / "manifest"


# ===========================================================================
# Read / Write
# ===========================================================================
class TestReadManifest:

    def test_returns_empty_when_missing(self, tmp_path):
        m = read_manifest(tmp_path)
        assert m["last_synced"] is None
        assert m["files"] == []

    def test_reads_valid_manifest(self, tmp_path):
        mdir = tmp_path / ".agent-manager"
        mdir.mkdir()
        data = {
            "last_synced": "2026-02-13T15:30:00+00:00",
            "files": [
                {"name": "a.txt", "agents": ["claude"], "hash": "abc"},
            ],
        }
        (mdir / "manifest").write_text(yaml.dump(data))

        m = read_manifest(tmp_path)
        assert m["last_synced"] == "2026-02-13T15:30:00+00:00"
        assert len(m["files"]) == 1
        assert m["files"][0]["name"] == "a.txt"

    def test_handles_corrupt_yaml(self, tmp_path):
        mdir = tmp_path / ".agent-manager"
        mdir.mkdir()
        (mdir / "manifest").write_text("::invalid yaml::[")

        with patch("agent_manager.core.manifest.message"):
            m = read_manifest(tmp_path)
        assert m["files"] == []

    def test_handles_non_dict_yaml(self, tmp_path):
        mdir = tmp_path / ".agent-manager"
        mdir.mkdir()
        (mdir / "manifest").write_text("- just a list")

        m = read_manifest(tmp_path)
        assert m["files"] == []


class TestWriteManifest:

    def test_creates_directory_and_file(self, tmp_path):
        manifest = {"files": []}
        write_manifest(tmp_path, manifest)

        assert (tmp_path / ".agent-manager" / "manifest").exists()

    def test_sets_last_synced(self, tmp_path):
        manifest = {"files": []}
        write_manifest(tmp_path, manifest)

        assert manifest["last_synced"] is not None
        assert "T" in manifest["last_synced"]

    def test_round_trip(self, tmp_path):
        manifest = {
            "files": [
                {"name": "x.txt", "agents": ["claude"], "hash": "abc123"},
            ],
        }
        write_manifest(tmp_path, manifest)
        loaded = read_manifest(tmp_path)

        assert len(loaded["files"]) == 1
        assert loaded["files"][0]["name"] == "x.txt"
        assert loaded["last_synced"] is not None


# ===========================================================================
# Lookup helpers
# ===========================================================================
class TestGetManifestEntry:

    def test_found(self):
        m = {"files": [{"name": "a.txt", "agents": ["x"], "hash": "h"}]}
        entry = get_manifest_entry(m, "a.txt")
        assert entry is not None
        assert entry["name"] == "a.txt"

    def test_not_found(self):
        m = {"files": [{"name": "a.txt", "agents": ["x"], "hash": "h"}]}
        assert get_manifest_entry(m, "b.txt") is None

    def test_empty_manifest(self):
        assert get_manifest_entry({"files": []}, "a.txt") is None


class TestIsManaged:

    def test_true_when_present(self):
        m = {"files": [{"name": "a.txt", "agents": ["x"], "hash": "h"}]}
        assert is_managed(m, "a.txt")

    def test_false_when_absent(self):
        m = {"files": []}
        assert not is_managed(m, "a.txt")


# ===========================================================================
# Update helpers
# ===========================================================================
class TestAddOrUpdateEntry:

    def test_adds_new_entry(self, tmp_path):
        m = {"files": []}
        f = tmp_path / "new.txt"
        f.write_text("content")

        add_or_update_entry(m, "new.txt", "claude", f)

        assert len(m["files"]) == 1
        assert m["files"][0]["name"] == "new.txt"
        assert m["files"][0]["agents"] == ["claude"]
        assert m["files"][0]["hash"] != ""

    def test_updates_existing_entry(self, tmp_path):
        f = tmp_path / "existing.txt"
        f.write_text("v1")
        h1 = _file_hash(f)

        m = {"files": [{"name": "existing.txt", "agents": ["claude"], "hash": h1}]}

        f.write_text("v2")
        add_or_update_entry(m, "existing.txt", "claude", f)

        assert len(m["files"]) == 1
        assert m["files"][0]["hash"] != h1

    def test_adds_new_agent_to_existing(self, tmp_path):
        f = tmp_path / "shared.txt"
        f.write_text("x")
        m = {"files": [{"name": "shared.txt", "agents": ["claude"], "hash": "h"}]}

        add_or_update_entry(m, "shared.txt", "cursor", f)

        assert m["files"][0]["agents"] == ["claude", "cursor"]

    def test_does_not_duplicate_agent(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("x")
        m = {"files": [{"name": "x.txt", "agents": ["claude"], "hash": "h"}]}

        add_or_update_entry(m, "x.txt", "claude", f)

        assert m["files"][0]["agents"] == ["claude"]


class TestRemoveAgentFromEntry:

    def test_removes_agent_keeps_entry(self):
        m = {"files": [{"name": "x.txt", "agents": ["claude", "cursor"], "hash": "h"}]}

        result = remove_agent_from_entry(m, "x.txt", "claude")

        assert result is False
        assert len(m["files"]) == 1
        assert m["files"][0]["agents"] == ["cursor"]

    def test_removes_last_agent_removes_entry(self):
        m = {"files": [{"name": "x.txt", "agents": ["claude"], "hash": "h"}]}

        result = remove_agent_from_entry(m, "x.txt", "claude")

        assert result is True
        assert len(m["files"]) == 0

    def test_entry_not_found(self):
        m = {"files": []}
        result = remove_agent_from_entry(m, "x.txt", "claude")
        assert result is False

    def test_agent_not_in_entry(self):
        m = {"files": [{"name": "x.txt", "agents": ["cursor"], "hash": "h"}]}
        result = remove_agent_from_entry(m, "x.txt", "claude")
        assert result is False
        assert m["files"][0]["agents"] == ["cursor"]


# ===========================================================================
# Cleanup
# ===========================================================================
class TestCleanupStaleFiles:

    def test_deletes_stale_file(self, tmp_path):
        stale = tmp_path / "old.txt"
        stale.write_text("old")

        m = {"files": [{"name": "old.txt", "agents": ["claude"], "hash": "h"}]}

        with patch("agent_manager.core.manifest.message"):
            deleted = cleanup_stale_files(
                tmp_path, m, "claude", current_files=set(),
            )

        assert "old.txt" in deleted
        assert not stale.exists()
        assert len(m["files"]) == 0

    def test_keeps_current_file(self, tmp_path):
        current = tmp_path / "keep.txt"
        current.write_text("keep")

        m = {"files": [{"name": "keep.txt", "agents": ["claude"], "hash": "h"}]}

        deleted = cleanup_stale_files(
            tmp_path, m, "claude", current_files={"keep.txt"},
        )

        assert deleted == []
        assert current.exists()
        assert len(m["files"]) == 1

    def test_removes_agent_but_keeps_shared_file(self, tmp_path):
        shared = tmp_path / "shared.txt"
        shared.write_text("shared")

        m = {"files": [{"name": "shared.txt", "agents": ["claude", "cursor"], "hash": "h"}]}

        with patch("agent_manager.core.manifest.message"):
            deleted = cleanup_stale_files(
                tmp_path, m, "claude", current_files=set(),
            )

        # File should NOT be deleted (cursor still owns it)
        assert deleted == []
        assert shared.exists()
        assert m["files"][0]["agents"] == ["cursor"]

    def test_ignores_unrelated_entries(self, tmp_path):
        m = {"files": [{"name": "other.txt", "agents": ["cursor"], "hash": "h"}]}

        deleted = cleanup_stale_files(
            tmp_path, m, "claude", current_files=set(),
        )

        assert deleted == []
        assert len(m["files"]) == 1

    def test_handles_already_deleted_file(self, tmp_path):
        m = {"files": [{"name": "gone.txt", "agents": ["claude"], "hash": "h"}]}

        with patch("agent_manager.core.manifest.message"):
            deleted = cleanup_stale_files(
                tmp_path, m, "claude", current_files=set(),
            )

        # Entry removed from manifest even though file was already gone
        assert deleted == []
        assert len(m["files"]) == 0
