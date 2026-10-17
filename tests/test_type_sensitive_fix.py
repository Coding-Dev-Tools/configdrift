"""Drift detection and fixes must agree on booleans inside container values."""

import json

import pytest
from typer.testing import CliRunner

from configdrift.cli import app
from configdrift.diff import diff_configs


@pytest.mark.parametrize("before,after", [(True, 1), ([True], [1]), ([{"enabled": True}], [{"enabled": 1}])])
def test_fix_corrects_bool_number_drift_and_converges(tmp_path, before, after):
    baseline = tmp_path / "dev.json"
    target = tmp_path / "prod.json"
    baseline.write_text(json.dumps({"setting": before}))
    target.write_text(json.dumps({"setting": after}))
    runner = CliRunner()

    assert diff_configs({"setting": before}, {"setting": after}).count == 1
    result = runner.invoke(app, ["fix", str(baseline), str(target)])

    assert result.exit_code == 0
    assert json.dumps(json.loads(target.read_text())["setting"]) == json.dumps(before)
    assert diff_configs({"setting": before}, json.loads(target.read_text())).count == 0
    assert runner.invoke(app, ["fix", str(baseline), str(target)]).exit_code == 0


def test_int_float_equivalence_is_retained():
    assert diff_configs({"setting": [1, {"count": 2}]}, {"setting": [1.0, {"count": 2.0}]}).count == 0


def test_json_output_preserves_long_literal_values(tmp_path):
    baseline = tmp_path / "dev.json"
    target = tmp_path / "prod.json"
    value = "[green]" + "x" * 150 + "[red]"
    baseline.write_text(json.dumps({"setting": "before"}))
    target.write_text(json.dumps({"setting": value}))

    result = CliRunner().invoke(app, ["check", str(baseline), str(target), "--output", "json"])

    data = json.loads(result.stdout)
    assert data["target"]["changes"][0]["new_value"] == value
