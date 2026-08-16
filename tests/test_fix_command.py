"""Tests for the `fix` CLI command — apply baseline values to target config files."""

import json
import pytest
from configdrift.cli import app
from pathlib import Path
from typer.testing import CliRunner

runner = CliRunner()


class TestFixCommandBasic:
    """Core fix behavior: overwrite target keys with baseline values."""

    def test_fix_json_overwrites_target_with_baseline(self, tmp_path: Path):
        baseline = tmp_path / "dev.json"
        target = tmp_path / "prod.json"
        baseline.write_text(json.dumps({"host": "localhost", "port": 8080}))
        target.write_text(json.dumps({"host": "prod.example.com", "port": 9090}))

        result = runner.invoke(app, ["fix", str(baseline), str(target)])
        assert result.exit_code == 0, result.output

        fixed = json.loads(target.read_text())
        assert fixed["host"] == "localhost"
        assert fixed["port"] == 8080

    def test_fix_yaml_overwrites_target_with_baseline(self, tmp_path: Path):
        baseline = tmp_path / "dev.yaml"
        target = tmp_path / "prod.yaml"
        baseline.write_text("host: localhost\nport: 8080\n")
        target.write_text("host: prod.example.com\nport: 9090\n")

        result = runner.invoke(app, ["fix", str(baseline), str(target)])
        assert result.exit_code == 0, result.output

        # Re-parse via load_file to verify round-trip
        from configdrift.loader import load_file

        fixed = load_file(str(target))
        assert fixed["host"] == "localhost"
        assert fixed["port"] == 8080

    def test_fix_preserves_keys_not_in_baseline(self, tmp_path: Path):
        """Keys only in target (not in baseline) should be preserved."""
        baseline = tmp_path / "dev.json"
        target = tmp_path / "prod.json"
        baseline.write_text(json.dumps({"host": "localhost"}))
        target.write_text(json.dumps({"host": "prod.example.com", "extra_key": "keep_me"}))

        result = runner.invoke(app, ["fix", str(baseline), str(target)])
        assert result.exit_code == 0, result.output

        fixed = json.loads(target.read_text())
        assert fixed["host"] == "localhost"
        assert fixed["extra_key"] == "keep_me"

    def test_fix_adds_missing_baseline_keys_to_target(self, tmp_path: Path):
        """Keys in baseline but missing from target should be added."""
        baseline = tmp_path / "dev.json"
        target = tmp_path / "prod.json"
        baseline.write_text(json.dumps({"host": "localhost", "new_key": "new_value"}))
        target.write_text(json.dumps({"host": "prod.example.com"}))

        result = runner.invoke(app, ["fix", str(baseline), str(target)])
        assert result.exit_code == 0, result.output

        fixed = json.loads(target.read_text())
        assert fixed["host"] == "localhost"
        assert fixed["new_key"] == "new_value"


class TestFixCommandEdgeCases:
    """Edge cases and error handling for the fix command."""

    def test_fix_requires_at_least_two_files(self):
        result = runner.invoke(app, ["fix", "only_one.json"])
        assert result.exit_code != 0

    def test_fix_nonexistent_baseline_exits_error(self, tmp_path: Path):
        target = tmp_path / "prod.json"
        target.write_text(json.dumps({"host": "x"}))
        result = runner.invoke(app, ["fix", str(tmp_path / "missing.json"), str(target)])
        assert result.exit_code != 0

    def test_fix_dry_run_does_not_modify_target(self, tmp_path: Path):
        baseline = tmp_path / "dev.json"
        target = tmp_path / "prod.json"
        baseline.write_text(json.dumps({"host": "localhost"}))
        original_content = json.dumps({"host": "prod.example.com"})
        target.write_text(original_content)

        result = runner.invoke(app, ["fix", "--dry-run", str(baseline), str(target)])
        assert result.exit_code == 0, result.output

        # Target must be unchanged
        assert target.read_text() == original_content
        # Output should mention dry-run or what would change
        assert "dry" in result.output.lower() or "would" in result.output.lower()

    def test_fix_toml_round_trip(self, tmp_path: Path):
        """Fix should work with TOML files when tomli-w is installed."""
        pytest.importorskip("tomli_w")
        baseline = tmp_path / "dev.toml"
        target = tmp_path / "prod.toml"
        baseline.write_text('[database]\nhost = "localhost"\nport = 5432\n')
        target.write_text('[database]\nhost = "prod.db"\nport = 3306\n')

        result = runner.invoke(app, ["fix", str(baseline), str(target)])
        assert result.exit_code == 0, result.output

        from configdrift.loader import load_file

        fixed = load_file(str(target))
        assert fixed["database.host"] == "localhost"
        assert fixed["database.port"] == 5432
