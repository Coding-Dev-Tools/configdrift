"""Unit tests for config file loaders (configdrift.loader)."""

import json
import pytest
import tempfile
from configdrift.loader import _flatten_nested, load_file
from pathlib import Path


class TestFlattenNested:
    def test_flat_dict_unchanged(self):
        data = {"host": "localhost", "port": 8080}
        result = _flatten_nested(data)
        assert result == {"host": "localhost", "port": 8080}

    def test_nested_dict_flattened(self):
        data = {"database": {"host": "localhost", "port": 5432}}
        result = _flatten_nested(data)
        assert result == {"database.host": "localhost", "database.port": 5432}

    def test_deeply_nested(self):
        data = {"a": {"b": {"c": "value"}}}
        result = _flatten_nested(data)
        assert result == {"a.b.c": "value"}

    def test_mixed_flat_and_nested(self):
        data = {"host": "localhost", "database": {"port": 5432}}
        result = _flatten_nested(data)
        assert result == {"host": "localhost", "database.port": 5432}

    def test_non_string_values_preserved(self):
        data = {"port": 8080, "debug": True, "ratio": 3.14}
        result = _flatten_nested(data)
        assert result["port"] == 8080
        assert result["debug"] is True
        assert result["ratio"] == 3.14

    def test_non_primitive_converted_to_str(self):
        data = {"tags": [1, 2, 3]}
        result = _flatten_nested(data)
        assert isinstance(result["tags"], str)

    def test_empty_dict(self):
        assert _flatten_nested({}) == {}


class TestLoadYaml:
    def test_load_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "test.yaml"
            p.write_text("host: localhost\nport: 8080\n")
            result = load_file(str(p))
            assert result["host"] == "localhost"
            assert result["port"] == 8080

    def test_load_yml_extension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "test.yml"
            p.write_text("key: value\n")
            result = load_file(str(p))
            assert result["key"] == "value"

    def test_load_nested_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "nested.yaml"
            p.write_text("database:\n  host: localhost\n  port: 5432\n")
            result = load_file(str(p))
            assert result["database.host"] == "localhost"
            assert result["database.port"] == 5432

    def test_yaml_non_dict_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "list.yaml"
            p.write_text("- item1\n- item2\n")
            with pytest.raises(ValueError, match="mapping"):
                load_file(str(p))


class TestLoadJson:
    def test_load_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "test.json"
            p.write_text(json.dumps({"host": "localhost", "port": 8080}))
            result = load_file(str(p))
            assert result["host"] == "localhost"

    def test_load_nested_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "nested.json"
            p.write_text(json.dumps({"database": {"host": "localhost"}}))
            result = load_file(str(p))
            assert result["database.host"] == "localhost"

    def test_json_non_dict_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "array.json"
            p.write_text(json.dumps([1, 2, 3]))
            with pytest.raises(ValueError, match="mapping"):
                load_file(str(p))


class TestLoadToml:
    def test_load_toml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "test.toml"
            p.write_text('[database]\nhost = "localhost"\nport = 5432\n')
            result = load_file(str(p))
            assert result["database.host"] == "localhost"
            assert result["database.port"] == 5432

    def test_load_toml_flat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "flat.toml"
            p.write_text('title = "test"\n')
            result = load_file(str(p))
            assert result["title"] == "test"


class TestLoadDotenv:
    def test_load_dotenv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / ".env"
            p.write_text("DATABASE_URL=postgres://localhost\nPORT=5432\n")
            result = load_file(str(p))
            assert result["DATABASE_URL"] == "postgres://localhost"
            assert result["PORT"] == "5432"

    def test_dotenv_comments_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / ".env"
            p.write_text("# This is a comment\nKEY=value\n")
            result = load_file(str(p))
            assert "KEY" in result
            assert len(result) == 1

    def test_dotenv_empty_lines_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / ".env"
            p.write_text("A=1\n\nB=2\n")
            result = load_file(str(p))
            assert len(result) == 2

    def test_dotenv_quoted_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / ".env"
            p.write_text('KEY="quoted value"\nSINGLE=\'single quoted\'\n')
            result = load_file(str(p))
            assert result["KEY"] == "quoted value"
            assert result["SINGLE"] == "single quoted"

    def test_dotenv_invalid_key_ignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / ".env"
            p.write_text("123BAD=value\nGOOD=val\n")
            result = load_file(str(p))
            assert "GOOD" in result
            assert "123BAD" not in result

    def test_dotenv_empty_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / ".env"
            p.write_text("EMPTY=\n")
            result = load_file(str(p))
            assert result["EMPTY"] == ""

    def test_dotenv_export_prefix(self):
        """Lines with 'export ' prefix should be parsed correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / ".env"
            p.write_text("export DATABASE_URL=postgres://localhost\nexport API_KEY=secret123\n")
            result = load_file(str(p))
            assert result["DATABASE_URL"] == "postgres://localhost"
            assert result["API_KEY"] == "secret123"

    def test_dotenv_inline_comment_unquoted(self):
        """Unquoted inline comments should be stripped from values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / ".env"
            p.write_text("HOST=localhost # production server\nPORT=8080#no space\n")
            result = load_file(str(p))
            assert result["HOST"] == "localhost"
            assert result["PORT"] == "8080"

    def test_dotenv_inline_comment_inside_quotes(self):
        """# inside quotes should be preserved in the value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / ".env"
            p.write_text('URL="https://example.com/#anchor"\n')
            result = load_file(str(p))
            assert result["URL"] == "https://example.com/#anchor"

    def test_dotenv_empty_file(self):
        """Empty .env file should return empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / ".env"
            p.write_text("")
            result = load_file(str(p))
            assert result == {}


class TestLoadFileUnsupported:
    def test_unsupported_extension_unparsable_returns_empty(self):
        """An extension no parser handles with binary content returns empty dict via dotenv fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "test.xyz"
            p.write_bytes(b"\x00\x01\x02\x03")
            # dotenv fallback parses zero lines, returns empty dict
            result = load_file(str(p))
            assert result == {}

    def test_unsupported_extension_parsable_falls_through(self):
        """Unknown extensions with valid YAML content get parsed by fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "test.xyz"
            p.write_text("host: localhost\n")
            # Should succeed via YAML fallback, not raise
            result = load_file(str(p))
            assert "host" in result

    def test_nonexistent_file_raises(self):
        with pytest.raises((FileNotFoundError, OSError)):
            load_file("/nonexistent/path/config.yaml")


class TestLoadFileFallback:
    def test_unknown_ext_tries_parsers(self):
        """Unknown extensions should try each parser in order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # A file with .cfg extension containing valid YAML
            p = Path(tmpdir) / "test.cfg"
            p.write_text("host: localhost\n")
            result = load_file(str(p))
            assert "host" in result
