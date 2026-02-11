"""Tests for utils/url.py - URL utility functions."""

from pathlib import Path

from agent_manager.utils.url import is_file_url, resolve_file_path


class TestIsFileUrl:
    """Test cases for is_file_url function."""

    def test_returns_true_for_file_url(self):
        """Test that file:// URLs are correctly identified."""
        assert is_file_url("file:///path/to/dir")
        assert is_file_url("file://~/Documents")
        assert is_file_url("file:///home/user/config")

    def test_returns_true_for_file_url_with_relative_path(self):
        """Test file:// URL with relative path."""
        assert is_file_url("file://relative/path")
        assert is_file_url("file://../parent/dir")

    def test_returns_false_for_http_url(self):
        """Test that HTTP URLs are not file URLs."""
        assert not is_file_url("http://example.com")
        assert not is_file_url("https://github.com/repo")

    def test_returns_false_for_git_url(self):
        """Test that Git URLs are not file URLs."""
        assert not is_file_url("git@github.com:user/repo.git")
        assert not is_file_url("git://github.com/user/repo.git")
        assert not is_file_url("ssh://git@github.com/user/repo.git")

    def test_returns_true_for_plain_absolute_path(self):
        """Test that plain absolute paths are detected as file URLs."""
        assert is_file_url("/absolute/path")
        assert is_file_url("/home/user/config")
        assert is_file_url("/")

    def test_returns_true_for_home_directory_path(self):
        """Test that home directory paths are detected as file URLs."""
        assert is_file_url("~/Documents")
        assert is_file_url("~/.config/app")
        assert is_file_url("~")

    def test_returns_true_for_relative_paths(self):
        """Test that relative paths with ./ or ../ are detected as file URLs."""
        assert is_file_url("./relative/path")
        assert is_file_url("../parent/path")
        assert is_file_url(".")
        assert is_file_url("..")
        assert is_file_url("./")
        assert is_file_url("../")

    def test_returns_false_for_bare_relative_path(self):
        """Test that bare relative paths (no ./ prefix) are NOT file URLs."""
        # These could be ambiguous with other URL schemes
        assert not is_file_url("relative/path")
        assert not is_file_url("subdir/file.txt")

    def test_returns_false_for_empty_string(self):
        """Test that empty string is not a file URL."""
        assert not is_file_url("")

    def test_returns_false_for_other_protocols(self):
        """Test other URL protocols are not file URLs."""
        assert not is_file_url("ftp://example.com")
        assert not is_file_url("sftp://example.com")
        assert not is_file_url("s3://bucket/path")
        assert not is_file_url("gs://bucket/path")

    def test_case_sensitive_protocol(self):
        """Test that protocol check is case-sensitive."""
        # file:// should be lowercase
        assert not is_file_url("FILE:///path")
        assert not is_file_url("File:///path")
        assert not is_file_url("FiLe:///path")

    def test_with_whitespace(self):
        """Test URLs with whitespace."""
        assert not is_file_url(" file:///path")  # Leading space
        assert not is_file_url("file:///path ")  # Trailing space
        # But file:// at start should work
        assert is_file_url("file:///path with spaces")

    def test_with_special_characters(self):
        """Test file URLs with special characters in path."""
        assert is_file_url("file:///path/with/special-chars_123")
        assert is_file_url("file:///path/with%20encoded%20spaces")

    def test_edge_case_just_protocol(self):
        """Test with just the protocol."""
        assert is_file_url("file://")
        assert is_file_url("file:///")


class TestResolveFilePath:
    """Test cases for resolve_file_path function."""

    def test_resolves_file_url_to_absolute_path(self):
        """Test that file:// URL is converted to absolute path."""
        result = resolve_file_path("file:///tmp/test")

        assert isinstance(result, Path)
        assert result.is_absolute()
        assert result == Path("/tmp/test").resolve()

    def test_strips_file_protocol_prefix(self):
        """Test that file:// prefix is removed."""
        result = resolve_file_path("file:///home/user/docs")

        # Should not contain file:// in the resolved path
        assert "file://" not in str(result)
        assert result == Path("/home/user/docs").resolve()

    def test_resolves_plain_path_without_file_protocol(self):
        """Test that paths without file:// are still resolved."""
        result = resolve_file_path("/tmp/test")

        assert isinstance(result, Path)
        assert result.is_absolute()
        assert result == Path("/tmp/test").resolve()

    def test_expands_home_directory_with_file_url(self):
        """Test that ~/ is expanded to user's home directory with file:// URL."""
        home = Path.home()
        result = resolve_file_path("file://~/Documents")

        assert result.is_absolute()
        assert str(result).startswith(str(home))
        assert str(result) == str(home / "Documents")

    def test_expands_home_directory_without_file_url(self):
        """Test that ~/ is expanded without file:// prefix."""
        home = Path.home()
        result = resolve_file_path("~/Documents")

        assert result.is_absolute()
        assert str(result) == str(home / "Documents")

    def test_resolves_relative_path_with_file_url(self):
        """Test that relative paths are resolved to absolute with file:// URL."""
        result = resolve_file_path("file://relative/path")

        assert isinstance(result, Path)
        assert result.is_absolute()
        # Should be resolved relative to current working directory
        assert "relative/path" in str(result)

    def test_resolves_relative_path_without_file_url(self):
        """Test that relative paths are resolved without file:// prefix."""
        result = resolve_file_path("relative/path")

        assert isinstance(result, Path)
        assert result.is_absolute()
        assert "relative/path" in str(result)

    def test_resolves_current_directory(self):
        """Test resolving current directory."""
        result = resolve_file_path(".")

        assert isinstance(result, Path)
        assert result.is_absolute()
        assert result == Path.cwd()

    def test_resolves_parent_directory(self):
        """Test resolving parent directory."""
        result = resolve_file_path("..")

        assert isinstance(result, Path)
        assert result.is_absolute()
        assert result == Path.cwd().parent

    def test_resolves_complex_relative_path(self):
        """Test resolving complex relative paths with .. and .."""
        result = resolve_file_path("./subdir/../other")

        assert isinstance(result, Path)
        assert result.is_absolute()
        # The path should be normalized (.. resolved)

    def test_resolves_path_with_trailing_slash(self):
        """Test path with trailing slash."""
        result = resolve_file_path("file:///tmp/test/")

        assert isinstance(result, Path)
        assert result == Path("/tmp/test").resolve()  # Path normalizes this

    def test_resolves_path_with_double_slashes(self):
        """Test path with double slashes."""
        result = resolve_file_path("file:///tmp//test")

        assert isinstance(result, Path)
        # Path should normalize double slashes

    def test_resolves_empty_string(self):
        """Test resolving empty string."""
        result = resolve_file_path("")

        assert isinstance(result, Path)
        assert result.is_absolute()
        # Empty string resolves to current directory
        assert result == Path.cwd()

    def test_preserves_multiple_path_components(self):
        """Test that multiple path components are preserved."""
        result = resolve_file_path("file:///a/b/c/d/e")

        assert str(result) == "/a/b/c/d/e"

    def test_handles_path_with_spaces(self):
        """Test path with spaces in directory names."""
        result = resolve_file_path("file:///path with spaces/dir")

        assert isinstance(result, Path)
        assert "path with spaces" in str(result)

    def test_handles_path_with_special_chars(self):
        """Test path with special characters."""
        result = resolve_file_path("file:///path-with_special.chars/dir")

        assert isinstance(result, Path)
        assert "path-with_special.chars" in str(result)

    def test_windows_style_path_on_unix(self):
        """Test handling of Windows-style paths (if on Unix)."""
        import platform

        if platform.system() != "Windows":
            # On Unix, this becomes a regular path
            result = resolve_file_path("file://C:\\Users\\test")
            assert isinstance(result, Path)

    def test_returns_path_object(self):
        """Test that return type is always Path object."""
        result1 = resolve_file_path("file:///tmp")
        result2 = resolve_file_path("/tmp")
        result3 = resolve_file_path("~/test")

        assert isinstance(result1, Path)
        assert isinstance(result2, Path)
        assert isinstance(result3, Path)


class TestUrlUtilsIntegration:
    """Integration tests for URL utility functions working together."""

    def test_is_file_url_and_resolve_together(self):
        """Test using is_file_url to check before resolving."""
        url = "file:///tmp/config"

        if is_file_url(url):
            result = resolve_file_path(url)
            assert result == Path("/tmp/config").resolve()

    def test_handling_various_url_types(self):
        """Test handling different URL types appropriately."""
        # URLs that should be detected as file URLs
        file_urls = [
            "file:///tmp/local",
            "/absolute/path",
            "~/config/path",
            "./relative/path",
            "../parent/path",
            ".",
        ]

        for url in file_urls:
            assert is_file_url(url), f"Expected {url} to be a file URL"
            result = resolve_file_path(url)
            assert isinstance(result, Path)

        # URLs that should NOT be detected as file URLs
        non_file_urls = [
            "https://github.com/repo",
            "git@github.com:user/repo.git",
            "relative/path",  # No ./ prefix
        ]

        for url in non_file_urls:
            assert not is_file_url(url), f"Expected {url} to NOT be a file URL"

    def test_round_trip_file_url_conversion(self):
        """Test converting to file URL and back."""
        original_path = "/tmp/test/dir"
        file_url = f"file://{original_path}"

        assert is_file_url(file_url)
        resolved = resolve_file_path(file_url)
        assert resolved == Path(original_path).resolve()

    def test_home_directory_expansion_consistency(self):
        """Test that ~/ expansion is consistent."""
        home = Path.home()

        result1 = resolve_file_path("~/test")
        result2 = resolve_file_path("file://~/test")

        # Both should expand to same absolute path
        assert result1 == result2
        assert str(result1).startswith(str(home))


class TestUrlUtilsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_path(self):
        """Test handling of very long paths."""
        long_path = "/".join(["dir"] * 100)  # 100 levels deep
        result = resolve_file_path(f"file:///{long_path}")

        assert isinstance(result, Path)
        assert "dir" in str(result)

    def test_path_with_unicode_characters(self):
        """Test path with unicode characters."""
        result = resolve_file_path("file:///tmp/文档/файл")

        assert isinstance(result, Path)
        # Unicode should be preserved
        assert "文档" in str(result) or "файл" in str(result)

    def test_path_with_dots_in_filename(self):
        """Test path with dots in filename."""
        result = resolve_file_path("file:///tmp/config.test.yaml")

        assert isinstance(result, Path)
        assert result == Path("/tmp/config.test.yaml").resolve()

    def test_symlink_path_resolution(self):
        """Test that symlinks are resolved to real path."""
        # Note: This test uses resolve() which follows symlinks
        result = resolve_file_path("/tmp")

        assert isinstance(result, Path)
        # resolve() will return the real path
        assert result.is_absolute()

    def test_nonexistent_path_still_resolves(self):
        """Test that nonexistent paths can still be resolved."""
        # resolve() works even if path doesn't exist
        result = resolve_file_path("file:///tmp/nonexistent/path/12345")

        assert isinstance(result, Path)
        assert result.is_absolute()
        # We can still get the absolute path even if it doesn't exist
