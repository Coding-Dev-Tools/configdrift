"""Tests for atomic write helpers — verify original file survives write failure."""

import os
import pytest
from configdrift._atomic import atomic_write_bytes, atomic_write_text
from pathlib import Path
from unittest.mock import patch


class TestAtomicWriteText:
    """Verify atomic_write_text preserves original on failure."""

    def test_successful_write(self, tmp_path: Path):
        target = tmp_path / "config.json"
        target.write_text("original")
        atomic_write_text(target, '{"key": "value"}\n')
        assert target.read_text() == '{"key": "value"}\n'

    def test_creates_file_if_missing(self, tmp_path: Path):
        target = tmp_path / "new.json"
        atomic_write_text(target, "hello")
        assert target.read_text() == "hello"

    def test_original_preserved_on_oserror(self, tmp_path: Path):
        """If os.replace fails, the original file must remain intact."""
        target = tmp_path / "config.json"
        target.write_text("original-content")

        with (
            patch("os.replace", side_effect=OSError("Simulated disk full")),
            pytest.raises(OSError, match="Simulated disk full"),
        ):
            atomic_write_text(target, "new-content")

        # Original must be untouched
        assert target.read_text() == "original-content"

    def test_no_temp_files_left_on_failure(self, tmp_path: Path):
        """Temp files must be cleaned up after a failed write."""
        target = tmp_path / "config.json"
        target.write_text("original")

        with patch("os.replace", side_effect=OSError("fail")), pytest.raises(OSError):
            atomic_write_text(target, "new")

        temps = list(tmp_path.glob("*.tmp"))
        assert temps == [], f"Leftover temp files: {temps}"

    def test_truncation_does_not_corrupt_original(self, tmp_path: Path):
        """Even if the temp-file write itself fails mid-stream, original is safe."""
        target = tmp_path / "config.json"
        original = "important-data-that-must-survive"
        target.write_text(original)

        real_fdopen = os.fdopen

        def failing_fdopen(fd, *args, **kwargs):
            fh = real_fdopen(fd, *args, **kwargs)  # noqa: F841
            # Simulate failure after opening but before writing
            raise OSError("Disk full during write")

        with (
            patch("os.fdopen", side_effect=failing_fdopen),
            pytest.raises(OSError, match="Disk full during write"),
        ):
            atomic_write_text(target, "replacement")

        assert target.read_text() == original


class TestAtomicWriteBytes:
    """Verify atomic_write_bytes preserves original on failure."""

    def test_successful_binary_write(self, tmp_path: Path):
        target = tmp_path / "data.bin"
        atomic_write_bytes(target, b"\x00\x01\x02")
        assert target.read_bytes() == b"\x00\x01\x02"

    def test_original_preserved_on_oserror(self, tmp_path: Path):
        target = tmp_path / "data.bin"
        target.write_bytes(b"original-bytes")

        with patch("os.replace", side_effect=OSError("fail")), pytest.raises(OSError):
            atomic_write_bytes(target, b"new-bytes")

        assert target.read_bytes() == b"original-bytes"
