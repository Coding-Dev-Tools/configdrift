"""Targeted coverage tests for uncovered lines in loader.py and cli.py."""

import pytest
import tempfile
import yaml
from configdrift.cli import app
from configdrift.loader import _strip_inline_comment, load_file
from pathlib import Path
from typer.testing import CliRunner

runner = CliRunner()


class TestStripInlineCommentToggles:
    """Cover loader.py:72, 74 — quote toggling in _strip_inline_comment."""

    def test_double_quote_toggle_with_hash(self):
        """Line 72: in_double should toggle when encountering " outside single quotes."""
        # A value with a " inside it, followed by # outside quotes
        # The " should be detected as the start/end of double-quoting
        result = _strip_inline_comment('prefix "hello" # comment')
        assert result == 'prefix "hello"', (
            f"Expected comment stripped after quoted section, got: {result!r}"
        )

    def test_single_quote_toggle_with_hash(self):
        """Line 74: in_single should toggle when encountering ' outside double quotes."""
        result = _strip_inline_comment("prefix 'hello' # comment")
        assert result == "prefix 'hello'", (
            f"Expected comment stripped after quoted section, got: {result!r}"
        )


class TestLoadDotenvQuoteStrip:
    """Cover loader.py:99 — quote stripping in _load_dotenv."""

    def test_quote_stripping_double(self):
        """Line 99: surrounding double quotes via _load_dotenv direct."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "test.env"
            p.write_text('DB_HOST="localhost"\n')
            result = load_file(str(p))
            assert result == {"DB_HOST": "localhost"}

    def test_quote_stripping_single(self):
        """Line 99: surrounding single quotes via _load_dotenv direct."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "test.env"
            p.write_text("DB_HOST='localhost'\n")
            result = load_file(str(p))
            assert result == {"DB_HOST": "localhost"}


class TestLoaderLine3132:
    """Cover loader.py:31-32 — ValueError fallback when _load_dotenv fails."""

    def test_unknown_ext_invalid_utf8_raises_valueerror(self):
        """Line 31-32: unknown extension with non-UTF-8 content triggers ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "config.bin"
            # Binary bytes that can't be decoded as UTF-8
            p.write_bytes(b"\xff\xfe\x00\x00hello")
            with pytest.raises(ValueError, match="Unsupported file format: .bin"):
                load_file(str(p))


class TestCliLine206:
    """Cover cli.py:206 — has_drift check after JSON output with breaking drift."""

    def test_scan_silent_strict_any_drift(self):
        """Line 206: scan --strict --output silent with non-breaking drift exits 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev_dir = Path(tmpdir) / "dev"
            prod_dir = Path(tmpdir) / "prod"
            dev_dir.mkdir()
            prod_dir.mkdir()
            # Non-breaking drift (info-level): host change
            (dev_dir / "c.yaml").write_text(yaml.dump({"host": "localhost"}))
            (prod_dir / "c.yaml").write_text(yaml.dump({"host": "prod.example.com"}))

            result = runner.invoke(
                app,
                ["scan", str(dev_dir), str(prod_dir), "--output", "silent", "--strict"],
            )
            assert result.exit_code == 1
