"""Unit tests for the diff engine (configdrift.diff)."""

import pytest
from configdrift.diff import (
    Change,
    ChangeType,
    DiffResult,
    Severity,
    _infer_severity_added,
    _infer_severity_changed,
    _infer_severity_removed,
    diff_configs,
    diff_environments,
)


class TestChangeDataclass:
    def test_change_str_added(self):
        c = Change(key="port", change_type=ChangeType.ADDED, new_value=443, env="prod")
        assert "[+]" in str(c)
        assert "port" in str(c)
        assert "443" in str(c)

    def test_change_str_removed(self):
        c = Change(
            key="host", change_type=ChangeType.REMOVED, old_value="localhost", env="dev"
        )
        assert "[-]" in str(c)
        assert "host" in str(c)

    def test_change_str_changed(self):
        c = Change(
            key="host",
            change_type=ChangeType.CHANGED,
            old_value="dev",
            new_value="prod",
            env="prod",
        )
        assert "[~]" in str(c)
        assert "dev" in str(c)
        assert "prod" in str(c)


class TestDiffResult:
    def test_empty_result_no_breaking(self):
        r = DiffResult()
        assert r.has_breaking is False
        assert r.count == 0

    def test_result_with_breaking(self):
        r = DiffResult(
            changes=[
                Change(
                    key="auth",
                    change_type=ChangeType.CHANGED,
                    severity=Severity.BREAKING,
                ),
                Change(
                    key="port", change_type=ChangeType.CHANGED, severity=Severity.INFO
                ),
            ]
        )
        assert r.has_breaking is True
        assert r.count == 2

    def test_by_type(self):
        r = DiffResult(
            changes=[
                Change(key="a", change_type=ChangeType.ADDED),
                Change(key="b", change_type=ChangeType.REMOVED),
                Change(key="c", change_type=ChangeType.ADDED),
            ]
        )
        added = r.by_type(ChangeType.ADDED)
        assert len(added) == 2
        assert all(c.change_type == ChangeType.ADDED for c in added)

    def test_by_severity(self):
        r = DiffResult(
            changes=[
                Change(
                    key="a", change_type=ChangeType.CHANGED, severity=Severity.BREAKING
                ),
                Change(key="b", change_type=ChangeType.CHANGED, severity=Severity.INFO),
                Change(
                    key="c", change_type=ChangeType.ADDED, severity=Severity.WARNING
                ),
            ]
        )
        breaking = r.by_severity(Severity.BREAKING)
        assert len(breaking) == 1
        assert breaking[0].key == "a"


class TestDiffConfigs:
    def test_no_changes(self):
        base = {"host": "localhost", "port": 8080}
        target = {"host": "localhost", "port": 8080}
        result = diff_configs(base, target)
        assert result.count == 0
        assert result.has_breaking is False

    def test_added_key(self):
        base = {"host": "localhost"}
        target = {"host": "localhost", "port": 443}
        result = diff_configs(base, target)
        added = result.by_type(ChangeType.ADDED)
        assert len(added) == 1
        assert added[0].key == "port"
        assert added[0].new_value == 443

    def test_removed_key(self):
        base = {"host": "localhost", "port": 8080}
        target = {"host": "localhost"}
        result = diff_configs(base, target)
        removed = result.by_type(ChangeType.REMOVED)
        assert len(removed) == 1
        assert removed[0].key == "port"
        assert removed[0].old_value == 8080

    def test_changed_key(self):
        base = {"host": "localhost"}
        target = {"host": "prod.example.com"}
        result = diff_configs(base, target)
        changed = result.by_type(ChangeType.CHANGED)
        assert len(changed) == 1
        assert changed[0].old_value == "localhost"
        assert changed[0].new_value == "prod.example.com"

    def test_critical_key_added_is_breaking(self):
        base = {"host": "localhost"}
        target = {"host": "localhost", "database_url": "postgres://prod"}
        result = diff_configs(base, target)
        added = result.by_type(ChangeType.ADDED)
        assert added[0].severity == Severity.BREAKING

    def test_critical_key_removed_is_breaking(self):
        base = {"database_url": "postgres://dev", "host": "localhost"}
        target = {"host": "localhost"}
        result = diff_configs(base, target)
        removed = result.by_type(ChangeType.REMOVED)
        assert removed[0].severity == Severity.BREAKING

    def test_critical_key_changed_is_breaking(self):
        base = {"auth_token": "old-token"}
        target = {"auth_token": "new-token"}
        result = diff_configs(base, target)
        assert result.has_breaking is True

    def test_non_critical_change_is_info(self):
        base = {"log_level": "debug"}
        target = {"log_level": "info"}
        result = diff_configs(base, target)
        changed = result.by_type(ChangeType.CHANGED)
        assert changed[0].severity == Severity.INFO

    def test_non_critical_added_is_warning(self):
        base = {"host": "localhost"}
        target = {"host": "localhost", "cache_ttl": "300"}
        result = diff_configs(base, target)
        added = result.by_type(ChangeType.ADDED)
        assert added[0].severity == Severity.WARNING

    def test_env_labels_propagated(self):
        base = {"host": "dev"}
        target = {"host": "prod"}
        result = diff_configs(base, target, base_env="staging", target_env="production")
        changed = result.by_type(ChangeType.CHANGED)
        assert changed[0].env == "production"

    def test_multiple_changes_sorted_by_key(self):
        base = {"z_key": 1, "a_key": 2, "m_key": 3}
        target = {"z_key": 10, "a_key": 20, "m_key": 30}
        result = diff_configs(base, target)
        keys = [c.key for c in result.changes]
        assert keys == sorted(keys)


class TestDiffEnvironments:
    def test_two_environments(self):
        configs = {
            "dev": {"host": "localhost", "port": 8080},
            "prod": {"host": "prod.example.com", "port": 8080},
        }
        results = diff_environments(configs, baseline_env="dev")
        assert "prod" in results
        assert results["prod"].count == 1
        assert results["prod"].changes[0].key == "host"

    def test_three_environments(self):
        configs = {
            "dev": {"host": "localhost"},
            "staging": {"host": "staging.example.com"},
            "prod": {"host": "prod.example.com"},
        }
        results = diff_environments(configs, baseline_env="dev")
        assert len(results) == 2
        assert "staging" in results
        assert "prod" in results

    def test_invalid_baseline_raises(self):
        configs = {"dev": {"host": "localhost"}}
        with pytest.raises(ValueError, match="prod"):
            diff_environments(configs, baseline_env="prod")

    def test_identical_environments_no_changes(self):
        configs = {
            "dev": {"host": "localhost"},
            "staging": {"host": "localhost"},
        }
        results = diff_environments(configs, baseline_env="dev")
        assert results["staging"].count == 0


class TestSeverityInference:
    def test_added_critical_prefix_database(self):
        assert _infer_severity_added("database_url", "x") == Severity.BREAKING

    def test_added_critical_prefix_auth(self):
        assert _infer_severity_added("auth_provider", "x") == Severity.BREAKING

    def test_added_critical_prefix_api_key(self):
        assert _infer_severity_added("api_key_prod", "x") == Severity.BREAKING

    def test_added_critical_prefix_secret(self):
        assert _infer_severity_added("secret_key", "x") == Severity.BREAKING

    def test_added_critical_prefix_password(self):
        assert _infer_severity_added("password_hash", "x") == Severity.BREAKING

    def test_added_critical_prefix_token(self):
        assert _infer_severity_added("token_refresh", "x") == Severity.BREAKING

    def test_added_critical_prefix_endpoint(self):
        assert _infer_severity_added("endpoint_url", "x") == Severity.BREAKING

    def test_added_non_critical(self):
        assert _infer_severity_added("cache_ttl", "300") == Severity.WARNING

    def test_removed_critical(self):
        assert _infer_severity_removed("database_url", "x") == Severity.BREAKING

    def test_removed_non_critical(self):
        assert _infer_severity_removed("log_level", "debug") == Severity.WARNING

    def test_changed_critical(self):
        assert _infer_severity_changed("auth_token", "old", "new") == Severity.BREAKING

    def test_changed_non_critical(self):
        assert _infer_severity_changed("log_level", "debug", "info") == Severity.INFO

    def test_case_insensitive_prefix(self):
        assert _infer_severity_added("Database_url", "x") == Severity.BREAKING
        assert _infer_severity_added("API_KEY", "x") == Severity.BREAKING
