import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_test_step_executes_full_suite():
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    test_steps = workflow["jobs"]["test"]["steps"]
    run_tests = next(
        (step for step in test_steps if step.get("name") == "Run tests"),
        None,
    )
    assert run_tests is not None, "CI test job must include a 'Run tests' step"
    assert run_tests.get("run") == "python -m pytest tests/ -v --tb=short"
