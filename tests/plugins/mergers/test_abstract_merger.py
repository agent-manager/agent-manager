"""Tests for mergers/abstract_merger.py - AbstractMerger base class."""

import pytest

from agent_manager.plugins.mergers.abstract_merger import AbstractMerger


# Create a concrete test implementation
class TestMerger(AbstractMerger):
    """Test implementation of AbstractMerger."""

    FILE_EXTENSIONS = [".test"]

    @classmethod
    def merge(cls, base: str, new: str, source: str, sources: list[str], **settings) -> str:
        """Simple test merge implementation."""
        return f"{base}+{new}"

    @classmethod
    def merge_preferences(cls) -> dict:
        """Test preferences."""
        return {
            "test_option": {
                "type": "str",
                "default": "default_value",
                "description": "Test option",
            }
        }


class TestAbstractMerger:
    """Test cases for AbstractMerger base class."""

    def test_file_extensions_attribute(self):
        """Test that FILE_EXTENSIONS attribute exists."""
        assert hasattr(AbstractMerger, "FILE_EXTENSIONS")
        assert isinstance(AbstractMerger.FILE_EXTENSIONS, list)
        assert AbstractMerger.FILE_EXTENSIONS == []

    def test_merge_is_abstract(self):
        """Test that merge method is abstract."""
        # Cannot instantiate abstract class
        with pytest.raises(TypeError):
            AbstractMerger()

    def test_merge_preferences_default_empty(self):
        """Test that default merge_preferences returns empty dict."""
        # We can call it on a concrete implementation
        prefs = TestMerger.merge_preferences()

        assert isinstance(prefs, dict)
        assert len(prefs) > 0  # Our test implementation has preferences

    def test_concrete_implementation_can_override_preferences(self):
        """Test that concrete classes can define preferences."""
        prefs = TestMerger.merge_preferences()

        assert "test_option" in prefs
        assert prefs["test_option"]["type"] == "str"
        assert prefs["test_option"]["default"] == "default_value"

    def test_validate_settings_with_valid_settings(self):
        """Test _validate_settings with valid settings."""
        # Should not raise any exception
        TestMerger._validate_settings({"test_option": "custom_value"})

    def test_validate_settings_with_unknown_setting(self):
        """Test _validate_settings warns about unknown settings."""
        # Should not raise exception, but may log debug message
        TestMerger._validate_settings({"unknown_option": "value"})

    def test_validate_settings_with_empty_settings(self):
        """Test _validate_settings with empty settings dict."""
        # Should not raise any exception
        TestMerger._validate_settings({})

    def test_concrete_merger_can_call_merge(self):
        """Test that concrete merger's merge method works."""
        result = TestMerger.merge("base", "new", "source", [])

        assert result == "base+new"

    def test_file_extensions_can_be_multiple(self):
        """Test that FILE_EXTENSIONS can contain multiple extensions."""

        class MultiExtMerger(AbstractMerger):
            FILE_EXTENSIONS = [".ext1", ".ext2", ".ext3"]

            @classmethod
            def merge(cls, base, new, source, sources, **settings):
                return new

        assert len(MultiExtMerger.FILE_EXTENSIONS) == 3
        assert ".ext1" in MultiExtMerger.FILE_EXTENSIONS
        assert ".ext2" in MultiExtMerger.FILE_EXTENSIONS
        assert ".ext3" in MultiExtMerger.FILE_EXTENSIONS


class TestMergerPreferenceSchema:
    """Test cases for merger preference schema structure."""

    def test_preference_schema_structure(self):
        """Test that preference schemas follow expected structure."""
        prefs = TestMerger.merge_preferences()

        for _pref_name, pref_schema in prefs.items():
            # Each preference should have type
            assert "type" in pref_schema
            assert pref_schema["type"] in ["int", "str", "bool", "float"]

            # Each preference should have default
            assert "default" in pref_schema

            # Description is optional but recommended
            if "description" in pref_schema:
                assert isinstance(pref_schema["description"], str)

    def test_int_preference_constraints(self):
        """Test int preference with min/max constraints."""

        class IntMerger(AbstractMerger):
            FILE_EXTENSIONS = []

            @classmethod
            def merge(cls, base, new, source, sources, **settings):
                return new

            @classmethod
            def merge_preferences(cls):
                return {
                    "indent": {
                        "type": "int",
                        "default": 2,
                        "min": 0,
                        "max": 8,
                    }
                }

        prefs = IntMerger.merge_preferences()
        assert prefs["indent"]["type"] == "int"
        assert prefs["indent"]["min"] == 0
        assert prefs["indent"]["max"] == 8

    def test_str_preference_with_choices(self):
        """Test str preference with choice constraints."""

        class ChoiceMerger(AbstractMerger):
            FILE_EXTENSIONS = []

            @classmethod
            def merge(cls, base, new, source, sources, **settings):
                return new

            @classmethod
            def merge_preferences(cls):
                return {
                    "style": {
                        "type": "str",
                        "default": "compact",
                        "choices": ["compact", "verbose", "minimal"],
                    }
                }

        prefs = ChoiceMerger.merge_preferences()
        assert prefs["style"]["type"] == "str"
        assert "choices" in prefs["style"]
        assert len(prefs["style"]["choices"]) == 3

    def test_bool_preference(self):
        """Test bool preference."""

        class BoolMerger(AbstractMerger):
            FILE_EXTENSIONS = []

            @classmethod
            def merge(cls, base, new, source, sources, **settings):
                return new

            @classmethod
            def merge_preferences(cls):
                return {
                    "enabled": {
                        "type": "bool",
                        "default": True,
                    }
                }

        prefs = BoolMerger.merge_preferences()
        assert prefs["enabled"]["type"] == "bool"
        assert prefs["enabled"]["default"] is True
