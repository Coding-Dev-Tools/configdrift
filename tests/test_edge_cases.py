"""Packaging and edge-case tests for configdrift."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from configdrift.loader import load_file


class TestPackaging:
    """Verify wheel includes py.typed and package metadata."""

    def test_py_typed_in_source(self):
        """py.typed marker exists in the source tree."""
        py_typed = Path("src/configdrift/py.typed")
        assert py_typed.exists(), f"{py_typed} not found"
        assert py_typed.stat().st_size == 0, "py.typed must be empty"

    def test_package_importable(self):
        """Package imports without errors."""
        result = subprocess.run(
            [sys.executable, "-c", "import configdrift; print(configdrift.__version__)"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip()


class TestLoadFileEdgeCases:
    """Edge cases for load_file."""

    def test_dotenv_key_with_equals_in_value(self):
        """Values containing = sign should be preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / ".env"
            p.write_text('CONNECTION_STRING=postgres://user:pass@host:5432/db?sslmode=require\n')
            result = load_file(str(p))
            assert result["CONNECTION_STRING"] == "postgres://user:pass@host:5432/db?sslmode=require"

    def test_dotenv_mixed_quotes_inline(self):
        """Mixed quote styles in .env should be handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / ".env"
            p.write_text(
                'DB_URL="postgres://localhost"\n'
                "API_KEY='secret123'\n"
                'REGION=us-east-1\n'
            )
            result = load_file(str(p))
            assert result["DB_URL"] == "postgres://localhost"
            assert result["API_KEY"] == "secret123"
            assert result["REGION"] == "us-east-1"

    def test_dotenv_whitespace_around_equals(self):
        """Whitespace around = should be stripped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / ".env"
            p.write_text("KEY = value\n")
            result = load_file(str(p))
            assert result["KEY"] == "value"
