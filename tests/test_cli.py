"""Tests for ConfigDrift CLI commands."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from typer.testing import CliRunner

from configdrift.cli import app

runner = CliRunner()


def test_cli_has_zero_sim108_violations() -> None:
    """src/configdrift/cli.py must have zero SIM108 (ternary-op) violations."""
    repo_root = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src/configdrift/cli.py", "--select=SIM108"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"ruff SIM108 violations in src/configdrift/cli.py:\n"
        f"{result.stdout}\n{result.stderr}"
    )


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

    def test_check_three_files(self):
        """Compare three config files with auto-labeled environments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            a = Path(tmpdir) / "a.yaml"
            b = Path(tmpdir) / "b.yaml"
            c = Path(tmpdir) / "c.yaml"
            a.write_text(yaml.dump({"host": "localhost", "port": 8080}))
            b.write_text(yaml.dump({"host": "staging.example.com", "port": 8080}))
            c.write_text(yaml.dump({"host": "prod.example.com", "port": 443}))

            result = runner.invoke(app, ["check", str(a), str(b), str(c)])
            assert result.exit_code == 0
            assert "file_1" in result.stdout or "Config Drift" in result.stdout
            assert "prod.example.com" in result.stdout

    def test_check_less_than_two_files(self):
        """Only one file should error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            a = Path(tmpdir) / "a.yaml"
            a.write_text(yaml.dump({"key": "val"}))
            result = runner.invoke(app, ["check", str(a)])
            assert result.exit_code == 1
            assert "Provide at least 2 config files" in result.stdout


    def test_check_with_custom_labels(self):
        """Custom --baseline and --target labels should appear in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev = Path(tmpdir) / "dev.yaml"
            prod = Path(tmpdir) / "prod.yaml"
            dev.write_text(yaml.dump({"host": "localhost"}))
            prod.write_text(yaml.dump({"host": "prod.example.com", "port": 443}))

            result = runner.invoke(app, [
                "check", str(dev), str(prod),
                "--baseline", "staging", "--target", "production",
            ])
            assert result.exit_code == 0
            assert "staging" in result.stdout or "production" in result.stdout
            assert "host" in result.stdout


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


    def test_scan_nonexistent_dir_warning(self):
        """Scan with a non-directory path should warn and skip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev_dir = Path(tmpdir) / "dev"
            dev_dir.mkdir()
            (dev_dir / "c.yaml").write_text(yaml.dump({"host": "localhost"}))
            fake_dir = Path(tmpdir) / "nonexistent"

            result = runner.invoke(app, ["scan", str(dev_dir), str(fake_dir)])
            assert "is not a" in result.stdout.replace("\n", " ")

    def test_scan_unreadable_file_in_dir(self):
        """Scan should warn when a config file in a directory can't be loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev_dir = Path(tmpdir) / "dev"
            prod_dir = Path(tmpdir) / "prod"
            dev_dir.mkdir()
            prod_dir.mkdir()
            (dev_dir / "app.yaml").write_text(yaml.dump({"host": "localhost"}))
            # Write invalid YAML that will cause a load error
            (prod_dir / "broken.yaml").write_text("{{invalid yaml::")
            (prod_dir / "good.yaml").write_text(yaml.dump({"host": "prod.example.com"}))

            result = runner.invoke(app, ["scan", str(dev_dir), str(prod_dir)])
            # Should still succeed but may include a warning about the broken file
            assert result.exit_code == 0 or "could not load" in result.stdout

    def test_scan_breaking_drift_exit_code(self):
        """Scan with breaking drift should exit 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev_dir = Path(tmpdir) / "dev"
            prod_dir = Path(tmpdir) / "prod"
            dev_dir.mkdir()
            prod_dir.mkdir()
            (dev_dir / "c.yaml").write_text(yaml.dump({"database_url": "postgres://dev"}))
            (prod_dir / "c.yaml").write_text(yaml.dump({"database_url": "postgres://prod"}))

            result = runner.invoke(app, ["scan", str(dev_dir), str(prod_dir)])
            assert result.exit_code == 1
            assert "BREAKING" in result.stdout

    def test_scan_no_args_no_config(self):
        """Scan with no directories and no config should error."""
        result = runner.invoke(app, ["scan"])
        assert result.exit_code == 1
        assert "Provide either" in result.stdout

    def test_scan_strict_exits_on_any_drift(self):
        """Scan --strict should exit 1 on non-breaking drift."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev_dir = Path(tmpdir) / "dev"
            prod_dir = Path(tmpdir) / "prod"
            dev_dir.mkdir()
            prod_dir.mkdir()
            (dev_dir / "c.yaml").write_text(yaml.dump({"host": "localhost"}))
            (prod_dir / "c.yaml").write_text(yaml.dump({"host": "prod.example.com"}))

            # Without --strict, info-level changes exit 0
            result = runner.invoke(app, ["scan", str(dev_dir), str(prod_dir)])
            assert result.exit_code == 0

            # With --strict, any drift exits 1
            result = runner.invoke(app, ["scan", str(dev_dir), str(prod_dir), "--strict"])
            assert result.exit_code == 1

    def test_scan_strict_no_drift_exits_zero(self):
        """Scan --strict should exit 0 when no drift exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev_dir = Path(tmpdir) / "dev"
            prod_dir = Path(tmpdir) / "prod"
            dev_dir.mkdir()
            prod_dir.mkdir()
            (dev_dir / "c.yaml").write_text(yaml.dump({"host": "localhost"}))
            (prod_dir / "c.yaml").write_text(yaml.dump({"host": "localhost"}))

            result = runner.invoke(app, ["scan", str(dev_dir), str(prod_dir), "--strict"])
            assert result.exit_code == 0

    def test_scan_silent_breaking_drift(self):
        """Scan silent mode should exit 1 when breaking drift exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev_dir = Path(tmpdir) / "dev"
            prod_dir = Path(tmpdir) / "prod"
            dev_dir.mkdir()
            prod_dir.mkdir()
            (dev_dir / "c.yaml").write_text(yaml.dump({"database_url": "postgres://dev"}))
            (prod_dir / "c.yaml").write_text(yaml.dump({"database_url": "postgres://prod"}))

            result = runner.invoke(app, ["scan", str(dev_dir), str(prod_dir), "--output", "silent"])
            assert result.exit_code == 1


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


    def test_check_toml_files(self):
        """Check command should work with TOML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev = Path(tmpdir) / "dev.toml"
            prod = Path(tmpdir) / "prod.toml"
            dev.write_text('[server]\nhost = "localhost"\nport = 8080\n')
            prod.write_text('[server]\nhost = "prod.example.com"\nport = 8080\n')

            result = runner.invoke(app, ["check", str(dev), str(prod)])
            assert result.exit_code == 0
            assert "server.host" in result.stdout

    def test_check_breaking_drift_table_exit_code(self):
        """Breaking drift with table output should exit 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev = Path(tmpdir) / "dev.yaml"
            prod = Path(tmpdir) / "prod.yaml"
            dev.write_text(yaml.dump({"database_url": "postgres://dev"}))
            prod.write_text(yaml.dump({"database_url": "postgres://prod"}))

            result = runner.invoke(app, ["check", str(dev), str(prod)])
            assert result.exit_code == 1
            assert "BREAKING" in result.stdout

    def test_check_strict_exits_on_any_drift_table(self):
        """Check --strict should exit 1 on non-breaking drift in table mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            a = Path(tmpdir) / "a.yaml"
            b = Path(tmpdir) / "b.yaml"
            a.write_text(yaml.dump({"host": "localhost"}))
            b.write_text(yaml.dump({"host": "staging.example.com"}))

            # Without --strict, info-level changes exit 0
            result = runner.invoke(app, ["check", str(a), str(b)])
            assert result.exit_code == 0

            # With --strict, any drift exits 1
            result = runner.invoke(app, ["check", str(a), str(b), "--strict"])
            assert result.exit_code == 1

    def test_check_strict_silent_exits_on_any_drift(self):
        """Check --strict with --output silent should exit 1 on any drift."""
        with tempfile.TemporaryDirectory() as tmpdir:
            a = Path(tmpdir) / "a.yaml"
            b = Path(tmpdir) / "b.yaml"
            a.write_text(yaml.dump({"host": "localhost"}))
            b.write_text(yaml.dump({"host": "staging.example.com"}))

            result = runner.invoke(app, ["check", str(a), str(b), "--output", "silent", "--strict"])
            assert result.exit_code == 1

    def test_check_strict_no_drift_exits_zero(self):
        """Check --strict should exit 0 when no drift exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            a = Path(tmpdir) / "a.yaml"
            b = Path(tmpdir) / "b.yaml"
            a.write_text(yaml.dump({"host": "localhost"}))
            b.write_text(yaml.dump({"host": "localhost"}))

            result = runner.invoke(app, ["check", str(a), str(b), "--strict"])
            assert result.exit_code == 0

    def test_check_dotenv_files(self):
        """Check command should work with .env files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev = Path(tmpdir) / ".env.dev"
            prod = Path(tmpdir) / ".env.prod"
            dev.write_text("HOST=localhost\nPORT=8080\n")
            prod.write_text("HOST=prod.example.com\nPORT=8080\n")

            result = runner.invoke(app, ["check", str(dev), str(prod)])
            assert result.exit_code == 0
            assert "HOST" in result.stdout

    def test_scan_env_and_toml_dirs(self):
        """Scan should load .env and .toml files from directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev_dir = Path(tmpdir) / "dev"
            prod_dir = Path(tmpdir) / "prod"
            dev_dir.mkdir()
            prod_dir.mkdir()
            (dev_dir / "app.env").write_text("HOST=localhost\n")
            (prod_dir / "app.env").write_text("HOST=prod.example.com\n")

            result = runner.invoke(app, ["scan", str(dev_dir), str(prod_dir), "--output", "json"])
            assert result.exit_code == 0
            data = json.loads(result.stdout)
            assert "prod" in data

    def test_scan_no_changes_env_skipped_in_table(self):
        """Scan with multiple envs where one has no changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dev_dir = Path(tmpdir) / "dev"
            staging_dir = Path(tmpdir) / "staging"
            prod_dir = Path(tmpdir) / "prod"
            for d in [dev_dir, staging_dir, prod_dir]:
                d.mkdir()
            (dev_dir / "c.yaml").write_text(yaml.dump({"host": "localhost", "port": 8080}))
            # staging is identical to dev — no changes
            (staging_dir / "c.yaml").write_text(yaml.dump({"host": "localhost", "port": 8080}))
            (prod_dir / "c.yaml").write_text(yaml.dump({"host": "prod.example.com", "port": 8080}))

            result = runner.invoke(app, ["scan", str(dev_dir), str(staging_dir), str(prod_dir)])
            assert result.exit_code == 0
            # Should show prod drift but skip staging (no changes)
            assert "prod" in result.stdout


class TestVersionCommand:
    def test_version_output(self):
        """--version should print version and exit."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "configdrift" in result.stdout
        assert "0.1.0" in result.stdout
