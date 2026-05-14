"""Tests for ConfigDrift loaders."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from configdrift.loader import load_file, _load_dotenv, _flatten_nested


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


class TestFlattenNested:
    def test_flatten(self):
        data = {"a": {"b": {"c": 1}, "d": 2}, "e": 3}
        result = _flatten_nested(data)
        assert result == {"a.b.c": 1, "a.d": 2, "e": 3}
