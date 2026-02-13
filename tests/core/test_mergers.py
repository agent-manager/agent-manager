"""Tests for core/mergers.py - Merger discovery and factory functions."""

from unittest.mock import Mock, patch

from agent_manager.core.merger_registry import MergerRegistry
from agent_manager.core.mergers import create_default_merger_registry, discover_merger_classes
from agent_manager.plugins.mergers import AbstractMerger, JsonMerger, MarkdownMerger, TextMerger, YamlMerger


class TestDiscoverMergerClassesImportError:
    """Test ImportError handling in discover_merger_classes."""

    def test_discover_handles_import_error(self):
        """Test that discover_merger_classes handles ImportError gracefully."""
        from agent_manager.core import mergers

        # Mock iter_modules to include a module that will fail to import
        with patch("pkgutil.iter_modules") as mock_iter:
            # Create a mock module info that will cause ImportError
            mock_module_info = Mock()
            mock_module_info.name = "broken_merger"
            mock_iter.return_value = [mock_module_info]

            # Mock import_module to raise ImportError for our broken module
            with patch("importlib.import_module", side_effect=ImportError("Module not found")):
                # Should not raise, just skip the broken module
                result = mergers.discover_merger_classes()

                # Result should be empty since we only had the broken module
                assert result == []


class TestDiscoverMergerClasses:
    """Test cases for discover_merger_classes function."""

    def test_discovers_merger_classes(self):
        """Test that merger classes are discovered."""
        mergers = discover_merger_classes()

        assert isinstance(mergers, list)
        assert len(mergers) > 0

    def test_discovers_json_merger(self):
        """Test that JsonMerger is discovered."""
        mergers = discover_merger_classes()
        merger_names = [m.__name__ for m in mergers]

        assert "JsonMerger" in merger_names

    def test_discovers_yaml_merger(self):
        """Test that YamlMerger is discovered."""
        mergers = discover_merger_classes()
        merger_names = [m.__name__ for m in mergers]

        assert "YamlMerger" in merger_names

    def test_discovers_markdown_merger(self):
        """Test that MarkdownMerger is discovered."""
        mergers = discover_merger_classes()
        merger_names = [m.__name__ for m in mergers]

        assert "MarkdownMerger" in merger_names

    def test_discovers_text_merger(self):
        """Test that TextMerger is discovered."""
        mergers = discover_merger_classes()
        merger_names = [m.__name__ for m in mergers]

        assert "TextMerger" in merger_names

    def test_does_not_discover_abstract_merger(self):
        """Test that AbstractMerger itself is not discovered."""
        mergers = discover_merger_classes()
        merger_names = [m.__name__ for m in mergers]

        assert "AbstractMerger" not in merger_names

    def test_does_not_discover_copy_merger(self):
        """Test that CopyMerger is not discovered (it's the default)."""
        mergers = discover_merger_classes()
        merger_names = [m.__name__ for m in mergers]

        assert "CopyMerger" not in merger_names

    def test_all_discovered_are_merger_subclasses(self):
        """Test that all discovered classes are AbstractMerger subclasses."""
        mergers = discover_merger_classes()

        for merger in mergers:
            assert issubclass(merger, AbstractMerger)

    def test_discovered_mergers_have_file_extensions(self):
        """Test that discovered mergers have FILE_EXTENSIONS attribute."""
        mergers = discover_merger_classes()

        for merger in mergers:
            assert hasattr(merger, "FILE_EXTENSIONS")
            assert isinstance(merger.FILE_EXTENSIONS, list)

    def test_returns_unique_merger_classes(self):
        """Test that no duplicate merger classes are returned."""
        mergers = discover_merger_classes()
        merger_names = [m.__name__ for m in mergers]

        assert len(merger_names) == len(set(merger_names))


class TestCreateDefaultMergerRegistry:
    """Test cases for create_default_merger_registry function."""

    def test_returns_merger_registry_instance(self):
        """Test that function returns a MergerRegistry instance."""
        registry = create_default_merger_registry()

        assert isinstance(registry, MergerRegistry)

    def test_registry_has_json_merger_registered(self):
        """Test that JsonMerger is registered for .json extension."""
        registry = create_default_merger_registry()

        merger = registry.extension_mergers.get(".json")
        assert merger == JsonMerger

    def test_registry_has_yaml_merger_registered(self):
        """Test that YamlMerger is registered for .yaml and .yml."""
        registry = create_default_merger_registry()

        yaml_merger = registry.extension_mergers.get(".yaml")
        yml_merger = registry.extension_mergers.get(".yml")

        assert yaml_merger == YamlMerger
        assert yml_merger == YamlMerger

    def test_registry_has_markdown_merger_registered(self):
        """Test that MarkdownMerger is registered for .md extension."""
        registry = create_default_merger_registry()

        md_merger = registry.extension_mergers.get(".md")
        markdown_merger = registry.extension_mergers.get(".markdown")

        assert md_merger == MarkdownMerger
        assert markdown_merger == MarkdownMerger

    def test_registry_has_text_merger_registered(self):
        """Test that TextMerger is registered for .txt extension."""
        registry = create_default_merger_registry()

        merger = registry.extension_mergers.get(".txt")
        assert merger == TextMerger

    def test_registry_has_default_merger(self):
        """Test that registry has a default merger set."""
        registry = create_default_merger_registry()

        assert registry.default_merger is not None
        assert hasattr(registry.default_merger, "merge")

    def test_all_registered_mergers_are_subclasses(self):
        """Test that all registered mergers are AbstractMerger subclasses."""
        registry = create_default_merger_registry()

        for merger in registry.extension_mergers.values():
            assert issubclass(merger, AbstractMerger)

    def test_creates_new_registry_each_time(self):
        """Test that each call creates a new registry instance."""
        registry1 = create_default_merger_registry()
        registry2 = create_default_merger_registry()

        assert registry1 is not registry2

    def test_registry_can_be_modified(self):
        """Test that returned registry can be modified."""
        registry = create_default_merger_registry()

        # Should be able to register new mergers
        from agent_manager.plugins.mergers.json_merger import JsonMerger

        registry.register_filename("custom.json", JsonMerger)

        assert "custom.json" in registry.filename_mergers

    def test_registry_extension_mergers_populated(self):
        """Test that registry has extension mergers populated."""
        registry = create_default_merger_registry()

        assert len(registry.extension_mergers) > 0

    def test_registry_has_no_filename_mergers_by_default(self):
        """Test that default registry has no filename-specific mergers."""
        registry = create_default_merger_registry()

        # By default, only extension-based mergers are registered
        assert len(registry.filename_mergers) == 0


class TestMergersIntegration:
    """Integration tests for merger discovery and registry creation."""

    def test_discovered_mergers_match_registry(self):
        """Test that discovered mergers are all in the registry."""
        mergers = discover_merger_classes()
        registry = create_default_merger_registry()

        # Get all unique mergers from registry
        registered_mergers = set(registry.extension_mergers.values())

        # All discovered mergers should be in the registry
        for merger in mergers:
            assert merger in registered_mergers

    def test_registry_covers_common_file_types(self):
        """Test that registry covers common configuration file types."""
        registry = create_default_merger_registry()

        common_extensions = [".json", ".yaml", ".yml", ".md", ".txt"]

        for ext in common_extensions:
            assert ext in registry.extension_mergers

    def test_registry_can_merge_common_files(self):
        """Test that registry can provide mergers for common files."""
        from pathlib import Path

        registry = create_default_merger_registry()

        test_files = [
            Path("config.json"),
            Path("settings.yaml"),
            Path("README.md"),
            Path("notes.txt"),
        ]

        for file_path in test_files:
            merger = registry.get_merger(file_path)
            assert merger is not None
            assert hasattr(merger, "merge")
