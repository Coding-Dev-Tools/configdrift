"""Coverage for incomplete scans and machine-readable collision diagnostics."""

import json
import pytest
from configdrift.cli import app
from typer.testing import CliRunner


@pytest.mark.parametrize("target_state", ["missing", "empty", "malformed"])
def test_scan_refuses_target_without_loaded_files(tmp_path, target_state):
    dev = tmp_path / "dev"
    prod = tmp_path / "prod"
    dev.mkdir()
    (dev / "settings.json").write_text('{"host": "localhost"}')
    if target_state != "missing":
        prod.mkdir()
    if target_state == "malformed":
        (prod / "settings.json").write_text("{")

    result = CliRunner().invoke(app, ["scan", str(dev), str(prod), "--output", "silent"])

    assert result.exit_code == 1
    assert "loaded no config files" in result.stdout


def test_scan_requires_a_comparison_environment(tmp_path):
    dev = tmp_path / "dev"
    dev.mkdir()
    (dev / "settings.json").write_text('{"host": "localhost"}')

    result = CliRunner().invoke(app, ["scan", str(dev)])

    assert result.exit_code == 1
    assert "at least two environments" in result.stdout


def test_scan_bool_number_collision_warns_without_corrupting_json(tmp_path):
    dev = tmp_path / "dev"
    prod = tmp_path / "prod"
    for directory in (dev, prod):
        directory.mkdir()
        (directory / "a.json").write_text('{"debug": true}')
        (directory / "b.json").write_text('{"debug": 1}')

    result = CliRunner().invoke(app, ["scan", str(dev), str(prod), "--output", "json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["prod"]["count"] == 0
    assert "conflicting" in result.stderr


def test_scan_load_warning_does_not_corrupt_json(tmp_path):
    dev = tmp_path / "dev"
    prod = tmp_path / "prod"
    for directory in (dev, prod):
        directory.mkdir()
        (directory / "settings.json").write_text('{"host": "localhost"}')
    (prod / "broken.json").write_text("{")

    result = CliRunner().invoke(app, ["scan", str(dev), str(prod), "--output", "json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["prod"]["count"] == 0
    assert "could not load" in result.stderr
