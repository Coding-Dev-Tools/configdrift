"""Tests for ConfigDrift CLI commands."""

import json
import tempfile
import yaml
from configdrift.cli import app
from pathlib import Path
from typer.testing import CliRunner

runner = CliRunner()


class TestCheckCommand:
    def test_check_two_files(self):
        """Compare two config files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev = Path(tmpdir) / "dev.yaml"
            prod = Path(tmpdir) / "prod.yaml"
            dev.write_text(yaml.dump({"host": "localhost", "port": 8080}))
            prod.write_text(yaml.dump({"host": "api.example.com", "port": 8080}))

            result = runner.invoke(app, ["check", str(dev), str(prod)])
            assert result.exit_code == 0
            assert "Config Drift" in result.stdout
            assert "host" in result.stdout

    def test_check_json_output(self):
        """Ensure JSON output format works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev = Path(tmpdir) / "dev.json"
            prod = Path(tmpdir) / "prod.json"
            dev.write_text(json.dumps({"host": "localhost"}))
            prod.write_text(json.dumps({"host": "prod.example.com", "port": 443}))

            result = runner.invoke(app, ["check", str(dev), str(prod), "--output", "json"])
            assert result.exit_code == 0
            data = json.loads(result.stdout)
            assert "target" in data
            assert data["target"]["count"] >= 1

    def test_check_silent_no_drift(self):
        """Silent mode exits 0 when no drift."""
        with tempfile.TemporaryDirectory() as tmpdir:
            a = Path(tmpdir) / "a.yaml"
            b = Path(tmpdir) / "b.yaml"
            a.write_text(yaml.dump({"key": "val"}))
            b.write_text(yaml.dump({"key": "val"}))

            result = runner.invoke(app, ["check", str(a), str(b), "--output", "silent"])
            assert result.exit_code == 0

    def test_check_silent_has_drift(self):
        """Silent mode exits 1 when breaking drift exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            a = Path(tmpdir) / "a.yaml"
            b = Path(tmpdir) / "b.yaml"
            a.write_text(yaml.dump({"database_url": "postgres://dev"}))
            b.write_text(yaml.dump({"database_url": "postgres://prod"}))

            result = runner.invoke(app, ["check", str(a), str(b), "--output", "silent"])
            assert result.exit_code == 1

    def test_check_error_file_not_found(self):
        """Non-existent file should produce an error."""
        result = runner.invoke(app, ["check", "nonexistent.yaml", "other.yaml"])
        assert result.exit_code == 1
        assert "Error loading" in result.stdout

    def test_check_less_than_two_files(self):
        """Only one file should error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            a = Path(tmpdir) / "a.yaml"
            a.write_text(yaml.dump({"key": "val"}))
            result = runner.invoke(app, ["check", str(a)])
            assert result.exit_code == 1
            assert "Provide at least 2 config files" in result.stdout


class TestScanCommand:
    def test_scan_two_dirs(self):
        """Scan directories as environments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev_dir = Path(tmpdir) / "dev"
            prod_dir = Path(tmpdir) / "prod"
            dev_dir.mkdir()
            prod_dir.mkdir()
            (dev_dir / "config.yaml").write_text(yaml.dump({"host": "localhost"}))
            (prod_dir / "config.yaml").write_text(yaml.dump({"host": "prod.example.com"}))

            result = runner.invoke(app, ["scan", str(dev_dir), str(prod_dir)])
            assert result.exit_code == 0
            assert "Config Drift" in result.stdout

    def test_scan_with_config_file(self):
        """Scan using .configdrift.yaml config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = Path(tmpdir) / ".configdrift.yaml"
            dev_dir = Path(tmpdir) / "dev"
            prod_dir = Path(tmpdir) / "prod"
            dev_dir.mkdir()
            prod_dir.mkdir()
            (dev_dir / "app.yaml").write_text(yaml.dump({"host": "localhost"}))
            (prod_dir / "app.yaml").write_text(yaml.dump({"host": "prod.example.com"}))

            cfg.write_text(yaml.dump({
                "environments": {
                    "dev": str(dev_dir),
                    "prod": str(prod_dir),
                }
            }))

            result = runner.invoke(app, ["scan", "--config", str(cfg)])
            assert result.exit_code == 0
            assert "prod" in result.stdout

    def test_scan_baseline_not_found(self):
        """Non-existent baseline should error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev_dir = Path(tmpdir) / "dev"
            dev_dir.mkdir()
            (dev_dir / "c.yaml").write_text(yaml.dump({"k": "v"}))
            result = runner.invoke(app, ["scan", str(dev_dir), "--baseline", "nonexistent"])
            assert result.exit_code == 1
            assert "not found" in result.stdout

    def test_scan_json_output(self):
        """Scan with JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev_dir = Path(tmpdir) / "dev"
            prod_dir = Path(tmpdir) / "prod"
            dev_dir.mkdir()
            prod_dir.mkdir()
            (dev_dir / "c.yaml").write_text(yaml.dump({"host": "localhost"}))
            (prod_dir / "c.yaml").write_text(yaml.dump({"host": "prod.example.com"}))

            result = runner.invoke(app, ["scan", str(dev_dir), str(prod_dir), "--output", "json"])
            assert result.exit_code == 0
            data = json.loads(result.stdout)
            assert "prod" in data


class TestInitCommand:
    def test_init_creates_file(self):
        """Init should create .configdrift.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", tmpdir])
            assert result.exit_code == 0
            assert Path(tmpdir, ".configdrift.yaml").exists()
            assert "Created" in result.stdout

    def test_init_existing_file(self):
        """Init should error if file already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / ".configdrift.yaml").write_text("key: val")
            result = runner.invoke(app, ["init", tmpdir])
            assert result.exit_code == 1
            assert "already exists" in result.stdout


class TestVersionCommand:
    def test_version_output(self):
        """--version should print version and exit."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "configdrift" in result.stdout
        assert "0.1.0" in result.stdout
