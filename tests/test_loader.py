"""Tests for ConfigDrift loaders."""

import json
import os
import pytest
import tempfile
import yaml
from configdrift.loader import _flatten_nested, load_file


class TestLoadYaml:
    def test_load_simple(self):
        content = yaml.dump({"key": "value", "nested": {"inner": 42}})
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["key"] == "value"
        assert result["nested.inner"] == 42

    def test_load_empty_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write("")
            f.flush()
            with pytest.raises(ValueError):
                load_file(f.name)
        os.unlink(f.name)


class TestLoadJson:
    def test_load_simple(self):
        data = {"host": "localhost", "db": {"port": 5432}}
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["host"] == "localhost"
        assert result["db.port"] == 5432


class TestLoadToml:
    def test_load_simple(self):
        content = "[server]\nhost = 'localhost'\nport = 8080\n[database]\nurl = 'postgres://...'\n"
        with tempfile.NamedTemporaryFile(suffix=".toml", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["server.host"] == "localhost"
        assert result["server.port"] == 8080
        assert result["database.url"] == "postgres://..."


class TestLoadDotenv:
    def test_export_prefix(self):
        """Lines with 'export ' prefix should be parsed correctly."""
        content = "export DATABASE_URL=postgres://localhost\nexport API_KEY=secret123\n"
        with tempfile.NamedTemporaryFile(suffix=".env", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["DATABASE_URL"] == "postgres://localhost"
        assert result["API_KEY"] == "secret123"

    def test_inline_comment_unquoted(self):
        """Unquoted inline comments should be stripped from values."""
        content = "HOST=localhost # production server\nPORT=8080#no space\n"
        with tempfile.NamedTemporaryFile(suffix=".env", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["HOST"] == "localhost"
        assert result["PORT"] == "8080"

    def test_inline_comment_inside_quotes(self):
        """# inside quotes should be preserved in the value."""
        content = 'URL="https://example.com/#anchor"\n'
        with tempfile.NamedTemporaryFile(suffix=".env", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["URL"] == "https://example.com/#anchor"

    def test_empty_env_file(self):
        """Empty .env file should return empty dict."""
        with tempfile.NamedTemporaryFile(suffix=".env", mode="w", delete=False) as f:
            f.write("")
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result == {}
    def test_load_simple(self):
        content = "DATABASE_URL=postgres://localhost\nAPI_KEY=secret123\n"
        with tempfile.NamedTemporaryFile(suffix=".env", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["DATABASE_URL"] == "postgres://localhost"
        assert result["API_KEY"] == "secret123"

    def test_load_with_quotes(self):
        content = 'DB_NAME="mydb"\nDB_PASS=\'secret\'\n'
        with tempfile.NamedTemporaryFile(suffix=".env", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["DB_NAME"] == "mydb"
        assert result["DB_PASS"] == "secret"

    def test_ignores_comments(self):
        content = "# This is a comment\nKEY=value\n"
        with tempfile.NamedTemporaryFile(suffix=".env", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["KEY"] == "value"
        assert "This is a comment" not in result


class TestLoadUnsupported:
    """Tests for fallback behaviour with unknown file extensions."""

    def test_fallback_yaml_content_in_cfg(self):
        """Files with .cfg containing valid YAML should be parsed via fallback."""
        content = yaml.dump({"key": "value", "nested": {"inner": 42}})
        with tempfile.NamedTemporaryFile(suffix=".cfg", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["key"] == "value"
        assert result["nested.inner"] == 42

    def test_fallback_yaml_as_json(self):
        """Files with unknown ext containing valid JSON should be parsed via fallback."""
        content = json.dumps({"host": "localhost", "port": 8080})
        with tempfile.NamedTemporaryFile(suffix=".cnf", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["host"] == "localhost"
        assert result["port"] == 8080

    def test_unsupported_format_fallback_to_dotenv(self):
        """Files with unknown extension and no structured content fall through to .env parser and returns a dict."""
        with tempfile.NamedTemporaryFile(suffix=".xyz", mode="w", delete=False) as f:
            f.write("not a config")
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert isinstance(result, dict)

    def test_unsupported_format_empty_result(self):
        """Garbage content with unknown extension returns empty dict via .env fallback."""
        with tempfile.NamedTemporaryFile(suffix=".xyz", mode="w", delete=False) as f:
            f.write("!!!garbage!!!")
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result == {}

    def test_yaml_non_dict_raises(self):
        """YAML containing a list (not a mapping) should raise ValueError."""
        content = yaml.dump(["item1", "item2"])
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            with pytest.raises(ValueError, match="YAML file must contain a mapping"):
                load_file(f.name)
        os.unlink(f.name)


class TestFlattenNested:
    def test_flatten(self):
        data = {"a": {"b": {"c": 1}, "d": 2}, "e": 3}
        result = _flatten_nested(data)
        assert result == {"a.b.c": 1, "a.d": 2, "e": 3}
