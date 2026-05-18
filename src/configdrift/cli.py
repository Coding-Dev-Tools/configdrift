"""ConfigDrift CLI entry point."""

import typer
from enum import Enum
from pathlib import Path
from rich.console import Console
from rich.table import Table
from typing import Any

try:
    from revenueholdings_license import require_license
except ImportError:
    require_license = None  # License check skipped (dev/CI mode)

from configdrift import __version__
from configdrift.diff import (
    Severity,
    diff_environments,
)
from configdrift.loader import load_file

app = typer.Typer(
    name="configdrift",
    help="Detect and fix configuration file drift across environments.",
    invoke_without_command=True,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"configdrift v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show the version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
):
    if require_license:
        require_license("configdrift")


class OutputFormat(str, Enum):
    TABLE = "table"
    JSON = "json"
    SILENT = "silent"


@app.command()
def check(
    files: list[str] = typer.Argument(..., help="Config files to compare (2+ files)."),  # noqa: B008
    baseline: str = typer.Option(
        "dev", "--baseline", "-b",
        help="Baseline environment name (used as label for first file in 2-file mode).",
    ),  # noqa: B008
    target: str = typer.Option("target", "--target", "-t", help="Target environment label for second file."),  # noqa: B008
    output: OutputFormat = typer.Option(OutputFormat.TABLE, "--output", "-o", help="Output format."),  # noqa: B008
):
    """Compare 2+ config files and report drift."""
    if len(files) < 2:
        console.print("[red]ERROR: Provide at least 2 config files to compare.[/red]")
        raise typer.Exit(code=1)

    env_configs: dict[str, dict[str, Any]] = {}
    env_labels = [baseline, target] if len(files) == 2 else [f"file_{i + 1}" for i in range(len(files))]

    for label, filepath in zip(env_labels, files, strict=False):
        try:
            env_configs[label] = load_file(filepath)
        except Exception as e:
            console.print(f"[red]Error loading {filepath}: {e}[/red]")
            raise typer.Exit(code=1) from e

    baseline_env = env_labels[0]
    results = diff_environments(env_configs, baseline_env=baseline_env)

    if output == OutputFormat.JSON:
        _output_json(results)
    elif output == OutputFormat.SILENT:
        has_drift = any(r.has_breaking for r in results.values())
        raise typer.Exit(code=1 if has_drift else 0)
    else:
        _output_table(results, baseline_env)

    # Exit codes for CI gating
    has_drift = any(r.has_breaking for r in results.values())
    if has_drift:
        raise typer.Exit(code=1)


def _output_table(results: dict[str, Any], baseline_env: str):
    for env_name, diff_result in results.items():
        if not diff_result.changes:
            continue

        table = Table(title=f"Config Drift: {baseline_env} → {env_name}")
        table.add_column("Key", style="cyan")
        table.add_column("Change", style="bold")
        table.add_column("Old Value", style="yellow")
        table.add_column("New Value", style="green")
        table.add_column("Severity", style="magenta")

        for change in diff_result.changes:
            symbol = {"added": "+", "removed": "-", "changed": "~"}[change.change_type.value]
            old_str = str(change.old_value) if change.old_value is not None else ""
            new_str = str(change.new_value) if change.new_value is not None else ""
            sev_style = (
            "red" if change.severity == Severity.BREAKING
            else "yellow" if change.severity == Severity.WARNING
            else "white"
        )
            table.add_row(
                change.key,
                f"{symbol} {change.change_type.value}",
                old_str,
                new_str,
                f"[{sev_style}]{change.severity.value}[/{sev_style}]",
            )

        console.print(table)
        console.print(f"Total changes: {diff_result.count}")
        if diff_result.has_breaking:
            console.print("[red]⚠ BREAKING CHANGES DETECTED[/red]")
        console.print()


def _output_json(results: dict[str, Any]):
    import json
    output = {}
    for env_name, diff_result in results.items():
        output[env_name] = {
            "changes": [
                {
                    "key": c.key,
                    "type": c.change_type.value,
                    "old_value": c.old_value,
                    "new_value": c.new_value,
                    "severity": c.severity.value,
                }
                for c in diff_result.changes
            ],
            "has_breaking": diff_result.has_breaking,
            "count": diff_result.count,
        }
    console.print(json.dumps(output, indent=2, default=str))


@app.command()
def scan(
    dirs: list[str] | None = typer.Argument(  # noqa: B008
        None, help="Directories containing config files. Each dir is treated as an environment.",
    ),
    baseline: str = typer.Option("dev", "--baseline", "-b", help="Baseline directory name for comparison."),  # noqa: B008
    config: str | None = typer.Option(None, "--config", "-c", help="Path to .configdrift.yaml config file."),  # noqa: B008
    output: OutputFormat = typer.Option(OutputFormat.TABLE, "--output", "-o", help="Output format."),  # noqa: B008
):
    """Scan directories of config files and compare environments."""
    if config:
        # Load config file for directory → env mapping (raw, not flattened)
        import yaml as _yaml
        with open(config, encoding="utf-8") as _f:
            cfg_data = _yaml.safe_load(_f) or {}
        dir_mapping = cfg_data.get("environments", {})
    elif dirs:
        # Use directory basenames as env names
        dir_mapping = {}
        for d in dirs:
            env_name = Path(d).stem
            dir_mapping[env_name] = d
    else:
        console.print("[red]ERROR: Provide either --config or directories as arguments.[/red]")
        raise typer.Exit(code=1)

    if baseline not in dir_mapping:
        console.print(f"[red]Baseline environment '{baseline}' not found.[/red]")
        raise typer.Exit(code=1)

    env_configs: dict[str, dict[str, Any]] = {}
    for env_name, dir_path in dir_mapping.items():
        env_configs[env_name] = {}
        p = Path(dir_path)
        if not p.is_dir():
            console.print(f"[yellow]Warning: '{dir_path}' is not a directory, skipping.[/yellow]")
            continue
        # Load all supported config files in the directory and merge
        for ext in ("*.yaml", "*.yml", "*.json", "*.toml", "*.env"):
            for f in p.glob(ext):
                try:
                    data = load_file(str(f))
                    env_configs[env_name].update(data)
                except Exception as e:
                    console.print(f"[yellow]Warning: could not load {f}: {e}[/yellow]")

    results = diff_environments(env_configs, baseline_env=baseline)

    if output == OutputFormat.JSON:
        _output_json(results)
    elif output == OutputFormat.SILENT:
        has_drift = any(r.has_breaking for r in results.values())
        raise typer.Exit(code=1 if has_drift else 0)
    else:
        _output_table(results, baseline)

    has_drift = any(r.has_breaking for r in results.values())
    if has_drift:
        raise typer.Exit(code=1)


@app.command()
def init(
    path: str = typer.Argument(".", help="Directory to create .configdrift.yaml in."),
):
    """Generate a .configdrift.yaml configuration file."""
    template = """# ConfigDrift configuration
# Define your environments and the config files to compare.

environments:
  dev: ./config/dev
  staging: ./config/staging
  prod: ./config/prod
"""
    target = Path(path) / ".configdrift.yaml"
    if target.exists():
        console.print(f"[yellow]File already exists: {target}[/yellow]")
        raise typer.Exit(code=1)
    target.write_text(template)
    console.print(f"[green]Created {target}[/green]")
