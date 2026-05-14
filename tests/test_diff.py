"""Tests for ConfigDrift diff engine."""

from configdrift.diff import (
    ChangeType,
    Severity,
    diff_configs,
    diff_environments,
    DiffResult,
    Change,
)


class TestDiffConfigs:
    def test_no_changes(self):
        base = {"host": "localhost", "port": 8080}
        target = {"host": "localhost", "port": 8080}
        result = diff_configs(base, target)
        assert len(result.changes) == 0
        assert not result.has_breaking

    def test_added_key(self):
        base = {"host": "localhost"}
        target = {"host": "localhost", "port": 8080}
        result = diff_configs(base, target, "dev", "prod")
        assert len(result.changes) == 1
        change = result.changes[0]
        assert change.change_type == ChangeType.ADDED
        assert change.key == "port"
        assert change.new_value == 8080
        assert change.env == "prod"

    def test_removed_key(self):
        base = {"host": "localhost", "port": 8080}
        target = {"host": "localhost"}
        result = diff_configs(base, target)
        assert len(result.changes) == 1
        assert result.changes[0].change_type == ChangeType.REMOVED
        assert result.changes[0].key == "port"

    def test_changed_value(self):
        base = {"port": 8080}
        target = {"port": 9090}
        result = diff_configs(base, target)
        assert len(result.changes) == 1
        change = result.changes[0]
        assert change.change_type == ChangeType.CHANGED
        assert change.old_value == 8080
        assert change.new_value == 9090

    def test_mixed_changes(self):
        base = {"a": 1, "b": 2, "c": 3}
        target = {"a": 1, "b": 99, "d": 4}
        result = diff_configs(base, target)
        assert len(result.changes) == 3
        types = {c.change_type for c in result.changes}
        assert ChangeType.CHANGED in types
        assert ChangeType.REMOVED in types
        assert ChangeType.ADDED in types

    def test_critical_key_added_breaking(self):
        base = {"host": "localhost"}
        target = {"host": "localhost", "database_url": "postgres://..."}
        result = diff_configs(base, target)
        assert result.has_breaking

    def test_critical_key_removed_breaking(self):
        base = {"database_url": "postgres://...", "host": "localhost"}
        target = {"host": "localhost"}
        result = diff_configs(base, target)
        assert result.has_breaking

    def test_critical_key_changed_breaking(self):
        base = {"api_key": "old-key"}
        target = {"api_key": "new-key"}
        result = diff_configs(base, target)
        assert result.has_breaking


class TestDiffEnvironments:
    def test_baseline_not_found(self):
        import pytest
        configs = {"dev": {"a": 1}}
        with pytest.raises(ValueError, match="Baseline environment.*not found"):
            diff_environments(configs, baseline_env="prod")

    def test_two_envs(self):
        configs = {
            "dev": {"host": "localhost", "port": 8080},
            "prod": {"host": "api.example.com", "port": 443},
        }
        results = diff_environments(configs, baseline_env="dev")
        assert "prod" in results
        assert results["prod"].count >= 1  # host changed, port changed

    def test_three_envs(self):
        configs = {
            "dev": {"host": "localhost"},
            "staging": {"host": "staging.example.com"},
            "prod": {"host": "prod.example.com"},
        }
        results = diff_environments(configs, baseline_env="dev")
        assert "staging" in results
        assert "prod" in results
        assert results["staging"].count == 1
        assert results["prod"].count == 1


class TestDiffResultHelpers:
    def test_by_type(self):
        changes = [
            Change(key="a", change_type=ChangeType.ADDED, new_value=1),
            Change(key="b", change_type=ChangeType.REMOVED, old_value=2),
            Change(key="c", change_type=ChangeType.CHANGED, old_value=1, new_value=3),
        ]
        result = DiffResult(changes=changes)
        assert len(result.by_type(ChangeType.ADDED)) == 1
        assert len(result.by_type(ChangeType.REMOVED)) == 1
        assert len(result.by_type(ChangeType.CHANGED)) == 1

    def test_by_severity(self):
        changes = [
            Change(key="a", change_type=ChangeType.ADDED, new_value=1, severity=Severity.INFO),
            Change(key="b", change_type=ChangeType.ADDED, new_value=2, severity=Severity.BREAKING),
        ]
        result = DiffResult(changes=changes)
        assert len(result.by_severity(Severity.INFO)) == 1
        assert len(result.by_severity(Severity.BREAKING)) == 1

    def test_count(self):
        changes = [
            Change(key="a", change_type=ChangeType.ADDED, new_value=1),
            Change(key="b", change_type=ChangeType.ADDED, new_value=2),
        ]
        result = DiffResult(changes=changes)
        assert result.count == 2
