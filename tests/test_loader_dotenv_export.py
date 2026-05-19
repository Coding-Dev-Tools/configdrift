"""Tests for .env export prefix handling and severity inference edge cases."""

import tempfile
import os
from configdrift.loader import load_file
from configdrift.diff import (
    ChangeType,
    Severity,
    diff_configs,
    diff_environments,
    DiffResult,
)


class TestDotenvExportPrefix:
    """Regression: .env files with 'export KEY=value' must parse correctly."""

    def test_export_prefix(self):
        content = "export DATABASE_URL=postgres://localhost\nexport API_KEY=secret123\n"
        with tempfile.NamedTemporaryFile(suffix=".env", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["DATABASE_URL"] == "postgres://localhost"
        assert result["API_KEY"] == "secret123"

    def test_export_prefix_with_quotes(self):
        content = 'export DB_NAME="mydb"\nexport DB_PASS=\'secret\'\n'
        with tempfile.NamedTemporaryFile(suffix=".env", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["DB_NAME"] == "mydb"
        assert result["DB_PASS"] == "secret"

    def test_mixed_export_and_plain(self):
        content = "PLAIN_KEY=value\nexport EXPORTED_KEY=other\n"
        with tempfile.NamedTemporaryFile(suffix=".env", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["PLAIN_KEY"] == "value"
        assert result["EXPORTED_KEY"] == "other"

    def test_export_no_space_before_equals(self):
        content = "export KEY=val\n"
        with tempfile.NamedTemporaryFile(suffix=".env", mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            result = load_file(f.name)
        os.unlink(f.name)
        assert result["KEY"] == "val"


class TestSeverityInference:
    """Tests for severity heuristics in diff_configs."""

    def test_non_critical_added_is_warning(self):
        base = {"host": "localhost"}
        target = {"host": "localhost", "port": 8080}
        result = diff_configs(base, target)
        added = [c for c in result.changes if c.change_type == ChangeType.ADDED]
        assert len(added) == 1
        assert added[0].severity == Severity.WARNING

    def test_non_critical_removed_is_warning(self):
        base = {"host": "localhost", "port": 8080}
        target = {"host": "localhost"}
        result = diff_configs(base, target)
        removed = [c for c in result.changes if c.change_type == ChangeType.REMOVED]
        assert len(removed) == 1
        assert removed[0].severity == Severity.WARNING

    def test_non_critical_changed_is_info(self):
        base = {"port": 8080}
        target = {"port": 9090}
        result = diff_configs(base, target)
        changed = [c for c in result.changes if c.change_type == ChangeType.CHANGED]
        assert len(changed) == 1
        assert changed[0].severity == Severity.INFO

    def test_all_critical_prefixes_breaking_on_change(self):
        """Every critical prefix triggers BREAKING on value change."""
        critical_keys = [
            "database_url", "auth_enabled", "api_key_id",
            "secret_key", "password_hash", "token_refresh",
            "endpoint_url",
        ]
        base = {k: "old" for k in critical_keys}
        target = {k: "new" for k in critical_keys}
        result = diff_configs(base, target)
        for change in result.changes:
            assert change.severity == Severity.BREAKING, (
                f"Expected BREAKING for key '{change.key}', got {change.severity}"
            )

    def test_diff_environments_single_env_returns_empty(self):
        """Single environment (baseline only) returns no results."""
        configs = {"dev": {"host": "localhost"}}
        results = diff_environments(configs, baseline_env="dev")
        assert results == {}


class TestDiffResultEdgeCases:
    """Edge-case tests for DiffResult."""

    def test_empty_diff_result_has_no_breaking(self):
        result = DiffResult()
        assert not result.has_breaking
        assert result.count == 0

    def test_empty_by_type_and_severity(self):
        result = DiffResult()
        assert result.by_type(ChangeType.ADDED) == []
        assert result.by_severity(Severity.BREAKING) == []
